import {
  createContext,
  useContext,
  useEffect,
  useState,
  type FormEvent,
} from "react";
import { Navigate, NavLink, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Pagination,
  TextField,
} from "@mui/material";
import { api } from "./api";
import type { Lang } from "./i18n";
import {
  adminText,
  adminRole,
  localizedName,
  localizedRecipeImage,
} from "./adminI18n";
const AdminLanguage = createContext<Lang>("zh");
function useAdminText() {
  const lang = useContext(AdminLanguage);
  const t = (text: string, values?: Record<string, string | number>) =>
    adminText(lang, text, values);
  return { lang, t };
}

const sections: Record<
  string,
  { permission: string; titles: [string, string, string] }
> = {
  users: {
    permission: "users.manage",
    titles: ["用户管理", "Users", "ユーザー管理"],
  },
  recipes: {
    permission: "recipes.manage",
    titles: ["菜单管理", "Recipes", "献立管理"],
  },
  knowledge: {
    permission: "knowledge.manage",
    titles: ["知识库管理", "Knowledge base", "知識ベース管理"],
  },
};
type Msg = { severity: "success" | "error"; text: string } | null;
const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const blank3 = () => ({ zh: "", en: "", ja: "" });

export function AdminPage({ user, lang }: { user: any; lang: Lang }) {
  const t = (text: string) => adminText(lang, text);
  const { section = "users" } = useParams();
  const allowed = Object.entries(sections).filter(([, item]) =>
    user.permissions?.includes(item.permission),
  );
  if (!allowed.length)
    return <Alert severity="error">{t("没有管理权限。")}</Alert>;
  if (
    !sections[section] ||
    !user.permissions.includes(sections[section].permission)
  )
    return <Navigate to={"/admin/" + allowed[0][0]} replace />;
  const title = (item: (typeof sections)[string]) =>
    item.titles[lang === "zh" ? 0 : lang === "en" ? 1 : 2];
  return (
    <AdminLanguage.Provider value={lang}>
      <div className="admin-page">
        <div className="page-title">
          <div>
            <h1>{title(sections[section])}</h1>
            <p>{t("管理账号、菜谱与资料；修改会同步到推荐服务。")}</p>
          </div>
        </div>
        <nav className="admin-tabs" aria-label={t("管理菜单")}>
          {allowed.map(([key, item]) => (
            <NavLink key={key} to={"/admin/" + key}>
              {title(item)}
            </NavLink>
          ))}
        </nav>
        {section === "users" ? (
          <Users user={user} />
        ) : section === "recipes" ? (
          <Recipes />
        ) : (
          <Knowledge />
        )}
      </div>
    </AdminLanguage.Provider>
  );
}

function Notice({ message }: { message: Msg }) {
  const { t } = useAdminText();
  return message ? (
    <Alert severity={message.severity} className="admin-notice">
      {t(message.text)}
    </Alert>
  ) : null;
}

