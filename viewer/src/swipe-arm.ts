import * as THREE from 'three';

// Illustrative foreground foreleg, not a reconstruction of anatomy or motor output.
// Unit cylinders are transformed in place; no geometry is rebuilt while seeking.
export function createSwipeArm(material: THREE.Material, handedness = 1) {
  const group = new THREE.Group();
  const segmentGeometry = new THREE.CylinderGeometry(.032, .032, 1, 7);
  const jointGeometry = new THREE.SphereGeometry(.041, 8, 6);
  const rest = [new THREE.Vector3(.25, -.1, .25), new THREE.Vector3(.8, -.3, .72), new THREE.Vector3(1.16, -.77, .9), new THREE.Vector3(1.34, -.81, 1.02)];
  rest.forEach(point => { point.x *= handedness; });
  const points = rest.map((point) => point.clone());
  const targets = rest.map((point) => point.clone());
  const lengths = rest.slice(1).map((point, index) => point.distanceTo(rest[index]));
  const tapTarget = new THREE.Vector3(), tapDirection = new THREE.Vector3();
  const distal = new THREE.Vector3(), bend = new THREE.Vector3();
  const joints = points.map(() => {
    const mesh = new THREE.Mesh(jointGeometry, material); mesh.castShadow = true; group.add(mesh); return mesh;
  });
  const segments = points.slice(1).map(() => {
    const mesh = new THREE.Mesh(segmentGeometry, material); mesh.castShadow = true; group.add(mesh); return mesh;
  });
  const inverseFly = new THREE.Matrix4(), normal = new THREE.Vector3(), across = new THREE.Vector3(), down = new THREE.Vector3(), direction = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0), idleAxis = new THREE.Vector3(0, 0, 1);
  const smooth = (value: number) => value * value * (3 - 2 * value);
  function placeSegments() {
    joints.forEach((joint, index) => joint.position.copy(points[index]));
    segments.forEach((segment, index) => {
      direction.subVectors(points[index + 1], points[index]);
      segment.position.copy(points[index]).addScaledVector(direction, .5);
      segment.scale.set(1, direction.length(), 1);
      segment.quaternion.setFromUnitVectors(up, direction.normalize());
    });
    group.updateMatrixWorld(true);
  }
  function update(fly: THREE.Group, phone: THREE.Group, progress: number | null, idleAngle: number) {
    fly.updateWorldMatrix(true, false); phone.updateWorldMatrix(true, false);
    inverseFly.copy(fly.matrixWorld).invert();
    for (let index = 0; index < points.length; index += 1) {
      points[index].copy(rest[index]).sub(rest[0]).applyAxisAngle(idleAxis, idleAngle).add(rest[0]);
    }
    if (progress !== null && progress > 0 && progress < 1) {
      const stroke = THREE.MathUtils.clamp((progress - .25) / .5, 0, 1);
      // ~72% of the actual 1.19 × (160/90) display height, in front of its .075 plane.
      targets[3].set(-.12, -.77 + 1.52 * stroke, .115).applyMatrix4(phone.matrixWorld).applyMatrix4(inverseFly);
      normal.set(0, 0, 1).transformDirection(phone.matrixWorld).transformDirection(inverseFly);
      across.set(1, 0, 0).transformDirection(phone.matrixWorld).transformDirection(inverseFly);
      down.set(0, -1, 0).transformDirection(phone.matrixWorld).transformDirection(inverseFly);
      targets[0].copy(rest[0]);
      // Bend below the face in the default camera, then approach the display from below.
      targets[1].copy(rest[0]).lerp(targets[3], .4).addScaledVector(normal, .42).addScaledVector(across, -.22).addScaledVector(down, .9);
      targets[2].copy(rest[0]).lerp(targets[3], .77).addScaledVector(normal, .2).addScaledVector(across, .1).addScaledVector(down, .65);
      const blend = progress < .25 ? smooth(progress / .25) : progress > .75 ? smooth((1 - progress) / .25) : 1;
      for (let index = 0; index < points.length; index += 1) points[index].lerp(targets[index], blend);
    }
    placeSegments();
  }
  function updateTap(fly: THREE.Group, board: THREE.Group, side: 'left' | 'right' | null, progress: number | null) {
    fly.updateWorldMatrix(true, false); board.updateWorldMatrix(true, false);
    inverseFly.copy(fly.matrixWorld).invert();
    points.forEach((point, index) => point.copy(rest[index]));
    if (side !== null && progress !== null && progress > 0 && progress < 1) {
      const reach = progress < .4 ? progress / .4 : progress > .6 ? (1 - progress) / .4 : 1;
      tapTarget.set(side === 'left' ? -.96 : .75, side === 'left' ? -.65 : -.25, .115).applyMatrix4(board.matrixWorld).applyMatrix4(inverseFly);
      tapTarget.lerpVectors(rest[3], tapTarget, smooth(reach));
      normal.set(0, 0, 1).transformDirection(board.matrixWorld).transformDirection(inverseFly);
      tapTarget.addScaledVector(normal, Math.sin(Math.PI * reach) * .25);
      // Keep the distal segment in front of the card, then solve the two fixed
      // proximal lengths analytically with the original outward elbow pole.
      distal.set(0, .20, -.091).normalize().transformDirection(board.matrixWorld).transformDirection(inverseFly);
      tapDirection.subVectors(rest[3], rest[2]).normalize().lerp(distal, smooth(reach)).normalize();
      points[3].copy(tapTarget); points[2].copy(tapTarget).addScaledVector(tapDirection, -lengths[2]);
      tapDirection.subVectors(points[2], rest[0]);
      const distance = tapDirection.length(); tapDirection.normalize();
      const along = (lengths[0] ** 2 - lengths[1] ** 2 + distance ** 2) / (2 * distance);
      const height = Math.sqrt(Math.max(0, lengths[0] ** 2 - along ** 2));
      distal.set(handedness, -.6, .1);
      bend.subVectors(rest[1], rest[0]).lerp(distal, smooth(reach));
      bend.addScaledVector(tapDirection, -bend.dot(tapDirection)).normalize();
      points[1].copy(rest[0]).addScaledVector(tapDirection, along).addScaledVector(bend, height);
    }
    placeSegments();
  }
  placeSegments();
  return { group, segments, joints, update, updateTap };
}
