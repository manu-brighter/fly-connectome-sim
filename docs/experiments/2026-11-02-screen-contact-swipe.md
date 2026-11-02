# Visible foreground-leg contact during a recorded swipe

The user clarified that the fly's arm must visibly move across the display.
The earlier fast-feed export only tilted and shifted an entire curved leg.
A diagnostic using that exact geometry placed its tip behind the phone's screen
plane, rather than on a readable swipe path. Its screen transition/input/frame
checks remain valid; they did not establish the requested visible limb contact.

The viewer correction uses a reusable three-segment foreground leg attached to
the fly. Current phone/fly transforms place its tip on the front display surface
during an upward stroke; body bob and pitch do not break that contact. Geometry
and movement remain illustrative, not measured anatomy or validated behavior.

The presentation gesture starts only after recorded ADVANCE:100ms reaching,
200ms contact stroke synchronized with the screen contents,100ms release and
retraction. It adds no observation, simulation tick, action, source frame or
presentation pause. During the illustrative approach the old last-fed frame
is held; during the stroke the incoming frame advances with the actual input.
STOP never triggers it; reduced motion bypasses it; seek/export use absolute
recorded time. The complete gesture is labelled illustrative.

## Reused measurement source

No Python/C++ source, protocol, policy or stimulus changed and no native run was
performed for this correction. The33-member model remains
`132b9c00a2a7d3d5da15963024abf85a0a31209d7f59f5903dd4edd9298a0ac2`.
The SAME ignored compact recording is
`runs/measured-video-replay-fast-reels-20261102.json`,12,443,795 bytes, SHA256
`fa9565bea925a66b2afaccb6e337a8dd5c3c2d0b52e65524575325e936b29323`.
It contains7s/210 measured input intervals/840 bins, with ADVANCE at3s.
Backend114-test/scientific-integrity checks are inherited unchanged source
evidence from the [fast-feed report](2026-11-02-fast-reel-feed-observation.md).

## Verification status

The old real Three-geometry diagnostic failed as expected: tip phone-local
z≈−1.24 was behind the display. New geometry tests cover actual mesh endpoints,
body transforms, anchor/segment continuity and upward contact at x=−.12,
y=−.77..+.75, z=.115 in phone coordinates (screen plane z=.075). A first
technically contacting revision still looked like a straight antenna in the
default-camera screenshot. The independent reviewer confirmed that visual
finding. Lowering knee/wrist along phone-local −Y made the elbow readable;
a projection regression first failed, then passed. Shoulder, tip path and
timeline stayed unchanged during that correction.

Final viewer tests: **66 passed**, no skips; TypeScript/Vite build exited0 with
the existing >500kB bundle advisory. The previous65-test run belongs to the
earlier visual candidate, not another additive suite. All20 first-party viewer
paths were frozen; the33 Python/C++ members and original compact-file hash were
checked unchanged. No backend/full-project/native tests were rerun.

Independent Sol source/geometry/visual review closed C0/I0/M0 after the
silhouette correction. It verified4002 actual Three-geometry poses and2001
contact/projection points, deterministic seeking and the actual decoded
lower/mid/upper/retracted frames. The final20-file viewer manifest SHA256 is
`9cef5b399a18ed638c51fdf229cb892d3f6fbade326f7f99890c10fcc04564d2`.

Chrome loaded the SAME compact file. At simulation3.2000s it showed clip1/frame6,
media PTS15360/15360, MBON11=100.00 and KC3.94, with the clearly bent foreground
leg touching the display. The actual export restored that paused position.
Its file is `viewer/test-output/screen-contact-arm-replay-30fps.webm`,
**2,484,033 bytes**, SHA256
`5841128e141af8a585de5543f282e777dedb24a47459878ecb3489fba8a36ee9`.
Independent EBML inspection and separate PyAV19.0.2 decoding confirmed225 VP9
frames,900x900,7.5s,33/34ms spacing and explicit end7500ms. It remains7s
measured replay plus15 labelled terminal-hold frames, with no new simulation time.

Decoded frame93 at3.1s shows lower-screen contact;96 at3.2s the middle of the
upward stroke;99 at3.3s upper-screen contact. The bent elbow and changing tip
position are visible in those actual encoded frames. Frame102 at3.4s is the
rest pose;224 retains the labelled terminal hold. The screen transition is
synchronized to the middle200ms, rather than starting before contact.

The correction does not expand scientific evidence or guarantee live-browser
FPS, mobile/accessibility or every browser. Raw recordings, screenshots, videos
and private test receipts remain ignored. Current continuation is recorded in
the [handover](../cloud-handover.md).
