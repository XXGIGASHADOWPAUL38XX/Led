import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-md text-xs transition-colors focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-default disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        default: "bg-primary/15 text-violet-200 hover:bg-primary/25",
        outline: "border border-border text-zinc-300 hover:bg-white/5",
        ghost: "hover:bg-white/5",
        destructive: "text-rose-300 hover:bg-rose-400/10",
        dashed: "border border-dashed border-primary/25 text-violet-300 hover:bg-primary/10",
        link: "text-violet-300 hover:text-violet-200",
      },
      size: {
        default: "px-3 py-2",
        sm: "px-2 py-1",
        icon: "p-1.5",
        inline: "px-1",
      },
    },
    compoundVariants: [
      // In lists, a column of red icons is noise: destructive icons stay quiet until hovered.
      { variant: "destructive", size: "icon", className: "text-muted-foreground hover:text-rose-300" },
    ],
    defaultVariants: { variant: "default", size: "default" },
  },
);

function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { Button };
