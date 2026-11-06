import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { fieldClassName } from "./input";

function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(fieldClassName, "resize-y px-3 py-2 text-xs", className)} {...props} />;
}

export { Textarea };
