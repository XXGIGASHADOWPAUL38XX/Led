import { Switch as SwitchPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

function Switch({ className, ...props }: ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        "group/switch flex items-center justify-end transition-colors outline-none data-[state=checked]:bg-violet-400/10",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="relative h-4 w-8 rounded-full bg-white/10 ring-1 ring-white/10 transition-colors group-data-[state=checked]/switch:bg-violet-500/70 group-data-[state=checked]/switch:ring-violet-300/30"
      >
        <SwitchPrimitive.Thumb className="absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-zinc-400 shadow-sm transition-[transform,background-color] data-[state=checked]:translate-x-4 data-[state=checked]:bg-violet-100 motion-reduce:transition-none" />
      </span>
    </SwitchPrimitive.Root>
  );
}

export { Switch };
