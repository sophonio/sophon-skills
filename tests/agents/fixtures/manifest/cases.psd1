# Manifest fixtures (docs/plans/2026-11-15-agents-v2-design.md section 7.5 F; the skill rules: docs/plans/2026-11-23-agents-v3-design.md,
# "Static checks"), run by Invoke-AgentLintFixtures in build/AgentLint.psm1 against
# the family contract (Get-AgentLintTestFamily), not against build/agent-src/family.psd1.
# Base is a valid lead-developer manifest and BaseTools its TOOLS.md. A case either gives its own Json, or
# Replace pairs applied to Base in order (both sides expand {U+XXXX} and {REPEAT:<text>:<n>}). Id defaults to
# lead-developer.
@{
    Base = @'
{
  "type": "agent",
  "schemaVersion": 1,
  "name": "lead-developer",
  "displayName": "Lead Developer",
  "version": "2.0.0",
  "description": "Runs a code change end to end in a bound repository: a plan file you approve, task-by-task execution and one verified commit per task.",
  "author": "Buildersoft LLC",
  "license": "MIT",
  "category": "development",
  "tags": [
    "development",
    "orchestration",
    "planning"
  ],
  "agent": {
    "whenToUse": "Pick this agent to plan and deliver a code change in a bound repository. Not for: questions about how code works (researcher), review of an existing diff (code-reviewer). Family role: lead-developer."
  },
  "requires": {
    "tools": [
      "agent.list",
      "fs.find",
      "fs.search",
      "session.history",
      "todo.write",
      "web.scrape"
    ]
  },
  "defaults": {
    "subAgents": {
      "enabled": true,
      "maxDepth": 1
    },
    "modelRouting": {
      "mode": "inherit"
    }
  },
  "sophon": {
    "minVersion": "2.2.0"
  }
}

'@

    BaseTools = @'
---
profiles:
  coding:
    pins:
      - agent.list
      - web.scrape
      - session.history
  chat:
    pins:
      - agent.list
      - todo.write
      - fs.find
      - fs.search
      - web.scrape
---
agent.list finds companions; web.scrape reads docs; session.history restores consent after a gap.

'@

    Cases = @(
        # ---- must pass ----
        @{ Name = 'valid lead manifest'; Expect = 'pass' }
        @{ Name = 'valid non-lead manifest'; Id = 'developer'; Expect = 'pass'
           Replace = @(
               @('"name": "lead-developer"', '"name": "developer"'),
               @('"displayName": "Lead Developer"', '"displayName": "Developer"'),
               @('Family role: lead-developer.', 'Family role: developer.'),
               @('"enabled": true,', '"enabled": false,'),
               @('"maxDepth": 1', '"maxDepth": 0')) }
        @{ Name = 'agent with its own Apache-2.0 license'; Id = 'frontend-developer'; Expect = 'pass'
           Replace = @(
               @('"name": "lead-developer"', '"name": "frontend-developer"'),
               @('"displayName": "Lead Developer"', '"displayName": "Frontend Developer"'),
               @('"license": "MIT"', '"license": "Apache-2.0"'),
               @('Family role: lead-developer.', 'Family role: frontend-developer.'),
               @('"enabled": true,', '"enabled": false,'),
               @('"maxDepth": 1', '"maxDepth": 0')) }

        # ---- must fail ----
        @{ Name = 'Apache-2.0 agent declaring the family MIT license'; Id = 'frontend-developer'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(
               @('"name": "lead-developer"', '"name": "frontend-developer"'),
               @('"displayName": "Lead Developer"', '"displayName": "Frontend Developer"'),
               @('Family role: lead-developer.', 'Family role: frontend-developer.'),
               @('"enabled": true,', '"enabled": false,'),
               @('"maxDepth": 1', '"maxDepth": 0')) }
        @{ Name = 'MIT agent declaring Apache-2.0'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(, @('"license": "MIT"', '"license": "Apache-2.0"')) }
        @{ Name = 'not JSON'; Expect = 'fail'; Rule = 'MAN-JSON'
           Replace = @(, @('"type": "agent",', '"type": "agent"')) }
        @{ Name = 'CR line ending'; Expect = 'fail'; Rule = 'MAN-FORMAT'
           Replace = @(, @('"type": "agent",', '"type": "agent",{U+000D}')) }
        @{ Name = 'odd indentation'; Expect = 'fail'; Rule = 'MAN-FORMAT'
           Replace = @(, @('  "type": "agent",', '   "type": "agent",')) }
        @{ Name = 'icon key'; Expect = 'fail'; Rule = 'MAN-KEYS'
           Replace = @(, @('"license": "MIT",', '"license": "MIT",{U+000A}  "icon": "robot",')) }
        @{ Name = 'heartbeat key'; Expect = 'fail'; Rule = 'MAN-KEYS'
           Replace = @(, @('  "sophon": {', '  "heartbeat": {{U+000A}    "intervalMinutes": 60{U+000A}  },{U+000A}  "sophon": {')) }
        @{ Name = 'keys out of order'; Expect = 'fail'; Rule = 'MAN-ORDER'
           Replace = @(, @('"type": "agent",{U+000A}  "schemaVersion": 1,', '"schemaVersion": 1,{U+000A}  "type": "agent",')) }
        @{ Name = 'name differs from folder'; Expect = 'fail'; Rule = 'MAN-NAME'
           Replace = @(, @('"name": "lead-developer"', '"name": "lead-dev"')) }
        @{ Name = 'wrong displayName'; Expect = 'fail'; Rule = 'MAN-DISPLAY'
           Replace = @(, @('"displayName": "Lead Developer"', '"displayName": "Lead Dev"')) }
        @{ Name = 'version major 1'; Expect = 'fail'; Rule = 'MAN-VERSION'
           Replace = @(, @('"version": "2.0.0"', '"version": "1.0.0"')) }
        @{ Name = 'version not SemVer'; Expect = 'fail'; Rule = 'MAN-VERSION'
           Replace = @(, @('"version": "2.0.0"', '"version": "2.0"')) }
        @{ Name = 'description over 600 characters'; Expect = 'fail'; Rule = 'MAN-DESC'
           Replace = @(, @('Runs a code change end to end in a bound repository', '{REPEAT:Runs a change :50}')) }
        @{ Name = 'wrong author'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(, @('"author": "Buildersoft LLC"', '"author": "Someone Else"')) }
        @{ Name = 'default wrong license'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(, @('"license": "MIT"', '"license": "Apache-2.0"')) }
        @{ Name = 'default wrong category'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(, @('"category": "development"', '"category": "productivity"')) }
        @{ Name = 'tags without development'; Expect = 'fail'; Rule = 'MAN-TAGS'
           Replace = @(, @('    "development",{U+000A}', '')) }
        @{ Name = 'tag not kebab-case'; Expect = 'fail'; Rule = 'MAN-TAGS'
           Replace = @(, @('"planning"', '"Plan Mode"')) }
        @{ Name = 'whenToUse without Not for'; Expect = 'fail'; Rule = 'MAN-AGENT'
           Replace = @(, @('Not for: questions', 'Also good for questions')) }
        @{ Name = 'whenToUse names no sibling'; Expect = 'fail'; Rule = 'MAN-AGENT'
           Replace = @(, @('Not for: questions about how code works (researcher), review of an existing diff (code-reviewer).', 'Not for: questions about how code works.')) }
        @{ Name = 'whenToUse marker for another role'; Expect = 'fail'; Rule = 'MAN-AGENT'
           Replace = @(, @('Family role: lead-developer.', 'Family role: developer.')) }
        @{ Name = 'agent.icon'; Expect = 'fail'; Rule = 'MAN-AGENT'
           Replace = @(, @('  "agent": {{U+000A}', '  "agent": {{U+000A}    "icon": "robot",{U+000A}')) }
        @{ Name = 'requires.tools missing a pin'; Expect = 'fail'; Rule = 'MAN-REQUIRES'
           Replace = @(, @('      "fs.search",{U+000A}', '')) }
        @{ Name = 'requires.tools not sorted'; Expect = 'fail'; Rule = 'MAN-REQUIRES'
           Replace = @(, @('      "fs.find",{U+000A}      "fs.search",', '      "fs.search",{U+000A}      "fs.find",')) }
        @{ Name = 'requires.tools with a zero-width space (a culture compare calls it equal)'; Expect = 'fail'; Rule = 'MAN-REQUIRES'
           Replace = @(, @('      "fs.find",', '      "fs.fi{U+200B}nd",')) }
        @{ Name = 'author with a zero-width space'; Expect = 'fail'; Rule = 'MAN-META'
           Replace = @(, @('"author": "Buildersoft LLC",', '"author": "Builder{U+200B}soft LLC",')) }
        @{ Name = 'lead without delegation'; Expect = 'fail'; Rule = 'MAN-DEFAULTS'
           Replace = @(, @('"enabled": true,', '"enabled": false,')) }
        @{ Name = 'non-lead with delegation'; Id = 'developer'; Expect = 'fail'; Rule = 'MAN-DEFAULTS'
           Replace = @(
               @('"name": "lead-developer"', '"name": "developer"'),
               @('"displayName": "Lead Developer"', '"displayName": "Developer"'),
               @('Family role: lead-developer.', 'Family role: developer.')) }
        @{ Name = 'model routing not inherit'; Expect = 'fail'; Rule = 'MAN-DEFAULTS'
           Replace = @(, @('"mode": "inherit"', '"mode": "auto"')) }
        @{ Name = 'minVersion 2.1.0'; Expect = 'fail'; Rule = 'MAN-SOPHON'
           Replace = @(, @('"minVersion": "2.2.0"', '"minVersion": "2.1.0"')) }
    )
}
