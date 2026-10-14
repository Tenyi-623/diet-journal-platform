"""Frozen synthetic scenarios; no personal data and no writes to application tables."""

import asyncio, hashlib, json, time
from pathlib import Path
import httpx
from backend.app.chat import classify
from backend.app.planner import plan_day, validate_plan, catalog
from backend.app.schemas import Profile
from backend.config import settings

OUT = Path("docs/evaluation")
OUT.mkdir(exist_ok=True)


async def main():
    scenarios = json.loads((OUT / "frozen-scenarios.json").read_text())
    results = []
    base = Profile(
        age=40,
        allergy_status="none",
        health_confirmed=True,
        demo_consent=True,
        income_band="JPY_A1",
    ).model_dump(exclude={"expected_version"})
    for case in scenarios["planner"]:
        profile = {**base, **case["profile"]}
        start = time.monotonic()
        r = plan_day(profile, case.get("budget"))
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "actual": r["status"],
                "pass": r["status"] == case["expected"],
                "hard_constraints_pass": validate_plan(r, profile)
                if r["status"] == "ready"
                else None,
                "totals": r.get("totals"),
                "budget_jpy": r.get("budget_jpy"),
                "seconds": time.monotonic() - start,
            }
        )
    ingredients, _ = catalog()
    names = {k: v["name"] for k, v in ingredients.items()}
    classification = []
    async with httpx.AsyncClient(timeout=180) as client:
        models = (await client.get(settings.ollama_base_url + "/api/tags")).json()[
            "models"
        ]
        for case in scenarios["classification"]:
            start = time.monotonic()
            try:
                r = await classify(
                    client, case["input"], case.get("history", []), names
                )
                row = {
                    "id": case["id"],
                    "language": case["language"],
                    "expected": case["domain"],
                    "actual": r.model_dump(),
                    "pass": r.domain == case["domain"],
                    "seconds": time.monotonic() - start,
                }
            except Exception as e:
                row = {
                    "id": case["id"],
                    "language": case["language"],
                    "pass": False,
                    "error": type(e).__name__,
                }
            classification.append(row)
            print(case["id"], row["pass"], flush=True)
    report = {
        "testset_sha256": hashlib.sha256(
            (OUT / "frozen-scenarios.json").read_bytes()
        ).hexdigest(),
        "models": models,
        "planner": results,
        "classification": classification,
        "limitations": "Synthetic engineering acceptance only. Model results are not proof for arbitrary inputs. No clinical efficacy, human citation review, or retrieval recall benchmark.",
    }
    (OUT / "frozen-results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(
        "PLANNER",
        sum(x["pass"] for x in results),
        "/",
        len(results),
        "CLASSIFIER",
        sum(x["pass"] for x in classification),
        "/",
        len(classification),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
