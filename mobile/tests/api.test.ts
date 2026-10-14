import { ApiClient, ApiError } from "../src/lib/api";

function response(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe("ApiClient", () => {
  it("sends the session token as a bearer header and preserves API results", async () => {
    const fetcher = jest.fn<
      Promise<Response>,
      [input: RequestInfo | URL, init?: RequestInit]
    >(async (_input, _init) => response(200, {
        message: "无法回答与饮食无关的内容",
        reason_code: "outside_diet_scope",
      }));
    const client = new ApiClient(
      "https://diet.example/api",
      () => "mobile-secret",
      jest.fn(),
      fetcher as unknown as typeof fetch,
    );

    const result = await client.json("/recommendation-jobs/job-1");
    const [, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];

    expect(result).toEqual({
      message: "无法回答与饮食无关的内容",
      reason_code: "outside_diet_scope",
    });
    expect(fetcher.mock.calls[0][0]).toBe("https://diet.example/api/recommendation-jobs/job-1");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer mobile-secret");
  });

  it("rejects HTTP API endpoints when LAN preview access is disabled", async () => {
    const client = new ApiClient("http://diet.example/api", () => null, jest.fn(), jest.fn() as unknown as typeof fetch);
    await expect(client.json("/me")).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining("HTTPS"),
    });
  });

  it("allows a preview-enabled request only to an RFC1918 IPv4 API host", async () => {
    const fetcher = jest.fn(async () => response(200, { ok: true })) as unknown as typeof fetch;
    const client = new ApiClient(
      "http://192.168.1.86:8000",
      () => null,
      jest.fn(),
      fetcher,
      true,
    );

    await client.json("/me");

    expect(fetcher).toHaveBeenCalledWith(
      "http://192.168.1.86:8000/api/me",
      expect.any(Object),
    );
  });

  it.each([
    "http://diet.example/api",
    "http://8.8.8.8/api",
    "http://172.15.0.1/api",
    "http://169.254.1.1/api",
    "http://127.0.0.1/api",
  ])("rejects a non-LAN HTTP API endpoint even when preview HTTP is enabled: %s", async (url) => {
    const fetcher = jest.fn(async () => response(200, { ok: true })) as unknown as typeof fetch;
    const client = new ApiClient(url, () => null, jest.fn(), fetcher, true);
    await expect(client.json("/me")).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining("局域网"),
    });
  });

  it("clears an expired authenticated session on 401", async () => {
    const onUnauthorized = jest.fn();
    const client = new ApiClient(
      "https://diet.example/api",
      () => "mobile-secret",
      onUnauthorized,
      jest.fn(async () => response(401, { detail: "登录已过期" })) as unknown as typeof fetch,
    );
    await expect(client.json("/me")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});
