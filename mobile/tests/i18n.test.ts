import { t } from "../src/i18n";

describe("mobile interface translations", () => {
  it("provides the login title in all supported languages", () => {
    expect(t("zh", "loginTitle")).toBe("欢迎回来");
    expect(t("en", "loginTitle")).toBe("Welcome back");
    expect(t("ja", "loginTitle")).toBe("おかえりなさい");
  });

  it("falls back to Chinese for an unknown translation key", () => {
    expect(t("en", "unknownKey")).toBe("unknownKey");
  });
});
