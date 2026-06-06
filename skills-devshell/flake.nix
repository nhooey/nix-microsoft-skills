{
  description = "nix-microsoft-skills dev-shell skill set — an isolated sub-flake invoked at RUNTIME by the root devShell, never a root input. The skill sources live only in THIS flake's lock, so the root nix-microsoft-skills stays a leaf with zero skill inputs and transitive consumers never drag the skill mesh in. The set is skillspkgs' curated authoring-with-git combination: the git/GitHub hygiene pack plus the authoring tooling, deduped into one consistent set.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";

    agent-skill-flake = {
      url = "github:nhooey/agent-skill-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # The lone skill source: skillspkgs' curated `authoring-with-git`
    # combination — the git/GitHub pack alongside the authoring tooling
    # (nix + humanizer + skill-creation + superpowers), deduped into one
    # consistent set. Surfaced through its own subdir flake so it stays
    # re-composable as a source. Splicing the raw git pack + the `authoring`
    # combination as two separate sources is equivalent in membership, but
    # the raw pack also carries `agent-skills-*-all` aggregate keys that the
    # builder's per-skill sift mis-reads (`agent-skill-` is a string prefix
    # of `agent-skills-`); the pre-deduped combination has clean per-skill
    # keys only, so this is the supported single-source shape.
    skillspkgs-combinations = {
      url = "github:nhooey/skillspkgs?dir=sources/combinations";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      nixpkgs,
      agent-skill-flake,
      skillspkgs-combinations,
      ...
    }@inputs:
    agent-skill-flake.lib.mkDevshellSkillsFlake {
      inherit nixpkgs;
      systems = import inputs.systems;
      name = "nix-microsoft-skills-devshell";
      sources = [
        { source = skillspkgs-combinations.combinations.authoring-with-git; }
      ];
    };
}
