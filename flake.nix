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

    # The skill builder library (zero skill inputs). Used both to BUILD this
    # repo's own output skills (`lib.mkSkillFlake`) and, via
    # `flakeModules.devshellSkills`, to wire the root dev shell to the runtime
    # `skills-devshell/` sub-flake. That module bundles numtide/devshell, so
    # this flake needs no `devshell` input of its own.
    agent-skill-flake = {
      url = "github:nhooey/agent-skill-flake";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.systems.follows = "systems";
      inputs.flake-parts.follows = "flake-parts";
      inputs.treefmt-nix.follows = "treefmt-nix";
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      flake-parts,
      systems,
      ...
    }@inputs:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = import systems;
      imports = [
        # Bundles numtide/devshell + the whole dev-shell skills convention
        # (motd, install-skills startup, the ci/dev/maintenance command trio,
        # and the reap-skills/update-skills-devshell pair). Configured via the
        # `agent-skill-flake.devshellSkills` options block below.
        inputs.agent-skill-flake.flakeModules.devshellSkills
        inputs.treefmt-nix.flakeModule
      ];

      # nix-microsoft-skills keeps its custom motd ("Run menu …"); the module's
      # generated banner is overridden by passing `motd` here.
      agent-skill-flake.devshellSkills = {
        name = "nix-microsoft-skills";
        motd = ''
          {bold}{14}nix-microsoft-skills{reset}
          Run {bold}menu{reset} to list available commands.
        '';
      };

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

          # Build one skill via agent-skill-flake.lib.mkSkillFlake and return
          # a { key; drv; } pair where `key` is the lib's own namespaced
          # attribute key (agent-skill-<owner>-<name>) so downstream
          # aggregators see a consistent prefix and bare names never leak.
          mkOne =
            name: pin:
            let
              repoCfg = pins.repos.${pin.repo};
              repoSrc = repoSrcs.${pin.repo};
              skillSrc = "${repoSrc}/${pin.srcSubdir}";
              flake = inputs.agent-skill-flake.lib.mkSkillFlake {
                inherit (inputs) nixpkgs;
                skillName = name;
                src = skillSrc;
                inherit (pin) description;
                systems = [ system ];
                # Hand the upstream repo coords to the builder so the lib can
                # derive the owner-namespaced package key
                # (`agent-skill-<owner>-<name>`) we pick up below.
                source = {
                  inherit (repoCfg) owner repo rev;
                };
              };
              # The lib hands back its canonical namespaced key
              # (agent-skill-<owner>-<name>) as `passthru.packageKey`, so we
              # re-key by it directly instead of rediscovering the convention.
              base = flake.packages.${system}.default;
            in
            {
              key = base.packageKey;
              drv = base.overrideAttrs (old: {
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
            };

          skillDrvs = lib.listToAttrs (
            lib.map (pair: lib.nameValuePair pair.key pair.drv) (
              lib.attrValues (lib.mapAttrs mkOne pins.skills)
            )
          );

          all = pkgs.symlinkJoin {
            name = "agent-skills-nix-microsoft-skills-all";
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
        in
        {
          packages = skillDrvs // {
            agent-skills-nix-microsoft-skills-all = all;
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

          # The devshellSkills module (imported above) supplies this devShell's
          # name, motd, the install-skills startup, the ci/dev/maintenance
          # command trio (check / fmt / update-flake), and the skills commands
          # (reap-skills / update-skills-devshell). Only nix-microsoft-skills'
          # own packages and the deps/bump command are set here; both are list
          # options, so they merge onto the module's rather than replacing them.
          devshells.default = {
            packages = [
              pkgs.gh
              pkgs.jq
              pkgs.nixfmt
              pkgs.shfmt
              pkgs.shellcheck
              pkgs.python3
            ];
            commands = [
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
