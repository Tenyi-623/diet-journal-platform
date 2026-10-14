import type { Lang } from "./i18n";

// Chinese keys also match existing server messages. Persisted document text,
// recipe translations and user-entered values are never rewritten by this map.
export const adminWords: Record<string, [string, string]> = {
  更多页: ["More pages", "その他のページ"],
  "解析或模型向量化失败，请检查文件与模型服务后重试": [
    "Parsing or indexing failed. Check the file and model service, then retry.",
    "解析または索引作成に失敗しました。ファイルとモデルサービスを確認して再試行してください。",
  ],
  "没有管理权限。": [
    "You do not have administration access.",
    "管理権限がありません。",
  ],
  "管理账号、菜谱与资料；修改会同步到推荐服务。": [
    "Manage accounts, recipes and sources. Changes are reflected in recommendations.",
    "アカウント・献立・資料を管理します。変更は提案サービスに反映されます。",
  ],
  管理菜单: ["Administration", "管理メニュー"],
  用户管理: ["Users", "ユーザー管理"],
  菜单管理: ["Recipes", "献立管理"],
  知识库管理: ["Knowledge base", "知識ベース管理"],
  "账号已保存。角色或状态变更后，原登录会话已失效。": [
    "Account saved. Role or status changes invalidate previous sessions.",
    "アカウントを保存しました。権限・状態の変更後は以前のログインが無効になります。",
  ],
  "密码已重置，原登录会话已失效。": [
    "Password reset. Previous sessions are now invalid.",
    "パスワードをリセットし、以前のログインを無効にしました。",
  ],
  搜索登录ID: ["Search login ID", "ログインIDで検索"],
  新增用户: ["Add user", "ユーザーを追加"],
  登录ID: ["Login ID", "ログインID"],
  角色: ["Roles", "ロール"],
  状态: ["Status", "状態"],
  创建时间: ["Created", "作成日"],
  操作: ["Actions", "操作"],
  "（当前账号）": [" (current account)", "（現在のアカウント）"],
  启用: ["Enabled", "有効"],
  已禁用: ["Disabled", "無効"],
  已停用: ["Disabled", "無効"],
  编辑: ["Edit", "編集"],
  重置密码: ["Reset password", "パスワードをリセット"],
  "共 {count} 个账号": ["{count} accounts", "全{count}アカウント"],
  上一页: ["Previous page", "前のページ"],
  下一页: ["Next page", "次のページ"],
  编辑用户: ["Edit user", "ユーザーを編集"],
  "新账号自动生成随机初始密码，保存后仅显示一次。": [
    "A random initial password is generated for new accounts and shown once after saving.",
    "新規アカウントにはランダムな初期パスワードを生成し、保存後に一度だけ表示します。",
  ],
  角色与权限: ["Roles and permissions", "ロールと権限"],
  启用账号: ["Enable account", "アカウントを有効にする"],
  取消: ["Cancel", "キャンセル"],
  保存: ["Save", "保存"],
  "重置 {id} 的密码？": [
    "Reset the password for {id}?",
    "{id} のパスワードをリセットしますか？",
  ],
  "将生成新的随机密码，并使该账号现有登录会话失效。": [
    "A new random password will be generated and this account's current sessions invalidated.",
    "新しいランダムなパスワードを生成し、このアカウントの現在のログインを無効にします。",
  ],
  确认重置: ["Confirm reset", "リセットを確定"],
  请保存初始登录信息: [
    "Save the initial login details",
    "初期ログイン情報を保存してください",
  ],
  "关闭后不会再次显示密码，请通过可信方式交给账号使用者。": [
    "The password will not be shown again after closing. Share it securely with the account holder.",
    "閉じるとパスワードは再表示されません。信頼できる方法で利用者に渡してください。",
  ],
  "已保存，关闭": ["Saved, close", "保存済み・閉じる"],
  读取文件失败: [
    "Could not read the file.",
    "ファイルを読み取れませんでした。",
  ],
  "文件不能超过 {limit} MB": [
    "The file must not exceed {limit} MB.",
    "ファイルは{limit}MB以下にしてください。",
  ],
  请合并重复配料: [
    "Combine duplicate ingredients before saving.",
    "重複する材料をまとめてください。",
  ],
  "菜谱已保存，首页推荐缓存已刷新。": [
    "Recipe saved. Home recommendations have been refreshed.",
    "献立を保存し、ホームの提案を更新しました。",
  ],
  "图片已替换。": ["Image replaced.", "画像を変更しました。"],
  "{count} 道菜谱 · 停用后不再用于新推荐，历史方案保留。": [
    "{count} recipes · Disabled recipes are excluded from new recommendations; history is retained.",
    "全{count}品・無効にした献立は新規提案から除外され、履歴は残ります。",
  ],
  新增菜谱: ["Add recipe", "献立を追加"],
  搜索菜名或编号: ["Search recipe name or ID", "献立名・IDで検索"],
  筛选餐次: ["Filter by meal", "食事区分で絞り込み"],
  全部餐次: ["All meals", "すべての食事"],
  早餐: ["Breakfast", "朝食"],
  午餐: ["Lunch", "昼食"],
  晚餐: ["Dinner", "夕食"],
  "共 {count} 道 · 每页 24 道": [
    "{count} recipes · 24 per page",
    "全{count}品・1ページ24品",
  ],
  "{count} 分钟": ["{count} min", "{count}分"],
  编辑菜谱与图片: ["Edit recipe and image", "献立・画像を編集"],
  "没有符合条件的菜谱。": [
    "No matching recipes.",
    "条件に一致する献立はありません。",
  ],
  菜谱分页: ["Recipe pagination", "献立のページ切り替え"],
  "当前第 {page} 页": ["Current page, {page}", "現在のページ、{page}"],
  "前往第 {page} 页": ["Go to page {page}", "{page}ページへ"],
  第一页: ["First page", "最初のページ"],
  最后一页: ["Last page", "最後のページ"],
  编辑菜谱: ["Edit recipe", "献立を編集"],
  "名称（{language}）": ["Name ({language})", "名前（{language}）"],
  中文: ["Chinese", "中国語"],
  英文: ["English", "英語"],
  日文: ["Japanese", "日本語"],
  餐次: ["Meal", "食事区分"],
  "准备时间（分钟）": ["Preparation time (minutes)", "準備時間（分）"],
  启用菜谱: ["Enable recipe", "献立を有効にする"],
  菜谱图片: ["Recipe image", "献立の画像"],
  上传替换图片: ["Upload replacement image", "画像をアップロードして変更"],
  "PNG、JPEG 或 WebP，不超过4MB。新菜谱请先保存再上传图片。": [
    "PNG, JPEG or WebP, up to 4 MB. Save a new recipe before uploading its image.",
    "PNG・JPEG・WebP、4MBまで。新規献立は保存してから画像をアップロードしてください。",
  ],
  配料与可食重量: ["Ingredients and edible weights", "材料と可食重量"],
  "营养值沿用食品数据库，按食品所列的生熟状态填写克数。": [
    "Nutrition comes from the food database. Enter grams in each food's specified raw or cooked state.",
    "栄養値は食品データベースを使用します。各食品の生・調理済みの表記に合わせてグラム数を入力してください。",
  ],
  配料: ["Ingredient", "材料"],
  克: ["Grams", "グラム"],
  移除: ["Remove", "削除"],
  添加配料: ["Add ingredient", "材料を追加"],
  "做法（{language}）": ["Instructions ({language})", "作り方（{language}）"],
  关闭: ["Close", "閉じる"],
  保存菜谱: ["Save recipe", "献立を保存"],
  指南解读: ["Guideline commentary", "ガイドライン解説"],
  指南章节: ["Guideline chapter", "ガイドラインの章"],
  食品成分资料: ["Food composition reference", "食品成分資料"],
  "历史指南（隔离）": [
    "Historical guideline (quarantined)",
    "旧ガイドライン（隔離）",
  ],
  膳食摄入标准: ["Dietary reference intakes", "食事摂取基準"],
  一般参考资料: ["General reference", "一般参考資料"],
  "文档设置已保存。": [
    "Document settings saved.",
    "資料の設定を保存しました。",
  ],
  请选择PDF文件: ["Select a PDF file.", "PDFファイルを選択してください。"],
  "文档已排队导入。导入完成后请查看提取内容，再启用检索。": [
    "Document queued for import. Review the extracted content before enabling retrieval.",
    "資料をインポート待ちに追加しました。完了後に抽出内容を確認してから検索を有効にしてください。",
  ],
  "新文档导入后默认停用，启用后才参与知识检索。": [
    "New imports are disabled by default. Enable them to include them in knowledge retrieval.",
    "新規資料はインポート後、初期状態では無効です。有効にすると知識検索の対象になります。",
  ],
  "管理员上传资料，尚未完成逐页人工审核。": [
    "Administrator-uploaded material; page-by-page human review is not complete.",
    "管理者がアップロードした資料です。ページごとの目視確認は未完了です。",
  ],
  上传PDF: ["Upload PDF", "PDFをアップロード"],
  刷新: ["Refresh", "更新"],
  导入任务: ["Import jobs", "インポート処理"],
  等待导入: ["Queued", "待機中"],
  正在提取与向量化: ["Extracting and indexing", "抽出・索引作成中"],
  导入完成: ["Imported", "インポート完了"],
  导入失败: ["Import failed", "インポート失敗"],
  重试: ["Retry", "再試行"],
  文档: ["Document", "資料"],
  类型: ["Type", "種類"],
  "页数 / 片段": ["Pages / chunks", "ページ / 断片"],
  "隔离页：{count}": ["Quarantined pages: {count}", "隔離ページ：{count}"],
  参与检索: ["Included in retrieval", "検索対象"],
  已隔离: ["Quarantined", "隔離済み"],
  导入中: ["Importing", "インポート中"],
  查看原文: ["View source text", "原文を表示"],
  编辑文档: ["Edit document", "資料を編集"],
  上传知识库文档: ["Upload knowledge document", "知識ベース資料をアップロード"],
  文档标题: ["Document title", "資料名"],
  出版机构: ["Publisher", "発行機関"],
  "版本 / 年份": ["Edition / year", "版 / 年"],
  资料类型: ["Source type", "資料の種類"],
  适用范围与资料说明: ["Scope and source notes", "適用範囲と資料の説明"],
  参与知识检索: ["Include in knowledge retrieval", "知識検索の対象にする"],
  选择PDF: ["Choose PDF", "PDFを選択"],
  尚未选择文件: ["No file selected", "ファイル未選択"],
  "不超过12MB、200页。当前提取PDF文字层；扫描件需要先完成OCR，缺少可提取文字的页面会隔离。":
    [
      "Up to 12 MB and 200 pages. Uses PDF text layers; scanned files need OCR first. Pages without extractable text are quarantined.",
      "12MB・200ページまで。PDFのテキストを抽出します。スキャン資料は事前にOCRが必要です。抽出できる文字のないページは隔離されます。",
    ],
  "处理中…": ["Processing…", "処理中…"],
  上传并导入: ["Upload and import", "アップロードしてインポート"],
  可检索页面: ["Retrievable page", "検索対象ページ"],
  隔离页面: ["Quarantined page", "隔離ページ"],
  普通用户: ["User", "一般ユーザー"],
  管理员: ["Administrator", "管理者"],
  用户管理员: ["User manager", "ユーザー管理担当"],
  菜谱管理员: ["Recipe editor", "献立管理担当"],
  知识库管理员: ["Knowledge editor", "知識ベース管理担当"],
  没有此管理功能的权限: [
    "You do not have permission for this action.",
    "この管理機能を操作する権限がありません。",
  ],
  未知角色: ["Unknown role.", "不明なロールです。"],
  不能分配管理角色: [
    "You cannot assign administrative roles.",
    "管理ロールを割り当てる権限がありません。",
  ],
  账号不存在: ["Account not found.", "アカウントが見つかりません。"],
  登录ID已存在: [
    "This login ID is already in use.",
    "このログインIDは既に使われています。",
  ],
  不能管理管理员账号: [
    "You cannot manage administrator accounts.",
    "管理者アカウントを操作する権限がありません。",
  ],
  不能禁用自己或修改自己的角色: [
    "You cannot disable yourself or change your own roles.",
    "自分のアカウントを無効にしたり、自分のロールを変更したりすることはできません。",
  ],
  必须保留至少一个启用的管理员: [
    "At least one enabled administrator must remain.",
    "少なくとも1人の有効な管理者が必要です。",
  ],
  请使用用户信息中的修改密码功能: [
    "Use Change password in your profile.",
    "ユーザー情報のパスワード変更を使用してください。",
  ],
  "配料需使用食品编号，重量须在0至2000g之间": [
    "Use food IDs and weights greater than 0 and at most 2,000 g.",
    "食品IDを使用し、重量は0g超・2000g以下にしてください。",
  ],
  单份总重量不能超过4000g: [
    "A serving must not exceed 4,000 g.",
    "1食分の総重量は4000g以下にしてください。",
  ],
  菜谱不存在: ["Recipe not found.", "献立が見つかりません。"],
  "菜谱已被修改，请刷新": [
    "This recipe has changed. Refresh before editing.",
    "献立が変更されています。更新してから編集してください。",
  ],
  只能使用已有结构化营养数据的配料: [
    "Use ingredients with existing structured nutrition data.",
    "構造化された栄養データのある材料を使用してください。",
  ],
  菜谱名称过长: ["The recipe name is too long.", "献立名が長すぎます。"],
  文件过大: ["The file is too large.", "ファイルが大きすぎます。"],
  文件编码无效: ["Invalid file encoding.", "ファイルのエンコードが無効です。"],
  文件为空或过大: [
    "The file is empty or too large.",
    "ファイルが空か、大きすぎます。",
  ],
  "仅支持PNG、JPEG、WebP，像素总数不能超过2000万": [
    "Use PNG, JPEG or WebP with no more than 20 million pixels.",
    "PNG・JPEG・WebP、2000万画素以下の画像を使用してください。",
  ],
  图片文件损坏或尺寸过大: [
    "The image is damaged or too large.",
    "画像が破損しているか、サイズが大きすぎます。",
  ],
  文档不存在: ["Document not found.", "資料が見つかりません。"],
  仅完整导入且通过提取检查的文档可以启用: [
    "Only fully imported documents that pass extraction checks can be enabled.",
    "インポートが完了し、抽出チェックを通過した資料のみ有効にできます。",
  ],
  页面不存在: ["Page not found.", "ページが見つかりません。"],
  请上传PDF文件: [
    "Upload a PDF file.",
    "PDFファイルをアップロードしてください。",
  ],
  该PDF已在知识库中: [
    "This PDF is already in the knowledge base.",
    "このPDFは既に知識ベースにあります。",
  ],
  "已有文档等待导入，请稍后上传": [
    "Documents are already queued. Try uploading later.",
    "インポート待ちの資料があります。しばらくしてからアップロードしてください。",
  ],
  "此文件已上传，请查看导入记录": [
    "This file was already uploaded. Check the import history.",
    "このファイルはアップロード済みです。インポート履歴を確認してください。",
  ],
  只有失败的导入任务可以重试: [
    "Only failed imports can be retried.",
    "失敗したインポートのみ再試行できます。",
  ],
  "仅支持未加密、1至200页的PDF": [
    "Use an unencrypted PDF with 1–200 pages.",
    "暗号化されていない1～200ページのPDFを使用してください。",
  ],
  "PDF文字过多，请拆分后上传": [
    "The PDF contains too much text. Split it before uploading.",
    "PDFの文字量が多すぎます。分割してアップロードしてください。",
  ],
  "PDF片段过多，请拆分后上传": [
    "The PDF creates too many chunks. Split it before uploading.",
    "PDFの断片数が多すぎます。分割してアップロードしてください。",
  ],
  "请检查表单填写内容。": [
    "Check the form fields and try again.",
    "フォームの入力内容を確認してください。",
  ],
  "Request failed": [
    "Request failed. Please try again.",
    "リクエストに失敗しました。再試行してください。",
  ],
  "Failed to fetch": [
    "Could not connect to the service.",
    "サービスに接続できませんでした。",
  ],
};

