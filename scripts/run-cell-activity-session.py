"""Capture one bounded ordinary session with passive, source-bound cell counts."""

import argparse
import json
from pathlib import Path

from fly_connectome_sim.experiment.cell_activity import run_cell_activity_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime-directory", "playlist", "proposal", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_cell_activity_session(args.output, playlist_path=args.playlist,
                                              proposal_path=args.proposal, runtime_directory=args.runtime_directory)))


if __name__ == "__main__":
    main()
