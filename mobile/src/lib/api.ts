import Constants from "expo-constants";
import { Platform } from "react-native";
import { getPrivateLanHttpHost, isAndroidLanHttpPreview } from "../../lib/lanHttpPolicy";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly payload?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type TokenProvider = () => string | null;
type UnauthorizedHandler = () => void | Promise<void>;

export type RequestOptions = RequestInit & {
  authenticated?: boolean;
};

function makeApiBaseUrl(raw: string | undefined, allowInsecureHttp: boolean): string {
  if (!raw?.trim()) {
    throw new ApiError(0, "尚未配置 API 地址；请设置 EXPO_PUBLIC_API_URL。 ");
  }

  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    throw new ApiError(0, "API 地址格式无效。 ");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new ApiError(0, "API 地址不能包含账号、密码、查询参数或片段。 ");
  }
  if (url.protocol !== "https:" && !(allowInsecureHttp && url.protocol === "http:")) {
    throw new ApiError(0, "移动端 API 必须使用 HTTPS。 ");
  }
  if (url.protocol === "http:" && !getPrivateLanHttpHost(url.toString())) {
    throw new ApiError(0, "内部演示 HTTP 仅允许连接 RFC1918 私有局域网 IPv4 地址。 ");
  }
  const path = url.pathname.replace(/\/+$/, "");
  url.pathname = path.endsWith("/api") ? path : `${path}/api`;
  return url.toString().replace(/\/$/, "");
}

export class ApiClient {
  private readonly baseUrl: string | null;
  readonly configurationError: string | null;

  constructor(
    rawBaseUrl: string | undefined,
    private readonly getToken: TokenProvider,
    private readonly onUnauthorized: UnauthorizedHandler,
    private readonly fetcher: typeof fetch = fetch,
    allowInsecureHttp = false,
  ) {
    try {
      this.baseUrl = makeApiBaseUrl(rawBaseUrl, allowInsecureHttp);
      this.configurationError = null;
    } catch (error) {
      this.baseUrl = null;
      this.configurationError = error instanceof Error ? error.message : "API 配置无效。";
    }
  }

  async json<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.send(path, options);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  async text(path: string, options: RequestOptions = {}): Promise<string> {
    return (await this.send(path, options)).text();
  }

  private async send(path: string, options: RequestOptions): Promise<Response> {
    if (!this.baseUrl) {
      throw new ApiError(0, this.configurationError ?? "API 配置无效。");
    }
    if (!path.startsWith("/") || path.startsWith("//")) {
      throw new ApiError(0, "API 路径无效。 ");
    }

    const { authenticated = true, ...init } = options;
    const token = authenticated ? this.getToken() : null;
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined && !headers.has("content-type")) {
      headers.set("Content-Type", "application/json");
    }
    if (token) headers.set("Authorization", `Bearer ${token}`);

    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        headers,
      });
    } catch {
      throw new ApiError(0, "无法连接饮食服务，请检查网络和 API 地址。 ");
    }

    if (!response.ok) {
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        payload = undefined;
      }
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? String((payload as { detail: unknown }).detail)
          : `请求失败（${response.status}）`;
      if (response.status === 401 && token) await this.onUnauthorized();
      throw new ApiError(response.status, detail, payload);
    }

    return response;
  }
}

const allowInsecureLanPreview =
  isAndroidLanHttpPreview(
    Platform.OS,
    Constants.expoConfig?.extra?.dietAndroidLanHttpPreview === true,
  );

export function createApiClient(
  getToken: TokenProvider,
  onUnauthorized: UnauthorizedHandler,
): ApiClient {
  return new ApiClient(
    process.env.EXPO_PUBLIC_API_URL,
    getToken,
    onUnauthorized,
    fetch,
    allowInsecureLanPreview,
  );
}
