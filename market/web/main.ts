import { parseAckReply, parseClaimReply, parsePauseReply, parseProposalResult, parseResumeReply, parseSnapshot } from './protocol.ts';
import type { Snapshot } from './protocol.ts';
import { applySnapshot, createState, disconnect, isFresh } from './state.ts';
import { element, renderBoard } from './render.ts';
import { startOperatorImage } from './image-main.ts';

type Mutation = { path: string; body: Record<string, unknown>; kind: 'claim' | 'pause' | 'resume' | 'fixture' };
class HttpError extends Error {
  status: number;
  constructor(status: number) { super('Serveranfrage abgelehnt'); this.status = status; }
}

export function startBoard(root: HTMLElement): () => void {
  const document = root.ownerDocument, window = document.defaultView!;
  // Read once, erase before any network operation, retain only in this closure.
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  window.history.replaceState(null, '', window.location.pathname + window.location.search);
  const operator = fragment.get('operator'), view = fragment.get('view');
  const validCapability = (value: string | null): value is string => value !== null && /^[A-Za-z0-9_-]{43}$/.test(value);
  const operatorToken = validCapability(operator) && !view && [...fragment.keys()].length === 1 ? operator : null;
  const readToken = operatorToken ?? (validCapability(view) && !operator && [...fragment.keys()].length === 1 ? view : null);
  let state = createState(), stopped = false, busy = false, serial = 0;
  let pollTimer: number | undefined, clockTimer: number | undefined, requestTimer: number | undefined;
  let controller: AbortController | null = null, uncertain: Mutation | null = null, activeMutation: Mutation | null = null;
  let queuedMutation: Mutation | null = null;
  let feedback: HTMLElement | null = null, retryButton: HTMLButtonElement | null = null;
  let drinkSelect: HTMLSelectElement | null = null, targetInput: HTMLInputElement | null = null;
  let configKey = '';
  let disposeImage: (() => void) | null = null;
  const buttons: HTMLButtonElement[] = [], disposers: (() => void)[] = [];
  const now = () => window.performance.now();
  const visible = () => !document.hidden && window.navigator.onLine !== false;
  const announce = (text: string) => { if (feedback) feedback.textContent = text; };
  function listen(target: EventTarget, name: string, callback: EventListener) {
    target.addEventListener(name, callback); disposers.push(() => target.removeEventListener(name, callback));
  }
  function render() {
    renderBoard(root, state, now());
    // Polling must not disable and blur a focused operator button. A deliberate
    // action during the serial read/ACK cycle queues once and runs after it.
    const enabled = !stopped && visible() && activeMutation === null && queuedMutation === null && isFresh(state, now());
    for (const button of buttons) button.disabled = !enabled;
    if (retryButton) { retryButton.hidden = uncertain === null; retryButton.disabled = !enabled || uncertain === null; }
    if (drinkSelect && targetInput && state.snapshot) {
      const key = `${state.snapshot.config_id}:${state.snapshot.incarnation}`;
      if (configKey !== key) {
        configKey = key;
        drinkSelect.replaceChildren(...state.snapshot.rows.map(row => {
          const option = element(document, 'option', row.name); option.value = row.id; return option;
        }));
        drinkSelect.value = state.snapshot.rows[0].id; updateTarget();
      }
    }
  }
  function updateTarget() {
    const row = state.snapshot?.rows.find(row => row.id === drinkSelect?.value);
    if (row && targetInput) {
      targetInput.min = String(row.minimum_rappen); targetInput.max = String(row.maximum_rappen);
      targetInput.step = String(row.grid_rappen); targetInput.value = String(row.maximum_rappen);
    }
  }
  function schedulePoll() {
    window.clearTimeout(pollTimer);
    if (!stopped && readToken) pollTimer = window.setTimeout(() => { void poll(); }, 1000);
  }
  function invalidate() {
    state = disconnect(state); serial++; controller?.abort(); controller = null;
    window.clearTimeout(requestTimer); requestTimer = undefined;
    if (activeMutation) { uncertain = activeMutation; announce('Ergebnis unbekannt. Dieselbe Aktion kann erneut abgefragt werden.'); }
    activeMutation = null; queuedMutation = null; busy = false; render(); schedulePoll();
  }
  function current(generation: number, operation: number, incarnation?: string): boolean {
    return !stopped && visible() && operation === serial && generation === state.connectionGeneration &&
      (incarnation === undefined || incarnation === state.snapshot?.incarnation);
  }
  async function request(path: string, token: string, body?: Record<string, unknown>): Promise<unknown> {
    const response = await window.fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      cache: 'no-store', credentials: 'omit', redirect: 'error', signal: controller!.signal,
    });
    // Bound wire size before parsing. Error response contents never enter the DOM or logs.
    const text = await response.text();
    if (new TextEncoder().encode(text).length > 65536) throw new Error('Ungültige Serverantwort');
    if (!response.ok) throw new HttpError(response.status);
    return JSON.parse(text) as unknown;
  }
  function begin(): number {
    busy = true; const operation = ++serial; controller = new AbortController();
    window.clearTimeout(pollTimer);
    requestTimer = window.setTimeout(() => { if (operation === serial) invalidate(); }, 5000);
    render(); return operation;
  }
  function finish(operation: number) {
    if (operation !== serial || stopped) return;
    window.clearTimeout(requestTimer); requestTimer = undefined; controller = null; activeMutation = null; busy = false;
    render(); schedulePoll();
    if (queuedMutation) { const mutation = queuedMutation; queuedMutation = null; void mutate(mutation); }
  }
  function accept(snapshot: Snapshot, generation: number, full = false): boolean {
    if (!full && state.snapshot && snapshot.incarnation !== state.snapshot.incarnation) { invalidate(); return false; }
    const previous = state, next = applySnapshot(state, snapshot, now(), generation);
    state = next;
    if (next === previous) return false;
    if (next.connectionGeneration !== generation) {
      // Only full GETs establish a restarted authority. Old session/challenge work is invalid now.
      if (uncertain?.kind === 'claim') uncertain = null;
      queuedMutation = null;
    }
    render(); return true;
  }
  async function acknowledge(operation: number) {
    const session = state.primarySession, challenge = state.snapshot?.challenge;
    const generation = state.connectionGeneration, incarnation = state.snapshot?.incarnation;
    if (!session || !challenge || challenge.session_id !== session.session_id || !current(generation, operation, incarnation) || !isFresh(state, now())) return;
    const reply = parseAckReply(await request('/api/primary/ack', session.primary_token, { session_id: session.session_id, challenge: challenge.id }));
    if (!current(generation, operation, incarnation)) return;
    if (!accept(reply.snapshot, generation)) return;
    if (!reply.accepted) announce(`Anwesenheit nicht bestätigt (${reply.reason}). Vollständiger Stand wird erneut geladen.`);
    // ACK's post-transition snapshot has no new challenge: never recurse or ACK again.
  }
  async function poll() {
    if (stopped || busy || !readToken) return;
    if (!visible()) { schedulePoll(); return; }
    const operation = begin(), generation = state.connectionGeneration;
    try {
      const snapshot = parseSnapshot(await request('/api/snapshot', state.primarySession?.primary_token ?? readToken));
      if (!current(generation, operation)) return;
      if (!accept(snapshot, generation, true)) { invalidate(); return; }
      await acknowledge(operation);
    } catch (error) {
      if (operation === serial && !stopped) {
        // A restarted authority or replacement claim revokes the previous bearer.
        // Reconnect with the original read capability to establish a full incarnation.
        if (error instanceof HttpError && error.status === 401) state = { ...state, primarySession: null };
        invalidate();
      }
    } finally { finish(operation); }
  }
  async function mutate(mutation: Mutation) {
    if (!operatorToken || stopped || !visible() || !isFresh(state, now())) return;
    if (busy) {
      if (!activeMutation && !queuedMutation) { queuedMutation = mutation; render(); }
      return;
    }
    activeMutation = mutation; uncertain = null;
    const operation = begin(), generation = state.connectionGeneration, incarnation = state.snapshot!.incarnation;
    try {
      const raw = await request(mutation.path, operatorToken, mutation.body);
      if (!current(generation, operation, incarnation)) return;
      if (mutation.kind === 'claim') {
        const reply = parseClaimReply(raw);
        if (!accept(reply.snapshot, generation)) return;
        state = { ...state, primarySession: { session_id: reply.session_id, primary_token: reply.primary_token } };
        announce('Primäre Tafel übernommen; Anwesenheit wird nach Darstellung bestätigt.'); render();
        activeMutation = null; await acknowledge(operation);
      } else if (mutation.kind === 'resume') {
        const reply = parseResumeReply(raw); if (!accept(reply.snapshot, generation)) return;
        announce(`${reply.result.status === 'accepted' ? 'Fortsetzen angenommen' : 'Fortsetzen abgelehnt'} (${reply.result.reason}).${reply.superseding_reason ? ' Neuere Pause hat Vorrang.' : ''}`);
      } else if (mutation.kind === 'pause') {
        const reply = parsePauseReply(raw);
        announce(reply.durable ? 'Pause gespeichert. Vollständiger Stand wird neu geladen.' : 'Pause gemeldet; Speicherung unbestätigt. Vollständiger Stand wird neu geladen.');
        // PauseReply is not a complete snapshot and cannot substitute for one.
        state = disconnect(state); render();
      } else {
        const reply = parseProposalResult(raw);
        announce(`Vergangenes Fixture-Ergebnis: ${reply.status} (${reply.reason}), Preisversion ${reply.terminal_price_version}. Aktuelle Preise stehen auf der Tafel.`);
      }
      activeMutation = null; uncertain = null;
    } catch (error) {
      if (operation === serial && !stopped) {
        if (activeMutation) {
          uncertain = mutation; announce('Ergebnis unbekannt. Dieselbe Aktion kann erneut abgefragt werden.');
        }
        if (error instanceof HttpError && error.status === 401) state = { ...state, primarySession: null };
        invalidate();
      }
    } finally { finish(operation); }
  }
  render();
  if (operatorToken) {
    const details = element(document, 'details', '', 'market-operator');
    details.append(element(document, 'summary', 'Bedienung öffnen / schliessen'));
    const actions = element(document, 'div', '', 'market-actions');
    function button(text: string, action: () => void) {
      const node = element(document, 'button', text); node.type = 'button'; buttons.push(node);
      listen(node, 'click', action); actions.append(node); return node;
    }
    const requestId = () => window.crypto.randomUUID();
    button('Primäre Tafel übernehmen', () => { if (state.snapshot) void mutate({ kind: 'claim', path: '/api/primary/claim', body: { incarnation: state.snapshot.incarnation, request_id: requestId() } }); });
    button('Pausieren', () => { void mutate({ kind: 'pause', path: '/api/pause', body: {} }); });
    button('Fortsetzen', () => { void mutate({ kind: 'resume', path: '/api/resume', body: { request_id: requestId() } }); });
    const fields = element(document, 'div', '', 'market-fixture-fields');
    const drinkLabel = element(document, 'label', 'Testgetränk'); drinkSelect = element(document, 'select'); drinkLabel.append(drinkSelect);
    const targetLabel = element(document, 'label', 'Zielpreis in Rappen'); targetInput = element(document, 'input'); targetInput.type = 'number'; targetInput.required = true; targetLabel.append(targetInput);
    fields.append(drinkLabel, targetLabel); listen(drinkSelect, 'change', updateTarget);
    const fixture = button('Testvorschlag senden', () => {
      const row = state.snapshot?.rows.find(row => row.id === drinkSelect?.value), target = Number(targetInput?.value);
      if (!row || !Number.isSafeInteger(target) || target < row.minimum_rappen || target > row.maximum_rappen || target % row.grid_rappen !== 0) {
        announce('Bitte einen Zielpreis im angezeigten Bereich und Raster eingeben.'); return;
      }
      void mutate({ kind: 'fixture', path: '/api/fixtures', body: { request_id: requestId(), scenario: {
        fixture_id: 'synthetic-price-v1', drink_id: row.id, target_rappen: target, expected_drink_version: row.drink_version,
      } } });
    });
    fixture.setAttribute('aria-describedby', 'market-fixture-help');
    retryButton = button('Ungewisse Aktion wiederholen', () => { if (uncertain) void mutate(uncertain); });
    feedback = element(document, 'p', 'Noch keine Bedienaktion.', 'market-feedback'); feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
    const help = element(document, 'p', 'Nur synthetische Testvorschläge. Eine abgelaufene Wartezeit aktiviert keinen Preis.'); help.id = 'market-fixture-help';
    details.append(fields, actions, help, feedback); root.append(details); render();
    disposeImage = startOperatorImage(root, operatorToken);
  }
  function clock() {
    if (stopped) return;
    render(); clockTimer = window.setTimeout(clock, 250);
  }
  listen(document, 'visibilitychange', () => { invalidate(); if (visible()) void poll(); });
  listen(window, 'offline', () => { invalidate(); });
  listen(window, 'online', () => { invalidate(); if (visible()) void poll(); });
  clockTimer = window.setTimeout(clock, 250); void poll();
  return () => {
    if (stopped) return;
    stopped = true; serial++; controller?.abort(); state = disconnect(state);
    window.clearTimeout(pollTimer); window.clearTimeout(clockTimer); window.clearTimeout(requestTimer);
    for (const dispose of disposers) dispose();
    disposeImage?.();
    render();
  };
}
