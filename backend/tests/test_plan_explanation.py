import copy
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.app.plan_explanation import enrich_plan, validated_claims, quote_candidates

QUOTE = "たんぱく質は、他の食事性因子との組合せも考えて、バランスよく摂取すべきである。"
SOURCE = {
    "chunk_id": 7,
    "source_kind": "dietary_reference_intakes",
    "content": "前文。\n" + QUOTE + "\n後文。",
}
CLAIM = {
    "text": "蛋白质的摄入应考虑与其他饮食因素的搭配，并保持均衡。",
    "citation": 7,
    "quote": QUOTE,
    "meals": ["dinner"],
}


class CitationTests(unittest.TestCase):
    def test_candidates_are_exact_general_adult_sentences(self):
        source = {
            **SOURCE,
            "content": QUOTE
            + "高齢者の減塩指導には全身状態の管理に注意する。"
            + "食塩は1日6gを目標とする。",
        }
        candidates = quote_candidates([source])
        self.assertEqual([c["quote"] for c in candidates], [QUOTE])

    def validate(self, claim, source=SOURCE):
        return validated_claims(
            json.dumps({"claims": [claim]}), [source], [{"meal": "dinner"}]
        )

    def test_real_quote_and_source_id_required(self):
        self.assertEqual(self.validate(CLAIM), [CLAIM])
        with self.assertRaisesRegex(ValueError, "citation"):
            self.validate({**CLAIM, "citation": 999})
        with self.assertRaisesRegex(ValueError, "match"):
            self.validate({**CLAIM, "quote": "これは根拠に含まれない架空の文章です。"})

    def test_wrong_population_source_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "inapplicable"):
            self.validate(CLAIM, {**SOURCE, "source_kind": "guideline_chapter"})

    def test_fabricated_meal_and_generated_numeric_advice_rejected(self):
        with self.assertRaisesRegex(ValueError, "meal"):
            self.validate({**CLAIM, "meals": ["breakfast"]})
        with self.assertRaisesRegex(ValueError, "Quantitative"):
            self.validate({**CLAIM, "text": "每天钠不得超过1000mg。"})

    def test_pdf_line_wrapping_does_not_break_quote_check(self):
        source = {**SOURCE, "content": QUOTE.replace("組合せ", "組\n合せ")}
        self.assertEqual(self.validate(CLAIM, source), [CLAIM])


class EnrichmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_keeps_validated_menu_without_fake_sources(self):
        for error in [
            httpx.ConnectError("offline"),
            ValueError("invalid citation"),
            TimeoutError(),
        ]:
            plan = {
                "status": "ready",
                "meals": [{"meal": "dinner"}],
                "totals": {"cost_jpy": 999},
            }
            before = copy.deepcopy(plan)
            with patch(
                "backend.app.plan_explanation.explain_plan",
                new=AsyncMock(side_effect=error),
            ):
                await enrich_plan(None, plan)
            for key in before:
                self.assertEqual(plan[key], before[key])
            self.assertEqual(plan["knowledge_explanation"]["status"], "unavailable")
            self.assertEqual(plan["evidence"], [])

    async def test_valid_explanation_preserves_menu_and_citations(self):
        plan = {
            "status": "ready",
            "meals": [{"meal": "dinner"}],
            "totals": {"cost_jpy": 999},
        }
        before = copy.deepcopy(plan)
        response = {"status": "ready", "claims": [CLAIM], "evidence": [SOURCE]}
        with patch(
            "backend.app.plan_explanation.explain_plan",
            new=AsyncMock(return_value=response),
        ):
            await enrich_plan(None, plan)
        for key in before:
            self.assertEqual(plan[key], before[key])
        self.assertEqual(plan["knowledge_explanation"]["claims"], [CLAIM])
        self.assertEqual(plan["evidence"], [SOURCE])

    async def test_empty_retrieval_does_not_call_generator(self):
        from backend.app.plan_explanation import explain_plan, SOURCE_KINDS

        with patch(
            "backend.app.plan_explanation.retrieve", new=AsyncMock(return_value=[])
        ) as retrieve:
            with patch(
                "backend.app.plan_explanation.generate", new=AsyncMock()
            ) as generate:
                result = await explain_plan(
                    None,
                    {
                        "meals": [
                            {
                                "meal": "dinner",
                                "name": {"ja": "豆腐"},
                                "ingredients": [],
                            }
                        ],
                    },
                )
        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(retrieve.call_args.kwargs["source_kinds"], SOURCE_KINDS)
        generate.assert_not_awaited()
