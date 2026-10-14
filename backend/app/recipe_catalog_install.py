"""Transactional, idempotent catalog extension; existing administrator edits win."""

from pathlib import Path

from psycopg.types.json import Jsonb

from .planner import calculate, catalog
from .recipe_catalog import INGREDIENTS, VERSION, recipes

ART = Path(__file__).resolve().parents[2] / "frontend/public/recipe-art"


def install_entries(c, ingredient_definitions, entries, version):
    c.execute("SELECT pg_advisory_xact_lock(1782026)")
    added_ingredients = added_recipes = 0
    for code, zh, en, ja, allergens, price in ingredient_definitions:
        # Resolve the exact same dataset as the application's existing rice.
        dataset = c.execute(
            "SELECT dataset_id FROM app_ingredients WHERE code='01088'"
        ).fetchone()
        if not dataset:
            raise ValueError("Install the base catalog first")
        food = c.execute(
            "SELECT * FROM foods WHERE dataset_id=%s AND code=%s",
            (dataset["dataset_id"], code),
        ).fetchone()
        if not food:
            raise ValueError(f"Missing source food: {code}")
        data = {
            "version": version,
            "state": "as_named_edible",
            "price_kind": "synthetic_demo",
            "price_basis": "JPY per 100g edible ingredient in named state",
            "cross_contact": "unknown",
            "review": "engineering_checked_not_clinical",
            "source_name_ja": food["name_ja"],
            "food_group": food["food_group"],
        }
        if code == "01026":
            data["allergen_note"] = "Conservative wheat/milk/egg/soy flags; check the actual bread label."
        if "nuts" in allergens:
            data["allergen_note"] = "Contains tree nuts. Check the actual ingredient label and cross-contact information."
        added_ingredients += c.execute(
            """INSERT INTO app_ingredients(code,dataset_id,name,allergens,price_per_100g,data)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (code, dataset["dataset_id"], Jsonb({"zh": zh, "en": en, "ja": ja}),
             allergens, price, Jsonb(data)),
        ).rowcount
    ingredients, _ = catalog(c)
    if not entries or len({r["id"] for r in entries}) != len(entries):
        raise ValueError("Unexpected catalog size or duplicate IDs")
    fingerprints = set()
    for row in entries:
        fingerprint = tuple(sorted(row["ingredients"]))
        if fingerprint in fingerprints:
            raise ValueError("Duplicate ingredient composition")
        fingerprints.add(fingerprint)
        if not (ART / f"{row['id']}.svg").is_file():
            raise ValueError(f"Missing recipe illustration: {row['id']}")
        for scale in row["data"]["scales"]:
            meal = calculate(row, ingredients, scale)
            if meal["nutrition"]["energy_kcal"] is None or meal["cost_jpy"] <= 0:
                raise ValueError(f"Incomplete recipe calculation: {row['id']}")
        added_recipes += c.execute(
            """INSERT INTO app_recipes(id,version,meal,name,ingredients,data,enabled)
            VALUES(%s,%s,%s,%s,%s,%s,true) ON CONFLICT DO NOTHING""",
            (row["id"], row["version"], row["meal"], Jsonb(row["name"]),
             Jsonb(row["ingredients"]), Jsonb(row["data"])),
        ).rowcount
    if added_recipes or added_ingredients:
        c.execute("DELETE FROM app_home_cache")
    return {"added_ingredients": added_ingredients, "added_recipes": added_recipes}


def install(c):
    entries = recipes()
    if len(entries) != 158:
        raise ValueError("Unexpected base catalog size")
    return install_entries(c, INGREDIENTS, entries, VERSION)


if __name__ == "__main__":
    # This offline data operation requires the database owner's credentials.
    import psycopg
    from psycopg.rows import dict_row
    from backend.config import settings

    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        print(install(connection))
