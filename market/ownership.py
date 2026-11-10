"""Process-lifetime ownership using stdlib operating-system advisory locks."""

import os
from pathlib import Path


class DatabaseOwnership:
    def __init__(self, database: Path):
        self._file = None
        handle = open(database.with_name(database.name + ".owner.lock"), "a+b")
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                # locking() covers bytes from the current offset, including beyond EOF.
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                # flock() operates on the descriptor; nonblocking exclusive ownership.
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            handle.close()
            raise
        self._file = handle

    def close(self):
        handle = self._file
        if handle is None:
            return
        self._file = None
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
