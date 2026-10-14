"""Compare optimized selection with an independent exhaustive reference."""

import random
import unittest
from itertools import product

from backend.app.meal_selection import animal_food, protein_food, select_meals


def exhaustive(candidates, target, budget, sodium, budget_min=0):
    feasible = 0
    choices = []
    for meals in product(*(candidates[k] for k in ("breakfast", "lunch", "dinner"))):
        if any(m["nutrition"]["energy_kcal"] is None for m in meals):
            continue
        energy = sum(m["nutrition"]["energy_kcal"] for m in meals)
        cost = sum(m["cost_jpy"] for m in meals)
        if not target * .9 <= energy <= target * 1.1:
            continue
        if not budget_min <= cost <= budget or sum(m["sodium_table_upper_mg"] for m in meals) > sodium:
            continue
        feasible += 1
        proteins = [{p["code"] for p in m["ingredients"] if protein_food(p["code"])} for m in meals]
        repeats = sum(len(proteins[i] & proteins[j]) for i in range(3) for j in range(i))
        score = abs(energy-target)/target*10 + cost/budget*.35 + repeats*.08
        choices.append(((score, tuple((m["recipe_id"], m["scale"]) for m in meals)), list(meals)))
    return (min(choices, key=lambda x: x[0])[1] if choices else None), feasible


class SelectionTests(unittest.TestCase):
    def test_matches_exhaustive_including_ties_and_constraints(self):
        rng = random.Random(178)
        for case in range(60):
            groups = {}
            for slot in ("breakfast", "lunch", "dinner"):
                groups[slot] = [
                    {
                        "recipe_id": f"{slot}-{n}", "scale": 1,
                        "nutrition": {"energy_kcal": rng.choice([None, 480.1, 600, 800, 960])},
                        "cost_jpy": rng.choice([150, 300.2, 500]),
                        "sodium_table_upper_mg": rng.choice([80, 350.1, 800]),
                        "ingredients": [{"code": c} for c in rng.sample(
                            ["11229", "11278", "10206", "12005", "04066", "04032", "01088"], 3)],
                    } for n in range(rng.randrange(0, 7))
                ]
            args = (groups, rng.choice([1600, 2000, 2400]), rng.choice([600, 1000, 2000]), rng.choice([500, 1500, 2000]))
            self.assertEqual(select_meals(*args), exhaustive(*args), f"case {case}")
            self.assertEqual(select_meals(*args, budget_min=900), exhaustive(*args, budget_min=900), f"range case {case}")

    def test_budget_bounds_are_inclusive_and_cheaper_menu_is_excluded(self):
        groups = {
            slot: [
                {"recipe_id": f"{slot}-{n}", "scale": 1,
                 "nutrition": {"energy_kcal": 2000 / 3}, "cost_jpy": cost,
                 "sodium_table_upper_mg": 50, "ingredients": []}
                for n, cost in enumerate([100, 500, 600, 900])
            ] for slot in ("breakfast", "lunch", "dinner")
        }
        for lower, upper in [(1500, 2000), (1500, 1500), (1800, 1800), (10000, 20000)]:
            self.assertEqual(select_meals(groups, 2000, upper, 2000, lower),
                             exhaustive(groups, 2000, upper, 2000, lower))
        selected, _ = select_meals(groups, 2000, 2000, 2000, 1500)
        self.assertEqual(sum(m["cost_jpy"] for m in selected), 1500)

    def test_decimal_sum_on_lower_and_upper_boundary(self):
        groups = {
            slot: [{"recipe_id": slot, "scale": 1,
                    "nutrition": {"energy_kcal": 2000 / 3}, "cost_jpy": cost,
                    "sodium_table_upper_mg": 50, "ingredients": []}]
            for slot, cost in zip(("breakfast", "lunch", "dinner"), (600.1, 399.2, 500.7))
        }
        selected, feasible = select_meals(groups, 2000, 1500, 2000, 1500)
        self.assertIsNotNone(selected)
        self.assertEqual(feasible, 1)

    def test_exact_energy_boundaries(self):
        groups = {
            slot: [
                {"recipe_id": f"{slot}-{n}", "scale": 1,
                 "nutrition": {"energy_kcal": e}, "cost_jpy": 100,
                 "sodium_table_upper_mg": 50, "ingredients": []}
                for n, e in enumerate([599.99999999, 600, 600.1, 733.3333333333, 800])
            ] for slot in ("breakfast", "lunch", "dinner")
        }
        self.assertEqual(select_meals(groups, 2000, 1000, 2000), exhaustive(groups, 2000, 1000, 2000))

    def test_new_animal_food_groups_excluded_from_vegetarian(self):
        for code in ["11229", "11278", "10206", "10156", "10136", "11288"]:
            self.assertTrue(animal_food(code))
        for code in ["12005", "13003", "04066", "04094", "06016"]:
            self.assertFalse(animal_food(code))
