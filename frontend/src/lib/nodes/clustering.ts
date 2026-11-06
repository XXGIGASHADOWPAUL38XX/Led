import type { Endpoint } from "../backend/protocol.ts";

export type ClusteringInput = { source: Endpoint | null; interval: [number, number] };
