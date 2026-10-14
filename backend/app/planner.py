"""Deterministic, versioned demonstration planner; no clinical target inference."""

from decimal import Decimal
from .db import connect
from .meal_selection import animal_food, select_meals
from .feedback import explain, labels, ResultCheckError
from .budget import valid_interval
from .food_requirements import satisfies_foods, describe_foods
from .qa_policy import text

FIELDS = {
    "ENERC_KCAL": ("energy_kcal", "kcal"),
    "PROT-": ("protein_g", "g"),
    "FAT-": ("fat_g", "g"),
    "CHOCDF-": ("carbs_g", "g"),
    "FIB-": ("fiber_g", "g"),
    "NA": ("sodium_mg", "mg"),
    "K": ("potassium_mg", "mg"),
}
RULE_VERSION = "catalog-178-budget-food-constraints-v4"
NOTE = {
    "zh": "演示方案：价格为模拟值，目标由用户确认；尚未经营养师审核，不用于个体治疗。",
    "en": "Demonstration: synthetic prices and user-confirmed targets. Not dietitian reviewed or a treatment plan.",
    "ja": "デモ：価格は仮定値、目標は利用者確認値です。管理栄養士による確認や個別治療用ではありません。",
}


def catalog(c=None):
    if c is None:
        with connect() as c:
            return catalog(c)
    rows = c.execute("SELECT * FROM app_ingredients ORDER BY code").fetchall()
    ingredients = {r["code"]: r for r in rows}
    for row in rows:
        values = c.execute(
            """SELECT v.*,n.metadata FROM food_values v JOIN food_nutrients n
          ON (n.dataset_id,n.code)=(v.dataset_id,v.nutrient_code)
          WHERE v.dataset_id=%s AND v.food_code=%s AND v.nutrient_code=ANY(%s)""",
            (row["dataset_id"], row["code"], list(FIELDS)),
        ).fetchall()
        row["nutrients"] = {v["nutrient_code"]: v for v in values}
        row["provenance"] = c.execute(
            "SELECT source FROM foods WHERE dataset_id=%s AND code=%s",
            (row["dataset_id"], row["code"]),
        ).fetchone()["source"]
    return ingredients, c.execute("SELECT * FROM app_recipes WHERE enabled ORDER BY id").fetchall()


def sodium_upper(v):
    # MEXT PDF physical pp33–34 (printed28–29): Tr is below 0.5mg for sodium.
    if v["status"] == "trace":
        return Decimal("0.5")
    if v["status"] != "numeric" or v["value"] is None:
        raise ValueError("Unknown sodium cannot satisfy a hard limit")
    value = Decimal(v["value"])
    if value == 0:
        return Decimal("0.1")
    step = Decimal(10) ** max(0, value.adjusted() - 1)
    return value + step / 2


def calculate(recipe, ingredients, scale=1):
    if scale not in recipe["data"]["scales"]:
        raise ValueError("Unsupported portion")
    totals = {name: Decimal(0) for name, _ in FIELDS.values()}
    unknown = set()
    flags = []
    sodium = Decimal(0)
    cost = Decimal(0)
    parts = []
    allergens = set()
    for code, base_grams in recipe["ingredients"].items():
        f = ingredients[code]
        grams = Decimal(str(base_grams)) * Decimal(str(scale))
        factor = grams / 100
        cost += Decimal(f["price_per_100g"]) * factor
        allergens.update(f["allergens"])
        for nutrient, (name, unit) in FIELDS.items():
            v = f["nutrients"].get(nutrient)
            if not v:
                unknown.add(name)
                continue
            if v["status"] == "numeric" and v["value"] is not None:
                totals[name] += Decimal(v["value"]) * factor
            else:
                unknown.add(name)
                flags.append(
                    {
                        "code": code,
                        "nutrient": nutrient,
                        "raw": v["raw"],
                        "status": v["status"],
                    }
                )
            if v["estimated"]:
                flags.append(
                    {
                        "code": code,
                        "nutrient": nutrient,
                        "raw": v["raw"],
                        "status": "estimated",
                    }
                )
        sodium += sodium_upper(f["nutrients"]["NA"]) * factor
        parts.append(
            {
                "code": code,
                "dataset_id": f["dataset_id"],
                "name": f["name"],
                "grams": float(grams),
                "ingredient_version": f["data"].get("version"),
                "source": f["provenance"],
                "nutrient_snapshot": {
                    k: {
                        "raw": v["raw"],
                        "value": str(v["value"]) if v["value"] is not None else None,
                        "status": v["status"],
                        "estimated": v["estimated"],
                    }
                    for k, v in f["nutrients"].items()
                },
                "price_jpy_per_100g": float(f["price_per_100g"]),
                "excel_sheet": f["provenance"]["excel_sheet"],
                "excel_row": f["provenance"]["excel_row"],
                "nutrient_cells": {
                    k: v["metadata"]["column"] + str(f["provenance"]["excel_row"])
                    for k, v in f["nutrients"].items()
                },
            }
        )
    return {
        "recipe_id": recipe["id"],
        "recipe_version": recipe["version"],
        "meal": recipe["meal"],
        "name": recipe["name"],
        "scale": scale,
        "image": recipe["data"]["image"],
        "minutes": recipe["data"]["minutes"],
        "ingredients": parts,
        "nutrition": {k: None if k in unknown else float(v) for k, v in totals.items()},
        "sodium_table_upper_mg": float(sodium),
        "salt_equivalent_table_upper_g": float(sodium * Decimal("2.54") / 1000),
        "cost_jpy": float(cost),
        "allergens": sorted(allergens),
        "quality_flags": flags,
        "instructions": recipe["data"]["instructions"],
    }


