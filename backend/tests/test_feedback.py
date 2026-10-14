import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import psycopg
from pydantic import ValidationError

from backend.app.chat import Intent, answer_question
from backend.app.feedback import MESSAGES, explain, failure_result, ResultCheckError
from backend.app.planner import plan_day
from backend.app.worker import execute


class OutcomeTests(unittest.TestCase):
    def test_every_outcome_has_localized_reason_and_action(self):
        for code in MESSAGES:
            messages = []
            for lang in ("zh", "en", "ja"):
                r = explain(code, lang, details="fixture")
                self.assertTrue(r["reason"])
                self.assertTrue(r["next_steps"][0])
                self.assertEqual(r["reason_code"], code)
                if code == "outside_diet_scope":
                    self.assertEqual(r["message"], "无法回答与饮食无关的内容")
                else:
                    self.assertIn(r["reason"], r["message"])
                    self.assertIn(r["next_steps"][0], r["message"])
                    messages.append(r["message"])
            if code != "outside_diet_scope":
                self.assertEqual(len(set(messages)), 3)

    def test_actual_exception_categories_without_private_exception_details(self):
        secret = "private password prompt upstream response"
        errors = [
            (TimeoutError(secret), "processing_timeout"),
            (httpx.ReadTimeout(secret), "processing_timeout"),
            (httpx.ConnectError(secret), "model_service_unavailable"),
            (psycopg.OperationalError(secret), "data_service_unavailable"),
            (json.JSONDecodeError(secret, "", 0), "invalid_model_output"),
            (RuntimeError(secret), "processing_error"),
            (ResultCheckError("plan_validation_failed"), "plan_validation_failed"),
            (ResultCheckError("unrecognized_restriction"), "unrecognized_restriction"),
        ]
        try:
            Intent.model_validate({})
        except ValidationError as exc:
            errors.append((exc, "invalid_model_output"))
        for error, code in errors:
            result = failure_result(error, "en")
            self.assertEqual(result["reason_code"], code)
            self.assertNotIn(secret, json.dumps(result))

    def test_off_topic_response_is_the_user_confirmed_fixed_sentence(self):
        from backend.app.feedback import explain

        for language in ("zh", "en", "ja"):
            result = explain("outside_diet_scope", language)
            self.assertEqual(result["message"], "无法回答与饮食无关的内容")

    def test_profile_limit_names_actual_conditions_without_database(self):
        for lang, expected in [("zh", "肾脏"), ("en", "kidney"), ("ja", "腎臓")]:
            result = plan_day({
                "age": 17, "language": lang, "conditions": ["kidney"],
                "allergens": ["other"],
            })
            self.assertEqual(result["reason_code"], "unsupported_plan_profile")
            self.assertEqual(result["unsupported_conditions"], ["minor", "kidney", "unspecified_allergen"])
            self.assertIn(expected, result["reason"])
            self.assertNotIn("diabetes", result["reason"])

    def test_missing_fields_and_missing_allergen_are_distinct(self):
        result = plan_day({})
        self.assertEqual(result["reason_code"], "profile_incomplete")
        self.assertEqual(result["fields"], ["age", "allergy_status", "health_confirmed", "demo_consent"])
        result = plan_day({
            "age": 30, "allergy_status": "present", "health_confirmed": True,
            "demo_consent": True, "allergens": [],
        })
        self.assertEqual(result["reason_code"], "allergen_unspecified")


class AsyncOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_unclear_and_missing_replacement_context_are_explained(self):
        for intent, code in [
            (Intent(domain="unclear", intent="qa"), "unclear_question"),
            (Intent(domain="diet", intent="replace"), "replacement_context_missing"),
            (Intent(domain="off_topic", intent="qa"), "outside_diet_scope"),
        ]:
            with patch("backend.app.worker.catalog", return_value=({}, [])), patch(
                "backend.app.worker.classify", new=AsyncMock(return_value=intent)
            ):
                r = await execute({"kind": "chat", "input": {"profile": {"language": "en"}, "message": "test"}})
                self.assertEqual(r["reason_code"], code)
                self.assertTrue(r["next_steps"])

    async def test_evidence_failures_keep_distinct_explanations_and_do_not_leak_answer(self):
        source = {"chunk_id": 1, "content": "Test evidence.", "warning": ""}
        for sources, output, code in [
            ([], None, "no_usable_evidence"),
            ([source], '{"claims":[]}', "insufficient_evidence"),
            ([source], '{"claims":[{"text":"Eat 9 grams","citations":[1]}]}', "numeric_verification_required"),
            ([source], '{"claims":[{"text":"Unsafe fabricated advice","citations":[9]}]}', "invalid_citation"),
        ]:
            with patch("backend.app.chat.retrieve", new=AsyncMock(return_value=sources)), patch(
                "backend.app.chat.generate", new=AsyncMock(return_value=output)
            ):
                r = await answer_question(None, "Food?", "", "en")
                self.assertEqual(r["reason_code"], code)
                self.assertTrue(r["next_steps"])
                self.assertNotIn("Eat 9 grams", r["message"])
                self.assertNotIn("Unsafe fabricated advice", r["message"])
