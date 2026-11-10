# Isolated local image decoding — prospective D2 design

Status: **Task1 worker independently accepted locally; Task2 parent remains open**.
See [component evidence](../../experiments/2026-11-10-image-decoding.md). The
[preceding D1](2026-11-10-image-admission-design.md) source CI gate and this
contract's independent prospective review are complete.

## Boundary and inspected basis

Decode one accepted bounded image in an owned disposable process and return exact
64×64 RGB bytes. No HTTP, upload UI, moderation UI, native engine, D1 mutation,
price mutation, API call or public/LAN exposure. New files: `market/image_decode.py`
(parent/API), `market/image_decode_windows.py` (small launch/pipe adapter),
`scripts/market-image-decode-worker.py` (private child/transform), and corresponding
`tests/market/test_image_decode*.py`. Do not change frozen helpers, core, D1,
authority, dependencies or replay. Engineering defaults below are not event
capacity, user promises or biological calibration.

Actual local inspection found Python3.12.14, Pillow12.3.0 and NumPy2.4.6 matching
the manifest. Pillow provides restricted-format opening, verify/load, EXIF
transpose, alpha compositing and fixed resampling; no new dependency is required.
Parent does not import Pillow or decode pixels. Portable transform tests may import
the child with trusted fixtures; production never falls back to in-process decode.
Real process ownership in this slice is Windows-only; Linux tests establish pixel
and protocol behavior, not Windows lifecycle or Linux process containment.

## Public parent contract and clocks

```text
DecodeRequest(incarnation: UUID, id: UUID, source_sha256: digest,
              encoded_bytes: int, media_type: "image/jpeg"|"image/png",
              accepted_ns: int, decode_deadline_ns: int)
DecodedImage(incarnation: UUID, id: UUID, source_sha256: digest,
             frame_sha256: digest, preprocessing_version: "market-rgb64/v1",
             rgb: bytes, source_width: int, source_height: int,
             oriented_width: int, oriented_height: int,
             format: "JPEG"|"PNG", completed_ns: int,
             observed_peak_working_set_bytes: int)
ImageDecoder(work_root: Path, clock: Clock|None = None)
ImageDecoder.decode(*, request: DecodeRequest, payload: bytes,
                    cancel: threading.Event|None = None) -> DecodedImage
ImageDecoder.close() -> None
```

Frozen exact dataclasses; exact built-in str/int/bytes, no bool-as-int, subclass,
bytearray or arbitrary mapping/iterable coercion. UUID/digest rules match D1.
Times are integers `[0, 2**63-1]`; require accepted+10000000000 without overflow,
decode_deadline_ns exactly that sum, accepted_ns<=now<deadline. Require
len(payload)=encoded_bytes in1..2097152 and SHA256(payload)=source_sha256 before
launch. Only these two exact MIME values are admitted; caller sends no filename,
URL, executable, model option, command or per-image directory.

Use unchanged public Clock/ClockSample/SystemClock from price_service. One common
perf-counter domain with D1 is required. Sample before launch, every monitor poll,
on final validation and after cleanup; backwards/invalid/failed samples fail closed.
The absolute D1 decode deadline includes writing/launch/import/decode/output and
successful cleanup. It is NEVER replaced by launch+10s or child-reported time.
Equality is timeout. A late valid child result is discarded. No automatic retry.
The child cannot read or call D1. Later trusted integration calls decoded only
while D1 still accepts the original receipt; D1 remains final lifecycle authority.

DecodeError.code is exactly invalid_request, busy, closed, unsupported_platform, ownership,
timeout, cancelled, clock, malformed_image, unsupported_format, geometry, mode,
multiple_frames, source_mismatch, child_failed, child_protocol, memory_limit,
monitor_stalled, cleanup_failed. No child exception text/raw image metadata leaks.
One short state lock protects busy/closed flags and latched cleanup/clock faults.
decode checks, in order: closed→closed, busy→busy, cleanup fault→ownership,
clock fault→clock, exact syntax/byte length, then marks busy. It never queues a
caller or retains a refused payload. Sample clock/check deadline/hash before files
or launch; clear busy only after terminal cleanup handling. Hash mismatch is
source_mismatch; invalid declared length/type is invalid_request.

