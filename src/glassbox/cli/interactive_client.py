"""Compatibility facade for interactive terminal session clients."""

from glassbox.cli.interactive_client_daemon import DaemonInteractiveSessionClient
from glassbox.cli.interactive_client_local import LocalInteractiveSessionClient
from glassbox.cli.interactive_client_models import InteractiveClientError
from glassbox.cli.interactive_client_models import InteractiveClientErrorKind
from glassbox.cli.interactive_client_models import InteractiveSessionClient
from glassbox.cli.interactive_client_models import InteractiveSessionSnapshot
from glassbox.cli.interactive_client_models import ReviewLoopAction
from glassbox.cli.interactive_client_models import ReviewLoopActionResult
from glassbox.cli.interactive_client_sse import interactive_snapshot_from_response
from glassbox.cli.interactive_client_sse import iter_sse_events

__all__ = [
    "DaemonInteractiveSessionClient",
    "InteractiveClientError",
    "InteractiveClientErrorKind",
    "InteractiveSessionClient",
    "InteractiveSessionSnapshot",
    "LocalInteractiveSessionClient",
    "ReviewLoopAction",
    "ReviewLoopActionResult",
    "interactive_snapshot_from_response",
    "iter_sse_events",
]
