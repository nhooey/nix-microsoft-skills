{
  description = "nix-microsoft-skills dev-shell skill set — an isolated sub-flake invoked at RUNTIME by the root devShell, never a root input. The skill sources live only in THIS flake's lock, so the root nix-microsoft-skills stays a leaf with zero skill inputs and transitive consumers never drag the skill mesh in.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";

    # The builder lib; it carries no skill inputs.
    agent-skill-flake = {
      url = "github:nhooey/agent-skill-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Skill sources, the same repos `github:nhooey/skillspkgs` aggregates.
    # They follow `nixpkgs` but not `agent-skill-flake`, so each keeps its own
    # compatible builder.
    coding-agent-skills = {
      url = "github:nhooey/coding-agent-skills/overnight-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    git-skills = {
      url = "github:nhooey/git-skills/overnight-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-skills = {
      url = "github:nhooey/nix-skills/overnight-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    python-skills = {
      url = "github:nhooey/python-skills/overnight-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    shell-skills = {
      url = "github:nhooey/shell-skills/overnight-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # skillspkgs' curated `authoring-with-git` combination: the git/GitHub
    # pack alongside the authoring tooling (nix + humanizer + skill-creation
    # + superpowers), deduped into one consistent set. Its git and nix packs
    # follow the inputs above, so the combination and the direct sources
    # agree on one revision of each.
    skillspkgs-combinations = {
      url = "github:nhooey/skillspkgs?dir=sources/combinations";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.git-skills.follows = "git-skills";
      inputs.nix-skills.follows = "nix-skills";
    };
  };

  outputs =
    {
      nixpkgs,
      agent-skill-flake,
      ...
    }@inputs:
    agent-skill-flake.lib.mkDevshellSkillsFlake {
      inherit nixpkgs;
      systems = import inputs.systems;
      name = "nix-microsoft-skills-devshell";
      sources = [
        # Commits, branches and pull requests, plus writing skills and this
        # flake: git/GitHub hygiene, nix-flakes, humanizer, skill-creator and
        # superpowers.
        { source = inputs.skillspkgs-combinations.combinations.authoring-with-git; }
        # Safe shell commands: named deletes, PIDs, no machine-wide changes.
        { source = inputs.shell-skills; }
        # The skill checker in scripts/ is Python.
        { source = inputs.python-skills; }
        # Running as a headless session in a checkout, keeping the scratchpad
        # tidy, and the cross-repository plan's graph.
        {
          source = inputs.coding-agent-skills;
          skills = [
            "coding-agent-headless-in-checkout"
            "coding-agent-plans-as-graph"
            "coding-agent-scratchpad-scripts"
          ];
        }
      ];
    };
}
