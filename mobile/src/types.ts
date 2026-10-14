export type Language = "zh" | "en" | "ja";

export type User = {
  id: number;
  login_id: string;
  roles?: string[];
  permissions?: string[];
};

export type UserProfile = {
  expected_version?: number;
  display_name: string;
  language: Language;
  age: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  activity: "low" | "moderate" | "high";
  income_band: string | null;
  daily_budget: number | null;
  allergy_status: "unknown" | "none" | "present";
  allergens: string[];
  conditions: string[];
  health_confirmed: boolean;
  diet: "any" | "vegetarian";
  dislikes: string[];
  cooking_minutes: number;
  region: "Japan-demo";
  demo_consent: boolean;
  energy_kcal: number;
  sodium_max_mg: number;
};

export type Ingredient = { code: string; name: string; grams: number };

export type Recipe = {
  recipe_id: string;
  meal: "breakfast" | "lunch" | "dinner";
  name: string | Record<string, string>;
  image: string;
  minutes: number;
  ingredients: Ingredient[];
  nutrition: Record<string, number | null>;
  cost_jpy: number;
  sodium_table_upper_mg?: number;
  allergens: string[];
  instructions: string | Record<string, string>;
};

export type HomeData = {
  status: string;
  date: string;
  personalized: boolean;
  meals?: Recipe[];
  examples?: Recipe[];
  message?: string;
  note?: string;
  totals?: Record<string, number | null>;
};

export type ApiJob = {
  job_id: string;
  status: string;
  result?: Record<string, unknown> | null;
  session_id?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown> | null;
  created_at?: string;
};

export type IncomeBand = {
  id: string;
  label: string;
  daily_budget: number;
  lower_jpy: number;
  upper_jpy: number | null;
};

export function localized(value: string | Record<string, string> | undefined, language = "zh"): string {
  if (typeof value === "string") return value;
  if (!value) return "";
  return value[language] ?? value.zh ?? Object.values(value)[0] ?? "";
}
