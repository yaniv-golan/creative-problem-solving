#!/usr/bin/env python3
"""Print the reading the run settled on, ask the user for the two things only they can give, and
record that it happened.

WHY THERE IS A PAUSE AT ALL. Phase 0 sharpens the brief silently and the run then spends about
forty minutes elaborating that reading. Two runs measured the cost. On a one-line prompt the run
invented a world pressure nobody had stated, ranked a family third on the bet that the pressure
was what drove the work, and wrote the question it should have asked into the option itself. On a
prompt the user had already refined -- one that carried what was already ruled out and what
success would look like -- the invented pressures stayed at world level and the top of the list
changed. Phase 0's own reading line was of the same quality in both. The difference was inputs
the model cannot fabricate, so the run asks for them instead of guessing.

WHY A SCRIPT HOLDS THE SENTENCES. Every other line the reader hears is printed by a script and
repeated verbatim, for the reason in references/pipeline-report.md: a model that skipped a stage
narrates having run it exactly as fluently as one that ran it. The gate is a weaker case of the
same thing -- a readback retyped from memory is a readback of what the model remembers, not of
what is in the file that dispatches -- so the four lines live here, in one copy, and the
orchestrator retypes none of them. The same file also renders the dispatch block at
`render-brief`, so the words a generator receives and the words the user approved come from one
place.

  brief_gate.py <work-dir> ask [--corrected]
  brief_gate.py <work-dir> skip --reason user-said-dont-ask|no-ask-mechanism
  brief_gate.py <work-dir> go
  brief_gate.py <work-dir> render-brief

`ask` prints ASK: lines, which the orchestrator puts to the user as one question and waits on.
`skip` and `go` print SAY: lines, which are repeated and not waited on. A refusal prints one
FAIL: line and exits 1; a work directory that is not there exits 2, because a heartbeat that
stays quiet about its own misconfiguration never fires and nobody notices.

THE GATE ASKS ONCE AND CORRECTS ONCE. A third exchange is refused here rather than left to
judgement: an interview is not a divergence pass, and each round narrows the space before it has
been explored.
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load_obj, brief_str, one_line

GATE = "gate.json"

# Both spellings of "we are starting", in one place because they are the same promise. The
# duration lives here rather than in the Opening it replaced: you cannot say "this takes about
# half an hour" and then stop to ask a question.
STARTING = ("This takes about half an hour, and I will tell you what each stage produced as it "
            "finishes.")

SKIP_REASONS = {
    # The user's own instruction, in any phrasing to that effect.
    "user-said-dont-ask": "You asked me not to ask, so I am starting.",
    # A host with no way to put a question to anyone. Never wait on a run nobody is watching.
    "no-ask-mechanism": "I cannot wait for an answer here, so I am starting.",
}


def die(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def _list_of_str(brief, key, path="brief.json"):
    """One model-authored list, or a refusal naming the key -- never a traceback.

    Same contract as robust_json.brief_str and for the same reason: brief.json is written by the
    orchestrating model, so `for x in brief["invented"]` over a string iterates characters and
    prints a premise per letter, which is a wrong answer rather than a stopped run.
    """
    v = brief.get(key)
    if v is None:
        return []
    if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
        shape = type(v).__name__ if not isinstance(v, list) else "list with a non-string in it"
        die(f"{os.path.basename(path)} — `{key}` is a {shape}, not a list of strings. Write "
            f"each entry as its own string, or leave the list empty. (looked in "
            f"{os.path.abspath(path)})")
    return [one_line(x) for x in v if one_line(x)]


def _brief(wd):
    path = os.path.join(wd, "brief.json")
    if not os.path.exists(path):
        die("brief.json — missing. Step 0c records the user's words, the reading, the actor and "
            "the decision before anything is dispatched; the gate reads them from there.")
    brief = load_obj(path)
    for key in ("reading", "actor", "decision"):
        if not brief_str(brief, key, path):
            die(f"brief.json — no `{key}`. The gate shows the reading, whose behaviour has to "
                f"change and what they are deciding; `{key}` is one of the three and there is "
                f"nothing to show without it.")
    if "invented" not in brief:
        die("brief.json — no `invented` list. If Phase 0 added nothing to the brief, say so with "
            "an empty list; an absent key cannot be told apart from a forgotten one.")
    return brief


# ---------------------------------------------------------------- the sentences

def render(mode, brief, reason=None, path="brief.json"):
    """The exact block for one mode, as a list of marked lines.

    ONE COPY OF EVERY SENTENCE. The plan that specifies this gate says the sentences are the
    design; they are held here and nowhere else, so a reviewer who changes a line changes it in
    one file and the readback, the record and the integrity check move together.
    """
    reading = one_line(brief_str(brief, "reading", path))
    actor = one_line(brief_str(brief, "actor", path))
    decision = one_line(brief_str(brief, "decision", path))
    invented = _list_of_str(brief, "invented", path)

    # "none", not an empty tail. The reader is being told what was added on their behalf, and a
    # sentence that trails off after a colon reads as a rendering fault rather than as an answer.
    pressures = "; ".join(invented) if invented else "none"

    head = [f"Reading this as {reading}. The person who has to act is {actor}, "
            f"deciding {decision}.",
            f"Pressures I added on my own, which you did not state: {pressures}."]

    if mode == "skip":
        return [f"SAY: {ln}" for ln in head + [f"{SKIP_REASONS[reason]} {STARTING}"]]
    if mode == "go":
        return [f"SAY: Starting. {STARTING}"]

    if mode == "ask-corrected":
        # SAY:, NOT ASK:, and the marker is the whole difference. This block asks nothing — it
        # shows the corrected reading and says the run is starting — and the marker is what tells
        # the orchestrator whether to wait. Marked ASK: it inherits "put it to the user and wait",
        # which on a host with a real user is a run hanging in front of a question that was never
        # posed. It also does NOT repeat the two questions: the user has just answered them, and
        # a block that asks again for what it is about to echo back reads as a broken exchange.
        #
        # THE ANSWERS ARE IN HERE BECAUSE THEY MUST BE HASHED. `readback_sha1` covers the exact
        # text printed, so anything outside this block can be rewritten afterwards and nothing
        # notices. These two are the whole point of the gate, they reach nine generators as "the
        # user's words" and the reader as "(your words)" — so the run may not hold a value for
        # either that the user was never shown. `go` refuses one that was not.
        solved = one_line(brief_str(brief, "counts_as_solved", path))
        tried = _list_of_str(brief, "tried_or_ruled_out", path)
        body = list(head)
        if solved:
            body.append(f"What would count as solved, in your words: {solved}.")
        if tried:
            body.append("Already tried or ruled out, in your words: " + "; ".join(tried) + ".")
        # "Recorded", not "Corrected": this block also closes the ordinary exchange, where the
        # user answered the two questions and corrected nothing, and "Corrected." there tells
        # them they changed something they did not.
        body.append(f"Recorded. Starting now; {STARTING[0].lower()}{STARTING[1:]}")
        return [f"SAY: {ln}" for ln in body]

    return [f"ASK: {ln}" for ln in head + [
        "Two things only you can tell me, each in a phrase, or say skip: What have you already "
        "tried or ruled out? What would count as solved?",
        "Say \"go\" to start, or correct anything above. I will fix it once and start, and I "
        "will not ask again."]]


def readback(gate, brief, path="brief.json"):
    """The block the user last saw the reading in, recomputed from the current brief.json.

    Which form it was is not stored, because it is already derivable and a sixth key would be a
    second source of truth: a skipped gate showed the skip block, a corrected one showed the
    corrected block (`prints` is 2 only after a correction), anything else showed the ask block.
    `go` prints no reading at all, so it neither writes this nor changes which form it names.
    """
    if gate.get("skip_reason"):
        return render("skip", brief, gate["skip_reason"], path)
    return render("ask-corrected" if gate.get("prints") == 2 else "ask", brief, path=path)


def sha1_of(lines):
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()


def unshown_answers(gate, brief, path="brief.json"):
    """The gate's two answers that the user was never shown back, or [].

    An answer recorded but never echoed is outside `readback_sha1` and therefore outside every
    check there is — and it is the value that reaches nine generators labelled "the user's words"
    and the reader labelled "(your words)". The `ask` block cannot carry them (at `ask` time they
    are empty by construction), so the rule is: **an answer exists only if a corrected print
    showed it**, which is `prints == 2`.

    Not enforced on the skip path. Nothing was asked there, so an answer in the brief came out of
    the user's own prompt, which they did write.
    """
    if not gate.get("asked") or gate.get("prints") == 2:
        return []
    named = []
    if one_line(brief_str(brief, "counts_as_solved", path)):
        named.append("counts_as_solved")
    if _list_of_str(brief, "tried_or_ruled_out", path):
        named.append("tried_or_ruled_out")
    return named


# ---------------------------------------------------------------- the record

def _load_gate(wd):
    path = os.path.join(wd, GATE)
    if not os.path.exists(path):
        return {"asked": False, "skip_reason": None, "prints": 0, "outcome": None,
                "readback_sha1": None}
    g = load_obj(path)
    if not isinstance(g.get("prints"), int):
        die("gate.json — `prints` is not a whole number. This file is written by "
            "brief_gate.py and read by verify_pipeline.py; a hand-edited one is not a record.")
    return g


def _save_gate(wd, g):
    with open(os.path.join(wd, GATE), "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=1, sort_keys=True)
        fh.write("\n")


# ---------------------------------------------------------------- the dispatch block

def render_problem(brief, path="brief.json"):
    """The constant part of every generator's PROBLEM block, from brief.json.

    Pasted into each dispatch rather than retyped, because a generator has Write and no reader:
    it cannot open brief.json, so whatever the orchestrator types is what it gets. This block is
    IDENTICAL across passes -- step 0c's uniformity rule -- and the per-pass "different phrasing
    of the same function" goes on one line above it.

    `verbatim_prompt` is deliberately absent. The generators receive the reading the user
    approved; handing them the raw prompt as well would put two statements of the problem in one
    dispatch and let a pass choose between them.
    """
    reading = one_line(brief_str(brief, "reading", path))
    actor = one_line(brief_str(brief, "actor", path))
    decision = one_line(brief_str(brief, "decision", path))
    solved = one_line(brief_str(brief, "counts_as_solved", path))
    tried = _list_of_str(brief, "tried_or_ruled_out", path)
    invented = _list_of_str(brief, "invented", path)

    out = [f"PROBLEM: {reading}. The person who has to act: {actor}. "
           f"What they are deciding: {decision}."]
    # Omitted when empty rather than rendered as "none": an empty heading in a dispatch prompt is
    # a slot a generator will try to fill.
    if solved:
        out.append(f"WHAT COUNTS AS SOLVED (the user's words): {solved}")
    if tried:
        out.append("ALREADY TRIED OR RULED OUT — do not hand these back:")
        out += [f"- {t}" for t in tried]
    if invented:
        out.append("PRESSURES ADDED FOR THIS RUN — these describe the world, not the person "
                   "asking:")
        out += [f"- {p}" for p in invented]
    return out


# ---------------------------------------------------------------- modes

def main(argv):
    if len(argv) < 3:
        print("FAIL: usage: brief_gate.py <work-dir> ask|skip|go|render-brief "
              "[--corrected] [--reason R]")
        return 2
    wd, mode = argv[1], argv[2]
    if not os.path.isdir(wd):
        # Exit 2, not 1: a wrong path is a misconfiguration of the caller, and a gate that
        # reports it as an ordinary refusal invites a re-run of the same wrong command.
        print(f"FAIL: {wd} is not a directory — the gate takes the run's _work directory, in the "
              f"shell's spelling (\"$BASE/$RUN/_work\", step 0b).")
        return 2

    corrected = "--corrected" in argv[3:]
    reason = None
    if "--reason" in argv[3:]:
        i = argv.index("--reason")
        reason = argv[i + 1] if i + 1 < len(argv) else None

    bpath = os.path.join(wd, "brief.json")
    if mode == "render-brief":
        # THE BLOCK IS NOT AVAILABLE BEFORE THE GATE RESOLVES. Without this a run can render the
        # dispatch block, fan out nine generators, and only then print a reading -- which would
        # satisfy every check while the user's one chance to correct arrived after the money was
        # spent. Nothing records dispatch order, so this is where that order is enforced.
        _g = _load_gate(wd)
        if _g.get("outcome") not in ("go", "skipped"):
            die("the gate has not resolved, so there is no approved reading to dispatch on. Run "
                "step 0d first: `ask` and then `go`, or `skip --reason …`.")
        for ln in render_problem(_brief(wd), bpath):
            print(ln)
        return 0

    brief = _brief(wd)
    g = _load_gate(wd)

    if mode == "ask":
        if corrected:
            if g.get("outcome") == "go":
                # THE READING THAT DISPATCHED IS THE ONE THAT STANDS. Correcting after `go` would
                # let a run dispatch on one reading and leave a different one in the record, and
                # every check downstream reads the record.
                die("this run has already started. A correction after `go` would leave a reading "
                    "in the record that is not the one the generators were dispatched with; if "
                    "the reading is wrong now, the run is wrong, not the record.")
            if g.get("prints", 0) >= 2:
                die("the gate asks once and corrects once; a run does not get a third exchange.")
            if g.get("prints") != 1 or not g.get("asked"):
                die("`ask --corrected` follows exactly one `ask`. This run has printed the gate "
                    f"{g.get('prints', 0)} time(s), so there is no reading for a correction to "
                    f"replace.")
            g["outcome"], g["prints"] = "corrected", 2
        else:
            if g.get("prints", 0) >= 1:
                die("the gate asks once and corrects once; a run does not get a third exchange. "
                    "If the user corrected the brief, re-run Phase 0 steps 3b and 4 on the "
                    "corrected brief and print with `ask --corrected`.")
            g["asked"], g["prints"], g["outcome"] = True, 1, None
        lines = render("ask-corrected" if corrected else "ask", brief, path=bpath)

    elif mode == "skip":
        if reason not in SKIP_REASONS:
            die("`skip` needs --reason user-said-dont-ask (the prompt said not to ask) or "
                "--reason no-ask-mechanism (this host cannot wait for an answer). "
                f"Got {reason!r}.")
        if g.get("prints", 0) >= 1:
            die("this run has already shown the reading and cannot then skip showing it. Say "
                "`go` to start.")
        g.update(asked=False, skip_reason=reason, prints=1, outcome="skipped")
        lines = render("skip", brief, reason, bpath)

    elif mode == "go":
        if g.get("outcome") == "skipped":
            # A TRUE SENTENCE AND A RECOVERY THAT EXISTS. This used to say nothing had been shown
            # yet, which on the skip path is false -- the reading was said -- and then named two
            # commands that both refuse. There is nothing to do here: the skip already started
            # the run.
            die("this run took the skip path, which already said the reading and started. There "
                "is no `go` to give: carry on with step 1.")
        if not g.get("asked"):
            die("`go` follows the gate. Nothing has been shown to the user yet, so there is "
                "nothing they said go to — run `ask`, or `skip --reason …` if you were told not "
                "to ask.")
        if g.get("outcome") not in (None, "corrected"):
            die(f"the gate is already finished (outcome: {g.get('outcome')}). It resolves once.")
        # THE TEXT THAT WAS PRINTED MUST STILL BE THE TEXT THAT DISPATCHES. Recomputed rather
        # than trusted: the cheapest way to have the gate and the freedom both is to print one
        # reading and edit the file afterwards, and by `go` that edit has already happened if it
        # is going to. verify_pipeline.py repeats the check at the end, for an edit made later.
        #
        # WHAT THIS DOES NOT PROVE, said plainly because two sentences here used to overclaim it:
        # a hash over rendered text cannot tell a reading that was put in front of a person from
        # one that was rendered into a pipe. It proves the gate ran and that the brief has not
        # moved since. Whether a human saw it is not knowable from this side.
        if sha1_of(readback(g, brief, bpath)) != g.get("readback_sha1"):
            die("brief.json has changed since the reading was shown; what the user approved is "
                "not what would dispatch. Print the new reading with `ask --corrected` before "
                "starting.")
        _unshown = unshown_answers(g, brief, bpath)
        if _unshown:
            die("brief.json carries " + " and ".join(f"`{k}`" for k in _unshown) + ", which the "
                "user has not been shown. Those reach the generators as the user's words and the "
                "report as \"(your words)\", so they may not be values only this run has seen: "
                "print them back with `ask --corrected`, then start.")
        g["outcome"] = "go"
        lines = render("go", brief, path=bpath)

    else:
        print(f"FAIL: unknown mode {mode!r} — ask, skip, go or render-brief.")
        return 2

    if mode != "go":
        g["readback_sha1"] = sha1_of(lines)
    _save_gate(wd, g)
    for ln in lines:
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
