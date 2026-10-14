export type LanHttpPolicy = {
  enabled: boolean;
  host: string | null;
  xml: string | null;
};

export function getPrivateLanHttpHost(apiUrl: string | undefined): string | null;

export function isAndroidLanHttpPreview(platform: string, enabled: boolean): boolean;

export function resolveLanHttpPolicy(options: {
  apiUrl: string | undefined;
  enabled: boolean;
}): LanHttpPolicy;
