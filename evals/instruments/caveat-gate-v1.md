# Frozen caveat gate v1

Frozen 2026-08-22. Guards against an atomiser that strips qualifying language unevenly between
arms — a failure that actually occurred and was caught at 0.21 against a 0.20 threshold.

## Formula

For each arm:
  source_density = hedge_markers_in_source_answers / source_words * 1000
  item_density   = hedge_markers_in_atomised_items  / item_words   * 1000
  retention      = item_density / source_density

Markers: `evals/HEDGE-MARKERS.txt`, sha256 a6c96ecbc0050c61d0c81a26b42e55b4701792e3b791b29a2f12212837b56e32
Matching: case-insensitive, whole-word, the file's alternation compiled as `\b(<alternation>)\b`.

## Two conditions — BOTH must hold

1. **Relative:** |retention(arm A) - retention(arm B)| <= 0.20
2. **Absolute floor:** retention >= 0.70 in EVERY arm

Condition 2 was absent from the first version of this gate and is the reason it exists as a
file. The relative test alone PASSES on 0% vs 0% retention — an atomiser that destroys all
qualifying language in both arms satisfies "differs by at most 20 points" perfectly while having
removed the thing the gate protects. Symmetric destruction is not fairness.

## On failure

One re-atomisation is permitted, and only for a caveat-gate failure. A second failure abandons
the primary endpoint rather than trying a third atomiser.
