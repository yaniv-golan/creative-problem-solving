I ran this as a deep pass: web research to map what already exists, then six independent generators that couldn't see each other's output, then a category-negation round, then pruning. About 48 candidates in, 8 out.

**Sharpened brief:** A stranger has decided they want in. You need enough confidence about who they are to accept the risk of admitting them; they need to reach the thing they came for. Today all of that confidence is purchased up front, before they've received anything — and 6 in 10 refuse to pay. Framed adversarially: the person suspects the request is a scam, the assurance bar is rising not falling, the budget is falling, and almost everyone you're losing was never fraudulent.

**The obvious answer (baseline, set aside):** defer the check until after first value, add social sign-in and magic links, cut fields, send a resume-link reminder, A/B test the explanatory copy. Everything below is measured by distance from that.

**One thing before the ideas.** Shortening the form and adding a progress bar are both *persuasion* fixes — they assume the person wants to continue and is being worn down. The KYC research says the single largest abandonment cause is "I don't have the document with me right now," which persuasion cannot touch. It's worth knowing whether your 60% is one population or four (people who can't comply now, people who don't trust the ask, people who hit a technical failure, and bots that *should* fail) before you spend on any of this. If a meaningful slice is paid-acquisition junk, your real honest-person loss is much smaller and the fix is upstream.

---

### A member posts a bond

An existing account holder in good standing stakes something they value — tenure, standing, a claim on their balance — on the newcomer being genuine. Identity assurance stops being evidence you extract from a stranger and becomes a collateralised claim on a party you can already reach and penalise.

- Why it's not the obvious answer: it doesn't reduce what's asked of the newcomer, it removes the newcomer from the transaction entirely.
- What has to be true: enough arrivals have a pre-existing tie to someone already inside, and vouchers respond fast enough that nobody is left waiting.
- Failure mode / cost: useless for cold traffic; creates a collusion surface; and a supervisor may not accept a member's word as an identity record at all.

### Score correct denial, not correct assertion

Stop asking people to prove they're themselves. Show them claims a criminal working from a stolen data packet would plausibly accept and a real person will confidently reject — "we have you at [wrong former address], is that right?" Honest people pass by knowing their own life. An impostor has no basis for confident denial.

- Why it's not the obvious answer: the signal comes from rejection rather than production, so the honest person supplies nothing and needs no document, camera, or code.
- What has to be true: you have enough third-party data about your population to generate credible-but-false claims.
- Failure mode / cost: this is knowledge-based authentication run backwards, and KBA has a bad reputation earned honestly — it degrades as breach data accumulates. Also fails for thin-file and recently-arrived people, who are disproportionately the ones you say you're losing.

### The house identifies itself first

Before asking for anything, recite non-public facts you already hold about this person — the exact amount and date of the charge that brought them here, the partner reference the referral arrived under, the last four of the account the payment came from — and ask only for confirmation or correction. Pair it with a hard rule that nothing is ever sent *inbound*: every contact is one the person initiates from a number or address they reached under their own power, because unsolicited direction of contact is the structural signature of a scam, and you cannot argue someone out of a pattern-match.

- Why it's not the obvious answer: trust badges and explanatory copy are assertions. This is evidence, and it doubles as a discriminating signal, because how someone confirms or amends a record is itself informative.
- What has to be true: you or your acquisition channel already hold at least one non-public fact about this person, and reciting it is legally survivable.
- Failure mode / cost: the recitation is itself a disclosure to whoever is on the other end, so it has to be facts an impostor already has or facts that are useless to them. Legal will want to look at this before engineering does.

### Ask at an hour they can answer

Detect that the person is somewhere the request is impossible — commuting, at work, on a shared or public machine, no document within arm's reach — and deliberately *decline to ask*, holding the exact state and reopening it when they're somewhere they can comply.

- Why it's not the obvious answer: it treats the request as having a right and a wrong hour, rather than a right and a wrong length. Deferred registration moves the ask later in the sequence; this moves it later in the *day*.
- What has to be true: context is inferable from signals you already have (device class, network, time, session shape), and the value of the thing they came for survives an interruption.
- Failure mode / cost: you eat the latency, and if the reopening is a notification you have re-created the inbound contact you were trying to avoid. Cheapest thing on this list to test.

### The barrier dissolves from your side

The wall between a newcomer and the loss-bearing core thins as a function of *your* passive observation — device continuity, return visits, coherence of behaviour with the stated purpose — never as a function of anything they're asked to do. The waiting happens on your side of the wall, so by the time they advance toward anything that can hurt you, the barrier has already gone. Screening is negative: only internal contradiction across freely emitted signals triggers a demand.

- Why it's not the obvious answer: progressive profiling still asks, just in smaller pieces. This asks nothing, and the accumulation is invisible.
- What has to be true: passive signal accrues faster than people advance toward the loss-bearing core, and your supervisor accepts a cumulative auditable total in place of a point-in-time attestation.
- Failure mode / cost: fails hard for one-shot high-value products where the first action is the risky one, and it is the option most likely to be rejected outright by compliance.

