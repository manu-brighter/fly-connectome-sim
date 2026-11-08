import { isSessionRecording } from './session-replay.ts';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { decodePixels, type Counts } from './replay.ts';
import { EXPORT_SIZE } from './export.ts';
import { flyPose, selectionTapProgress } from './motion.ts';
import { createSwipeArm } from './swipe-arm.ts';
import { isVideoRecording, videoInputLabel, videoPlaneHeight, videoPolicyLabel, videoSpeedLabel } from './video-replay.ts';
import { type AnyRecording, type sampleAnyAtTick } from './recording.ts';
import { eventPresentation, isEventRecording, type EventOption, type sampleEventAtTick } from './event-replay.ts';
import { CELL_PANEL_MIN_WIDTH, buildActivityTraces, drawSciencePanel, prepareCellPanel, projectSomaPoints, scienceLayout, type ActivityTrace } from './science-panel.ts';
import type { Anatomy } from './anatomy.ts';
import type { CellActivity } from './cell-activity.ts';

type Sample = ReturnType<typeof sampleAnyAtTick>;
const INK = '#172B3A';

export function presentationCaption(sample: Sample | null, terminalHold: boolean, holdElapsedTicks: number, reducedMotion: boolean) {
  const swipe = sample && 'gesture' in sample && sample.gesture && !reducedMotion;
  const tap = sample && 'decision' in sample && selectionTapProgress(eventPresentation(sample).selectedSide, terminalHold ? holdElapsedTicks : 0, reducedMotion) !== null;
  return [swipe ? 'Illustrative swipe · presentation only' : tap ? 'Illustrative tap · presentation only' : terminalHold ? 'Recorded terminal sample · presentation hold' : 'Recorded simulation · illustrative fly motion',
    terminalHold ? 'No simulation time advances' : 'Pose is illustrative, not measured movement'];
}
function fittedFov(base: number, aspect: number) {
  return 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(base / 2)) * Math.max(1, 1.5 / aspect)) * 180 / Math.PI;
}

