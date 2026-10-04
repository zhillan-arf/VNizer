"""Stop child processes when their Linux parent exits unexpectedly."""

import ctypes
import os
import signal
import sys


def terminate_with_parent(expected):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot set the child termination signal.")
    if os.getppid() != expected:
        os.kill(os.getpid(), signal.SIGKILL)


if __name__ == "__main__":
    terminate_with_parent(int(sys.argv[1]))
    os.execvp(sys.argv[2], sys.argv[2:])
