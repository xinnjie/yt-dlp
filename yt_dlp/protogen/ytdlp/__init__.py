"""Namespace package for bundled yt-dlp protocol buffer stubs."""

from __future__ import annotations

import sys as _sys

# The generated files still import "ytdlp.<...>", so register this package
# under that legacy top-level name for backward compatibility.
_sys.modules.setdefault('ytdlp', _sys.modules[__name__])

__all__ = []
