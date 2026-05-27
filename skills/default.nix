# Single source of truth for every upstream pin in this collection.
#
# Shape:
#   repos.<key>  = { owner; repo; rev; hash; defaultBranch; }
#                  — fetched once per (rev, hash) so 8 wshaddix skills
#                    share one tarball.
#   skills.<name> = { repo; srcSubdir; description; }
#                  — `repo` is a key into `repos`.
#
# The `bump` script reads this file to compare each pinned rev to its
# upstream HEAD (via `gh api`). One commit per repo on `--apply`.

{
  repos = {
    wshaddix-dotnet-skills = {
      owner = "wshaddix";
      repo = "dotnet-skills";
      rev = "09da68dc1f3c06f3bde05f49a6301c75478ab123";
      hash = "sha256-ezxw010Iy92/x39zQgfbOlVX++UcY64IIqzaPItrvFU=";
      defaultBranch = "master";
    };
    managedcode-dotnet-skills = {
      owner = "managedcode";
      repo = "dotnet-skills";
      rev = "3e19aaaa768f65db4152849dafc6817fd9b1815c";
      hash = "sha256-vJ6Zwcn+iEhCF6FGdZMOu4fZy8O1krscIuz5aLAYO48=";
      defaultBranch = "main";
    };
    peterblazejewicz-claude-plugins = {
      owner = "peterblazejewicz";
      repo = "claude-plugins";
      rev = "47004879a09142cdcfbb27d18f791c05e2cc967c";
      hash = "sha256-uqho7gyAEiN0c8lPbTZUIxO80f0K8LCltpuoq/t6DMQ=";
      defaultBranch = "main";
    };
  };

  skills = {
    csharp-concurrency-patterns = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/csharp-concurrency-patterns";
      description = "C# concurrency patterns: locks, async coordination, thread safety";
    };
    dotnet-csharp-async-patterns = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-csharp-async-patterns";
      description = ".NET / C# async patterns: Task, ValueTask, cancellation, async streams";
    };
    dotnet-csharp-modern-patterns = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-csharp-modern-patterns";
      description = "Modern C# language features and idioms";
    };
    dotnet-csproj-reading = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-csproj-reading";
      description = "Reading and interpreting .NET .csproj files";
    };
    dotnet-editorconfig = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-editorconfig";
      description = "Authoring .editorconfig for .NET projects";
    };
    dotnet-solution-navigation = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-solution-navigation";
      description = "Navigating .NET solution / project structure";
    };
    dotnet-xunit = {
      repo = "wshaddix-dotnet-skills";
      srcSubdir = "skills/dotnet-xunit";
      description = "Writing tests with xUnit.net";
    };
    managedcode-convert-to-cpm = {
      repo = "managedcode-dotnet-skills";
      srcSubdir = "catalog/Tools/Official-DotNet-NuGet/skills/convert-to-cpm";
      description = "Convert a .NET solution to Central Package Management (CPM)";
    };
    avalonia-dev-review = {
      repo = "peterblazejewicz-claude-plugins";
      srcSubdir = "plugins/avalonia-dev/skills/review";
      description = "Avalonia UI developer review skill";
    };
    frontend-ui-engineering-avalonia = {
      repo = "peterblazejewicz-claude-plugins";
      srcSubdir = "plugins/dotnet-skills/skills/frontend-ui-engineering-avalonia";
      description = "Frontend UI engineering for Avalonia";
    };
  };
}
