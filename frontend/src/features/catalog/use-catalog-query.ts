import { useQuery } from "@tanstack/react-query";
import { useBackend } from "@/api/backend-context";
import { unwrap } from "@/api/client";
import { useBackendStatus } from "@/api/hooks";
import type { Catalog } from "./catalog-context";

/** Fetch the catalog once the backend is reachable; the browser revalidates it by ETag. */
export function useCatalogQuery() {
  const backend = useBackend();
  const connected = useBackendStatus().connection === "connected";
  return useQuery({
    queryKey: ["catalog"],
    enabled: connected,
    staleTime: Infinity,
    queryFn: async (): Promise<Catalog> => {
      const nodes = await unwrap(backend.http.GET("/api/v1/catalog"));
      return Object.fromEntries(nodes.map((node) => [node.type, node]));
    },
  }).data;
}
