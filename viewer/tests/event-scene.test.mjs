import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import { runInNewContext } from 'node:vm';
import * as THREE from 'three';
import * as stageModule from '../src/stage.ts';
import * as armModule from '../src/swipe-arm.ts';
import { selectionTapProgress } from '../src/motion.ts';

test('stage initializes the full-canvas clear color before its first scene render', () => {
  let createdScene;
  class Scene extends THREE.Scene { constructor() { super(); createdScene = this; } }
  class Renderer {
    shadowMap = {};
    color = new THREE.Color('#000000');
    alpha = 0;
    renders = 0;
    setPixelRatio() {}
    setClearColor(color, alpha) { this.color.set(color); this.alpha = alpha; }
    render() { this.renders++; }
  }
  class Controls { target = new THREE.Vector3(); update() {} }
  const source = stripTypeScriptTypes(readFileSync(new URL('../src/stage.ts', import.meta.url), 'utf8')).replace(/^import .+;\r?$/gm, '').replace(/^export /gm, '');
  const createStage = runInNewContext(source + '\ncreateStage;', { THREE: { ...THREE, Scene, WebGLRenderer: Renderer }, OrbitControls: Controls,
    ...armModule, matchMedia: () => ({ matches: false }) });
  const stage = createStage({ getContext: () => ({}) });
  assert.equal(stage.renderer.renders, 0);
  assert.equal(stage.renderer.color.getHexString(), createdScene.background.getHexString(), 'First full-canvas clear must already match the scene background');
  assert.equal(stage.renderer.alpha, 1);
});

// Exact visible option content used for the authorized live-proposal acceptance.
// This fixture contains no request, transport response or provider receipt.
const liveProposal = { brief: { guests: 100 }, options: [
  { id: 'rooftop-sunset-01', title: 'Sunset Rooftop Social', setting: 'rooftop', music: 'Deep house', budget_chf: 4200, capacity: 120, duration_minutes: 240,
    programme: [{ start_minute: 0, label: 'Welcome drinks' }, { start_minute: 45, label: 'Sunset dinner' }, { start_minute: 120, label: 'Live DJ set' }, { start_minute: 210, label: 'Late networking' }] },
  { id: 'warehouse-garden-02', title: 'Indoor Summer Bash', setting: 'warehouse', music: 'Indie dance', budget_chf: 3800, capacity: 140, duration_minutes: 300,
    programme: [{ start_minute: 0, label: 'Arrival and check-in' }, { start_minute: 30, label: 'Team games' }, { start_minute: 110, label: 'Buffet dinner' }, { start_minute: 180, label: 'Dance floor opens' }, { start_minute: 270, label: 'Final toast' }] },
] };
function planSample(option, phase = 'selected') {
  return { tick: phase === 'pending' ? 89999 : 90000, sourceTick: phase === 'pending' ? 89999 : 90000, decisionTick: 90000,
    decision: phase === 'pending' ? null : { counts: { motor_left: 6, motor_right: 2 }, readout: { signed_difference_hz: -8, action: option?.id === liveProposal.options[0].id ? 'inspect_left' : option ? 'inspect_right' : 'defer' } },
    plan: phase === 'pending' ? null : { brief: liveProposal.brief, selected_option: option }, leftOptionId: liveProposal.options[0].id,
    feedContext: 'Feed ended at 7.000 s · END · playlist exhausted (clip window end)' };
}

