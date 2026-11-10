import type { AnyImageStatus as ImageStatus } from './image-protocol.ts';
import type { ImageState } from './image-state.ts';
import { moderationGates } from './image-state.ts';
import type { NativeState } from './native-state.ts';
import { nativeFreshness } from './native-state.ts';
import { groups } from './native-protocol.ts';

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
  if (status.schema !== 'market-image-status-wire/v1') {
    if (status.detail === 'ready') return 'Bild freigegeben. Wartet auf ein freies Modellintervall.';
    if (status.detail === 'dispatching') return 'Bildübergabe angefragt. Modellstart noch unbestätigt.';
    if (status.detail === 'processing') return `${status.completed_observations}/8 Modellintervalle verarbeitet. Bild wird verarbeitet.`;
    if (status.detail === 'completed') return '8/8 Modellintervalle verarbeitet.';
    if (status.detail === 'worker_outcome_unknown') return `Ergebnis unbekannt. ${status.completed_observations}/8 Modellintervalle bestätigt.`;
    if (status.status === 'rejected' && status.worker_session !== null)
      return `${detailText[status.detail]} ${status.completed_observations}/8 Modellintervalle bestätigt.`;
  }
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
export type GuestView = { file: HTMLInputElement; send: HTMLButtonElement; feedback: HTMLElement; scope: HTMLElement; guidance: HTMLElement; root: HTMLElement };
export function createGuestView(root: HTMLElement): GuestView {
  const document = root.ownerDocument;
  root.classList.add('market-image-guest');
  const heading = node(document, 'h1', 'Bild senden');
  const label = node(document, 'p', 'Lokaler Bildtest — Verbindung wird beim Senden geprüft'); label.className = 'image-scope';
  const guidance = node(document, 'p', 'Die Bedienperson prüft eine verkleinerte Vorschau. Der bestätigte Bildstatus zeigt, ob das Bild verarbeitet wurde.');
  const fileLabel = node(document, 'label', 'Bilddatei'); const file = node(document, 'input');
  file.type = 'file'; file.accept = 'image/jpeg,image/png'; fileLabel.append(file);
  const help = node(document, 'p', 'JPEG oder PNG, höchstens 2 MiB.');
  const send = node(document, 'button', 'Bild senden'); send.type = 'button';
  const feedback = node(document, 'p', 'Wähle ein Bild zum Senden.'); feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
  root.append(heading, label, guidance, fileLabel, help, send, feedback);
  return { file, send, feedback, scope: label, guidance, root };
}
export type OperatorView = { root: HTMLElement; scope: HTMLElement; canvas: HTMLCanvasElement; status: HTMLElement;
  timing: HTMLElement; approve: HTMLButtonElement; reject: HTMLButtonElement; retry: HTMLButtonElement };
export function createOperatorView(root: HTMLElement): OperatorView {
  const document = root.ownerDocument;
  const section = node(document, 'section'); section.className = 'market-image-operator';
  const scope = node(document, 'p', 'Lokaler Bildtest — Simulation nicht verbunden');
  section.append(node(document, 'h2', 'Bildprüfung'), scope);
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
  return { root: section, scope, canvas, status, timing, approve, reject, retry };
}
export function renderOperator(view: OperatorView, value: ImageState, now: number, feedback?: string,
  retry?: { approved: boolean } | null, nativeReady = true): void {
  const pending = value.state?.pending;
  const gates = moderationGates(value, now);
  view.approve.disabled = !gates.approve || !!retry || !nativeReady; view.reject.disabled = !gates.reject || !!retry || !nativeReady;
  view.retry.hidden = !retry;
  view.retry.disabled = !retry || !(retry.approved ? gates.approve : gates.reject) || !nativeReady;
  if (retry) view.retry.textContent = retry.approved ? 'Freigabe erneut bestätigen' : 'Ablehnung erneut bestätigen';
  const stale = value.disconnected || value.receivedAtMs === null || now - value.receivedAtMs >= 5000;
  if (view.scope) view.scope.textContent = value.state?.schema === 'market-image-intake/v3' ? 'Lokaler Live-Pilot — experimenteller konfigurierter Motor-Readout.' : value.state?.schema === 'market-image-intake/v2' ? 'Lokaler neuronaler Bildtest — Preise weiterhin synthetisch.' : 'Lokaler Bildtest — Simulation nicht verbunden';
  const active = value.state && value.state.schema !== 'market-image-intake/v1' ? value.state.active : null;
  const text = feedback ?? (stale ? value.state && value.state.schema !== 'market-image-intake/v1' ? 'Verbindung unklar. Bildentscheidungen gesperrt.' : 'Aktueller Bildstatus unbekannt.' : value.state?.health === 'stopping' ? 'Lokaler Bildtest beendet.' :
    value.state?.health === 'faulted' ? 'Bildannahme derzeit nicht verfügbar.' : !nativeReady ? 'Verbindung unklar. Bildentscheidungen gesperrt.' : pending ? statusText(pending) : active ? statusText(active) : 'Kein Bild zur Prüfung.');
  if (view.status.textContent !== text) view.status.textContent = text;
  const time = !stale && pending ? remainingText(pending) : '';
  if (view.timing.textContent !== time) view.timing.textContent = time;
  if (!value.painted) { clearPreview(view.canvas); view.canvas.hidden = true; } else view.canvas.hidden = false;
}

