const fs = require("node:fs/promises");
const path = require("node:path");
const { withAndroidManifest, withDangerousMod } = require("expo/config-plugins");
const { resolveLanHttpPolicy } = require("../lib/lanHttpPolicy");

module.exports = function withLanHttpAndroid(config, options = {}) {
  const policy = resolveLanHttpPolicy({ apiUrl: options.apiUrl, enabled: true });

  config = withAndroidManifest(config, (modConfig) => {
    const application = modConfig.modResults.manifest.application?.[0];
    if (!application) throw new Error("AndroidManifest.xml 中缺少 application 节点。");

    application.$ ??= {};
    delete application.$["android:usesCleartextTraffic"];
    application.$["android:networkSecurityConfig"] = "@xml/network_security_config";
    return modConfig;
  });

  return withDangerousMod(config, ["android", async (modConfig) => {
    const resourceDirectory = path.join(
      modConfig.modRequest.platformProjectRoot,
      "app",
      "src",
      "main",
      "res",
      "xml",
    );
    await fs.mkdir(resourceDirectory, { recursive: true });
    await fs.writeFile(
      path.join(resourceDirectory, "network_security_config.xml"),
      policy.xml,
      "utf8",
    );
    return modConfig;
  }]);
};
