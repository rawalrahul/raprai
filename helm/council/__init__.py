"""helm/council — AI Council debate module.

The names below load on first use, so `helm.council.runner` (which the MCP server
uses to run an AI) can be imported without the web server's packages.
"""

__all__ = ["make_council", "make_council_message", "build_transcript", "run_council"]


def __getattr__(name):
    if name in ("make_council", "make_council_message", "build_transcript"):
        from . import models
        return getattr(models, name)
    if name == "run_council":
        from .executor import run_council
        return run_council
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