close on closed returns None without clock/filesystem reads; close while busy raises
busy. Otherwise close may retry bounded cleanup using ONLY its retained exact Job/
process handles and known files, never PID discovery. If process closure cannot be
confirmed, retain the bounded owner context and root lock, keep closed=false and
raise cleanup_failed. Do not discard the last usable Job/process handles merely
because some other handles closed. Once held process exit AND zero Job processes
are confirmed, handles/files may be cleaned; filesystem/handle-cleanup failure also
retains the root lock and faults reuse. Only successful complete cleanup releases
DatabaseOwnership and sets closed=true. This also applies after clock/cleanup
faults. Closed takes precedence over retained fault labels; decode after successful
close always raises closed. No new recovery method or automatic reopened instance.
At a monitor poll, simultaneous failures select clock, cancelled, timeout,
monitor_stalled, memory_limit, child_protocol, then child_failed, in that order.
The first selected failure is retained; cleanup_failed overrides every outcome.
After owned-process drain and cleanup, sample the parent clock once more (unless
already clock-faulted), latching any newly detected clock fault even if a previous
failure remains the returned reason. Then perform one final cancel.is_set read:
that read is the cancellation cutoff. A candidate success selects clock, cancelled,
then timeout at this final gate; cancellation observed there rejects even if it
arrived during cleanup. Event.set after that read is outside the completed call.
No blocking work follows that gate before publishing RGB; completed_ns is this
final successful parent sample, not child exit time. Earlier failures remain first
unless cleanup_failed overrides; later clock failure still prevents instance reuse.
Format/geometry/decode rejections require protocol/exit/ownership validation.

## Existing ownership reuse and smallest new surface

Reuse unchanged `scripts/market_supervision.py` WindowsJob and WindowsProcess
classes, including held identity/peak/exit and terminate-and-wait. Do not call
WindowsJob.assign: it repairs missing membership and is not verification-only.
Its plain scripts-namespace import fails on the flat market_artifacts import.
One startup-only import before service threads may temporarily prepend the fixed
repository scripts directory, import market_supervision, then remove that entry
in finally. Verify both modules' resolved __file__ match the fixed repository files;
refuse preloaded foreign modules. Local inspection confirmed this loads only
market_artifacts/the pure recorder, not engine construction or a supervisor run.
Do not call the old acquisition runner, readiness, native release or log functions.

The controller selected creation-time Job assignment: new code is limited to
STARTUPINFOEX/attribute-list CreateProcessW launch and anonymous output pipe setup/
capped reading. Supply PROC_THREAD_ATTRIBUTE_JOB_LIST containing the owned Job
and PROC_THREAD_ATTRIBUTE_HANDLE_LIST containing exactly the three child streams.
Reuse the old STARTUPINFO/PROCESS_INFORMATION structures inside the extended
adapter and WindowsProcess(handle=returned_handle), raw K.IsProcessInJob verification,
K.ResumeThread/handle-close/termination primitives. A separate ctypes function
binding must not mutate frozen module function signatures. Do not duplicate its
Job/process classes or process-tree monitor. No frozen-file extraction is needed.

Launch the actual executable held by WindowsProcess(os.getpid()).identity, not a
bare command/PATH lookup or the venv redirector. Require Python3.12.14 and the
expected repository venv package directory. Invoke that exact interpreter with
`-I -S -B`, the fixed child script and the generated job directory. Bytecode writes
are disabled before any package import, including absent/stale caches. The bootstrap
adds only the verified fixed `.venv/Lib/site-packages` for Pillow and refuses any
Pillow version other than12.3.0; no user site,
PYTHONPATH or dynamic script selection. Clear inherited environment except required
Windows system directory variables and job-local TEMP/TMP. No provider credentials.
The child imports no market authority, D1, native code or project engine.

Create suspended/hidden, already assigned through JOB_LIST to the newly owned
non-inheritable kill-on-close Job. Hold actual process/thread handles, verify
executable identity, creation time and direct verify-only IsProcessInJob against
the held process/owned Job, then resume. False or failing membership is ownership
failure: terminate the exact held suspended process and drain owned resources;
never call assign/AssignProcessToJobObject to repair a missing JOB_LIST binding.
The only
inherited handles are stdin=NUL,
stderr=NUL and the child stdout pipe; parent read end and Job handle are excluded.
Close parent copies of child pipe ends promptly. Assignment/identity/resume failure
terminates the exact held suspended process and closes all handles, never PID search.
Parent crash closes its Job handle and terminates the creation-time-bound child
and descendants, including before verification/resume. There is no fallback to
create-then-assign. Unsupported attributes, failed ownership or incompatible Job
configuration fail closed without releasing a child outside its owned Job. This
requires Windows10/Server2016 or newer and this local Python3.12 runtime; actual
Windows11 parent-crash evidence is required, not inferred from the API alone.

## Finite scratch and child output

work_root is trusted startup configuration: an existing directory under repository
`.tools/`, absolute/resolved with every component free of symlinks/junctions. No
image-controlled paths. Hold unchanged DatabaseOwnership on work_root/decoder
for instance lifetime; it creates decoder.owner.lock. At most one `job` directory
exists, containing only request.json (<=2048 bytes) and input.bin (<=2097152 bytes).
Create exclusively; use no recursive cleanup or caller-named files. Child cwd/TMP
is job; trusted decoder code creates no other files. Parent checks identities of
opened ordinary files and ancestors, and refuses reparse points or unexpected
entries. An existing job directory on opening a new instance refuses ownership;
do not guess that a crashed previous worker has finished from a free file lock.
No automatic stale deletion, fresh-directory rotation or accumulation is allowed.
Recovery may separately inspect owned-process closure and clean that exact bounded
directory. During the current owned call, empty/partially written known files are
removable only after zero owned processes is confirmed.

