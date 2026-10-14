import unittest
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from backend.app.recipe_catalog import INGREDIENTS, recipes
from backend.app.seed import INGREDIENTS as BASE_INGREDIENTS, RECIPES


class CatalogDefinitionTests(unittest.TestCase):
    def test_count_distinct_compositions_and_editable_payloads(self):
        from backend.app.admin import RecipeEdit

        rows = recipes()
        self.assertEqual(len(rows) + len(RECIPES), 178)
        self.assertEqual(Counter(r["meal"] for r in rows), {"breakfast": 42, "lunch": 58, "dinner": 58})
        signatures = [tuple(sorted(r["ingredients"])) for r in rows]
        signatures.extend(tuple(sorted(r[5])) for r in RECIPES)
        self.assertEqual(len(signatures), len(set(signatures)))
        known = {r[0] for r in BASE_INGREDIENTS + INGREDIENTS}
        self.assertEqual(len(known), 47)
        for r in rows:
            self.assertLessEqual(set(r["ingredients"]), known)
            RecipeEdit(
                name=r["name"], meal=r["meal"], ingredients=r["ingredients"],
                instructions=r["data"]["instructions"], minutes=r["data"]["minutes"],
                enabled=True, expected_version=r["version"],
            )
        for lang in ("zh", "en", "ja"):
            self.assertEqual(len({r["name"][lang] for r in rows}), 158)

    def test_all_new_illustrations_exist_and_parse(self):
        folder = Path(__file__).resolve().parents[2] / "frontend/public/recipe-art"
        for row in recipes():
            for lang in ("zh", "en", "ja"):
                suffix = ".svg" if lang == "zh" else f".{lang}.svg"
                path = folder / (row["id"] + suffix)
                root = ElementTree.parse(path).getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertIn(row["name"][lang], root.find("{http://www.w3.org/2000/svg}title").text)
