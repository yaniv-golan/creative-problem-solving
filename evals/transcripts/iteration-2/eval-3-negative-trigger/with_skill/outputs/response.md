**Postgres.** For this workload it's the lower-risk choice, and the reasoning is less about consistency guarantees than most people expect.

## Why the consistency argument favors Postgres — but not for the usual reason

Both databases can give you strong consistency. MongoDB has had multi-document ACID transactions since 4.0 (4.2 across shards), majority write concern by default since 5.0, and causally-consistent sessions. The gap isn't capability, it's **defaults and blast radius**:

- In Postgres, a single-node read is strongly consistent because that's the only thing it can be. You have to actively opt *out* (routing reads to an async replica) to get staleness.
- In MongoDB, strong consistency is a per-operation property. `readConcern`/`writeConcern` are set per query, per collection, per driver config, and often per ORM abstraction layer. `readConcern: "linearizable"` exists but is single-document only and expensive enough that nobody leaves it on.

That difference matters at the 18-month mark, not on day one. The failure mode is a new engineer adding a read path with default read concern against a secondary and reintroducing staleness in one endpoint. Postgres makes that mistake require a deliberate connection-string change; Mongo makes it a default.

## Why the data-model argument also favors Postgres

Session storage is a key-value workload: fetch by session ID, write on refresh, delete on logout. You will almost never touch two sessions in one transaction, which means MongoDB's headline feature here — multi-document transactions — is answering a question you're not asking. Meanwhile you *do* get a schema (session records are boringly uniform), real foreign keys to your users table, and `SELECT ... FOR UPDATE` if you ever need session-level locking for things like refresh-token rotation.

## The honest points against Postgres

- **Write churn.** Sessions are update-heavy and short-lived, which is the workload Postgres's MVCC handles worst. Budget for autovacuum tuning, a `fillfactor` below 100 to keep HOT updates working, and avoid indexing the columns you update most (a `last_seen_at` index will defeat HOT updates entirely).
- **Expiry.** MongoDB has TTL indexes; Postgres does not. You'll write a partition-drop job or a batched delete. Partitioning by expiry window and dropping whole partitions is the clean version — cheap, and it sidesteps the vacuum problem above.
- **If you're already a Mongo shop with no Postgres in production**, the operational cost of a second datastore probably outweighs everything above. Set `writeConcern: majority` and `readConcern: majority`, pin session reads to the primary, and you'll be fine. This decision is not close to load-bearing enough to justify adopting a new database.

## The question I'd actually push on

"Strong consistency" for sessions usually decomposes into two concrete requirements, and it's worth confirming which one you mean:

1. **Read-your-writes after auth events** — login, logout, permission change, token revocation must take effect immediately. Both databases do this trivially if you read from the primary.
2. **Immediate global revocation** — a compromised session must die everywhere within milliseconds. This one is *not* a database property. If you put a cache in front of session lookups (and at any real traffic level, you will — session reads happen on every request), your consistency is determined by your invalidation design, not your storage engine.

So: the consistency risk in this system is overwhelmingly likely to enter through the cache or read-replica you add for latency six months from now, not through the choice you're making today. If you pick Postgres and then put an un-invalidated 30-second cache in front of it, you have a MongoDB-with-default-read-concern system with extra steps.

**Recommendation:** Postgres, partitioned by expiry, session reads from the primary, no read replicas in the session path. Write down the revocation latency you're willing to tolerate *now* — that number, not the database, is the thing that will constrain you later.
