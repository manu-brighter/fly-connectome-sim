import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import { createMarketTraderScene, createMarketTraderRig, marketTradePose, validMarketInput, validMarketTrade, disposeMarketObjects, fitMarketCamera } from '../src/market-trader-scene.ts';

test('market prices use confirmed bounds and reach the actual endpoint in either direction', () => {
  for (const trade of [{ from: 4, to: 9, minimum: 3, maximum: 10 }, { from: 9, to: 4, minimum: 3, maximum: 10 }]) {
    assert.equal(marketTradePose(trade, 0, false).value, trade.from);
    assert.equal(marketTradePose(trade, 1, false).value, trade.to);
    assert.equal(marketTradePose(trade, .3, true).value, trade.to);
    for (let p = 0; p <= 1; p += .01) {
      const pose = marketTradePose(trade, p, false);
      assert.ok(pose.value >= Math.min(trade.from, trade.to) && pose.value <= Math.max(trade.from, trade.to));
      assert.ok(pose.handleY >= .72 && pose.handleY <= 1.72);
    }
  }
});

test('the freestanding phone remains clear of head and abdomen through the trade turn', () => {
  const rig = createMarketTraderRig();
  for (let p = 0; p <= 1; p += .05) {
    rig.pose(p * 2, p, null, false);
    rig.group.updateMatrixWorld(true);
    const phoneBox = new THREE.Box3().setFromObject(rig.phone);
    for (const local of [[0, 0, 0], [0, .05, .65], [0, -.1, -.9]]) {
      const point = rig.fly.group.localToWorld(new THREE.Vector3(...local));
      assert.ok(phoneBox.distanceToPoint(point) > .42, `Body or head intersects phone at ${p}`);
    }
  }
  disposeMarketObjects(rig.group);
});

test('swipe reaches the screen and price gesture contacts the moving physical handle', () => {
  const rig = createMarketTraderRig();
  for (const p of [.3, .5, .7]) {
    rig.pose(0, null, p, false); rig.group.updateMatrixWorld(true);
    const tip = rig.phone.worldToLocal(rig.fly.swipeArm.joints[3].getWorldPosition(new THREE.Vector3()));
    assert.ok(Math.abs(tip.x) < .595 && Math.abs(tip.y) < 1.05);
    assert.ok(tip.z > .095 && tip.z < .15);
  }
  for (const p of [.3, .5, .7]) {
    const trade = { from: 4, to: 9, minimum: 3, maximum: 10 };
    rig.pose(0, p, null, false, trade); rig.group.updateMatrixWorld(true);
    const tip = rig.fly.swipeArm.joints[3].getWorldPosition(new THREE.Vector3());
    assert.ok(tip.distanceTo(rig.handle.getWorldPosition(new THREE.Vector3())) < 1e-6);
  }
  disposeMarketObjects(rig.group);
});

test('both forelegs clear the physical phone throughout complete upward and downward trade gestures', () => {
  const rig = createMarketTraderRig();
  const phoneBounds = new THREE.Box3(new THREE.Vector3(-.748, -1.285, -.083), new THREE.Vector3(.705, 1.285, .098)).expandByScalar(.045);
  for (const trade of [{ from: 3, to: 10, minimum: 3, maximum: 10 }, { from: 10, to: 3, minimum: 3, maximum: 10 }]) {
    for (let step = 0; step <= 100; step++) {
      const progress = step / 100;
      rig.pose(progress * 2.6, progress, null, false, trade); rig.group.updateMatrixWorld(true);
      for (const arm of [rig.fly.swipeArm, rig.fly.oppositeArm]) {
        const points = arm.joints.map(joint => rig.phone.worldToLocal(joint.getWorldPosition(new THREE.Vector3())));
        for (let segment = 0; segment < 3; segment++) {
          const delta = points[segment + 1].clone().sub(points[segment]), length = delta.length();
          const hit = new THREE.Ray(points[segment], delta.normalize()).intersectBox(phoneBounds, new THREE.Vector3());
          assert.ok(!hit || hit.distanceTo(points[segment]) > length, `Phone intersection: price ${trade.from}→${trade.to}, progress ${progress}, segment ${segment}`);
        }
      }
    }
  }
  disposeMarketObjects(rig.group);
});

test('RGB uploads have bounded dimensions and exact byte counts; invalid prices are rejected', () => {
  assert.equal(validMarketInput({ id: 'one', pixels: new Uint8Array(18), width: 2, height: 3 }), true);
  for (const input of [{ id: 'x', pixels: new Uint8Array(18), width: 2, height: 4 }, { id: '', pixels: new Uint8Array(3), width: 1, height: 1 }, { id: 'x', pixels: new Uint8Array(3), width: 8192, height: 8192 }]) assert.equal(validMarketInput(input), false);
  assert.equal(validMarketTrade({ id: 'x', name: 'Water', from: 4, to: 5, minimum: 3, maximum: 8 }), true);
  for (const to of [NaN, Infinity, 9]) assert.equal(validMarketTrade({ id: 'x', name: 'Water', from: 4, to, minimum: 3, maximum: 8 }), false);
});