Request JSON has exactly schema="market-image-decode/v1", incarnation, id,
source_sha256, encoded_bytes, media_type. Strict UTF-8, duplicate/unknown keys and
nonfinite values rejected; no pixel or user-provided metadata in it. Child validates
file size/type and exact source hash again before parsing. No native timestamps
or D1 status in child protocol. The generated directory is not a public CLI path.

stdout is ONE bounded binary message: uint32 little-endian JSON-header byte count,
strict JSON header <=2048 bytes, then either exactly12288 RGB bytes or zero on
rejection. Total <=14340 bytes. Parent retains at most14341 bytes to detect overflow,
reads only currently available bytes in <=4096-byte chunks and checks the clock/
cancel/memory between reads; never unbounded communicate/read or a blocking pipe
thread. Extra/truncated bytes, duplicate messages, wrong keys/digests/IDs, stdout
after the exact frame or a nonzero exit reject. stderr goes to NUL, not an unlimited
log. Require EOF, process exit0 and empty owned job before successful return.

Both success and rejection headers have exactly schema="market-image-decode-result/v1".
Header success keys: schema, incarnation, id, source_sha256, status="decoded",
preprocessing_version, frame_sha256, source_width, source_height, oriented_width,
oriented_height, format. Rejection keys: schema, incarnation, id, source_sha256,
status="rejected", reason (malformed_image/unsupported_format/geometry/mode/
multiple_frames/source_mismatch). Parent distrusts and strictly validates all
header fields/geometry and independently hashes RGB. Pillow's
DecompressionBombWarning/DecompressionBombError map to geometry. Other warning, invalid EXIF
orientation, metadata parse failure and supported decoder verify/load errors map
to malformed_image. MIME/format mismatch maps to unsupported_format; out-of-bounds
dimensions to geometry, prohibited source bit depth/mode to mode, non-single-frame
to multiple_frames, and rechecked input hash mismatch to source_mismatch.
Unexpected child exceptions
exit nonzero without traceback and become child_failed; they are not success.

## Exact pixel policy market-rgb64/v1

1. Child permits Pillow JPEG/PNG decoders only and requires decoded format to match
   MIME. Set LOAD_TRUNCATED_IMAGES=False, MAX_IMAGE_PIXELS=12000000; treat warnings
   during opening/verification/loading/transform as malformed_image, except Pillow's
   decompression-bomb warning/error maps to geometry as above. Set PNG
   MAX_TEXT_CHUNK=65536 and MAX_TEXT_MEMORY=262144 using their pinned Pillow
   semantics: the safe zlib helper bounds expanded bytes per compressed payload;
   the text accumulator sums decoded value-string lengths (Unicode code points)
   for successfully decoded text chunks, including repeated keys. These are NOT
   all-chunk encoded-byte caps: uncompressed tEXt/iTXt has no65536-byte per-value
   cap, multibyte UTF-8 may exceed262144 encoded bytes while below the character
   limit, and keys/language fields are not counted by that accumulator. Existing
   2-MiB whole-source and sampled-memory limits remain separate. Do not add a
   general PNG text parser or claim malformed metadata silently ignored by Pillow
   was rejected. Excesses detected by these limits map to malformed_image.
