import unittest
from unittest.mock import patch, AsyncMock

from backend.app.chat import Intent
from backend.app.food_requirements import requested_foods, satisfies_foods
from backend.app.meal_selection import select_meals
from backend.app.worker import execute


class FoodRequirementsTests(unittest.TestCase):
    def test_foods_are_attached_to_the_requested_meal(self):
        for message in [
            "我想吃鱼，早上要含坚果",
            "I want fish, include nuts at breakfast",
            "魚を食べたい。朝食にはナッツを入れて",
        ]:
            self.assertEqual(requested_foods(message, ["fish", "nuts"]), [
                {"meal": "any", "food": "fish"}, {"meal": "breakfast", "food": "nuts"},
            ])
        self.assertEqual(requested_foods("早餐不要鱼，晚餐吃鱼", ["fish"]),
                         [{"meal": "dinner", "food": "fish"}])

    def test_food_requirements_are_verified_for_correct_meal(self):
        requirements = [{"meal": "breakfast", "food": "nuts"}, {"meal": "any", "food": "fish"}]
        self.assertFalse(satisfies_foods([
            {"meal": "breakfast", "allergens": []}, {"meal": "lunch", "allergens": ["nuts","fish"]},
        ], requirements))
        self.assertTrue(satisfies_foods([
            {"meal": "breakfast", "allergens": ["nuts"]}, {"meal": "lunch", "allergens": ["fish"]},
        ], requirements))

    def test_daily_fish_request_cannot_be_replaced_by_cheaper_non_fish_plan(self):
        groups = {}
        for meal in ("breakfast", "lunch", "dinner"):
            groups[meal] = [
                {"meal": meal, "recipe_id": meal + str(i), "scale": 1,
                 "nutrition": {"energy_kcal": 2000/3}, "cost_jpy": cost,
                 "sodium_table_upper_mg": 100, "ingredients": [], "allergens": allergens}
                for i, (cost, allergens) in enumerate([(100, []), (500, ["fish"])])
            ]
        meals, _ = select_meals(groups, 2000, 2000, 2000, required_foods=["fish"])
        self.assertTrue(any("fish" in m["allergens"] for m in meals))
        meals, _ = select_meals(groups, 2000, 2000, 2000, required_foods=["nuts"])
        self.assertIsNone(meals)


class FoodContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_budget_only_followup_retains_saved_food_requirements(self):
        requirements = [{"meal": "breakfast", "food": "nuts"}, {"meal": "any", "food": "fish"}]
        with patch("backend.app.worker.catalog", return_value=({}, [])), patch(
            "backend.app.worker.classify", new=AsyncMock(return_value=Intent(
                domain="diet", intent="plan", budget=2000, budget_min=1500,
            ))
        ), patch("backend.app.worker.plan_day", return_value={"status":"infeasible"}) as planner:
            await execute({"kind":"chat","input":{
                "message":"预算改成1500到2000日元", "profile":{},
                "previous_plan":{"budget_jpy":2000,"food_requirements":requirements},
            }})
            self.assertEqual(planner.call_args.kwargs["food_requirements"], requirements)
