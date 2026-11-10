import { parseAcceptance, parseImageStatus, parseIntakeState, readBoundedResponse, readImageJson, verifyRgb } from './image-protocol.ts';
import type { ImageStatus } from './image-protocol.ts';
import { adoptOperatorState, adoptPaintedPreview, createImageState, currentPending, disconnectImage, identity, invalidatePreview, moderationGates, sameTuple } from './image-state.ts';
import type { ImageState, Painted } from './image-state.ts';
import { clearPreview, createGuestView, createOperatorView, paintRgb, renderOperator, remainingText, statusText } from './image-view.ts';

class HttpError extends Error { status: number; constructor(status: number) { super('Bildanfrage abgelehnt'); this.status = status; } }
function readable(window: Window): boolean { return !window.document.hidden && window.navigator.onLine !== false; }
async function request(window: Window, path: string, token: string, signal: AbortSignal,
  body?: File | Record<string, unknown>): Promise<Response> {
  const raw = typeof File !== 'undefined' && body instanceof File;
  return window.fetch(path, { method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': raw ? (body as File).type : 'application/json' }) },
    ...(body === undefined ? {} : { body: raw ? body : JSON.stringify(body) }),
    cache: 'no-store', credentials: 'omit', redirect: 'error', signal });
}
function message(status: number): string {
  if (status === 409) return 'Gerade ist bereits ein Bild in Prüfung. Versuche es später.';
  if (status === 429) return 'Zu viele Anfragen. Bitte kurz warten.';
  if (status === 400 || status === 413 || status === 415) return 'Wähle ein JPEG oder PNG bis 2 MiB.';
  return 'Bildannahme derzeit nicht verfügbar.';
}
function listen(target: EventTarget, name: string, callback: EventListener, disposers: (() => void)[]): void {
  target.addEventListener(name, callback); disposers.push(() => target.removeEventListener(name, callback));
}
export function startGuest(root: HTMLElement): () => void {
  const document = root.ownerDocument, window = document.defaultView!;
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  window.history.replaceState(null, '', window.location.pathname + window.location.search);
  const candidate = fragment.get('guest');
  const token = fragment.size === 1 && candidate && /^ig\.[A-Za-z0-9_-]{43}$/.test(candidate) ? candidate : null;
  const view = createGuestView(root), disposers: (() => void)[] = [];
  let stopped = false, uncertain = false, busy = false, receipt: { id: string; incarnation: string; token: string } | null = null;
  let timer: number | undefined, active: AbortController | null = null, serial = 0;
  if (!token) { view.feedback.textContent = 'Dieser Bildzugang fehlt oder ist ungültig. Öffne den bereitgestellten lokalen Link.'; view.send.disabled = true; }
  function schedule() { window.clearTimeout(timer); if (!stopped && receipt) timer = window.setTimeout(() => { void poll(); }, 2000); }
  async function withDeadline<T>(action: (signal: AbortSignal) => Promise<T>): Promise<T> {
    const controller = new AbortController(); active = controller;
    const deadline = window.setTimeout(() => controller.abort(), 5000);
    try { return await action(controller.signal); }
    finally { window.clearTimeout(deadline); if (active === controller) active = null; }
  }
  async function poll() {
    if (stopped || busy || !receipt) return;
    if (!readable(window)) { view.feedback.textContent = 'Aktueller Bildstatus unbekannt.'; schedule(); return; }
    busy = true; const current = receipt, operation = ++serial;
    try {
      const status = await withDeadline(async signal => {
        const response = await request(window, `/api/images/status/${current.id}`, current.token, signal);
        if (!response.ok) throw new HttpError(response.status);
        return parseImageStatus(await readImageJson(response));
      });
      if (stopped || operation !== serial || receipt !== current) return;
      if (status.id !== current.id || status.incarnation !== current.incarnation) throw new Error('Falsche Bildidentität');
      view.feedback.textContent = `${statusText(status)} ${remainingText(status)}`.trim();
      if (status.status === 'rejected' || status.status === 'expired') { receipt = null; view.send.disabled = false; }
    } catch (error) {
      if (stopped || operation !== serial) return;
      if (error instanceof HttpError && (error.status === 401 || error.status === 404)) {
        view.feedback.textContent = 'Bildstatus nicht mehr verfügbar.'; receipt = null; view.send.disabled = false;
      } else view.feedback.textContent = 'Aktueller Bildstatus unbekannt.';
    } finally { busy = false; schedule(); }
  }
  async function upload() {
    if (!token || stopped || busy || uncertain || receipt || !readable(window)) return;
    const file = view.file.files?.[0];
    if (!file || !['image/jpeg', 'image/png'].includes(file.type) || file.size < 1 || file.size > 2097152) {
      view.feedback.textContent = 'Wähle ein JPEG oder PNG bis 2 MiB.'; return;
    }
    busy = true; receipt = null; const operation = ++serial; view.send.disabled = true; view.feedback.textContent = 'Bild wird gesendet …';
    try {
      const accepted = await withDeadline(async signal => {
        const response = await request(window, '/api/images', token, signal, file);
        if (!response.ok) throw new HttpError(response.status);
        return parseAcceptance(await readImageJson(response));
      });
      if (stopped || operation !== serial) return;
      receipt = { id: accepted.image.id, incarnation: accepted.image.incarnation, token: accepted.status_capability };
      view.feedback.textContent = statusText(accepted.image); schedule();
    } catch (error) {
      if (stopped || operation !== serial) return;
      if (error instanceof HttpError) { view.feedback.textContent = message(error.status); return; }
      uncertain = true;
      view.feedback.textContent = 'Ob dein Bild angekommen ist, ist unbekannt. Es wird nicht automatisch erneut gesendet.';
    } finally { busy = false; view.send.disabled = !token || uncertain || !!receipt; }
  }
  listen(view.send, 'click', () => { void upload(); }, disposers);
  function interrupt() {
    serial++; active?.abort();
    if (busy && !receipt) {
      uncertain = true; view.send.disabled = true;
      view.feedback.textContent = 'Ob dein Bild angekommen ist, ist unbekannt. Es wird nicht automatisch erneut gesendet.';
    } else if (receipt) view.feedback.textContent = 'Aktueller Bildstatus unbekannt.';
  }
  listen(window, 'offline', interrupt, disposers);
  listen(window, 'online', () => { if (receipt) void poll(); }, disposers);
  listen(document, 'visibilitychange', () => { if (!readable(window)) interrupt(); else if (receipt) void poll(); }, disposers);
  return () => { stopped = true; serial++; active?.abort(); window.clearTimeout(timer); for (const dispose of disposers) dispose(); receipt = null; };
}

