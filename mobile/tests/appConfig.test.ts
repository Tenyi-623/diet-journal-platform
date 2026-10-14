const appConfigModule = require("../app.config");
const createAppConfig = appConfigModule.default ?? appConfigModule;
const baseConfig = require("../app.json").expo;

describe("Expo app configuration", () => {
  const previousApiUrl = process.env.EXPO_PUBLIC_API_URL;
  const previousPreviewFlag = process.env.DIET_ANDROID_LAN_HTTP_PREVIEW;

  afterEach(() => {
    if (previousApiUrl === undefined) delete process.env.EXPO_PUBLIC_API_URL;
    else process.env.EXPO_PUBLIC_API_URL = previousApiUrl;
    if (previousPreviewFlag === undefined) delete process.env.DIET_ANDROID_LAN_HTTP_PREVIEW;
    else process.env.DIET_ANDROID_LAN_HTTP_PREVIEW = previousPreviewFlag;
  });

  it("does not add an HTTP exception to the normal app config", () => {
    delete process.env.DIET_ANDROID_LAN_HTTP_PREVIEW;
    process.env.EXPO_PUBLIC_API_URL = "https://api.example.invalid";

    const config = createAppConfig({ config: baseConfig });

    expect(config.extra.dietAndroidLanHttpPreview).toBe(false);
    expect(config.plugins).toEqual(baseConfig.plugins);
  });

  it("adds the Android LAN HTTP plugin only for a valid internal preview config", () => {
    process.env.DIET_ANDROID_LAN_HTTP_PREVIEW = "true";
    process.env.EXPO_PUBLIC_API_URL = "http://192.168.1.86:8000";

    const config = createAppConfig({ config: baseConfig });

    expect(config.extra.dietAndroidLanHttpPreview).toBe(true);
    expect(config.plugins).toContainEqual([
      "./plugins/withLanHttpAndroid",
      { apiUrl: "http://192.168.1.86:8000" },
    ]);
  });

  it("fails app config resolution when preview HTTP targets a public host", () => {
    process.env.DIET_ANDROID_LAN_HTTP_PREVIEW = "true";
    process.env.EXPO_PUBLIC_API_URL = "http://8.8.8.8:8000";

    expect(() => createAppConfig({ config: baseConfig })).toThrow(
      "必须是无凭据的 RFC1918 IPv4 HTTP 地址",
    );
  });
});
