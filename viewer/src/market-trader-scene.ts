import * as THREE from 'three';
import { createFly } from './stage.ts';

export type MarketInput = { id: string; pixels: Uint8Array; width: number; height: number };
export type MarketTrade = { id: string; name: string; from: number; to: number; minimum: number; maximum: number };
type PriceRange = Pick<MarketTrade, 'from' | 'to' | 'minimum' | 'maximum'>;
const COLORS = { navy: '#111f32', slate: '#223751', edge: '#3a526c', amber: '#d59a47', mint: '#83e0ba', coral: '#f18a7d', cyan: '#90cddc', ink: '#dce7ef' };
const smooth = (value: number) => { const p = THREE.MathUtils.clamp(value, 0, 1); return p * p * (3 - 2 * p); };

export function validMarketInput(input: MarketInput) {
  return typeof input.id === 'string' && input.id.length > 0 && input.id.length <= 512 && input.pixels instanceof Uint8Array
    && Number.isSafeInteger(input.width) && Number.isSafeInteger(input.height) && input.width > 0 && input.height > 0
    && input.width <= 2048 && input.height <= 2048 && input.width * input.height <= 1048576
    && input.pixels.length === input.width * input.height * 3;
}
export function validMarketTrade(trade: MarketTrade) {
  return typeof trade.id === 'string' && trade.id.length > 0 && typeof trade.name === 'string' && trade.name.length > 0
    && [trade.from, trade.to, trade.minimum, trade.maximum].every(Number.isFinite) && trade.minimum < trade.maximum
    && trade.from >= trade.minimum && trade.from <= trade.maximum && trade.to >= trade.minimum && trade.to <= trade.maximum;
}

// These poses acknowledge an event. Their interpolated positions are illustration,
// never additional observations or intermediate authoritative prices.
export function marketTradePose(trade: PriceRange, progress: number, reducedMotion: boolean) {
  const p = reducedMotion ? 1 : smooth((progress - .24) / .5);
  const value = THREE.MathUtils.lerp(trade.from, trade.to, p);
  return { value, handleY: .72 + (value - trade.minimum) / (trade.maximum - trade.minimum), reach: reducedMotion ? 0 : smooth(Math.min(progress / .24, (1 - progress) / .24)) };
}

function box(parent: THREE.Group, size: [number, number, number], position: [number, number, number], color: string, metalness = .1) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), new THREE.MeshStandardMaterial({ color, metalness, roughness: .52 }));
  mesh.position.set(...position); mesh.castShadow = true; mesh.receiveShadow = true; parent.add(mesh); return mesh;
}

function phoneBezel(parent: THREE.Group, width: number, height: number, depth: number, radius: number, color: string, z: number) {
  const shape = new THREE.Shape(), x = -width / 2, y = -height / 2;
  shape.moveTo(x + radius, y); shape.lineTo(x + width - radius, y); shape.quadraticCurveTo(x + width, y, x + width, y + radius);
  shape.lineTo(x + width, y + height - radius); shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  shape.lineTo(x + radius, y + height); shape.quadraticCurveTo(x, y + height, x, y + height - radius);
  shape.lineTo(x, y + radius); shape.quadraticCurveTo(x, y, x + radius, y);
  const geometry = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 8, steps: 1 });
  geometry.translate(0, 0, z - depth / 2);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .35, metalness: .6 })); mesh.castShadow = true; parent.add(mesh); return mesh;
}

