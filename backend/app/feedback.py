"""User-facing outcomes: an observed reason and an actionable next step."""

import json
import httpx
import psycopg
from pydantic import ValidationError

FEEDBACK_VERSION = "explanatory-outcomes-v1"

# Each entry: status, reason (zh/en/ja), next steps (zh/en/ja).
MESSAGES = {
    "required_food_unavailable": ("infeasible", (
        "当前可用菜谱中，没有同时满足以下食材和餐次要求、且符合您档案限制的候选：{details}。因此暂时无法完成这份菜单。",
        "No available recipe candidate meets these food and meal requirements together with your profile restrictions: {details}. The requested menu cannot yet be completed.",
        "現在のレシピには、次の食材・食事条件とプロフィールの制限を同時に満たす候補がありません：{details}。そのため、指定の献立を完成できません。",
    ), (
        "可请管理员补充对应食材与菜谱，或明确调整这项食材/餐次要求。系统不会自行忽略要求，也不会放宽真实过敏限制。",
        "Ask an administrator to add the relevant ingredients and recipes, or explicitly change this food or meal requirement. The system will not silently drop it or relax genuine allergy restrictions.",
        "管理者に該当食材・レシピの追加を依頼するか、食材・食事条件の変更を明示してください。条件を勝手に無視したり、実際のアレルギー制限を緩めたりはしません。",
    )),
    "invalid_budget_range": ("needs_clarification", (
        "本次预算区间不完整或上下限无效，无法确定允许的每日花销。",
        "The budget range is incomplete or its bounds are invalid, so the allowed daily spending is unclear.",
        "予算範囲が不完全、または上下限が無効なため、一日に許容される食費を決められません。",
    ), (
        "请用整数日元明确上下限，且下限不大于上限；目前支持一百至两万日元。例如“每天一千五百至两千日元”。若只限制最高花费，请说明“不超过两千日元”。",
        "Give whole-yen minimum and maximum amounts, with the minimum no higher than the maximum, within one hundred to twenty thousand yen. For example, 'between fifteen hundred and two thousand yen daily', or simply 'no more than two thousand yen'.",
        "百円から二万円の範囲で整数の下限・上限を指定し、下限が上限を超えないようにしてください。例：「一日千五百円から二千円」。上限だけなら「二千円以下」と指定してください。",
    )),
    "ambiguous_budget_range": ("needs_clarification", (
        "消息中出现了不同的金额区间，尚不能确定哪一个是一天三餐的总预算。",
        "The message contains different spending ranges, so the total daily budget is unclear.",
        "メッセージに異なる金額範囲があり、三食合計の一日予算を特定できません。",
    ), (
        "请单独写明每天三餐合计的预算下限和上限后重新提交。",
        "Specify the minimum and maximum total daily cost for all three meals, then resubmit.",
        "三食合計の一日予算の下限と上限を明記して再送してください。",
    )),
    "no_feasible_budget_range": ("infeasible", (
        "现有菜谱中没有组合能同时满足您要求的每日花销区间 {details}、指定食材/餐次条件、能量范围和钠上限，因此没有返回区间外的菜单。",
        "No current recipe combination meets the requested daily spending range {details}, food/meal requirements, energy range and sodium limit together, so no out-of-range menu was returned.",
        "指定された一日の食費範囲 {details} と食材・食事条件・エネルギー範囲・ナトリウム上限を同時に満たす組み合わせがなく、範囲外の献立は返していません。",
    ), (
        "可调整预算区间或非健康类偏好后重试，或请管理员补充菜谱；真实过敏和健康限制仍应保留。若只要求不超预算，可以明确写出“只限制最高花费”。",
        "Adjust the range or nonmedical preferences, or ask an administrator to add recipes. Keep genuine allergy and health restrictions. If you only need a spending ceiling, state that explicitly.",
        "予算範囲や健康に関係しない好みを見直すか、管理者にレシピ追加を依頼してください。実際のアレルギー・健康制限は維持してください。上限だけでよければその旨を指定してください。",
    )),
    "unrecognized_restriction": ("needs_clarification", (
        "未能把这次提到的食材限制可靠地对应到食品目录，直接筛选可能漏掉需要排除的食材。",
        "The ingredient restriction could not be reliably matched to the food catalog, so selection might miss an ingredient to exclude.",
        "今回の食材制限を食品カタログに正確に対応付けられず、除外すべき食材を見落とす可能性があります。",
    ), (
        "请写明具体食材名称，或在“用户信息”选择并保存对应过敏原或不喜欢的食材后重试。",
        "Specify the ingredient name, or save the corresponding allergen or disliked ingredient in your profile and retry.",
        "具体的な食材名を記入するか、「ユーザー情報」で該当するアレルゲン・苦手な食材を保存して再試行してください。",
    )),
    "plan_validation_failed": ("failed", (
        "自动选出的菜单未通过独立校验，因此尚不能作为完成的推荐发布。",
        "The automatically selected menu failed independent validation, so it cannot be published as a completed recommendation.",
        "自動選定された献立が独立した検証を通過せず、完成した推薦として公開できませんでした。",
    ), (
        "请重新提交；若持续发生，请联系管理员检查菜谱数据和计算规则，不需要通过删除健康限制来绕过。",
        "Resubmit. If this persists, ask an administrator to check recipe data and calculation rules; do not remove health restrictions to bypass validation.",
        "再送してください。続く場合は管理者にレシピデータと計算ルールの確認を依頼し、健康制限を削除して回避しないでください。",
    )),
    "user_cancelled": ("cancelled", (
        "你已取消本次任务，因此没有继续等待它的结果。",
        "You cancelled this task, so the app stopped waiting for its result.",
        "今回のタスクをキャンセルしたため、結果の待機を終了しました。",
    ), (
        "如仍需要回答，可以修改问题后重新发送。",
        "If you still need an answer, edit the question if needed and send it again.",
        "回答が必要な場合は、必要に応じて質問を変更して再送してください。",
    )),
    "outside_diet_scope": ("out_of_scope", (
        "这个问题包含当前饮食助手未覆盖的内容，现有知识库和处理流程无法可靠支持这部分回答。",
        "This question includes topics outside the diet assistant's coverage, which its knowledge base and workflows cannot reliably answer.",
        "この質問には食事アシスタントの対象外の内容が含まれ、現在の資料と処理では信頼できる回答を作成できません。",
    ), (
        "可以继续询问食材、营养、烹饪、饮食预算或菜单安排；若包含多个问题，请把饮食相关部分单独发来。",
        "Ask about ingredients, nutrition, cooking, food budgets or meal planning. If several topics are mixed, send the diet-related part separately.",
        "食材・栄養・調理・食費・献立について質問できます。複数の話題がある場合は食事に関する部分を分けて送ってください。",
    )),
    "unclear_question": ("needs_clarification", (
        "这条消息还不足以判断你想了解哪种食物，或希望生成怎样的菜单。",
        "The message does not yet identify the food question or meal plan you want.",
        "このメッセージだけでは、知りたい食品や希望する献立を特定できません。",
    ), (
        "请补充食材名称、具体疑问或餐次，例如“豆腐有哪些营养”或“安排一天三餐，预算一千日元”。",
        "Add the ingredient, specific question or meal, for example 'What nutrients does tofu contain?' or 'Plan a day of meals for one thousand yen.'",
        "食品名・具体的な疑問・食事を補足してください。例：「豆腐にはどんな栄養がある？」「一日千円で三食を提案して」。",
    )),
    "profile_update_required": ("needs_clarification", (
        "这次提到的信息或限制尚未在用户档案中确认，直接生成菜单可能沿用旧条件。",
        "The information or restriction in this message has not been confirmed in your profile, so a meal plan could use outdated constraints.",
        "今回の情報や制限はプロフィールで未確認のため、古い条件で献立を作成する可能性があります。",
    ), (
        "请到“用户信息”核对相关健康、过敏、偏好或预算信息并保存，再提交菜单请求；也可以先询问一般饮食知识。",
        "Review and save the relevant health, allergy, preference or budget information in your profile, then resubmit. You can still ask general diet questions.",
        "「ユーザー情報」で健康・アレルギー・好み・予算の該当項目を確認して保存し、再送してください。一般的な食事の質問は続けられます。",
    )),
    "replacement_context_missing": ("needs_clarification", (
        "换餐需要原方案和要替换的餐次；这次请求缺少其中的信息，无法确定应保留哪些餐。",
        "A replacement needs the original plan and the meal to change. The request lacks that context, so the meals to keep are unclear.",
        "食事の変更には元のプランと変更する食事が必要ですが、情報が足りず、残す食事を特定できません。",
    ), (
        "请在历史方案里选择早餐、午餐或晚餐后点击换餐；若要调整预算，也请写明每日金额。",
        "Open a saved plan and select breakfast, lunch or dinner to replace. Specify a daily amount if changing the budget.",
        "履歴のプランで朝食・昼食・夕食を選んで変更してください。予算を変える場合は一日分の金額も指定してください。",
    )),
    "unsupported_plan_profile": ("unsupported", (
        "档案中有以下需要单独评估的条件：{details}。当前自动菜单规则没有覆盖这些条件，无法核验方案是否适用。",
        "Your profile includes conditions requiring separate assessment: {details}. The automatic meal rules do not cover them, so the plan's suitability cannot be verified.",
        "個別の評価が必要な条件が記録されています：{details}。現在の自動献立ルールはこれらを網羅せず、適用可否を確認できません。",
    ), (
        "可以继续询问相关饮食知识。请先与医生或营养师确认个人饮食限制；档案若有误可更正，真实健康或过敏条件请保留。",
        "You can continue asking diet questions. Confirm personal dietary restrictions with your clinician or dietitian. Correct inaccurate records, but keep genuine health and allergy information.",
        "食事に関する質問は続けられます。個人の制限は医師・管理栄養士に確認してください。誤記は修正できますが、実際の健康・アレルギー情報は残してください。",
    )),
    "profile_incomplete": ("needs_clarification", (
        "生成个人菜单还缺少这些已确认信息：{details}。缺少它们时，系统无法确定应使用的筛选条件。",
        "A personal meal plan still needs these confirmed details: {details}. Without them, the appropriate filters are unknown.",
        "個人向け献立には次の確認済み情報が必要です：{details}。未確認のままでは適切な絞り込み条件を決められません。",
    ), (
        "请在“用户信息”完成并保存这些项目，然后重新提交推荐请求。",
        "Complete and save these fields in User information, then resubmit the request.",
        "「ユーザー情報」で該当項目を確認・保存してから、もう一度リクエストしてください。",
    )),
    "allergen_unspecified": ("needs_clarification", (
        "档案选择了“存在过敏”，但没有填写具体过敏原，因此无法排除对应食材。",
        "Your profile indicates an allergy but names no allergen, so the affected ingredients cannot be excluded.",
        "プロフィールではアレルギーありとなっていますが、具体的な原因が未入力のため、該当食材を除外できません。",
    ), (
        "请在“用户信息”选择已确认的过敏原并保存；尚不明确时可以先询问一般知识，暂不生成个人菜单。",
        "Save the confirmed allergens in User information. If they are not yet known, ask general questions before requesting a personal plan.",
        "「ユーザー情報」に確認済みのアレルゲンを保存してください。不明な場合は、個人の献立作成前に一般的な質問をご利用ください。",
    )),
    "budget_missing": ("needs_clarification", (
        "请求和档案都没有可用的每日预算，也无法从收入档次得到预算，因此没有金额上限可用于筛选。",
        "Neither the request nor profile supplies a usable daily budget, and no income-band budget is available, so there is no spending limit for selection.",
        "リクエスト・プロフィール・所得区分から一日の予算を取得できず、選定に必要な金額上限がありません。",
    ), (
        "可以直接在消息中写明每日预算（日元），或在“用户信息”保存每日预算或收入档次。",
        "Specify a daily budget in yen in your message, or save a daily budget or income band in User information.",
        "メッセージに一日の予算を円で指定するか、「ユーザー情報」に予算または所得区分を保存してください。",
    )),
    "no_meal_candidates": ("infeasible", (
        "现有菜谱经过数据完整性、过敏、偏好、时间和换餐条件筛选后，以下餐次没有候选：{details}。",
        "After data-completeness, allergy, preference, time and replacement checks, the current catalog has no candidates for: {details}.",
        "データの完全性・アレルギー・好み・調理時間・変更条件で絞り込むと、次の食事に候補が残りません：{details}。",
    ), (
        "可检查不喜欢的食材或烹饪时间是否填写合适，换餐时也可尝试重新生成全天方案；管理员可补充菜谱。保留真实的过敏和健康限制，仅增加预算未必能解决候选缺失。",
        "Check preferences and cooking time; for replacements, try a new full-day plan. An administrator can add recipes. Keep genuine allergy and health restrictions; a higher budget alone may not restore missing candidates.",
        "好みや調理時間を確認し、変更時は一日分の再作成も試せます。管理者はレシピを追加できます。実際のアレルギー・健康制限は維持してください。予算増だけで候補不足が解消するとは限りません。",
    )),
    "no_feasible_combination": ("infeasible", (
        "各餐次都有候选，但没有组合同时满足每日预算、能量范围和钠上限；目前不能把原因单独归结为预算。",
        "Each meal has candidates, but no combination meets the daily budget, energy range and sodium limit together. This does not establish budget as the sole cause.",
        "各食事に候補はありますが、予算・エネルギー範囲・ナトリウム上限を同時に満たす組み合わせがありません。予算だけが原因とは断定できません。",
    ), (
        "可逐项调整预算、非健康类偏好或烹饪时间后重试，或请管理员补充菜谱。不要为了生成结果而删除真实过敏条件或随意提高健康目标上限。",
        "Try adjusting the budget, nonmedical preferences or cooking time one at a time, or ask an administrator to add recipes. Do not remove genuine allergies or arbitrarily raise health limits to obtain a result.",
        "予算・健康に関係しない好み・調理時間を一項目ずつ見直すか、管理者にレシピ追加を依頼してください。結果を出すために実際のアレルギーを消したり健康上限を任意に上げたりしないでください。",
    )),
    "no_usable_evidence": ("unsupported", (
        "本次检索没有找到可用的知识库原文，因此无法给出有来源支撑的解释。",
        "This search found no usable knowledge-base passages to support an explanation.",
        "今回の検索では、説明の根拠となる利用可能な原文が見つかりませんでした。",
    ), (
        "请补充具体食材或缩小问题范围后再试；管理员也可补充相关知识资料。涉及个人食用限制时，请提供医生已确认的限制。",
        "Name the food or narrow the question and try again. An administrator can add relevant references. For personal restrictions, provide clinician-confirmed details.",
        "食品名を補足するか質問を絞って再度お試しください。管理者は関連資料を追加できます。個人の制限については医師に確認済みの内容を補足してください。",
    )),
    "insufficient_evidence": ("unsupported", (
        "检索到了相关资料，但未能形成有依据且适用于这次问题的回答；相似原文并不代表足以支持个人结论。",
        "Related passages were retrieved, but they did not yield a supported answer applicable to this question. Similar text alone does not establish a personal conclusion.",
        "関連資料は見つかりましたが、今回の質問に適用できる根拠のある回答には至りませんでした。文章の類似だけでは個人の結論を裏付けられません。",
    ), (
        "请明确要了解的是营养成分、烹饪方式还是个人食用限制，或补充已确认的相关条件；也可请管理员补充适用资料。",
        "Specify whether you mean nutrients, cooking or personal restrictions, or add confirmed relevant context. An administrator can add applicable references.",
        "栄養成分・調理方法・個人の摂取制限のどれについて知りたいか明確にするか、確認済みの条件を補足してください。管理者による適用資料の追加も可能です。",
    )),
    "numeric_verification_required": ("unsupported", (
        "候选回答中只剩含数值的内容，系统尚未核对这些数值是否可用于本次回答，因此没有直接发布。",
        "Only numerical content remained in the candidate answer, and those values have not been verified for this response, so they were not published.",
        "回答候補に数値を含む内容しか残らず、今回使用できる数値か確認できていないため、そのまま掲載していません。",
    ), (
        "可以查看下方原文，或改问不涉及个人用量的一般原理；个人摄入量需要结合经确认的条件核对。",
        "Review the original passages below or ask about general principles without personal quantities. Individual intake amounts need verification against confirmed circumstances.",
        "下の原文を確認するか、個人の摂取量を含まない一般的な仕組みを質問してください。個人の摂取量は確認済みの条件に照らして検証が必要です。",
    )),
    "invalid_citation": ("failed", (
        "生成的解释引用了本次没有检索到的来源，未通过来源核验，因此没有发布这段解释。",
        "The generated explanation cited a source not retrieved for this request. It failed source verification and was not published.",
        "生成された説明が今回取得していない出典を参照したため、出典確認を通過せず掲載していません。",
    ), (
        "请稍后重试或把问题拆成更具体的单个问题；若持续发生，请联系管理员检查知识检索与模型输出。",
        "Try again or ask one more specific question. If this persists, contact an administrator to check retrieval and model output.",
        "再度試すか、より具体的な一つの質問に分けてください。続く場合は管理者に検索とモデル出力の確認を依頼してください。",
    )),
    "processing_timeout": ("failed", (
        "处理超过等待时限，尚未得到完成校验的结果。",
        "Processing exceeded the time limit before a validated result was available.",
        "検証済みの結果を得る前に処理の待機時間を超えました。",
    ), (
        "请稍后重试，或先发送一个较简短的问题；如果反复超时，请联系管理员检查服务负载。",
        "Retry later or send a shorter question. If timeouts recur, contact an administrator to check service load.",
        "しばらくして再試行するか、短い質問を送ってください。繰り返す場合は管理者にサービス負荷の確認を依頼してください。",
    )),
    "model_service_unavailable": ("failed", (
        "调用模型或检索服务时连接失败或服务返回错误，本次处理没有完成。",
        "A model or retrieval service connection failed or returned an error, so processing did not complete.",
        "モデルまたは検索サービスへの接続失敗・エラー応答により処理が完了しませんでした。",
    ), (
        "请稍后重新提交；持续发生时请联系管理员检查模型服务。也可以在“今日食谱”查看已有结果。",
        "Resubmit later. If this persists, ask an administrator to check the model service. You can also view existing results on Today's meals.",
        "しばらくして再送してください。続く場合は管理者にモデルサービスの確認を依頼してください。「今日の食事」で既存の結果も確認できます。",
    )),
    "invalid_model_output": ("failed", (
        "模型输出未满足本次处理需要的结构或校验要求，无法把它作为完整结果返回。",
        "The model output did not meet the required structure or validation checks, so it could not be returned as a complete result.",
        "モデル出力が必要な構造や検証条件を満たさず、完成した結果として返せませんでした。",
    ), (
        "请重试或将问题写得更具体；持续发生时请联系管理员检查模型输出。",
        "Retry or make the question more specific. If this persists, ask an administrator to check model output.",
        "再試行するか質問を具体的にしてください。続く場合は管理者にモデル出力の確認を依頼してください。",
    )),
    "data_service_unavailable": ("failed", (
        "读取或保存所需数据时发生异常，本次处理没有完成。",
        "An error occurred while reading or saving required data, so processing did not complete.",
        "必要なデータの読み取り・保存でエラーが発生し、処理が完了しませんでした。",
    ), (
        "请稍后重试；持续发生时请联系管理员检查数据服务。",
        "Retry later. If this persists, contact an administrator to check the data service.",
        "しばらくして再試行してください。続く場合は管理者にデータサービスの確認を依頼してください。",
    )),
    "processing_interrupted": ("failed", (
        "任务中断后重试仍未在有效时间内完成，系统已停止继续等待这次任务。",
        "The interrupted task still did not complete within its retry window, so the system stopped waiting for it.",
        "中断した処理が再試行期間内にも完了せず、今回のタスクの待機を終了しました。",
    ), (
        "请重新发送请求；如果再次中断，请联系管理员检查后台任务服务。",
        "Send the request again. If it is interrupted again, contact an administrator to check background processing.",
        "リクエストをもう一度送ってください。再度中断する場合は管理者にバックグラウンド処理の確認を依頼してください。",
    )),
    "processing_error": ("failed", (
        "处理过程中发生异常，未得到可返回的完整结果；目前无法进一步确定具体原因。",
        "An unexpected processing error prevented a complete result. A more specific cause has not been established.",
        "処理中の予期しないエラーにより完全な結果が得られず、現時点では詳しい原因を特定できません。",
    ), (
        "请稍后重试；如反复出现，请把发生时间和问题内容提供给管理员排查。",
        "Retry later. If it recurs, give the administrator the time and question for investigation.",
        "しばらくして再試行してください。繰り返す場合は発生時刻と質問内容を管理者に伝えてください。",
    )),
}

