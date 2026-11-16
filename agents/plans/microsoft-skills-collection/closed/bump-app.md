---
title: bump app refreshes pins one commit per upstream repository
state: implemented
kind: implementation
part-of: microsoft-skills-collection
implemented-by: ab42396
touches: [flake.nix, scripts/bump.sh]
---

# `bump` app refreshes pins one commit per upstream repository

`apps.bump` runs `scripts/bump.sh`, formatted by `shfmt`, which:

1. reads each pinned rev from `skills/default.nix` with `nix eval`;
2. calls `gh api repos/<owner>/<repo>/commits/<defaultBranch>` once per
   upstream repository, not once per skill;
3. prints each repository's old and new short rev and how many skills it
   carries, or that it is up to date;
4. with `--apply`, rewrites the rev and hash (hash from
   `nix flake prefetch`) and makes one commit per upstream repository,
   subject `chore(deps): bump <owner>/<repo> to <new-short>`, with the
   affected skills in the body.

Bumping is explicit: nothing refreshes pins on a build.

## Check

1. `nix run .#bump` reaches every upstream repository and changes no file.
2. `nix run .#bump -- --apply` on a stale pin makes exactly one commit per
   upstream repository.