export function startOperatorImage(root: HTMLElement, operatorToken: string): () => void {
  const document = root.ownerDocument, window = document.defaultView!;
  const view = createOperatorView(root), disposers: (() => void)[] = [];
  let state: ImageState = createImageState(), stopped = false, hidden = false, busy = false;
  let timer: number | undefined, clockTimer: number | undefined, active: AbortController | null = null;
  let serial = 0, activeMutation: number | null = null, feedback: string | undefined;
  let retry: { id: string; incarnation: string; action_id: string; approved: boolean; tuple: Painted | null } | null = null;
  function render() {
    if (state.receivedAtMs !== null && window.performance.now() - state.receivedAtMs >= 5000 && state.painted) {
      state = invalidatePreview(state); clearPreview(view.canvas);
    }
    renderOperator(view, state, window.performance.now(), feedback, retry);
  }
  function schedule() { window.clearTimeout(timer); if (!stopped && !hidden) timer = window.setTimeout(() => { void poll(); }, 2000); }
  async function fetchBounded(path: string, body?: Record<string, unknown>, rgb = false): Promise<{ response: Response; bytes?: Uint8Array; json?: unknown }> {
    const controller = new AbortController(); active = controller;
    const deadline = window.setTimeout(() => controller.abort(), 5000);
    try {
      const response = await request(window, path, operatorToken, controller.signal, body);
      if (!response.ok) return { response };
      if (rgb) return { response, bytes: await readBoundedResponse(response, 12288, true) };
      return { response, json: await readImageJson(response) };
    } finally { window.clearTimeout(deadline); if (active === controller) active = null; }
  }
  async function preview(tuple: Painted, operation: number, generation: number) {
    try {
      const result = await fetchBounded(`/api/images/preview/${tuple.id}/${tuple.frame_sha256}`, undefined, true);
      if (!result.response.ok || !result.bytes) throw new HttpError(result.response.status);
      await verifyRgb(result.bytes, tuple.frame_sha256, window.crypto);
      if (stopped || operation !== serial || generation !== state.generation || !readable(window) ||
        state.receivedAtMs === null || window.performance.now() - state.receivedAtMs >= 5000 ||
        !sameTuple(identity(currentPending(state)!), tuple)) return;
      if (!paintRgb(view.canvas, result.bytes)) throw new Error('Canvas nicht verfügbar');
      state = adoptPaintedPreview(state, tuple, generation); feedback = undefined; render();
    } catch {
      if (stopped || operation !== serial) return;
      state = invalidatePreview(state); clearPreview(view.canvas);
      feedback = 'Vorschau nicht verfügbar. Freigabe gesperrt.'; render();
    }
  }
  async function poll() {
    if (stopped || hidden || busy) return;
    if (!readable(window)) { state = disconnectImage(state); feedback = undefined; render(); schedule(); return; }
    busy = true; const operation = ++serial, generation = state.generation;
    try {
      const result = await fetchBounded('/api/images/state');
      if (result.response.status === 404 && state.state === null) { hidden = true; view.root.hidden = true; return; }
      if (!result.response.ok) throw new HttpError(result.response.status);
      const next = parseIntakeState(result.json);
      if (stopped || operation !== serial || generation !== state.generation) return;
      const previous = currentPending(state), previousTuple = previous ? identity(previous) : null;
      state = adoptOperatorState(state, next, window.performance.now(), generation);
      const pending = currentPending(state), tuple = pending ? identity(pending) : null;
      if (!sameTuple(previousTuple, tuple) || pending?.status !== 'accepted') clearPreview(view.canvas);
      if (retry && (retry.id !== pending?.id || retry.incarnation !== pending.incarnation ||
        !sameTuple(retry.tuple, tuple))) retry = null;
      feedback = undefined; render();
      if (tuple && pending?.status === 'accepted' && pending.detail === 'awaiting_approval' && pending.preview_available && !state.painted)
        await preview(tuple, operation, state.generation);
    } catch {
      if (stopped || operation !== serial) return;
      state = disconnectImage(state); clearPreview(view.canvas); feedback = undefined; render();
    } finally { busy = false; schedule(); }
  }
  async function moderate(approved: boolean, previous?: typeof retry) {
    const gates = moderationGates(state, window.performance.now());
    if (stopped || busy || !readable(window) || !(approved ? gates.approve : gates.reject)) return;
    const pending = currentPending(state)!;
    if (previous && (previous.id !== pending.id || previous.incarnation !== pending.incarnation || previous.approved !== approved ||
      !sameTuple(previous.tuple, identity(pending)))) return;
    const action = previous ?? { id: pending.id, incarnation: pending.incarnation,
      action_id: window.crypto.randomUUID(), approved, tuple: identity(pending) };
    retry = null; busy = true; state = { ...invalidatePreview(state), pendingMutation: true };
    clearPreview(view.canvas); feedback = 'Bildentscheidung wird gesendet …'; render();
    const operation = ++serial, generation = state.generation;
    activeMutation = operation;
    try {
      const result = await fetchBounded(`/api/images/moderate/${action.id}`,
        { incarnation: action.incarnation, action_id: action.action_id, approved });
      if (!result.response.ok) throw new HttpError(result.response.status);
      const reply = parseImageStatus(result.json);
      if (stopped || operation !== serial || generation !== state.generation) return;
      if (reply.id !== action.id || reply.incarnation !== action.incarnation || currentPending(state)?.id !== action.id) throw new Error('Falsche Bildidentität');
      // A moderation reply describes this receipt; a fresh state probe determines the active pane.
      feedback = statusText(reply); state = { ...state, pendingMutation: false };
    } catch {
      if (stopped || operation !== serial) return;
      retry = action; state = { ...state, pendingMutation: false };
      feedback = 'Ergebnis der Bildentscheidung unbekannt.';
    } finally {
      if (activeMutation === operation) {
        activeMutation = null; state = { ...state, pendingMutation: false }; busy = false;
        if (!stopped) { render(); void poll(); }
      }
    }
  }
  listen(view.approve, 'click', () => { void moderate(true); }, disposers);
  listen(view.reject, 'click', () => { void moderate(false); }, disposers);
  listen(view.retry, 'click', () => { if (retry) void moderate(retry.approved, retry); }, disposers);
  listen(window, 'offline', () => { active?.abort(); state = disconnectImage(state); clearPreview(view.canvas); render(); }, disposers);
  listen(window, 'online', () => { void poll(); }, disposers);
  listen(document, 'visibilitychange', () => { if (!readable(window)) { active?.abort(); state = disconnectImage(state); clearPreview(view.canvas); render(); } else void poll(); }, disposers);
  function tick() { if (stopped) return; render(); clockTimer = window.setTimeout(tick, 250); }
  clockTimer = window.setTimeout(tick, 250); void poll();
  return () => { stopped = true; serial++; active?.abort(); window.clearTimeout(timer); window.clearTimeout(clockTimer);
    for (const dispose of disposers) dispose(); clearPreview(view.canvas); state = disconnectImage(state); render(); };
}
