import createClient from "openapi-fetch";
import { fromJson, toJson } from "./protocol.ts";
import type { paths } from "./schema";

/** The backend's HTTP origin; its WebSocket is served at /ws on the same origin. */
export const backendUrl = () => import.meta.env.VITE_BACKEND_URL ?? `http://${window.location.hostname}:8000`;

/** Typed client for the HTTP API; arrays cross JSON as base64 envelopes and the tab id scopes undo history. */
export function createHttpClient(baseUrl: string, clientId: string, fetch: typeof globalThis.fetch = globalThis.fetch) {
  return createClient<paths>({
    baseUrl,
    fetch,
    headers: { "X-Client-Id": clientId },
    bodySerializer: (body) => JSON.stringify(toJson(body)),
  });
}

/** The message of a refused request: ours send `detail` as text, FastAPI's validation errors as a list. */
export function refusal(error: unknown) {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (Array.isArray(detail)) return detail.map((item: { msg?: string }) => item.msg).join("; ");
  return typeof detail === "string" ? detail : "Request failed";
}

/** Unwrap an openapi-fetch result: the decoded body once `settle` allows it, or the refusal as an Error. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
  settle: (response: Response) => Promise<void> = async () => {},
): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined) throw Error(refusal(error));
  await settle(response);
  return fromJson(data) as T;
}
