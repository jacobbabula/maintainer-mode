# Contributing

Keep changes focused on the evidence-first contribution contract.

1. Open or reference an issue that explains the behavior and claim boundary.
2. Add a regression test before changing a deterministic gate or receipt field.
3. Preserve zero runtime dependencies unless the tradeoff is discussed first.
4. Run `python -m unittest discover -s tests -v`.
5. Update the schema documentation when serialized output changes.

Do not weaken a safety boundary for a smoother demo. Unknown policy must remain visible, candidate duplicates must remain reviewable, and local receipts must never be described as hosted CI or maintainer approval.