test('both live plans remain disjoint from actual tablet meshes in reserved900px and narrow viewports', () => {
  for (const width of [900, 341, 700]) {
    let stableViewport;
    for (const [option, phase] of [[liveProposal.options[0], 'selected'], [liveProposal.options[1], 'selected'], [null, 'pending'], [null, 'defer']]) {
      const boxes = [], texts = [], sample = planSample(option, phase), before = JSON.stringify(sample);
      const context = { font: '', save() {}, restore() {}, fillRect(x, y, width, height) { boxes.push({ x, y, width, height }); },
        measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
        fillText(text, x, y) { texts.push({ text, x, y, font: this.font, width: this.measureText(text).width }); } };
      const sceneHeight = width === 900 ? 480 : 640;
      const layout = stageModule.eventSceneViewport?.(context, width, sceneHeight, sample, liveProposal, { motor_left: 1, motor_right: 1 })
        ?? { scene: { x: 0, y: 0, width, height: sceneHeight - 36 }, planWidth: width, minimumSceneHeight: sceneHeight };
      stageModule.drawEventPlan(context, layout.planWidth, sample);
      const rig = stageModule.createFly(), board = stageModule.createEventBoard(), viewport = layout.scene;
      const camera = new THREE.PerspectiveCamera(35, viewport.width / viewport.height, .1, 50);
      stageModule.placeEventScene(rig.group, rig.head, board.group, camera);
      camera.updateMatrixWorld(true); board.group.updateMatrixWorld(true); rig.group.updateMatrixWorld(true);
      const points = [];
      for (const object of [board.group, rig.group]) object.traverse(mesh => {
        if (!mesh.geometry) return;
        const positions = mesh.geometry.attributes.position;
        for (let index = 0; index < positions.count; index++) {
          const p = new THREE.Vector3().fromBufferAttribute(positions, index).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(p.x) < 1 && Math.abs(p.y) < 1, 'Actual meshes must stay within the scene subviewport');
          if (object === board.group) points.push([viewport.x + (p.x + 1) * viewport.width / 2, viewport.y + (1 - p.y) * viewport.height / 2]);
        }
      });
      const boardBox = { left: Math.min(...points.map(p => p[0])), right: Math.max(...points.map(p => p[0])), top: Math.min(...points.map(p => p[1])), bottom: Math.max(...points.map(p => p[1])) };
      assert.ok(boxes.every(box => box.x + box.width < boardBox.left || box.x > boardBox.right || box.y + box.height < boardBox.top || box.y > boardBox.bottom), `${width}px ${phase}: plan and actual tablet must not overlap`);
      assert.ok(viewport.width > 0 && viewport.height >= 300);
      assert.ok(texts.every(line => Number(line.font.match(/(\d+)px/)[1]) >= 12 && line.x + line.width <= layout.planWidth - 12));
      if (option && phase !== 'pending') for (const entry of option.programme) assert.ok(texts.map(line => line.text).join(' ').includes(entry.label), entry.label);
      if (phase === 'pending') assert.ok(texts.every(line => !liveProposal.options.some(option => line.text.includes(option.title))));
      for (const side of ['left', 'right']) for (const progress of [0, .25, .5, .75, 1]) {
        const arm = rig.tapArms[side]; arm.updateTap(rig.group, board.group, side, progress);
        const tip = arm.joints[3].getWorldPosition(new THREE.Vector3()).project(camera);
        assert.ok(Math.abs(tip.x) < 1 && Math.abs(tip.y) < 1, 'Complete fixed-length tap tip stays in scene subviewport');
      }
      if (width === 900) assert.deepEqual(viewport, { x: 310, y: 0, width: 590, height: 444 });
      if (stableViewport) assert.deepEqual(viewport, stableViewport, 'Selection/pending/defer must reserve the same camera region');
      stableViewport = viewport;
      assert.equal(JSON.stringify(sample), before);
    }
  }
});

test('tap runs once after selection and remains absent for defer and reduced motion', () => {
  assert.equal(selectionTapProgress(null, 8000, false), null);
  assert.equal(selectionTapProgress('left', 8000, true), null);
  for (const elapsed of [0, 1999, 2000, 18000, 29999]) assert.equal(selectionTapProgress('right', elapsed, false), null);
  assert.equal(selectionTapProgress('left', 10000, false), .5);
  assert.equal(selectionTapProgress('left', 6000, false), .25);
  assert.equal(selectionTapProgress('left', 6000, false), selectionTapProgress('left', 6000, false));
});

test('active stage caption labels the swipe as presentation-only and hold as frozen neural time', () => {
  assert.equal(typeof stageModule.presentationCaption, 'function');
  assert.match(stageModule.presentationCaption({ gesture: { progress: .5 } }, false, 0, false).join(' '), /Illustrative swipe.*presentation only/);
  assert.doesNotMatch(stageModule.presentationCaption({ gesture: { progress: .5 } }, false, 0, true).join(' '), /swipe/);
  assert.match(stageModule.presentationCaption({}, true, 8000, false).join(' '), /No simulation time advances/);
});

