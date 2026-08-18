**Postgres.** For a session store with a strong-consistency requirement, it's the lower-risk default and the burden of proof should be on anyone arguing for MongoDB.

## Why

**Consistency is the default, not a configuration.** Postgres gives you serializable-capable transactions on a single primary with no tuning. MongoDB *can* be strongly consistent — `writeConcern: majority` + `readConcern: majority` (or `linearizable`), and multi-document transactions have existed since 4.0/4.2 — but it's opt-in per operation. That means every code path, every driver default, every new engineer is a chance to silently read stale data from a secondary. A consistency guarantee you have to remember to ask for is a guarantee you will eventually forget to ask for.

**Session data is relational and tiny.** A session is a flat row: `session_id, user_id, created_at, expires_at, ip, user_agent, revoked_at`, maybe a small JSON blob of claims. There's no document hierarchy to model, no schema flexibility you need. MongoDB's actual advantages — flexible schemas, nested documents, horizontal sharding — don't apply here.

**The operations you'll actually want are relational.** "Revoke all sessions for this user," "log everyone out on password change," "show me a user's active devices," "expire everything issued before the key rotation." Those are indexed queries and joins against your users table, which is almost certainly already in Postgres.

**One fewer datastore.** If your primary DB is already Postgres, adding Mongo for sessions buys you a second backup story, a second failover runbook, a second on-call knowledge domain, and cross-store consistency problems at user-deletion time. That cost is real and recurring; the benefit here is close to zero.

## The honest case for MongoDB

It isn't zero, and it's worth saying so rather than strawmanning it:

- Your team already runs Mongo at scale and has no Postgres operational experience. Operational familiarity beats theoretical fit more often than architecture diagrams admit.
- You need write throughput past what a single Postgres primary handles and you want sharding built in rather than bolted on. This is a real threshold, but it's high — a well-indexed Postgres box handles session write rates for a very large user base.
- TTL indexes give you automatic session expiry for free. In Postgres you write a cron job or partition by expiry date. Minor, but genuinely nicer in Mongo.

None of these is "strong consistency," which is the criterion you named — and on that criterion Postgres wins on defaults and operational safety, not on raw capability.

## Two things to check before you commit

**1. Do you need durable session storage at all?** If sessions are short-lived and re-authenticatable, Redis with AOF persistence is a better fit than either: sub-millisecond reads, native TTL, and the durability tradeoff is acceptable because a lost session just means a re-login. If sessions carry authorization state or need an audit trail, ignore this and use Postgres. If you're storing sessions to avoid a token round-trip, stateless signed JWTs plus a small Postgres revocation list is a third shape worth 10 minutes of thought — though revocation lists reintroduce most of the state you were avoiding.

**2. What does "strong consistency" mean in your case?** Read-your-own-writes after login is easy and both databases handle it. Linearizable reads across regions during a network partition is a much harder requirement, and if that's what you mean, neither single-primary Postgres nor Mongo is really the answer — you're looking at CockroachDB, Spanner, or accepting regional session affinity. Worth pinning down which one you have.

## Recommendation

Postgres, with a `sessions` table, a partial index on `(user_id) WHERE revoked_at IS NULL`, and either a partition-by-expiry scheme or a periodic cleanup job. Revisit only if you hit a write-throughput ceiling you've actually measured.
