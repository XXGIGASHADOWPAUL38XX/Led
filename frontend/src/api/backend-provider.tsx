import { type ReactNode, useEffect } from "react";
import { BackendContext } from "./backend-context";
import type { BackendStore } from "./store";

/** Share one backend store with the tree and keep its connection open while mounted. */
export function BackendProvider({ store, children }: { store: BackendStore; children: ReactNode }) {
  useEffect(() => {
    store.connection.start();
    return () => store.connection.stop();
  }, [store]);
  return <BackendContext value={store}>{children}</BackendContext>;
}
