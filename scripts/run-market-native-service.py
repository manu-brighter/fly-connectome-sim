"""Explicit bounded native-image proof beside a synthetic local price board."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Failed cleanup retains the actual owners and fences any later release.
_unclosed_owners = ()


def _check_platform():
    if sys.platform != "win32" or sys.version_info[:3] != (3, 12, 14):
        raise ValueError("unsupported_platform")


def _ordinary(path):
    path = Path(path).absolute()
    for member in (path, *path.parents):
        info = member.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("unsafe_path")
    return path


def _control(path):
    from market.native_protocol import parse_json
    path = _ordinary(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 1048576:
        raise ValueError("invalid_control")
    with path.open("rb") as stream:
        raw = stream.read(1048577)
        after = os.fstat(stream.fileno())
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if len(raw) != before.st_size or identity(before) != identity(after) or identity(before) != identity(path.stat()):
        raise ValueError("changed_control")
    return raw, parse_json(raw, byte_limit=1048576, node_limit=20000)


def _read_prepared_config(root):
    from market.native_protocol import canonical_bytes, canonical_sha256, validate_protocol, validate_bindings
    from market.native_session import NativeConfig
    raw_protocol, value = _control(root / "protocol.json")
    from market.native_protocol import from_declaration, scope
    profile = from_declaration(value)
    with scope(profile):
        declaration = validate_protocol(value)
    raw_bindings, value = _control(root / "bindings.json")
    with scope(profile):
        bindings = validate_bindings(value, declaration)
    if raw_protocol != canonical_bytes(declaration) or raw_bindings != canonical_bytes(bindings):
        raise ValueError("noncanonical_control")
    if Path(bindings.project_root) != ROOT or Path(bindings.work_root) != root:
        raise ValueError("wrong_root")
    if Path(bindings.decoder_work_root) != root.parent / (root.name + "-decoder"):
        raise ValueError("wrong_decoder_root")
    return NativeConfig(bindings.incarnation, bindings.worker_session, canonical_sha256(declaration), root,
        profile=profile.name, duration_minutes=profile.duration_minutes, max_observations=profile.max_observations)


def _decoder_root(root):
    tools = ROOT / ".tools"
    decoder = root.parent / (root.name + "-decoder")
    if not root.is_relative_to(tools) or root == tools:
        raise ValueError("unsafe_work_root")
    _ordinary(root.parent)
    return decoder


def _fresh_database(path, root, decoder):
    path = path.absolute()
    _ordinary(path.parent)
    if path.is_relative_to(root) or path.is_relative_to(decoder):
        raise ValueError("unsafe_database")
    if any(os.path.lexists(str(path) + suffix) for suffix in ("", "-wal", "-shm", ".owner.lock")):
        raise ValueError("existing_database")
    return path


def _watch_session(session, server, stopped, failed):
    try:
        while not stopped.wait(0.05):
            snapshot = session.snapshot()
            if snapshot.fault is not None or snapshot.cleanup_fault is not None:
                failed.set()
                server.shutdown()
                return
            if snapshot.state in ("ended", "closed"):
                # Two seconds remain inside the session's existing finalization budget.
                if not stopped.wait(2):
                    server.shutdown()
                return
    except Exception:
        failed.set()
        server.shutdown()


def _start(args):
    global _unclosed_owners
    from market.fixtures import load_config
    from market.image_admission import AdmissionController
    from market.image_decode import ImageDecoder
    from market.image_intake import ImageIntake
    from market.local_server import _load_assets, _validate_bind, create_server
    from market.native_session import NativeSession
    from market.price_service import SystemClock, open_authority

    if _unclosed_owners:
        raise ValueError("unclosed_owner")
    _check_platform()
    root = args.work_root.absolute()
    decoder_root = _decoder_root(root)
    _ordinary(root)
    _ordinary(decoder_root)
    if not decoder_root.is_dir() or any(decoder_root.iterdir()):
        raise ValueError("decoder_not_fresh")
    db = _fresh_database(args.db, root, decoder_root)
    _validate_bind(args.host, args.port)
    _load_assets(args.assets, images_enabled=True)
    config = load_config(args.config)
    native_config = _read_prepared_config(root)
    clock = SystemClock()
    session = NativeSession(native_config, clock)
    prepared = session.load_prepared(args.prepared_sha256)
    decoder = authority = intake = server = watcher = None
    native_prices = None
    live = native_config.profile == "live-pilot/v1"
    attempted = False
    stopped, failed = threading.Event(), threading.Event()
    result = 0
    try:
        decoder = ImageDecoder(decoder_root, clock)
        authority = open_authority(config, db, clock, mode="native") if live else open_authority(config, db, clock)
        if live:
            from market.native_price import NativePricePump
            native_prices = NativePricePump(authority, session, clock, max_observations=native_config.max_observations)
        _unclosed_owners = (session, decoder, authority)
        attempted = True
        session.start(prepared, allow_native_run=True)
        intake = ImageIntake(AdmissionController(native_config.incarnation, clock), decoder, clock, native_session=session)
        _unclosed_owners = (intake, authority)
        server_options = dict(image_intake=intake)
        if live:
            server_options["native_prices"] = native_prices
        server = create_server(authority, args.host, args.port, args.assets, **server_options)
        _unclosed_owners = (server,)
        if live:
            print(f"Lokaler Live-Pilot ({native_config.profile}): maximal {native_config.duration_minutes} reale Minuten / {native_config.max_observations} Beobachtungen; eine durchgehende Engine.", flush=True)
            print("Experimentelle neuronale Preissteuerung — keine Verkaufspreise oder biologische Validierung.", flush=True)
        else:
            print("Begrenzter nativer Bildtest: 40 Beobachtungen / 20 Modellsekunden / maximal 900 reale Sekunden.", flush=True)
            print("Synthetische Preise — keine Verkaufspreise; keine neuronale Preissteuerung.", flush=True)
        print("Startmeldung misst Hostzeit vor observe; kein Nachweis des physischen C++-Eintritts.", flush=True)
        print("Clock: " + json.dumps(clock.describe(), sort_keys=True), flush=True)
        print(server.operator_url, flush=True)
        print(server.view_url, flush=True)
        print(server.guest_url, flush=True)
        watcher = threading.Thread(target=_watch_session, args=(session, server, stopped, failed), name="native-cli-watch", daemon=True)
        watcher.start()
        server.serve_forever()
        snapshot = session.snapshot()
        if failed.is_set() or snapshot.fault is not None or snapshot.cleanup_fault is not None:
            result = 1
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        try:
            # Server owns intake, which owns session+decoder; never close them twice.
            if server is not None:
                server.server_close()
            else:
                try:
                    if intake is not None:
                        intake.begin_stop()
                        intake.finish_close()
                    else:
                        try:
                            if attempted:
                                session.begin_stop("shutdown")
                                session.finish_receipts()
                                session.finish_close()
                        finally:
                            if decoder is not None:
                                decoder.close()
                finally:
                    if authority is not None:
                        authority.close()
            _unclosed_owners = ()
        except BaseException:
            # Preserve exact handles/owners on every unconfirmed close.
            if not _unclosed_owners:
                _unclosed_owners = (session, decoder, authority, intake, server)
            raise
        finally:
            if watcher is not None:
                watcher.join(1)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expliziter begrenzter nativer Bildtest; synthetische Preise")
    commands = parser.add_subparsers(dest="mode", required=True)
    prepare = commands.add_parser("prepare", help="Nur vorhandene Quellen/Cache prüfen und binden; kein Start")
    prepare.add_argument("--work-root", type=Path, required=True)
    prepare.add_argument("--profile", choices=("bounded-image20s/v1", "live-pilot/v1"), default="bounded-image20s/v1")
    prepare.add_argument("--duration-minutes", type=int, default=480)
    prepare.add_argument("--max-observations", type=int, default=86400)
    start = commands.add_parser("start", help="Eine explizit freigegebene vorbereitete Sitzung starten")
    start.add_argument("--work-root", type=Path, required=True)
    start.add_argument("--prepared-sha256", required=True)
    start.add_argument("--allow-native-run", action="store_true", required=True)
    start.add_argument("--config", type=Path, required=True)
    start.add_argument("--db", type=Path, required=True)
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8765)
    start.add_argument("--assets", type=Path, default=ROOT / "viewer/dist")
    inspect = commands.add_parser("inspect", help="Versiegelte Evidenz nur lesen; kein nativer Start")
    inspect.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.mode == "start" and re.fullmatch(r"[0-9a-f]{64}", args.prepared_sha256) is None:
        parser.error("--prepared-sha256 requires a lowercase SHA-256 digest")
    try:
        if args.mode == "inspect":
            from market.native_protocol import inspect_evidence
            final = inspect_evidence(args.work_root.absolute())
            print(json.dumps(dict(integrity_only=True, native_attestation=False, final=final.to_dict()), sort_keys=True))
            return 0
        if _unclosed_owners:
            raise ValueError("unclosed_owner")
        if args.mode == "start":
            return _start(args)
        _check_platform()
        from market.native_protocol import canonical_sha256
        from market.native_session import NativeConfig, NativeSession, current_protocol
        from market.price_service import SystemClock
        root = args.work_root.absolute()
        _decoder_root(root)
        from market.native_protocol import NativeProfile, scope
        profile = NativeProfile(args.profile, args.duration_minutes, args.max_observations)
        declaration = current_protocol(profile.name, profile.duration_minutes, profile.max_observations) if profile.live else current_protocol()
        session = NativeSession(NativeConfig(str(uuid4()), str(uuid4()), canonical_sha256(declaration), root,
        profile=profile.name, duration_minutes=profile.duration_minutes, max_observations=profile.max_observations), SystemClock())
        prepared = session.prepare()
        print(json.dumps(dict(prepared=prepared.to_dict(), prepared_sha256=canonical_sha256(prepared),
            proof=profile.name, model_observations=profile.max_observations if profile.live else 40,
            wall_seconds=profile.duration_minutes * 60 if profile.live else 900,
            native_released=False), sort_keys=True))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        # Closed errors only: no paths, arbitrary exception text or capabilities.
        from market.native_protocol import FAULTS
        code = getattr(error, "code", None)
        if _unclosed_owners:
            code = "cleanup_failed"
        elif code not in FAULTS:
            code = "prerequisite_failed"
        print("Native service failed: " + code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