LABELS = {
    "age": ("年龄", "age", "年齢"),
    "allergy_status": ("过敏情况", "allergy status", "アレルギーの有無"),
    "health_confirmed": ("健康情况确认", "health confirmation", "健康状態の確認"),
    "demo_consent": ("页面底部的目标与模拟价格确认", "target and estimated-price confirmation at the bottom of the profile", "ページ下部の目標・仮定価格への確認"),
    "minor": ("未满十八岁", "under eighteen", "十八歳未満"),
    "diabetes": ("糖尿病", "diabetes", "糖尿病"),
    "kidney": ("肾脏相关疾病", "kidney condition", "腎臓に関する疾患"),
    "pregnancy": ("孕期", "pregnancy", "妊娠"),
    "other": ("其他健康条件", "other health conditions", "その他の健康条件"),
    "unspecified_allergen": ("未明确的其他过敏原", "an unspecified other allergen", "その他の未指定アレルゲン"),
    "breakfast": ("早餐", "breakfast", "朝食"),
    "lunch": ("午餐", "lunch", "昼食"),
    "dinner": ("晚餐", "dinner", "夕食"),
}


def labels(keys, language):
    index = {"zh": 0, "en": 1, "ja": 2}.get(language, 0)
    return ("、" if index != 1 else ", ").join(LABELS[k][index] for k in keys)


def explain(code, language="zh", *, details="", **metadata):
    status, reasons, steps = MESSAGES[code]
    index = {"zh": 0, "en": 1, "ja": 2}.get(language, 0)
    reason = reasons[index].format(details=details)
    next_step = steps[index]
    message = (
        "无法回答与饮食无关的内容"
        if code == "outside_diet_scope"
        else reason + "\n\n" + next_step
    )
    return {
        "status": status, "reason_code": code, "reason": reason,
        "next_steps": [next_step], "message": message,
        **metadata,
    }


class ResultCheckError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


def failure_result(exc, language="zh"):
    # Do not expose exception text, upstream bodies, prompts or connection URLs.
    if isinstance(exc, ResultCheckError):
        code = exc.reason_code
    elif isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        code = "processing_timeout"
    elif isinstance(exc, httpx.HTTPError):
        code = "model_service_unavailable"
    elif isinstance(exc, (ValidationError, json.JSONDecodeError)):
        code = "invalid_model_output"
    elif isinstance(exc, psycopg.Error):
        code = "data_service_unavailable"
    else:
        code = "processing_error"
    return explain(code, language)