test('shared GPU resources are disposed exactly once', () => {
  const root = new THREE.Group(), geometry = new THREE.BoxGeometry(), texture = new THREE.Texture(), material = new THREE.MeshBasicMaterial({ map: texture });
  root.add(new THREE.Mesh(geometry, material), new THREE.Mesh(geometry, material));
  const calls = { geometry: 0, material: 0, texture: 0 };
  geometry.addEventListener('dispose', () => calls.geometry++); material.addEventListener('dispose', () => calls.material++); texture.addEventListener('dispose', () => calls.texture++);
  disposeMarketObjects(root);
  assert.deepEqual(calls, { geometry: 1, material: 1, texture: 1 });
});

test('portrait and landscape cameras frame the complete rig including wings, board, phone and desk', () => {
  const rig = createMarketTraderRig(), camera = new THREE.OrthographicCamera(-7, 7, 5, -5, .1, 70);
  const bounds = new THREE.Box3().setFromObject(rig.group);
  for (const aspect of [.45, .7, 1, 1.5, 2.4]) {
    fitMarketCamera(camera, rig.group, aspect);
    for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y]) for (const z of [bounds.min.z, bounds.max.z]) {
      const point = new THREE.Vector3(x, y, z).project(camera);
      assert.ok(Math.abs(point.x) <= .94 && Math.abs(point.y) <= .94, `Clipped scene at aspect ${aspect}: ${point.toArray()}`);
    }
  }
  disposeMarketObjects(rig.group);
});

test('reduced motion holds the final price without a gesture or autonomous body motion', () => {
  const rig = createMarketTraderRig(), trade = { from: 4, to: 9, minimum: 3, maximum: 10 };
  rig.pose(0, .5, .5, true, trade); rig.group.updateMatrixWorld(true);
  const points = rig.fly.swipeArm.joints.map(joint => joint.getWorldPosition(new THREE.Vector3()));
  rig.pose(123, .5, .5, true, trade); rig.group.updateMatrixWorld(true);
  assert.equal(rig.handle.position.y, marketTradePose(trade, 1, true).handleY);
  assert.equal(rig.fly.group.position.y, .98);
  rig.fly.swipeArm.joints.forEach((joint, index) => assert.ok(joint.getWorldPosition(new THREE.Vector3()).distanceTo(points[index]) < 1e-9));
  disposeMarketObjects(rig.group);
});

test('WebGL fallback clears stale photos and disposal cancels work and detaches observers', () => {
  const original = Object.fromEntries(['document', 'window', 'ResizeObserver', 'requestAnimationFrame', 'cancelAnimationFrame'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const elements = [], callbacks = new Map(); let disconnected = false, nextFrame = 0;
  const context = new Proxy({ createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }) }, { get: (object, key) => key in object ? object[key] : () => {} });
  const element = tag => {
    const value = { tag, style: {}, width: 0, height: 0, clientWidth: 700, clientHeight: 450, children: [], listeners: new Map(), setAttribute() {}, append(child) { this.children.push(child); child.parent = this; }, remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }, addEventListener(name, callback) { this.listeners.set(name, callback); }, removeEventListener(name) { this.listeners.delete(name); }, getContext: name => name === '2d' ? context : null };
    elements.push(value); return value;
  };
  const oldError = console.error;
  try {
    console.error = () => {};
    Object.defineProperties(globalThis, {
      document: { configurable: true, value: { createElement: element, hidden: false } },
      window: { configurable: true, value: { devicePixelRatio: 1, matchMedia: () => ({ matches: false }) } },
      ResizeObserver: { configurable: true, value: class { observe() {} disconnect() { disconnected = true; } } },
      requestAnimationFrame: { configurable: true, value: callback => { callbacks.set(++nextFrame, callback); return nextFrame; } },
      cancelAnimationFrame: { configurable: true, value: id => callbacks.delete(id) },
    });
    const host = element('host'), scene = createMarketTraderScene(host);
    const input = { id: 'one', pixels: new Uint8Array(18), width: 2, height: 3 };
    scene.setInput(input);
    assert.equal(elements.some(value => value.width === 2 && value.height === 3), false, 'Disconnected scenes do not accept fresh photos');
    scene.setConnection(true);
    scene.setInput(input);
    const photo = elements.find(value => value.width === 2 && value.height === 3);
    assert.ok(photo, 'Actual image is copied into a bounded surface');
    scene.setInput(null); assert.equal(photo.width, 1); assert.equal(photo.height, 1);
    scene.setInput(input); scene.setActivity({ motor_left: 2, motor_right: NaN });
    const replacement = elements.find(value => value.width === 2 && value.height === 3);
    scene.setConnection(false); assert.equal(replacement.width, 1, 'Disconnect clears the active image without waiting for the caller');
    scene.setTrade({ id: 'one', name: 'Water', from: 4, to: 5, minimum: 3, maximum: 8 });
    const root = host.children[0], webglCanvas = root.children[0];
    webglCanvas.listeners.get('webglcontextlost')({ preventDefault() {} });
    assert.equal(root.children.length, 2, 'Context loss reuses the bounded fallback surface');
    assert.equal(callbacks.size, 1); scene.dispose(); scene.dispose();
    assert.equal(callbacks.size, 0); assert.equal(disconnected, true); assert.equal(host.children.length, 0);
    assert.equal(webglCanvas.listeners.size, 0);
    scene.setInput(input); assert.equal(callbacks.size, 0);
  } finally {
    console.error = oldError;
    for (const [key, descriptor] of Object.entries(original)) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; }
  }
});
