"""Turn positive food requests into checkable meal constraints."""

import re
from .qa_policy import ALLERGENS

MEALS = {
    "breakfast": r"早餐|早饭|早上|朝食|朝ご[飯は]ん|breakfast",
    "lunch": r"午餐|午饭|中午|昼食|昼ご[飯は]ん|lunch",
    "dinner": r"晚餐|晚饭|晚上|夕食|晩ご[飯は]ん|dinner",
}
MEAL_LABELS = {
    "any": ("全天", "Across the day", "一日全体"),
    "breakfast": ("早餐", "Breakfast", "朝食"),
    "lunch": ("午餐", "Lunch", "昼食"),
    "dinner": ("晚餐", "Dinner", "夕食"),
}


def requested_foods(message, categories):
    """Categories come from positive intent, never from the allergy profile."""
    constraints = set()
    clauses = re.split(r"[，,。;；\n]", message)
    for category in set(categories):
        if category not in ALLERGENS or category == "other":
            continue
        scopes = set()
        for clause in clauses:
            match = re.search(ALLERGENS[category][3], clause, re.IGNORECASE)
            if not match:
                continue
            before = clause[:match.start()]
            if re.search(r"(?:不要|不吃|不含|不放|不用|不加|without|no|exclude)\s*$", before, re.IGNORECASE):
                continue
            scopes.update(meal for meal, pattern in MEALS.items() if re.search(pattern, clause, re.IGNORECASE))
        for meal in scopes or {"any"}:
            constraints.add((meal, category))
    return [{"meal": meal, "food": category} for meal, category in sorted(constraints)]


def satisfies_foods(meals, requirements):
    return all(
        any(
            (r["meal"] == "any" or r["meal"] == meal["meal"])
            and r["food"] in meal.get("allergens", [])
            for meal in meals
        )
        for r in requirements or []
    )


def describe_foods(requirements, language):
    index = {"zh": 0, "en": 1, "ja": 2}.get(language, 0)
    return "；".join(
        f"{MEAL_LABELS[r['meal']][index]}：{ALLERGENS[r['food']][index]}" for r in requirements
    )
