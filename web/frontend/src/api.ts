const configuredBase = (import.meta.env.VITE_API_BASE ?? "").trim().replace(/\/$/, "");
const configuredTrackBase = (import.meta.env.VITE_TRACK_API_BASE ?? "").trim().replace(/\/$/, "");
export const apiConfigured = import.meta.env.DEV || Boolean(configuredBase);
export const trackApiConfigured = import.meta.env.DEV || Boolean(configuredTrackBase || configuredBase);

function fetchFrom(base: string, path: string, init?: RequestInit): Promise<Response> {
  if (!import.meta.env.DEV && !base) {
    return Promise.reject(new Error("No backend configured. Set the appropriate GitHub Actions repository variable."));
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return fetch(`${base}${normalizedPath}`, init);
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetchFrom(configuredBase, path, init);
}

export function trackApiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetchFrom(configuredTrackBase || configuredBase, path, init);
}

function normalizeMedia<T>(value: T, base: string): T {
  if (!base) return value;
  const visit = (item: unknown): unknown => {
    if (typeof item === "string" && item.startsWith("/media/")) return `${base}${item}`;
    if (Array.isArray(item)) return item.map(visit);
    if (item && typeof item === "object") return Object.fromEntries(Object.entries(item).map(([key, child]) => [key, visit(child)]));
    return item;
  };
  return visit(value) as T;
}

export function normalizeApiResult<T>(value: T): T {
  return normalizeMedia(value, configuredBase);
}

export function normalizeTrackApiResult<T>(value: T): T {
  return normalizeMedia(value, configuredTrackBase || configuredBase);
}
