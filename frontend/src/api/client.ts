import createClient, { type Client } from "openapi-fetch";
import type { paths } from "./schema";

/** The backend's HTTP origin; its WebSocket is served at /ws on the same origin. */
export const backendUrl = () => import.meta.env.VITE_BACKEND_URL ?? `http://${window.location.hostname}:8000`;

let client: Client<paths> | undefined;
/** Typed HTTP client generated from the backend's OpenAPI document. */
export const api = () => (client ??= createClient<paths>({ baseUrl: backendUrl() }));
