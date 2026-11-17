# Next pilot candidate: ledger checker / 台帳係
**Status:** DESIGN ONLY, not implemented. Owner's existing private ledger schema has not been inspected here.

## Purpose and safety boundary
Compare two **synthetic** ledgers and report missing entries, extra entries, and conflicting values without modifying either source. No accounts, network, uploads, deletion, automated correction, or scheduling. Failure to parse either ledger returns ERROR and produces no misleading complete comparison.

## First design stage
1. P1: have the environment owner document the **generalized** ledger fields, comparison rules, valid identifiers, duplicate handling, and known failure cases. Do not supply actual private rows or private code.
2. E.L.I.S. will propose a minimal public JSON schema with explicitly typed fields and clear error handling. Verify it with the tester before implementation.
3. Implement independent parser/comparator and synthetic fixtures only.
4. Add technical specification, beginner explanation, HowTo, AI setup and explanation checks, unit/negative tests, and report format.
5. Validate fresh clone, invariant source files, malformed/inconsistent/duplicate input, missing entries, and a clean-room explanation before considering VERIFIED.

## Provisional acceptance scenarios
- Equal ledgers → complete comparison with no discrepancies.
- Missing/excess entry → report exact synthetic ID.
- Same ID but different values → explicit conflict without silent correction.
- Duplicate IDs, unexpected types, malformed file → fail closed, no successful result.
- Verify results irrespective of row order; no hidden changes to source files.
- Public docs must not show actual people, email addresses, account identifiers, or non-synthetic records.

**No code may be published as “verified” solely on this plan.**