export function drawOverlay(context: CanvasRenderingContext2D, width: number, height: number, logicalWidth: number, recording: AnyRecording | null, sample: Sample | null, terminalHold = false, reducedMotion = false) {
  const inputLine = sample && recording ? `${'decision' in sample ? 'Paired event cards' : 'input' in sample ? `${videoSpeedLabel(recording)} · ${videoInputLabel(sample.input)}` : `Input ${sample.segment.stimulus}`}   •   ${(sample.tick / 10000).toFixed(3)} / ${(recording.duration_ticks / 10000).toFixed(3)} s` : '';
  const populationLine = sample ? `MBON11 ${sample.rates.mbon11.toFixed(2)}   KC ${sample.rates.kc.toFixed(2)}` : '';
  const motorLine = sample ? `L ${sample.rates.motor_left.toFixed(2)}   R ${sample.rates.motor_right.toFixed(2)} Hz/cell` : '';
  const flagsLine = sample && 'policy' in sample ? `${videoPolicyLabel(sample.policy)} · stim none · learning false · integrity-only` : 'External stimulation: none   Learning: false   Stored mode: integrity-only';
  const narrowFlagsLine = sample && 'policy' in sample ? `${videoPolicyLabel(sample.policy)} · integrity-only` : 'Stimulation: none · learning: false · stored: integrity-only';
  context.font = '500 14px Bahnschrift, Aptos, sans-serif';
  const populationX = Math.max(320, 22 + context.measureText(inputLine).width + 24);
  const motorX = populationX + context.measureText(populationLine).width + 24;
  const measuredRight = motorX + context.measureText(motorLine).width + 22;
  context.font = '11px Bahnschrift, Aptos, sans-serif';
  const narrow = logicalWidth < 650 || measuredRight > logicalWidth || populationX + context.measureText(flagsLine).width + 22 > logicalWidth;
  const scale = width / logicalWidth;
  context.save(); context.scale(scale, scale);
  const w = logicalWidth, h = height / scale;
  context.fillStyle = INK;
  context.font = `500 ${narrow ? 11 : 15}px Bahnschrift, Aptos, sans-serif`;
  const swiping = sample && 'gesture' in sample && sample.gesture && !reducedMotion;
  const caption = swiping ? 'Illustrative swipe · presentation only' : terminalHold ? narrow ? 'Recorded simulation · presentation hold' : 'Recorded simulation / illustrative fruit fly / presentation hold' : 'Recorded simulation / illustrative fruit fly';
  context.fillText(caption, 22, h - (narrow ? 126 : 116), w - 44);
  context.font = '12px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#597083';
  if (!narrow) context.fillText(terminalHold ? 'Presentation hold: terminal recorded sample; no simulation time advances.' : 'Geometry and pose are illustrative, not anatomical or measured movement.', 22, h - 94);
  const overlayHeight = narrow ? 108 : 76;
  context.fillStyle = 'rgba(243,247,250,.96)'; context.fillRect(0, h - overlayHeight, w, overlayHeight);
  context.strokeStyle = '#bdceda'; context.beginPath(); context.moveTo(0, h - overlayHeight); context.lineTo(w, h - overlayHeight); context.stroke();
  if (!sample || !recording) {
    context.font = `500 ${narrow ? 15 : 18}px Bahnschrift, Aptos, sans-serif`; context.fillStyle = INK; context.fillText('Your recording belongs here.', 22, h - (narrow ? 72 : 43));
    context.font = '11px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#597083';
    context.fillText(narrow ? 'Open measured-replay/v1,' : 'Open measured-replay/v1, measured-video-replay/v1 or /v2, event-choice-replay/v1 or feed-event-replay/v1.', 22, h - (narrow ? 57 : 25));
    if (narrow) {
      context.fillText('measured-video-replay/v1 or /v2,', 22, h - 42);
      context.fillText('event-choice-replay/v1 or feed-event-replay/v1.', 22, h - 27);
    }
    context.fillText('Activity is never generated by the viewer.', 22, h - (narrow ? 12 : 10));
  } else {
    context.font = `500 ${narrow ? 12 : 14}px Bahnschrift, Aptos, sans-serif`; context.fillStyle = INK;
    if (narrow && context.measureText(inputLine).width > w - 44) context.font = `500 ${Math.max(8, Math.floor(12 * (w - 44) / context.measureText(inputLine).width))}px Bahnschrift, Aptos, sans-serif`;
    context.fillText(inputLine, 22, h - (narrow ? 85 : 48));
    context.font = `500 ${narrow ? 12 : 14}px Bahnschrift, Aptos, sans-serif`;
    context.fillText(populationLine, narrow ? 22 : populationX, h - (narrow ? 64 : 48));
    context.fillText(motorLine, narrow ? 22 : motorX, h - (narrow ? 46 : 48));
    context.font = `${narrow ? 9 : 11}px Bahnschrift, Aptos, sans-serif`; context.fillStyle = '#597083';
    const sourceLine = 'input' in sample ? `Sim ${(sample.sourceTick / 10000).toFixed(4)} s · media PTS ${sample.input.source_pts} · event ${sample.segment.event_sequence}` : `Source ${(sample.sourceTick / 10000).toFixed(4)} s · event ${sample.segment.event_sequence} · ${sample.bin.duration_ticks / 10} ms bin`;
    context.fillText(sourceLine, 22, h - (narrow ? 27 : 23));
    context.fillText(narrow ? narrowFlagsLine : flagsLine, narrow ? 22 : populationX, h - (narrow ? 12 : 23));
  }
  if (sample && 'decision' in sample) drawEventPlan(context, logicalWidth, sample);
  context.restore();
}

