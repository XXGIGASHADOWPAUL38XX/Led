import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Joins class names; on a Tailwind conflict the last class wins, so callers can override a component's defaults. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
