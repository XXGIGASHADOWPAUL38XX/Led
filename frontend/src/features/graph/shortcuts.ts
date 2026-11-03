export function isTyping() {
  return Boolean(document.activeElement?.closest("input, textarea, select, [contenteditable=true], [role=combobox]"));
}
