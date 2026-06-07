"""Generate clean, shareable PDF summaries of split expenses (via fpdf2)."""
from fpdf import FPDF

from src.money import to_cents, to_dollars
from src.splitter import compute_shares

PINK = (242, 102, 160)
PINK_T = (255, 229, 240)
GREY = (120, 120, 120)


def _s(t) -> str:
    """Core PDF fonts are latin-1 only; replace anything outside it."""
    return str(t).encode("latin-1", "replace").decode("latin-1")


def _trim(t, n):
    t = str(t)
    return t if len(t) <= n else t[:n - 1] + "."


def _row(pdf, cells, h=7, fill=False, border=1):
    for i, (text, w, align) in enumerate(cells):
        last = i == len(cells) - 1
        pdf.cell(w, h, _s(text), border=border, align=align, fill=fill,
                 new_x="LMARGIN" if last else "RIGHT",
                 new_y="NEXT" if last else "TOP")


def _statements(expenses):
    return sorted({e.get("source", "") for e in expenses if e.get("source")})


def _header(pdf, title, generated_on, statements):
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*PINK)
    pdf.cell(0, 10, _s(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    stmt = "; ".join(statements) if statements else "(none)"
    pdf.multi_cell(0, 5, _s("Statements included: " + stmt))
    pdf.cell(0, 6, _s("Generated " + generated_on), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def per_person_pdf(expenses, person_id, people, generated_on) -> bytes:
    person = next((p for p in people if p["id"] == person_id), None)
    name = person["name"] if person else str(person_id)

    rows, total_cents = [], 0
    for e in expenses:
        shares = compute_shares(e)
        if person_id in shares:
            rows.append((e["date"], e["merchant"], e["category"], e["amount"], shares[person_id]))
            total_cents += to_cents(shares[person_id])

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    _header(pdf, f"Expenses to split with {name}", generated_on, _statements(expenses))

    cols = [("Date", 24, "L"), ("Merchant", 72, "L"), ("Category", 34, "L"),
            ("Total", 28, "R"), (f"{name} owes", 28, "R")]
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*PINK_T)
    _row(pdf, [(c[0], c[1], c[2]) for c in cols], fill=True)

    pdf.set_font("Helvetica", "", 10)
    for d, m, c, tot, share in rows:
        _row(pdf, [(d, 24, "L"), (_trim(m, 40), 72, "L"), (_trim(c, 18), 34, "L"),
                   (f"${tot:.2f}", 28, "R"), (f"${share:.2f}", 28, "R")])
    if not rows:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, _s(f"No split expenses for {name} in this selection."),
                 new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(*PINK_T)
    _row(pdf, [("", 24, "L"), ("", 72, "L"), ("Total owed", 34, "L"),
               ("", 28, "R"), (f"${to_dollars(total_cents):.2f}", 28, "R")], fill=True)
    return bytes(pdf.output())


def combined_pdf(expenses, people, generated_on) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    _header(pdf, "Split expenses - combined", generated_on, _statements(expenses))

    n = max(1, len(people))
    person_w = 26
    date_w, cat_w, total_w = 22, 30, 24
    merch_w = max(40, 277 - (date_w + cat_w + total_w + person_w * n))

    head = [("Date", date_w, "L"), ("Merchant", merch_w, "L"), ("Category", cat_w, "L"),
            ("Total", total_w, "R")] + [(p["name"], person_w, "R") for p in people]
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*PINK_T)
    _row(pdf, [(h[0], h[1], h[2]) for h in head], fill=True)

    totals = {p["id"]: 0 for p in people}
    pdf.set_font("Helvetica", "", 10)
    for e in expenses:
        shares = compute_shares(e)
        if not shares:
            continue
        cells = [(e["date"], date_w, "L"), (_trim(e["merchant"], int(merch_w / 1.9)), merch_w, "L"),
                 (_trim(e["category"], 16), cat_w, "L"), (f"${e['amount']:.2f}", total_w, "R")]
        for p in people:
            amt = shares.get(p["id"], 0.0)
            totals[p["id"]] += to_cents(amt)
            cells.append((f"${amt:.2f}" if amt else "-", person_w, "R"))
        _row(pdf, cells)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(*PINK_T)
    foot = [("", date_w, "L"), ("Totals", merch_w, "L"), ("", cat_w, "L"), ("", total_w, "R")]
    foot += [(f"${to_dollars(totals[p['id']]):.2f}", person_w, "R") for p in people]
    _row(pdf, foot, fill=True)
    return bytes(pdf.output())
