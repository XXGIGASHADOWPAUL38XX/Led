import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useBackendStatus } from "@/api/hooks";
import type { Catalog } from "./catalog-context";

/** Fetch the catalog once the backend is reachable; the browser revalidates it by ETag. */
export function useCatalogQuery() {
  const connected = useBackendStatus().connection === "connected";
  return useQuery({
    queryKey: ["catalog"],
    enabled: connected,
    staleTime: Infinity,
    queryFn: async (): Promise<Catalog> => {
      const { data, error } = await api().GET("/api/v1/catalog");
      if (error || !data) throw Error("Could not load the node catalog");
      return Object.fromEntries(data.map((node) => [node.type, node]));
    },
  }).data;
}
