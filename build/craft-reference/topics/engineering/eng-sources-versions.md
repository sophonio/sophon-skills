---
id: eng-sources-versions
summary: Where the declared and resolved version lives per ecosystem, a source ranking, and where changelogs are kept.
reviewed: 2026-11
---
# Sources and versions: where the version lives, by ecosystem

## Version in use

The declared range says what is allowed; the lockfile says what is installed.

| Ecosystem | Declared | Resolved | Runtime pin |
|---|---|---|---|
| npm, pnpm, Yarn | `package.json` | `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock` | `.nvmrc`, `engines`, `packageManager` |
| Python | `pyproject.toml`, `requirements*.txt` | `poetry.lock`, `uv.lock`, pinned requirements | `.python-version`, `requires-python` |
| .NET | `*.csproj`, `Directory.Packages.props` | `packages.lock.json`, `obj/project.assets.json` | `global.json`, `TargetFramework` |
| Go | `go.mod` | `go.sum` plus `go.mod` | the `go` and `toolchain` lines |
| Rust | `Cargo.toml` | `Cargo.lock` | `rust-toolchain.toml` |
| Java, Kotlin | `pom.xml`, `build.gradle(.kts)`, `libs.versions.toml` | `gradle.lockfile`, or the resolved dependency tree | `.java-version`, toolchain block |
| Ruby | `Gemfile` | `Gemfile.lock` | `.ruby-version` |
| PHP | `composer.json` | `composer.lock` | `config.platform.php` |

A monorepo can hold several lockfiles; the one nearest the code in question applies. `.tool-versions` pins runtimes for several languages at once.

## Source ranking

1. The package's own source or type definitions at the installed version, inside the project's dependency folder.
2. Official documentation for that version (versioned docs, not the latest page).
3. The changelog or release notes between the version in use and the one described.
4. The standard or specification the package implements.
5. Issue trackers of the project: for known bugs, with the version they name.

Blog posts, forum answers, tutorials and generated summaries are leads to check against 1 to 4.

## Changelogs

`CHANGELOG.md`, `HISTORY.md` or `NEWS` at the repository root; the project's GitHub releases page; a "migration" or "upgrading" page in the docs for major versions; the package registry's release notes.
