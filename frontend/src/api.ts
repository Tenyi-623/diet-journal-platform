import { translate } from "./i18n";
import type { Lang } from "./i18n";

let csrf = "";
export function setCSRF(value: string) {
  csrf = value;
}
export async function api(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<any> {
  const lang = (localStorage.getItem("diet-language") || "zh") as Lang;
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }).catch(() => {
    throw new Error(translate(lang, "connectionProblem"));
  });
  const value = await response
    .json()
    .catch(() => {
      throw new Error(translate(lang, "responseUnreadable"));
    });
  if (!response.ok) {
    if (response.status === 401 && path !== "/me" && path !== "/auth/login")
      window.location.assign("/login");
    const error = new Error(
      typeof value.detail === "string"
        ? value.detail
        : translate(lang, response.status === 422 ? "invalidRequest" : "responseUnreadable"),
    );
    (error as any).status = response.status;
    throw error;
  }
  return value;
}
export const requestKey = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(16)), (v) =>
    v.toString(16).padStart(2, "0"),
  ).join("");
