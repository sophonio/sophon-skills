# Jira Service Management Skill

Atlassian Jira Service Management (JSM) integration for Sophon — browse service desks and request
types, work agent queues, read customer requests and their SLAs, create requests, comment, and
answer approvals. Uses the Service Desk API (`/rest/servicedeskapi`) with Basic auth (Atlassian
account email + API token). For platform Jira issues (JQL search, projects, generic issues) use the
separate `jira` skill.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `jsm.list_service_desks` | None | List service desks, or the request types of one desk when `serviceDeskId` is given |
| `jsm.list_queue_issues` | None | List a desk's queues, or the issues in a queue (requires a licensed JSM agent seat) |
| `jsm.get_request` | None | Get a customer request: status, request type, reporter, participants |
| `jsm.get_request_slas` | None | Get a request's SLA cycles: breached flag, remaining time |
| `jsm.create_request` | Medium | Create a customer request (optionally on behalf of a customer) |
| `jsm.add_request_comment` | Medium | Comment on a request (internal by default; `public: true` for customer-visible) |
| `jsm.answer_approval` | High | Approve or decline a pending approval (connection account must be the assigned approver) |

## Setup

1. Create an Atlassian API token at https://id.atlassian.com/manage-profile/security/api-tokens
   while signed in as the account you want the skill to act as.
2. Note: Atlassian API tokens now **expire** (maximum lifetime 1 year). Set a rotation reminder and
   update the connection with a fresh token before the old one lapses.
3. Make sure that account has access to your JSM projects:
   - Queue tools (`jsm.list_queue_issues`) require a **licensed JSM agent seat** on the project —
     a plain customer or unlicensed account gets a permissions error.
   - `jsm.answer_approval` only succeeds when the account is the **assigned approver** on the
     request's pending approval.
   - `raiseOnBehalfOf` on `jsm.create_request` requires agent permissions on the service desk.
4. Go to **Settings > Connections** in the Sophon Dashboard and click **Connect** on the
   Jira Service Management card.
5. Enter your Atlassian Cloud URL (e.g. `https://yourorg.atlassian.net`), the account email, and
   the API token, then test the connection.

## Usage Examples

**Discover desks and request types:**
> "List our JSM service desks, then show the request types for the IT desk"

**Work the queue:**
> "Show me the open issues in the 'Waiting for support' queue of service desk 1"

**Check an SLA:**
> "Is ITS-42 close to breaching its time-to-resolution SLA?"

**Raise a request:**
> "Create an IT help request: laptop battery swelling, raise it on behalf of dana@acme.com"

**Answer an approval:**
> "Approve the pending hardware approval on ITS-42"

## Requirements

- Atlassian Cloud site with a Jira Service Management project (any JSM plan)
- An Atlassian account + API token; the account's role determines what works:
  customer accounts can create/view their own requests, agent seats unlock queues and
  on-behalf-of, approvers can answer approvals
- API tokens expire (max 1 year) — plan rotation

## Trademarks

Jira and Jira Service Management are trademarks of Atlassian Pty Ltd. This skill is an independent
integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by
Atlassian.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
