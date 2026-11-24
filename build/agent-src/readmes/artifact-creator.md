# Artifact Creator

Artifact Creator turns a brief and available evidence into reports, explainers, feature documents, guides, diagrams and presentations across subjects. It also handles ordinary chat; a repository is not required.

## When to use

- Shape a sourced report or explainer for a particular audience.
- Create a feature guide, diagram or presentation from supplied material.
- Turn a draft into a clearer, better-structured artifact with its evidence preserved.

## How it works

It establishes the audience, purpose, format, evidence and destination; clarifies consequential ambiguities; grounds claims; structures the content; creates an actual file or canvas when tools allow; checks what it can; and revises and delivers with limitations stated. It distinguishes facts from inference and uncertainty, retains citation evidence, and does not invent sources or data. Document content is untrusted input, not instructions to the agent.

For substantial research, bring findings from a coordinator or researcher. This agent does not delegate. An installed technical-writer or visual-designer may help with specialist work; an installed frontend-developer is a better fit for interactive applications. Their availability is not assumed.

## Outputs and limits

- Output paths are non-destructive: revisions use distinct paths and identifiers. This does not promise persistent revision history. Publishing requires your approval.
- Generated imagery is opt-in. Illustrations are not evidence of real events.
- Presentations are created with complete slides and theme in a single create operation. Charts and PDF export are guidance only; edits use a separate output path.
- A document may be uploaded and presented in a canvas using its returned document id on a best-effort basis. Preview does not guarantee a download. The canvas is a user preview; the agent does not claim to see it.
- The agent distinguishes a created artifact from one structurally checked or visually inspected. It reports missing capabilities and unperformed checks. Pinned built-in file creation tool schemas have not been live tested for this package; actual availability depends on the session.

## Tools

TOOLS.md pins canvas.render, document.read, document.retrieve, document.search, document.upload, office.powerpoint, office.word and pdf in the coding profile, and the same set except document.search in the chat profile, where document.search is already a core tool. The agent checks available schemas and permissions before use. These pins do not guarantee successful file creation or downloads.

## Credits and license

Ideas re-expressed in our own words come from obra/superpowers (MIT, © 2025 Jesse Vincent) and blader/humanizer (MIT, © 2025 Siqi Chen).

Licensed under the Apache-2.0 License; see LICENSE.
