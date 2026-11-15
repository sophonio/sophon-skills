## Reading git
- No card: code.git `{operation:"status"}` (hides files staged as new, deleted or renamed; the Git state block shows them), `{operation:"log", count}` (HEAD, ≤200), `{operation:"branch"}` without branch_name, `{operation:"remote"}`, `{operation:"stash", stash_action:"list"}`.
- A card: `{operation:"diff"}` = HEAD vs working tree, tracked files only (fs.read new files; committed work is invisible to it); `{operation:"blame", file_path}`.
- Ranges, other branches: one os.execute, e.g. `git --no-pager log --oneline <base>..HEAD && git --no-pager diff --stat <base>...HEAD`; old file versions via `git show <rev>:<path>`, never a checkout. Base: usually main or master (check the branch list). Never fetch, pull or switch branches to look.
- A child with a diff file in its brief reads it with fs.read, never os.execute or code.git diff.