2. Require dimensions1..8192 and product<=12000000 BEFORE full load; require n_frames
   exactly1 (static JPEG's absent n_frames means1). Allowed source modes are JPEG
   L/RGB and PNG1/L/LA/P/RGB/RGBA. Before full load, inspect PNG's first IHDR:
   require signature,13-byte IHDR length/type and valid IHDR CRC within the first
   33 bytes, then reject source bit depth16 as mode, including RGB16/RGBA16 that
   Pillow otherwise exposes as RGB/RGBA. Source1/2/4/8-bit combinations still require
   valid decoder/color-type/mode constraints. Invalid IHDR is malformed_image.
   Reject CMYK/integer/float/other decoded modes; no silent color conversion.
   verify(), reopen the same bounded immutable source bytes, recheck, then load().
   This detects supported decoder errors; it is not a proof of arbitrary file purity.
3. EXIF-only orientation: after full load, use a FRESH Image.Exif object loaded
   from image.info["exif"] when present; absent orientation is1. Do not call image
   getexif/exif_transpose, whose cached/XMP fallback would change this rule. Ignore
   XMP-only orientation and Raw-profile fallback. Require exact integer1..8 and
   apply1=identity,2=FLIP_LEFT_RIGHT,3=ROTATE_180,4=FLIP_TOP_BOTTOM,5=TRANSPOSE,
   6=ROTATE_270,7=TRANSVERSE,8=ROTATE_90 using Image.Transpose. Malformed EXIF or
   orientation maps to malformed_image; EXIF wins over conflicting XMP.
   Preserve the pre-orientation dimensions separately. Ignore ICC/XMP color profiles:
   output uses decoded channel values, not a color-managed photographic conversion.
   Output has no EXIF/XMP/ICC/comments/text metadata because it is raw RGB only.
4. Convert oriented image to RGBA (including palette/transparency), composite over
   opaque black using pinned Pillow alpha_composite, then convert to RGB BEFORE
   resampling. With oriented w,h and L=max(w,h), choose each output extent as
   max(1,(64*extent + L//2)//L). This intentionally upscales small images, caps the
   longer side at64 and uses integer half-up sizing. Resize with BILINEAR.
5. Paste unmasked into a black RGB64×64 canvas at ((64-width)//2,(64-height)//2);
   odd padding goes right/bottom. Emit exactly12288 top-to-bottom C-order RGB bytes.
   Frame hash follows unchanged engine rgb-input/v1: SHA256 of the exact prefix
   `{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n`
   followed by those bytes. Parent computes the same digest without importing engine.

The preview later displayed/approved must use these exact canonical pixels, never
the original file. A decoded result is not moderation approval or image handoff.

## Monitoring, failure and cleanup truth

Poll target20ms, maximum adjacent poll gap250ms; larger gap rejects monitor_stalled.
Sample actual held process peak working set; above536870912 bytes terminates with
memory_limit. This is the sampled held process's PeakWorkingSetSize, not total
system RAM or a sum of coincident child peaks. Require the Job to contain only that
one decoder; unexpected children
reject child_protocol and are terminated as owned descendants. Deadline/cancel/
clock/pipe/protocol failure kills the Job; terminate-and-wait is bounded by the
existing10-second cleanup wait. Already exited process still needs final pipe,
identity/peak/exit/job checks. Catch cancellation/BaseException through finally;
KeyboardInterrupt re-raises only after proven successful cleanup; if cleanup also
fails, raise cleanup_failed instead and retain the faulted owned state. Apply that
same cleanup override to other BaseException unwinding. Never kill unrelated processes.

This is a separate process with supervised stop thresholds, NOT an OS sandbox,
credential boundary, filesystem/network denial or instantaneous memory quota.
Sampling may overshoot; owner scheduling/OS calls can stall;10s decode expiration
does not imply all cleanup completed by10s. After kill, verify zero Job processes,
close pipes/process/thread/Job handles only once process closure is confirmed,
remove only the two recognized files and
empty job directory, then return/raise. Cleanup failure wins over the original
decode result, discards RGB, retains bounded owner context/root lock as defined
above and refuses reuse until successful close. No unbounded failure-history list.
Returned pixels never coexist with an unconfirmed surviving decoder. Parent crash
can leave the bounded input file and block reopening until explicit local recovery;
do not claim instant erasure
or secure deletion. No full-night image/log retention or process-history arrays.

## Required gates and evidence

The controller's creation-time Job choice resolves the identified launch gap;
it is a technical local implementation decision, not a new user approval gate.
Microsoft documents JOB_LIST creation-time assignment and HANDLE_LIST restricted
inheritance in [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
The old suspended-create-then-assign method alone cannot establish parent-crash
ownership in its pre-assignment interval. The new narrow launcher must be reviewed
and exercised with harmless actual children before any image lifecycle acceptance.

Tests: trusted PNG/JPEG fixtures, MIME mismatch, modes/frames/geometry/byte edges,
truncation/CRC/text limits including uncompressed/multibyte/repeated keys, RGB16/
RGBA16 source rejection, eight EXIF orientations, XMP-only/conflicting orientation,
alpha/palette/grayscale, exact aspect
rounding/padding/hash and metadata absence; strict protocol/oversized/truncated pipe,
startup/assignment failure, timeout, cancellation, child crash, memory/monitor gap,
missing creation-time membership with no assign fallback, final cancel during
cleanup, final deadline equality, post-cleanup clock fault, interrupt plus cleanup
failure, closed/faulted/busy precedence and idempotent close, bounded retained
ownership and later close cleanup, exact response schema/reasons, absent/stale
bytecode-cache fixture, stale scratch and symlink/junction refusal. Actual harmless Windows
children must establish successful decode, flooding/timeout cancellation, parent
crash including launch, zero survivors and unrelated-process preservation. Real
Windows lifecycle tests may skip on Linux with the reason; portable pixel passes
are not ownership evidence. No new native model or user image run is needed.
