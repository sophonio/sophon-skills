## Design source
For interface work, the first source that exists decides the look.
1. The user's words, or the brief's DESIGN key (a file, "sophon-default" or "plain").
2. The project's own system: `DESIGN.md` at the repository root or the file an AGENTS.md "Design rules" line names, then the token or theme file, then the component library, then the styles its screens already use. Extend it; restyle it only when asked. A system someone chose is never a "default look".
3. Neither exists: the user chooses. UI/UX Designer runs its direction round; every other role asks once, header "Design": [Sophon design default (Recommended)] [Plain standard] [Direction round]. Plain is the platform's or component library's stock look; the round is UI/UX Designer's.
- Before the pick, nothing from an option reaches a project file. No answer applies nothing: do what needs no look and report the look as open.
- "Just build it" removes discovery questions, never this one.
- Delegated to build with no DESIGN key and no project system: build nothing; return your options as text with STATUS NEEDS_CONTEXT.
