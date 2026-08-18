I've read this as push-dominant — the outside offer converts a drift that already started rather than creating one. If it's actually pull (nothing is wrong, they just become legible to a bigger market at month 18), then options 3 and 6 are the only ones that matter and the rest is overhead.

**Before any of this: you don't yet know which clock is running.** Four candidates — (a) it's a calendar artefact, a vesting event or a hiring-cohort spike rather than an experience curve; (b) the build they were hired for shipped and the job went custodial; (c) someone above them stopped growing the size of decisions they own; (d) the company stopped opening new hard problems faster than they finish them. Cheapest way to separate them: plot every departure against two dates — their start date, and the date their biggest project shipped or got cancelled. If exits track the second, it's (b)/(d); if the first, it's (a). Then ask the people who *passed* 30 months what changed for them around month 18. Survivors will tell you what leavers politely won't.

### Rebuild something on a clock shorter than the leaving interval

Pick one load-bearing subsystem a year and rebuild it deliberately — executed by people who didn't build it, with the original author present, answering questions, and barred from writing any of it. Ise Jingū has rebuilt its main shrine every 20 years for roughly 1,300 years, on an alternate site, and the interval sits below a working life precisely so each cohort of carpenters builds the whole thing once alongside the previous one. Two things fall out: transfer happens as work rather than as documentation, and you manufacture greenfield build work out of the system you already have — which is the thing month-18 people say they've run out of.
- What has to be true: your subsystems are small enough that a rebuild is a quarter, not a year.
- Failure mode / cost: you spend real capacity re-solving solved problems, and the first one overruns. If the rebuild is just a port to a newer framework, you bought nothing.
- Who runs it: whoever owns the roadmap has to protect the slot. An engineering manager cannot fund this out of slack.

### Treat unsolved problems as a stock with a depletion rate

A strong person consumes the hard problems that existed when they arrived, at a rate. If you open new fronts more slowly than that, a fixed-tenure exit is arithmetic, not sentiment — and every people-side intervention is treating a roadmap problem with an HR instrument. Count it directly: how many genuinely unsolved, consequential problems are open right now, and how many people do you have who could lead one? Below 1:1 and the 18-month number is your answer rather than your mystery.
- What has to be true: your market supports opening new fronts. If it doesn't, the honest version is that you're a two-year stop for this profile and should staff for that deliberately.
- Failure mode / cost: opening fronts you can't fund produces a graveyard of cancelled projects, which loses the same people faster.
- Who runs it: the CEO. This is a company-shape decision, not a management one.

### Stop hiring the profile the rival is shopping for

The 18-month curve is partly set at the offer stage. Someone whose trajectory points at a bigger name keeps pointing there regardless of what you build around them; someone who already did that tour and left it is buying what you actually sell. Bias intake toward net sellers of prestige, and toward people who want the specific shape of work you have rather than the category it belongs to.
- What has to be true: enough inbound to be selective, and the honesty to tell the two apart at interview.
- Failure mode / cost: slow — it only touches cohorts you hire from here. And it degrades easily into a rationalisation for hiring people with fewer options, which is a different and worse company.
- Who runs it: whoever writes offers, with the hiring manager. Cheapest to start, slowest to pay.

### Make the written record conclusive rather than advisory

"Why it's built this way" lives in heads because writing it down has no payoff — the knowledge protects the system just as well from inside someone's head, as long as they're in the review to object. Invert the payoff: an objection that isn't on the record has no standing to block a change, and no standing to be invoked after the breakage. Registering becomes the only way to protect what you know. This is the operating principle of the Torrens land-title system (South Australia, Real Property Act 1858): the register is conclusive evidence of title, not one input among several, and that's what forced everyone onto it.
- What has to be true: you hold the line the first time a respected person says "I always knew that would break" about something they never wrote down. Flinch once and it's over.
- Failure mode / cost: defensive over-registration and a register nobody reads. Cap it at load-bearing subsystems.
- Who runs it: a tech lead with standing to reject a change on procedural grounds.

### Schedule the absence before it happens

Coming at this from several unrelated directions, the same move kept appearing, which is itself informative about the problem: you cannot ask someone what only they know, and you cannot read it off the documentation — the only reliable instrument is removing them and watching what breaks. Make one person unreachable inside their domain for a bounded window while they're still here and still willing to fix what surfaces. Every question the team is forced to escalate gets logged as a defect against the record, never against the substitute.
- What has to be true: the organisation reads the resulting failures as fundable work rather than as proof the absent person is indispensable. If it does the latter, you've made the problem worse.
- Failure mode / cost: real degradation during the window. The untested case looks like FOGBANK — Y-12 needed the better part of a decade and roughly $69M to reconstruct a manufacturing process after the people who knew it retired and the records turned out to be sparse.
- Who runs it: an engineering manager, next month. Cheapest item here.

### Give them something with no market price

You lose every contest with a number attached, so stop entering them. What a much larger company structurally cannot supply is a claim that isn't fungible: a standing veto over changes to a system someone built, first refusal on the next hard problem before it's staffed, a bespoke arrangement about schedule or location or shape-of-life that costs you one conversation and costs them a policy exception nobody will file. Astronomy formalises exactly this — the teams who build the instruments receive guaranteed observing time, hundreds of hours reserved outside the competitive proposal process, because what they want can't be bought.
- What has to be true: the resource you're granting a claim on is genuinely scarce and genuinely wanted. Priority access to something abundant is worth nothing.
- Failure mode / cost: vetoes accumulate into a system nobody can change, and bespoke deals become visible unfairness. Both need expiry dates.
- Who runs it: you, personally. It doesn't scale past a couple of dozen people, which at your size is fine.

**Cut, and why:**
- *Renting your best people out as paid external advisors.* It does force them to articulate the system — while you pay to introduce them to their next employer.
- *Circulating the rival's cancelled projects and layoff history internally.* Reads as insecurity; the one person it convinces was staying anyway.
- *Asking people to write down in advance what offer would make them leave.* Teaches them to recognise a good offer.
- *Two signatures on every consequential decision.* With headcount falling you'd be spending your scarcest resource on ceremony. Narrow it to blast-radius review on load-bearing changes, or skip it.
- *Deliberately coupling systems so exits hurt visibly.* Works, and leaves you with a worse system than the one you were protecting.
- *Buying a standing post-departure claim on a leaver's time for their old area* — a purchased option, not a goodwill alumni list. Cheap and worth doing, but it manages the loss rather than reducing it, so it isn't an answer to the question you asked.

**What I'd look at first, and what would change that:** the two-date plot, then the absence drill, then the problem-stock count — which is not the order above. The drill because it costs a week and tells you the size of the exposure; the stock count because if your ratio of open hard problems to people who could lead one is under 1, nothing else here is doing any work. Two things you know and I don't: whether the 18-month cluster tracks a vesting date or a project-completion date, which decides whether half of this is even relevant; and whether the leavers mostly reported to the same one or two people, in which case this is a specific problem wearing a systemic costume.
