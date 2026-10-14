import unittest
from pathlib import Path
from xml.etree import ElementTree

from backend.app.nut_catalog import INGREDIENTS, recipes
from backend.app.recipe_catalog import recipes as base_extension
from backend.app.seed import RECIPES


class NutCatalogTests(unittest.TestCase):
    def test_six_distinct_three_language_breakfasts_without_egg(self):
        from backend.app.admin import RecipeEdit
        rows = recipes()
        self.assertEqual(len(rows), 6)
        self.assertEqual(len(rows) + len(base_extension()) + len(RECIPES), 184)
        nuts = {r[0] for r in INGREDIENTS}
        self.assertEqual(nuts, {"05040", "05014"})
        self.assertTrue(all(r[4] == ["nuts"] for r in INGREDIENTS))
        self.assertEqual(len({tuple(sorted(r["ingredients"])) for r in rows}), 6)
        for r in rows:
            self.assertEqual(r["meal"], "breakfast")
            self.assertTrue(nuts & set(r["ingredients"]))
            self.assertNotIn("12005", r["ingredients"])
            self.assertEqual(set(r["name"]), {"zh", "en", "ja"})
            self.assertEqual(set(r["data"]["instructions"]), {"zh", "en", "ja"})
            RecipeEdit(name=r["name"], meal=r["meal"], ingredients=r["ingredients"],
                       instructions=r["data"]["instructions"], minutes=r["data"]["minutes"],
                       enabled=True, expected_version=r["version"])

    def test_nut_images_are_valid_and_localized(self):
        art = Path(__file__).resolve().parents[2] / "frontend/public/recipe-art"
        for row in recipes():
            for lang in ("zh", "en", "ja"):
                suffix = ".svg" if lang == "zh" else f".{lang}.svg"
                root = ElementTree.parse(art / (row["id"] + suffix)).getroot()
                title = root.find("{http://www.w3.org/2000/svg}title").text
                self.assertIn(row["name"][lang], title)
