"use client";

import { useCallback, useSyncExternalStore } from "react";
import { backend, initialStatus, initialGeneration } from "./store";
import { emptyViewSettings } from "./template";

const empty = () => null;
export function useGeneration() {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe("jev", listener), []), () => backend.generation, () => initialGeneration);
}
export function useGenerationPreview() {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe("jev-preview", listener), []), () => backend.generationPreview, empty);
}
export function useBackendStatus() {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe("status", listener), []), () => backend.status, () => initialStatus);
}
export function useGraph() {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe("graph", listener), []), () => backend.snapshot, empty);
}
export function useBackendNode(id: string) {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe(`node:${id}`, listener), [id]), () => backend.node(id), empty);
}
export function useArray(nodeId: string, element: string) {
  return useSyncExternalStore(useCallback((listener) => backend.watchArray(nodeId, element, listener), [nodeId, element]), () => backend.array(nodeId, element), empty);
}
export function usePlayer(id: string) {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe(`player:${id}`, listener), [id]), () => backend.player(id), empty);
}
export function useSearchResults(id: string) {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe(`results:${id}`, listener), [id]), () => backend.searchResults(id), empty);
}

export function useViewSettings(nodeId: string, viewId: string) {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe(`display:${JSON.stringify([nodeId, viewId])}`, listener), [nodeId, viewId]),
    () => backend.viewSettings(nodeId, viewId), () => emptyViewSettings);
}
export function useTemplateRevision() {
  return useSyncExternalStore(useCallback((listener) => backend.subscribe("template", listener), []), () => backend.templateRevision, () => 0);
}
