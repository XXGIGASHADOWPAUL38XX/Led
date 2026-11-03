import { useCallback, useSyncExternalStore } from "react";
import { useBackend } from "./backend-context";
import { initialStatus, initialGeneration, type BackendStore } from "./store";
import { emptyViewSettings } from "./template";

/** Read one store value and re-render only when its key is emitted. */
function useStoreValue<T>(key: string, read: (backend: BackendStore) => T, initial: T) {
  const backend = useBackend();
  return useSyncExternalStore(
    useCallback((listener) => backend.subscribe(key, listener), [backend, key]),
    () => read(backend),
    () => initial,
  );
}

export const useGeneration = () => useStoreValue("jev", (backend) => backend.generation, initialGeneration);
export const useGenerationPreview = () => useStoreValue("jev-preview", (backend) => backend.generationPreview, null);
export const useBackendStatus = () => useStoreValue("status", (backend) => backend.status, initialStatus);
export const useGraph = () => useStoreValue("graph", (backend) => backend.snapshot, null);
export const useBackendNode = (id: string) => useStoreValue(`node:${id}`, (backend) => backend.node(id), null);
export const usePlayer = (id: string) => useStoreValue(`player:${id}`, (backend) => backend.player(id), null);
export const useSearchResults = (id: string) =>
  useStoreValue(`results:${id}`, (backend) => backend.searchResults(id), null);
export const useViewSettings = (nodeId: string, viewId: string) =>
  useStoreValue(
    `display:${JSON.stringify([nodeId, viewId])}`,
    (backend) => backend.viewSettings(nodeId, viewId),
    emptyViewSettings,
  );
export const useTemplateRevision = () => useStoreValue("template", (backend) => backend.templateRevision, 0);

export function useArray(nodeId: string, element: string) {
  const backend = useBackend();
  return useSyncExternalStore(
    useCallback((listener) => backend.watchArray(nodeId, element, listener), [backend, nodeId, element]),
    () => backend.array(nodeId, element),
    () => null,
  );
}
