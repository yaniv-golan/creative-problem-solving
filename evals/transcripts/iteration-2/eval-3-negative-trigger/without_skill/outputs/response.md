**Pick Postgres.** For session storage with a strong-consistency requirement, it's the lower-risk default, and the tie-breakers below only widen the gap.

## Why Postgres wins on your stated requirement

**Consistency model.** Postgres is single-writer per shard with real ACID transactions and serializable isolation available out of the box. You get read-your-writes for free, no configuration required. MongoDB *can* give you strong consistency — `writeConcern: majority` plus `readConcern: majority`/`linearizable`, and multi-document transactions since 4.0 — but it's opt-in per operation. Every code path has to remember to ask for it. Defaults in MongoDB favor availability and latency; defaults in Postgres favor correctness. When correctness is the requirement, you want it to be the default, not a flag someone can forget in a hotfix.

**Data shape fits.** Sessions are small, uniform, keyed records: session ID, user ID, issued/expiry timestamps, maybe a small claims blob. That's a table with an index, not a document store. If you need flexible per-session metadata, Postgres `JSONB` handles it with GIN indexing — you get schemaless fields without giving up transactions.

**Expiry is easy either way, but Postgres is more controllable.** Mongo's TTL indexes are convenient but the reaper runs about every 60 seconds, so deletion is approximate. In Postgres you either filter on `expires_at > now()` at read time (correct immediately) plus a periodic cleanup job, or use partitioning by expiry window and drop partitions. Either gives you exact semantics at read time.

**Operational simplicity.** Strongly consistent Mongo means a replica set, correct write/read concerns everywhere, and understanding rollback windows during elections. A single Postgres primary with a sync or async replica is a well-understood setup that every ops person and every managed provider (RDS, Cloud SQL, Neon, Supabase) supports natively.

## Where MongoDB would actually be the better call

Be honest about the cases — if any of these describe you, revisit:

- **You need multi-region active-active writes.** Neither is great here, but Mongo's sharding and zone-based writes give you more built-in machinery than vanilla Postgres. Though for sessions, this usually pushes you toward a different answer entirely (see below).
- **Session documents are large, deeply nested, and highly variable per client.** Rare for sessions, but possible if you're stuffing a lot of app state in there.
- **Your team already runs Mongo at scale and has no Postgres expertise.** Operational familiarity is a real and underrated factor. A well-run Mongo beats a badly-run Postgres.

## The question worth asking before you commit

**Do sessions actually belong in your primary datastore at all?** Session lookup happens on essentially every authenticated request. That's a very high-QPS, low-latency, short-TTL workload — different in character from the rest of your data. The common production answer is Redis (or Valkey / ElastiCache / Memorystore) as the session store, with Postgres as the system of record for users and any session events you need durably audited.

Redis gets you sub-millisecond reads, native TTL expiry, and — importantly for your requirement — a single-writer model that gives strong consistency on a primary. The usual objection is durability, but you can run AOF with `appendfsync everysec`, and for sessions the failure mode of losing a few seconds of session writes is "some users re-login," not data corruption.

So the shape I'd actually recommend:

- **Redis** — hot session lookup, TTL-driven expiry
- **Postgres** — users, credentials, refresh tokens, session audit trail, anything transactional

If you'd rather not run two systems on day one (very reasonable for a new service), **start with Postgres alone.** It'll comfortably handle session load well past the point most services ever reach, and adding Redis as a cache layer later is a non-breaking change. Starting with Mongo and later needing real transactional guarantees is a much more painful migration.

## Things to nail down regardless

A few decisions that matter more than the DB choice:

1. **Session tokens must be opaque and random** (≥128 bits from a CSRNG), and store a hash of the token, not the token itself. A DB leak shouldn't be a session-hijacking event.
2. **Index on `expires_at`** and always filter on it at read time — never trust the reaper alone.
3. **Decide your revocation story now.** "Log out all devices," password-change invalidation, and admin force-logout are much easier with server-side sessions than with stateless JWTs — which is a good argument for the DB-backed approach you're already taking.
4. **Sliding vs. absolute expiry.** Sliding expiry means a write on every request, which changes your load profile a lot. If you go sliding, consider only refreshing when the session is past, say, half its TTL.

## Bottom line

Postgres over MongoDB, clearly, given strong consistency is the stated constraint. But give Redis-plus-Postgres a serious look before you build — for this specific workload it's the shape most teams converge on, and it's easy to grow into from a Postgres-only start.
