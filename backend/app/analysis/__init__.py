"""Context Rot analysis engine.

This package contains the deterministic detection engine described in
Phase 4: a set of independently-testable, composable detectors that each
measure one specific signal (repetition, contradiction, staleness, etc.),
plus an engine that runs them and aggregates their output into a
`ContextHealthScore`.

Nothing in this package talks to the database directly -- detectors
operate over the plain-data `SessionContext` in `app.analysis.context`, so
they can be unit-tested without a database and reused by any future
transport (API, batch job, CLI).
"""
