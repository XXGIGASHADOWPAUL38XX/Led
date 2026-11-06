import type { Endpoint } from "../../api/protocol.ts";

export type ClusteringInput = { source: Endpoint | null; interval: [number, number] };