function Users({ user }: { user: any }) {
  const { lang, t } = useAdminText();
  const [rows, setRows] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState<Msg>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState<any>(null);
  const [secret, setSecret] = useState("");
  const [resetTarget, setResetTarget] = useState<any>(null);
  const canRoles = user.permissions.includes("roles.manage");
  async function load() {
    setLoading(true);
    try {
      const [list, roleData] = await Promise.all([
        api(`/admin/users?q=${encodeURIComponent(q)}&offset=${offset}`),
        api("/admin/roles"),
      ]);
      setRows(list.users);
      setTotal(list.total);
      setRoles(roleData.roles);
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [q, offset]);
  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      if (editor.id) {
        await api(`/admin/users/${editor.id}`, "PATCH", {
          enabled: editor.enabled,
          roles: editor.roles,
        });
      } else {
        const result = await api("/admin/users", "POST", {
          login_id: editor.login_id,
          roles: editor.roles,
        });
        setSecret(`${result.user.login_id}\n${result.initial_password}`);
      }
      setEditor(null);
      setMessage({
        severity: "success",
        text: "账号已保存。角色或状态变更后，原登录会话已失效。",
      });
      await load();
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    setBusy(true);
    try {
      const result = await api(
        `/admin/users/${resetTarget.id}/reset-password`,
        "POST",
        {},
      );
      setSecret(`${resetTarget.login_id}\n${result.initial_password}`);
      setResetTarget(null);
      setMessage({
        severity: "success",
        text: "密码已重置，原登录会话已失效。",
      });
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Notice message={message} />
      <div className="admin-toolbar">
        <TextField
          label={t("搜索登录ID")}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
        />
        <Button
          variant="contained"
          onClick={() =>
            setEditor({ login_id: "", roles: ["user"], enabled: true })
          }
        >
          {t("新增用户")}
        </Button>
      </div>
      {loading && <CircularProgress size={20} />}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("登录ID")}</th>
              <th>{t("角色")}</th>
              <th>{t("状态")}</th>
              <th>{t("创建时间")}</th>
              <th>{t("操作")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  {row.login_id}
                  {row.id === user.id ? t("（当前账号）") : ""}
                </td>
                <td>
                  {row.roles
                    .map((id: string) =>
                      adminRole(lang, id, roles.find((r) => r.id === id)?.name),
                    )
                    .join(lang === "en" ? ", " : "、")}
                </td>
                <td>{row.enabled ? t("启用") : t("已禁用")}</td>
                <td>
                  {new Date(row.created_at).toLocaleDateString(
                    lang === "zh" ? "zh-CN" : lang === "ja" ? "ja-JP" : "en-GB",
                  )}
                </td>
                <td>
                  <Button
                    onClick={() => setEditor({ ...row })}
                    disabled={
                      !canRoles && row.permissions.includes("roles.manage")
                    }
                  >
                    {t("编辑")}
                  </Button>
                  <Button
                    onClick={() => setResetTarget(row)}
                    disabled={
                      row.id === user.id ||
                      (!canRoles && row.permissions.includes("roles.manage"))
                    }
                  >
                    {t("重置密码")}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="admin-pagination">
        <span>{t("共 {count} 个账号", { count: total })}</span>
        <Button disabled={!offset} onClick={() => setOffset(offset - 50)}>
          {t("上一页")}
        </Button>
        <Button
          disabled={offset + 50 >= total}
          onClick={() => setOffset(offset + 50)}
        >
          {t("下一页")}
        </Button>
      </div>
      <Dialog
        open={!!editor}
        onClose={() => !busy && setEditor(null)}
        maxWidth="sm"
        fullWidth
      >
        {editor && (
          <form onSubmit={save}>
            <DialogTitle>
              {editor.id ? t("编辑用户") : t("新增用户")}
            </DialogTitle>
            <DialogContent className="admin-form">
              <TextField
                label={t("登录ID")}
                required
                disabled={!!editor.id}
                value={editor.login_id}
                onChange={(e) =>
                  setEditor({ ...editor, login_id: e.target.value })
                }
              />
              <p className="muted">
                {t("新账号自动生成随机初始密码，保存后仅显示一次。")}
              </p>
              <fieldset>
                <legend>{t("角色与权限")}</legend>
                {roles.map((role) => (
                  <FormControlLabel
                    key={role.id}
                    control={
                      <Checkbox
                        checked={editor.roles.includes(role.id)}
                        disabled={!canRoles || editor.id === user.id}
                        onChange={(e) =>
                          setEditor({
                            ...editor,
                            roles: e.target.checked
                              ? [...editor.roles, role.id]
                              : editor.roles.filter(
                                  (r: string) => r !== role.id,
                                ),
                          })
                        }
                      />
                    }
                    label={adminRole(lang, role.id, role.name)}
                  />
                ))}
              </fieldset>
              {!!editor.id && (
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={editor.enabled}
                      disabled={editor.id === user.id}
                      onChange={(e) =>
                        setEditor({ ...editor, enabled: e.target.checked })
                      }
                    />
                  }
                  label={t("启用账号")}
                />
              )}
              <Notice
                message={message?.severity === "error" ? message : null}
              />
            </DialogContent>
            <DialogActions>
              <Button disabled={busy} onClick={() => setEditor(null)}>
                {t("取消")}
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={busy || !editor.roles.length}
              >
                {t("保存")}
              </Button>
            </DialogActions>
          </form>
        )}
      </Dialog>
      <Dialog
        open={!!resetTarget}
        onClose={() => !busy && setResetTarget(null)}
      >
        <DialogTitle>
          {t("重置 {id} 的密码？", { id: resetTarget?.login_id ?? "" })}
        </DialogTitle>
        <DialogContent>
          {t("将生成新的随机密码，并使该账号现有登录会话失效。")}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(null)} disabled={busy}>
            {t("取消")}
          </Button>
          <Button onClick={reset} disabled={busy}>
            {t("确认重置")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={!!secret} onClose={() => setSecret("")}>
        <DialogTitle>{t("请保存初始登录信息")}</DialogTitle>
        <DialogContent>
          <p>{t("关闭后不会再次显示密码，请通过可信方式交给账号使用者。")}</p>
          <pre className="admin-secret">{secret}</pre>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSecret("")}>{t("已保存，关闭")}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

async function fileBody(file: File, limit: number) {
  if (file.size > limit)
    throw new Error(`文件不能超过 ${limit / 1024 / 1024} MB`);
  const content = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  });
  return { filename: file.name, content_base64: content };
}

