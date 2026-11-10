import { createMarketTraderScene } from './market-trader-scene.ts';
import { adoptTraderPrices, createTraderPrices, adoptTraderActivity, createTraderActivity } from '../../market/web/trader-state.ts';
import type { VerifiedNativeFrame, PricePoint } from '../../market/web/trader-state.ts';
import type { BoardState } from '../../market/web/state.ts';
import { createNativeState, nativeFreshness } from '../../market/web/native-state.ts';
import type { NativeState } from '../../market/web/native-state.ts';
import { groups } from '../../market/web/native-protocol.ts';

const money = (value: number) => `CHF ${(value / 100).toFixed(2)}`;
const labels = ['PAM11', 'PPL101', 'KC', 'MBON07', 'MBON11', 'Motor links', 'Motor rechts'];
export function createMarketTrader(root: HTMLElement, createScene = createMarketTraderScene) {
  const document = root.ownerDocument;
  function element<K extends keyof HTMLElementTagNameMap>(tag: K, text = '', className = '') {
    const value = document.createElement(tag); value.textContent = text; value.className = className; return value;
  }
  function svg() { const value = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); value.setAttribute('viewBox', '0 0 460 124'); value.setAttribute('aria-hidden', 'true'); return value; }
  function path(target: SVGSVGElement, data: string, className: string) {
    const value = document.createElementNS('http://www.w3.org/2000/svg', 'path'); value.setAttribute('d', data); value.setAttribute('class', className); target.append(value);
  }
  root.className = 'fly-exchange';
  const header = element('header', '', 'exchange-header'), brand = element('div');
  brand.append(element('h1', 'Fly Exchange'), element('p', 'Eine Fruchtfliege am Trading Desk. Echte Modellaktivität, illustrative Bewegungen.'));
  const connection = element('p', 'Verbindung wird geprüft', 'exchange-connection'); connection.setAttribute('role', 'status');
  header.append(brand, connection);
  const layout = element('div', '', 'exchange-layout'), hero = element('section', '', 'exchange-hero');
  hero.setAttribute('aria-label', 'Illustrative Fruchtfliege am Trading Desk');
  const sceneHost = element('div', '', 'exchange-scene'), phoneNote = element('p', 'Wartet auf einen bestätigten Bildeingang.', 'exchange-phone-note');
  const stats = element('div', '', 'exchange-stats');
  const clockValue = element('strong', '—'), intervalValue = element('strong', '—'), inputValue = element('strong', '—');
  for (const [label, value] of [['Modellzeit', clockValue], ['Beobachtungen', intervalValue], ['Bildeingang', inputValue]] as const) {
    const cell = element('div'); cell.append(value, element('span', label)); stats.append(cell);
  }
  hero.append(sceneHost, phoneNote, stats);
  const side = element('aside', '', 'exchange-market');
  const chart = element('section', '', 'exchange-chart'); chart.setAttribute('aria-label', 'Beobachteter Preisverlauf');
  const chartHead = element('div', '', 'exchange-chart-heading'), chartTitle = element('h2', 'Bestätigte Kurse');
  const select = element('select'); select.setAttribute('aria-label', 'Getränk für Preisverlauf'); chartHead.append(chartTitle, select);
  const chartNumber = element('div', '', 'exchange-chart-number'), price = element('strong', '—'), change = element('span', 'Historie beginnt mit dem aktuellen Stand'); chartNumber.append(price, change);
  const priceSvg = svg(), chartNote = element('p', 'Noch kein bestätigter Preisstand.', 'exchange-chart-note');
  const chartBounds = element('div', '', 'exchange-chart-bounds'), minimum = element('span'), maximum = element('span');
  chartBounds.append(minimum, maximum);
  chart.append(chartHead, chartNumber, priceSvg, chartBounds, chartNote);
  const board = element('div', '', 'exchange-board'); side.append(chart, board); layout.append(hero, side);
  const activity = element('section', '', 'exchange-activity'); activity.setAttribute('aria-label', 'Sieben gemessene Populationsraten');
  const activityHeader = element('div', '', 'exchange-activity-heading');
  activityHeader.append(element('h2', 'Im Modell'), element('p', 'Empfangene 500-ms-Fenster. Fehlende Intervalle bleiben als Lücke sichtbar.'));
  const traces = element('div', '', 'exchange-traces');
  const plots = groups.map((group, index) => {
    const cell = element('div', '', 'exchange-trace'), value = element('strong', '—'), picture = svg();
    cell.append(element('span', labels[index]), value, picture); traces.append(cell); return { group, value, picture };
  });
  activity.append(activityHeader, traces);
  const integrity = element('p', 'Lokale experimentelle Preise aus einem konfigurierten Motor-Readout. Keine Verkaufspreise oder biologische Validierung.', 'exchange-integrity');
  root.replaceChildren(header, layout, activity, integrity);
  let scene: ReturnType<typeof createMarketTraderScene> | null = null;
  try { scene = createScene(sceneHost); }
  catch { sceneHost.classList.add('exchange-scene-fallback'); sceneHost.textContent = 'Die 3D-Szene ist auf diesem Gerät nicht verfügbar. Bestätigte Kurse und Messdaten bleiben sichtbar.'; }
  let prices = createTraderPrices(), measurement = createTraderActivity(), native: NativeState = createNativeState();
  let cached: VerifiedNativeFrame | null = null, selected: string | null = null, lastTrade: string | null = null;
  let stopped = false, now = 0, oldPoints = measurement.points, oldHistory: PricePoint[] | undefined;
  const selectChange = () => { selected = select.value; oldHistory = undefined; render(); };
  select.addEventListener('change', selectChange);

  function drawPrice() {
    const row = prices.rows.find(item => item.id === selected) ?? prices.rows[0];
    if (!row) return;
    selected = row.id; select.value = row.id;
    const points = prices.histories[row.id] ?? [], first = points[0], latest = points.at(-1);
    price.textContent = money(row.current_rappen);
    minimum.textContent = `Min ${money(row.minimum_rappen)}`;
    maximum.textContent = `Max ${money(row.maximum_rappen)}`;
    const difference = first ? row.current_rappen - first.price : 0;
    change.textContent = difference ? `${difference > 0 ? '+' : '−'}CHF ${(Math.abs(difference) / 100).toFixed(2)} seit Anzeige` : 'Aktueller Ausgangsstand';
    change.className = difference > 0 ? 'exchange-up' : difference < 0 ? 'exchange-down' : '';
    if (oldHistory === points) return;
    oldHistory = points; priceSvg.replaceChildren();
    for (const y of [14, 62, 110]) path(priceSvg, `M 10 ${y} H 450`, 'exchange-grid');
    let line = '';
    points.forEach((point, index) => {
      const x = points.length === 1 ? 230 : 12 + index / (points.length - 1) * 436;
      const y = 110 - (point.price - row.minimum_rappen) / Math.max(1, row.maximum_rappen - row.minimum_rappen) * 96;
      line += index === 0 || point.gap ? ` M ${x} ${y}` : ` H ${x} V ${y}`;
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); dot.setAttribute('cx', String(x)); dot.setAttribute('cy', String(y)); dot.setAttribute('r', index === points.length - 1 ? '4' : '2'); priceSvg.append(dot);
    });
    if (line) path(priceSvg, line, 'exchange-price-path');
    chartNote.textContent = points.some(point => point.gap) || prices.gap ? 'Unterbrechung: Zwischenstände wurden nicht beobachtet.' :
      points.length === 1 ? 'Historie ab diesem Seitenaufruf. Noch keine bestätigte Änderung.' : `${points.length - 1} bestätigte Änderungen seit ${first.utc.slice(11, 19)}. Letzter Stand ${latest?.utc.slice(11, 19)}.`;
  }
  function drawActivity() {
    const latest = measurement.points.at(-1);
    for (const plot of plots) plot.value.textContent = latest ? `${latest.rates[plot.group].toFixed(1)} Hz` : '—';
    if (oldPoints === measurement.points) return;
    oldPoints = measurement.points;
    for (const plot of plots) {
      plot.picture.replaceChildren();
      const max = Math.max(1, ...measurement.points.map(point => point.rates[plot.group]));
      let line = '';
      measurement.points.forEach((point, index) => {
        const x = measurement.points.length === 1 ? 12 : 12 + index / (measurement.points.length - 1) * 436;
        const y = 108 - point.rates[plot.group] / max * 88;
        line += index === 0 || point.gap ? ` M ${x} ${y}` : ` L ${x} ${y}`;
      });
      path(plot.picture, line, 'exchange-activity-path');
    }
  }
  function render() {
    if (stopped) return;
    const fresh = nativeFreshness(native, now), live = prices.live && prices.connected && fresh.live && fresh.ageMs !== null && fresh.ageMs < 5000;
    connection.textContent = live ? 'Modell verbunden' : 'Letzter Stand · live unbestätigt'; connection.dataset.live = String(live);
    scene?.setConnection(live);
    scene?.setActivity(live ? native.snapshot?.group_rates_hz ?? null : null);
    clockValue.textContent = native.snapshot ? `${(native.snapshot.model_ms / 1000).toFixed(1)} s` : '—';
    intervalValue.textContent = native.snapshot ? String(native.snapshot.observations_completed) : '—';
    inputValue.textContent = live ? native.snapshot?.input_kind === 'image' ? 'Freigegebenes Bild' : 'Schwarzbild' : 'Unbekannt';
    const snapshot = native.snapshot;
    const matches = live && cached && snapshot && cached.incarnation === snapshot.incarnation && cached.worker_session === snapshot.worker_session &&
      cached.observations_completed === snapshot.observations_completed && cached.image_id === snapshot.image_id && cached.frame_sha256 === snapshot.frame_sha256 && snapshot.input_kind === 'image';
    if (matches && cached) {
      scene?.setInput({ id: `${cached.incarnation}/${cached.worker_session}/${cached.image_id}/${cached.frame_sha256}`, pixels: cached.pixels, width: 64, height: 64 });
      phoneNote.textContent = 'Das Smartphone zeigt exakt den bestätigten 64 × 64 Modelleingang.';
    } else {
      scene?.setInput(null);
      phoneNote.textContent = !live ? 'Verbindung oder Messung unklar. Kein Bild wird als aktueller Eingang gezeigt.' : snapshot?.input_kind === 'black' ?
        'Das Modell erhält gerade ein Schwarzbild.' : 'Freigegebener Bildeingang gemessen. Zugehörige Pixel noch nicht verfügbar.';
    }
    activity.dataset.stale = String(!live);
    drawPrice(); drawActivity();
    if (live && prices.trade && prices.trade.id !== lastTrade) {
      lastTrade = prices.trade.id; selected = prices.trade.drinkId; select.value = selected; oldHistory = undefined;
      scene?.setTrade({ ...prices.trade, from: prices.trade.from / 100, to: prices.trade.to / 100, minimum: prices.trade.minimum / 100, maximum: prices.trade.maximum / 100 });
      drawPrice();
    }
  }
  const presentation = {
    onBoard(value: BoardState, nowMs: number) {
      now = nowMs; const previous = prices; prices = adoptTraderPrices(prices, value, now);
      if (prices.incarnation !== previous.incarnation || prices.config !== previous.config) {
        selected = null; lastTrade = null; cached = null; oldHistory = undefined;
        select.replaceChildren(...prices.rows.map(row => { const option = element('option', row.name); option.value = row.id; return option; }));
      }
      if (!prices.connected || !prices.trade) { scene?.setTrade(null); lastTrade = null; }
      render();
    },
    onState(value: NativeState, nowMs: number) { now = nowMs; native = value; measurement = adoptTraderActivity(measurement, value, now); render(); },
    onFrame(value: VerifiedNativeFrame | null) { cached = value; render(); },
  };
  return { board, presentation, dispose() { stopped = true; cached = null; select.removeEventListener('change', selectChange); scene?.dispose(); scene = null; } };
}
