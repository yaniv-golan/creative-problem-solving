# Gotchas

Failure modes this pipeline has actually produced, with what each costs. `SKILL.md` points here;
read it when something is going wrong, or once before your first run.

These are orientation rather than steps, which is why they are a reference: nothing here is
executed in order, and a run that never hits any of them is a run that went well.

---

- **Framework theater.** Rigid templates degrade reasoning and long sectioned output
  scores better without being better. Generate free-form, structure afterwards. More
  headings than mechanisms means delete headings.
- **Don't turn up the temperature.** It correlates weakly with novelty and moderately with
  incoherence — you buy nonsense faster than insight. Diversity comes from prompt
  structure, not the sampler.
- **Ordinary personas beat famous ones.** "Think like Steve Jobs" changes voice, not
  knowledge. Use several mundane specific ones — a procurement officer, a night-shift
  nurse — because the mechanism is partitioned knowledge, not costume.
- **Pick lenses for separation, not for a number.** Use every lens that attacks the problem
  differently; drop one only when it would produce the same shape of answer as one already
  chosen.
- **The user's framing is the strongest anchor in the room.** Attack the brief before the
  solution space, and generate before showing anything — once they've seen your first
  three ideas, everything after is a variation on them.
- **Elaboration is not creativity.** A long, detailed, thoroughly-specified obvious idea is
  still the obvious idea. Check distance from baseline, not word count.
- **Novices are who this hurts.** Model assistance widens the gap between experienced and
  inexperienced people on reframing, and sycophancy lands hardest on those who can't push
  back. If the user seems unsure of the domain, be more explicit about your uncertainty,
  not less.