export function createMarketTraderRig() {
  const group = new THREE.Group(), fly = createFly();
  fly.group.position.set(-1.05, .98, .15); fly.group.rotation.set(0, .92, 0); group.add(fly.group);
  // Keep the proven six-legged construction, with warmer chitin for this set.
  const colors = new Map([['82694b', COLORS.amber], ['51412f', '#805827'], ['342e29', '#302a27'], ['a83328', '#ba3541'], ['72291f', '#8e2638']]);
  const recolored = new Set<THREE.Material>();
  fly.group.traverse(object => {
    if (!(object instanceof THREE.Mesh) || !(object.material instanceof THREE.MeshStandardMaterial) || recolored.has(object.material)) return;
    recolored.add(object.material); const replacement = colors.get(object.material.color.getHexString()); if (replacement) object.material.color.set(replacement);
  });
  // The desk reads as a physical miniature: a chamfer-like tier, brass edge,
  // dark inset worktop, and four modest feet rather than a luminous stage.
  box(group, [8.4, .2, 5.6], [0, -.25, -.2], '#17283e');
  box(group, [8.15, .07, 5.35], [0, -.115, -.2], '#50627a');
  box(group, [8, .12, 5.2], [0, -.02, -.2], COLORS.slate);
  for (const x of [-3.4, 3.4]) for (const z of [-2.2, 1.8]) box(group, [.24, .25, .24], [x, -.43, z], '#101b2b');
  // A work mat visually locates the fly without trapping it in a card.
  box(group, [3.9, .035, 3.4], [-1.35, .055, -.1], '#1a2c42');
  const phone = new THREE.Group(); phone.position.set(1.35, 1.3, 1.18); phone.rotation.set(-.2, -.5, -.04); group.add(phone);
  phoneBezel(phone, 1.36, 2.52, .15, .14, '#070e1b', 0);
  phoneBezel(phone, 1.41, 2.57, .075, .17, '#718396', -.045);
  const screenMaterial = new THREE.MeshBasicMaterial({ color: '#172434', toneMapped: false });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.19, 2.16), screenMaterial); screen.position.z = .081; phone.add(screen);
  const island = phoneBezel(phone, .36, .075, .016, .037, '#020710', .09); island.position.y = 1.17;
  box(phone, [.31, .022, .016], [0, -1.18, .09], '#a1adb9');
  box(phone, [.025, .22, .045], [-.72, .48, -.025], '#8194a4', .7);
  const stand = new THREE.Group(); group.add(stand);
  box(stand, [1.5, .07, 1.1], [1.34, .1, 1.18], '#597085', .6);
  box(stand, [.2, .68, .18], [1.34, .42, .9], '#526779', .6);
  const board = new THREE.Group(); board.position.set(.95, 2.27, -2.24); board.rotation.y = -.08; group.add(board);
  box(board, [4.45, 2.72, .16], [0, 0, 0], '#071323', .65);
  box(board, [4.55, 2.82, .06], [0, 0, -.07], COLORS.edge, .65);
  const boardMaterial = new THREE.MeshBasicMaterial({ color: '#ffffff', toneMapped: false });
  const boardScreen = new THREE.Mesh(new THREE.PlaneGeometry(4.22, 2.49), boardMaterial); boardScreen.position.z = .09; board.add(boardScreen);
  for (const x of [-.9, .9]) box(group, [.16, 1, .2], [x + .95, .55, -2.24], '#455a70', .7);
  box(group, [2.7, .09, .7], [.95, .12, -2.18], '#0e1c2e');
  const lever = new THREE.Group(); lever.position.set(1.25, 0, -.58); group.add(lever);
  box(lever, [1.03, .16, .67], [0, .18, 0], '#101b2a', .5);
  box(lever, [.55, 1.68, .16], [0, 1.1, 0], '#344d66', .6);
  box(lever, [.035, 1.25, .03], [0, 1.2, .1], '#8ca3b5', .7);
  for (let index = 0; index < 6; index++) box(lever, [.16, .014, .02], [.17, .72 + index / 5, .1], '#8394a5');
  const handle = new THREE.Group(); handle.position.set(0, 1.22, .24); lever.add(handle);
  box(handle, [.62, .15, .29], [0, 0, 0], COLORS.amber, .4);
  box(handle, [.4, .035, .02], [0, .045, .155], '#f3d5a0');
  // A miniature steel mug and a restrained brass desk inset complete the set.
  const mug = new THREE.Mesh(new THREE.CylinderGeometry(.18, .15, .3, 24), new THREE.MeshStandardMaterial({ color: '#8192a4', metalness: .72, roughness: .35 }));
  mug.position.set(-3.05, .24, 1.52); mug.castShadow = true; group.add(mug);
  const coffee = new THREE.Mesh(new THREE.CircleGeometry(.15, 24), new THREE.MeshBasicMaterial({ color: '#24180f' })); coffee.rotation.x = -Math.PI / 2; coffee.position.set(-3.05, .393, 1.52); group.add(coffee);
  box(group, [.9, .018, .06], [-2.95, .07, 2.14], COLORS.amber, .6);
  const rest = fly.swipeArm.joints.map(joint => joint.position.clone()), target = new THREE.Vector3(), direction = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  function pose(time: number, tradeProgress: number | null, swipeProgress: number | null, reducedMotion: boolean, trade?: PriceRange) {
    const tradePose = trade && tradeProgress !== null ? marketTradePose(trade, tradeProgress, reducedMotion) : null;
    const reach = tradePose?.reach ?? 0;
    fly.group.rotation.y = .92 + .78 * reach;
    fly.group.position.y = .98 + (reducedMotion ? 0 : Math.sin(time * 1.6) * .012);
    fly.group.rotation.x = reducedMotion ? 0 : Math.sin(time * 1.2) * .008;
    fly.wings.forEach(({ side, group: wing }) => { wing.rotation.z = reducedMotion ? 0 : side * (.035 + Math.sin(time * 3.5) * .018); });
    fly.head.rotation.set(0, 0, 0);
    group.updateWorldMatrix(true, true);
    const gaze = tradeProgress !== null && tradeProgress < .9 && !reducedMotion ? lever.localToWorld(new THREE.Vector3(0, 1.4, .4)) : phone.localToWorld(new THREE.Vector3(0, .2, .08));
    fly.head.lookAt(gaze);
    fly.oppositeArm.update(fly.group, phone, null, 0);
    fly.swipeArm.update(fly.group, phone, reducedMotion ? null : swipeProgress, 0);
    if (tradePose) {
      handle.position.y = tradePose.handleY;
      group.updateWorldMatrix(true, true);
      if (reach > 0) {
        target.copy(handle.getWorldPosition(new THREE.Vector3())); fly.group.worldToLocal(target);
        const points = rest.map(point => point.clone());
        points[3].lerp(target, reach);
        points[1].lerp(new THREE.Vector3(.95, -.22, .38).lerp(target, .28), reach);
        points[2].lerp(new THREE.Vector3().lerpVectors(rest[0], target, .75).add(new THREE.Vector3(.18, -.22, .1)), reach);
        fly.swipeArm.joints.forEach((joint, index) => joint.position.copy(points[index]));
        fly.swipeArm.segments.forEach((segment, index) => {
          direction.subVectors(points[index + 1], points[index]); segment.position.copy(points[index]).addScaledVector(direction, .5);
          segment.scale.set(1, direction.length(), 1); segment.quaternion.setFromUnitVectors(up, direction.normalize());
        });
      }
    }
  }
  pose(0, null, null, true);
  return { group, fly, phone, screen, board, boardScreen, handle, pose };
}

