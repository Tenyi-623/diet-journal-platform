"""Integration suite; explicitly requires isolated diet_restore_check database."""

import asyncio, os, unittest, uuid
from unittest.mock import patch, AsyncMock
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlsplit


@unittest.skipUnless(
    os.getenv("DIET_TEST_DATABASE_URL"), "isolated test DB not configured"
)
class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = os.environ["DIET_TEST_DATABASE_URL"]
        assert urlsplit(cls.url).path == "/diet_restore_check", (
            "Refusing to test against demo database"
        )
        os.environ["APP_DATABASE_URL"] = cls.url
        from backend.app.setup import migrate

        migrate(cls.url)
        from backend.app.seed import seed

        seed()
        from backend.main import app
        from fastapi.testclient import TestClient

        cls.app = app
        cls.Client = TestClient
        from backend.app.auth import HASHER

        cls.hashed = HASHER.hash("Test-only-password-2026")

    @classmethod
    def db(cls):
        return psycopg.connect(cls.url, row_factory=dict_row)

    def setUp(self):
        # Core queue tests never depend on the local model service.
        explanation_patch = patch(
            "backend.app.plan_explanation.explain_plan",
            new=AsyncMock(return_value={"status": "no_evidence", "claims": [], "evidence": []}),
        )
        explanation_patch.start()
        self.addCleanup(explanation_patch.stop)
        with self.db() as c:
            c.execute("TRUNCATE app_users CASCADE")
            c.execute("DELETE FROM app_login_attempts")
            for i in [1, 2]:
                c.execute(
                    "INSERT INTO app_users(id,login_id,password_hash) VALUES(%s,%s,%s)",
                    (i, f"diet{i:03}", self.hashed),
                )
        self.a = self.Client(self.app)
        self.b = self.Client(self.app)
        for client, n in [(self.a, 1), (self.b, 2)]:
            r = client.post(
                "/api/auth/login",
                json={"login_id": f"diet{n:03}", "password": "Test-only-password-2026"},
            )
            self.assertEqual(r.status_code, 200, r.text)
            client.headers["x-csrf-token"] = r.json()["csrf"]

    def tearDown(self):
        self.a.close()
        self.b.close()

    def profile(self, **overrides):
        from backend.app.schemas import Profile

        return Profile(
            age=40,
            allergy_status="none",
            health_confirmed=True,
            demo_consent=True,
            income_band="JPY_A1",
            **overrides,
        ).model_dump()

    def save(self, **overrides):
        r = self.a.patch("/api/profile", json=self.profile(**overrides))
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def plan(self, **overrides):
        from backend.app.planner import plan_day

        return plan_day(self.profile(**overrides))

    def job(self):
        self.save()
        r = self.a.post(
            "/api/recommendation-jobs", json={"idempotency_key": str(uuid.uuid4())}
        )
        self.assertEqual(r.status_code, 202, r.text)
        return r.json()["job_id"]

    def finish(self):
        from backend.app.worker import claim, execute, publish

        job = claim()
        result = asyncio.run(execute(job))
        publish(job, result)
        return job, result

    def test_auth_csrf_registration(self):
        with self.Client(self.app) as guest:
            for path in [
                "/api/profile",
                "/api/knowledge/documents",
                "/api/openapi.json",
                "/api/recipe-images/b1",
            ]:
                self.assertEqual(guest.get(path).status_code, 401, path)
            self.assertEqual(
                guest.get("/profile", follow_redirects=False).status_code, 303
            )
            self.assertEqual(guest.get("/register").status_code, 404)
            self.assertIn(
                guest.post("/api/auth/register", json={}).status_code, [404, 405]
            )
        self.assertEqual(self.a.post("/api/embed", json={}).status_code, 410)
        self.assertEqual(
            self.a.patch(
                "/api/profile", json=self.profile(), headers={"x-csrf-token": "bad"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.a.patch(
                "/api/profile",
                json=self.profile(),
                headers={"origin": "https://evil.example"},
            ).status_code,
            403,
        )
        self.assertEqual(self.a.post("/api/auth/logout", json={}).status_code, 200)
        self.assertEqual(self.a.get("/api/me").status_code, 401)

    def test_mobile_bearer_login_has_no_cookie_and_revokes_on_logout(self):
        with self.Client(self.app) as mobile:
            response = mobile.post("/api/auth/mobile/login", json={
                "login_id": "diet001", "password": "Test-only-password-2026",
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("set-cookie", response.headers)
            payload = response.json()
            self.assertEqual(payload["token_type"], "Bearer")
            self.assertEqual(payload["expires_in"], 43200)
            token = payload["access_token"]
            headers = {"authorization": f"Bearer {token}"}
            self.assertEqual(mobile.get("/api/me", headers=headers).status_code, 200)
            updated = mobile.patch(
                "/api/profile", headers=headers, json=self.profile(display_name="Mobile user")
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertEqual(updated.json()["profile"]["display_name"], "Mobile user")
            self.assertEqual(mobile.post("/api/auth/logout", headers=headers, json={}).status_code, 200)
            self.assertEqual(mobile.get("/api/me", headers=headers).status_code, 401)

    def test_mobile_login_rejects_unknown_account_without_creating_session(self):
        with self.Client(self.app) as mobile:
            response = mobile.post("/api/auth/mobile/login", json={
                "login_id": "missing", "password": "wrong-password",
            })
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("set-cookie", response.headers)

    def test_profile_isolation_and_version(self):
        self.save(display_name="Synthetic A")
        self.assertEqual(
            self.b.get("/api/profile").json()["profile"]["display_name"], ""
        )
        self.assertEqual(
            self.a.patch("/api/profile", json=self.profile()).status_code, 409
        )
        self.assertEqual(
            self.a.patch(
                "/api/profile", json={**self.profile(), "user_id": 2}
            ).status_code,
            422,
        )

    def test_lan_login_and_csrf_after_ip_change(self):
        # No fixed origin allowlist: both home and lab addresses must work.
        for base in ("http://192.168.11.39:8000", "http://10.20.30.40:8000"):
            with self.Client(self.app, base_url=base) as client:
                headers = {"origin": base, "sec-fetch-site": "same-origin"}
                response = client.post("/api/auth/login", headers=headers, json={
                    "login_id": "diet001", "password": "Test-only-password-2026",
                })
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn("diet_session", client.cookies)
                self.assertEqual(client.get("/api/me").status_code, 200)
                csrf = response.json()["csrf"]
                self.assertEqual(client.post("/api/auth/logout", json={},
                    headers={**headers, "x-csrf-token": "wrong"}).status_code, 403)
                self.assertEqual(client.post("/api/auth/logout", json={},
                    headers={"origin": "http://other.example", "x-csrf-token": csrf}
                ).status_code, 403)
                self.assertEqual(client.post("/api/auth/logout", json={},
                    headers={**headers, "sec-fetch-site": "cross-site", "x-csrf-token": csrf}
                ).status_code, 403)
                self.assertEqual(client.get("/api/me").status_code, 200)
                self.assertEqual(client.post("/api/auth/logout", json={},
                    headers={**headers, "x-csrf-token": csrf}).status_code, 200)
                self.assertEqual(client.get("/api/me").status_code, 401)

    def test_home_and_food_provenance(self):
        h = self.a.get("/api/home/today")
        self.assertEqual(h.status_code, 200, h.text)
        self.assertFalse(h.json()["personalized"])
        self.assertTrue(h.json()["examples"])
        self.save()
        h = self.a.get("/api/home/today").json()
        self.assertTrue(h["personalized"])
        self.assertEqual(len(h["meals"]), 3)
        for m in h["meals"]:
            self.assertEqual(self.a.get(m["image"]).status_code, 200)
        f = self.a.get("/api/foods/01088").json()
        self.assertEqual(len(f["values"]), 54)

    def grant(self, uid=1, role="admin"):
        with self.db() as c:
            c.execute("DELETE FROM app_user_roles WHERE user_id=%s", (uid,))
            c.execute("INSERT INTO app_user_roles VALUES(%s,%s)", (uid,role))

    def test_rbac_denies_regular_user_and_grants_only_scoped_permissions(self):
        for route in ["/api/admin/users", "/api/admin/recipes", "/api/admin/knowledge"]:
            self.assertEqual(self.a.get(route).status_code, 403)
        self.assertEqual(self.a.post("/api/admin/users",json={"login_id":"blocked"}).status_code,403)
        self.grant(role="recipe_editor")
        me=self.a.get("/api/me").json()
        self.assertEqual(me["permissions"],["recipes.manage"])
        self.assertEqual(self.a.get("/api/admin/recipes").status_code,200)
        self.assertEqual(self.a.get("/api/admin/users").status_code,403)
        self.assertEqual(self.a.get("/api/admin/knowledge").status_code,403)
        self.assertEqual(self.a.post("/api/admin/knowledge/uploads",json={"content_base64":"x"*25000}).status_code,403)

    def test_admin_user_creation_roles_and_session_revocation(self):
        self.grant()
        created=self.a.post("/api/admin/users",json={"login_id":"new_member","roles":["user"]})
        self.assertEqual(created.status_code,201,created.text)
        self.assertGreater(created.json()["user"]["id"],50)
        self.assertTrue(created.json()["initial_password"])
        self.assertEqual(self.a.post("/api/admin/users",json={"login_id":"new_member"}).status_code,409)
        r=self.a.patch("/api/admin/users/2",json={"enabled":True,"roles":["recipe_editor"]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.b.get("/api/me").status_code,401)
        self.assertEqual(self.a.patch("/api/admin/users/1",json={"enabled":False,"roles":["admin"]}).status_code,409)
        self.assertEqual(self.a.patch("/api/admin/users/1",json={"enabled":True,"roles":["user"]}).status_code,409)
        with self.db() as c:
            log=c.execute("SELECT detail FROM app_admin_audit WHERE action='user.create'").fetchone()
        self.assertNotIn("password",str(log))

    def test_user_manager_cannot_create_or_reset_administrator(self):
        self.grant(role="user_manager")
        self.grant(uid=2)
        self.assertEqual(self.a.post("/api/admin/users",json={"login_id":"evil_admin","roles":["admin"]}).status_code,403)
        self.assertEqual(self.a.post("/api/admin/users/2/reset-password",json={}).status_code,403)
        self.assertEqual(self.a.patch("/api/admin/users/2",json={"enabled":False,"roles":["user"]}).status_code,403)
        self.assertEqual(self.a.post("/api/admin/users",json={"login_id":"ordinary","roles":["user"]}).status_code,201)

    def test_admin_password_reset_revokes_old_sessions(self):
        self.grant()
        r=self.a.post("/api/admin/users/2/reset-password",json={})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.b.get("/api/me").status_code,401)
        self.assertEqual(self.b.post("/api/auth/login",json={"login_id":"diet002","password":"Test-only-password-2026"}).status_code,401)
        self.assertEqual(self.b.post("/api/auth/login",json={"login_id":"diet002","password":r.json()["initial_password"]}).status_code,200)
        self.assertEqual(self.a.post("/api/admin/users/1/reset-password",json={}).status_code,409)
        self.assertEqual(self.a.post("/api/admin/users",json={"login_id":"csrf_blocked"},headers={"x-csrf-token":"wrong"}).status_code,403)

    def test_recipe_edit_validation_and_disable(self):
        self.grant(role="recipe_editor")
        from backend.app.planner import catalog
        r=self.a.get("/api/admin/recipes").json()["recipes"][0]
        body={"name":r["name"],"meal":r["meal"],"ingredients":r["ingredients"],"minutes":r["data"]["minutes"],
              "instructions":r["data"]["instructions"],"enabled":False}
        created=self.a.post("/api/admin/recipes",json=body)
        self.assertEqual(created.status_code,201,created.text)
        row=created.json()
        self.assertNotIn(row["id"],[r["id"] for r in catalog()[1]])
        body.update(enabled=True,expected_version=row["version"])
        saved=self.a.patch("/api/admin/recipes/"+row["id"],json=body)
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertIn(row["id"],[r["id"] for r in catalog()[1]])
        self.assertEqual(self.a.patch("/api/admin/recipes/"+row["id"],json=body).status_code,409)
        body["ingredients"]={"99999":100}
        self.assertEqual(self.a.post("/api/admin/recipes",json=body).status_code,422)
        with self.db() as c:
            c.execute("DELETE FROM app_recipes WHERE id=%s",(row["id"],))

    def test_images_are_validated_immutable_and_invalidate_cache(self):
        import base64,io,tempfile
        from pathlib import Path
        from PIL import Image
        self.grant(role="recipe_editor")
        row=self.a.get("/api/admin/recipes").json()["recipes"][0]
        original=row.copy()
        with tempfile.TemporaryDirectory() as folder,patch("backend.app.admin.MEDIA",Path(folder)):
            def payload(color,version):
                out=io.BytesIO()
                Image.new("RGB",(8,8),color).save(out,format="PNG")
                return {"filename":"picture.png","content_base64":base64.b64encode(out.getvalue()).decode(),"expected_version":version}
            r=self.a.post(f"/api/admin/recipes/{row['id']}/image",json=payload("red",row["version"]))
            self.assertEqual(r.status_code,200,r.text)
            old_url=r.json()["data"]["image"]
            self.assertEqual(self.a.get(old_url).headers["content-type"],"image/webp")
            changed=self.a.post(f"/api/admin/recipes/{row['id']}/image",json=payload("blue",r.json()["version"]))
            self.assertEqual(changed.status_code,200,changed.text)
            self.assertNotEqual(old_url,changed.json()["data"]["image"])
            self.assertEqual(self.a.get(old_url).status_code,200)
            bad={**payload("red",changed.json()["version"]),"content_base64":base64.b64encode(b"<svg><script>alert(1)</script></svg>").decode()}
            self.assertEqual(self.a.post(f"/api/admin/recipes/{row['id']}/image",json=bad).status_code,422)
            self.assertEqual(self.b.post(f"/api/admin/recipes/{row['id']}/image",json=bad).status_code,403)
        from psycopg.types.json import Jsonb
        with self.db() as c:
            c.execute("UPDATE app_recipes SET data=%s,version=%s WHERE id=%s",(Jsonb(original["data"]),original["version"],row["id"]))

    def test_knowledge_disable_excludes_retrieval_and_quarantine_cannot_publish(self):
        self.grant(role="knowledge_editor")
        docs=self.a.get("/api/admin/knowledge").json()["documents"]
        doc=next(d for d in docs if d["status"]=="ready")
        body={k:doc[k] for k in ["title","publisher","edition","source_kind","warning"]}
        from backend.knowledge import search_database
        with self.db() as c:
            fingerprint=c.execute("SELECT c.fingerprint FROM kb_collections c JOIN kb_documents d ON c.id=d.collection_id WHERE d.id=%s",(doc["id"],)).fetchone()["fingerprint"]
        try:
            self.assertEqual(self.a.patch(f"/api/admin/knowledge/{doc['id']}",json={**body,"enabled":False}).status_code,200)
            self.assertEqual(search_database(fingerprint,[1.0]*2560,5,document_id=doc["id"]),[])
        finally:
            self.a.patch(f"/api/admin/knowledge/{doc['id']}",json={**body,"enabled":doc["enabled"]})
        quarantined=next(d for d in docs if d["status"]=="quarantined")
        body={k:quarantined[k] for k in ["title","publisher","edition","source_kind","warning"]}
        self.assertEqual(self.a.patch(f"/api/admin/knowledge/{quarantined['id']}",json={**body,"enabled":True}).status_code,409)
        self.assertEqual(self.a.get(f"/api/admin/knowledge/{doc['id']}/pages?page=1").status_code,200)

    def test_pdf_upload_queue_and_real_import_with_stubbed_embeddings(self):
        import base64,tempfile
        from pathlib import Path
        import pymupdf
        from backend.app.kb_import import claim_upload,process_upload
        from backend.config import settings
        self.grant(role="knowledge_editor")
        pdf=pymupdf.open()
        page=pdf.new_page()
        page.insert_text((50,70),"Administrative ingestion test. This paragraph is a synthetic test fixture.\\n"*5)
        raw=pdf.tobytes();pdf.close()
        body={"filename":"test.pdf","content_base64":base64.b64encode(raw).decode(),"title":"Test fixture","publisher":"Test suite","edition":"test",
              "source_kind":"reference","warning":"Synthetic test only"}
        with tempfile.TemporaryDirectory() as folder,patch("backend.app.admin.PDFS",Path(folder)):
            r=self.a.post("/api/admin/knowledge/uploads",json=body)
            self.assertEqual(r.status_code,202,r.text)
            self.assertEqual(self.a.post("/api/admin/knowledge/uploads",json=body).status_code,409)
            upload=claim_upload()
            with self.db() as c:
                collection=c.execute("SELECT model_digest,fingerprint FROM kb_collections WHERE model=%s LIMIT 1",(settings.embedding_model,)).fetchone()
            async def embed(client,**kwargs):
                return [[1.0]*2560 for _ in kwargs["texts"]]
            with patch("backend.ingest.model_identity",new=AsyncMock(return_value=(collection["model_digest"],collection["fingerprint"]))),patch("backend.ingest.embed_texts",side_effect=embed):
                asyncio.run(process_upload(upload))
            with self.db() as c:
                row=c.execute("SELECT status,document_id,error FROM app_kb_uploads WHERE id=%s",(upload["id"],)).fetchone()
                self.assertEqual(row["status"],"ready",row["error"])
                doc=c.execute("SELECT enabled,status FROM kb_documents WHERE id=%s",(row["document_id"],)).fetchone()
                self.assertFalse(doc["enabled"])
                self.assertEqual(doc["status"],"ready")
                c.execute("DELETE FROM app_kb_uploads WHERE id=%s",(upload["id"],))
                c.execute("DELETE FROM kb_documents WHERE id=%s",(row["document_id"],))

    def test_menu_evidence_persisted_in_job_and_recommendation(self):
        self.job()
        evidence = {"status": "ready", "claims": [{"text": "test", "citation": 7}],
                    "evidence": [{"chunk_id": 7, "content": "test snapshot"}]}
        with patch("backend.app.plan_explanation.explain_plan", new=AsyncMock(return_value=evidence)):
            job, result = self.finish()
        with self.db() as c:
            stored_job = c.execute("SELECT result FROM app_jobs WHERE id=%s", (job["id"],)).fetchone()["result"]
            stored_plan = c.execute("SELECT data FROM app_recommendations WHERE id=%s", (result["recommendation_id"],)).fetchone()["data"]
        self.assertEqual(stored_job["evidence"], result["evidence"])
        self.assertEqual(stored_plan["knowledge_explanation"], result["knowledge_explanation"])
        self.assertEqual(len(stored_plan["meals"]), 3)

    def test_retrieval_filters_sources_before_ranking(self):
        from backend.knowledge import search_database
        with self.db() as c:
            fingerprint = c.execute(
                "SELECT c.fingerprint FROM kb_collections c JOIN kb_documents d ON c.id=d.collection_id WHERE d.source_kind='guideline_commentary' AND d.status='ready' LIMIT 1"
            ).fetchone()["fingerprint"]
        rows = search_database(fingerprint, [1.0] * 2560, 3, source_kinds=["guideline_commentary"])
        self.assertTrue(rows)
        self.assertTrue(all(r["source_kind"] == "guideline_commentary" for r in rows))
        self.assertEqual(search_database(fingerprint, [1.0] * 2560, 3, source_kinds=[]), [])

    def test_income_budget_and_target_independence(self):
        from backend.app.planner import plan_day, validate_plan

        for i, budget in enumerate([900, 1100, 1300, 1500, 1700, 1900], 1):
            p = self.profile()
            p["income_band"] = f"JPY_A{i}"
            r = plan_day(p)
            self.assertEqual(r["status"], "ready")
            self.assertEqual(r["budget_jpy"], budget)
            self.assertTrue(validate_plan(r, p))
            self.assertEqual(r["targets"]["energy_kcal"], 2000)
        p = self.profile(daily_budget=1200)
        r = plan_day(p, 1100)
        self.assertEqual(r["budget_source"], "request")
        self.assertEqual(r["budget_jpy"], 1100)
        self.assertEqual(plan_day(p, 100)["status"], "infeasible")

    def test_allergies_restrictions_and_unsupported(self):
        from backend.app.planner import plan_day, validate_plan

        for allergens in [
            ["milk"],
            ["soy"],
            ["egg", "fish"],
            ["milk", "soy", "egg", "fish", "wheat"],
        ]:
            p = self.profile()
            p.update(allergy_status="present", allergens=allergens, daily_budget=2000)
            r = plan_day(p)
            self.assertIn(r["status"], ["ready", "infeasible"])
            if r["status"] == "ready":
                self.assertTrue(validate_plan(r, p))
                self.assertFalse(
                    set(allergens) & set(a for m in r["meals"] for a in m["allergens"])
                )
        for key, value in [
            ("age", 17),
            ("conditions", ["kidney"]),
            ("conditions", ["pregnancy"]),
            ("allergens", ["other"]),
        ]:
            p = self.profile()
            p[key] = value
            self.assertEqual(plan_day(p)["status"], "unsupported")
        p = self.profile()
        p["allergy_status"] = "unknown"
        self.assertEqual(plan_day(p)["status"], "needs_clarification")
        p = self.profile(diet="vegetarian")
        r = plan_day(p)
        self.assertEqual(r["status"], "ready")
        self.assertTrue(validate_plan(r, p))

    def test_trace_and_hand_calculation(self):
        from backend.app.planner import calculate, catalog, sodium_upper
        from decimal import Decimal

        ingredients, rows = catalog()
        r = next(x for x in rows if x["id"] == "b1")
        out = calculate(r, ingredients)
        manual = sum(
            Decimal(str(g))
            / 100
            * ingredients[code]["nutrients"]["ENERC_KCAL"]["value"]
            for code, g in r["ingredients"].items()
        )
        self.assertAlmostEqual(out["nutrition"]["energy_kcal"], float(manual))
        self.assertEqual(sodium_upper({"status": "trace"}), Decimal(".5"))
        with self.assertRaises(ValueError):
            sodium_upper({"status": "not_reported", "value": None})
        self.assertTrue(
            any(calculate(x, ingredients)["nutrition"]["fiber_g"] is None for x in rows)
        )

    def test_extended_catalog_calculations_images_and_preserved_edits(self):
        from decimal import Decimal
        from backend.app.planner import calculate, catalog
        from backend.app.recipe_catalog_install import install

        ingredients, rows = catalog()
        self.assertEqual(len(rows), 184)
        self.assertEqual(len(ingredients), 49)
        extended = [r for r in rows if r["id"].startswith("r178-")]
        self.assertEqual(len(extended), 158)
        for row in extended:
            for scale in row["data"]["scales"]:
                meal = calculate(row, ingredients, scale)
                manual = sum(
                    Decimal(str(grams)) * Decimal(str(scale)) / 100
                    * ingredients[code]["nutrients"]["ENERC_KCAL"]["value"]
                    for code, grams in row["ingredients"].items()
                )
                self.assertAlmostEqual(meal["nutrition"]["energy_kcal"], float(manual))
                self.assertGreaterEqual(meal["sodium_table_upper_mg"], 0)
            response = self.a.get(row["data"]["image"])
            self.assertEqual(response.status_code, 200)
            self.assertIn("image/svg+xml", response.headers["content-type"])
        for lang, caption in [("zh", "食材示意图"), ("en", "Ingredient illustration"), ("ja", "食材イメージ")]:
            response = self.a.get(f"/api/recipe-images/r178-b001?lang={lang}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(caption, response.text)
        self.assertEqual(self.a.get("/api/recipe-images/r178-b001?lang=../../").status_code, 422)
        # Existing neutral illustrations still work for every language.
        self.assertEqual(self.a.get("/api/recipe-images/b1?lang=ja").status_code, 200)
        with self.db() as c:
            c.execute(
                """UPDATE app_recipes SET enabled=false,
                data=jsonb_set(data,'{image}','"/api/recipe-media/custom.webp"')
                WHERE id='r178-b001'"""
            )
            result = install(c)
            self.assertEqual(result, {"added_ingredients": 0, "added_recipes": 0})
            changed = c.execute("SELECT * FROM app_recipes WHERE id='r178-b001'").fetchone()
            self.assertFalse(changed["enabled"])
            self.assertEqual(changed["data"]["image"], "/api/recipe-media/custom.webp")
            c.rollback()

    def test_extended_vegetarian_validation_catches_new_meat_and_fish(self):
        from copy import deepcopy
        from backend.app.planner import plan_day, validate_plan
        from backend.app.meal_selection import animal_food

        profile = self.profile(diet="vegetarian", daily_budget=2000)
        plan = plan_day(profile)
        self.assertEqual(plan["status"], "ready")
        self.assertTrue(validate_plan(plan, profile))
        self.assertFalse(any(animal_food(p["code"]) for m in plan["meals"] for p in m["ingredients"]))
        for code in ["11229", "11278", "10156", "10206"]:
            altered = deepcopy(plan)
            altered["meals"][0]["ingredients"][0]["code"] = code
            self.assertFalse(validate_plan(altered, profile))
        # Exercise home examples with only newly added dishes, so old recipe
        # ordering cannot hide a regression in their separate filtering path.
        from backend.app.planner import catalog
        ingredients, rows = catalog()
        examples = [r for r in rows if r["id"].startswith("r178-")]
        example_profile = self.profile(diet="vegetarian")
        example_profile["allergy_status"] = "unknown"
        self.assertEqual(self.a.patch("/api/profile", json=example_profile).status_code, 200)
        with patch("backend.app.api.catalog", return_value=(ingredients, examples)):
            home = self.a.get("/api/home/today").json()
        self.assertTrue(home["examples"])
        self.assertFalse(any(animal_food(p["code"]) for m in home["examples"] for p in m["ingredients"]))

    def test_job_idempotency_and_isolation(self):
        jid = self.job()
        self.assertEqual(self.b.get("/api/recommendation-jobs/" + jid).status_code, 404)
        body = {"idempotency_key": "idem-key-0001", "budget": 1000}
        x = self.a.post("/api/recommendation-jobs", json=body).json()
        y = self.a.post("/api/recommendation-jobs", json=body).json()
        self.assertEqual(x["job_id"], y["job_id"])
        self.assertEqual(
            self.a.post(
                "/api/recommendation-jobs", json={**body, "budget": 1200}
            ).status_code,
            409,
        )
        self.a.post(
            "/api/recommendation-jobs", json={"idempotency_key": "idem-key-0002"}
        )
        self.assertEqual(
            self.a.post(
                "/api/recommendation-jobs", json={"idempotency_key": "idem-key-0003"}
            ).status_code,
            429,
        )

    def test_history_substitution_and_snapshot(self):
        self.job()
        job, result = self.finish()
        self.assertEqual(result["status"], "ready")
        rid = result["recommendation_id"]
        self.assertEqual(self.b.get("/api/recommendations/" + rid).status_code, 404)
        self.assertEqual(
            self.b.post(
                "/api/recommendations/" + rid + "/substitutions",
                json={"meal": "lunch", "idempotency_key": "replace-0001"},
            ).status_code,
            404,
        )
        r = self.a.post(
            "/api/recommendations/" + rid + "/substitutions",
            json={"meal": "lunch", "idempotency_key": "replace-0001"},
        )
        self.assertEqual(r.status_code, 202)
        _, new = self.finish()
        self.assertEqual(new["status"], "ready")
        for old, m in zip(result["meals"], new["meals"]):
            if old["meal"] == "lunch":
                self.assertNotEqual(old["recipe_id"], m["recipe_id"])
            else:
                self.assertEqual(old, m)
        p = self.profile()
        p.update(expected_version=1, income_band="JPY_A6")
        self.a.patch("/api/profile", json=p)
        self.assertEqual(
            self.a.get("/api/recommendations/" + rid).json()["data"]["budget_jpy"], 900
        )

    def test_budget_range_selection_independent_validation_and_infeasible_case(self):
        from backend.app.planner import plan_day, validate_plan
        p = self.profile()
        p["allergy_status"], p["allergens"] = "present", ["egg"]
        cheap = plan_day(p, 2000)
        self.assertLess(cheap["totals"]["cost_jpy"], 1500)
        bounded = plan_day(p, 2000, budget_min=1500)
        self.assertEqual(bounded["status"], "ready")
        self.assertTrue(1500 <= bounded["totals"]["cost_jpy"] <= 2000)
        self.assertTrue(validate_plan(bounded, p))
        self.assertFalse(validate_plan({**cheap, "budget_min_jpy": 1500}, p))
        self.assertNotEqual([m["recipe_id"] for m in cheap["meals"]],
                            [m["recipe_id"] for m in bounded["meals"]])
        impossible = plan_day(p, 20000, budget_min=19000)
        self.assertEqual(impossible["reason_code"], "no_feasible_budget_range")
        self.assertNotIn("meals", impossible)
        self.assertIn("19000", impossible["message"])

    def test_requested_foods_are_enforced_and_missing_breakfast_is_explained(self):
        from backend.app.planner import plan_day, validate_plan, catalog, calculate
        p = self.profile()
        fish = [{"meal": "any", "food": "fish"}]
        result = plan_day(p, 2000, budget_min=1500, food_requirements=fish)
        self.assertEqual(result["status"], "ready")
        self.assertTrue(any("fish" in m["allergens"] for m in result["meals"]))
        self.assertTrue(validate_plan(result, p))
        ingredients, recipes = catalog()
        without_nuts = [r for r in recipes if "nuts" not in calculate(r, ingredients)["allergens"]]
        required = [*fish, {"meal": "breakfast", "food": "nuts"}]
        with patch("backend.app.planner.catalog", return_value=(ingredients, without_nuts)):
            missing = plan_day(p, 2000, budget_min=1500, food_requirements=required)
        self.assertEqual(missing["reason_code"], "required_food_unavailable")
        self.assertEqual(missing["budget_min_jpy"], 1500)
        self.assertEqual(missing["unavailable_food_requirements"], [{"meal":"breakfast","food":"nuts"}])
        self.assertIn("1500", missing["message"])
        self.assertIn("早餐：坚果", missing["message"])
        self.assertNotIn("区间无效", missing["message"])
        self.assertNotIn("meals", missing)

    def test_nut_breakfasts_meet_original_request_and_keep_allergy_constraints(self):
        from backend.app.planner import plan_day, validate_plan, catalog, calculate
        from decimal import Decimal
        p = self.profile()
        p.update(allergy_status="present", allergens=["egg"])
        required = [{"meal": "any", "food": "fish"}, {"meal": "breakfast", "food": "nuts"}]
        result = plan_day(p, 2000, budget_min=1500, food_requirements=required)
        self.assertEqual(result["status"], "ready")
        self.assertTrue(1500 <= result["totals"]["cost_jpy"] <= 2000)
        self.assertTrue(validate_plan(result, p))
        breakfast = next(m for m in result["meals"] if m["meal"] == "breakfast")
        self.assertIn("nuts", breakfast["allergens"])
        self.assertTrue(any("fish" in m["allergens"] for m in result["meals"]))
        self.assertTrue(all("egg" not in m["allergens"] for m in result["meals"]))
        ingredients, rows = catalog()
        for row in [r for r in rows if r["id"].startswith("nuts-")]:
            for scale in row["data"]["scales"]:
                m = calculate(row, ingredients, scale)
                self.assertIn("nuts", m["allergens"])
                manual = sum(Decimal(str(g)) * Decimal(str(scale)) / 100 *
                             ingredients[code]["nutrients"]["ENERC_KCAL"]["value"]
                             for code, g in row["ingredients"].items())
                self.assertAlmostEqual(m["nutrition"]["energy_kcal"], float(manual))
                for part in m["ingredients"]:
                    self.assertTrue(part["excel_sheet"])
                    self.assertGreater(part["excel_row"], 0)
        self.assertEqual(ingredients["05040"]["nutrients"]["NA"]["status"], "trace")
        p["allergens"] = ["nuts"]
        safe = plan_day(p, 2000)
        self.assertEqual(safe["status"], "ready")
        self.assertTrue(all("nuts" not in m["allergens"] for m in safe["meals"]))
        unavailable = plan_day(p, 2000, budget_min=1500, food_requirements=required)
        self.assertEqual(unavailable["status"], "infeasible")
        self.assertNotIn("meals", unavailable)

    def test_nut_import_is_idempotent_preserves_edits_and_images_are_served(self):
        from backend.app.nut_catalog_install import install
        for lang in ("zh", "en", "ja"):
            response = self.a.get("/api/recipe-images/nuts-b001", params={"lang": lang})
            self.assertEqual(response.status_code, 200)
            self.assertIn("image/svg+xml", response.headers["content-type"])
        self.assertEqual(self.a.get("/api/recipe-images/nuts-b999").status_code, 404)
        with self.db() as c:
            c.execute("""UPDATE app_recipes SET enabled=false,
                data=jsonb_set(data,'{image}','"/api/recipe-media/custom.webp"')
                WHERE id='nuts-b001'""")
            self.assertEqual(install(c), {"added_ingredients": 0, "added_recipes": 0})
            row = c.execute("SELECT enabled,data FROM app_recipes WHERE id='nuts-b001'").fetchone()
            self.assertFalse(row["enabled"])
            self.assertEqual(row["data"]["image"], "/api/recipe-media/custom.webp")
            c.rollback()

    def test_budget_range_api_persists_and_substitution_preserves_or_replaces_bounds(self):
        self.save()
        response = self.a.post("/api/recommendation-jobs", json={
            "budget": 2000, "budget_min": 1500, "idempotency_key": "budget-range-0001",
        })
        self.assertEqual(response.status_code, 202, response.text)
        _, plan = self.finish()
        self.assertEqual(plan["status"], "ready")
        rid = plan["recommendation_id"]
        saved = self.a.get("/api/recommendations/" + rid).json()["data"]
        self.assertEqual(saved["budget_min_jpy"], 1500)
        changed = self.a.post("/api/recommendation-jobs", json={
            "budget": 2000, "budget_min": 1600, "idempotency_key": "budget-range-0001",
        })
        self.assertEqual(changed.status_code, 409)
        for index, body, expected in [
            (1, {}, 1500), (2, {"budget": 1800}, None),
            (3, {"budget": 2000, "budget_min": 1600}, 1600),
        ]:
            response = self.a.post("/api/recommendations/" + rid + "/substitutions", json={
                "meal": "lunch", "idempotency_key": f"range-substitute-{index}", **body,
            })
            self.assertEqual(response.status_code, 202, response.text)
            with self.db() as c:
                job = c.execute("SELECT input FROM app_jobs WHERE id=%s",
                                (response.json()["job_id"],)).fetchone()
            self.assertEqual(job["input"]["budget_min"], expected)
            _, replacement = self.finish()
            self.assertEqual(replacement["budget_min_jpy"], expected)
            if replacement["status"] == "ready":
                self.assertGreaterEqual(replacement["totals"]["cost_jpy"], expected or 0)
                self.assertLessEqual(replacement["totals"]["cost_jpy"], body.get("budget", 2000))

    def test_cancel_publish_and_expired_lease(self):
        from backend.app.worker import claim, publish

        jid = self.job()
        job = claim()
        self.assertEqual(
            self.a.post(
                "/api/recommendation-jobs/" + jid + "/cancel", json={}
            ).status_code,
            200,
        )
        publish(job, {"status": "ready", "message": "late"})
        self.assertEqual(
            self.a.get("/api/recommendation-jobs/" + jid).json()["status"], "cancelled"
        )
        with self.db() as c:
            c.execute(
                "UPDATE app_jobs SET status='running',lease_until=now()-interval '1 second',attempts=1 WHERE id=%s",
                (jid,),
            )
        self.assertIsNotNone(claim())
        with self.db() as c:
            c.execute(
                "UPDATE app_jobs SET lease_until=now()-interval '1 second' WHERE id=%s",
                (jid,),
            )
        self.assertIsNone(claim())
        self.assertEqual(
            self.a.get("/api/recommendation-jobs/" + jid).json()["status"], "failed"
        )

    def test_chat_scope_explanation_and_isolation(self):
        from backend.app.chat import Intent
        from backend.app.feedback import explain

        r = self.a.post(
            "/api/diet-chat/messages",
            json={"message": "电影推荐", "idempotency_key": "chat-idem-0001"},
        )
        self.assertEqual(r.status_code, 202, r.text)
        sid = r.json()["session_id"]
        self.assertEqual(self.b.get("/api/diet-chat/sessions/" + sid).status_code, 404)
        with patch(
            "backend.app.worker.classify",
            new=AsyncMock(return_value=Intent(domain="off_topic", intent="qa")),
        ):
            job, result = self.finish()
        self.assertEqual(result, explain("outside_diet_scope", "zh"))
        self.assertEqual(
            self.a.get("/api/diet-chat/sessions/" + sid).json()["messages"][-1][
                "content"
            ],
            result["message"],
        )

    def test_expired_chat_explanation_is_persisted_once(self):
        from backend.app.worker import claim
        response = self.a.post("/api/diet-chat/messages", json={
            "message": "Food question", "language": "en", "idempotency_key": "expired-chat-0001",
        }).json()
        with self.db() as c:
            c.execute(
                "UPDATE app_jobs SET status='running',attempts=2,lease_until=now()-interval '1 second' WHERE id=%s",
                (response["job_id"],),
            )
        self.assertIsNone(claim())
        self.assertIsNone(claim())
        job = self.a.get("/api/recommendation-jobs/" + response["job_id"]).json()
        messages = self.a.get("/api/diet-chat/sessions/" + response["session_id"]).json()["messages"]
        assistants = [m for m in messages if m["role"] == "assistant"]
        self.assertEqual(len(assistants), 1)
        self.assertEqual(job["result"]["reason_code"], "processing_interrupted")
        self.assertEqual(assistants[0]["content"], job["result"]["message"])
        self.assertIn("interrupted", assistants[0]["content"])

    def test_plan_no_candidates_and_no_combination_have_distinct_reasons(self):
        from backend.app.planner import plan_day
        p = self.profile()
        r = plan_day(p, 100)
        self.assertEqual(r["reason_code"], "no_feasible_combination")
        self.assertTrue(all(r["candidate_counts"].values()))
        p["cooking_minutes"] = 0  # Deliberately eliminate every catalog candidate.
        r = plan_day(p)
        self.assertEqual(r["reason_code"], "no_meal_candidates")
        self.assertFalse(any(r["candidate_counts"].values()))
        self.assertIn("早餐", r["reason"])
        p = self.profile()
        p["income_band"] = None
        self.assertEqual(plan_day(p)["reason_code"], "budget_missing")

    def test_password_revokes_existing_sessions(self):
        self.assertEqual(
            self.a.post(
                "/api/auth/password",
                json={
                    "current_password": "Test-only-password-2026",
                    "new_password": "Another-test-password",
                },
            ).status_code,
            200,
        )
        self.assertEqual(self.a.get("/api/me").status_code, 401)

    def test_body_limits(self):
        self.assertEqual(
            self.a.post(
                "/api/diet-chat/messages", json={"message": "x" * 25000}
            ).status_code,
            413,
        )
        self.assertEqual(
            self.a.post("/api/diet-chat/messages", content="x").status_code, 415
        )

    def test_login_throttle(self):
        with self.Client(self.app) as client:
            for i in range(8):
                self.assertEqual(
                    client.post(
                        "/api/auth/login",
                        json={"login_id": "missing", "password": "bad"},
                    ).status_code,
                    401,
                )
            self.assertEqual(
                client.post(
                    "/api/auth/login", json={"login_id": "missing", "password": "bad"}
                ).status_code,
                429,
            )

    def test_model_outputs_fail_closed(self):
        from backend.app.chat import classify, answer_question
        import httpx

        async def run():
            async with httpx.AsyncClient() as client:
                with patch(
                    "backend.app.chat.generate", new=AsyncMock(return_value="not json")
                ):
                    with self.assertRaises(Exception):
                        await classify(client, "diet", [], {})
                source = {
                    "chunk_id": 1,
                    "document_id": 1,
                    "title": "Test",
                    "pdf_page": 3,
                    "printed_page": "2",
                    "content": "Salt context",
                    "warning": "demo",
                    "citation": "Test p3",
                }
                with patch(
                    "backend.app.chat.retrieve", new=AsyncMock(return_value=[source])
                ):
                    with patch(
                        "backend.app.chat.generate",
                        new=AsyncMock(
                            return_value='{"claims":[{"text":"Unsupported citation","citations":[999]}]}'
                        ),
                    ):
                        r = await answer_question(client, "salt", "", "en")
                        self.assertEqual(r["status"], "failed")
                        self.assertEqual(r["reason_code"], "invalid_citation")
                        self.assertNotIn("Unsupported citation", r["message"])
                    with patch(
                        "backend.app.chat.generate",
                        new=AsyncMock(
                            return_value='{"claims":[{"text":"Take 9 grams","citations":[1]}]}'
                        ),
                    ):
                        r = await answer_question(client, "salt", "", "en")
                        self.assertEqual(r["status"], "unsupported")

        asyncio.run(run())

    def test_unknown_sodium_excludes_recipe(self):
        from backend.app.planner import calculate, catalog
        import copy

        ingredients, rows = catalog()
        ingredients = copy.deepcopy(ingredients)
        code = next(iter(rows[0]["ingredients"]))
        ingredients[code]["nutrients"]["NA"].update(status="not_reported", value=None)
        with self.assertRaises(ValueError):
            calculate(rows[0], ingredients)

    def test_known_unsupported_profile_never_shows_examples(self):
        from backend.app.schemas import Profile

        profile = Profile(conditions=["kidney"]).model_dump()
        self.assertEqual(self.a.patch("/api/profile", json=profile).status_code, 200)
        home = self.a.get("/api/home/today").json()
        self.assertEqual(home["status"], "unsupported")
        self.assertEqual(home["examples"], [])
