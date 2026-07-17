# Planner Skill

Microsoft Planner integration for Sophon — list plans, buckets, and tasks, read task details and
checklists, and create, update, and assign tasks in a Microsoft 365 group's basic plans via
Microsoft Graph. Uses app-only (client-credentials) authentication; task writes handle Planner's
mandatory `If-Match` ETag concurrency automatically (with one retry on edit conflicts).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `planner.list_plans` | None | List a group's Planner plans (id, title, owner) |
| `planner.list_buckets` | None | List a plan's buckets (id, name, orderHint) |
| `planner.list_tasks` | None | List tasks in a plan or bucket (title, progress, due date, assignees, priority) |
| `planner.get_task` | None | Get a task plus its description and checklist |
| `planner.create_task` | Medium | Create a task in a plan (bucket, due date, assignees optional) |
| `planner.update_task` | Medium | Update a task's title, percentComplete, dueDateTime, or bucket |
| `planner.assign_task` | Medium | Add or remove a user on a task's assignments |

## Setup

1. In the [Azure portal](https://portal.azure.com), open **Microsoft Entra ID > App registrations**
   and create (or reuse) an app registration. Note the **Application (client) ID** and
   **Directory (tenant) ID**.
2. Under **Certificates & secrets**, create a **client secret** and copy its value.
3. Under **API permissions**, add **Microsoft Graph > Application permissions**:
   - `Tasks.Read.All` — required for the read tools
   - `Tasks.ReadWrite.All` — required for `planner.create_task`, `planner.update_task`, and
     `planner.assign_task`
4. Click **Grant admin consent** for your tenant (a tenant administrator must do this — app-only
   Planner access does not work without admin consent).
   - **Warning:** `Tasks.Read.All` / `Tasks.ReadWrite.All` are **tenant-wide** application
     permissions — the app can read (and with ReadWrite, modify) the Planner plans and tasks of
     **every group in the tenant**, not just the default group you configure below. Grant them
     deliberately.
5. Find the **Microsoft 365 group ID** whose plans you want to use by default (Entra ID >
   Groups > your group > Object ID). Microsoft Graph has no app-only "list all plans" endpoint,
   so this skill discovers plans through a group; individual tools accept a `groupId` override.
6. In the Sophon Dashboard, go to **Settings > Connections**, click **Connect** on the Planner
   card, and enter the Tenant ID, Client ID, Client Secret, and Default Group ID, then test the
   connection.

## Usage Examples

**List plans:**
> "Show me the Planner plans for our team group"

**See what's in flight:**
> "List the tasks in the 'Sprint 12' plan that aren't complete yet"

**Create a task:**
> "Create a Planner task 'Draft Q3 budget' in the Finance plan, due July 31, assigned to Ann"

**Move a task along:**
> "Mark task 'Draft Q3 budget' as in progress and move it to the Review bucket"

**Reassign work:**
> "Remove Bob from the 'Draft Q3 budget' task and assign it to Carol"

## Requirements

- Microsoft 365 work/school tenant (Planner is not available for consumer accounts)
- An Entra ID app registration with `Tasks.Read.All` / `Tasks.ReadWrite.All` **application**
  permissions and tenant admin consent
- **Basic plans only:** Planner Premium (Project-backed) plans are not supported on Microsoft
  Graph v1.0 and will not appear or be editable through this skill
- The list tools (`list_plans`, `list_buckets`, `list_tasks`) return the **first page** of Graph
  results only and do not follow `@odata.nextLink`; Planner collections are typically single-page,
  but very large collections may be truncated
- Planner enforces service limits (e.g. maximum tasks per plan, plans per group, assignees per
  task). When a limit is hit, Graph returns a 403 with a code such as `MaximumTasksInProject` or
  `MaximumPlansOwnedByGroup`; this skill surfaces that code plainly in the error message

## Trademarks

Microsoft, Microsoft 365, Planner, and Microsoft Graph are trademarks of the Microsoft group of
companies. This skill is an independent integration developed by Buildersoft LLC and is not
affiliated with, endorsed by, or sponsored by Microsoft.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
