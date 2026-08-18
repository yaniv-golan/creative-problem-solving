**Postgres** — for this workload it's the lower-risk choice, and it isn't close.

## Why

**1. Consistency is the default, not a per-call decision.**
MongoDB *can* be strongly consistent — replica set with `w: "majority"`, `readConcern: "majority"` (or `"linearizable"`), and multi-document transactions since 4.0/4.2. The old "Mongo loses data" trope is outdated. But it's opt-in per operation. The default read concern is still `local`, and one service, one ORM config, or one analytics job that quietly sets `readPreference: secondary` reintroduces stale reads — exactly the failure mode you're trying to design out. Consistency you have to maintain by convention erodes. In Postgres you get ACID on a single primary for free, with `SERIALIZABLE` available per-transaction when you want it.

**2. Your hardest requirement is probably atomic token rotation, and that's a one-liner in SQL.**
Refresh-token rotation, single-use nonces, and "revoke all sessions on password change" all need an atomic compare-and-swap. In Postgres:

```sql
UPDATE sessions SET state = 'rotated', successor = $new
WHERE id = $id AND state = 'active'
RETURNING *;
```

Zero rows back means someone beat you to it — replay detected, in one statement, under the default isolation level. Mongo can do this too (`findOneAndUpdate` is atomic on a single document), but the moment revocation spans multiple documents you're in a transaction, and Mongo transactions on sharded clusters carry real cost and constraints.

**3. Session data is relational and its schema is fixed.**
`session_id, user_id, device, ip, issued_at, expires_at, revoked_at`. You will want to list all sessions for a user, revoke by device, join against users for an audit trail. The schema flexibility that is Mongo's main advantage buys you nothing on a table whose shape you already know.

**4. Mongo's real edge — horizontal write sharding — is scale you likely don't have.**
A single Postgres primary handles tens of thousands of session writes/sec with sane indexing. Reach for sharding when you've measured that you need it.

## The one case where I'd say MongoDB

If your team already runs Mongo in production and has never operated Postgres. A correctly configured Mongo replica set beats a badly run Postgres, and operational familiarity beats theoretical fit. Mongo also gives you TTL indexes for free — expired sessions get swept automatically (within ~60s), whereas Postgres needs you to build that.

## Postgres gotchas for sessions, and the fixes

- **Churn and bloat.** If you update `last_seen_at` on every request, every request creates a dead tuple. Autovacuum will struggle. Fix: throttle that write to once per N minutes, keep indexes minimal, and set `fillfactor` to ~80 so HOT updates can happen in-page.
- **Expiry.** Don't `DELETE FROM sessions WHERE expires_at < now()` on a hot table. Partition by expiry window and `DROP PARTITION` — it's O(1) and leaves no bloat.
- **Read replicas will undo your work.** If you scale session validation onto async replicas, you've reinvented the stale reads you rejected Mongo's defaults for. Validation reads go to the primary, or you use `synchronous_commit = remote_apply`.
- **Don't use `UNLOGGED` tables** as a performance shortcut here — they don't survive a crash, and a crash that logs out every user is an outage.
- **Connection count.** Put pgbouncer in transaction mode in front of it before you have 500 app instances.

## Two things worth pinning down before you commit

**What does "strong consistency" mean here, concretely?** Read-your-writes after login? Immediate global revocation? Exactly-once refresh rotation? They have different costs, and only the last one genuinely constrains the choice. Write down the specific guarantee — it'll sharpen the design more than the database pick will.

**Do you need a database in the write path at all?** The common architecture is short-lived signed access tokens (60–300s, validated with no DB read) plus a durable store for refresh tokens and a revocation list. That cuts session-store QPS by one to two orders of magnitude and makes the Postgres-vs-Mongo question nearly irrelevant. If you add a Redis cache in front, treat it as advisory only — revocation must invalidate it synchronously, or your "strong consistency" is decorative.

**Bottom line:** Postgres, partitioned by expiry, validation reads on the primary, short-lived access tokens in front of it.
