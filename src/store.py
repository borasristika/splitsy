"""Read/write the three JSON data files. All paths under one data directory."""
import json
import os
from src.categories import DEFAULT_CATEGORIES


def default_settings() -> dict:
    return {
        "people": [],
        "defaultPartnerId": None,
        "defaultSplitWays": 2,
        "categories": list(DEFAULT_CATEGORIES),
        "statementFolder": None,
    }


class Store:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    def _load(self, name: str, default):
        path = self._path(name)
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, name: str, data):
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_expenses(self):
        return self._load("expenses.json", [])

    def save_expenses(self, expenses):
        self._save("expenses.json", expenses)

    def load_rules(self):
        return self._load("rules.json", {})

    def save_rules(self, rules):
        self._save("rules.json", rules)

    def load_settings(self):
        s = self._load("settings.json", None)
        if s is None:
            s = default_settings()
            self._save("settings.json", s)
        return s

    def save_settings(self, settings):
        self._save("settings.json", settings)