function Recipes() {
  const { lang, t } = useAdminText();
  const [rows, setRows] = useState<any[]>([]);
  const [foods, setFoods] = useState<any[]>([]);
  const [editor, setEditor] = useState<any>(null);
  const [message, setMessage] = useState<Msg>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [mealFilter, setMealFilter] = useState("all");
  const [page, setPage] = useState(1);
  const filtered = rows.filter(
    (row) =>
      (mealFilter === "all" || row.meal === mealFilter) &&
      [row.id, ...Object.values(row.name), ...(row.data?.search_keywords ?? [])].some((name) =>
        String(name)
          .toLocaleLowerCase()
          .includes(query.trim().toLocaleLowerCase()),
      ),
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / 24));
  const currentPage = Math.min(page, pageCount);
  async function load() {
    try {
      const data = await api("/admin/recipes");
      setRows(data.recipes);
      setFoods(data.ingredients);
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    }
  }
  useEffect(() => {
    void load();
  }, []);
  function open(row?: any) {
    setMessage(null);
    setEditor(
      row
        ? {
            ...row,
            name: { ...row.name },
            data: { ...row.data, instructions: { ...row.data.instructions } },
            parts: Object.entries(row.ingredients).map(([code, grams]) => ({
              code,
              grams,
            })),
          }
        : {
            name: blank3(),
            meal: "breakfast",
            enabled: true,
            data: { minutes: 20, instructions: blank3() },
            parts: [{ code: foods[0]?.code ?? "", grams: 100 }],
          },
    );
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      if (
        new Set(editor.parts.map((p: any) => p.code)).size !==
        editor.parts.length
      )
        throw new Error("请合并重复配料");
      const payload = {
        name: editor.name,
        meal: editor.meal,
        enabled: editor.enabled,
        expected_version: editor.version ?? null,
        minutes: Number(editor.data.minutes),
        instructions: editor.data.instructions,
        ingredients: Object.fromEntries(
          editor.parts.map((p: any) => [p.code, Number(p.grams)]),
        ),
      };
      await api(
        editor.id ? `/admin/recipes/${editor.id}` : "/admin/recipes",
        editor.id ? "PATCH" : "POST",
        payload,
      );
      setEditor(null);
      setMessage({
        severity: "success",
        text: "菜谱已保存，首页推荐缓存已刷新。",
      });
      await load();
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  async function image(file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      const row = await api(`/admin/recipes/${editor.id}/image`, "POST", {
        ...(await fileBody(file, 4 * 1024 * 1024)),
        expected_version: editor.version,
      });
      // Preserve unsaved text edits while advancing the version after image replacement.
      setEditor((current: any) => ({
        ...current,
        version: row.version,
        data: { ...current.data, image: row.data.image },
      }));
      setMessage({ severity: "success", text: "图片已替换。" });
      await load();
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Notice message={message} />
      <div className="admin-toolbar">
        <p>
          {t("{count} 道菜谱 · 停用后不再用于新推荐，历史方案保留。", {
            count: rows.length,
          })}
        </p>
        <Button variant="contained" onClick={() => open()}>
          {t("新增菜谱")}
        </Button>
      </div>
      <div className="admin-toolbar admin-recipe-filters">
        <TextField
          label={t("搜索菜名或编号")}
          size="small"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
        />
        <TextField
          label={t("筛选餐次")}
          select
          size="small"
          value={mealFilter}
          onChange={(e) => {
            setMealFilter(e.target.value);
            setPage(1);
          }}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="all">{t("全部餐次")}</MenuItem>
          <MenuItem value="breakfast">{t("早餐")}</MenuItem>
          <MenuItem value="lunch">{t("午餐")}</MenuItem>
          <MenuItem value="dinner">{t("晚餐")}</MenuItem>
        </TextField>
        <p>{t("共 {count} 道 · 每页 24 道", { count: filtered.length })}</p>
      </div>
      <div className="admin-recipe-grid">
        {filtered.slice((currentPage - 1) * 24, currentPage * 24).map((row) => (
          <article className="admin-recipe" key={row.id}>
            <img
              src={localizedRecipeImage(row.data.image, lang)}
              alt={localizedName(row.name, lang)}
              loading="lazy"
            />
            <div>
              <h3>{localizedName(row.name, lang)}</h3>
              <p>
                {
                  (
                    {
                      breakfast: t("早餐"),
                      lunch: t("午餐"),
                      dinner: t("晚餐"),
                    } as any
                  )[row.meal]
                }{" "}
                · {row.enabled ? t("启用") : t("已停用")} ·{" "}
                {t("{count} 分钟", { count: row.data.minutes })}
              </p>
              <Button onClick={() => open(row)}>{t("编辑菜谱与图片")}</Button>
            </div>
          </article>
        ))}
      </div>
      {filtered.length === 0 && <p>{t("没有符合条件的菜谱。")}</p>}
      {pageCount > 1 && (
        <Pagination
          count={pageCount}
          page={currentPage}
          onChange={(_, value) => setPage(value)}
          aria-label={t("菜谱分页")}
          getItemAriaLabel={(type, page, selected) =>
            type === "page"
              ? t(selected ? "当前第 {page} 页" : "前往第 {page} 页", {
                  page: page ?? 1,
                })
              : t(
                  {
                    first: t("第一页"),
                    last: t("最后一页"),
                    next: t("下一页"),
                    previous: t("上一页"),
                    "start-ellipsis": t("更多页"),
                    "end-ellipsis": t("更多页"),
                  }[type],
                )
          }
          sx={{ my: 3 }}
        />
      )}
      <Dialog
        open={!!editor}
        onClose={() => !busy && setEditor(null)}
        maxWidth="md"
        fullWidth
      >
        {editor && (
          <form onSubmit={save}>
            <DialogTitle>
              {editor.id ? t("编辑菜谱") : t("新增菜谱")}
            </DialogTitle>
            <DialogContent className="admin-form">
              <Notice message={message} />
              <div className="admin-form-grid">
                {(["zh", "en", "ja"] as const).map((contentLang) => (
                  <TextField
                    key={contentLang}
                    label={t("名称（{language}）", {
                      language: { zh: t("中文"), en: t("英文"), ja: t("日文") }[
                        contentLang
                      ],
                    })}
                    required
                    value={editor.name[contentLang]}
                    onChange={(e) =>
                      setEditor({
                        ...editor,
                        name: { ...editor.name, [contentLang]: e.target.value },
                      })
                    }
                  />
                ))}
              </div>
              <div className="admin-form-grid">
                <TextField
                  select
                  label={t("餐次")}
                  value={editor.meal}
                  onChange={(e) =>
                    setEditor({ ...editor, meal: e.target.value })
                  }
                >
                  <MenuItem value="breakfast">{t("早餐")}</MenuItem>
                  <MenuItem value="lunch">{t("午餐")}</MenuItem>
                  <MenuItem value="dinner">{t("晚餐")}</MenuItem>
                </TextField>
                <TextField
                  type="number"
                  label={t("准备时间（分钟）")}
                  required
                  inputProps={{ min: 1, max: 240 }}
                  value={editor.data.minutes}
                  onChange={(e) =>
                    setEditor({
                      ...editor,
                      data: { ...editor.data, minutes: e.target.value },
                    })
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={editor.enabled}
                      onChange={(e) =>
                        setEditor({ ...editor, enabled: e.target.checked })
                      }
                    />
                  }
                  label={t("启用菜谱")}
                />
              </div>
              <h3>{t("菜谱图片")}</h3>
              {editor.data.image && (
                <img
                  className="admin-image-preview"
                  src={localizedRecipeImage(editor.data.image, lang)}
                  alt={localizedName(editor.name, lang)}
                />
              )}
              <Button component="label" disabled={busy || !editor.id}>
                {t("上传替换图片")}
                <input
                  hidden
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    void image(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </Button>
              <p className="muted">
                {t("PNG、JPEG 或 WebP，不超过4MB。新菜谱请先保存再上传图片。")}
              </p>
              <h3>{t("配料与可食重量")}</h3>
              <p className="muted">
                {t("营养值沿用食品数据库，按食品所列的生熟状态填写克数。")}
              </p>
              {editor.parts.map((part: any, index: number) => (
                <div className="admin-ingredient-row" key={index}>
                  <TextField
                    select
                    label={t("配料")}
                    value={part.code}
                    onChange={(e) =>
                      setEditor({
                        ...editor,
                        parts: editor.parts.map((p: any, i: number) =>
                          i === index ? { ...p, code: e.target.value } : p,
                        ),
                      })
                    }
                  >
                    {foods.map((f) => (
                      <MenuItem key={f.code} value={f.code}>
                        {localizedName(f.name, lang)} · {f.code}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label={t("克")}
                    type="number"
                    required
                    inputProps={{ min: 0.1, max: 2000, step: 0.1 }}
                    value={part.grams}
                    onChange={(e) =>
                      setEditor({
                        ...editor,
                        parts: editor.parts.map((p: any, i: number) =>
                          i === index ? { ...p, grams: e.target.value } : p,
                        ),
                      })
                    }
                  />
                  <Button
                    disabled={editor.parts.length <= 1}
                    onClick={() =>
                      setEditor({
                        ...editor,
                        parts: editor.parts.filter(
                          (_: any, i: number) => i !== index,
                        ),
                      })
                    }
                  >
                    {t("移除")}
                  </Button>
                </div>
              ))}
              <Button
                disabled={editor.parts.length >= foods.length}
                onClick={() =>
                  setEditor({
                    ...editor,
                    parts: [
                      ...editor.parts,
                      {
                        code: foods.find(
                          (f) =>
                            !editor.parts.some((p: any) => p.code === f.code),
                        )?.code,
                        grams: 100,
                      },
                    ],
                  })
                }
              >
                {t("添加配料")}
              </Button>
              {(["zh", "en", "ja"] as const).map((contentLang) => (
                <TextField
                  key={contentLang}
                  label={t("做法（{language}）", {
                    language: { zh: t("中文"), en: t("英文"), ja: t("日文") }[
                      contentLang
                    ],
                  })}
                  multiline
                  minRows={3}
                  required
                  value={editor.data.instructions[contentLang]}
                  onChange={(e) =>
                    setEditor({
                      ...editor,
                      data: {
                        ...editor.data,
                        instructions: {
                          ...editor.data.instructions,
                          [contentLang]: e.target.value,
                        },
                      },
                    })
                  }
                />
              ))}
            </DialogContent>
            <DialogActions>
              <Button disabled={busy} onClick={() => setEditor(null)}>
                {t("关闭")}
              </Button>
              <Button variant="contained" type="submit" disabled={busy}>
                {t("保存菜谱")}
              </Button>
            </DialogActions>
          </form>
        )}
      </Dialog>
    </>
  );
}

const kinds: Record<string, string> = {
  guideline_commentary: "指南解读",
  guideline_chapter: "指南章节",
  food_composition_reference: "食品成分资料",
  historical_guideline: "历史指南（隔离）",
  dietary_reference_intakes: "膳食摄入标准",
  reference: "一般参考资料",
};
function Knowledge() {
  const { t } = useAdminText();
  const [documents, setDocuments] = useState<any[]>([]);
  const [uploads, setUploads] = useState<any[]>([]);
  const [editor, setEditor] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<Msg>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<any>(null);
  async function load() {
    try {
      const data = await api("/admin/knowledge");
      setDocuments(data.documents);
      setUploads(data.uploads);
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const pending = uploads.some((u) =>
    ["queued", "processing"].includes(u.status),
  );
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(() => {
      void load();
    }, 5000);
    return () => clearInterval(timer);
  }, [pending]);
  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const metadata = {
        title: editor.title,
        publisher: editor.publisher,
        edition: editor.edition,
        source_kind: editor.source_kind,
        warning: editor.warning,
      };
      if (editor.id) {
        await api(`/admin/knowledge/${editor.id}`, "PATCH", {
          ...metadata,
          enabled: editor.enabled,
        });
        setMessage({ severity: "success", text: "文档设置已保存。" });
      } else {
        if (!file) throw new Error("请选择PDF文件");
        await api("/admin/knowledge/uploads", "POST", {
          ...metadata,
          ...(await fileBody(file, 12 * 1024 * 1024)),
        });
        setMessage({
          severity: "success",
          text: "文档已排队导入。导入完成后请查看提取内容，再启用检索。",
        });
      }
      setEditor(null);
      setFile(null);
      await load();
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  async function page(doc: any, number = 1) {
    try {
      const result = await api(
        `/admin/knowledge/${doc.id}/pages?page=${number}`,
      );
      setPreview({ doc, ...result });
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    }
  }
  async function retry(id: string) {
    setBusy(true);
    try {
      await api(`/admin/knowledge/uploads/${id}/retry`, "POST", {});
      await load();
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Notice message={message} />
      <div className="admin-toolbar">
        <p>{t("新文档导入后默认停用，启用后才参与知识检索。")}</p>
        <Button
          variant="contained"
          onClick={() => {
            setFile(null);
            setMessage(null);
            setEditor({
              title: "",
              publisher: "",
              edition: "",
              source_kind: "reference",
              warning: t("管理员上传资料，尚未完成逐页人工审核。"),
              enabled: false,
            });
          }}
        >
          {t("上传PDF")}
        </Button>
        <Button onClick={load}>{t("刷新")}</Button>
      </div>
      {!!uploads.length && (
        <section className="admin-imports">
          <h3>{t("导入任务")}</h3>
          {uploads.map((upload) => (
            <div key={upload.id}>
              <strong>{upload.metadata.title}</strong>
              <span>
                {
                  (
                    {
                      queued: t("等待导入"),
                      processing: t("正在提取与向量化"),
                      ready: t("导入完成"),
                      failed: t("导入失败"),
                    } as any
                  )[upload.status]
                }
              </span>
              {upload.error && <small>{t(upload.error)}</small>}
              {upload.status === "failed" && (
                <Button disabled={busy} onClick={() => retry(upload.id)}>
                  {t("重试")}
                </Button>
              )}
            </div>
          ))}
        </section>
      )}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t("文档")}</th>
              <th>{t("类型")}</th>
              <th>{t("页数 / 片段")}</th>
              <th>{t("状态")}</th>
              <th>{t("操作")}</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <strong>{doc.title}</strong>
                  <small>
                    {doc.publisher} · {doc.edition}
                  </small>
                </td>
                <td>{t(kinds[doc.source_kind] ?? doc.source_kind)}</td>
                <td>
                  {doc.page_count} / {doc.chunks}
                  <small>
                    {t("隔离页：{count}", { count: doc.quarantined_pages })}
                  </small>
                </td>
                <td>
                  {doc.status === "ready"
                    ? doc.enabled
                      ? t("参与检索")
                      : t("已停用")
                    : doc.status === "quarantined"
                      ? t("已隔离")
                      : t("导入中")}
                </td>
                <td>
                  <Button
                    onClick={() => {
                      setMessage(null);
                      setEditor({
                        ...doc,
                        enabled: doc.status === "ready" && doc.enabled,
                      });
                    }}
                  >
                    {t("编辑")}
                  </Button>
                  <Button onClick={() => page(doc)}>{t("查看原文")}</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Dialog
        open={!!editor}
        onClose={() => !busy && setEditor(null)}
        maxWidth="sm"
        fullWidth
      >
        {editor && (
          <form onSubmit={save}>
            <DialogTitle>
              {editor.id ? t("编辑文档") : t("上传知识库文档")}
            </DialogTitle>
            <DialogContent className="admin-form">
              <Notice
                message={message?.severity === "error" ? message : null}
              />
              {(["title", "publisher", "edition"] as const).map((key) => (
                <TextField
                  key={key}
                  label={
                    {
                      title: t("文档标题"),
                      publisher: t("出版机构"),
                      edition: t("版本 / 年份"),
                    }[key]
                  }
                  required
                  value={editor[key]}
                  onChange={(e) =>
                    setEditor({ ...editor, [key]: e.target.value })
                  }
                />
              ))}
              <TextField
                select
                label={t("资料类型")}
                value={editor.source_kind}
                onChange={(e) =>
                  setEditor({ ...editor, source_kind: e.target.value })
                }
              >
                {Object.entries(kinds).map(([id, label]) => (
                  <MenuItem key={id} value={id}>
                    {t(label)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label={t("适用范围与资料说明")}
                multiline
                minRows={3}
                value={editor.warning}
                onChange={(e) =>
                  setEditor({ ...editor, warning: e.target.value })
                }
              />
              {editor.id ? (
                <FormControlLabel
                  label={t("参与知识检索")}
                  control={
                    <Checkbox
                      checked={editor.enabled && editor.status === "ready"}
                      disabled={editor.status !== "ready"}
                      onChange={(e) =>
                        setEditor({ ...editor, enabled: e.target.checked })
                      }
                    />
                  }
                />
              ) : (
                <>
                  <Button component="label">
                    {t("选择PDF")}
                    <input
                      hidden
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                  </Button>
                  <span>{file?.name ?? t("尚未选择文件")}</span>
                  <p className="muted">
                    {t(
                      "不超过12MB、200页。当前提取PDF文字层；扫描件需要先完成OCR，缺少可提取文字的页面会隔离。",
                    )}
                  </p>
                </>
              )}
            </DialogContent>
            <DialogActions>
              <Button disabled={busy} onClick={() => setEditor(null)}>
                {t("取消")}
              </Button>
              <Button type="submit" variant="contained" disabled={busy}>
                {busy ? t("处理中…") : editor.id ? t("保存") : t("上传并导入")}
              </Button>
            </DialogActions>
          </form>
        )}
      </Dialog>
      <Dialog
        open={!!preview}
        onClose={() => setPreview(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{preview?.doc.title}</DialogTitle>
        <DialogContent>
          <div className="admin-pagination">
            <Button
              disabled={preview?.pdf_page <= 1}
              onClick={() => page(preview.doc, preview.pdf_page - 1)}
            >
              {t("上一页")}
            </Button>
            <span>
              PDF {preview?.pdf_page} / {preview?.doc.page_count}
            </span>
            <Button
              disabled={preview?.pdf_page >= preview?.doc.page_count}
              onClick={() => page(preview.doc, preview.pdf_page + 1)}
            >
              {t("下一页")}
            </Button>
          </div>
          <p>
            {preview?.status === "eligible" ? t("可检索页面") : t("隔离页面")} ·{" "}
            {preview?.reason}
          </p>
          <pre className="admin-page-text">{preview?.content}</pre>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreview(null)}>{t("关闭")}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
