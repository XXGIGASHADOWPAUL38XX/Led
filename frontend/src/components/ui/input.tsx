import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Boxed field look shared by Input and Textarea; the focus ring matches the node fields (CoreElement). */
export const fieldClassName =
  "w-full rounded-md border border-border bg-black/20 text-zinc-200 outline-none transition-colors placeholder:text-zinc-600 focus:border-violet-400/70 focus:ring-2 focus:ring-violet-400/15 disabled:opacity-40";

function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(fieldClassName, "px-2.5 py-1.5 text-xs", className)} {...props} />;
}

export { Input };
