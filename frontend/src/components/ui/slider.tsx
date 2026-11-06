import { Slider as SliderPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const looks = {
  // A thin track with round handles, for standalone ranges and seek bars.
  bar: {
    root: "relative flex h-4 w-full touch-none items-center select-none data-[disabled]:opacity-40",
    track: "relative h-1 w-full overflow-hidden rounded-full bg-white/10",
    range: "absolute h-full rounded-full bg-primary",
    thumb:
      "block size-3 rounded-full bg-violet-200 shadow outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card",
  },
  // Fills a node field row (CoreElement): the value is the shaded area, the handle shows on hover or focus.
  fill: {
    root: "absolute inset-0 flex cursor-ew-resize touch-none items-center rounded-[inherit] select-none",
    track: "relative h-full w-full overflow-hidden rounded-[inherit]",
    range:
      "absolute inset-y-0 bg-gradient-to-r from-violet-500/25 to-violet-400/45 group-hover:from-violet-500/35 group-hover:to-violet-400/55",
    thumb:
      "block h-7 w-0.5 rounded-full bg-violet-200/70 opacity-0 transition-opacity outline-none group-hover:opacity-100 focus:opacity-100",
  },
};

type ThumbProps = ComponentProps<typeof SliderPrimitive.Thumb>;

/** One handle per value; `thumbs[i]` carries the accessible name of handle i. */
function Slider({
  look = "bar",
  thumbs,
  className,
  ...props
}: ComponentProps<typeof SliderPrimitive.Root> & { look?: keyof typeof looks; thumbs: ThumbProps[] }) {
  const classes = looks[look];
  return (
    <SliderPrimitive.Root className={cn(classes.root, className)} {...props}>
      <SliderPrimitive.Track className={classes.track}>
        <SliderPrimitive.Range className={classes.range} />
      </SliderPrimitive.Track>
      {thumbs.map((thumb, index) => (
        <SliderPrimitive.Thumb key={index} className={classes.thumb} {...thumb} />
      ))}
    </SliderPrimitive.Root>
  );
}

export { Slider };
