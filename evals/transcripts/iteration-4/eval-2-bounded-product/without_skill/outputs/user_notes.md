MODE: none

## What I did
Answered the question directly from product/growth reasoning. No skill was invoked, no web research, no subagents. The response is saved verbatim in `response.md`.

## Approach taken
Reframed the problem before listing ideas: the two fixes already tried (shorter form, progress bar) both assume a friction cause, so the answer leads with a diagnostic split of the 60% into four failure modes (never received / never opened / opened but abandoned / never requested), then organizes ideas by which failure mode they address, then gives a sequenced plan.

## Things a human should check
- **No access to the actual product or analytics.** Everything is generic best practice; none of it is validated against their funnel. The diagnostic section is the load-bearing part — the idea list is a menu, not a recommendation.
- **Numbers used as rules of thumb** (median time-to-verify under ~60s, 20s provider failover, 30min/24h resume emails) are conventional practice, not cited benchmarks. Treat as starting points to tune, not targets.
- **The "defer verification" recommendation has real security/abuse/compliance implications** that I could not assess. If they're in fintech, healthcare, or anywhere with KYC/regulatory verification requirements, that recommendation may be a non-starter. The response flags this and asks why they verify, but a human should sanity-check it against their domain.
- **The bot/fraud point** — that some of the 60% may be non-human — is speculative but worth them checking before optimizing.
- The response ends with a clarifying question rather than assuming. If a single-shot answer with no follow-up was wanted, that ending may need trimming.
