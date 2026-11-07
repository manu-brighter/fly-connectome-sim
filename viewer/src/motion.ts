// Presentation-only motion. No recorded rate or motor readout enters this pose.
export function flyPose(tick: number, reducedMotion: boolean) {
  const time = reducedMotion ? 0 : tick / 10000;
  return {
    bob: Math.sin(time * 2 * Math.PI * 1.2) * .045,
    bodyPitch: Math.sin(time * 2 * Math.PI * .72) * .045,
    headYaw: Math.sin(time * 2 * Math.PI * .53 + .4) * .09,
    wingAngle: Math.sin(time * 2 * Math.PI * 7) * .24,
    legAngle: Math.sin(time * 2 * Math.PI * 1.4) * .055,
  };
}

// A single illustrative acknowledgement, never an extra neural measurement.
export function selectionTapProgress(selectedSide: 'left' | 'right' | null, holdElapsedTicks: number, reducedMotion: boolean) {
  if (selectedSide === null || reducedMotion || holdElapsedTicks <= 2000 || holdElapsedTicks >= 18000) return null;
  return (holdElapsedTicks - 2000) / 16000;
}
