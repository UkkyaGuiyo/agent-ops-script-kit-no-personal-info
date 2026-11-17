# Architecture / 役割分担

**Script:** deterministic, repeatable checks with typed results and explicit failure.
**AI assistant:** interprets and explains, but must verify its own tool access and never claim unexecuted tests.
**Human:** configures scope and approves consequential actions.

Pilot pipeline: JSON config → local metadata scan → JSON on stdout; exit 0 on complete success or 2 on error. No background scheduler, remote access, or report file.

Shared intake with distinct pending/delivered/failed states is a **planned future subsystem**, not included as working software yet. Failure to fetch must never become “nothing new.”
