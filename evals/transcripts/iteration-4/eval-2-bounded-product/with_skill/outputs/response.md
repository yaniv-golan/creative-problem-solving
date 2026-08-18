I'm reading "account verification" as a confirmation code or link sent to email/SMS. If it's really ID-document upload or bank linking, tell me — options 1 and 2 largely stop applying and 4 becomes most of the answer.

**First, which 60% is this?** Three buckets that share no fixes: (a) never got the message — deliverability, typo'd address, carrier filtering; (b) got it, didn't finish — mechanics or trust; (c) finished later on another device and your session-scoped funnel logged them as lost. Delivery logs plus a 7-day cohort view separates all three in an afternoon. Split by acquisition source too: if the drop concentrates in one paid channel, 60% may be correct sorting rather than a broken step, and none of the below applies.

### Stop checking most people, and price what leaks through
The gate is an insurance premium charged to every user against a claim you may never have measured. Work out what an unverified account actually costs over 90 days — support load, spam, free-tier compute, refund fraud — and compare it to the revenue sitting in the 60%. If the premium exceeds the claim, let almost everyone through and screen against known-bad after the fact, so cost scales with abuse volume instead of user volume.
- What has to be true: abuse cost per bad account is knowable and bounded.
- Failure mode: a regulator or platform partner makes this not your decision to make.
- Who runs it: finance/analytics, not engineering. One person, one week, nothing shipped.

### Deliver the thing before there's an account to verify
Instead of making the proof cheaper, remove the object that needs proving: let a first-timer get one real result from a stateless, link-addressed session with no login. The account becomes an upgrade they request when they want the result to persist, be shared, or be paid for — and at that point they have their own reason to hand you a channel. The check stops being an admission ticket and becomes a save button.
- What has to be true: at least one unit of your value survives having no stored state.
- Failure mode: two code paths, and attribution gets worse before it gets better.
- Who runs it: PM plus backend. This is a product decision, not a growth experiment.

### Split one check into the three jobs it's actually doing
Most "verify your account" screens fuse three unrelated requirements: a way to reach the person again, assurance they aren't one of ten thousand copies, and sometimes a legal identity. Fused, everyone pays the highest of the three prices at the earliest possible moment. Separated: reachability can be optional at signup, uniqueness gets checked at whichever action makes abuse profitable, legal identity only where money or regulation demands it. Only the third is ever a hard law — the rest is convention.
- What has to be true: you can name which of the three you need, and when.
- Failure mode: three scattered asks can annoy more than one big ask if you don't retire the ones you don't need.
- Who runs it: whoever owns abuse/risk with the product owner. Biggest build here.

### Prove it from what they're already carrying
People arrive holding several things that already demonstrate control of an identity: a device you can bind a passkey to, a live OAuth session, an employer domain with real mail records, a payment instrument already on file. Treat verification as background classification over those signals rather than an interactive event, and challenge only the residual who fail. The challenge stops being a step everyone walks through and becomes an exception a minority sees.
- What has to be true: enough traffic carries at least one usable signal to move the number.
- Failure mode: silent checks are hard to debug and can fail closed on exactly the users you want most.
- Who runs it: a buy rather than a build, unless you already have a risk engineer.

### Delete the handoff, not the form
The step asks someone to leave your surface, find a message in another app, carry a value back, and land in a session that may no longer exist. Every one of those is a place to lose them and none of them is the form — which is why shortening it didn't help. Three separate removals: have the original tab poll server-side and advance by itself so nothing is transcribed; accept a *reply* on the channel as the proof, since replying is a far cheaper motor action than copying; and put the first genuinely useful output inside the message, so opening it is something they wanted to do anyway.
- What has to be true: your drop is bucket (b) — the message arrived.
- Failure mode: reply-as-proof needs inbound handling and gets messy with shared or forwarded inboxes.
- Who runs it: front-end plus auth. Cheapest item here, one sprint.

### Treat every stall as an inbound lead, for two weeks
Put someone on a rota watching stalls in near-real-time and have them reach out within a minute or two on whichever channel demonstrably works. It doesn't scale and isn't meant to — it buys the diagnosis and the recovery at once, because what people say in that first minute is what you cannot get from a survey the next day. Whatever they tell you is the spec for the permanent fix.
- What has to be true: enough volume to learn from, not so much that one person drowns.
- Failure mode: it works, and quietly becomes a permanent headcount cost.
- Who runs it: support or growth, explicitly time-boxed.

**Cut, and why**
- Small refundable charge as a liveness signal — raises the ask at the moment they're already balking. Only viable if a card was coming anyway.
- 72-hour expiry on unverified accounts — nice loss-frame, but at this step they haven't built anything to lose.
- Users vouching for each other — works in dense teams, nowhere else.
- Better copy, trust badges, reminder drips — same family as the progress bar. You've done that.

**What I'd look at first, and what would change it.** The three-bucket split, then the handoff removal — two of the three most common causes of a 60% figure here are the message not arriving and the return session dying, and both are addressed by removing the trip rather than by anything upstream. What would flip me to the first two options is a number I don't have: what an unverified account actually costs you. If that's small, everything from the third option down is effort spent defending a gate you didn't need. And if you already know the drop concentrates in one channel or one device class, that alone reorders this list.
