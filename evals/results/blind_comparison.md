# Blind comparison — iteration 5

Judged as the person who asked the question and has to act on the answer. A/B assignment was
counterbalanced, so the labels carry no information about which arm is which.

---

## The retention pair — "We keep losing senior engineers at 18 months; it's not the money"

**Answer A** — Six mechanisms (periodic rebuild, problem-stock depletion, hiring intake, conclusive written record, scheduled absence, non-fungible grants), each with what-has-to-be-true / failure mode / owner, plus seven cut ideas and an ordering.

**Answer B** — Structured diagnosis: why 18 months, a pushback on "it's not the money," three diagnostic instruments, four ranked causes, structural and operational fixes, a don't-bother list, a reframe, and a three-item close.

### Winner: **A**

### 1. Which would I rather have received

B's single best paragraph is one A has no equivalent for:

> "most benchmarking compares *year-one* offers, and big companies don't compete on year one — they compete on years two through four, via annual refresh grants... their effective total comp is *declining* relative to market every single year they stay, even though you 'matched' on day one."

That is the highest-base-rate explanation for an 18-month cluster, it directly and respectfully contradicts the premise I stated, and it comes with a week-long test. If B is right, A wasted my time entirely.

But past that paragraph, B is largely material I already have. "Build a real staff/principal IC track," "stay interviews," "maintain a hard problems list," "sponsor external visibility," "don't counteroffer" — an engineering leader losing their third senior person has read all of this. B even acknowledges the ceiling of its own framing: "In rough order of likelihood... **No visible next rung**. This is the most common cause and the most fixable."

A converts B's diagnosis into instruments. Where B says the problem stopped being hard, A makes it countable:

> "how many genuinely unsolved, consequential problems are open right now, and how many people do you have who could lead one? Below 1:1 and the 18-month number is your answer rather than your mystery."

That threshold is the difference between a hypothesis and a measurement. Similarly, B says exit interviews are worthless and to interview stayers — A says the same, then adds the sharper instrument: "plot every departure against two dates — their start date, and the date their biggest project shipped or got cancelled."

Both answers independently arrive at the manager-concentration check, in nearly identical language (B: "a management problem wearing a retention costume"; A: "a specific problem wearing a systemic costume"). That diagnostic is a wash and shouldn't count for either.

### 2. Which gave me something I would not have thought of

A, and not close. Four things I would not have generated:

- **The absence drill.** "Make one person unreachable inside their domain for a bounded window while they're still here and still willing to fix what surfaces. Every question the team is forced to escalate gets logged as a defect against the record, never against the substitute." A week's cost, and it sizes the exposure directly rather than inferring it.
- **The Torrens inversion.** "an objection that isn't on the record has no standing to block a change, and no standing to be invoked after the breakage. Registering becomes the only way to protect what you know." This is the only proposal in either answer that fixes documentation incentives rather than exhorting people to document.
- **The rebuild cycle**, executed by people who didn't build it, original author present and "barred from writing any of it" — which manufactures greenfield work out of an existing system, aimed precisely at what B correctly identifies as cause #2 but only answers with "maintain a hard problems list."
- **Non-fungible grants**, with guaranteed observing time in astronomy as the precedent: "What a much larger company structurally cannot supply is a claim that isn't fungible." B's version of this insight is "put senior engineers in the room where strategy is decided," which is the standard formulation.

B's genuinely non-obvious contribution is the refresh-grant argument and the closing reframe ("If you're losing the median and keeping your top three, the system is working"). Real, but one or two items against A's four.

### 3. Which is more likely to contain something false or overstated

**A** — every external anchor checks out:

- ✅ Ise Jingū rebuilt every 20 years for ~1,300 years on an alternate site — correct, including the alternate-site detail.
- ✅ Torrens system, South Australia, Real Property Act 1858, register as conclusive evidence of title — correct on jurisdiction, year, and the legal point being borrowed.
- ✅ FOGBANK — "Y-12 needed the better part of a decade and roughly $69M to reconstruct a manufacturing process after the people who knew it retired." Confirmed: $69M spent after an earlier $23M on failed alternatives, completed 2008, close to a decade after the refurbishment program started.
- ✅ Guaranteed time observations reserved outside the competitive proposal process for instrument builders — correct.

**B** — no hard external numbers to check, which is itself a choice. Its two flat empirical assertions are the two most-repeated unsourced folk claims in this genre: "Recruiter contact rates peak in exactly this window" and counteroffers "mostly fail within a year." Neither is sourced, and B's source list is Medium posts and recruiting-vendor content. B partly redeems this with an unusually good caveat:

> "figures like '68% cite limited growth opportunities' circulate widely in recruiting-industry content but trace back to vendor surveys with thin methodology... I wouldn't quote the specific percentages to your board."

That is the most honest sentence in either answer and it should be said plainly. But it also concedes that B's evidence base is thin, while A's four anchors survive checking intact.

### 4. Which respects my time

A, and it's the cleaner win of the two dimensions where length could have gone wrong: A is the **shorter** answer (~55 lines vs ~82) and still carries more distinct proposals. B spends roughly a third of its length on diagnosis before reaching any action, and its "What's usually actually going on at a well-paying startup" section is four paragraphs restating widely known causes. A front-loads the diagnostic into one paragraph, gives six mechanisms, then explicitly reorders them against its own presentation: "the two-date plot, then the absence drill, then the problem-stock count — which is not the order above."

A also does the harder favour of telling me what not to do, with reasons, including one it recommends anyway while noting it doesn't answer my question: buying a post-departure claim on a leaver's time is "Cheap and worth doing, but it manages the loss rather than reducing it." B's "Don't bother with" list has two items and no reasoning beyond a sentence each.

### 5. Where the winner still falls short

- **A never names refresh grants.** It gestures at the clock — option (a) is "a calendar artefact, a vesting event," and one of its two closing unknowns is "whether the 18-month cluster tracks a vesting date or a project-completion date" — but it never states the mechanism, which is that a matched day-one offer decays against a competitor stacking annual grants. If that's the real cause, A's six mechanisms are all treating the wrong organ. B gets this and A doesn't; that is A's one serious gap.
- **Several items need authority A doesn't check I have.** "Who runs it: the CEO. This is a company-shape decision" and "Who runs it: you, personally" assume the asker can commit the company. If they're a VP Eng, half the list is unavailable.
- **The absence drill is riskier than presented.** A flags the failure mode ("the organisation reads the resulting failures as fundable work rather than as proof the absent person is indispensable") but doesn't say how to set that framing up front, and the downside — visible degradation blamed on the wrong person — is a career-cost for whoever runs it.
- **No sequencing over time.** Six mechanisms and an ordering of the first three, but nothing about what happens in months 3-12, or which of these can run concurrently. B's "If you do only three things" close is tighter as a landing.

---

## Summary

| | Retention |
|---|---|
| Winner | **A** |
| Decisive reason | Converts diagnosis into countable instruments with owners and failure modes, in fewer words, with every external anchor surviving spot-check |
| Loser's best moment | B's refresh-grant pushback on "it's not the money" |
| Factual risk | B: two flat unsourced folk claims (recruiter contact peaks, counteroffer failure rate) on a source base of Medium and vendor content |
| Length verdict | Winner is the shorter answer — length did not decide it |
