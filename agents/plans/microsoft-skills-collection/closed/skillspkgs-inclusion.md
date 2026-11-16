---
title: Collection included in skillspkgs
state: implemented
kind: implementation
part-of: microsoft-skills-collection
---

# Collection included in `skillspkgs`

`nhooey/skillspkgs` takes this repository as the flake input
`nix-microsoft-skills`, in its root flake and in
`sources/aggregated/flake.nix`.

## Check

`skillspkgs`'s `flake.nix` has a `nix-microsoft-skills` input pointing at
`github:nhooey/nix-microsoft-skills`.
