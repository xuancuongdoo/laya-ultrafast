# wikipedia demo

Search Wikipedia for "Ada Lovelace" and open the article. Proves the
backend contract: same loop as the flight demo, different site, swappable
backend.

```bash
uv run python demos/wikipedia/run.py            # mock backend, fully offline
uv run python demos/wikipedia/run.py --laya     # real Laya backend on :8770
```

The mock path runs search → article end to end. The `--laya` path
exercises the same loop against the real classifier but currently stops
at an immediate `DONE` (known operation-head limit on content-heavy
pages, see repo README) — the verify step reports this honestly instead
of passing.

Independent verification (not just a `DONE` choice): final URL is exactly
`.../wiki/Ada_Lovelace`, the article body carries its markers, and the
title is exactly `Ada Lovelace - Wikipedia`.