export function disposeMarketObjects(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>(), textures = new Set<THREE.Texture>();
  root.traverse(object => {
    if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return;
    geometries.add(object.geometry);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material);
      for (const value of Object.values(material)) if (value instanceof THREE.Texture) textures.add(value);
    }
  });
  textures.forEach(texture => texture.dispose()); geometries.forEach(geometry => geometry.dispose()); materials.forEach(material => material.dispose());
}

export function fitMarketCamera(camera: THREE.OrthographicCamera, rig: THREE.Group, aspect: number) {
  camera.position.set(8.4, 6.6, 10.8); camera.lookAt(0, 1.2, -.15); camera.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(rig), corners: THREE.Vector3[] = [];
  for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y]) for (const z of [bounds.min.z, bounds.max.z]) corners.push(new THREE.Vector3(x, y, z).applyMatrix4(camera.matrixWorldInverse));
  const halfWidth = Math.max(...corners.map(point => Math.abs(point.x))) * 1.08;
  const halfHeight = Math.max(...corners.map(point => Math.abs(point.y))) * 1.08;
  const h = Math.max(halfHeight, halfWidth / Math.max(.2, aspect));
  camera.left = -h * aspect; camera.right = h * aspect; camera.top = h; camera.bottom = -h; camera.updateProjectionMatrix();
}

