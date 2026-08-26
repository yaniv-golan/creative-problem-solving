#!/usr/bin/env python3
"""Generate evals/scenarios/*.yaml from evals/evals.json.

`evals.json` is the record: the prompts and the graded assertions, versioned, with the reasoning
for every change in its `notes`. The scenarios are how you RUN it — cowork-harness executes the
prompt against a real sandboxed agent and has a pinned judge grade each assertion as a
`semantic_matches` rubric claim.

Generating one from the other keeps them honest. Hand-maintained copies of 47 assertions drift,
and a rubric that no longer matches the record grades something nobody wrote down.

  python3 tools/build-eval-scenarios.py [--check]

--check regenerates into memory and fails if any committed scenario differs, which is what CI
runs so a hand-edit to a scenario cannot land without the JSON moving too.
"""
import json, os, sys, textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "evals", "evals.json")
OUT = os.path.join(ROOT, "evals", "scenarios")

# Why each case exists, in the scenario itself, so a reader of the YAML is not sent to the JSON.
WHY = {
    1: "Strategic prompt. Measures whether the options differ in KIND — how the money is made —\n# rather than in degree.",
    2: "Bounded problem. Measures diagnosis before prescription, and proportionality: the risk\n# here is an oversized answer, not a thin one.",
    3: "NEGATIVE trigger. A decision with a defensible correct answer — the divergence engine\n# should not run at all. This one asserts the skill does NOT fire.",
    4: "Light question. Measures whether a small problem gets a small answer that still differs\n# in mechanism.",
    5: "Held out from all tuning. Measures whether the accumulated fixes generalise or merely fit\n# evals 2 and 4.",
}

TEMPLATE = """\
# GENERATED from ../evals.json (v{ver}, eval {eid}) by tools/build-eval-scenarios.py.
# Edit the assertions THERE and regenerate — a hand-edit here fails CI's --check.
#
# {why}
name: eval-{eid}-{name}
session: ../sessions/default.yaml
baseline: desktop-1.37937.1
fidelity: container
# The eval prompts are self-contained and several end by telling the model not to ask, so a gate
# here is a finding rather than something to script an answer for.
on_unanswered: first

prompt: |
{prompt}

assert:
  - result: success
{extra}\
  # semantic_matches is LIVE-ONLY: the judge is a model call, so this cannot run on the
  # token-free replay lane, and `lint` says so. That warning is expected here, not a defect.
  #
  # semantic_matches is TOOL-USE BLIND. Its judged corpus is the final message, the transcript
  # and authored files — never a tool call (harness TOOL_USE_BLIND_KEYS). So a rubric claim about
  # what the model DID, as opposed to what it said or wrote, is only as good as the trace it left
  # in text or on disk. Keep the claims here about reader-visible output, and let the hard
  # assertions above carry anything that depends on a tool call.
  #
  # No min_pass. Recipe 5's point is that answers vary run to run, so the signal is each claim's
  # pass RATE across N>=3 reps, read from RunResult.assertions[].semanticClaims — not one green.
  # Set min_pass to the reliably-hit core once a baseline profile exists.
  - semantic_matches:
      rubric:
{rubric}
"""

def build():
    d = json.load(open(SRC))
    out = {}
    for e in d["evals"]:
        eid, name = e["id"], e["name"]
        extra = ""
        if eid == 3:
            extra = ("  # The whole point of this case: the engine must stay out of a question that has a\n"
                     "  # defensible answer. A divergence engine that runs on everything is worse than none.\n"
                     "  #\n"
                     "  # This assertion, not the rubric, is what actually polices it. The rubric's\n"
                     "  # 'does not produce divergence-pipeline artifacts' claim is a soft cross-check:\n"
                     "  # semantic_matches cannot see a tool call, so it catches a pipeline that NARRATES\n"
                     "  # itself or writes files, and would miss one that ran purely through dispatches.\n"
                     "  # no_skill_triggered is tool-use aware and carries the weight.\n"
                     "  - no_skill_triggered: creative-problem-solving\n")
        out[f"eval-{eid}-{name}.yaml"] = TEMPLATE.format(
            ver=d["version"], eid=eid, name=name, why=WHY[eid],
            prompt=textwrap.indent(e["prompt"], "  "),
            extra=extra,
            rubric="\n".join("        - " + json.dumps(a) for a in e["assertions"]),
        )
    return out

def main():
    built = build()
    if "--check" in sys.argv:
        bad = []
        for fn, body in built.items():
            p = os.path.join(OUT, fn)
            if not os.path.exists(p) or open(p).read() != body:
                bad.append(fn)
        if bad:
            print("FAIL: scenario(s) out of sync with evals.json: " + ", ".join(bad))
            print("      run: python3 tools/build-eval-scenarios.py")
            sys.exit(1)
        print(f"all {len(built)} eval scenarios match evals.json")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, body in built.items():
        open(os.path.join(OUT, fn), "w").write(body)
        print(f"  wrote {fn}")

if __name__ == "__main__":
    main()
