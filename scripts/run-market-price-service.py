"""Run the separate synthetic local test price board; never starts a simulator."""

import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from market.fixtures import load_config
from market.local_server import _load_assets, _validate_bind, create_server
from market.price_service import MarketError, SystemClock, open_authority


# A failed application cleanup must retain the exact owner until confirmed close.
_unclosed_image_owner = None


def main(argv: list[str] | None = None) -> int:
    global _unclosed_image_owner
    parser = argparse.ArgumentParser(description="Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--assets", type=Path, default=Path("viewer/dist"))
    parser.add_argument("--image-work-root", type=Path)
    args = parser.parse_args(argv)
    authority = None
    server = None
    decoder = None
    intake = None
    result = 0
    errors = (OSError, ValueError, MarketError)
    try:
        if _unclosed_image_owner is not None:
            raise MarketError("cleanup_failed")
        _validate_bind(args.host, args.port)
        _load_assets(args.assets, images_enabled=args.image_work_root is not None)
        if args.image_work_root is not None:
            try:
                from market.image_admission import AdmissionController
                from market.image_decode import DecodeError, ImageDecoder
                from market.image_intake import ImageIntake, IntakeError
            except Exception:
                raise MarketError("invalid_startup") from None
            errors += (DecodeError, IntakeError)
            if sys.platform != "win32" or sys.version_info[:3] != (3, 12, 14):
                raise DecodeError("unsupported_platform")
            root = args.image_work_root.absolute()
            tools = Path(__file__).absolute().parents[1] / ".tools"
            if root == tools or not root.is_relative_to(tools):
                raise DecodeError("ownership")
        config = load_config(args.config)
        clock = SystemClock()
        if args.image_work_root is not None:
            # D2 requires an existing trusted root; never create an unchecked path.
            decoder = ImageDecoder(args.image_work_root, clock)
            _unclosed_image_owner = decoder
            intake = ImageIntake(AdmissionController(str(uuid4()), clock), decoder, clock)
            _unclosed_image_owner = intake
        args.db.parent.mkdir(parents=True, exist_ok=True)
        authority = open_authority(config, args.db, clock)
        server = create_server(authority, args.host, args.port, args.assets, image_intake=intake)
        print("Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten", flush=True)
        print("Clock: " + json.dumps(clock.describe(), sort_keys=True), flush=True)
        print(server.operator_url, flush=True)
        print(server.view_url, flush=True)
        if intake is not None:
            print(server.guest_url, flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except errors as error:
        # Never print arbitrary exception payloads or opening capabilities on failure.
        code = "invalid_startup" if isinstance(error, (OSError, ValueError)) else error.code
        print("Market service failed: " + code, file=sys.stderr)
        result = 1
    finally:
        try:
            if server is not None:
                server.server_close()
            else:
                try:
                    if authority is not None:
                        authority.close()
                finally:
                    if intake is not None:
                        intake.begin_stop()
                        intake.finish_close()
                    elif decoder is not None:
                        decoder.close()
            if decoder is not None:
                _unclosed_image_owner = None
        except errors:
            print("Market service failed: cleanup_failed", file=sys.stderr)
            result = 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
