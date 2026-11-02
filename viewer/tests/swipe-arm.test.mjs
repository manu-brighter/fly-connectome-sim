import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import * as armModule from '../src/swipe-arm.ts';
import { flyPose } from '../src/motion.ts';

test('articulated foreground tip contacts and traverses the real portrait display under fly motion', () => {
  const fly = new THREE.Group(), phone = new THREE.Group();
  fly.position.set(-.65, .85, .1); fly.rotation.y = 1.1;
  phone.position.set(1.5, 1.02, .7); phone.rotation.y = -.2; phone.rotation.x = -.75;
  const arm = armModule.createSwipeArm(new THREE.MeshStandardMaterial()); fly.add(arm.group);
  const geometries = arm.segments.map((segment) => segment.geometry), tips = [];
  for (const [tick, progress] of [[41000, .25], [42000, .5], [43000, .75]]) {
    const pose = flyPose(tick, false);
    fly.position.y = .85 + pose.bob; fly.rotation.x = pose.bodyPitch;
    arm.update(fly, phone, progress, -pose.legAngle);
    fly.updateMatrixWorld(true);
    const tip = phone.worldToLocal(arm.segments[2].localToWorld(new THREE.Vector3(0, .5, 0)));
    assert.ok(Math.abs(tip.x) < .595 && tip.y > -1.0678 && tip.y < 1.0478);
    assert.ok(tip.z > .095 && tip.z < .15, `Tip must sit just in front of pixels, got ${tip.z}`);
    tips.push(tip.y);
    const anchor = fly.worldToLocal(arm.joints[0].getWorldPosition(new THREE.Vector3()));
    assert.ok(anchor.distanceTo(new THREE.Vector3(.25, -.1, .25)) < 1e-6);
    for (let index = 0; index < 3; index += 1) {
      const start = arm.segments[index].localToWorld(new THREE.Vector3(0, -.5, 0));
      const end = arm.segments[index].localToWorld(new THREE.Vector3(0, .5, 0));
      assert.ok(start.distanceTo(arm.joints[index].getWorldPosition(new THREE.Vector3())) < 1e-6);
      assert.ok(end.distanceTo(arm.joints[index + 1].getWorldPosition(new THREE.Vector3())) < 1e-6);
      assert.ok(start.toArray().concat(end.toArray()).every(Number.isFinite));
      assert.ok(start.distanceTo(end) > .1);
      assert.equal(arm.segments[index].geometry, geometries[index]);
    }
    const upper = arm.segments[0].getWorldDirection(new THREE.Vector3());
    assert.ok(upper.toArray().every(Number.isFinite));
    const a = arm.joints[0].position, b = arm.joints[1].position, c = arm.joints[2].position;
    assert.ok(new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3().subVectors(c, b)).length() > .02, 'The foreleg must visibly bend at a joint');
  }
  assert.ok(tips[1] > tips[0] && tips[2] > tips[1] && tips[2] - tips[0] > 1.3);
});

test('reach, release and backward seek are absolute poses and idle reuses the original foreleg anchor', () => {
  const fly = new THREE.Group(), phone = new THREE.Group();
  phone.position.set(1.5, 1.02, .7); phone.rotation.set(-.75, -.2, 0);
  const arm = armModule.createSwipeArm(new THREE.MeshBasicMaterial()); fly.add(arm.group);
  const tip = () => arm.segments[2].localToWorld(new THREE.Vector3(0, .5, 0));
  arm.update(fly, phone, null, .03); fly.updateMatrixWorld(true); const rest = tip();
  for (const progress of [0, 1]) {
    arm.update(fly, phone, progress, .03); fly.updateMatrixWorld(true);
    assert.ok(tip().distanceTo(rest) < 1e-6);
  }
  arm.update(fly, phone, .125, .03); fly.updateMatrixWorld(true); const reach = tip();
  assert.ok(reach.distanceTo(rest) > .2);
  arm.update(fly, phone, .875, .03); fly.updateMatrixWorld(true); const release = tip();
  assert.ok(release.distanceTo(rest) > .2);
  arm.update(fly, phone, .125, .03); fly.updateMatrixWorld(true);
  assert.ok(tip().distanceTo(reach) < 1e-6);
  arm.update(fly, phone, null, .03); fly.updateMatrixWorld(true);
  assert.ok(tip().distanceTo(rest) < 1e-6);
});

test('default 900px camera sees a bent foreleg below the face throughout the contact stroke', () => {
  const fly = new THREE.Group(), phone = new THREE.Group();
  fly.position.set(-.65, .85, .1); fly.rotation.y = 1.1;
  phone.position.set(1.5, 1.02, .7); phone.rotation.set(-.75, -.2, 0);
  const arm = armModule.createSwipeArm(new THREE.MeshBasicMaterial()); fly.add(arm.group);
  const camera = new THREE.PerspectiveCamera(35, 1, .1, 50);
  camera.position.set(6.1, 5.3, 10.8); camera.lookAt(.25, .9, 0); camera.updateMatrixWorld(true);
  const projected = (point) => {
    const ndc = point.project(camera); return new THREE.Vector2((ndc.x + 1) * 450, (1 - ndc.y) * 450);
  };
  for (let elapsed = 1000; elapsed <= 3000; elapsed += 100) {
    const pose = flyPose(30000 + elapsed, false);
    fly.position.y = .85 + pose.bob; fly.rotation.x = pose.bodyPitch;
    arm.update(fly, phone, elapsed / 4000, -pose.legAngle); fly.updateMatrixWorld(true);
    const [shoulder, knee, wrist, tip] = arm.joints.map((joint) => projected(joint.getWorldPosition(new THREE.Vector3())));
    const face = projected(fly.localToWorld(new THREE.Vector3(0, .05, .65)));
    assert.ok(knee.y > Math.max(face.y, shoulder.y) + 30, `Elbow is hidden at ${elapsed} ticks`);
    assert.ok(wrist.y > face.y + 10, `Wrist crosses the face at ${elapsed} ticks`);
    const strokeLine = tip.clone().sub(shoulder), kneeOffset = knee.clone().sub(shoulder);
    const bendDistance = Math.abs(strokeLine.cross(kneeOffset)) / strokeLine.length();
    assert.ok(bendDistance > 30, `Foreleg projects as a straight rod at ${elapsed} ticks`);
    assert.ok(knee.distanceTo(wrist) > 25 && wrist.distanceTo(tip) > 25);
  }
});
