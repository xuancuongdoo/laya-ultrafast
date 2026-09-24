# Hunting contract (downstream loop-wiring consumer)

Offline static audit tools. Stdlib only, no network, no browser, no paid
APIs. Findings and maps are JSON-serializable. The secrets playbook
reports PATHS ONLY — it never reads or prints file contents or values.

## Import paths

- `security.reconnaissance.phase.recon`, `security.reconnaissance.phase.save_map`
- `security.reconnaissance.CoverageLedger` (also at `security.reconnaissance.ledger`)
- `security.hunting.PLAYBOOKS`, `security.hunting.run_all`, `security.hunting.critique`
- `security.hunting.playbooks.secrets.run`, `.prompt_injection.run`, `.done_safety.run`

## Signatures

- `recon(target_root, ledger=None) -> dict` — walk `*.py` (skips `.venv`,
  `__pycache__`, `.git`, `node_modules`, `dist`, `recordings`); marks
  `(str(target_root), recon)` verified when a ledger is given.
- `save_map(map, path) -> Path` — indented JSON, creates parents.
- Each playbook: `run(target_root) -> list[dict]`.
- `run_all(target_root) -> list[dict]` — secrets + prompt_injection +
  done_safety in registry order.
- `critique(target, ledger, findings) -> dict`.

## Shapes

Map: `{target, root, modules: [{path, package, lines}], packages: [...],
entry_points: [...], tests: [...], generated_at}`. `path`/`tests` are
posix paths relative to the root. `package` is the dotted dir holding
`__init__.py` (else null). `packages` includes namespace parents (e.g.
`backends`). `entry_points` holds `name = target` console scripts, then
`demos/*/run.py`, then `ultrafast/demo.py` when present.

Finding: `{id, target, area, severity, detail}`. `area` mirrors `target`
so every finding passes `security.records.chain.verify_finding` and
appends to a records chain. `severity` is one of
info/low/medium/high/critical. Id prefixes: `SEC-`, `PI-`, `DS-`.

Critique: `{target, coverage: float, uncovered: [[area, phase], ...],
critical: [ids], severities: {sev: count}, notes: [...]}`.

## Usage

```python
from security.hunting import critique, run_all
from security.reconnaissance import CoverageLedger
from security.reconnaissance.phase import recon, save_map

ledger = CoverageLedger()
arch = recon(".", ledger)
save_map(arch, "evidence/arch-map.json")
findings = run_all(".")
verdict = critique(".", ledger, findings)
```