function paintBoard(canvas: HTMLCanvasElement, trade: MarketTrade | null, rates: Record<string, number> | null, connected: boolean) {
  const context = canvas.getContext('2d'); if (!context) return;
  const w = canvas.width, h = canvas.height;
  context.fillStyle = '#101f32'; context.fillRect(0, 0, w, h);
  context.font = '500 25px Bahnschrift, Aptos, sans-serif'; context.fillStyle = COLORS.ink; context.fillText('Handelsplatz', 30, 43);
  context.fillStyle = connected ? COLORS.mint : COLORS.coral; context.beginPath(); context.arc(w - 34, 34, 5, 0, Math.PI * 2); context.fill();
  context.font = '15px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#92a7bb'; context.fillText(connected ? 'Bestätigte Preisänderungen' : 'Verbindung unterbrochen · letzter Stand', 30, 73);
  if (trade) {
    const accent = trade.to >= trade.from ? COLORS.mint : COLORS.coral;
    context.font = '500 25px Bahnschrift, Aptos, sans-serif'; context.fillStyle = COLORS.ink; context.fillText(trade.name.slice(0, 42), 30, 119, w - 60);
    context.font = '500 38px Bahnschrift, Aptos, sans-serif'; context.fillStyle = accent; context.fillText(`CHF ${trade.to.toFixed(2)}`, 30, 167);
    context.font = '16px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#a2b5c6'; context.fillText(`zuvor CHF ${trade.from.toFixed(2)}`, 30, 194);
    const chart = { x: 300, y: 118, width: w - 342, height: 138 };
    context.strokeStyle = '#2e4359'; context.lineWidth = 1;
    for (let line = 0; line <= 4; line++) { const y = chart.y + line * chart.height / 4; context.beginPath(); context.moveTo(chart.x, y); context.lineTo(chart.x + chart.width, y); context.stroke(); }
    const y = (price: number) => chart.y + chart.height * (1 - (price - trade.minimum) / (trade.maximum - trade.minimum));
    context.strokeStyle = accent; context.lineWidth = 5; context.beginPath(); context.moveTo(chart.x + 10, y(trade.from)); context.lineTo(chart.x + chart.width - 10, y(trade.to)); context.stroke();
    for (const [x, price] of [[chart.x + 10, trade.from], [chart.x + chart.width - 10, trade.to]]) { context.fillStyle = accent; context.beginPath(); context.arc(x, y(price), 6, 0, Math.PI * 2); context.fill(); }
    context.font = '13px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#8ea5bb'; context.fillText('vorher', chart.x, chart.y + chart.height + 23); context.fillText('bestätigt', chart.x + chart.width - 68, chart.y + chart.height + 23);
  } else {
    context.font = '500 29px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#c0cfdd'; context.fillText('Die Fliege ist am Desk.', 30, 150);
    context.font = '18px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#8ea5bb'; context.fillText('Warten auf eine bestätigte Preisänderung.', 30, 184);
  }
  context.fillStyle = '#243c53'; context.fillRect(30, h - 75, w - 60, 1);
  context.font = '14px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#8ea5bb';
  const entries = rates ? Object.entries(rates).filter(([, value]) => Number.isFinite(value) && value >= 0).slice(0, 4) : [];
  context.fillText(entries.length ? entries.map(([name, value]) => `${name.replaceAll('_', ' ')} ${value.toFixed(2)}`).join('   '): 'Noch keine gemessene Aktivität', 30, h - 44, w - 60);
  context.font = '12px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#768da3'; context.fillText('Pose und Bewegung sind illustrativ.', 30, h - 19);
}