// The same sampled result paints interactive and encoded frames. Imported text
// is drawn literally; the selected proposal never appears before effective_tick.
export function eventPlanLayout(context: CanvasRenderingContext2D, width: number, sample: ReturnType<typeof sampleEventAtTick>) {
  const view = eventPresentation(sample), maxWidth = Math.min(width - 44, 600);
  const source = [view.status, ...(sample.decision ? [view.title, ...view.lines, view.measurement] : [])];
  const lines: Array<{ text: string; font: string; color: string }> = [];
  for (const [index, text] of source.entries()) {
    const font = index === 1 ? '600 13px Bahnschrift, Aptos, sans-serif' : '400 12px Bahnschrift, Aptos, sans-serif';
    context.font = font;
    const push = (value: string) => lines.push({ text: value, font, color: index === 0 ? '#597083' : INK });
    let line = '';
    for (const word of text.split(' ')) {
      if (context.measureText(word).width > maxWidth) {
        if (line) { push(line); line = ''; }
        for (const character of word) {
          if (line && context.measureText(line + character).width > maxWidth) { push(line); line = character; }
          else line += character;
        }
      } else if (line && context.measureText(`${line} ${word}`).width > maxWidth) { push(line); line = word; }
      else line = line ? `${line} ${word}` : word;
    }
    if (line) push(line);
  }
  return { x: 12, y: 12, width: maxWidth + 20, height: 18 + lines.length * 15, lines };
}
export function drawEventPlan(context: CanvasRenderingContext2D, width: number, sample: ReturnType<typeof sampleEventAtTick>) {
  const layout = eventPlanLayout(context, width, sample);
  context.save(); context.fillStyle = 'rgba(243,247,250,.94)'; context.fillRect(layout.x, layout.y, layout.width, layout.height);
  for (const [index, line] of layout.lines.entries()) {
    context.font = line.font; context.fillStyle = line.color; context.fillText(line.text, 22, 31 + index * 15);
  }
  context.restore(); return layout;
}

type CardProposal = { brief: { guests: number }; options: EventOption[] };
export function eventSceneViewport(context: CanvasRenderingContext2D, width: number, sceneHeight: number,
                                   sample: ReturnType<typeof sampleEventAtTick>, proposal: CardProposal,
                                   populations: Pick<Counts, 'motor_left' | 'motor_right'>) {
  if (width >= CELL_PANEL_MIN_WIDTH) return { planWidth: 310, minimumSceneHeight: 336, scene: { x: 310, y: 0, width: width - 310, height: sceneHeight - 36 } };
  // Bounds-only placeholders reserve every possible option and defer before a
  // decision. They are never drawn, recorded or used for the adapter. Their
  // counts are fixed upper bounds, not future measured results.
  const decision = { counts: { motor_left: populations.motor_left * 5000, motor_right: populations.motor_right * 5000 },
    readout: { signed_difference_hz: -10000, action: 'inspect_right' } };
  const heights = [...proposal.options, null].map(option => eventPlanLayout(context, width, {
    ...sample, decision, plan: { brief: proposal.brief, selected_option: option },
  } as ReturnType<typeof sampleEventAtTick>).height);
  const reserved = Math.max(...heights) + 36;
  const minimumSceneHeight = reserved + 336;
  return { planWidth: width, minimumSceneHeight, scene: { x: 0, y: reserved, width, height: Math.max(sceneHeight, minimumSceneHeight) - reserved - 36 } };
}

// One bounded presentation surface per loaded video; never an extra neural input.
export function createVideoSwipeSurface(canvas: HTMLCanvasElement) {
  const context = canvas.getContext('2d')!;
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
  texture.magFilter = THREE.NearestFilter; texture.minFilter = THREE.NearestFilter; texture.generateMipmaps = false;
  return {
    texture,
    draw(outgoing: CanvasImageSource, incoming: CanvasImageSource, progress: number) {
      const width = canvas.width, height = canvas.height;
      context.save(); context.beginPath(); context.rect(0, 0, width, height); context.clip();
      context.imageSmoothingEnabled = false; context.clearRect(0, 0, width, height);
      context.drawImage(outgoing, 0, -height * progress, width, height);
      context.drawImage(incoming, 0, height * (1 - progress), width, height);
      context.restore(); texture.needsUpdate = true;
    },
    dispose() { texture.dispose(); canvas.width = 1; canvas.height = 1; },
  };
}

