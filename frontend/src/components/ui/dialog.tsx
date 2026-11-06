import { Dialog as DialogPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogClose = DialogPrimitive.Close;
const DialogTitle = DialogPrimitive.Title;

function DialogContent({ className, ...props }: ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/65" />
      <DialogPrimitive.Content
        className={cn(
          "fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 rounded-xl border border-white/15 bg-card p-5 text-zinc-200 shadow-2xl outline-none",
          className,
        )}
        {...props}
      />
    </DialogPrimitive.Portal>
  );
}

export { Dialog, DialogClose, DialogContent, DialogTitle };
