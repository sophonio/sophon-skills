# Plugins

This directory is reserved for **Sophon plugins**. No plugins live here yet — it is scaffolded so
plugins have a home when the first one is built.

## Skills vs. plugins

- A **skill** (`skills/<name>/`) is sandboxed code with a `manifest.json` declaring tools. Packaged
  as `<name>-<version>.sophon-skill` by `build/Build-MarketplacePackages.ps1`.
- A **plugin** is a compiled **.NET gRPC** component that extends Sophon at a defined interface —
  `pluginInterface` ∈ `ChannelAdapter`, `ModelProvider`, `VaultBackend`, `DocumentExtractor`,
  `EmbeddingProvider`, `Tool`. It is packaged as `<name>-<version>.sophon-plugin`: the same manifest
  contract plus `"type": "plugin"` + `pluginInterface`, and the archive must contain a `publish/`
  directory with at least one `.dll`.

## Scaffolds

Contributor starting points are under [`../templates/`](../templates):
`plugin-channel`, `plugin-model-provider`, `plugin-vault-backend`, `plugin-document-extractor`.

## Building plugin packages

The `.sophon-plugin` build path is compiled (dotnet) and **not** handled by
`build/Build-MarketplacePackages.ps1`, which packages skills only. A plugin build/package step will
be added here alongside the first plugin. The Marketplace upload flow
([`../docs/PUBLISHING.md`](../docs/PUBLISHING.md)) is otherwise identical — same `POST /api/v1/publish`
endpoint and `smk_` key; `Publish-MarketplacePackages.ps1` already uploads `.sophon-plugin`
artifacts if present in `dist/`.