export function createEventBoard() {
  const group = new THREE.Group(); group.position.set(1.6, 1.9, .1); group.rotation.set(-.45, -.2, 0); group.visible = false;
  const frame = new THREE.Mesh(new THREE.BoxGeometry(4.04, 2.36, .13), new THREE.MeshStandardMaterial({ color: '#203747', roughness: .6 })); frame.castShadow = true; group.add(frame);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(3.84, 2.16), new THREE.MeshBasicMaterial({ color: '#ffffff' })); screen.position.z = .071; group.add(screen);
  function highlight(side: 'left' | 'right') {
    const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-.93, -1.07, 0), new THREE.Vector3(.93, -1.07, 0), new THREE.Vector3(.93, 1.07, 0), new THREE.Vector3(-.93, 1.07, 0)]);
    const outline = new THREE.LineLoop(geometry, new THREE.LineBasicMaterial({ color: '#70e4a1' }));
    outline.position.set(side === 'left' ? -.96 : .96, 0, .08); outline.visible = false; group.add(outline); return outline;
  }
  const highlights = { left: highlight('left'), right: highlight('right') };
  return {
    group, screen, highlights,
    setSample(sample: ReturnType<typeof sampleEventAtTick>, texture: THREE.Texture) {
      if (screen.material.map !== texture) { screen.material.map = texture; screen.material.needsUpdate = true; }
      const side = eventPresentation(sample).selectedSide;
      highlights.left.visible = side === 'left'; highlights.right.visible = side === 'right';
    },
  };
}

export function createFly() {
  const fly = new THREE.Group(); fly.position.set(-.65, 0.85, 0.1); fly.rotation.y = 1.1;
  const shell = new THREE.MeshStandardMaterial({ color: '#82694b', roughness: 0.83 });
  const dark = new THREE.MeshStandardMaterial({ color: '#342e29', roughness: 0.9 });
  const band = new THREE.MeshStandardMaterial({ color: '#51412f', roughness: 0.8 });
  const eyeMaterial = new THREE.MeshStandardMaterial({ color: '#a83328', roughness: 0.45, metalness: 0.04, flatShading: true });
  const eyeDark = new THREE.MeshStandardMaterial({ color: '#72291f', roughness: 0.48, flatShading: true });
  const sphere = (parent: THREE.Group, material: THREE.Material, position: number[], scale: number[], detail = 24) => {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, detail, detail), material);
    mesh.position.set(...position as [number, number, number]); mesh.scale.set(...scale as [number, number, number]); mesh.castShadow = true; parent.add(mesh); return mesh;
  };
  sphere(fly, shell, [0, 0, 0], [.4, .42, .55]);
  for (let i = 0; i < 6; i += 1) {
    const width = .37 * (1 - i * .115);
    sphere(fly, i % 2 ? band : shell, [0, -.045 - i * .025, -.48 - i * .19], [width, .29 - i * .025, .25]);
  }
  const head = new THREE.Group(); fly.add(head);
  sphere(head, dark, [0, .05, .65], [.36, .3, .3]);
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.IcosahedronGeometry(.29, 3), side < 0 ? eyeDark : eyeMaterial);
    eye.position.set(side * .27, .08, .76); eye.scale.set(.8, 1, .9); eye.castShadow = true; head.add(eye);
  }
  function line(parent: THREE.Group, points: THREE.Vector3[], color: string, opacity = 1) {
    const curve = new THREE.CatmullRomCurve3(points);
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(20));
    const material = new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity });
    parent.add(new THREE.Line(geometry, material));
  }
  // These six legs and wing veins are illustrative construction, never mapped neurons.
  const legs: THREE.Group[] = [], wings: Array<{ side: number; group: THREE.Group }> = [];
  const swipeArm = createSwipeArm(dark);
  const oppositeArm = createSwipeArm(dark, -1);
  for (const side of [-1, 1]) {
    for (let leg = 0; leg < 3; leg += 1) {
      if (side === 1 && leg === 0) { fly.add(swipeArm.group); legs.push(swipeArm.group); continue; }
      if (side === -1 && leg === 0) { fly.add(oppositeArm.group); legs.push(oppositeArm.group); continue; }
      const start = new THREE.Vector3(side * .25, -.1, .25 - leg * .35);
      const knee = new THREE.Vector3(side * (.8 + leg * .07), -.3, .72 - leg * .73);
      const ankle = new THREE.Vector3(side * (1.16 + leg * .035), -.77, .9 - leg * .95);
      const points = [start, knee, ankle, new THREE.Vector3(ankle.x + side * .18, -.81, ankle.z + .12)];
      const legMesh = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 16, .021, 5, false), dark);
      const legGroup = new THREE.Group(); legMesh.castShadow = true; legGroup.add(legMesh); fly.add(legGroup); legs.push(legGroup);
    }
    const wingGroup = new THREE.Group(); fly.add(wingGroup); wings.push({ side, group: wingGroup });
    const shape = new THREE.Shape();
    shape.moveTo(side * .13, -.08);
    shape.bezierCurveTo(side * .65, -.08, side * 1.95, -.65, side * 1.98, -1.42);
    shape.bezierCurveTo(side * 1.91, -1.91, side * .73, -1.39, side * .13, -.08);
    const wingMaterial = new THREE.MeshPhysicalMaterial({ color: '#d2e4ed', roughness: .2, metalness: .05, transparent: true, opacity: .53, side: THREE.DoubleSide, depthWrite: false });
    const wing = new THREE.Mesh(new THREE.ShapeGeometry(shape, 24), wingMaterial);
    wing.rotation.x = Math.PI / 2; wing.position.y = .3; wing.position.z = -.05; wingGroup.add(wing);
    const outline = shape.getPoints(45).map((p) => new THREE.Vector3(p.x, .31, p.y - .05));
    line(wingGroup, outline, '#6d8796', .55);
    for (let vein = 0; vein < 4; vein += 1) {
      line(wingGroup, [new THREE.Vector3(side * .16, .315, -.15), new THREE.Vector3(side * (.55 + vein * .15), .315, -.65), new THREE.Vector3(side * (1.65 - vein * .19), .315, -1.55 + vein * .1)], '#7d929b', .5);
    }
    line(fly, [new THREE.Vector3(side * .12, .1, .88), new THREE.Vector3(side * .19, .14, 1.12), new THREE.Vector3(side * .37, .23, 1.19)], '#342e29');
    for (let hair = 0; hair < 10; hair += 1) {
      const z = -.4 + hair * .095;
      line(fly, [new THREE.Vector3(side * .3, .25, z), new THREE.Vector3(side * (.39 + (hair % 3) * .025), .37, z - .03)], '#514535', .7);
    }
  }
  return { group: fly, head, legs, wings, swipeArm, oppositeArm, tapArms: { left: swipeArm, right: oppositeArm } };
}

