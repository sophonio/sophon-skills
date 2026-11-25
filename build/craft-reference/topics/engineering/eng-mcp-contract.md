---
id: eng-mcp-contract
summary: Per-tool contract questions, schema and error conventions with examples, the ten-question evaluation file format.
reviewed: 2026-11
---
# MCP tool contracts and the evaluation set

A tool is judged by whether a model that has only its name, description and schema can finish a real task with it.

## Tool contract

| Item | Question | Example |
|---|---|---|
| name | service prefix, verb, resource, snake_case? | `tracker_list_issues`, `tracker_close_issue` |
| title | short and human-readable? | "List issues" |
| description | what it does, what it returns, when a sibling tool fits better, one example request? | "Lists issues in one project, newest first. For a single issue by key use tracker_get_issue." |
| inputs | every field typed, bounded, described, with defaults stated? | `limit` integer 1-100, default 20 |
| scope | the smallest set of objects this tool can touch? | one project id, not "all projects" |
| reads and writes | separate tools? | `tracker_get_issue` and `tracker_update_issue` |
| destructive | one exact id per call; the description says it deletes or overwrites? | `tracker_delete_comment(comment_id)` |
| annotations | readOnlyHint, destructiveHint, idempotentHint, openWorldHint set to what the tool really does? | a list tool: read-only true, idempotent true |
| server checks | ownership, bounds and allowed values checked in code on every call, whatever the description says? | the project id is matched to the caller's account |
| outbound URLs | listed schemes and hosts only; private addresses refused after DNS and after each redirect? | an attachment fetcher |

## Schemas and errors

| Convention | Form |
|---|---|
| enums | a closed list of strings for any field with known values |
| dates | ISO 8601 strings; the description names the time zone |
| ids | strings, with the format in the description ("issue key such as ABC-123") |
| lists | input `limit` and `offset` or `cursor`; output `total`, `count`, `has_more`, `next_offset` or `next_cursor` |
| response format | `response_format`: `markdown` (default, readable dates, names with ids in parentheses) or `json` (every field) |
| structured output | `outputSchema` and `structuredContent` only for tools that always return JSON |
| size | results kept under about 25,000 characters by returning fewer items, never by cutting text mid-item |
| errors | a tool result with `isError: true` and one sentence: what failed and the next step |

Error sentences that help: "Project 'web' not found; call tracker_list_projects for valid ids." "Rate limit reached; retry after 60 s." "limit must be 1-100; got 500." Sentences that do not: a stack trace, "Error 500", "Something went wrong".

## Evaluation set

The file holds ten question and answer pairs:

```xml
<evaluation>
  <qa_pair>
    <question>In project WEB, which closed issue labelled "regression" had the most comments in March 2025? Give its key.</question>
    <answer>WEB-1182</answer>
  </qa_pair>
</evaluation>
```

| Property | A question has it when |
|---|---|
| independent | it does not need the answer to another question |
| read-only | answering it changes no data |
| multi-hop | it takes several calls, such as list, filter, then get |
| not a keyword lookup | the answer is not found by one search for words in the question |
| realistic | a real user of the service could ask it |
| stable | it uses closed or historical data and fixed date ranges, never a live count |
| verifiable | one value, compared as an exact string, with its format given in the question |

Weak: "How many open issues are there?" (changes every day). Weak: "What is issue WEB-1?" (one call). Stronger: "Which user closed the most issues in project WEB during Q4 2024? Give the username."
