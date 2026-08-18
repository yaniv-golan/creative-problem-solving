MODE: none

## What a human should review

**Approach taken.** Treated this as a diagnosis problem rather than a research problem. Three web searches were run for supporting evidence, but the substance of the answer comes from reasoning about the structure of the 18-month pattern, not from the sources.

**The main analytical move.** I pushed back on the user's premise that "it's not the money." Their benchmarking almost certainly compares year-one offers, while big companies compete on years 2–4 via annual RSU refreshers. A company that genuinely matches on day one can be 20–40% behind by year three without realizing it. This is presented as the cheapest hypothesis to rule out, not as a claim that comp definitely is the cause. Worth checking whether this framing lands or feels like it dodges what they asked.

**Unverified assumptions embedded in the answer.** The user gave no company size, stage, funding status, or team structure. I assumed:
- A venture-backed startup somewhere between roughly 40 and 150 people
- Standard 4-year/1-year-cliff equity, illiquid
- Competitors are large public tech companies with liquid RSUs and annual refresh cycles
- Enough departures to constitute a pattern (implied by "keep losing")

If any of these are wrong — e.g. a much larger company, a bootstrapped one, or only two or three departures total — parts of the advice shift materially. In particular, with fewer than ~5 departures the "18-month mark" may be coincidence rather than signal, and the manager-concentration check becomes underpowered.

**Source quality caveat.** The retention statistics available on this topic (e.g. "68% cite limited growth opportunities," "5x more likely to leave with a poor manager") come almost entirely from recruiting-vendor content marketing with thin or undisclosed methodology. I deliberately did not build the argument on these numbers, and added an explicit note at the end of the response warning against quoting them to a board. The directional claim (growth and management outrank pay once pay is competitive) is well-supported and consistent with established motivation research; the precise figures are not.

**Recommendations with real cost or risk attached.**
- *Secondary liquidity for employees past 24 months* requires board and investor buy-in and has cap-table and 409A implications. Presented as high-leverage, which I believe, but it is not a decision the reader can make unilaterally.
- *Sponsoring external visibility* (talks, open source) genuinely does increase employees' marketability. I flagged it as counterintuitive but did not dwell on the downside risk.
- *Advice against counteroffers* is stated firmly. It reflects the general pattern but there are legitimate exceptions for a genuinely irreplaceable person during a critical window.

**Deliberately omitted.** Did not cover legal or contractual retention mechanisms (non-competes, clawbacks, retention bonuses tied to milestones). These are jurisdiction-dependent, increasingly unenforceable in the US, and generally counterproductive for senior ICs — but a reader might expect them mentioned.

**Tooling note.** `mcp__workspace__bash` could not create the output directory (permission denied on `/Users` — the workspace shell is an isolated Linux environment and the outputs path is not mounted there). Files were written with the `Write` tool instead, which worked. Recorded as 1 error in metrics.json.
