from __future__ import annotations


class CdfError(Exception):
    pass


class NoCandidatesError(CdfError):
    """The walk found nothing to pick from; not a failure, just an empty result."""
