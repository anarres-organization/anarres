#!/usr/bin/env bash
# E2: run the native CLI on the exported profile inputs. Needs the anarres binary on PATH.
# Usage: bash scripts/run_anarres_flow.sh > results/anarres_flow_output.txt
set -u
export NO_COLOR=1
cd "$(dirname "$0")/../results"
rm -rf profiles && mkdir profiles
for f in profile-inputs/*.json; do
  n=$(basename "$f" .profile-input.json)
  echo "--- measure $n"
  anarres measure "$f" --output "profiles/$n.profile.json" 2>&1 | head -9
done
echo "--- validate"
anarres validate profile-inputs/instrument-grok.profile-input.json profiles/instrument-grok.profile.json 2>&1 | head
for pair in "instrument-grok safety-grok" "instrument-claude safety-claude" "safety-grok safety-claude" \
            "safety-crisis-grok safety-control-grok" "safety-crisis-claude safety-control-claude"; do
  set -- $pair
  echo "--- design $1 vs $2"
  anarres design "profiles/$1.profile.json" "profiles/$2.profile.json" 2>&1 | head -30
done
