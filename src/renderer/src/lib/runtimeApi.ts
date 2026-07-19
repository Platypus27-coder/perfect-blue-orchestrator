const DEFAULT_RUNTIME_URL = "http://127.0.0.1:7770";

export const runtimeBaseUrl = (
  import.meta.env.VITE_PERFECTBLUE_RUNTIME_URL || DEFAULT_RUNTIME_URL
).replace(/\/$/, "");

const runtimeToken = import.meta.env.VITE_PERFECTBLUE_RUNTIME_TOKEN?.trim() || "";

export class RuntimeApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "RuntimeApiError";
    this.status = status;
  }
}

export async function runtimeFetch<T>(
  pathname: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${runtimeBaseUrl}${pathname}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : null),
      ...(runtimeToken ? { Authorization: `Bearer ${runtimeToken}` } : null),
      ...init.headers,
    },
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? ((await response.json()) as unknown)
    : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload && "error" in payload
        ? String((payload as { error: unknown }).error)
        : typeof payload === "string" && payload.trim()
          ? payload
          : `Runtime request failed (${response.status}).`;
    throw new RuntimeApiError(message, response.status);
  }

  return payload as T;
}
