const { resolveLanHttpPolicy } = require("./lib/lanHttpPolicy");

module.exports = ({ config }) => {
  const sourceConfig = config ?? require("./app.json").expo;
  const lanHttpPreview = process.env.DIET_ANDROID_LAN_HTTP_PREVIEW === "true";
  const policy = resolveLanHttpPolicy({
    apiUrl: process.env.EXPO_PUBLIC_API_URL,
    enabled: lanHttpPreview,
  });
  const plugins = [...(sourceConfig.plugins ?? [])];

  if (policy.enabled) {
    plugins.push([
      "./plugins/withLanHttpAndroid",
      { apiUrl: process.env.EXPO_PUBLIC_API_URL },
    ]);
  }

  return {
    ...sourceConfig,
    extra: {
      ...(sourceConfig.extra ?? {}),
      dietAndroidLanHttpPreview: policy.enabled,
    },
    plugins,
  };
};