*(This one is the honeybee candy-plug: a new queen dropped into a hive gets killed, so she's caged behind a sugar plug the workers spend 3–5 days chewing through from their side, while her pheromone spreads. The delay costs the queen nothing and it dissolves at the rate of the colony's own accumulating familiarity. Verified — it's standard practice.)*

### Assurance rides in on money they push out

Have the person send a trivial amount *out* of an account they already control, initiated entirely inside their own bank's app. Nothing arrives inbound so the phishing reflex never fires, and the incoming payment carries the sending bank's already-completed identity work in its metadata.

- Why it's not the obvious answer: it's the inverse of a penny-drop. Direction of travel is doing the work, not the payment.
- What has to be true: the payer-name and account-holder data on the inbound rail is admissible to you as assurance rather than as unattested self-declaration.
- Failure mode / cost: **this is fully commercialised** — Trustly's Pay N Play and the pay-by-bank identity products do exactly this. Which is good news: you buy it, you don't build it. Excludes the unbanked, and jurisdiction-dependent.

### The errand is the evidence

Every fact the person must supply *anyway* to reach what they came for — the property being covered, the employer being claimed through, the amount, the destination — gets scored silently against bureau, telco and registry records as it lands. Corroboration is manufactured as a by-product of pursuing the goal, so no question exists purely as a toll.

- Why it's not the obvious answer: pre-fill makes the toll shorter. This deletes the toll and harvests the errand instead.
- What has to be true: the task-intrinsic data carries enough entropy, cross-referenced, to reach your assurance threshold on its own.
- Failure mode / cost: it probably doesn't, on its own, for a regulated product — so it's a contributor to a score, not a replacement. Also the least visible to the person, which is a compliance-disclosure question.

### Manage the exposure, not the certainty

Three moves in one direction: close the outbound paths so money leaves only to the instrument it entered on and goods ship only to the address bound to the payment; instrument the *assets* rather than the door, so the identity demand is generated by the thing being touched anomalously rather than by the arrival; then price and reserve against the residual instead of extracting more evidence from everyone.

- Why it's not the obvious answer: it stops treating identity confidence as something to maximise and starts treating it as a priced exposure. The 60% is currently a population-wide behavioural tax paid to avoid a per-capita cost you have never actually quantified.
- What has to be true: your obligation is a risk-outcome standard rather than a categorical procedural precondition. This is the assumption to check first, because it determines whether half this list is even legal for you.
- Failure mode / cost: if the duty is procedural, this is non-compliance with extra steps. It also requires a number — expected loss per admitted uncertain person — that most teams don't have and that finance will contest.

*(The asset-instrumentation half is borrowed from immunology: the immune system largely gave up on classifying self versus non-self at the border. A T cell meeting an antigen without a costimulatory signal from distressed surrounding tissue goes anergic rather than attacking. The tissue raises the alarm, not the gate. Verified — Matzinger's danger model, on top of the Bretscher–Cohn two-signal rule.)*

---

**Cut, and why:**
- *Statistical sampling instead of per-head checking* (mark-recapture, Dorfman pooling) — mathematically lovely, but no supervisor accepts a population-level bound in place of a per-person record, and operationally it collapses into risk-based tiering, which you probably already have.
- *Pre-computing identity records for everyone plausibly eligible before they arrive* — no lawful basis under GDPR or CCPA. Dead on arrival.
- *Paying known fraudsters a bounty for techniques that worked* — this is red-teaming with a legal problem bolted on. Buy an adversarial dataset instead.
- *Rugby's advantage rule — hold the failed check open, rewind and enforce later* — requires perfect reversibility of everything done in the window, which fails the moment money leaves.
- *Letting the person own and monetise their own assurance record* — collapses into reusable identity wallets, which already exist and which you'd buy, not build.
- *Asking the person's employer, landlord or bank to answer for them* — they won't answer at scale, and frequently legally can't.

**Set diversity:** 6.72 effectively distinct directions out of 8 (84%), no near-duplicate pairs above threshold. That is a measure of *diversity*, which is measurable — not novelty, which isn't.

**On prior art, specifically.** I searched for existing approaches before generating and used the results as a difference constraint. Reverse authentication (the house going first) exists as a concept and in patents, mostly in banking anti-phishing, and I did not find it deployed at account opening. Pay-by-bank identity is fully commercialised. Reusable credentials, passkeys, risk-based tiering, desktop-to-mobile handoff, progressive profiling and deferred registration are all mature and were excluded from generation. I did not find the correct-denial screen or context-timed deferral written up as conversion tactics — but anyone with a mature fraud-analytics team may be doing something like the errand-as-evidence pattern under a different name, and I'd expect a large neobank to have tried the exposure-management framing. Treat "I didn't find it" as a falsifiable claim about where I looked, not as a claim that it's new.

**What would change my ranking:**
1. **Whether "account-verification" means a document-and-selfie check or an emailed code.** If it's a code, ideas 6, 7 and 8 mostly don't apply, and the money is in the house-goes-first framing plus deliverability forensics — a chunk of that 60% may simply not be receiving the message.
2. **Whether your regulatory duty is a risk-outcome standard or a procedural must-do-before-anything.** Ideas 1, 5 and 8 are the highest-leverage things here under the first reading and flatly illegal under the second. Answer this before you build.
3. **What share of the 60% come back later.** If many do, you have a latency problem rather than an abandonment problem, and idea 4 is nearly free.

Sources: [KYC UX and drop-off causes](https://kycaid.com/blog/reduce-user-drop-off-kyc-verification-ux/) · [KYC funnel loss benchmarks](https://veridas.com/en/kyc-funnel-loss-customer-drop-off/) · [onboarding abandonment data](https://www.jumio.com/how-to-reduce-customer-abandonment/) · [sign-up flow practices](https://www.pingidentity.com/en/resources/blog/post/frictionless-signup.html) · [reusable digital identity](https://www.dock.io/post/reusable-digital-identity-verification-vendors) · [Trustly Pay N Play](https://www.trustly.com/products/paynplay) · [reverse authentication](https://www.researchgate.net/publication/256363279_Reverse_Authentication_in_Financial_Transactions_and_Identity_Management) · [queen introduction candy plug](https://www.basfbees.org/queen-installation.html) · [Matzinger danger model](https://pmc.ncbi.nlm.nih.gov/articles/PMC4417989/)
