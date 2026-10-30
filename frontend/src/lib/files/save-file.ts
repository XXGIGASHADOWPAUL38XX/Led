type SavePickerWindow = Window & {
  showSaveFilePicker?: (options: { suggestedName: string; types: { description: string; accept: Record<string, string[]> }[] }) => Promise<FileSystemFileHandle>;
};

/** Open the native dialog during the click gesture, before awaiting backend data. */
export async function saveFile(filename: string, bytes: () => Promise<Uint8Array>): Promise<string> {
  const browser = window as SavePickerWindow;
  if (browser.showSaveFilePicker) {
    const handle = await browser.showSaveFilePicker({ suggestedName: filename,
      types: [{ description: 'LED node template', accept: { 'application/octet-stream': ['.led'] } }],
    });
    const data = await bytes();
    const writable = await handle.createWritable();
    await writable.write(Uint8Array.from(data));
    await writable.close();
    return handle.name;
  }
  const data = await bytes();
  const url = URL.createObjectURL(new Blob([Uint8Array.from(data)], { type: 'application/octet-stream' }));
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}
