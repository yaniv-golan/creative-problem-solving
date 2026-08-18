MODE: fast

## Gate conditions

The skill's gate says **default to fast**, and go deep only if **at least two** of five
conditions hold. Evaluated:

| Condition | Holds? |
|---|---|
| About what to build/become, not how to fix something specific | **No** — this is fixing one specific step |
| User has tried the obvious answers / says they're stuck | **Yes** — "already tried shortening the form and adding a progress bar", "I'm out of ideas" |
| No known-good answer; reasonable experts would disagree | **No** — verification UX has well-established patterns |
| Decision is expensive or hard to reverse | **No** — these are sprint-sized experiments |
| Answer needs current facts I'd have to look up | **No** |

Only 1 of 5 holds → fast. The skill also names this case explicitly: *"A drop-off number, a
bug, a 'which of these', a question with a defensible right answer: fast, or no pipeline at
all."* Not "none", because the user is asking for options and states they're stuck, which is
the skill's core trigger.

## What was run

- **Phase 0** — function restated ("get a stranger to a state the business can trust, without
  asking them to prove anything at the moment they have no reason to bother"); banned-word list
  (onboarding, flow, drop-off, verification, form, progress bar, step, funnel, friction,
  conversion); obvious answer written down and set aside (magic links, better copy, reminder
  drips, skip-for-now); three adversarial attributes injected (person suspects phishing;
  engineering budget falling; regulator about to require *more* proof).
- **Phase 1** — five labelled passes with "not reusing" between them: contradiction, first
  principles, inversion, analogical transfer, actor reversal. Verbalized sampling used; the
  low-probability tail produced the three ideas that ended up ranked first, second and sixth.
  Biomimicry skipped (deep-mode only per the skill). SCAMPER and morphological skipped.
- **Phase 2** — pooled output clustered into four (move the check in time / move who does the
  proving / remove the handoff / assist and recover). Negation round produced three genuinely
  outside clusters: change who arrives, remove the account entirely, price the abuse. Two of
  those became options 1 and 2. One negation pass only.
- **Phase 3** — convergence read by hand found two attractors: *decouple the check from first
  use* (3 lenses independently) and *delete the surface handoff* (2 lenses). Both are in the
  answer rather than deduped away. Cross-consistency prune killed the $1-charge and 72h-expiry
  ideas. Borrowed mechanisms (hotel front desk, clinic escort, door policy) restated as
  principles with no citations, per the fast-mode rule.
- **Phase 4** — diagnosis-first opener (cause unknown), ambiguity reading disclosed, ~1000
  words, no process/lens/cluster/score in the output.

## Things a human should review

1. **The diversity script behaved exactly as the skill warns.** I ran it on 18 one-line
   mechanisms: "17.70 effectively distinct (98%), no pairs above 0.22." Meanwhile my own read
   found two mechanisms each appearing across multiple lenses. The number is noise here; the
   hand read is what did the work. Consistent with the skill's own documented false negative.
2. **Borderline call on running the script at all.** The skill says skip it in fast mode with
   fewer than ~12 short ideas. The *survivor* set was 6; the *pre-prune pool* was 18. I read
   "fewer than ~12" as applying to the pool and ran it. The skill doesn't say which set the
   threshold refers to — worth disambiguating.
3. **Ambiguity handling — I did not ask.** Phase 0 permits one clarifying question and uses
   *this exact example* ("the verification step could mean document KYC, an email link, or an
   SMS code"). In a one-shot eval I can't ask, so I took the documented fallback: pick the
   likeliest reading, name it in line one, say what changes under the others. If the harness
   intends "asking one question" to be a valid response shape, this run under-tests that path.
4. **Ordering ambiguity in the skill.** Phase 4 says order "by distance from the obvious
   answer, not by your confidence" but doesn't say which end leads. I led with the most
   distant. Nearest-first is an equally literal reading of the same sentence.
5. **Mild tension in the template.** Phase 4 caps the diagnosis at "about three lines" while
   also requiring 2-4 candidate causes plus the cheapest test to separate them. Mine runs ~4
   lines. On a symptom-report like this one the diagnosis is load-bearing enough that I'd
   rather overspend there than on a seventh idea, but it is over the stated budget.
6. **Domain claims worth a sanity check by someone who owns the funnel.** "Two of the three
   most common causes of a 60% figure at this step" in the closing paragraph is my judgement,
   not a sourced statistic, and in fast mode it wasn't verified. It's framed as my read rather
   than as fact, but a reviewer should decide whether that framing is strong enough.
7. **One idea was demoted out of the option list on purpose.** "Change who arrives — the 60%
   may be correct sorting, and this is marketing's number not the onboarding team's" is folded
   into the diagnosis opener rather than given its own heading, to hold the word budget. It's
   arguably the single most contrarian item in the pool and a reviewer might want it promoted.
