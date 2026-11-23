# Sophon built-in tool catalogue for the agent tool-name lint (build/AgentLint.psm1).
#
# Pinned to sophon commit a431e1a64 (v2.2.2). Hand-maintained: when the Sophon runtime adds, renames or
# removes a tool, update this file in the same change that relies on it.
#
# How Allowed was derived (all paths under sophon/src):
#   - every `public string Name => "<name>";` in a class implementing ITool (Sophon.Skills/Tools/*.cs,
#     Sophon.Core/Agents/AgentCreateTool.cs, Sophon.Core/Orchestration/DynamicToolChainTool.cs,
#     Sophon.Gateway/Tools/NodeListTool.cs), including the multi-tool files WorkflowTools.cs and
#     ScheduleTools.cs;
#   - the tools whose Name is a constant: tools.search and tools.load (Skills/ToolSelection/ToolProfile.cs),
#     todo.write (Orchestration/Planning/TodoList.cs), plan.propose (Orchestration/Planning/PlanModeNote.cs).
#   MCP-bridged, sandboxed and CLI MCP-serve tools are dynamic and are not listed. Total: 141.
#
# SkillTools (the tools declared in skills/*/manifest.json) are NOT stored here: Get-AgentCatalog reads them
# from the skills tree at load time, so the list can never drift from the skills it describes.
@{
    SophonCommit  = 'a431e1a64'
    SophonVersion = '2.2.2'

    # Every real model-facing tool name (141), ordinal order.
    Allowed = @(
        'agent.create', 'agent.delegate', 'agent.delete', 'agent.get', 'agent.list', 'agent.templates', 'agent.update',
        'archive',
        'browser.act', 'browser.screenshot',
        'calculator.evaluate', 'calendar', 'canvas.render', 'channel.list', 'clipboard',
        'code.build', 'code.deps', 'code.execute', 'code.format', 'code.git', 'code.lint', 'code.test',
        'coding.claude_code', 'coding.codex', 'coding.copilot',
        'connection.configure', 'connection.list', 'connection.status', 'contacts', 'cron.manage', 'crypto',
        'data.csv', 'data.json', 'data.sqlite', 'data.xml', 'data.yaml',
        'datetime.now', 'desktop.activity', 'diff',
        'document.ask', 'document.collection.create', 'document.collection.delete', 'document.collection.list',
        'document.delete', 'document.info', 'document.list', 'document.read', 'document.retrieve', 'document.save_url',
        'document.search', 'document.summarize', 'document.update', 'document.upload',
        'email.compose',
        'fs.apply_patch', 'fs.copy', 'fs.create_directory', 'fs.delete', 'fs.edit', 'fs.find', 'fs.info', 'fs.list',
        'fs.move', 'fs.multi_edit', 'fs.read', 'fs.search', 'fs.write',
        'http.request', 'image.generate', 'info.request', 'insights.query',
        'markdown', 'marketplace.install', 'marketplace.search', 'media.image', 'media.video',
        'memory.diagram', 'memory.entity.list', 'memory.forget', 'memory.graph', 'memory.link', 'memory.list',
        'memory.search', 'memory.traverse', 'memory.write',
        'message.send', 'music.generate', 'network', 'node.list', 'node.present_canvas',
        'office.excel', 'office.powerpoint', 'office.word',
        'os.execute', 'os.execute_sandboxed', 'os.info',
        'pdf', 'plan.propose', 'plan.recover', 'process', 'qrcode', 'remote.control',
        'schedule.create', 'schedule.delete', 'schedule.explain', 'schedule.get', 'schedule.history', 'schedule.list',
        'schedule.next_runs', 'schedule.pause', 'schedule.resume', 'schedule.status', 'schedule.trigger',
        'schedule.update',
        'session.history', 'session.repair', 'session.switch_model', 'sessions.yield',
        'skill.author', 'skill.generate_from_doc',
        'template', 'todo.write', 'tool.create_chain', 'tools.load', 'tools.search', 'translate', 'tts.file',
        'video.generate', 'weather', 'web.feed', 'web.scrape', 'web.search',
        'workflow.clone', 'workflow.create', 'workflow.delete', 'workflow.describe', 'workflow.edit', 'workflow.list',
        'workflow.pause', 'workflow.resume', 'workflow.trigger'
    )

    # Real tools that agent text may name ONLY in a negated statement (the line or the line before holds a
    # negation word). An entry ending in '.*' covers every name with that prefix. TOOLS.md may never pin one.
    # Source: the family wording rules (design section 7.3, lint item 2).
    Restricted = @(
        'sessions.yield',
        'code.test', 'code.build', 'code.lint', 'code.format', 'code.deps', 'code.execute',
        'os.execute_sandboxed',
        'marketplace.install',
        'agent.create', 'agent.update', 'agent.delete', 'agent.templates',
        'session.switch_model', 'session.repair',
        'skill.*', 'workflow.*', 'cron.*', 'schedule.*', 'coding.*',
        'tool.create_chain',
        'remote.control', 'desktop.activity', 'clipboard', 'contacts', 'calendar',
        'message.send', 'email.compose', 'node.present_canvas', 'connection.configure', 'process'
    )

    # Names that are not Sophon tools, each with the hint printed by the lint. Allowed only in a negated
    # statement ("There is no web.fetch; use web.scrape").
    Denied = @{
        'web.fetch'                   = 'use web.scrape {operation:"readability", url}'
        'web.get'                     = 'use web.scrape {operation:"readability", url}'
        'web.read'                    = 'use web.scrape {operation:"readability", url}'
        'web.browse'                  = 'use web.scrape, or browser.act for interaction'
        'http.get'                    = 'use http.request'
        'http.fetch'                  = 'use http.request'
        'email.send'                  = 'there is no email-sending tool for agents (email.compose is restricted)'
        'workflow.run'                = 'there is no workflow-run tool; the lead runs waves with agent.delegate'
        'workflow.start'              = 'there is no workflow-run tool; the lead runs waves with agent.delegate'
        'tool_search'                 = 'use tools.search'
        'tool_load'                   = 'use tools.load'
        'tool.search'                 = 'use tools.search'
        'tool.load'                   = 'use tools.load'
        'tools.find'                  = 'use tools.search'
        'tools.list'                  = 'use tools.search'
        'agent.spawn'                 = 'use agent.delegate'
        'agent.run'                   = 'use agent.delegate'
        'agent.call'                  = 'use agent.delegate'
        'agent.task'                  = 'use agent.delegate'
        'subagent.run'                = 'use agent.delegate'
        'subagent.spawn'              = 'use agent.delegate'
        'sessions.spawn'              = 'use agent.delegate'
        'sessions.send'               = 'use agent.delegate'
        'session.yield'               = 'sessions.yield is restricted; never use it'
        'todo.read'                   = 'there is no todo reader: todo.write replies with counts only, so keep the list yourself'
        'todo.update'                 = 'use todo.write (each call replaces the whole list)'
        'todo.add'                    = 'use todo.write (each call replaces the whole list)'
        'plan.exit'                   = 'use plan.propose'
        'plan.approve'                = 'use plan.propose, or info.request when plan mode is off'
        'plan.execute'                = 'plan.execute is an approval card, not a tool: use plan.propose'
        'plan.write'                  = 'write the plan file with fs.write'
        'fs.glob'                     = 'use fs.find'
        'fs.grep'                     = 'use fs.search'
        'fs.ls'                       = 'use fs.list'
        'fs.cat'                      = 'use fs.read'
        'fs.open'                     = 'use fs.read'
        'fs.stat'                     = 'use fs.info'
        'fs.mkdir'                    = 'use fs.create_directory'
        'fs.rm'                       = 'use fs.delete'
        'fs.remove'                   = 'use fs.delete'
        'fs.rename'                   = 'use fs.move'
        'fs.mv'                       = 'use fs.move'
        'fs.cp'                       = 'use fs.copy'
        'fs.patch'                    = 'edit with the tool the Workspace section names'
        'fs.replace'                  = 'edit with the tool the Workspace section names'
        'os.run'                      = 'use os.execute'
        'os.exec'                     = 'use os.execute'
        'os.shell'                    = 'use os.execute'
        'os.bash'                     = 'use os.execute'
        'shell.run'                   = 'use os.execute'
        'shell.exec'                  = 'use os.execute'
        'shell.execute'               = 'use os.execute'
        'bash.run'                    = 'use os.execute'
        'bash.exec'                   = 'use os.execute'
        'cmd.run'                     = 'use os.execute'
        'powershell.run'              = 'use os.execute'
        'terminal.run'                = 'use os.execute'
        'code.run'                    = 'use os.execute'
        'code.push'                   = 'use os.execute git push'
        'code.review'                 = 'there is no review tool: review inline, or the lead delegates to code-reviewer'
        'git.push'                    = 'use os.execute git push'
        'git.pull'                    = 'use os.execute git pull, after asking'
        'git.fetch'                   = 'use os.execute git fetch, after asking'
        'git.commit'                  = 'use the os.execute verify-and-commit command (code.git commit stages everything)'
        'git.add'                     = 'use os.execute git add with a pathspec'
        'git.status'                  = 'use code.git {operation:"status"}'
        'git.diff'                    = 'use code.git {operation:"diff"}'
        'git.log'                     = 'use code.git {operation:"log"}'
        'git.branch'                  = 'use code.git {operation:"branch"}'
        'git.checkout'                = 'use os.execute git checkout -b'
        'github.create_pull_request'  = 'use os.execute gh pr create'
        'github.create_pr'            = 'use os.execute gh pr create'
        'github.pr_create'            = 'use os.execute gh pr create'
        'github.pull_request'         = 'use os.execute gh pr create'
        'gh.pr'                       = 'use os.execute gh pr create'
        'gh.pr_create'                = 'use os.execute gh pr create'
        'pr.create'                   = 'use os.execute gh pr create'
        'ask.user'                    = 'use info.request'
        'info.ask'                    = 'use info.request'
        'memory.read'                 = 'use memory.search'
        'memory.delete'               = 'use memory.forget'
        'memory.save'                 = 'use memory.write'
        'memory.store'                = 'use memory.write'
        'browser.navigate'            = 'use browser.act'
        'browser.open'                = 'use browser.act'
        'browser.click'               = 'use browser.act'
        'browser.snapshot'            = 'use browser.screenshot'
        'canvas.show'                 = 'use canvas.render'
        'canvas.present'              = 'use canvas.render'
        'datetime.today'              = 'use datetime.now'
        'notebook.edit'               = 'there is no notebook tool'
    }

    # Claude Code tool names: an error in SOUL and TOOLS text when written in backticks (case-sensitive).
    ClaudeCodeNames = @(
        'Bash', 'Read', 'Write', 'Edit', 'MultiEdit', 'Grep', 'Glob', 'LS', 'Task', 'TodoWrite',
        'AskUserQuestion', 'ExitPlanMode', 'EnterPlanMode', 'Workflow', 'WebFetch', 'WebSearch',
        'NotebookEdit', 'Agent', 'Skill'
    )

    # Dotted tokens that are not tool references even though their first segment is a known namespace.
    NotTools = @(
        'e.g', 'i.e', 'a.k.a', 'n.b',
        'coding.subagent', 'coding.graphnode',
        'remote.origin', 'remote.origin.url', 'remote.origin.fetch',
        'http.server', 'http.proxy', 'http.sslverify', 'http.postbuffer',
        'document.body', 'document.title', 'document.head', 'document.forms', 'document.images', 'document.links',
        'document.fonts', 'document.cookie'
    )

    # Known first segments. Get-AgentCatalog adds the first segment of every dotted Allowed, Denied and
    # SkillTools name, so this list only names the extra ones and documents the expected set.
    Namespaces = @(
        'agent', 'browser', 'calculator', 'canvas', 'channel', 'code', 'coding', 'connection', 'cron', 'data',
        'datetime', 'desktop', 'document', 'email', 'fs', 'http', 'image', 'info', 'insights', 'marketplace',
        'media', 'memory', 'message', 'music', 'node', 'office', 'os', 'plan', 'remote', 'schedule', 'session',
        'sessions', 'skill', 'todo', 'tool', 'tools', 'tts', 'video', 'web', 'workflow',
        'git', 'github', 'gh', 'pr', 'shell', 'bash', 'cmd', 'powershell', 'terminal', 'subagent', 'ask',
        'notebook'
    )

    # A dotted candidate whose last segment is one of these is a host name, unless the whole token is listed.
    Tlds = @('io', 'com', 'org', 'net', 'dev', 'app', 'ai')

    # A dotted candidate whose last segment is one of these is a file name, unless the whole token is listed.
    FileExtensions = @(
        'md', 'markdown', 'mdx', 'rst', 'adoc', 'txt', 'json', 'jsonc', 'jsonl', 'yml', 'yaml', 'toml', 'xml', 'csv',
        'tsv', 'ini', 'cfg', 'conf', 'config', 'env', 'lock', 'log', 'ps1', 'psm1', 'psd1', 'ps1xml', 'cs', 'csx',
        'csproj', 'sln', 'slnx', 'props', 'targets', 'fsproj', 'vbproj', 'vb', 'razor', 'cshtml', 'resx', 'py',
        'pyi', 'pyc', 'ipynb', 'js', 'mjs', 'cjs', 'ts', 'mts', 'cts', 'tsx', 'jsx', 'vue', 'svelte', 'astro',
        'html', 'htm', 'css', 'scss', 'sass', 'less', 'sh', 'bash', 'zsh', 'fish', 'cmd', 'bat', 'exe', 'dll',
        'so', 'dylib', 'zip', 'gz', 'tgz', 'tar', 'nupkg', 'snupkg', 'jar', 'war', 'whl', 'wasm', 'png', 'jpg',
        'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'pdf', 'docx', 'xlsx', 'pptx', 'sql', 'db', 'sqlite', 'go',
        'mod', 'sum', 'rs', 'java', 'kt', 'kts', 'gradle', 'rb', 'php', 'swift', 'c', 'h', 'cpp', 'hpp', 'cc',
        'lua', 'pl', 'dart', 'scala', 'ex', 'exs', 'erl', 'hs', 'elm', 'proto', 'graphql', 'gql', 'tf', 'hcl',
        'gitignore', 'gitattributes', 'editorconfig', 'npmrc', 'nvmrc', 'map', 'min', 'bak', 'tmp', 'out',
        'pem', 'crt', 'cer', 'pub', 'bin', 'obj', 'dat', 'cache', 'tex',
        # Media (video, audio, subtitles, LUTs, fonts): file names such as clip.mp4 or cues.srt are not tools.
        'mp4', 'mov', 'mkv', 'webm', 'm4v', 'avi', 'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'opus', 'srt', 'vtt',
        'ass', 'cube', 'ttf', 'otf'
    )

    # code.git (sophon/src/Sophon.Skills/Tools/CodeGitTool.cs:25-26, :53-55): the operation enum and the
    # stash_action enum.
    CodeGitOperations = @(
        'status', 'diff', 'log', 'commit', 'branch', 'checkout', 'merge', 'stash', 'remote', 'clone', 'tag',
        'blame', 'cherry_pick'
    )
    StashActions = @('save', 'pop', 'list', 'drop')

    # Git subcommands the lint recognises after "code.git " in prose ("code.git push"); any of these that is
    # not a code.git operation is reported unless the statement is negated.
    GitVerbs = @(
        'add', 'am', 'amend', 'apply', 'bisect', 'blame', 'branch', 'checkout', 'cherry-pick', 'cherry_pick',
        'clean', 'clone', 'commit', 'config', 'describe', 'diff', 'fetch', 'gc', 'grep', 'init', 'log', 'merge',
        'mv', 'notes', 'pr', 'prune', 'pull', 'push', 'rebase', 'reflog', 'remote', 'reset', 'restore', 'revert',
        'rm', 'show', 'stash', 'status', 'submodule', 'switch', 'tag', 'worktree'
    )

    # Edit tools: never pinned in TOOLS.md (fragment 02 names "the edit tool the Workspace section names").
    EditTools = @('fs.edit', 'fs.multi_edit', 'fs.apply_patch')

    # Core tool sets per profile (sophon/src/Sophon.Core/Skills/ToolSelection/ToolProfile.cs:61-161), used to
    # find core-duplicate pins. subagent = chat minus message.send, info.request and plan.recover; graphnode =
    # chat minus message.send and plan.recover; coding.subagent = coding minus info.request, plan.propose and
    # plan.recover; coding.graphnode = coding minus plan.propose and plan.recover. tools.search and tools.load
    # are appended to every profile (IncludeMetaTools).
    MetaTools = @('tools.search', 'tools.load')
    ProfileCore = @{
        'chat'             = @('datetime.now', 'memory.search', 'memory.write', 'message.send', 'fs.read', 'fs.write',
                               'fs.list', 'code.execute', 'document.search', 'web.search', 'calculator.evaluate',
                               'sessions.yield', 'info.request', 'agent.delegate', 'plan.recover')
        'voice'            = @('datetime.now', 'memory.search', 'memory.write', 'message.send', 'web.search')
        'heartbeat'        = @('datetime.now', 'memory.search', 'message.send', 'schedule.list')
        'cron'             = @('datetime.now', 'memory.search', 'message.send', 'schedule.list')
        'subagent'         = @('datetime.now', 'memory.search', 'memory.write', 'fs.read', 'fs.write', 'fs.list',
                               'code.execute', 'document.search', 'web.search', 'calculator.evaluate',
                               'sessions.yield', 'agent.delegate')
        'graphnode'        = @('datetime.now', 'memory.search', 'memory.write', 'fs.read', 'fs.write', 'fs.list',
                               'code.execute', 'document.search', 'web.search', 'calculator.evaluate',
                               'sessions.yield', 'info.request', 'agent.delegate')
        'coding'           = @('agent.delegate', 'code.git', 'datetime.now', 'fs.edit', 'fs.find', 'fs.list',
                               'fs.multi_edit', 'fs.read', 'fs.search', 'fs.write', 'info.request', 'memory.search',
                               'memory.write', 'os.execute', 'plan.propose', 'plan.recover', 'sessions.yield',
                               'todo.write', 'web.search')
        'coding.subagent'  = @('agent.delegate', 'code.git', 'datetime.now', 'fs.edit', 'fs.find', 'fs.list',
                               'fs.multi_edit', 'fs.read', 'fs.search', 'fs.write', 'memory.search', 'memory.write',
                               'os.execute', 'sessions.yield', 'todo.write', 'web.search')
        'coding.graphnode' = @('agent.delegate', 'code.git', 'datetime.now', 'fs.edit', 'fs.find', 'fs.list',
                               'fs.multi_edit', 'fs.read', 'fs.search', 'fs.write', 'info.request', 'memory.search',
                               'memory.write', 'os.execute', 'sessions.yield', 'todo.write', 'web.search')
    }

    # Profiles where a scoped tool set can replace the core, so pinning a core tool there is meaningful.
    ChildProfiles = @('subagent', 'coding.subagent', 'graphnode', 'coding.graphnode')
}
