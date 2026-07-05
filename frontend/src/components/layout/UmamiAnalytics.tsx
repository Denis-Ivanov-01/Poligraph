function isHttpUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function UmamiAnalytics() {
  const enabled = import.meta.env.NEXT_PUBLIC_UMAMI_ENABLED === "true";
  const scriptUrl = import.meta.env.NEXT_PUBLIC_UMAMI_SCRIPT_URL;
  const websiteId = import.meta.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID;

  if (!enabled || !scriptUrl || !websiteId || !isHttpUrl(scriptUrl)) {
    return null;
  }

  return <script async defer data-website-id={websiteId} src={scriptUrl} />;
}
