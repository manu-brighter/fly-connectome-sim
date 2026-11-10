"""Run the separate synthetic local test price board; never starts a simulator."""

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from market.fixtures import load_config
from market.local_server import _load_assets, _validate_bind, create_server
from market.price_service import MarketError, SystemClock, open_authority


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--assets", type=Path, default=Path("viewer/dist"))
    args = parser.parse_args(argv)
    authority = None
    server = None
    try:
        _validate_bind(args.host, args.port)
        _load_assets(args.assets)
        config = load_config(args.config)
        clock = SystemClock()
        args.db.parent.mkdir(parents=True, exist_ok=True)
        authority = open_authority(config, args.db, clock)
        server = create_server(authority, args.host, args.port, args.assets)
        print("Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten", flush=True)
        print("Clock: " + json.dumps(clock.describe(), sort_keys=True), flush=True)
        print(server.operator_url, flush=True)
        print(server.view_url, flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, MarketError) as error:
        # Never print arbitrary exception payloads or opening capabilities on failure.
        code = error.code if isinstance(error, MarketError) else "invalid_startup"
        print("Market service failed: " + code, file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.server_close()
        elif authority is not None:
            authority.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
