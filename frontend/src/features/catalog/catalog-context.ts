import { createContext } from "react";
import { useRequiredContext } from "@/lib/react/use-required-context";
import type { NodeDefinition } from "../nodes/definition";

export type Catalog = Record<string, NodeDefinition>;

/** The node catalog, provided once it is loaded; null while the backend has not answered. */
export const CatalogContext = createContext<Catalog | null>(null);

export const useCatalog = () => useRequiredContext(CatalogContext, "useCatalog");
