import unittest
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError
from backend.app.budget import explicit_budget_range, resolve_budget, current_budget
from backend.app.chat import classify, Intent
from backend.app.feedback import ResultCheckError
from backend.app.schemas import PlanRequest
from backend.app.worker import execute


class BudgetTests(unittest.TestCase):
    def test_explicit_money_ranges_in_three_languages(self):
        for message in [
            "一天的花销在1500日元-2000日元之间", "预算1500-2000",
            "预算在 1500 到 2000", "between 1,500 and 2,000 yen",
            "JPY 1500–JPY 2000", "¥1500–¥2000", "1500〜2000円",
            "１５００～２０００円", "1500円から2000円",
        ]:
            self.assertEqual(explicit_budget_range(message), (1500, 2000), message)

    def test_ceiling_and_non_money_ranges_do_not_create_a_floor(self):
        for message in [
            "预算2000日元", "不超过2000日元", "1500-2000 kcal",
            "预算2000日元，能量1500-2000千卡", "年龄18-60岁",
            "早餐预算500-600日元，一天预算2000日元",
        ]:
            self.assertIsNone(explicit_budget_range(message), message)

    def test_invalid_or_ambiguous_bounds_require_clarification(self):
        for message in ["预算2000-1500日元", "预算50-2000日元", "预算1500-30000日元",
                        "预算1500.5-2000日元", "1500-2000日元或者2500-3000日元"]:
            with self.assertRaises(ResultCheckError, msg=message):
                explicit_budget_range(message)

    def test_api_rejects_incomplete_and_inverted_ranges(self):
        for bounds in [{"budget_min": 1500}, {"budget_min": 2000, "budget": 1500}]:
            with self.assertRaises(ValidationError):
                PlanRequest(idempotency_key="budget-check-0001", **bounds)
        self.assertEqual(PlanRequest(idempotency_key="budget-check-0001",
                                    budget_min=1500, budget=2000).budget_min, 1500)

    def test_previous_range_is_preserved_unless_new_budget_is_explicit(self):
        previous = {"budget_min_jpy": 1500, "budget_jpy": 2000}
        self.assertEqual(resolve_budget(None, None, previous), (2000, 1500))
        self.assertEqual(resolve_budget(1800, None, previous), (1800, None))
        self.assertEqual(resolve_budget(1900, 1600, previous), (1900, 1600))
        self.assertEqual(resolve_budget(None, None, {"budget_jpy": 2000}), (2000, None))

    def test_chinese_written_amounts_and_mixed_ceiling_plus_range(self):
        for message in [
            "请推荐一千五百日元至两千日元之间的三餐计划",
            "预算2000日元，请推荐一千五百日元至两千日元之间的三餐计划",
            "每天一千五百至两千日元", "千五百円から二千円",
            "between fifteen hundred and two thousand yen",
        ]:
            self.assertEqual(current_budget(message), (2000, 1500), message)
        for message in [
            "帮我安排一日三餐，我想吃鱼，早上要含坚果，我的一日预算是2000日元",
            "一天预算两千日元", "二千円以内", "two thousand yen daily",
        ]:
            self.assertEqual(current_budget(message), (2000, None), message)
        self.assertEqual(current_budget("一日预算2000日元，早餐500-600日元"), (2000, None))


class BudgetAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_reported_model_omission_cannot_override_current_budget(self):
        raw = '{"domain":"diet","intent":"plan","budget_min":1500,"requested_allergens":["fish","nuts"]}'
        prefix = "帮我安排一日三餐，我想吃鱼，早上要含坚果，我的一日预算是2000日元"
        for message, floor in [
            (prefix, None),
            (prefix + "，请推荐一千五百日元至两千日元之间的三餐计划", 1500),
        ]:
            with patch("backend.app.chat.generate", new=AsyncMock(return_value=raw)):
                intent = await classify(None, message, [{"role":"assistant","content":"请指定预算区间"}], {})
            self.assertEqual((intent.budget, intent.budget_min), (2000, floor))

    async def test_no_amount_does_not_copy_model_hallucinated_history_amount(self):
        with patch("backend.app.chat.generate", new=AsyncMock(return_value=Intent(
            domain="diet", intent="plan", budget_min=1500,
        ).model_dump_json())):
            intent = await classify(None, "换个方案", [], {})
        self.assertEqual((intent.budget, intent.budget_min), (None, None))

    async def test_literal_range_corrects_a_model_dropped_floor(self):
        with patch("backend.app.chat.generate", new=AsyncMock(return_value=Intent(
            domain="diet", intent="plan", budget=2000,
        ).model_dump_json())):
            intent = await classify(None, "一天的花销在1500日元-2000日元之间", [], {})
        self.assertEqual((intent.budget_min, intent.budget), (1500, 2000))

    async def test_worker_passes_lower_bound_into_planner(self):
        for upper, lower, expected_upper, expected_lower in [
            (2000, 1500, 2000, 1500), (None, None, 2000, 1500), (1800, None, 1800, None),
        ]:
            with patch("backend.app.worker.catalog", return_value=({}, [])), patch(
                "backend.app.worker.classify", new=AsyncMock(return_value=Intent(
                    domain="diet", intent="plan", budget=upper, budget_min=lower,
                ))
            ), patch("backend.app.worker.plan_day", return_value={"status": "infeasible"}) as planner:
                await execute({"kind": "chat", "input": {
                    "profile": {}, "message": "Plan meals",
                    "previous_plan": {"budget_jpy": 2000, "budget_min_jpy": 1500},
                }})
                self.assertEqual(planner.call_args.args[1], expected_upper)
                self.assertEqual(planner.call_args.kwargs["budget_min"], expected_lower)