def add_totals(meals):
    names = [v[0] for v in FIELDS.values()]
    result = {
        k: None
        if any(m["nutrition"][k] is None for m in meals)
        else float(sum(Decimal(str(m["nutrition"][k])) for m in meals))
        for k in names
    }
    result["sodium_table_upper_mg"] = float(
        sum(Decimal(str(m["sodium_table_upper_mg"])) for m in meals)
    )
    result["salt_equivalent_table_upper_g"] = (
        result["sodium_table_upper_mg"] * 2.54 / 1000
    )
    result["cost_jpy"] = float(sum(Decimal(str(m["cost_jpy"])) for m in meals))
    return result


def validate_plan(plan, profile):
    meals = plan["meals"]
    t = add_totals(meals)
    energy = profile.get("energy_kcal", 2000)
    if len(meals) != 3 or {m["meal"] for m in meals} != {
        "breakfast",
        "lunch",
        "dinner",
    }:
        return False
    if t["energy_kcal"] is None or not energy * 0.9 <= t["energy_kcal"] <= energy * 1.1:
        return False
    if t["sodium_table_upper_mg"] > profile.get("sodium_max_mg", 2000):
        return False
    minimum = plan.get("budget_min_jpy")
    if not valid_interval(minimum, plan["budget_jpy"]):
        return False
    if not (minimum or 0) <= t["cost_jpy"] <= plan["budget_jpy"]:
        return False
    if not satisfies_foods(meals, plan.get("food_requirements", [])):
        return False
    if any(set(m["allergens"]) & set(profile.get("allergens", [])) for m in meals):
        return False
    if any(
        p["code"] in profile.get("dislikes", [])
        for m in meals
        for p in m["ingredients"]
    ):
        return False
    if profile.get("diet") == "vegetarian" and any(
        animal_food(p["code"]) for m in meals for p in m["ingredients"]
    ):
        return False
    if any(m["minutes"] > profile.get("cooking_minutes", 45) for m in meals):
        return False
    return True