export type NativeView = { root: HTMLElement; scope: HTMLElement; status: HTMLElement; timing: HTMLElement; input: HTMLElement;
  rows: { count: HTMLElement; rate: HTMLElement }[] };
export function createNativeView(root: HTMLElement): NativeView {
  const document = root.ownerDocument, section = node(document, 'section'); section.className = 'market-native'; section.hidden = true;
  const heading = node(document, 'h2', 'Neuronaler Bildtest');
  const scope = node(document, 'p', 'Lokaler neuronaler Bildtest — Preise weiterhin synthetisch.');
  const status = node(document, 'p', 'Noch keine bestätigte Messung.'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const timing = node(document, 'p'), input = node(document, 'p');
  const table = node(document, 'table'); table.setAttribute('aria-label', 'Letzte bestätigte Gruppenmessung über 500 ms');
  const head = node(document, 'thead'), labels = node(document, 'tr');
  for (const label of ['Gruppe', 'Spikes / 500 ms', 'Rate / Hz']) { const cell = node(document, 'th', label); cell.setAttribute('scope', 'col'); labels.append(cell); }
  head.append(labels); const body = node(document, 'tbody');
  const rows = groups.map(group => {
    const row = node(document, 'tr'), name = node(document, 'th', group), count = node(document, 'td', '—'), rate = node(document, 'td', '—');
    name.setAttribute('scope', 'row'); row.append(name, count, rate); body.append(row); return { count, rate };
  });
  table.append(head, body); section.append(heading, scope, status, timing, input, table); root.append(section);
  return { root: section, scope, status, timing, input, rows };
}
export function renderNative(view: NativeView, value: NativeState, now: number): void {
  const snapshot = value.snapshot, fresh = nativeFreshness(value, now);
  view.scope.textContent = snapshot?.schema === 'market-native-state/v2' ? 'Experimenteller konfigurierter Motor-Readout — lokale Testpreise, keine biologische Validierung.' : 'Lokaler neuronaler Bildtest — Preise weiterhin synthetisch.';
  const phases = { starting: 'Modellstart ausstehend', running: 'Modelltest läuft', stopping: 'Modelltest wird beendet', ended: 'Modelltest beendet', faulted: 'Modelltest gestoppt' };
  view.status.textContent = !fresh.transport ? 'Verbindung unklar' : `${phases[snapshot!.state]}${snapshot!.fault ? ` (${snapshot!.fault})` : ''}${snapshot!.time_uncertain ? ' · Messalter unbekannt' : snapshot!.observations_completed === 0 ? ' · Noch keine bestätigte Messung' : !fresh.measurement ? ' · Messung veraltet' : ''}.`;
  view.root.setAttribute('data-live', String(fresh.live));
  view.timing.textContent = snapshot ? `Modellzeit: ${(snapshot.model_ms / 1000).toFixed(1)} / ${snapshot.model_limit_ms / 1000} s (Modelllimit). Messalter: ${fresh.ageMs === null ? 'unbekannt' : `${(fresh.ageMs / 1000).toFixed(1)} s`}.` : 'Modellzeit und Messalter unbekannt.';
  view.input.textContent = !snapshot?.input_kind ? 'Noch kein gemessener Eingang.' : snapshot.input_kind === 'black' ?
    'Letzte Messung: schwarzes Bild.' : `Letzte Messung: Bild ${snapshot.image_id}. Die Freigabevorschau zeigt den getrennten Prüfauftrag.`;
  groups.forEach((group, index) => {
    view.rows[index].count.textContent = snapshot?.group_spikes ? String(snapshot.group_spikes[group]) : '—';
    view.rows[index].rate.textContent = snapshot?.group_rates_hz ? snapshot.group_rates_hz[group].toFixed(3) : '—';
  });
}
