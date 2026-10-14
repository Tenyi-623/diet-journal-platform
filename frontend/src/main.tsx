import React, { createContext, useContext, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  useNavigate,
} from "react-router-dom";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Button,
  TextField,
  MenuItem,
  Alert,
  Checkbox,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Chip,
  LinearProgress,
} from "@mui/material";
import {
  Leaf,
  ArrowUpRight,
  ArrowRight,
  MessageCircle,
  UserRound,
  History,
  LogOut,
  Utensils,
  Clock,
  ChevronRight,
  Send,
  Plus,
  BookOpen,
  Settings2,
  Sun,
  Check,
  ShieldCheck,
} from "lucide-react";
import { api, setCSRF, requestKey } from "./api";
import { translate } from "./i18n";
import type { Lang } from "./i18n";
import { PlanExplanation } from "./PlanExplanation";
import { AdminPage } from "./Admin";
import "./style.css";
const theme = createTheme({
  palette: {
    primary: { main: "#285442" },
    background: { default: "#f8f7f3", paper: "#ffffff" },
  },
  typography: {
    fontFamily:
      'Inter, "Noto Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      styleOverrides: { root: { boxShadow: "none", padding: "10px 20px" } },
    },
    MuiTextField: { defaultProps: { size: "small", fullWidth: true } },
    MuiCheckbox: { styleOverrides: { root: { padding: 7 } } },
  },
});
type Context = {
  lang: Lang;
  setLang: (x: Lang) => void;
  t: (k: string) => string;
  user: any;
  logout: () => void;
};
const AppContext = createContext<Context>(null!);
const useApp = () => useContext(AppContext);
const label = (item: any, lang: Lang) =>
  typeof item === "string" ? item : (item?.[lang] ?? item?.zh ?? "");
