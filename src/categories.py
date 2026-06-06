"""Default category buckets and a keyword-based guesser."""

DEFAULT_CATEGORIES = [
    "Coffee", "Grocery", "Restaurants", "Beauty",
    "Shopping", "Transport", "Subscriptions", "Miscellaneous",
]

# Keyword -> category. Checked as case-insensitive substring of the merchant text.
_KEYWORDS = [
    ("STARBUCKS", "Coffee"), ("COFFEE", "Coffee"), ("CAFE", "Coffee"),
    ("PEET", "Coffee"), ("DUNKIN", "Coffee"), ("BLUE BOTTLE", "Coffee"),
    ("SAFEWAY", "Grocery"), ("INDIA CASH", "Grocery"), ("HANKOOK", "Grocery"),
    ("SUPERMARKET", "Grocery"), ("TRADER", "Grocery"), ("WHOLE FOODS", "Grocery"),
    ("COSTCO", "Grocery"), ("MEAT CORNER", "Grocery"), ("GROCERY", "Grocery"),
    ("MARKET", "Grocery"),
    ("DARBAR", "Restaurants"), ("RESTAURANT", "Restaurants"), ("GRILL", "Restaurants"),
    ("KITCHEN", "Restaurants"), ("PIZZA", "Restaurants"), ("STREET FOOD", "Restaurants"),
    ("SEPHORA", "Beauty"), ("ULTA", "Beauty"), ("SALON", "Beauty"),
    ("SPA", "Beauty"), ("NAIL", "Beauty"),
    ("SHEIN", "Shopping"), ("AMAZON", "Shopping"), ("GOODWILL", "Shopping"),
    ("TARGET", "Shopping"), ("APPLE.COM/BILL", "Subscriptions"),
    ("UBER", "Transport"), ("LYFT", "Transport"), ("SHELL", "Transport"),
    ("CHEVRON", "Transport"), ("GAS", "Transport"),
    ("SPOTIFY", "Subscriptions"), ("NETFLIX", "Subscriptions"),
    ("UDEMY", "Subscriptions"),
]


def guess_category(merchant: str) -> str:
    text = (merchant or "").upper()
    for keyword, category in _KEYWORDS:
        if keyword in text:
            return category
    return "Miscellaneous"
