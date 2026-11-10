import type { ImageStatus } from './image-protocol.ts';
import type { ImageState } from './image-state.ts';
import { moderationGates } from './image-state.ts';

function node<K extends keyof HTMLElementTagNameMap>(document: Document, tag: K, text?: string): HTMLElementTagNameMap[K] {
  const item = document.createElement(tag); if (text !== undefined) item.textContent = text; return item;
}
const detailText: Record<string, string> = {
  decoding: 'Bild empfangen. Vorschau wird vorbereitet.', awaiting_approval: 'Wartet auf Freigabe.',
  ready: 'Bild freigegeben. Wartet ohne angeschlossene Simulation.',
  ttl_expired: 'Bild abgelaufen. Es wurde keiner Simulation übergeben.',
  decode_failed: 'Bild konnte nicht gelesen werden.', decode_timeout: 'Zeit zum Einlesen überschritten.',
  moderation_rejected: 'Bild abgelehnt.', moderation_timeout: 'Frist zur Freigabe abgelaufen.',
  worker_failed: 'Bildannahme wegen eines technischen Fehlers gestoppt.',
  session_ended: 'Lokaler Bildtest beendet.', clock: 'Zeitprüfung fehlgeschlagen. Bildannahme gestoppt.',
};
export function statusText(status: ImageStatus): string {
  return Object.hasOwn(detailText, status.detail) ? detailText[status.detail] : 'Aktueller Bildstatus unbekannt.';
}
export function remainingText(status: ImageStatus): string {
  if (status.time_uncertain) return 'Verbleibende Zeit unbekannt.';
  if (status.status === 'accepted' && status.detail === 'awaiting_approval')
    return `Freigabe noch ca. ${Math.ceil((status.remaining_moderation_ms ?? 0) / 1000)} s möglich`;
  if (status.status === 'queued') return `Verbleibende Gesamtfrist: ca. ${Math.ceil((status.remaining_handoff_ms ?? 0) / 60000)} Min.`;
  return '';
}
export function paintRgb(canvas: HTMLCanvasElement, rgb: Uint8Array): boolean {
  if (rgb.length !== 12288 || canvas.width !== 64 || canvas.height !== 64) return false;
  const context = canvas.getContext('2d'); if (!context) return false;
  const pixels = new Uint8ClampedArray(64 * 64 * 4);
  for (let i = 0, j = 0; i < rgb.length; i += 3, j += 4) {
    pixels[j] = rgb[i]; pixels[j + 1] = rgb[i + 1]; pixels[j + 2] = rgb[i + 2]; pixels[j + 3] = 255;
  }
  const ImageDataClass = canvas.ownerDocument.defaultView!.ImageData;
  context.putImageData(new ImageDataClass(pixels, 64, 64), 0, 0); return true;
}
export function clearPreview(canvas: HTMLCanvasElement): void { canvas.getContext('2d')?.clearRect(0, 0, 64, 64); }
export type GuestView = { file: HTMLInputElement; send: HTMLButtonElement; feedback: HTMLElement; root: HTMLElement };
export function createGuestView(root: HTMLElement): GuestView {
  const document = root.ownerDocument;
  root.classList.add('market-image-guest');
  const heading = node(document, 'h1', 'Bild senden');
  const label = node(document, 'p', 'Lokaler Bildtest — Simulation nicht verbunden'); label.className = 'image-scope';
  const guidance = node(document, 'p', 'Die Bedienperson prüft eine verkleinerte Vorschau. Dein Bild verändert hier keine Getränkepreise.');
  const fileLabel = node(document, 'label', 'Bilddatei'); const file = node(document, 'input');
  file.type = 'file'; file.accept = 'image/jpeg,image/png'; fileLabel.append(file);
  const help = node(document, 'p', 'JPEG oder PNG, höchstens 2 MiB.');
  const send = node(document, 'button', 'Bild senden'); send.type = 'button';
  const feedback = node(document, 'p', 'Wähle ein Bild zum Senden.'); feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
  root.append(heading, label, guidance, fileLabel, help, send, feedback);
  return { file, send, feedback, root };
}
export type OperatorView = { root: HTMLElement; canvas: HTMLCanvasElement; status: HTMLElement;
  timing: HTMLElement; approve: HTMLButtonElement; reject: HTMLButtonElement; retry: HTMLButtonElement };
export function createOperatorView(root: HTMLElement): OperatorView {
  const document = root.ownerDocument;
  const section = node(document, 'section'); section.className = 'market-image-operator';
  section.append(node(document, 'h2', 'Bildprüfung'), node(document, 'p', 'Lokaler Bildtest — Simulation nicht verbunden'));
  const body = node(document, 'div'); body.className = 'market-image-review';
  const canvas = node(document, 'canvas'); canvas.width = 64; canvas.height = 64; canvas.hidden = true;
  canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', 'Geprüfte verkleinerte Vorschau, 64 × 64 Pixel');
  const content = node(document, 'div');
  const status = node(document, 'p', 'Kein Bild zur Prüfung.'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const timing = node(document, 'p', '');
  const actions = node(document, 'div'); actions.className = 'market-image-actions';
  const approve = node(document, 'button', 'Bild freigeben'), reject = node(document, 'button', 'Bild ablehnen');
  const retry = node(document, 'button', 'Freigabe erneut bestätigen');
  for (const button of [approve, reject, retry]) { button.type = 'button'; button.disabled = true; }
  retry.hidden = true; actions.append(approve, reject, retry); content.append(status, timing, actions); body.append(canvas, content);
  section.append(body); root.append(section);
  return { root: section, canvas, status, timing, approve, reject, retry };
}
export function renderOperator(view: OperatorView, value: ImageState, now: number, feedback?: string,
  retry?: { approved: boolean } | null): void {
  const pending = value.state?.pending;
  const gates = moderationGates(value, now);
  view.approve.disabled = !gates.approve || !!retry; view.reject.disabled = !gates.reject || !!retry;
  view.retry.hidden = !retry;
  view.retry.disabled = !retry || !(retry.approved ? gates.approve : gates.reject);
  if (retry) view.retry.textContent = retry.approved ? 'Freigabe erneut bestätigen' : 'Ablehnung erneut bestätigen';
  const stale = value.disconnected || value.receivedAtMs === null || now - value.receivedAtMs >= 5000;
  const text = feedback ?? (stale ? 'Aktueller Bildstatus unbekannt.' : value.state?.health === 'stopping' ? 'Lokaler Bildtest beendet.' :
    value.state?.health === 'faulted' ? 'Bildannahme derzeit nicht verfügbar.' : pending ? statusText(pending) : 'Kein Bild zur Prüfung.');
  if (view.status.textContent !== text) view.status.textContent = text;
  const time = !stale && pending ? remainingText(pending) : '';
  if (view.timing.textContent !== time) view.timing.textContent = time;
  if (!value.painted) { clearPreview(view.canvas); view.canvas.hidden = true; } else view.canvas.hidden = false;
}
