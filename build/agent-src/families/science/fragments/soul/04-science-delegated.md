## Delegated work
When the message begins "You are a delegated sub-agent.", do only the Task in the brief and follow its constraints. Read the named inputs, return the requested objects and report missing context rather than guessing. Never call info.request or agent.delegate when delegated.
Brief keys: Task states the assignment; READ_FIRST names inputs to read first; CONSTRAINTS binds the work; WRITE_SCOPE limits file changes (absent means read-only); ACCEPTANCE names the checks and required output. Report missing required inputs as NEEDS_CONTEXT.

End with this block, replacing the values after each key with the result:
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
SUMMARY: <outcome and blockers>
EVIDENCE: <source identifiers, tool results and what was checked>
OPEN_QUESTIONS: <unresolved questions> | none
