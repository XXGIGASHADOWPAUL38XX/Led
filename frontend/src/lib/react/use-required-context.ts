import { type Context, useContext } from "react";

/** Read a context that has no meaningful default: using it outside its provider is a programming error. */
export function useRequiredContext<T>(context: Context<T | null>, hook: string): T {
  const value = useContext(context);
  if (value === null) throw Error(`${hook} must be used inside its provider`);
  return value;
}
