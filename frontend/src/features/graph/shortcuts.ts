export function isTyping() {
  return Boolean(document.activeElement?.closest("input, textarea, select, [contenteditable=true], [role=combobox]"));
}

/** Canvas shortcuts stay off while a modal dialog covers the canvas. */
export function isDialogOpen() {
  return Boolean(document.querySelector("[role=dialog]"));
}