test('event composition clears the actual fly meshes and points its head at the board', () => {
  assert.equal(typeof stageModule.createFly, 'function', 'Actual fly geometry must be independently placeable');
  assert.equal(typeof stageModule.placeEventScene, 'function', 'Cards need their own scene composition');
  const rig = stageModule.createFly(), board = stageModule.createEventBoard();
  const camera = new THREE.PerspectiveCamera(35, 900 / 585, .1, 50);
  stageModule.placeEventScene(rig.group, rig.head, board.group, camera);
  rig.group.updateMatrixWorld(true); board.group.updateMatrixWorld(true); camera.updateMatrixWorld(true);
  const boardBounds = new THREE.Box3().setFromObject(board.group);
  const flyBounds = new THREE.Box3().setFromObject(rig.group);
  const inverseBoard = new THREE.Matrix4().copy(board.group.matrixWorld).invert();
  rig.group.traverse(mesh => {
    if (!mesh.geometry) return;
    const positions = mesh.geometry.attributes.position;
    for (let index = 0; index < positions.count; index++) {
      const p = new THREE.Vector3().fromBufferAttribute(positions, index).applyMatrix4(mesh.matrixWorld).applyMatrix4(inverseBoard);
      assert.ok(Math.abs(p.x) > 2.04 || Math.abs(p.y) > 1.20 || Math.abs(p.z) > .085, 'Actual fly surface must clear tablet case');
    }
  });
  assert.ok(flyBounds.min.y >= -.015 && flyBounds.min.y <= .08, 'Resting legs must meet the floor');
  const headPosition = rig.head.localToWorld(new THREE.Vector3(0, .05, .65));
  const gaze = new THREE.Vector3(0, 0, 1).transformDirection(rig.head.matrixWorld);
  const towardBoard = new THREE.Vector3().subVectors(board.group.position, headPosition).normalize();
  assert.ok(gaze.dot(towardBoard) > .98, 'Head must face the actual board, not oscillate into space');
  for (const object of [rig.group, board.group]) object.traverse(mesh => {
    if (!mesh.geometry) return;
    const positions = mesh.geometry.attributes.position;
    for (let index = 0; index < positions.count; index++) {
      const projected = new THREE.Vector3().fromBufferAttribute(positions, index).applyMatrix4(mesh.matrixWorld).project(camera);
      assert.ok(Math.abs(projected.x) < .98 && projected.y > -.95 && projected.y < .95, 'Actual scene vertices must fit the top presentation viewport');
    }
  });
});

test('selected-side tap reaches both actual card planes, retracts and is seek deterministic', () => {
  assert.equal(typeof stageModule.createFly, 'function');
  assert.equal(typeof stageModule.placeEventScene, 'function');
  const rig = stageModule.createFly(), board = stageModule.createEventBoard();
  stageModule.placeEventScene(rig.group, rig.head, board.group, new THREE.PerspectiveCamera());
  for (const side of ['left', 'right']) {
    const arm = rig.tapArms[side];
    assert.equal(typeof arm.updateTap, 'function', 'The selected card needs a contact gesture');
    const tip = () => board.group.worldToLocal(arm.joints[3].getWorldPosition(new THREE.Vector3()));
    arm.updateTap(rig.group, board.group, null, 0);
    const rest = tip();
    arm.updateTap(rig.group, board.group, side, .5);
    const contact = tip();
    assert.ok(Math.abs(contact.x - (side === 'left' ? -.96 : .75)) < .001);
    assert.ok(Math.abs(contact.y - (side === 'left' ? -.65 : -.25)) < .001 && contact.z > .095 && contact.z < .15);
    const shoulder = arm.joints[0].getWorldPosition(new THREE.Vector3());
    const wrist = arm.joints[2].getWorldPosition(new THREE.Vector3());
    assert.ok(shoulder.distanceTo(wrist) > .1);
    arm.updateTap(rig.group, board.group, side, .2); const reach = tip();
    assert.ok(reach.distanceTo(rest) > .1 && reach.distanceTo(contact) > .1);
    arm.updateTap(rig.group, board.group, side, 1); assert.ok(tip().distanceTo(rest) < 1e-6);
    arm.updateTap(rig.group, board.group, side, .2); assert.ok(tip().distanceTo(reach) < 1e-6);
    arm.updateTap(rig.group, board.group, null, .5); assert.ok(tip().distanceTo(rest) < 1e-6);
  }
});

