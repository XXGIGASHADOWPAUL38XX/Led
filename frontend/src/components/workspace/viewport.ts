export const MIN_ZOOM = 0.1;
export const MAX_ZOOM = 2;
export const clampZoom = (zoom: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
export function zoomScroll(scroll: number, anchor: number, previous: number, next: number) {
  return (scroll + anchor) * next / previous - anchor;
}
