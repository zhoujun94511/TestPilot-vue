export function triggerBlobDownload(blob: Blob, filename: string, fallbackName = 'download.bin') {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function triggerTextDownload(
  content: string,
  filename: string,
  mimeType = 'application/json;charset=utf-8'
) {
  triggerBlobDownload(new Blob([content], { type: mimeType }), filename, 'download.txt');
}
