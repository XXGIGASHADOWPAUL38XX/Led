import { createContext } from "react";

/** Port state shared with every Terminal inside the canvas; keys come from terminalKey(). */
export const WorkspaceContext = createContext<{
  compatible: ReadonlySet<string> | null;
  origin: string | null;
  linked: ReadonlySet<string>;
  selectPort: (key: string, extend: boolean) => void;
  disconnect: (key: string) => void;
} | null>(null);