def plan_day(profile, budget=None, replace=None, budget_min=None, food_requirements=None):
    language = profile.get("language", "zh")
    food_requirements = food_requirements or []
    if not valid_interval(budget_min, budget):
        return explain("invalid_budget_range", language)
    unsupported = []
    if profile.get("age") is not None and profile["age"] < 18:
        unsupported.append("minor")
    unsupported.extend(sorted(set(profile.get("conditions", [])) - {"hypertension"}))
    if "other" in profile.get("allergens", []):
        unsupported.append("unspecified_allergen")
    if unsupported:
        return explain("unsupported_plan_profile", language,
                       details=labels(unsupported, language), unsupported_conditions=unsupported)
    needed = []
    if not profile.get("age"):
        needed.append("age")
    if profile.get("allergy_status", "unknown") == "unknown":
        needed.append("allergy_status")
    if not profile.get("health_confirmed"):
        needed.append("health_confirmed")
    if not profile.get("demo_consent"):
        needed.append("demo_consent")
    if needed:
        return explain("profile_incomplete", language, details=labels(needed, language), fields=needed)
    if profile["allergy_status"] == "present" and not profile.get("allergens"):
        return explain("allergen_unspecified", language, fields=["allergens"])
    with connect() as c:
        policy = c.execute(
            "SELECT * FROM app_income_policies WHERE id=%s",
            (profile.get("income_band"),),
        ).fetchone()
        ingredients, recipes = catalog(c)
    budget_source = (
        "request"
        if budget is not None
        else "profile"
        if profile.get("daily_budget")
        else "income_policy"
    )
    effective = (
        budget
        if budget is not None
        else profile.get("daily_budget") or (policy["daily_budget"] if policy else None)
    )
    if not effective:
        return explain("budget_missing", language, fields=["income_band", "daily_budget"])
    candidates = {k: [] for k in ["breakfast", "lunch", "dinner"]}
    for recipe in recipes:
        for scale in recipe["data"]["scales"]:
            try:
                m = calculate(recipe, ingredients, scale)
            except ValueError:
                continue
            if set(m["allergens"]) & set(profile.get("allergens", [])):
                continue
            if any(p["code"] in profile.get("dislikes", []) for p in m["ingredients"]):
                continue
            if profile.get("diet") == "vegetarian" and any(
                animal_food(p["code"]) for p in m["ingredients"]
            ):
                continue
            if m["minutes"] > profile.get("cooking_minutes", 45):
                continue
            if not satisfies_foods([m], [r for r in food_requirements if r["meal"] == m["meal"]]):
                continue
            if replace:
                if m["meal"] == replace["meal"]:
                    old = next(
                        x for x in replace["plan"]["meals"] if x["meal"] == m["meal"]
                    )
                    if old["recipe_id"] == m["recipe_id"]:
                        continue
                else:
                    old = next(
                        x for x in replace["plan"]["meals"] if x["meal"] == m["meal"]
                    )
                    if (m["recipe_id"], m["scale"]) != (old["recipe_id"], old["scale"]):
                        continue
            candidates[m["meal"]].append(m)
    unavailable_foods = [
        r for r in food_requirements
        if not satisfies_foods([m for group in candidates.values() for m in group], [r])
    ]
    if unavailable_foods:
        outcome = explain(
            "required_food_unavailable", language,
            details=describe_foods(unavailable_foods, language),
            budget_jpy=effective, budget_min_jpy=budget_min,
            food_requirements=food_requirements, unavailable_food_requirements=unavailable_foods,
            candidate_counts={k: len(v) for k, v in candidates.items()},
        )
        if budget_min is not None:
            outcome["message"] = text(language,
                f"已识别您的每日预算区间：¥{budget_min}–¥{effective}。",
                f"Your daily budget range is recognized: ¥{budget_min}–¥{effective}.",
                f"一日の予算範囲を確認しました：¥{budget_min}–¥{effective}。") + "\n\n" + outcome["message"]
        return outcome
    best, feasible = select_meals(
        candidates, profile["energy_kcal"], effective, profile["sodium_max_mg"], budget_min or 0,
        [r["food"] for r in food_requirements if r["meal"] == "any"],
    )
    if best is None:
        missing_meals = [k for k, v in candidates.items() if not v]
        return explain(
            "no_meal_candidates" if missing_meals else
            "no_feasible_budget_range" if budget_min is not None else "no_feasible_combination",
            language, details=labels(missing_meals, language) if missing_meals else f"¥{budget_min}–¥{effective}",
            budget_jpy=effective, budget_min_jpy=budget_min,
            food_requirements=food_requirements,
            candidate_counts={k: len(v) for k, v in candidates.items()},
        )
    output = {
        "status": "ready",
        "meals": best,
        "totals": add_totals(best),
        "budget_jpy": effective,
        "budget_min_jpy": budget_min,
        "food_requirements": food_requirements,
        "budget_source": budget_source,
        "income_policy": {"id": policy["id"], "version": policy["version"]}
        if policy
        else None,
        "rule_version": RULE_VERSION,
        "price_kind": "synthetic_demo",
        "nutrition_basis": "per_100g_edible_in_named_state",
        "profile_snapshot": profile,
        "note": NOTE[language],
        "feasible_candidates": feasible,
        "targets": {
            "energy_kcal": profile["energy_kcal"],
            "energy_tolerance": 0.1,
            "sodium_max_mg": profile["sodium_max_mg"],
            "source": "user_confirmed_demo_targets_not_clinical_prescription",
        },
        "calculation_note": "Tr sodium uses conservative display upper bound 0.5 mg/100g from MEXT PDF pp33–34; bounds reflect table precision, not real biological variation. No purchase-package estimate.",
        "evidence": [],
    }
    if not validate_plan(output, profile):
        raise ResultCheckError("plan_validation_failed")
    return output
