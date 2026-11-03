import { createContext, useContext } from "react";
import type { BackendStore } from "./store";

export const BackendContext = createContext<BackendStore | null>(null);

/** The backend store of the nearest BackendProvider. */
export function useBackend() {
  const backend = useContext(BackendContext);
  if (!backend) throw Error("useBackend must be used inside a BackendProvider");
  return backend;
}