export function placeEventScene(fly: THREE.Group, head: THREE.Group, board: THREE.Group, camera: THREE.PerspectiveCamera) {
  board.position.set(1.25, 1.4, 0); board.rotation.set(-.25, -.4, 0);
  fly.position.copy(board.localToWorld(new THREE.Vector3(0, 0, 1.6))); fly.position.y = .85;
  fly.rotation.set(0, Math.atan2(board.position.x - fly.position.x, board.position.z - fly.position.z), 0);
  fly.updateWorldMatrix(true, true); board.updateWorldMatrix(true, true);
  head.lookAt(board.localToWorld(new THREE.Vector3(0, 0, .071)));
  camera.fov = fittedFov(33, camera.aspect); camera.position.set(-10, 5, 8);
  camera.lookAt(1.25, 2.25, .6); camera.updateProjectionMatrix();
  fly.updateWorldMatrix(true, true);
}

export function createStage(canvas: HTMLCanvasElement) {
  const context = canvas.getContext('2d')!;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#DFEAF2');
  renderer.setClearColor(scene.background, 1);
  scene.fog = new THREE.Fog('#DFEAF2', 18, 30);
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 50);
  camera.position.set(6.1, 5.3, 10.8);
  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0.25, 0.9, 0);
  controls.enablePan = false; controls.enableDamping = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  controls.minDistance = 8; controls.maxDistance = 16;
  controls.minPolarAngle = Math.PI / 6; controls.maxPolarAngle = Math.PI / 2.2;
  controls.update();
  scene.add(new THREE.HemisphereLight('#ffffff', '#738b9b', 2.6));
  const key = new THREE.DirectionalLight('#fff7eb', 3.4);
  key.position.set(-3, 8, 6); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -7; key.shadow.camera.right = 7; key.shadow.camera.top = 7; key.shadow.camera.bottom = -7;
  key.shadow.normalBias = 0.025;
  scene.add(key);
  const fill = new THREE.DirectionalLight('#c6dbff', 1.4); fill.position.set(5, 3, -4); scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(100, 100), new THREE.MeshStandardMaterial({ color: '#DFEAF2', roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const { group: fly, head, legs, wings, swipeArm, oppositeArm, tapArms } = createFly(); scene.add(fly);
  const phone = new THREE.Group(); phone.position.set(1.5, 1.02, .7); phone.rotation.y = -.2; phone.rotation.x = -.75; scene.add(phone);
  const caseMaterial = new THREE.MeshStandardMaterial({ color: '#203747', roughness: .44, metalness: .25 });
  const phoneCase = new THREE.Mesh(new THREE.BoxGeometry(1.47, 2.65, .13), caseMaterial); phoneCase.castShadow = true; phone.add(phoneCase);
  const screenMaterial = new THREE.MeshBasicMaterial({ color: '#c9d9e5' });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.29, 2.25), screenMaterial); screen.position.set(0, -.015, .071); phone.add(screen);
  const pixelsScreen = new THREE.Mesh(new THREE.PlaneGeometry(1.19, 1.19), new THREE.MeshBasicMaterial({ color: '#c9d9e5' })); pixelsScreen.position.set(0, -.01, .075); phone.add(pixelsScreen);
  const cameraDot = new THREE.Mesh(new THREE.CircleGeometry(.033, 20), new THREE.MeshBasicMaterial({ color: '#09141c' })); cameraDot.position.set(0, 1.22, .073); phone.add(cameraDot);
  const home = new THREE.Mesh(new THREE.PlaneGeometry(.37, .027), new THREE.MeshBasicMaterial({ color: '#91a5b5' })); home.position.set(0, -1.2, .074); phone.add(home);
  const eventBoard = createEventBoard(); scene.add(eventBoard.group);

  let textures: Record<string, THREE.CanvasTexture> = {};
  let recording: AnyRecording | null = null;
  let sample: Sample | null = null;
  let swipeSurface: ReturnType<typeof createVideoSwipeSurface> | null = null;
  let exporting = false;
  let eventPhase: boolean | null = null;
  let anatomy: Anatomy | null = null, somaProjection: Array<[number, number]> = [], activityTraces: ActivityTrace[] = [];
  let cellPanel: ReturnType<typeof prepareCellPanel> | null = null;
  function setRecording(next: AnyRecording) {
    swipeSurface?.dispose(); swipeSurface = null;
    Object.values(textures).forEach((texture) => texture.dispose()); textures = {};
    recording = next;
    eventPhase = null;
    anatomy = null; somaProjection = []; activityTraces = buildActivityTraces(next);
    cellPanel = null; canvas.classList.remove('has-cell-activity');
    phone.visible = !isEventRecording(next); eventBoard.group.visible = isEventRecording(next);
    eventBoard.screen.material.map = null; eventBoard.screen.material.needsUpdate = true;
    eventBoard.highlights.left.visible = false; eventBoard.highlights.right.visible = false;
    pixelsScreen.geometry.dispose();
    pixelsScreen.geometry = new THREE.PlaneGeometry(1.19, (isVideoRecording(next) || isSessionRecording(next)) ? videoPlaneHeight(1.19, 90, 160) : 1.19);
    if (isVideoRecording(next) || isSessionRecording(next)) {
      const surface = document.createElement('canvas'); surface.width = 90; surface.height = 160;
      swipeSurface = createVideoSwipeSurface(surface);
    }
    for (const [name, input] of Object.entries(next.inputs)) {
      const pixels = decodePixels(input);
      const image = document.createElement('canvas'); image.width = input.width; image.height = input.height;
      const ctx = image.getContext('2d')!, rgba = ctx.createImageData(input.width, input.height);
      for (let i = 0; i < pixels.length / 3; i += 1) rgba.data.set([pixels[i * 3], pixels[i * 3 + 1], pixels[i * 3 + 2], 255], i * 4);
      ctx.putImageData(rgba, 0, 0);
      const texture = new THREE.CanvasTexture(image); texture.colorSpace = THREE.SRGBColorSpace;
      texture.magFilter = THREE.NearestFilter; texture.minFilter = THREE.NearestFilter; texture.generateMipmaps = false;
      textures[name] = texture;
    }
    sample = null;
    const material = pixelsScreen.material as THREE.MeshBasicMaterial; material.map = null; material.needsUpdate = true;
  }
  function render(terminalHold = false, holdElapsedTicks = 0) {
    const logicalWidth = exporting ? EXPORT_SIZE : Math.min(900, canvas.clientWidth);
    const cardSample = cellPanel && sample && 'decision' in sample ? sample : null;
    const proposal = cardSample && recording ? recording.source.metadata.proposal as CardProposal : null;
    if (!exporting) {
      const base = cellPanel ? (logicalWidth < CELL_PANEL_MIN_WIDTH ? 1600 : 900) : 0;
      const required = cardSample && proposal && recording && logicalWidth < CELL_PANEL_MIN_WIDTH
        ? scienceLayout(logicalWidth, 0, true).panelHeight + eventSceneViewport(context, logicalWidth, 0, cardSample, proposal, recording.groups).minimumSceneHeight : 0;
      const minimum = Math.max(base, required);
      canvas.style.minHeight = minimum ? `${minimum}px` : '';
    }
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(devicePixelRatio, 1.75);
    const width = exporting ? EXPORT_SIZE : Math.max(1, Math.round(rect.width * ratio));
    const height = exporting ? EXPORT_SIZE : Math.max(1, Math.round(rect.height * ratio));
    const scale = width / logicalWidth, logicalHeight = height / scale;
    const layout = scienceLayout(logicalWidth, logicalHeight, cellPanel !== null);
    const viewport = cardSample && proposal && recording ? eventSceneViewport(context, logicalWidth, layout.sceneHeight, cardSample, proposal, recording.groups)
      : { planWidth: logicalWidth, scene: { x: 0, y: 0, width: logicalWidth, height: layout.sceneHeight - 36 } };
    const sceneWidth = Math.max(1, Math.round(viewport.scene.width * scale)), sceneHeight = Math.max(1, Math.round(viewport.scene.height * scale));
    const sceneX = Math.round(viewport.scene.x * scale), sceneY = Math.round(viewport.scene.y * scale);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width; canvas.height = height; renderer.setSize(width, height, false);
    }
    camera.aspect = sceneWidth / sceneHeight; camera.updateProjectionMatrix();
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const inputName = sample && ('frame_id' in sample.segment ? sample.segment.frame_id : sample.segment.stimulus);
    if (inputName) {
      let texture = textures[inputName]!;
      if (swipeSurface && sample && 'gesture' in sample && sample.gesture && !reducedMotion) {
        if (sample.gesture.screenProgress === 0) texture = textures[sample.gesture.outgoingFrameId];
        else if (sample.gesture.screenProgress < 1) {
          swipeSurface.draw(textures[sample.gesture.outgoingFrameId].image, textures[sample.gesture.incomingFrameId].image, sample.gesture.screenProgress);
          texture = swipeSurface.texture;
        }
      }
      if (sample && 'decision' in sample) eventBoard.setSample(sample, texture);
      else {
        const material = pixelsScreen.material as THREE.MeshBasicMaterial;
        if (material.map !== texture) { material.map = texture; material.color.set('#ffffff'); material.needsUpdate = true; }
      }
    }
    if (sample) {
      const paired = 'decision' in sample;
      if (eventPhase !== paired) {
        if (paired) {
          placeEventScene(fly, head, eventBoard.group, camera);
          controls.target.set(1.25, 2.25, .6);
        } else {
          fly.position.set(-.65, .85, .1); fly.rotation.set(0, 1.1, 0); head.rotation.set(0, 0, 0);
          camera.fov = 35; camera.position.set(6.1, 5.3, 10.8); camera.lookAt(.25, .9, 0);
          camera.updateProjectionMatrix(); controls.target.set(.25, .9, 0);
        }
        eventPhase = paired;
      }
      phone.visible = !paired; eventBoard.group.visible = paired;
      if (!eventBoard.group.visible) { eventBoard.highlights.left.visible = false; eventBoard.highlights.right.visible = false; }
      const pose = flyPose(sample.tick, reducedMotion);
      fly.position.y = paired ? .85 : .85 + pose.bob; fly.rotation.x = paired ? 0 : pose.bodyPitch;
      if (paired) head.lookAt(eventBoard.group.localToWorld(new THREE.Vector3(0, 0, .071)));
      else head.rotation.set(0, pose.headYaw, 0);
      wings.forEach(({ side, group }) => { group.rotation.z = paired ? 0 : side * pose.wingAngle; });
      legs.forEach((group, index) => { if (group !== swipeArm.group && group !== oppositeArm.group) group.rotation.z = paired ? 0 : (index % 2 ? -1 : 1) * pose.legAngle; });
      if ('decision' in sample) {
        const side = eventPresentation(sample).selectedSide;
        swipeArm.updateTap(fly, eventBoard.group, null, null); oppositeArm.updateTap(fly, eventBoard.group, null, null);
        if (side) tapArms[side].updateTap(fly, eventBoard.group, side, selectionTapProgress(side, terminalHold ? holdElapsedTicks : 0, reducedMotion));
      } else {
        swipeArm.update(fly, phone, !reducedMotion && 'gesture' in sample && sample.gesture ? sample.gesture.progress : null, -pose.legAngle);
        oppositeArm.update(fly, phone, null, pose.legAngle);
      }
    }
    if (!exporting) controls.update();
    camera.fov = fittedFov(eventPhase ? 33 : 35, camera.aspect); camera.updateProjectionMatrix();
    renderer.setScissorTest(false); renderer.setViewport(0, 0, width, height); renderer.clear();
    // Shared measurements keep the scene, captions and science panel disjoint.
    renderer.setViewport(sceneX, height - sceneY - sceneHeight, sceneWidth, sceneHeight);
    renderer.setScissor(sceneX, height - sceneY - sceneHeight, sceneWidth, sceneHeight); renderer.setScissorTest(true);
    renderer.render(scene, camera);
    renderer.setScissorTest(false);
    context.drawImage(renderer.domElement, 0, 0, width, height);
    if (recording && sample) {
      context.save(); context.scale(scale, scale);
      context.font = '12px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#172B3A';
      presentationCaption(sample, terminalHold, holdElapsedTicks, reducedMotion).forEach((caption, index) => context.fillText(caption, 16, layout.sceneHeight - 22 + index * 14, logicalWidth - 32));
      if ('decision' in sample) drawEventPlan(context, viewport.planWidth, sample);
      drawSciencePanel(context, logicalWidth, logicalHeight, recording, sample, activityTraces, anatomy, somaProjection, cellPanel);
      context.restore();
    } else drawOverlay(context, width, height, logicalWidth, recording, sample, terminalHold, reducedMotion);
  }
  function dispose() {
    swipeSurface?.dispose(); swipeSurface = null;
    renderer.setAnimationLoop(null); controls.dispose();
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
        child.geometry.dispose();
        const materials = Array.isArray(child.material) ? child.material : [child.material]; materials.forEach((material) => material.dispose());
      }
    });
    Object.values(textures).forEach((texture) => texture.dispose()); renderer.dispose();
  }
  return { renderer, render, setRecording,
    setAnatomy: (next: Anatomy | null) => { if (exporting) return; const nextPanel = cellPanel ? prepareCellPanel(cellPanel.detail, next) : null; anatomy = next; somaProjection = projectSomaPoints(next); cellPanel = nextPanel; },
    setCellActivity: (next: CellActivity | null) => { if (exporting) return; cellPanel = next ? prepareCellPanel(next, anatomy) : null; canvas.classList.toggle('has-cell-activity', next !== null); },
    setSample: (next: Sample) => { sample = next; }, setExporting: (value: boolean) => { exporting = value; controls.enabled = !value; }, dispose };
}
