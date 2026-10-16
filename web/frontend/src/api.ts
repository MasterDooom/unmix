const configuredBase = (import.meta.env.VITE_API_BASE ?? "").trim().replace(/\/$/, "");
export const apiConfigured = import.meta.env.DEV || Boolean(configuredBase);

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!import.meta.env.DEV && !configuredBase) {
    return Promise.reject(new Error("No backend configured. Set the UNMIX_API_BASE repository variable to the deployed HTTPS API URL."));
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return fetch(`${configuredBase}${normalizedPath}`, init);
}

export function normalizeApiResult<T>(value: T): T {
  if (!configuredBase) return value;
  const visit = (item: unknown): unknown => {
    if (typeof item === "string" && item.startsWith("/media/")) return `${configuredBase}${item}`;
    if (Array.isArray(item)) return item.map(visit);
    if (item && typeof item === "object") return Object.fromEntries(Object.entries(item).map(([key, child]) => [key, visit(child)]));
    return item;
  };
  return visit(value) as T;
}
