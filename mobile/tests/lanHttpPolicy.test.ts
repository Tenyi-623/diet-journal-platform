const { isAndroidLanHttpPreview, resolveLanHttpPolicy } = require("../lib/lanHttpPolicy");

describe("LAN HTTP build policy", () => {
  it("enables the HTTP preview exception only in an Android preview build", () => {
    expect(isAndroidLanHttpPreview("android", true)).toBe(true);
    expect(isAndroidLanHttpPreview("ios", true)).toBe(false);
    expect(isAndroidLanHttpPreview("android", false)).toBe(false);
  });

  it("keeps HTTP disabled when the LAN preview build flag is off", () => {
    expect(
      resolveLanHttpPolicy({ apiUrl: "http://192.168.1.86:8000", enabled: false }),
    ).toEqual({ enabled: false, host: null, xml: null });
  });

  it("allows only the configured RFC1918 IPv4 host and denies cleartext by default", () => {
    expect(
      resolveLanHttpPolicy({ apiUrl: "http://192.168.1.86:8000/api", enabled: true }),
    ).toEqual({
      enabled: true,
      host: "192.168.1.86",
      xml: [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<network-security-config>",
        '  <base-config cleartextTrafficPermitted="false" />',
        '  <domain-config cleartextTrafficPermitted="true">',
        '    <domain includeSubdomains="false">192.168.1.86</domain>',
        "  </domain-config>",
        "</network-security-config>",
        "",
      ].join("\n"),
    });
  });

  it.each([
    "http://diet.example:8000",
    "http://8.8.8.8:8000",
    "http://172.15.255.254:8000",
    "http://172.32.0.1:8000",
    "http://169.254.1.1:8000",
    "http://127.0.0.1:8000",
    "https://192.168.1.86:8000",
    "http://192.168.1.86:8000?token=unsafe",
  ])("refuses to generate an HTTP exception for %s", (apiUrl) => {
    expect(() => resolveLanHttpPolicy({ apiUrl, enabled: true })).toThrow(
      "必须是无凭据的 RFC1918 IPv4 HTTP 地址",
    );
  });
});
