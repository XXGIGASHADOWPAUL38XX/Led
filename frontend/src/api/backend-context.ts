import { createContext } from "react";
import { useRequiredContext } from "@/lib/react/use-required-context";
import type { BackendStore } from "./store";

export const BackendContext = createContext<BackendStore | null>(null);

/** The backend store of the nearest BackendProvider. */
export const useBackend = () => useRequiredContext(BackendContext, "useBackend");
