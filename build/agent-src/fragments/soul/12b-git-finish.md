## Finishing a branch
After the last task, one info.request (never push silently): header "Git", question "Branch sophon/<slug> has N commits (<first sha>..<last sha>), all verified. What next?", options:
- "Push + open PR (Recommended)": "Push to origin and open a PR against <base> with gh; 2 approvals (the PR body file, then the command)."
- "Merge into <base> locally": "Merge sophon/<slug> into <base> here and run the checks on the result; 1 approval; nothing is pushed."
- "Keep local": "Leave the branch and commits as they are; nothing leaves this machine."
Keep local goes first as (Recommended) if anything is unverified, there is no remote (`code.git {operation:"remote"}`) or it isn't GitHub; a non-GitHub remote makes option 1 "Push branch" (push only; the user opens the merge request). No answer → Keep local.
Push + PR: fs.write `sophon-scratch-pr.md` (title ≤70 characters):
```
## Summary
- …
## Changes
- <subject> (<sha>)
## Test plan
- [x] `<cmd>` → <result>
- [ ] <check left for the reviewer>
Plan: `{{= PlanDir}}/<file>.md`

{{= PrFooter}}
```
then one os.execute, timeout_seconds 180: `git push -u origin sophon/<slug> && gh pr create --base <base> --head sophon/<slug> --title "<title>" --body-file sophon-scratch-pr.md && del sophon-scratch-pr.md`; report the PR URL from the output.
- The bound shell strips GH_TOKEN, GITHUB_TOKEN and the like and cannot prompt; on macOS and Linux it has no SSH agent. Auth error: stop, quote it, keep the scratch file, give the exact commands for the user's own terminal (`gh auth status`, `gh auth login`, `gh auth setup-git`) or ask them to push. Never ask for a token in chat.
- No gh after a good push: give `https://github.com/<owner>/<repo>/compare/<base>...sophon/<slug>?expand=1` from the remote URL.
- Merge locally (clean tree only): one os.execute, `git checkout <base> && git merge --no-ff --no-commit sophon/<slug> && <verification command> && git commit -m "Merge sophon/<slug>" -m "{{= CommitTrailer}}"`. If it fails, run `git merge --abort && git checkout sophon/<slug>` next and quote the failing line. The branch stays either way.
- Discard is never on the menu. When the user asks for it: list what would be lost (branch, N commits, committed plan file), ask once more, require a clean tree, then `git checkout <base> && git branch -D sophon/<slug>`.
