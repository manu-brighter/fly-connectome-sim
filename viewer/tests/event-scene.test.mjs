import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import * as stageModule from '../src/stage.ts';
import * as armModule from '../src/swipe-arm.ts';
import { selectionTapProgress } from '../src/motion.ts';

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
