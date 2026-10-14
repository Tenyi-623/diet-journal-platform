"""Profile context and deterministic allergy safeguards for educational Q&A."""

import re

ALLERGENS = {
    "egg": ("鸡蛋", "egg", "卵", r"鸡蛋|雞蛋|蛋黄|蛋黃|蛋清|鶏卵|たまご|玉子|卵|\beggs?\b|\byolks?\b"),
    "milk": ("牛奶", "milk", "乳", r"牛奶|奶酪|乳製品|牛乳|チーズ|\bmilk\b|\bdairy\b|\bcheese\b"),
    "soy": ("大豆", "soy", "大豆", r"大豆|豆腐|豆浆|豆漿|豆乳|\bsoy(?:a|beans?)?\b|\btofu\b"),
    "wheat": ("小麦", "wheat", "小麦", r"小麦|小麥|小麦粉|\bwheat\b"),
    "fish": ("鱼", "fish", "魚", r"鱼|魚|\bfish\b|\bsalmon\b|\btuna\b"),
    "nuts": ("坚果", "nuts", "ナッツ", r"坚果|堅果|花生|核桃|杏仁|巴旦木|扁桃仁|ナッツ|アーモンド|くるみ|クルミ|落花生|\b(?:peanuts?|nuts?|almonds?|walnuts?)\b"),
    "other": ("其他未注明的过敏原", "an unspecified allergen", "その他の未指定アレルゲン", r"(?!)"),
}
CONDITIONS_JA = {
    "hypertension": "高血圧", "diabetes": "糖尿病", "kidney": "腎臓病",
    "pregnancy": "妊娠", "other": "その他の健康上の制限",
}


def text(language, zh, en, ja):
    return {"zh": zh, "en": en, "ja": ja}.get(language, zh)


def allergy_source(language):
    # Curated supplementary reference, not an uploaded KB document or a PDF chunk.
    return {
        "chunk_id": "safety-nhs-food-allergy",
        "source_type": "external_guidance",
        "title": "NHS — Food allergy",
        "publisher": "NHS",
        "url": "https://www.nhs.uk/conditions/food-allergy/",
        "checked_on": "2026-10-11",
        "content": text(language,
            "NHS 建议避开引起过敏的食物及含相关成分的食品，仔细核对配料，并遵循专科医生制定的过敏管理方案。",
            "NHS advises avoiding foods that trigger an allergy, checking ingredients, and following the specialist's allergy action plan.",
            "NHS は原因食品とその成分を含む食品を避け、原材料を確認し、専門医のアレルギー管理計画に従うよう案内しています。"),
        "warning": text(language,
            "补充的公开健康资料；不是知识库检索片段。个人过敏记录来自用户档案，未经本系统诊断。",
            "Supplementary public guidance, not a retrieved KB passage. Allergy information is user-reported, not diagnosed by this app.",
            "補足の公開健康情報であり、知識ベースの検索結果ではありません。アレルギー情報は自己申告で、本システムによる診断ではありません。"),
    }


def allergy_conflict(allergens, language, *, status="needs_clarification"):
    """Explain a verified request/profile conflict before selecting alternatives."""
    matched = sorted(set(allergens))
    index = {"zh": 0, "en": 1, "ja": 2}.get(language, 0)
    names = ("、" if index != 1 else ", ").join(ALLERGENS[a][index] for a in matched)
    reason = text(language,
        f"由于您对{names}过敏，所以无法推荐{names}相关的饮食。",
        f"Your profile records an allergy to {names}, so I cannot recommend meals containing {names}.",
        f"プロフィールに{names}のアレルギーが記録されているため、{names}を含む食事はおすすめできません。")
    next_step = text(language,
        f"可以为您安排不含{names}的方案。您可以回复“安排不含{names}的三餐”继续。",
        f"I can help plan meals without {names}. Reply with a request for meals excluding {names} to continue.",
        f"{names}を使わない献立を提案できます。続ける場合は「{names}抜きの三食を提案して」と返信してください。")
    return {
        "status": status,
        "reason_code": "requested_food_allergy_conflict",
        "reason": reason, "next_steps": [next_step],
        "message": reason + "\n\n" + next_step,
        "safety_basis": "saved_profile", "matched_allergens": matched,
        "evidence": [allergy_source(language)],
    }


def qa_context(profile):
    """Only medically relevant, bounded enum data reaches the model."""
    age = profile.get("age")
    return {
        "age_group": "unknown" if age is None else "minor" if age < 18 else "adult",
        "conditions": [c for c in profile.get("conditions", []) if c in CONDITIONS_JA],
        "allergens": [a for a in profile.get("allergens", []) if a in ALLERGENS],
        "allergy_status": profile.get("allergy_status", "unknown"),
        "health_confirmed": bool(profile.get("health_confirmed")),
        "diet": profile.get("diet", "any"),
    }


def safety_context(question, japanese, profile, language, new_profile_facts=False):
    context = qa_context(profile)
    allergens = context["allergens"]
    lang_index = {"zh": 0, "en": 1, "ja": 2}.get(language, 0)
    names = "、".join(ALLERGENS[a][lang_index] for a in allergens)
    warnings = []
    evidence = []
    matched = [
        a for a in allergens
        if re.search(ALLERGENS[a][3], question + "\n" + japanese, re.IGNORECASE)
    ]
    if allergens:
        warnings.append(text(language,
            f"你当前的用户档案记录了以下过敏原：{names}。本回答不能作为食用这些食材或含其成分食品的许可；请核对配料，并遵循医生为你制定的过敏管理方案。若档案填写有误，请先到“用户信息”核对更正。",
            f"Your saved profile lists these allergens: {names}. This answer does not clear you to eat them or foods containing them. Check ingredients and follow your clinician's allergy plan. Correct an inaccurate record in User information.",
            f"保存されたプロフィールのアレルゲン：{names}。この回答は、それらや含有食品を食べてよいという判断ではありません。原材料を確認し、医師の管理計画に従ってください。誤記は「ユーザー情報」で確認・修正してください。"))
        evidence.append(allergy_source(language))
    if context["allergy_status"] == "unknown" or (
        context["allergy_status"] == "present" and not allergens
    ) or "other" in allergens:
        warnings.append(text(language,
            "过敏信息尚不完整，可以提供一般知识，但需确认具体过敏原后才能判断个人食用限制。",
            "Allergy information is incomplete. General information is available, but personal food restrictions need the specific allergen to be confirmed.",
            "アレルギー情報が不完全です。一般的な情報は提供できますが、個人の摂取制限には具体的なアレルゲンの確認が必要です。"))
    if context["conditions"] or context["age_group"] == "minor":
        warnings.append(text(language,
            "会结合档案中的健康条件查找资料。一般营养知识不能单独确定你个人是否适合食用或食用量；需考虑病情、治疗情况和医生的具体限制。",
            "The search considers your recorded health conditions. General nutrition information cannot determine personal suitability or portions without clinical context and your clinician's restrictions.",
            "記録された健康条件を考慮して検索します。一般的な栄養情報だけでは個人の摂取可否や量は判断できず、病状・治療・医師の指示の確認が必要です。"))
    if new_profile_facts:
        warnings.append(text(language,
            "这次提到的新健康或过敏信息尚未写入档案；以下仅作知识解释。生成菜单前请到“用户信息”确认更新。",
            "New health or allergy information in this question has not been saved. This is educational information; confirm your profile before generating meals.",
            "今回の新しい健康・アレルギー情報はプロフィールに保存されていません。以下は一般情報です。献立作成前に「ユーザー情報」で更新してください。"))
    return context, warnings, evidence, matched