function Money({ value }: { value: number }) {
  return <span>¥{Math.round(value).toLocaleString()}</span>;
}
function BudgetAmount({ result }: { result: any }) {
  return <span>
    {result.budget_min_jpy != null && <><Money value={result.budget_min_jpy} />–</>}
    <Money value={result.budget_jpy} />
  </span>;
}
function Language() {
  const { lang, setLang } = useApp();
  return (
    <select
      aria-label="Language"
      className="language"
      value={lang}
      onChange={(e) => setLang(e.target.value as Lang)}
    >
      <option value="zh">中文</option>
      <option value="en">English</option>
      <option value="ja">日本語</option>
    </select>
  );
}
function Brand() {
  const { t } = useApp();
  return (
    <div className="brand">
      <span className="brand-mark">
        <Leaf size={22} />
      </span>
      <span>
        {t("brand")}
        <small>DIET JOURNAL</small>
      </span>
    </div>
  );
}
function App() {
  const [lang, setLanguage] = useState<Lang>(
    (localStorage.getItem("diet-language") as Lang) || "zh",
  );
  const [user, setUser] = useState<any>(undefined);
  const [initError, setInitError] = useState("");
  const setLang = (v: Lang) => {
    setLanguage(v);
    localStorage.setItem("diet-language", v);
    document.documentElement.lang = v;
  };
  useEffect(() => {
    api("/me")
      .then((x) => {
        setUser(x);
        setCSRF(x.csrf);
      })
      .catch((e) => {
        if (e.status === 401) setUser(null);
        else setInitError(e.message);
      });
  }, []);
  const logout = async () => {
    await api("/auth/logout", "POST", {});
    setUser(null);
    setCSRF("");
  };
  const context = {
    lang,
    setLang,
    t: (k: string) => translate(lang, k),
    user,
    logout,
  };
  return (
    <AppContext.Provider value={context}>
      {user === undefined ? (
        <div className="loading">
          {initError ? (
            <Alert severity="error">{initError}</Alert>
          ) : (
            <CircularProgress />
          )}
        </div>
      ) : (
        <Routes>
          <Route
            path="/login"
            element={
              user ? (
                <Navigate to="/home" replace />
              ) : (
                <Login
                  onLogin={(u) => {
                    setCSRF(u.csrf);
                    setUser(u);
                  }}
                />
              )
            }
          />
          <Route
            path="/*"
            element={user ? <Shell /> : <Navigate to="/login" replace />}
          />
        </Routes>
      )}
    </AppContext.Provider>
  );
}
function Login({ onLogin }: { onLogin: (u: any) => void }) {
  const { t } = useApp();
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await api("/auth/login", "POST", { login_id: id, password }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <Brand />
        <div className="story-copy">
          <span className="eyebrow">A THOUGHTFUL PLATE, EVERY DAY</span>
          <h1>{t("tagline")}</h1>
          <p>{t("intro")}</p>
          <div className="still-life">
            <div className="plate">
              <span className="rice" />
              <span className="veg v1" />
              <span className="veg v2" />
              <span className="veg v3" />
              <span className="salmon" />
              <span className="lemon" />
            </div>
            <span className="chopstick c1" />
            <span className="chopstick c2" />
          </div>
        </div>
        <div className="story-foot">
          <Leaf size={15} />
          {t("privacy")}
        </div>
      </section>
      <section className="login-form">
        <div className="login-top">
          <Language />
        </div>
        <form onSubmit={submit}>
          <span className="eyebrow">YOUR DAILY NOURISHMENT</span>
          <h2>{t("loginTitle")}</h2>
          <p>{t("loginSub")}</p>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            label={t("id")}
            autoComplete="username"
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
            inputProps={{ maxLength: 30 }}
          />
          <TextField
            label={t("password")}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button
            type="submit"
            variant="contained"
            disabled={busy}
            fullWidth
            endIcon={
              busy ? <CircularProgress size={16} /> : <ArrowRight size={18} />
            }
          >
            {t("login")}
          </Button>
          <div className="login-note">
            <ShieldCheck size={17} />
            <span>{t("noRegister")}</span>
          </div>
        </form>
      </section>
    </div>
  );
}
function Shell() {
  const { t, user, logout, lang } = useApp();
  return (
    <div
      className={"app-shell" + (user.permissions?.length ? " has-admin" : "")}
    >
      <aside className="sidebar">
        <Brand />
        <div className="nav-caption">YOUR SPACE</div>
        <nav>
          {[
            ["/home", "home", Sun],
            ["/profile", "profile", UserRound],
            ["/chat", "chat", MessageCircle],
            ["/history", "history", History],
          ].map(([path, key, Icon]: any) => (
            <NavLink key={path} to={path}>
              <Icon size={19} />
              {t(key)}
              <ChevronRight className="nav-arrow" size={15} />
            </NavLink>
          ))}
        </nav>
        {user.permissions?.length > 0 && (
          <nav className="admin-sidebar" aria-label={t("adminMenu")}>
            <span className="eyebrow">{t("adminMenu")}</span>
            {[
              ["users.manage", "/admin/users", "adminUsers"],
              ["recipes.manage", "/admin/recipes", "adminRecipes"],
              ["knowledge.manage", "/admin/knowledge", "adminKnowledge"],
            ]
              .filter(([permission]) => user.permissions.includes(permission))
              .map(([, path, key]) => (
                <NavLink key={path} to={path}>
                  <Settings2 size={17} />
                  {t(key)}
                </NavLink>
              ))}
          </nav>
        )}
        <div className="sidebar-bottom">
          <div className="user-badge">
            <span>
              {user.login_id.startsWith("diet")
                ? user.login_id.slice(-2)
                : user.login_id.slice(0, 2).toUpperCase()}
            </span>
            <div>{user.login_id}</div>
          </div>
          <button className="plain logout" onClick={() => logout()}>
            <LogOut size={17} />
            {t("logout")}
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-actions">
            <Language />
            <button
              className="plain mobile-logout"
              aria-label={t("logout")}
              onClick={() => logout()}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/home" element={<Home />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route
              path="/admin/:section"
              element={<AdminPage user={user} lang={lang} />}
            />
            <Route path="*" element={<Navigate to="/home" replace />} />
          </Routes>
        </main>
        <footer className="page-footer">{t("demoNote")}</footer>
      </div>
    </div>
  );
}
function PageTitle({
  title,
  sub,
  action,
}: {
  title: string;
  sub: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      {action}
    </div>
  );
}
function RecipeCard({ meal, onOpen }: { meal: any; onOpen: (m: any) => void }) {
  const { t, lang } = useApp();
  return (
    <article className="recipe-card" onClick={() => onOpen(meal)}>
      <button className="recipe-cover" aria-label={label(meal.name, lang)}>
        <img
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = "/api/recipe-images/b1";
          }}
          src={meal.image}
          alt={label(meal.name, lang)}
          loading="lazy"
        />
        <span className="meal-badge">{t(meal.meal)}</span>
        <span className="cover-arrow">
          <ArrowUpRight size={18} />
        </span>
      </button>
      <div className="recipe-content">
        <h3>{label(meal.name, lang)}</h3>
        <div className="recipe-facts">
          <span>{Math.round(meal.nutrition.energy_kcal)} kcal</span>
          <span>
            <Clock size={13} />
            {meal.minutes} {t("minutes")}
          </span>
        </div>
        <div className="recipe-bottom">
          <span>
            <Money value={meal.cost_jpy} />
            <small> / {t("example")}</small>
          </span>
          <span className="text-link">
            {t("details")} <ArrowRight size={14} />
          </span>
        </div>
      </div>
    </article>
  );
}
function RecipeDialog({ meal, onClose }: { meal: any; onClose: () => void }) {
  const { t, lang } = useApp();
  if (!meal) return null;
  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{label(meal.name, lang)}</DialogTitle>
      <DialogContent>
        <img
          className="detail-image"
          src={meal.image}
          alt={label(meal.name, lang)}
        />
        <p className="muted">{t("demoNote")}</p>
        <h3>{t("ingredients")}</h3>
        <div className="ingredient-list">
          {meal.ingredients.map((p: any) => (
            <div key={p.code}>
              <span>
                {label(p.name, lang)}
                <small>
                  #{p.code} · {p.excel_sheet} {p.excel_row}
                </small>
              </span>
              <strong>{p.grams.toFixed(1)} g</strong>
            </div>
          ))}
        </div>
        <h3>{t("method")}</h3>
        <p className="readable">{label(meal.instructions, lang)}</p>
        <h3>{t("nutrition")}</h3>
        <Nutrients
          totals={{
            ...meal.nutrition,
            sodium_table_upper_mg: meal.sodium_table_upper_mg,
            salt_equivalent_table_upper_g: meal.salt_equivalent_table_upper_g,
            cost_jpy: meal.cost_jpy,
          }}
        />
        <details>
          <summary>{t("source")}</summary>
          <p className="muted">
            MEXT 2020 / 2021-12-28 · Excel 表全体 · {t("demoPrices")}
          </p>
          {meal.ingredients.map((p: any) => (
            <p key={p.code}>
              <b>{p.code}</b> —{" "}
              {Object.entries(p.nutrient_cells ?? {})
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
              <br />
              <small>
                {t("pdfContext")}:{" "}
                {(p.source?.pdf_references ?? [])
                  .map((r: any) => r.pdf_page)
                  .join(", ") || "—"}
              </small>
            </p>
          ))}
          {meal.quality_flags.length > 0 && (
            <p className="muted">
              {t("trace")} · {meal.quality_flags.length}
            </p>
          )}
        </details>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
function Nutrients({ totals }: { totals: any }) {
  const { t } = useApp();
  return (
    <div className="nutrient-grid">
      {[
        ["energy_kcal", "kcal", "kcal"],
        ["protein_g", "protein", "g"],
        ["fat_g", "fat", "g"],
        ["carbs_g", "carbs", "g"],
        ["fiber_g", "fiber", "g"],
        ["sodium_table_upper_mg", "sodium", "mg"],
        ["potassium_mg", "potassium", "mg"],
        ["salt_equivalent_table_upper_g", "salt", "g"],
      ].map(([field, key, unit]) => (
        <div key={field}>
          <span>{t(key)}</span>
          <strong>
            {totals[field] === null
              ? t("trace")
              : `${Number(totals[field]).toFixed(unit === "g" ? 1 : 0)} ${unit}`}
          </strong>
        </div>
      ))}
    </div>
  );
}
function Plan({
  result,
  onOpen,
  onSubstitute,
}: {
  result: any;
  onOpen: (m: any) => void;
  onSubstitute?: (meal: string) => void;
}) {
  const { t, lang } = useApp();
  return (
    <section className="plan-result">
      <div className="plan-head">
        <span className="success-chip">
          <Check size={15} />
          {t("ready")}
        </span>
        <span>
          <Money value={result.totals.cost_jpy} /> /{" "}
          <BudgetAmount result={result} />
        </span>
      </div>
      <div className="recipe-grid compact">
        {result.meals.map((m: any) => (
          <div key={m.meal}>
            <RecipeCard meal={m} onOpen={onOpen} />
            {onSubstitute && (
              <Button size="small" onClick={() => onSubstitute(m.meal)}>
                {t("replace")}
              </Button>
            )}
          </div>
        ))}
      </div>
      <Nutrients totals={result.totals} />
      <PlanExplanation result={result} lang={lang} onOpen={onOpen} />
      <p className="muted">{result.note}</p>
    </section>
  );
}
function Evidence({ sources }: { sources: any[] }) {
  const { t } = useApp();
  if (!sources?.length) return null;
  return (
    <div className="evidence">
      <h4>
        <BookOpen size={16} />
        {t("evidence")}
      </h4>
      {sources.map((s) => (
        <details key={s.chunk_id}>
          <summary>
            {s.title}{s.pdf_page != null && ` · PDF ${s.pdf_page}`}
          </summary>
          <p className="readable">{s.content}</p>
          {s.source_type === "external_guidance" && s.url?.startsWith("https://") && (
            <p><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title} ↗</a></p>
          )}
          <small>{s.warning}</small>
        </details>
      ))}
    </div>
  );
}
function useJob() {
  const [job, setJob] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!job) return;
    let active = true;
    let timer: any;
    const poll = async () => {
      try {
        const r = await api("/recommendation-jobs/" + job.job_id);
        if (!active) return;
        if (["queued", "running"].includes(r.status)) {
          setJob((j: any) => ({ ...j, status: r.status }));
          timer = setTimeout(poll, 1500);
        } else {
          setResult(r.result ?? { status: r.status });
          setJob(null);
        }
      } catch (e: any) {
        if (active) {
          setError(e.message);
          setJob(null);
        }
      }
    };
    timer = setTimeout(poll, 500);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [job?.job_id]);
  return {
    job,
    result,
    error,
    setError,
    setResult,
    start: (j: any) => {
      setResult(null);
      setError("");
      setJob(j);
    },
    cancel: async () => {
      if (job) {
        try {
          const response = await api("/recommendation-jobs/" + job.job_id + "/cancel", "POST", {});
          setJob(null);
          setResult(response.result);
        } catch (e: any) {
          setError(e.message);
        }
      }
    },
  };
}
function JobStatus({ control }: { control: ReturnType<typeof useJob> }) {
  const { t } = useApp();
  return (
    <>
      {control.error && <Alert severity="error">{control.error}</Alert>}
      {control.job && (
        <div className="job-status">
          <LinearProgress />
          <p>
            {t(control.job.status)}{" "}
            <Button size="small" onClick={control.cancel}>
              {t("cancel")}
            </Button>
          </p>
        </div>
      )}
      {control.result &&
        !control.result.meals &&
        control.result.status !== "ready" && (
          <Alert
            severity={control.result.status === "failed" ? "error" : "info"}
          >
            {control.result.message || `${t(control.result.status)} · ${t("messageHelp")}`}
          </Alert>
        )}
    </>
  );
}
function Home() {
  const { t, lang } = useApp();
  const nav = useNavigate();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const control = useJob();
  useEffect(() => {
    api("/home/today")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PageTitle
        title={t("today")}
        sub={t("todaySub")}
        action={
          <span className="date-pill">
            {new Intl.DateTimeFormat(
              lang === "zh" ? "zh-CN" : lang === "ja" ? "ja-JP" : "en-GB",
              {
                month: "long",
                day: "numeric",
                weekday: "short",
                timeZone: "Asia/Tokyo",
              },
            ).format(new Date())}
          </span>
        }
      />
      {error && <Alert severity="error">{error}</Alert>}
      {!data && !error ? (
        <CircularProgress />
      ) : (
        <>
          {data && (
            <>
              <section className="hero-panel">
                <div>
                  <span className="eyebrow">GOOD FOOD, YOUR WAY</span>
                  <h2>
                    {data.personalized ? t("personalized") : t("complete")}
                  </h2>
                  <p>{data.personalized ? t("demoNote") : t("completeSub")}</p>
                  <div className="hero-actions">
                    <Button
                      variant="contained"
                      startIcon={<MessageCircle size={17} />}
                      onClick={() => nav("/chat")}
                    >
                      {t("startChat")}
                    </Button>
                    <Button
                      onClick={() => nav("/profile")}
                      endIcon={<ArrowUpRight size={17} />}
                    >
                      {t("settings")}
                    </Button>
                  </div>
                </div>
                <div className="hero-leaf">
                  <Leaf size={125} strokeWidth={0.9} />
                  <span>
                    eat well.
                    <br />
                    live gently.
                  </span>
                </div>
              </section>
              {data.personalized && (
                <div className="stat-grid">
                  <div>
                    <span>{t("kcal")}</span>
                    <strong>
                      {Math.round(data.totals.energy_kcal)}
                      <small> kcal</small>
                    </strong>
                  </div>
                  <div>
                    <span>{t("sodium")}</span>
                    <strong>
                      {Math.round(data.totals.sodium_table_upper_mg)}
                      <small> mg</small>
                    </strong>
                  </div>
                  <div>
                    <span>{t("cost")}</span>
                    <strong>
                      <Money value={data.totals.cost_jpy} />
                      <small> / <BudgetAmount result={data} /></small>
                    </strong>
                  </div>
                </div>
              )}
              <div className="section-heading">
                <h2>{data.personalized ? t("home") : t("examples")}</h2>
                {data.personalized && (
                  <Button
                    disabled={!!control.job}
                    onClick={async () => {
                      try {
                        control.start(
                          await api("/recommendation-jobs", "POST", {
                            language: lang,
                            idempotency_key: requestKey(),
                          }),
                        );
                      } catch (e: any) {
                        control.setError(e.message);
                      }
                    }}
                  >
                    {t("generate")} <ArrowRight size={16} />
                  </Button>
                )}
              </div>
              {data.status !== "ready" && (
                <Alert severity="info">{data.message || t(data.status)}</Alert>
              )}
              <div className="recipe-grid">
                {(data.meals ?? data.examples ?? []).map((m: any) => (
                  <RecipeCard key={m.recipe_id} meal={m} onOpen={setSelected} />
                ))}
              </div>
            </>
          )}
        </>
      )}
      <JobStatus control={control} />
      {control.result?.recommendation_id && (
        <Alert severity="success">
          {t("ready")} · {t("history")}
        </Alert>
      )}
      <RecipeDialog meal={selected} onClose={() => setSelected(null)} />
    </>
  );
}
function FormSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="form-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
function ProfilePage() {
  const { t, lang, setLang, logout } = useApp();
  const [data, setData] = useState<any>(null);
  const [version, setVersion] = useState(0);
  const [bands, setBands] = useState<any[]>([]);
  const [foods, setFoods] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [bp, setBP] = useState<any[]>([]);
  const [systolic, setSystolic] = useState("");
  const [diastolic, setDiastolic] = useState("");
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  useEffect(() => {
    Promise.all([
      api("/profile"),
      api("/income-bands"),
      api("/foods"),
      api("/blood-pressure"),
    ])
      .then(([p, b, f, bp]) => {
        setData(p.profile);
        setVersion(p.version);
        setBands(b.bands);
        setFoods(f.foods);
        setBP(bp.records);
      })
      .catch((e) => setError(e.message));
  }, []);
  const update = (key: string, value: any) => {
    setData((old: any) => ({ ...old, [key]: value }));
    setSaved(false);
  };
  const toggle = (key: string, value: string) =>
    update(
      key,
      data[key].includes(value)
        ? data[key].filter((x: string) => x !== value)
        : [...data[key], value],
    );
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api("/profile", "PATCH", {
        ...data,
        expected_version: version,
      });
      setData(r.profile);
      setVersion(r.version);
      setLang(r.profile.language);
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return (
      <>
        {error ? <Alert severity="error">{error}</Alert> : <CircularProgress />}
      </>
    );
  const number = (
    field: string,
    title: string,
    min: number,
    max: number,
    optional = false,
  ) => (
    <TextField
      label={t(title)}
      type="number"
      value={data[field] ?? ""}
      onChange={(e) =>
        update(field, e.target.value === "" ? null : Number(e.target.value))
      }
      required={!optional}
      inputProps={{
        min,
        max,
        step: field.includes("cm") || field.includes("kg") ? 0.1 : 1,
      }}
    />
  );
  const check = (field: string, value: string) => (
    <FormControlLabel
      key={value}
      control={
        <Checkbox
          checked={data[field].includes(value)}
          onChange={() => toggle(field, value)}
        />
      }
      label={t(value)}
    />
  );
  const band = bands.find((b) => b.id === data.income_band);
  return (
    <>
      <PageTitle title={t("profileTitle")} sub={t("profileSub")} />
      <form onSubmit={save} className="profile-form">
        {error && <Alert severity="error">{error}</Alert>}
        {saved && <Alert severity="success">{t("saved")}</Alert>}
        <FormSection title={t("basics")}>
          <div className="form-grid">
            <TextField
              label={t("displayName")}
              value={data.display_name}
              onChange={(e) => update("display_name", e.target.value)}
              inputProps={{ maxLength: 40 }}
            />
            {number("age", "age", 1, 120)}
            {number("height_cm", "height", 70, 240, true)}
            {number("weight_kg", "weight", 20, 250, true)}
            <TextField
              select
              label={t("activity")}
              value={data.activity}
              onChange={(e) => update("activity", e.target.value)}
            >
              {["low", "moderate", "high"].map((v) => (
                <MenuItem value={v} key={v}>
                  {t(v)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label={t("language")}
              value={data.language}
              onChange={(e) => update("language", e.target.value)}
            >
              {[
                ["zh", "中文"],
                ["en", "English"],
                ["ja", "日本語"],
              ].map(([v, k]) => (
                <MenuItem value={v} key={v}>
                  {k}
                </MenuItem>
              ))}
            </TextField>
          </div>
        </FormSection>
        <FormSection title={t("incomeTitle")}>
          <div className="form-grid">
            <TextField
              select
              label={t("income")}
              value={data.income_band ?? ""}
              onChange={(e) => update("income_band", e.target.value || null)}
            >
              <MenuItem value="">{t("choose")}</MenuItem>
              {bands.map((b) => (
                <MenuItem value={b.id} key={b.id}>
                  {lang === "zh"
                    ? b.upper_jpy
                      ? `${b.lower_jpy / 10000}～不满${b.upper_jpy / 10000}万日元`
                      : "1000万日元及以上"
                    : lang === "en"
                      ? b.upper_jpy
                        ? `¥${b.lower_jpy.toLocaleString()} – < ¥${b.upper_jpy.toLocaleString()}`
                        : "¥10,000,000+"
                      : b.label}
                </MenuItem>
              ))}
            </TextField>
            {number("daily_budget", "customBudget", 100, 20000, true)}
          </div>
          <p className="muted">{t("incomeHint")}</p>
          {band && (
            <div className="budget-preview">
              <span>{t("policyBudget")}</span>
              <strong>
                ¥{band.daily_budget} / {t("budget")}
              </strong>
            </div>
          )}
        </FormSection>
        <FormSection title={t("health")}>
          <TextField
            select
            label={t("allergyStatus")}
            value={data.allergy_status}
            onChange={(e) => {
              update("allergy_status", e.target.value);
              if (e.target.value === "none") update("allergens", []);
            }}
          >
            {["unknown", "none", "present"].map((v) => (
              <MenuItem value={v} key={v}>
                {t(v)}
              </MenuItem>
            ))}
          </TextField>
          {data.allergy_status === "present" && (
            <div className="checks">
              {["milk", "egg", "soy", "wheat", "fish", "nuts", "other"].map(
                (v) => check("allergens", v),
              )}
            </div>
          )}
          <p className="field-title">{t("conditions")}</p>
          <div className="checks">
            {["hypertension", "diabetes", "kidney", "pregnancy", "other"].map(
              (v) => check("conditions", v),
            )}
          </div>
          <FormControlLabel
            control={
              <Checkbox
                checked={data.health_confirmed}
                onChange={(e) => update("health_confirmed", e.target.checked)}
              />
            }
            label={t("healthConfirmed")}
          />
          <div className="form-grid top-gap">
            <TextField
              select
              label={t("diet")}
              value={data.diet}
              onChange={(e) => update("diet", e.target.value)}
            >
              {["any", "vegetarian"].map((v) => (
                <MenuItem value={v} key={v}>
                  {t(v)}
                </MenuItem>
              ))}
            </TextField>
            {number("cooking_minutes", "cooking", 10, 120)}
          </div>
          <p className="field-title">{t("dislikes")}</p>
          <div className="food-chips">
            {foods.map((f) => (
              <Chip
                key={f.code}
                label={label(f.name, lang)}
                clickable
                color={data.dislikes.includes(f.code) ? "primary" : "default"}
                variant={data.dislikes.includes(f.code) ? "filled" : "outlined"}
                onClick={() => toggle("dislikes", f.code)}
              />
            ))}
          </div>
        </FormSection>
        <FormSection title={t("targets")}>
          <Alert severity="info">{t("targetHint")}</Alert>
          <div className="form-grid top-gap">
            {number("energy_kcal", "energyTarget", 1200, 3200)}
            {number("sodium_max_mg", "sodiumTarget", 500, 3000)}
          </div>
          <FormControlLabel
            control={
              <Checkbox
                checked={data.demo_consent}
                onChange={(e) => update("demo_consent", e.target.checked)}
              />
            }
            label={t("consent")}
          />
        </FormSection>
        <div className="sticky-save">
          <Button
            type="submit"
            variant="contained"
            disabled={busy}
            startIcon={
              busy ? <CircularProgress size={16} /> : <Check size={17} />
            }
          >
            {t("save")}
          </Button>
          {saved && <span className="muted">{t("saved")}</span>}
        </div>
      </form>
      <FormSection title={t("bpTitle")}>
        <p className="muted">{t("bpNote")}</p>
        <div className="form-grid">
          <TextField
            label={t("systolic")}
            type="number"
            value={systolic}
            onChange={(e) => setSystolic(e.target.value)}
          />
          <TextField
            label={t("diastolic")}
            type="number"
            value={diastolic}
            onChange={(e) => setDiastolic(e.target.value)}
          />
        </div>
        <Button
          onClick={async () => {
            try {
              await api("/blood-pressure", "POST", {
                systolic: Number(systolic),
                diastolic: Number(diastolic),
                measured_at: new Date().toISOString(),
              });
              setBP((await api("/blood-pressure")).records);
              setError("");
            } catch (e: any) {
              setError(e.message);
            }
          }}
        >
          {t("add")}
        </Button>
        {bp.slice(0, 8).map((r) => (
          <div className="bp-row" key={r.id}>
            <span>{new Date(r.measured_at).toLocaleString()}</span>
            <strong>
              {r.systolic} / {r.diastolic} mmHg
            </strong>
          </div>
        ))}
      </FormSection>
      <FormSection title={t("passwordTitle")}>
        <div className="form-grid">
          <TextField
            type="password"
            label={t("currentPassword")}
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
          />
          <TextField
            type="password"
            label={t("newPassword")}
            value={newPass}
            onChange={(e) => setNewPass(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <Button
          onClick={async () => {
            try {
              await api("/auth/password", "POST", {
                current_password: current,
                new_password: newPass,
              });
              window.location.href = "/login";
            } catch (e: any) {
              setError(e.message);
            }
          }}
        >
          {t("changePassword")}
        </Button>
      </FormSection>
    </>
  );
}
function ChatPage() {
  const { t, lang } = useApp();
  const [text, setText] = useState("");
  const [sid, setSid] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [sending, setSending] = useState(false);
  const control = useJob();
  useEffect(() => {
    api("/diet-chat/sessions")
      .then((r) => setSessions(r.sessions))
      .catch((e) => control.setError(e.message));
  }, []);
  useEffect(() => {
    if (control.result) {
      setMessages((ms) => [
        ...ms,
        {
          role: "assistant",
          content: control.result.message ?? t(control.result.status),
          data: control.result,
        },
      ]);
      api("/diet-chat/sessions").then((r) => setSessions(r.sessions));
    }
  }, [control.result]);
  async function send(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    try {
      const r = await api("/diet-chat/messages", "POST", {
        message: text,
        session_id: sid,
        language: lang,
        idempotency_key: requestKey(),
      });
      setSid(r.session_id);
      setMessages((ms) => [...ms, { role: "user", content: text, data: {} }]);
      setText("");
      control.start(r);
    } catch (e: any) {
      control.setError(e.message);
    } finally {
      setSending(false);
    }
  }
  return (
    <>
      <PageTitle
        title={t("chatTitle")}
        sub={t("chatSub")}
        action={
          <Button
            disabled={!!control.job}
            startIcon={<Plus size={17} />}
            onClick={() => {
              setSid(null);
              setMessages([]);
              control.setResult(null);
            }}
          >
            {t("newChat")}
          </Button>
        }
      />
      <div className="chat-layout">
        <section className="chat-surface">
          {!messages.length && (
            <div className="chat-welcome">
              <span className="chat-symbol">
                <Leaf size={34} />
              </span>
              <h2>{t("tagline")}</h2>
              <p>{t("chatSub")}</p>
              <div className="suggestions">
                {(lang === "zh"
                  ? [
                      "帮我安排一天三餐",
                      "如何减少烹调中的盐？",
                      "预算900日元吃什么？",
                    ]
                  : lang === "en"
                    ? [
                        "Plan three meals for today",
                        "How can I use less salt in cooking?",
                        "Plan meals within ¥900",
                      ]
                    : [
                        "一日の献立を提案して",
                        "調理の塩を減らす方法は？",
                        "900円で食事を提案して",
                      ]
                ).map((s) => (
                  <button key={s} onClick={() => setText(s)}>
                    {s}
                    <ArrowUpRight size={14} />
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="messages">
            {messages.map((m, i) => (
              <div className={"message " + m.role} key={i}>
                {m.role === "assistant" && (
                  <span className="assistant-avatar">
                    <Leaf size={17} />
                  </span>
                )}
                <div className="bubble">
                  {m.content && <p>{m.content}</p>}
                  {m.data?.meals ? (
                    <Plan result={m.data} onOpen={setSelected} />
                  ) : (
                    <Evidence sources={m.data?.evidence} />
                  )}
                </div>
              </div>
            ))}
          </div>
          {control.error && <Alert severity="error">{control.error}</Alert>}
          {control.job && (
            <div className="chat-progress">
              <CircularProgress size={15} />
              {t(control.job.status)}
              <Button size="small" onClick={control.cancel}>
                {t("cancel")}
              </Button>
            </div>
          )}
          <form className="chat-compose" onSubmit={send}>
            <textarea
              aria-label={t("placeholder")}
              placeholder={t("placeholder")}
              value={text}
              maxLength={1500}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  if (!control.job && !sending) send(e);
                }
              }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={!text.trim() || !!control.job || sending}
              aria-label={t("send")}
            >
              <Send size={19} />
            </Button>
          </form>
          <div className="compose-foot">{t("demoNote")}</div>
        </section>
        <aside className="chat-side">
          <h3>{t("chatHistory")}</h3>
          {sessions.map((s) => (
            <button
              className={"session " + (sid === s.id ? "selected" : "")}
              disabled={!!control.job}
              key={s.id}
              onClick={async () => {
                try {
                  const r = await api("/diet-chat/sessions/" + s.id);
                  setSid(s.id);
                  setMessages(r.messages);
                  control.setResult(null);
                  if (r.active_job) control.start(r.active_job);
                } catch (e: any) {
                  control.setError(e.message);
                }
              }}
            >
              <MessageCircle size={15} />
              {new Date(s.created_at).toLocaleString()}
            </button>
          ))}
          <div className="chat-tip">
            <Settings2 size={22} />
            <p>{t("completeSub")}</p>
            <NavLink to="/profile">{t("settings")} →</NavLink>
          </div>
        </aside>
      </div>
      <RecipeDialog meal={selected} onClose={() => setSelected(null)} />
    </>
  );
}
function HistoryPage() {
  const { t, lang } = useApp();
  const [rows, setRows] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [error, setError] = useState("");
  const [budget, setBudget] = useState("");
  const control = useJob();
  const load = () =>
    api("/recommendations")
      .then((r) => setRows(r.recommendations))
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    if (control.result?.recommendation_id) load();
  }, [control.result]);
  return (
    <>
      <PageTitle title={t("historyTitle")} sub={t("historySub")} />
      {error && <Alert severity="error">{error}</Alert>}
      <JobStatus control={control} />
      {!rows.length && (
        <div className="empty">
          <History size={36} />
          <p>{t("empty")}</p>
        </div>
      )}
      <TextField
        className="history-budget"
        label={t("requestBudget")}
        type="number"
        value={budget}
        onChange={(e) => setBudget(e.target.value)}
        inputProps={{ min: 100, max: 20000 }}
      />
      {rows.map((r) => (
        <section key={r.id} className="history-item">
          <div className="history-heading">
            <h3>{new Date(r.created_at).toLocaleString()}</h3>
            <span>
              {r.data.budget_source} · {r.data.income_policy?.id ?? "—"}
            </span>
          </div>
          <Plan
            result={r.data}
            onOpen={setSelected}
            onSubstitute={
              control.job
                ? undefined
                : async (meal) => {
                    try {
                      control.start(
                        await api(
                          "/recommendations/" + r.id + "/substitutions",
                          "POST",
                          {
                            meal,
                            language: lang,
                            budget: budget ? Number(budget) : null,
                            idempotency_key: requestKey(),
                          },
                        ),
                      );
                    } catch (e: any) {
                      control.setError(e.message);
                    }
                  }
            }
          />
        </section>
      ))}
      <RecipeDialog meal={selected} onClose={() => setSelected(null)} />
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
);
