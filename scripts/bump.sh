#!/usr/bin/env bash
# Compare each pinned upstream rev in pins.nix to GitHub HEAD.
#
#   bump            read-only — print "<repo>: <old> → <new> (<N skills>)"
#                   per behind upstream, or "<repo>: up to date".
#   bump --apply    rewrite revs + hashes in place, one commit per repo.

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

apply=0
case "${1:-}" in
--apply) apply=1 ;;
-h | --help)
  sed -n '2,7p' "$0"
  exit 0
  ;;
"") ;;
*)
  echo "unknown arg: $1" >&2
  exit 2
  ;;
esac

# Under `nix run`, the script lives in the store; the repo root is the
# user's cwd. Confirm via `git rev-parse` so we fail clearly if the user
# invoked us from outside a clone.
if ! repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "bump must be run from inside a clone of nix-microsoft-skills" >&2
  exit 1
fi
pins_file=$repo_root/pins.nix

if [[ ! -f $pins_file ]]; then
  echo "pins file not found: $pins_file" >&2
  echo 'run `skills-dev bump` from a clone of nix-microsoft-skills' >&2
  exit 1
fi

# Extract pins as JSON via `nix eval`. One eval call covers every repo and
# every skill — cheaper and simpler than re-parsing the Nix file by hand.
pins_json=$(nix eval --json --impure --expr \
  "let p = import \"$pins_file\"; in {
     repos = p.repos;
     skillsByRepo = builtins.mapAttrs
       (repoKey: _:
         builtins.filter
           (n: p.skills.\${n}.repo == repoKey)
           (builtins.attrNames p.skills))
       p.repos;
   }")

repo_keys=$(jq -r '.repos | keys[]' <<<"$pins_json")

behind=0
for key in $repo_keys; do
  owner=$(jq -r ".repos[\"$key\"].owner" <<<"$pins_json")
  repo=$(jq -r ".repos[\"$key\"].repo" <<<"$pins_json")
  old_rev=$(jq -r ".repos[\"$key\"].rev" <<<"$pins_json")
  old_hash=$(jq -r ".repos[\"$key\"].hash" <<<"$pins_json")
  branch=$(jq -r ".repos[\"$key\"].defaultBranch" <<<"$pins_json")
  skills_for_repo=$(jq -r ".skillsByRepo[\"$key\"][]" <<<"$pins_json" | sort)
  n_skills=$(printf '%s\n' "$skills_for_repo" | wc -l | tr -d ' ')

  new_rev=$(gh api "repos/$owner/$repo/commits/$branch" --jq .sha)
  if [[ -z $new_rev || $new_rev == "null" ]]; then
    echo "ERROR: could not resolve $owner/$repo@$branch HEAD" >&2
    exit 1
  fi

  if [[ $new_rev == "$old_rev" ]]; then
    echo "$owner/$repo: up to date (${old_rev:0:7})"
    continue
  fi

  behind=$((behind + 1))
  echo "$owner/$repo: ${old_rev:0:7} → ${new_rev:0:7} ($n_skills skill(s))"

  if [[ $apply -eq 1 ]]; then
    prefetch_json=$(nix flake prefetch \
      "github:$owner/$repo/$new_rev" --json --refresh)
    new_hash=$(jq -r .hash <<<"$prefetch_json")

    # Rewrites only the rev / hash lines inside this repo's `<key> = { ... }`
    # block; see rewrite_pin.py.
    python3 "$script_dir/rewrite_pin.py" \
      "$pins_file" "$key" "$old_rev" "$new_rev" "$old_hash" "$new_hash"

    # Commit per repo, listing affected skills in the body so the
    # diff stays a one-line rev change but the impact is recoverable
    # from `git log`.
    skills_block=$(printf '%s\n' "$skills_for_repo" | sed 's/^/  - /')
    commit_msg=$(
      cat <<EOF
chore(deps): bump $owner/$repo to ${new_rev:0:7}

Was: $old_rev
Now: $new_rev

Skills refreshed from this upstream:
$skills_block
EOF
    )
    (cd "$repo_root" && git add "$pins_file" &&
      git commit -m "$commit_msg")
  fi
done

if [[ $apply -eq 0 && $behind -gt 0 ]]; then
  echo
  echo "$behind upstream(s) behind. Re-run with --apply to bump."
fi
