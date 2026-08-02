/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PUBLIC_BASE_URL?: string;
  readonly NEXT_PUBLIC_UMAMI_ENABLED?: string;
  readonly NEXT_PUBLIC_UMAMI_SCRIPT_URL?: string;
  readonly NEXT_PUBLIC_UMAMI_WEBSITE_ID?: string;
}
