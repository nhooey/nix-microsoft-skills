---
title: Default branch protected by a ruleset
state: implemented
kind: implementation
part-of: microsoft-skills-collection
---

# Default branch protected by a ruleset

The repository's default branch has an active Rulesets-API ruleset, as
`github-policy-protect-default-branch` describes: pull request required,
required status checks, no force-push, no deletion, admins included.

## Check

`gh api repos/nhooey/nix-microsoft-skills/rulesets` lists an active
`default-branch-protection` ruleset.
