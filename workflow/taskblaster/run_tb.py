"""Windows-compatible runner for TaskBlaster workflows.

Works around the ``signal.SIGCONT`` issue on Windows by monkey-patching
the signal handler setup before invoking the TaskBlaster worker.
"""

import signal
import sys


def _patched_setup_kill_signal_handlers():
    """Windows-safe replacement: skip signals that don't exist."""
    from taskblaster.cli.main import TaskBlasterInterrupt

    def raise_signal(sig, frame):
        raise TaskBlasterInterrupt(f"Interrupted by signal {sig}.")

    for sig_name in ["SIGCONT", "SIGTERM"]:
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, raise_signal)


# Apply the patch before importing the CLI
import taskblaster.cli.main as _cli_main  # noqa: E402

_cli_main.setup_kill_signal_handlers = _patched_setup_kill_signal_handlers

# Now delegate to the real `tb` CLI entry point
from taskblaster.cli.main import tb  # noqa: E402

if __name__ == "__main__":
    sys.exit(tb())
