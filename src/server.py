"""Tiny stdlib HTTP server: JSON API + static frontend from web/."""
import json
import os
import cgi
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from src.store import Store
from src.reports import per_person_totals, per_person_csv, combined_csv
from src.pdf_export import per_person_pdf, combined_pdf
from src.ingest import ingest_text
from src.splitter import compute_shares
from src import splitwise


def _filter_by_source(expenses, source):
    if not source or source == "ALL":
        return expenses
    return [e for e in expenses if e.get("source") == source]


def _scope_label(source):
    return "All statements" if (not source or source == "ALL") else source

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

_CONTENT_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".svg": "image/svg+xml",
}


def _make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # quiet

        # ---- helpers ----
        def _send_json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text, content_type="text/plain", code=200, filename=None):
            self._send_bytes(text.encode(), content_type, code, filename)

        def _send_bytes(self, body, content_type="application/octet-stream", code=200, filename=None):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length).decode() or "{}")

        def _state(self):
            expenses = store.load_expenses()
            return {
                "expenses": expenses,
                "rules": store.load_rules(),
                "settings": store.load_settings(),
                "totals": per_person_totals(expenses),
            }

        # ---- routing ----
        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            q = parse_qs(parsed.query)
            source = q.get("source", [None])[0]
            if path == "/api/state":
                return self._send_json(self._state())
            if path == "/api/totals":
                expenses = _filter_by_source(store.load_expenses(), source)
                return self._send_json({"totals": per_person_totals(expenses)})
            if path == "/api/export/combined.csv":
                expenses = _filter_by_source(store.load_expenses(), source)
                people = store.load_settings()["people"]
                return self._send_text(combined_csv(expenses, people),
                                        "text/csv", filename="combined.csv")
            if path == "/api/export/person.csv":
                pid = q.get("id", [None])[0]
                expenses = _filter_by_source(store.load_expenses(), source)
                people = store.load_settings()["people"]
                return self._send_text(per_person_csv(expenses, pid, people),
                                        "text/csv", filename=f"{self._person_name(pid)}.csv")
            if path == "/api/export/combined.pdf":
                expenses = _filter_by_source(store.load_expenses(), source)
                people = store.load_settings()["people"]
                pdf = combined_pdf(expenses, people, _scope_label(source), self._today())
                return self._send_bytes(pdf, "application/pdf", filename="split-expenses-combined.pdf")
            if path == "/api/export/person.pdf":
                pid = q.get("id", [None])[0]
                expenses = _filter_by_source(store.load_expenses(), source)
                people = store.load_settings()["people"]
                pdf = per_person_pdf(expenses, pid, people, _scope_label(source), self._today())
                return self._send_bytes(pdf, "application/pdf",
                                        filename=f"{self._person_name(pid)}-split-expenses.pdf")
            return self._serve_static(path)

        def _today(self):
            return datetime.date.today().isoformat()

        def _person_name(self, pid):
            for p in store.load_settings()["people"]:
                if p["id"] == pid:
                    return p["name"].replace(" ", "_")
            return str(pid)

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/expenses":
                data = self._read_json()
                store.save_expenses(data["expenses"])
                return self._send_json({"ok": True, "totals": per_person_totals(data["expenses"])})
            if path == "/api/rules":
                data = self._read_json()
                store.save_rules(data["rules"])
                return self._send_json({"ok": True})
            if path == "/api/settings":
                data = self._read_json()
                store.save_settings(data["settings"])
                return self._send_json({"ok": True})
            if path == "/api/upload":
                return self._handle_upload()
            if path == "/api/splitwise/connect":
                return self._handle_sw_connect()
            if path == "/api/splitwise/push":
                return self._handle_sw_push()
            return self._send_json({"error": "not found"}, 404)

        def _handle_sw_connect(self):
            token = (self._read_json().get("token") or "").strip()
            if not token:
                return self._send_json({"error": "missing token"}, 400)
            try:
                user = splitwise.get_current_user(token)
                friends = splitwise.get_friends(token)
                groups = splitwise.get_groups(token)
            except splitwise.SplitwiseError as e:
                return self._send_json({"error": str(e)}, 400)
            settings = store.load_settings()
            settings["splitwiseToken"] = token
            settings["splitwiseUserId"] = user["id"]
            settings["splitwiseGroups"] = [{"id": g["id"], "name": g["name"]} for g in groups]
            settings["splitwiseFriends"] = [
                {"id": f["id"],
                 "name": (f"{f.get('first_name','')} {f.get('last_name','') or ''}".strip()
                          or f.get("email") or str(f["id"]))}
                for f in friends]
            store.save_settings(settings)
            return self._send_json({
                "currentUser": {"id": user["id"],
                                "name": f"{user.get('first_name','')} {user.get('last_name','') or ''}".strip()},
                "friends": settings["splitwiseFriends"],
                "groups": settings["splitwiseGroups"],
            })

        def _handle_sw_push(self):
            data = self._read_json()
            person_id = data.get("personId")
            group_id = data.get("groupId") or 0
            settings = store.load_settings()
            token = settings.get("splitwiseToken")
            my_id = settings.get("splitwiseUserId")
            if not token or not my_id:
                return self._send_json({"error": "Splitwise not connected"}, 400)
            person_map = {p["id"]: p.get("splitwiseUserId") for p in settings["people"]}
            expenses = store.load_expenses()
            pushed, skipped, errors = [], [], []
            for e in expenses:
                if e.get("status") != "split":
                    continue
                if person_id not in compute_shares(e):
                    continue
                if e.get("splitwiseExpenseId"):
                    skipped.append(e["id"])
                    continue
                try:
                    payload = splitwise.build_expense_payload(e, my_id, person_map, group_id)
                    sw_id = splitwise.create_expense(token, payload)
                    e["splitwiseExpenseId"] = sw_id
                    pushed.append(e["id"])
                except splitwise.SplitwiseError as ex:
                    errors.append({"id": e["id"], "merchant": e.get("merchant"), "error": str(ex)})
            store.save_expenses(expenses)
            return self._send_json({"pushed": len(pushed), "skipped": len(skipped),
                                    "errors": errors})

        def _handle_upload(self):
            ctype = self.headers.get("Content-Type", "")
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype})
            fileitem = form["file"]
            import tempfile
            from src.pdf_text import extract_text
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(fileitem.file.read())
                tmp_path = tmp.name
            source = os.path.splitext(os.path.basename(fileitem.filename))[0]
            text = extract_text(tmp_path)
            os.unlink(tmp_path)
            result = ingest_text(text, source=source, existing=store.load_expenses(),
                                 rules=store.load_rules(), settings=store.load_settings())
            store.save_expenses(result["expenses"])
            return self._send_json({"report": result["report"],
                                    "expenses": result["expenses"],
                                    "totals": per_person_totals(result["expenses"])})

        def _serve_static(self, path):
            if path == "/":
                path = "/index.html"
            full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
            if not full.startswith(WEB_DIR) or not os.path.isfile(full):
                return self._send_json({"error": "not found"}, 404)
            ext = os.path.splitext(full)[1]
            with open(full, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", _CONTENT_TYPES.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def make_server(host="127.0.0.1", port=8000, data_dir=None):
    data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    store = Store(data_dir)
    return ThreadingHTTPServer((host, port), _make_handler(store))


def main():
    httpd = make_server(port=int(os.environ.get("PORT", "8000")))
    host, port = httpd.server_address
    print(f"Expense Splitter running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
