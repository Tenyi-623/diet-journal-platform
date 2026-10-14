function isRfc1918Ipv4(host) {
  if (!/^(?:\d{1,3}\.){3}\d{1,3}$/.test(host)) return false;

  const parts = host.split(".");
  const octets = parts.map(Number);
  if (octets.some((octet, index) => octet < 0 || octet > 255 || String(octet) !== parts[index])) {
    return false;
  }

  const [first, second] = octets;
  return (
    first === 10 ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168)
  );
}

function getPrivateLanHttpHost(apiUrl) {
  if (typeof apiUrl !== "string" || !apiUrl.trim()) return null;

  let url;
  try {
    url = new URL(apiUrl.trim());
  } catch {
    return null;
  }

  if (
    url.protocol !== "http:" ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !isRfc1918Ipv4(url.hostname)
  ) {
    return null;
  }

  return url.hostname;
}

function resolveLanHttpPolicy({ apiUrl, enabled }) {
  if (!enabled) return { enabled: false, host: null, xml: null };

  const host = getPrivateLanHttpHost(apiUrl);
  if (!host) {
    throw new Error(
      "启用局域网 HTTP 时，EXPO_PUBLIC_API_URL 必须是无凭据的 RFC1918 IPv4 HTTP 地址，且不能包含查询参数或片段。",
    );
  }

  return {
    enabled: true,
    host,
    xml: [
      '<?xml version="1.0" encoding="utf-8"?>',
      "<network-security-config>",
      '  <base-config cleartextTrafficPermitted="false" />',
      '  <domain-config cleartextTrafficPermitted="true">',
      `    <domain includeSubdomains="false">${host}</domain>`,
      "  </domain-config>",
      "</network-security-config>",
      "",
    ].join("\n"),
  };
}

function isAndroidLanHttpPreview(platform, enabled) {
  return platform === "android" && enabled === true;
}

module.exports = {
  getPrivateLanHttpHost,
  isAndroidLanHttpPreview,
  resolveLanHttpPolicy,
};