export function createMarketTraderScene(host: HTMLElement) {
  const root = document.createElement('div'); root.className = 'market-trader-scene';
  root.style.cssText = 'position:relative;width:100%;height:100%;min-height:320px;overflow:hidden;background:#111f32;';
  const canvas = document.createElement('canvas'); canvas.style.cssText = 'display:block;width:100%;height:100%;position:absolute;inset:0;';
  canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', 'Illustrative Fruchtfliege am Trading-Desk mit Foto und bestätigtem Preis.'); root.append(canvas); host.append(root);
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  let disposed = false, contextLost = false, frame = 0, renderer: THREE.WebGLRenderer | null = null;
  let inputId: string | null = null, lastInputId: string | null = null, lastTradeId: string | null = null;
  let trade: MarketTrade | null = null, rates: Record<string, number> | null = null, connected = false;
  let photo: HTMLCanvasElement | null = null, photoTexture: THREE.CanvasTexture | null = null, swipeStarted = -Infinity, tradeStarted = -Infinity;
  const boardCanvas = document.createElement('canvas'); boardCanvas.width = 768; boardCanvas.height = 432;
  const scene = new THREE.Scene(); scene.background = new THREE.Color(COLORS.navy);
  const camera = new THREE.OrthographicCamera(-7, 7, 5, -5, .1, 70), rig = createMarketTraderRig(); scene.add(rig.group);
  const idleCanvas = document.createElement('canvas'); idleCanvas.width = 256; idleCanvas.height = 456;
  const idleContext = idleCanvas.getContext('2d');
  if (idleContext) {
    idleContext.fillStyle = '#142337'; idleContext.fillRect(0, 0, 256, 456); idleContext.textAlign = 'center';
    idleContext.fillStyle = '#a9becf'; idleContext.font = '500 25px Bahnschrift, Aptos, sans-serif';
    idleContext.fillText('Wartet auf', 128, 212); idleContext.fillText('Bild', 128, 244);
    idleContext.fillStyle = '#70899f'; idleContext.font = '13px Bahnschrift, Aptos, sans-serif'; idleContext.fillText('Kein aktueller Eingang', 128, 286);
  }
  const idleTexture = new THREE.CanvasTexture(idleCanvas); idleTexture.colorSpace = THREE.SRGBColorSpace;
  rig.screen.material.map = idleTexture; rig.screen.material.color.set('#ffffff'); rig.screen.material.needsUpdate = true;
  const boardTexture = new THREE.CanvasTexture(boardCanvas); boardTexture.colorSpace = THREE.SRGBColorSpace;
  rig.boardScreen.material.map = boardTexture; rig.boardScreen.material.needsUpdate = true;
  scene.add(new THREE.HemisphereLight('#c6e5f0', '#2a2933', 2.8));
  const key = new THREE.DirectionalLight('#ffe5b9', 4.3); key.position.set(-3, 7, 6); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 20 }); key.shadow.bias = -.001; scene.add(key);
  const fill = new THREE.DirectionalLight('#86cde4', 2); fill.position.set(5, 4, -3); scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: COLORS.navy, roughness: 1 })); floor.rotation.x = -Math.PI / 2; floor.position.y = -.58; floor.receiveShadow = true; scene.add(floor);
  let fallbackCanvas: HTMLCanvasElement | null = null;
  function refreshBoard() { paintBoard(boardCanvas, trade, rates, connected); boardTexture.needsUpdate = true; }
  function fallback() {
    if (!fallbackCanvas) {
      fallbackCanvas = document.createElement('canvas'); fallbackCanvas.style.cssText = canvas.style.cssText; fallbackCanvas.setAttribute('role', 'img');
      fallbackCanvas.setAttribute('aria-label', 'Statische Ersatzansicht: Foto und bestätigte Preisänderung. 3D ist nicht verfügbar.'); root.append(fallbackCanvas); canvas.style.visibility = 'hidden';
    }
    const context = fallbackCanvas.getContext('2d'); if (!context) return;
    const width = Math.max(320, root.clientWidth), height = Math.max(320, root.clientHeight); fallbackCanvas.width = width * 1.5; fallbackCanvas.height = height * 1.5;
    context.scale(1.5, 1.5); context.fillStyle = COLORS.navy; context.fillRect(0, 0, width, height);
    const boardW = Math.min(width * .72, 600), boardH = boardW * 432 / 768;
    context.drawImage(boardCanvas, (width - boardW) / 2, 18, boardW, boardH);
    const phoneW = Math.min(width * .17, 105), phoneH = phoneW * 1.8, phoneX = width * .56, phoneY = Math.max(boardH + 35, height * .52);
    context.fillStyle = COLORS.slate; context.fillRect(width * .15, phoneY + phoneH * .9, width * .7, 15);
    // The fallback is an explicitly static illustration, with the same real input.
    context.save(); context.translate(width * .35, phoneY + phoneH * .5);
    context.fillStyle = '#c8dce5'; context.globalAlpha = .48;
    for (const side of [-1, 1]) { context.beginPath(); context.ellipse(-20, side * 19 - 15, 37, 13, side * .5, 0, Math.PI * 2); context.fill(); }
    context.globalAlpha = 1; context.fillStyle = COLORS.amber; context.beginPath(); context.ellipse(-16, 10, 37, 20, .25, 0, Math.PI * 2); context.fill();
    context.strokeStyle = '#785329'; context.lineWidth = 3;
    for (let i = 0; i < 4; i++) { context.beginPath(); context.moveTo(-41 + i * 13, -3); context.lineTo(-38 + i * 13, 26); context.stroke(); }
    context.fillStyle = '#b83246'; context.beginPath(); context.ellipse(22, 4, 16, 18, 0, 0, Math.PI * 2); context.fill();
    context.strokeStyle = '#b29b73'; context.lineWidth = 2;
    for (let i = 0; i < 3; i++) for (const side of [-1, 1]) { context.beginPath(); context.moveTo(i * 12 - 25, 15); context.lineTo(i * 16 - 38, 35 + side * 5); context.lineTo(i * 21 - 42, 48); context.stroke(); }
    context.restore(); context.fillStyle = '#6d859d'; context.fillRect(phoneX - 5, phoneY - 5, phoneW + 10, phoneH + 10); context.fillStyle = '#0b1422'; context.fillRect(phoneX, phoneY, phoneW, phoneH);
    const image = photo ?? idleCanvas;
    const scale = Math.min((phoneW - 8) / image.width, (phoneH - 18) / image.height), imageW = image.width * scale, imageH = image.height * scale;
    context.drawImage(image, phoneX + (phoneW - imageW) / 2, phoneY + (phoneH - imageH) / 2, imageW, imageH);
    context.font = '13px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#9fb3c7'; context.fillText('Statische Ansicht · 3D nicht verfügbar', 18, height - 17);
  }
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75)); renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.1; renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  } catch { fallback(); }
  function resize() {
    if (disposed) return;
    const width = Math.max(1, root.clientWidth), height = Math.max(320, root.clientHeight);
    renderer?.setSize(width, height, false); fitMarketCamera(camera, rig.group, width / height);
    if (!renderer || contextLost) fallback();
  }
  const observer = new ResizeObserver(resize); observer.observe(root);
  function loseContext(event: Event) { event.preventDefault(); contextLost = true; fallback(); }
  function restoreContext() { if (disposed) return; contextLost = false; fallbackCanvas?.remove(); fallbackCanvas = null; canvas.style.visibility = ''; resize(); }
  canvas.addEventListener('webglcontextlost', loseContext); canvas.addEventListener('webglcontextrestored', restoreContext);
  function draw(now: number) {
    if (disposed) return;
    const tradeProgress = trade ? THREE.MathUtils.clamp((now - tradeStarted) / 2600, 0, 1) : null;
    const swipeProgress = inputId && now - swipeStarted < 1250 ? THREE.MathUtils.clamp((now - swipeStarted) / 1250, 0, 1) : null;
    rig.pose(now / 1000, tradeProgress, swipeProgress, media.matches || !connected, trade ?? undefined);
    if (renderer && !contextLost && !document.hidden) renderer.render(scene, camera);
    frame = requestAnimationFrame(draw);
  }
  refreshBoard(); resize(); frame = requestAnimationFrame(draw);
  function clearPhoto() {
    rig.screen.material.map = idleTexture; rig.screen.material.color.set('#ffffff'); rig.screen.material.needsUpdate = true; rig.screen.scale.set(1, 1, 1);
    photoTexture?.dispose(); photoTexture = null; if (photo) { photo.width = 1; photo.height = 1; } photo = null; inputId = null; swipeStarted = -Infinity;
  }
  return {
    setInput(input: MarketInput | null) {
      if (disposed) return;
      if (!connected) { clearPhoto(); if (!renderer || contextLost) fallback(); return; }
      if (!input || !validMarketInput(input)) { clearPhoto(); if (!renderer || contextLost) fallback(); return; }
      if (input.id === inputId) return;
      clearPhoto(); photo = document.createElement('canvas'); photo.width = input.width; photo.height = input.height;
      const context = photo.getContext('2d'); if (!context) { clearPhoto(); return; }
      const rgba = context.createImageData(input.width, input.height);
      for (let index = 0; index < input.width * input.height; index++) { rgba.data[index * 4] = input.pixels[index * 3]; rgba.data[index * 4 + 1] = input.pixels[index * 3 + 1]; rgba.data[index * 4 + 2] = input.pixels[index * 3 + 2]; rgba.data[index * 4 + 3] = 255; }
      context.putImageData(rgba, 0, 0); photoTexture = new THREE.CanvasTexture(photo); photoTexture.colorSpace = THREE.SRGBColorSpace;
      photoTexture.generateMipmaps = false; photoTexture.minFilter = THREE.LinearFilter; photoTexture.magFilter = THREE.LinearFilter;
      // Contain the supplied image in the portrait display without cropping.
      const ratio = input.width / input.height, screenRatio = 1.19 / 2.16;
      rig.screen.scale.set(ratio > screenRatio ? 1 : ratio / screenRatio, ratio > screenRatio ? screenRatio / ratio : 1, 1);
      rig.screen.material.map = photoTexture; rig.screen.material.color.set('#ffffff'); rig.screen.material.needsUpdate = true;
      inputId = input.id; swipeStarted = input.id === lastInputId ? -Infinity : performance.now(); lastInputId = input.id;
      if (!renderer || contextLost) fallback();
    },
    setActivity(next: Record<string, number> | null) {
      if (disposed) return; rates = next ? Object.fromEntries(Object.entries(next).filter(([, value]) => Number.isFinite(value) && value >= 0).slice(0, 32)) : null;
      refreshBoard(); if (!renderer || contextLost) fallback();
    },
    setTrade(next: MarketTrade | null) {
      if (disposed) return;
      if (!next || !validMarketTrade(next)) { trade = null; tradeStarted = -Infinity; refreshBoard(); if (!renderer || contextLost) fallback(); return; }
      if (next.id === trade?.id) return;
      trade = { ...next, name: next.name.slice(0, 200) }; tradeStarted = connected && next.id !== lastTradeId ? performance.now() : -Infinity; lastTradeId = next.id;
      refreshBoard(); if (!renderer || contextLost) fallback();
    },
    setConnection(next: boolean) {
      if (disposed) return; connected = next;
      if (!next) { clearPhoto(); tradeStarted = -Infinity; }
      refreshBoard(); if (!renderer || contextLost) fallback();
    },
    dispose() {
      if (disposed) return; disposed = true; cancelAnimationFrame(frame); observer.disconnect();
      canvas.removeEventListener('webglcontextlost', loseContext); canvas.removeEventListener('webglcontextrestored', restoreContext);
      clearPhoto(); disposeMarketObjects(scene); renderer?.dispose(); renderer = null; boardCanvas.width = 1; boardCanvas.height = 1; idleCanvas.width = 1; idleCanvas.height = 1;
      if (fallbackCanvas) { fallbackCanvas.width = 1; fallbackCanvas.height = 1; } root.remove();
    },
  };
}
