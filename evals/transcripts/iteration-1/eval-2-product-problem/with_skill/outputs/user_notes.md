# Notes on running the skill

## Mode chosen: DEEP

The skill's rule is "fast for a quick side question, deep for a real strategic problem, anything
the user will act on." A 60% loss at a named funnel step, with two remedies already tried and
budget clearly attached, is unambiguously the second. It also has the property deep mode is
built for — the user has already exhausted the obvious answers, so retrieval-as-difference-
constraint is doing real work rather than being ceremony. No ambiguity here, so I didn't ask.

## Things I was unsure about

**1. I don't know what "account-verification" actually means.** Document-and-selfie KYC, an
emailed confirmation link, or an SMS code are three very different problems, and roughly half
the generated ideas only apply to the first. This is the biggest unresolved ambiguity in the
whole exercise. The skill says to show the sharpened brief to the user before generating and
that their correction is worth more than an extra generation round — but I'm running
non-interactively, so I couldn't. I resolved it by writing the brief at a level of abstraction
that covers all three ("enough confidence about who this person is"), and then surfacing the
ambiguity explicitly as the #1 item under "what would change my ranking." A real interactive
run should ask this one question before Phase 1.

**2. Generator count.** The skill says 5-7 generators and separately warns that per-agent
diversity contribution falls off past ~5. I used 6. Contradiction and first principles did
overlap somewhat on this problem (both converged on "operator proves itself first"), so 5 would
probably have been fine and cheaper. The overlap wasn't wasted, though — four independent
generators landing on the same mechanism is itself a signal, and I noted it in the merge record.

**3. The diversity script's duplicate list is not as reliable as the skill claims.** The skill
says to treat the duplicate-pair list as the trustworthy output and the headline number as an
upper bound. On my first run it flagged 4 near-duplicate pairs, all involving the same idea, and
all four were mechanically unrelated to their supposed partner — the flagged idea was simply
twice as long as the others, and the char-n-gram kernel reads length. Trimming it to comparable
length made all four pairs vanish and moved the verdict from "clustered" to "acceptable" without
changing a single mechanism. So the tool is length-sensitive in a way the docstring doesn't warn
about, and the practical rule is: **normalise idea length before scoring, or the duplicate list
lies.** Worth adding to the skill.

**4. "Order by distance from baseline, not confidence" produces an odd reading order.** The
distances are lexical, so an idea can rank first for using unusual vocabulary rather than for
being genuinely far from the obvious answer. I followed the instruction anyway, since the spread
was 0.71-0.88 and fairly tight, but the ordering carries less information than the skill implies.

## Where the skill was ambiguous or led me astray

- **Phase 4's output template versus the "framework theater" gotcha.** The skill prescribes a
  fairly rigid report template (three fixed bullets per idea) and then, two sections later, warns
  that rigid output templates degrade reasoning and that if your output has more headings than
  mechanisms you should delete headings. These pull against each other. I followed the template
  because it's genuinely load-bearing here (the "what has to be true" bullet is where most of the
  honest content lives), but kept prose between ideas rather than adding sub-headings.
- **The banned-word list applies to generators, not to the final report.** The skill doesn't say
  this explicitly. Writing the user-facing answer without ever using the word "verification"
  would have been contorted and unhelpful, so I let the banned list expire at the end of Phase 1.
- **"Report novelty as a hypothesis" is harder than it sounds when the answer is "this already
  exists."** One of my strongest survivors (money-rail assurance) turned out to be a shipped
  commercial product. The skill's honesty rule covers "I found no prior art" but doesn't say what
  to do when you *do* find it. I kept the idea and labelled it as buyable rather than inventable,
  which seems more useful than cutting it — but that's my call, not the skill's instruction.

## Workarounds

- The initial `find` on the macOS path returned nothing because the shell tool runs in an
  isolated Linux workspace where the folder is mounted at `/sessions/.../mnt/outputs/`. Located
  the mount, then ran `scripts/diversity.py` from there without further trouble. One wasted call.
