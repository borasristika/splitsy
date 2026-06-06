import json
import tempfile
import threading
import unittest
import urllib.request
from src import server


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.httpd = server.make_server(host="127.0.0.1", port=0, data_dir=cls.dir)
        cls.port = cls.httpd.server_address[1]
        cls.t = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return json.loads(r.read().decode())

    def _post(self, path, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=data, headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def test_state_has_keys(self):
        state = self._get("/api/state")
        for k in ("expenses", "rules", "settings", "totals"):
            self.assertIn(k, state)

    def test_save_expenses_returns_totals(self):
        exp = [{"id": "a", "date": "2026-01-01", "merchant": "M", "amount": 30.0,
                "category": "Misc", "status": "split", "source": "s",
                "rawDescription": "M", "matchKey": "M",
                "split": {"participants": ["p1"], "includeSelf": True, "shares": "equal"}}]
        res = self._post("/api/expenses", {"expenses": exp})
        self.assertTrue(res["ok"])
        self.assertEqual(res["totals"], {"p1": 15.0})


if __name__ == "__main__":
    unittest.main()
