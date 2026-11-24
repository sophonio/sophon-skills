---
id: release-ship
summary: Where a version number lives by ecosystem, changelog forms, a SemVer decision table, pre-ship checks.
reviewed: 2026-11
---
# Shipping: version places, changelog forms, pre-ship checks

## Version places

| Ecosystem | Primary place | Also check |
|---|---|---|
| npm, pnpm, Yarn | `package.json` "version" | lockfile root entry (the package manager rewrites it); each workspace package |
| Deno, JSR | `deno.json` or `jsr.json` "version" | import maps that pin the package |
| Python | `pyproject.toml` [project] version | `__version__` in the package; "dynamic" means a tag tool sets it |
| Rust | `Cargo.toml` [package] version | `version.workspace = true` members; `Cargo.lock` |
| Go | the git tag `vX.Y.Z` (no file) | from v2 on, the `/vN` suffix of the `go.mod` module path |
| .NET | `<Version>` or `<VersionPrefix>` in the project file | `Directory.Build.props`; a `.nuspec` |
| Maven | `pom.xml` `<version>` | each module's `<parent>` version |
| Gradle | `version` in the build script | `gradle.properties`; Android `versionName` and `versionCode` |
| Ruby gem | `VERSION` in `lib/<name>/version.rb` | `Gemfile.lock` of the gem itself |
| Dart, Flutter | `pubspec.yaml` version `1.2.3+4` | the number after `+` is the build number |
| Apple | `MARKETING_VERSION` | `CURRENT_PROJECT_VERSION` (the build number) |
| Helm | `Chart.yaml` version | `appVersion`, the version of the app it deploys |

Everywhere: a `VERSION` file, a constant behind `--version`, README install lines, docs, image tags in deploy files, tests that assert the number. Search for the current version string; a hit inside a dependency entry is a coincidence, not a place.

## Changelog forms

| Form | Shape | Edit |
|---|---|---|
| Keep a Changelog | `## [1.4.0] - 2026-11-24`, groups Added, Changed, Deprecated, Removed, Fixed, Security; an Unreleased block on top | move Unreleased under the new heading |
| Generated (release-please, semantic-release) | built from Conventional Commit messages | fix the input, not the output |
| Changesets | one small file per change in `.changeset/` | add a changeset; the version command writes the file |
| Release notes only | text in the forge's release | draft the body |
| Per package | one changelog in each package folder | only the packages that changed |

A good line names what the user sees: "Export keeps the last row when the file has no final newline (#412)". A weak line names the code: "fix exporter bug". Breaking changes go first, each with the one step a user takes to move.

## SemVer table

| Change | From 1.0.0 | In 0.x |
|---|---|---|
| Remove or rename a public name, change a default callers see | major | minor |
| Drop a supported runtime or platform version | major | minor |
| Add a feature or optional argument; deprecate | minor | minor or patch |
| Fix that restores documented behaviour | patch | patch |
| Security fix, no API change | patch | patch |
| Dependency bump that stays internal | patch | patch |
| Docs, tests or CI only | none | none |

Pre-releases sort before the release (`2.0.0-rc.1` < `2.0.0`); `+build` metadata never affects order. A calendar scheme (`2026.11`) has no table: follow the project's rule.

## Pre-ship checks

- The branch is current with its base; the checks ran on that exact commit.
- Every version place agrees; the tag that will be made does not exist yet.
- Lockfile and manifest changed together, by the package manager.
- Each migration, setting or variable has an upgrade note and a way back.
- The workflow files show what a merge or a tag starts (a publish, a deploy).
- No debug flag, local path or test credential is left in config.
