import { useId, useState } from "react";
import { BookOpen } from "lucide-react";
import { translate, type Lang } from "./i18n";

export function PlanExplanation({
  result,
  lang,
  onOpen,
}: {
  result: any;
  lang: Lang;
  onOpen: (meal: any) => void;
}) {
  const id = useId();
  const [openCitations, setOpenCitations] = useState<number[]>([]);
  const text = (zh: string, en: string, ja: string) =>
    lang === "zh" ? zh : lang === "en" ? en : ja;
  const name = (value: any) => value?.[lang] ?? value?.zh ?? "";
  const t = (key: string) => translate(lang, key);
  const num = (n: number, digits = 0) =>
    Number(n).toLocaleString(lang, { maximumFractionDigits: digits });
  const { totals, targets, budget_jpy: budget } = result;
  const profile = result.profile_snapshot ?? {};
  const explanation = result.knowledge_explanation;
  const sources: any[] = result.evidence ?? [];
  const sourceNumber = (cid: number) =>
    sources.findIndex((s) => s.chunk_id === cid) + 1;
  const budgetSource =
    result.budget_source === "request"
      ? text("本次请求", "this request", "今回のリクエスト")
      : result.budget_source === "profile"
        ? text(
            "已保存的每日预算",
            "your saved daily budget",
            "保存した一日予算",
          )
        : text(
            "收入档位的模拟预算",
            "the income band's demo budget",
            "収入区分の仮定予算",
          );

  return (
    <div className="plan-explanation">
      <section
        aria-label={text(
          "为什么这样推荐",
          "Why these meals",
          "この献立を選んだ理由",
        )}
      >
        <h3>
          {text("为什么这样推荐", "Why these meals", "この献立を選んだ理由")}
        </h3>
        {targets && (
          <ul className="selection-reasons">
            <li>
              {result.budget_min_jpy != null ? text(
                `预算区间：${budgetSource}要求每天 ¥${num(result.budget_min_jpy)}–¥${num(budget)}。三餐模拟食用成本 ¥${num(totals.cost_jpy, 2)}，同时满足下限和上限。`,
                `Budget range: ${budgetSource} specifies ¥${num(result.budget_min_jpy)}–¥${num(budget)} daily. Estimated food cost is ¥${num(totals.cost_jpy, 2)}, meeting both bounds.`,
                `予算範囲：${budgetSource}で一日 ¥${num(result.budget_min_jpy)}–¥${num(budget)} を指定。三食の仮定食費 ¥${num(totals.cost_jpy, 2)} は下限・上限の両方を満たします。`,
              ) : text(
                `预算：使用${budgetSource} ¥${num(budget)}。三餐模拟食用成本 ¥${num(totals.cost_jpy, 1)}，剩余 ¥${num(budget - totals.cost_jpy, 1)}；预算是上限，不要求花满。`,
                `Budget: ¥${num(budget)} from ${budgetSource}. Estimated demo food cost is ¥${num(totals.cost_jpy, 1)}, leaving ¥${num(budget - totals.cost_jpy, 1)}. The budget is a ceiling, not a spending target.`,
                `予算：${budgetSource}の ¥${num(budget)} を使用。三食の仮定食費は ¥${num(totals.cost_jpy, 1)}、残額は ¥${num(budget - totals.cost_jpy, 1)}。予算は上限で、使い切る必要はありません。`,
              )}
            </li>
            {result.food_requirements?.length > 0 && (
              <li>
                {text("已满足的食材要求：", "Food requests met: ", "満たした食材の条件：")}
                {result.food_requirements.map((r: any) =>
                  `${r.meal === "any" ? text("全天", "Across the day", "一日全体") : t(r.meal)}：${t(r.food)}`
                ).join("；")}
              </li>
            )}
            <li>
              {text(
                `能量：全天 ${num(totals.energy_kcal)} kcal，位于你确认的 ${num(targets.energy_kcal)} kcal 目标允许范围 ${num(targets.energy_kcal * (1 - targets.energy_tolerance))}–${num(targets.energy_kcal * (1 + targets.energy_tolerance))} kcal 内。`,
                `Energy: ${num(totals.energy_kcal)} kcal, within the allowed ${num(targets.energy_kcal * (1 - targets.energy_tolerance))}–${num(targets.energy_kcal * (1 + targets.energy_tolerance))} kcal range around your confirmed ${num(targets.energy_kcal)} kcal target.`,
                `エネルギー：合計 ${num(totals.energy_kcal)} kcal。確認した目標 ${num(targets.energy_kcal)} kcal の許容範囲 ${num(targets.energy_kcal * (1 - targets.energy_tolerance))}–${num(targets.energy_kcal * (1 + targets.energy_tolerance))} kcal 内です。`,
              )}
            </li>
            <li>
              {text(
                `钠：按成分表显示精度估算的全天上界为 ${num(totals.sodium_table_upper_mg)} mg，未超过你确认的 ${num(targets.sodium_max_mg)} mg 上限。此数值是表值估算，不是实际餐食测量结果，也不表示钠越低越好。`,
                `Sodium: the table-precision upper estimate is ${num(totals.sodium_table_upper_mg)} mg, within your confirmed ${num(targets.sodium_max_mg)} mg cap. This is a table estimate, not a meal measurement or a claim that less sodium is always better.`,
                `ナトリウム：成分表の表示精度に基づく上限推定は ${num(totals.sodium_table_upper_mg)} mg、確認した上限 ${num(targets.sodium_max_mg)} mg 以下です。実際の食事の測定値ではなく、低いほどよいという意味でもありません。`,
              )}
            </li>
          </ul>
        )}
        <p>
          {text(
            `筛选时排除了档案中记录的过敏原、不喜欢的食材及不符合饮食偏好的组合，单餐准备时间不超过 ${profile.cooking_minutes ?? 45} 分钟。在${result.feasible_candidates ? ` ${num(result.feasible_candidates)} 个` : ""}可行组合中，综合考虑接近能量目标、模拟成本和主要蛋白质食材的重复程度。`,
            `Selection excludes recorded allergens, disliked ingredients and incompatible dietary preferences, and limits preparation to ${profile.cooking_minutes ?? 45} minutes per meal. Feasible menus${result.feasible_candidates ? ` (${num(result.feasible_candidates)})` : ""} are scored by distance from the energy target, demo cost and repetition of main protein ingredients.`,
            `記録されたアレルゲン、苦手な食品、食事の好みに合わない組み合わせを除外し、一食の準備時間を ${profile.cooking_minutes ?? 45} 分以内に制限。条件を満たす${result.feasible_candidates ? ` ${num(result.feasible_candidates)} 通りの` : ""}組み合わせから、目標エネルギーとの差、仮定費用、主なたんぱく源の重複を総合評価しました。`,
          )}
        </p>
        <p className="muted">
          {text(
            "这些目标来自你确认的演示设置。满足当前约束不等于已证明全面营养均衡；知识库用于解释饮食原则，不直接设定个人目标或生成配方。",
            "Targets come from your confirmed demo settings. Passing these constraints does not establish full nutritional balance. Retrieved sources explain dietary principles; they do not set personal targets or supply the recipes.",
            "目標は確認済みのデモ設定です。条件を満たすことは栄養バランス全体の保証ではありません。資料は食事の原則の説明に使い、個人の目標やレシピは定めません。",
          )}
        </p>
        <div className="meal-reasons">
          {result.meals.map((m: any) => (
            <article key={m.meal}>
              <h4>
                {t(m.meal)} · {name(m.name)}
              </h4>
              <p>
                {m.ingredients
                  .map((p: any) => `${name(p.name)} ${num(p.grams, 1)} g`)
                  .join(" · ")}
              </p>
              <p>
                {text(
                  `提供 ${num(m.nutrition.energy_kcal)} kcal（约占全天 ${num((m.nutrition.energy_kcal / totals.energy_kcal) * 100)}%），钠表值上界 ${num(m.sodium_table_upper_mg)} mg；模拟成本 ¥${num(m.cost_jpy, 1)}，准备时间 ${m.minutes} 分钟。`,
                  `Provides ${num(m.nutrition.energy_kcal)} kcal (${num((m.nutrition.energy_kcal / totals.energy_kcal) * 100)}% of the daily total), with a table sodium upper estimate of ${num(m.sodium_table_upper_mg)} mg. Demo cost: ¥${num(m.cost_jpy, 1)}; preparation: ${m.minutes} minutes.`,
                  `${num(m.nutrition.energy_kcal)} kcal（一日合計の約 ${num((m.nutrition.energy_kcal / totals.energy_kcal) * 100)}%）、ナトリウム表値上限 ${num(m.sodium_table_upper_mg)} mg。仮定費用 ¥${num(m.cost_jpy, 1)}、準備 ${m.minutes} 分。`,
                )}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section
        aria-label={text(
          "知识库依据",
          "Knowledge base evidence",
          "知識ベースの根拠",
        )}
      >
        <h3>
          <BookOpen size={17} />{" "}
          {text("知识库依据", "Knowledge base evidence", "知識ベースの根拠")}
        </h3>
        {explanation?.status === "ready" ? (
          <>
            <p className="muted">
              {text(
                "以下为检索原文后的模型解释，已核对引用编号和摘录文字，尚未完成人工支持性审核。指南支持的是饮食原则，并非这份具体菜单。",
                "These explanations use retrieved passages. Citation IDs and quoted text are checked; support for the interpretation has not been human reviewed. Sources describe principles, not this exact menu.",
                "検索した原文に基づくモデルの説明です。引用番号と抜粋文字列は照合済みですが、解釈の妥当性は人手未確認です。資料は原則の根拠であり、この献立そのものの出典ではありません。",
              )}
            </p>
            {explanation.claims.map((claim: any, index: number) => (
              <article className="knowledge-claim" key={index}>
                <p>
                  {claim.text}{" "}
                  <a
                    href={`#${id}-source-${claim.citation}`}
                    onClick={() =>
                      setOpenCitations((ids) => [
                        ...new Set([...ids, claim.citation]),
                      ])
                    }
                  >
                    [{sourceNumber(claim.citation)}]
                  </a>
                </p>
                <small>
                  {text("对应餐次", "Related meals", "関連する食事")}：
                  {claim.meals.map(t).join(" · ")}
                </small>
                <blockquote lang="ja">{claim.quote}</blockquote>
              </article>
            ))}
            <div className="evidence">
              {sources.map((s, index) => (
                <details
                  key={s.chunk_id}
                  id={`${id}-source-${s.chunk_id}`}
                  open={openCitations.includes(s.chunk_id)}
                >
                  <summary
                    onClick={(event) => {
                      event.preventDefault();
                      setOpenCitations((ids) =>
                        ids.includes(s.chunk_id)
                          ? ids.filter((cid) => cid !== s.chunk_id)
                          : [...ids, s.chunk_id],
                      );
                    }}
                  >
                    [{index + 1}] {s.title} · PDF {s.pdf_page}
                    {s.printed_page
                      ? ` · ${text("印刷页", "printed page", "冊子ページ")} ${s.printed_page}`
                      : ""}
                  </summary>
                  <p className="muted">
                    {s.publisher} · {s.edition}
                  </p>
                  <p className="readable" lang="ja">
                    {s.content}
                  </p>
                  <small>{s.warning}</small>
                </details>
              ))}
            </div>
          </>
        ) : (
          <p className="muted">
            {!explanation
              ? text(
                  "这条历史方案未保存知识库解释。重新提交推荐可生成带引用的新方案。",
                  "This saved plan has no retrieved explanation. Submit a new request for a cited plan.",
                  "この履歴には資料に基づく説明がありません。再度リクエストすると引用付きの献立を作成できます。",
                )
              : explanation.message
                ? explanation.message
              : explanation.status === "no_evidence"
                ? text(
                    "本次未找到足以支持菜单解释的原文，因此没有附加知识库结论。上方仍展示可核对的计算依据；可以请管理员补充相关资料后重新请求。",
                    "No passage sufficiently supported an explanation for this menu. The calculation reasons remain available above; ask an administrator to add relevant references, then request again.",
                    "この献立の説明を支える原文が見つからなかったため、資料に基づく結論は付けていません。計算根拠は上に表示しています。管理者に関連資料の追加を依頼してから再度リクエストできます。",
                  )
                : text(
                    "本次知识库解释暂不可用；已保留通过校验的菜单及计算出处，可稍后重新请求。",
                    "The retrieved explanation is temporarily unavailable. The validated menu and calculation sources are preserved; you can request again later.",
                    "資料に基づく説明は一時的に利用できません。検証済みの献立と計算出典は保持されています。後ほど再試行できます。",
                  )}
          </p>
        )}
      </section>

      <section
        aria-label={text(
          "营养与菜谱出处",
          "Nutrition and recipe sources",
          "栄養値とレシピの出典",
        )}
      >
        <h3>
          {text(
            "营养与菜谱出处",
            "Nutrition and recipe sources",
            "栄養値とレシピの出典",
          )}
        </h3>
        <p>
          {text(
            "营养数值：文部科学省《日本食品标准成分表2020年版（八订）》结构化主表。按配料对应状态的每100g数值 × 可食重量计算；下方可展开核对每种配料的工作表、行号和单元格。",
            "Nutrients: the structured main table of MEXT's Standard Tables of Food Composition in Japan 2020 (8th revision), calculated from values per 100 g in the ingredient's stated condition and its edible weight. Expand below for worksheet, row and cell references.",
            "栄養値：文部科学省「日本食品標準成分表2020年版（八訂）」の構造化した本表。材料の記載状態に対応する可食部100g当たりの値と重量から計算。下でシート・行・セルを確認できます。",
          )}
        </p>
        {result.meals.map((m: any) => (
          <details key={m.meal}>
            <summary>
              {t(m.meal)} · {name(m.name)} — {t("source")}
            </summary>
            {m.ingredients.map((p: any) => (
              <div className="ingredient-source" key={p.code}>
                <strong>
                  {name(p.name)} · {p.code} · {num(p.grams, 1)} g
                </strong>
                <p>
                  Excel · {p.excel_sheet} · {text("行", "row", "行")}{" "}
                  {p.excel_row}
                </p>
                <small>
                  {Object.entries(p.nutrient_cells ?? {})
                    .map(([key, cell]) => {
                      const labels: Record<string, string> = {
                        ENERC_KCAL: "kcal",
                        "PROT-": "protein",
                        "FAT-": "fat",
                        "CHOCDF-": "carbs",
                        "FIB-": "fiber",
                        NA: "sodium",
                        K: "potassium",
                      };
                      return `${key === "NA" ? text("钠（原表值）", "Sodium (source value)", "ナトリウム（原表値）") : t(labels[key] ?? key)}: ${cell}`;
                    })
                    .join(" · ")}
                </small>
              </div>
            ))}
            <button className="plain text-link" onClick={() => onOpen(m)}>
              {t("details")} →
            </button>
          </details>
        ))}
        <p className="muted">
          {text(
            "菜谱与做法来自项目自建演示模板；价格为模拟食用成本，不是市场报价。每餐的模板版本和配料原值随方案保存。含微量或缺失数据的营养素不按零计算；尚不能据此判断膳食纤维是否达标。",
            "Recipes and preparation steps are project demo templates. Prices are simulated food costs, not market quotes. Template versions and raw ingredient values are saved with the plan. Trace or missing nutrient values are not treated as zero; fibre adequacy cannot be established from incomplete values.",
            "レシピと作り方は本プロジェクトのデモ用テンプレートです。価格は仮定の食費で実売価格ではありません。テンプレートの版と材料の原値を献立とともに保存します。微量・欠損値はゼロ扱いせず、不完全な値から食物繊維の充足は判定できません。",
          )}
        </p>
      </section>
    </div>
  );
}
