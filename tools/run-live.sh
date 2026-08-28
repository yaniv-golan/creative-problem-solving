#!/usr/bin/env bash
# Run the live behavioural lane so the result survives and the exit code is readable.
#
# Two traps this exists for, both hit on 2026-08-28:
#
#  1. THE EXIT CODE. `cowork-harness run … | grep …` reports grep's status, not the harness's.
#     That is how a run whose three assertions all read `pass: true` was taken for a pass while
#     the harness itself exited 1. So the status goes to its own file, never through a pipe.
#     HANDOFF-2026-08-26.md lists this among five errors that each produced "a clean, plausible,
#     wrong number".
#  2. THE 30-MINUTE CEILING. `ideas-command` runs ~27 minutes and is allowed 46. An agent-tracked
#     background command is killed at 30, mid-run, with no verdict — so this detaches with nohup.
#     A human in a terminal never meets that ceiling and loses nothing by using this anyway.
#
# `setsid` is deliberately NOT used: it does not exist on macOS, and `nohup setsid …` fails
# silently, producing no log, no process and no status file at all.
#
#   tools/run-live.sh [scenario-path ...]      # default: every scenario
set -euo pipefail

TARGET="${*:-tests/scenarios}"
OUT="${COWORK_RUN_OUT:-$(mktemp -d)}"
ENVFILE="${COWORK_DOTENV:-.env}"
LOG="$OUT/live.log"; RC="$OUT/live.rc"

[ -f "$ENVFILE" ] || { echo "no $ENVFILE — the harness injects only env/.env, never a Keychain" \
                            "credential. Mint one with: claude setup-token" >&2; exit 2; }

nohup sh -c "cowork-harness --dotenv '$ENVFILE' run $TARGET > '$LOG' 2>&1; echo \$? > '$RC'" \
      >/dev/null 2>&1 &

echo "started: $TARGET"
echo "  log:    $LOG"
echo "  status: $RC   (written when it finishes; read this, never a pipeline's exit code)"