test('entire selected foreleg path clears tablet case with actual tube and joint radii', () => {
  const rig = stageModule.createFly(), board = stageModule.createEventBoard();
  stageModule.placeEventScene(rig.group, rig.head, board.group, new THREE.PerspectiveCamera());
  for (const side of ['left', 'right']) for (let step = 0; step <= 100; step++) {
    const arm = rig.tapArms[side];
    arm.updateTap(rig.group, board.group, null, 0);
    const restLengths = arm.segments.map(segment => segment.scale.y);
    arm.updateTap(rig.group, board.group, side, step / 100);
    const joints = arm.joints.map(joint => board.group.worldToLocal(joint.getWorldPosition(new THREE.Vector3())));
    arm.segments.forEach((segment, index) => assert.ok(Math.abs(segment.scale.y - restLengths[index]) < 1e-6, 'Tap must preserve every original segment length'));
    const check = (point, radius) => {
      // Minkowski-expanded actual 4.04 x 2.36 x .13 tablet case.
      assert.ok(Math.abs(point.x) >= 2.02 + radius || Math.abs(point.y) >= 1.18 + radius || Math.abs(point.z) >= .065 + radius,
        `${side} tap at ${step}% enters tablet case: ${point.toArray()} radius ${radius}`);
    };
    joints.forEach(point => check(point, arm.joints[0].geometry.parameters.radius));
    for (let segment = 0; segment < 3; segment++) for (let part = 0; part <= 30; part++) {
      check(joints[segment].clone().lerp(joints[segment + 1], part / 30), arm.segments[segment].geometry.parameters.radiusTop);
    }
  }
});

test('moving forelegs clear actual thorax/head triangle surfaces beyond their shoulder sockets', () => {
  const rig = stageModule.createFly(), board = stageModule.createEventBoard();
  stageModule.placeEventScene(rig.group, rig.head, board.group, new THREE.PerspectiveCamera());
  const body = rig.group.children.filter(mesh => mesh.isMesh).slice(0, 1);
  rig.head.traverse(mesh => { if (mesh.isMesh) body.push(mesh); });
  const triangles = [];
  for (const mesh of body) {
    const positions = mesh.geometry.attributes.position, indices = mesh.geometry.index;
    for (let index = 0; index < (indices?.count ?? positions.count); index += 3) {
      const vertices = [0, 1, 2].map(offset => new THREE.Vector3().fromBufferAttribute(positions, indices ? indices.getX(index + offset) : index + offset).applyMatrix4(mesh.matrixWorld));
      triangles.push(new THREE.Triangle(...vertices));
    }
  }
  const closest = new THREE.Vector3();
  for (const side of ['left', 'right']) for (let step = 0; step <= 100; step++) {
    const arm = rig.tapArms?.[side] ?? rig.swipeArm;
    arm.updateTap(rig.group, board.group, side, step / 100);
    const joints = arm.joints.map(joint => joint.getWorldPosition(new THREE.Vector3())), root = joints[0];
    for (let index = 1; index < joints.length; index++) {
      const minimum = Math.min(...triangles.map(triangle => triangle.closestPointToPoint(joints[index], closest).distanceTo(joints[index])));
      assert.ok(minimum >= arm.joints[index].geometry.parameters.radius, `${side} at ${step}% joint ${index} intersects actual body surface`);
    }
    for (let segment = 0; segment < 3; segment++) for (let part = 0; part <= 20; part++) {
      const point = joints[segment].clone().lerp(joints[segment + 1], part / 20);
      if (point.distanceTo(root) < .18) continue; // Only the bounded shoulder socket is embedded.
      const radius = arm.segments[segment].geometry.parameters.radiusTop;
      const minimum = Math.min(...triangles.map(triangle => triangle.closestPointToPoint(point, closest).distanceTo(point)));
      assert.ok(minimum >= radius, `${side} at ${step}% segment ${segment}: body surface distance ${minimum} < ${radius}`);
    }
  }
});