export function adminText(
  lang: Lang,
  text: string,
  values: Record<string, string | number> = {},
): string {
  if (lang === "zh" && text === "Request failed") return "请求失败，请重试。";
  if (lang === "zh" && text === "Failed to fetch") return "无法连接服务。";
  const fileSize = text.match(/^文件不能超过 (\d+(?:\.\d+)?) MB$/);
  if (fileSize)
    return adminText(lang, "文件不能超过 {limit} MB", { limit: fileSize[1] });
  // FastAPI validation errors use JSON rather than a display-ready message.
  if (text.startsWith("[")) {
    try {
      const errors = JSON.parse(text);
      if (
        Array.isArray(errors) &&
        errors.length &&
        errors.every((e) => Array.isArray(e.loc) && typeof e.msg === "string")
      ) {
        return errors
          .map((e) => {
            const message = e.msg.replace(/^Value error, /, "");
            return adminText(
              lang,
              adminWords[message] ? message : "请检查表单填写内容。",
            );
          })
          .filter((v, i, all) => all.indexOf(v) === i)
          .join(" ");
      }
    } catch {
      /* Unknown server text is left intact. */
    }
  }
  let translated =
    lang === "zh" ? text : (adminWords[text]?.[lang === "en" ? 0 : 1] ?? text);
  if (lang === "en" && Number(values.count) === 1) {
    translated = translated
      .replace("{count} recipes", "{count} recipe")
      .replace("{count} accounts", "{count} account");
  }
  return translated.replace(/\{(\w+)\}/g, (whole, key) =>
    values[key] === undefined ? whole : String(values[key]),
  );
}

export function localizedName(value: any, lang: Lang): string {
  if (typeof value === "string") return value;
  return (
    value?.[lang]?.trim() ||
    value?.zh?.trim() ||
    value?.en?.trim() ||
    value?.ja?.trim() ||
    ""
  );
}

export function adminRole(lang: Lang, id: string, fallback?: string): string {
  const roles: Record<string, string> = {
    user: "普通用户",
    admin: "管理员",
    user_manager: "用户管理员",
    recipe_editor: "菜谱管理员",
    knowledge_editor: "知识库管理员",
  };
  return adminText(lang, roles[id] ?? fallback ?? id);
}

export function localizedRecipeImage(image: string, lang: Lang): string {
  // Uploaded photos are language-neutral and their URLs must stay immutable.
  if (!image?.startsWith("/api/recipe-images/")) return image;
  return image.split("?")[0] + "?lang=" + lang;
}
