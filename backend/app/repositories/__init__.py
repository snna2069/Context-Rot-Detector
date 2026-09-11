"""Package marker for the persistence (repository) layer.

Repositories only perform direct database reads/writes. Business rules such
as duplicate detection and ordering validation live in `app.services`.
"""
