{
  description = "nix-microsoft-skills: Claude Code skills for the Microsoft / .NET stack, packaged as a Nix flake";

  inputs = {
    # Rolling unstable: skills are content, not built artifacts, so we want
    # the most recent treefmt / nixfmt / shellcheck without waiting for the
    # next NixOS release. Pin a release branch instead if reproducibility
    # across years matters more than tool recency.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    systems.url = "github:nix-systems/default";

    devshell = {
      url = "github:numtide/devshell";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    flake-skills = {
      url = "github:nhooey/flake-skills";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # The skills-git pack installed at project scope on `nix develop`, via
    # its `reconcileScript` (matching skills-git's own dev shell idiom).
    skills-git = {
      url = "github:nhooey/skills-git";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-skills.follows = "flake-skills";
      };
    };

    # skillspkgs' curated `authoring` combination (nix-*, humanizer,
    # skill-creator, superpowers). Pulled at `?dir=sources/combinations` so
    # only the combination-builder eval is fetched, not the full skillspkgs
    # tree.
    skillspkgs-combinations = {
      url = "github:nhooey/skillspkgs?dir=sources/combinations";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-skills.follows = "flake-skills";
      };
    };
  };

  outputs =
    { flake-parts, systems, ... }@inputs:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = import systems;
      imports = [
        inputs.devshell.flakeModule
        inputs.treefmt-nix.flakeModule
      ];

      perSystem =
        {
          pkgs,
          system,
          lib,
          ...
        }:
        let
          pins = import ./skills/default.nix;

          # Memoize per-repo fetches: one tarball per unique (owner, repo,
          # rev), shared across every skill that pins to it.
          repoSrcs = lib.mapAttrs (
            _: cfg:
            pkgs.fetchFromGitHub {
              inherit (cfg)
                owner
                repo
                rev
                hash
                ;
            }
          ) pins.repos;

          # Build one skill via flake-skills.lib.mkSkillFlake and return
          # just the derivation (the lib also returns apps/install scaffolding
          # that this consumer-agnostic collection doesn't expose).
          mkOne =
            name: pin:
            let
              repoCfg = pins.repos.${pin.repo};
              repoSrc = repoSrcs.${pin.repo};
              skillSrc = "${repoSrc}/${pin.srcSubdir}";
              flake = inputs.flake-skills.lib.mkSkillFlake {
                inherit (inputs) nixpkgs;
                skillName = name;
                src = skillSrc;
                inherit (pin) description;
                systems = [ system ];
              };
            in
            (flake.packages.${system}.default).overrideAttrs (old: {
              meta = (old.meta or { }) // {
                homepage = "https://github.com/${repoCfg.owner}/${repoCfg.repo}/tree/${repoCfg.rev}/${pin.srcSubdir}";
              };
              passthru = (old.passthru or { }) // {
                upstream = {
                  inherit (repoCfg) owner repo rev;
                  inherit (pin) srcSubdir;
                };
              };
            });

          skillDrvs = lib.mapAttrs mkOne pins.skills;

          all = pkgs.symlinkJoin {
            name = "nix-microsoft-skills-all";
            paths = lib.attrValues skillDrvs;
          };

          # Asserts the aggregate shape that every downstream relies on:
          # 10 directories, each with a top-level SKILL.md whose YAML
          # frontmatter parses, carries `name:`, and matches the directory.
          # Silent corruption is worse than a noisy failure here.
          skillsValid =
            pkgs.runCommand "skills-valid"
              {
                nativeBuildInputs = [ pkgs.python3 ];
                inherit all;
                expectedCount = toString (lib.length (lib.attrNames pins.skills));
                expected = lib.concatStringsSep "\n" (lib.attrNames pins.skills);
              }
              ''
                python3 ${./scripts/check-skills.py} \
                  "$all/share/claude-skills" \
                  "$expectedCount" \
                  <(printf '%s\n' "$expected" | sort)
                touch $out
              '';

          # The dev shell's full skill set as one combination: the skills-git
          # pack plus skillspkgs' `authoring` combination spliced in as a
          # source. One reconcile hook converges the union under one owner.
          devShellSkills = inputs.flake-skills.lib.mkCombination {
            inherit (inputs) nixpkgs;
            systems = [ system ];
            name = "nix-microsoft-skills-devshell";
            packagePrefix = "agent-skill-";
            sources = [
              { source = inputs.skills-git; }
              { source = inputs.skillspkgs-combinations.combinations.authoring; }
            ];
          };
        in
        {
          packages = skillDrvs // {
            inherit all;
            default = all;
          };

          checks = {
            skills-valid = skillsValid;
          }
          // (lib.mapAttrs' (n: v: lib.nameValuePair "skill-${n}" v) skillDrvs);

          treefmt = {
            projectRootFile = "flake.nix";
            programs.nixfmt.enable = true;
            programs.shfmt.enable = true;
          };

          # Auto-reconcile skills at project scope on `nix develop`: the
          # skills-git pack plus skillspkgs' curated `authoring` combination,
          # merged into one combination that a single reconcile hook converges
          # — one owner, declarative + idempotent.
          devshells.default = {
            name = "nix-microsoft-skills";
            motd = ''
              {bold}{14}nix-microsoft-skills{reset}
              Run {bold}menu{reset} to list available commands.
            '';
            devshell.startup.install-skills.text = ''
              ${devShellSkills.reconcileScript system}
            '';
            packages = [
              pkgs.gh
              pkgs.jq
              pkgs.nixfmt
              pkgs.shfmt
              pkgs.shellcheck
              pkgs.python3
            ];
            commands = [
              # ci
              {
                category = "ci";
                name = "check";
                help = "Run nix flake check (treefmt + skills-valid + per-skill builds)";
                command = "nix flake check \"$@\"";
              }
              {
                category = "ci";
                name = "fmt";
                help = "Format the tree via treefmt (nixfmt + shfmt)";
                command = "nix fmt \"$@\"";
              }
              # deps
              {
                category = "deps";
                name = "bump";
                help = "Compare pinned upstream revs to GitHub HEAD; pass --apply to rewrite";
                command = "nix run .#bump -- \"$@\"";
              }
            ];
          };

          apps.bump = {
            type = "app";
            meta.description = "Compare pinned upstream revs to GitHub HEAD; rewrite with --apply";
            program = toString (
              pkgs.writeShellApplication {
                name = "bump";
                runtimeInputs = [
                  pkgs.bash
                  pkgs.coreutils
                  pkgs.gh
                  pkgs.jq
                  pkgs.nix
                ];
                text = ''
                  exec bash ${./scripts/bump.sh} "$@"
                '';
              }
              + "/bin/bump"
            );
          };
        };
    };
}
