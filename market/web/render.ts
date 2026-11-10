import { isFresh } from './state.ts';
import type { BoardState } from './state.ts';

type RowView = {
  node: HTMLLIElement; name: HTMLElement; amount: HTMLElement; change: HTMLElement; info: HTMLElement;
  version: number; price: number;
  activation: { version: number; direction: 'increase' | 'decrease'; deadlineMs: number } | null;
};
type View = { banner: HTMLElement; lists: HTMLOListElement[]; date: HTMLElement; incarnation: string | null; rows: Map<string, RowView> };
const views = new WeakMap<HTMLElement, View>();
export function element<K extends keyof HTMLElementTagNameMap>(document: Document, tag: K, text = '', className = ''): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node;
}
export function renderBoard(root: HTMLElement, state: BoardState, nowMs: number): void {
  const document = root.ownerDocument;
  let view = views.get(root);
  if (!view) {
    root.className = 'market-board';
    const header = element(document, 'header', '', 'market-heading');
    header.append(element(document, 'h1', 'Lokaler Testbetrieb'), element(document, 'p', 'Testvorschläge, keine Verkaufspreise.'));
    const banner = element(document, 'div', '', 'market-status'); banner.setAttribute('role', 'status'); banner.setAttribute('aria-live', 'polite');
    const board = element(document, 'section', '', 'market-prices'); board.setAttribute('aria-label', 'Letzte bestätigte Getränkepreise');
    const lists = [element(document, 'ol'), element(document, 'ol')]; lists[1].start = 11; board.append(...lists);
    const date = element(document, 'p', '', 'market-date');
    root.replaceChildren(header, banner, board, date,
      element(document, 'p', 'Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten', 'market-integrity'));
    view = { banner, lists, date, incarnation: null, rows: new Map() }; views.set(root, view);
  }
  const snapshot = state.snapshot, fresh = isFresh(state, nowMs);
  const status = !fresh ? 'Letzter bekannter Stand — aktuell unbekannt' : snapshot?.fault ? '■ Sicherheitsstopp' :
    snapshot?.paused ? 'Ⅱ Pausiert' : snapshot?.primary_state === 'present' ? '● Verbunden · Testbetrieb aktiv' : 'Verbunden · Primäre Tafel nicht bestätigt';
  const presence = { unclaimed: 'nicht übernommen', awaiting_ack: 'Bestätigung ausstehend', present: 'anwesend', absent: 'abwesend' };
  const detail = snapshot ? `${fresh ? '' : `Letzte Meldung: ${snapshot.paused ? 'Pausiert' : 'Testbetrieb freigegeben'} · `}Primäre Tafel: ${presence[snapshot.primary_state]}${snapshot.fault ? ` · Sicherheitsstopp (${snapshot.fault})` : ''}` : 'Noch kein bestätigter Stand.';
  const bannerText = `${status}. ${detail}`;
  if (view.banner.textContent !== bannerText) view.banner.textContent = bannerText;
  view.banner.setAttribute('data-unknown', String(!fresh));
  view.date.textContent = snapshot ? `Stand: ${snapshot.server_utc} · Preisversion ${snapshot.price_version} · Revision ${snapshot.revision}` : 'Preise erscheinen nach dem ersten vollständigen bestätigten Stand.';
  const groups: HTMLElement[][] = [[], []], split = Math.ceil((snapshot?.rows.length ?? 0) / 2);
  view.lists[1].start = split + 1;
  if (snapshot && view.incarnation !== snapshot.incarnation) {
    view.incarnation = snapshot.incarnation; view.rows.clear();
  }
  for (const [index, row] of (snapshot?.rows ?? []).entries()) {
    let rendered = view.rows.get(row.id);
    if (!rendered) {
      const node = element(document, 'li', '', 'market-row'), line = element(document, 'div', '', 'market-price-line');
      const name = element(document, 'span', '', 'market-name'), amount = element(document, 'strong', '', 'market-amount');
      line.append(name, amount);
      const information = element(document, 'div', '', 'market-row-info');
      const change = element(document, 'span'), info = element(document, 'span');
      information.append(change, info); node.append(line, information);
      rendered = { node, name, amount, change, info, version: row.drink_version, price: row.current_rappen, activation: null };
      view.rows.set(row.id, rendered);
    } else if (row.drink_version > rendered.version && row.current_rappen !== rendered.price) {
      // Keep the observed activation through ACK/finish/countdown renders. Only a
      // newer drink version creates a new window; poll revisions cannot replay it.
      rendered.activation = {
        version: row.drink_version, direction: row.current_rappen > rendered.price ? 'increase' : 'decrease', deadlineMs: nowMs + 1200,
      };
    }
    rendered.version = row.drink_version; rendered.price = row.current_rappen;
    rendered.name.textContent = row.name; rendered.amount.textContent = `CHF ${(row.current_rappen / 100).toFixed(2)}`;
    const activation = rendered.activation;
    const active = activation !== null && activation.version === row.drink_version && nowMs < activation.deadlineMs;
    const className = active ? 'market-row market-activated' : 'market-row';
    if (rendered.node.className !== className) rendered.node.className = className;
    rendered.change.hidden = !active;
    rendered.change.textContent = active ? activation.direction === 'increase' ? '↑ Erhöht' : '↓ Gesenkt' : '';
    rendered.change.className = active ? `market-${activation.direction}` : '';
    if (!active) rendered.activation = null;
    const elapsed = state.receivedAtMs === null ? 0 : Math.max(0, nowMs - state.receivedAtMs);
    const remaining = Math.max(0, row.remaining_lock_ms - elapsed);
    const eligibility = row.remaining_lock_ms > 0 ?
      `${row.recovery_lock ? 'Sicherheitswartezeit nach Neustart · ' : ''}${remaining > 0 ? `noch ca. ${Math.ceil(remaining / 60000)} Min. Wartezeit (geschätzt)` : 'Wartezeit geschätzt abgelaufen; Server entscheidet'}` : 'Keine gemeldete Wartezeit; Server entscheidet';
    rendered.info.textContent = `Version ${row.drink_version} · ${eligibility}`;
    groups[index < split ? 0 : 1].push(rendered.node);
  }
  view.lists.forEach((list, index) => {
    const rows = groups[index];
    // Replacing unchanged nodes would restart/truncate their CSS animation.
    if (list.children.length !== rows.length || rows.some((row, position) => list.children[position] !== row)) list.replaceChildren(...rows);
  });
}
