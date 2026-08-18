MODE: none

No skill was invoked. This is a standard technical architecture question (Postgres vs MongoDB for session storage with a strong-consistency requirement) answered directly from domain knowledge. No available skill matched — the catalog covered unrelated domains (document formats, business-analysis workflows, and skill authoring), none of which apply to a database selection question.

No tools were needed beyond writing the required output files: no codebase to search, no files provided by the user, no web research required (the tradeoffs involved — MongoDB's opt-in writeConcern/readConcern majority vs Postgres's default ACID, TTL index reaper granularity, JSONB indexing — are stable and well within training knowledge).

Substantive judgment in the answer:
- Answered the question as asked (Postgres) rather than deflecting.
- Named the honest counter-cases where MongoDB would win, rather than presenting a one-sided case.
- Raised the reframe the user did not ask for but likely needs: sessions are a high-QPS, short-TTL workload that often belongs in Redis, with Postgres as the system of record. Framed as a question to consider, not a refusal to answer the original question.
- Recommended Postgres-only as the pragmatic day-one start, noting the asymmetry: adding Redis later is non-breaking, migrating off Mongo for transactional guarantees is not.
- Added security/operational notes (hash stored tokens, index expires_at and filter at read time, revocation story, sliding vs absolute expiry) since they materially affect the design more than the DB pick does.
