# Preflight scan rules for agent packages (build/AgentLint.psm1, Invoke-AgentPreflight).
#
# Each block mirrors a scanner the package meets after it leaves this repo, so a package that passes here
# passes those scanners cleanly. Sources are pinned to sophon a431e1a64 (v2.2.2) and the sophon-marketplace
# tree of the same date. Copy changes from the named source file; do not edit the literals by hand.
# Re-diffed at M9 (2026-11-25): the sophon source files are byte-identical at v3-main 38c3f7d, and
# AgentPromptHeuristics.cs at sophon-marketplace 102cd75 (last changed 61cf910) matches P4 and P5. Its rune walk flags Cf above U+FFFF, so P3 gained 'format-astral'.
#
# Rule ids: SCAN-P1 possible_secret, SCAN-P2 injection literals, SCAN-P3 hidden characters, SCAN-P4 prompt
# heuristics, SCAN-P5 hosts, SCAN-P6 template residue, SCAN-WORD this family's stricter wording policy.
@{
    # ---------------------------------------------------------------------------------------------------------
    # P2 - injection literals.
    # Mirrors sophon/src/Sophon.Core/Security/SuspiciousPatterns.cs (the Tiered table, lines 95-143).
    # Matching follows SuspiciousPatterns.Scan: the whole text is lower-cased, every control character
    # (newlines included) becomes a space, and a literal matches only where each end of it that is a word
    # character (letter, digit or underscore) sits on a word boundary. The runtime install scan
    # (sophon/src/Sophon.Core/Agents/Packaging/AgentPackageScanner.cs) warns at Medium and above; this
    # preflight fails on ANY High or ANY Medium literal (the runtime needs two Medium hits). Low literals are
    # informational only and never fail.
    # ---------------------------------------------------------------------------------------------------------
    P2 = @{
        High = @(
            'ignore previous instructions', 'ignore all previous', 'forget all prior', 'ignore your guidelines',
            'reveal your instructions', 'reveal your prompt', 'your system prompt', 'print your instructions',
            'repeat the words above', 'repeat your instructions', 'pretend you are', 'roleplay as',
            '<|im_start|>', '</external_content'
        )
        Medium = @(
            'ignore the above', 'disregard previous', 'disregard the above', 'disregard all', 'forget previous',
            'forget everything', 'you are now', 'you''re now', 'new instruction:', 'end of instructions',
            'begin new conversation', 'do anything now', 'dan mode', 'pretend to be', 'jailbreak', 'admin mode',
            '<system>'
        )
        Low = @(
            'you are a ', 'new instructions', 'system prompt', 'developer mode', 'dev mode', 'act as ', 'override',
            'bypass', 'root access', 'sudo ', 'without restrictions', '[system]', 'assistant:'
        )
    }

    # ---------------------------------------------------------------------------------------------------------
    # P4 - moderator-assist heuristics, applied per line.
    # Mirrors sophon-marketplace/src/Sophon.Marketplace.Api/Publishing/AgentPromptHeuristics.cs (lines 31-82).
    # Options: IgnoreCase and CultureInvariant, except encoded-blob (CultureInvariant only). The marketplace
    # applies them to SOUL.md, VOICE.md, HEARTBEAT.md, TOOLS.md and the manifest's displayName, description
    # and agent.whenToUse; this preflight also applies them to README.md.
    # remote-exec is two regexes: a download command, then a pipe into a shell anywhere after the FIRST
    # download command on the line (FindRemoteExec).
    # ---------------------------------------------------------------------------------------------------------
    P4 = @(
        @{
            Id         = 'ignore-instructions'
            Pattern    = '\b(?:ignore|disregard|forget|override)\b[^\n]{0,40}\b(?:previous|prior|above|earlier|all|any|system|safety|original)\b[^\n]{0,30}\b(?:instructions?|rules|prompts?|guidelines|directives)\b'
            IgnoreCase = $true
        }
        @{
            Id         = 'prompt-reveal'
            Pattern    = '\b(?:reveal|print|output|repeat|show)\b[^\n]{0,30}\b(?:system prompt|hidden instructions|your instructions)\b'
            IgnoreCase = $true
        }
        @{
            Id         = 'approval-bypass'
            Pattern    = '\b(?:auto-?approve|bypass|skip|disable|circumvent|avoid)\b[^\n]{0,30}\b(?:approvals?|confirmations?|permissions?|consent|safety checks?|guardrails?)\b'
            IgnoreCase = $true
        }
        @{
            # SecretWords + [^\n]{0,60} + SendWords | SendWords + [^\n]{0,60} + SecretWords
            Id         = 'secret-exfiltration'
            Pattern    = '(?:\b(?:api[ _-]?keys?|access[ _-]?tokens?|passwords?|credentials?|secrets?|private[ _-]?keys?)\b|\.env\b)[^\n]{0,60}\b(?:send|post|upload|exfiltrate|forward|e-?mail|transmit)\b|\b(?:send|post|upload|exfiltrate|forward|e-?mail|transmit)\b[^\n]{0,60}(?:\b(?:api[ _-]?keys?|access[ _-]?tokens?|passwords?|credentials?|secrets?|private[ _-]?keys?)\b|\.env\b)'
            IgnoreCase = $true
        }
        @{
            Id         = 'role-token-spoof'
            Pattern    = '<\|?(?:im_start|im_end|endoftext)\|?>|\[/?INST\]|</?(?:system|assistant|tool_call|function_call)>'
            IgnoreCase = $true
        }
        @{
            Id          = 'remote-exec'
            Pattern     = '\b(?:curl|wget|iwr|invoke-webrequest)\b'
            PipePattern = '\|\s*(?:sh|bash|zsh|pwsh|iex)\b'
            IgnoreCase  = $true
        }
        @{
            Id         = 'html-comment'
            Pattern    = '<!--'
            IgnoreCase = $true
        }
        @{
            Id         = 'encoded-blob'
            Pattern    = '[A-Za-z0-9+/]{120,}={0,2}'
            IgnoreCase = $false
        }
        @{
            Id         = 'jailbreak-persona'
            Pattern    = '\b(?:do anything now|developer mode|jailbreak|no (?:ethical|moral) (?:guidelines|restrictions))\b'
            IgnoreCase = $true
        }
    )

    # ---------------------------------------------------------------------------------------------------------
    # P3 - hidden and control characters, reported per line with the first offending code point.
    # Mirrors sophon/src/Sophon.Core/Agents/Packaging/AgentPackageValidator.cs (hidden_characters: any Cf),
    # sophon/src/Sophon.Core/Workspaces/ProjectInstructionsProvider.cs (HiddenFindings: tag characters
    # U+E0000-U+E007F and bidi controls), sophon/src/Sophon.Core/Security/PreviewTextSanitizer.cs (what counts
    # as hidden: C0/C1 controls, zero-width characters, Hangul fillers, variation selectors, U+2028/U+2029)
    # and AgentPromptHeuristics.FirstHiddenCharacter (any Cf, walked by rune, so supplementary planes too).
    # Stricter here: CR, NUL and a BOM always fail,
    # and so does any variation selector (the PrFooter emoji is written without U+FE0F). TAB is not hidden
    # (layout checks forbid it separately). Supplementary planes are matched as UTF-16 surrogate pairs: \p{Cf}
    # never matches a pair, so 'tag' and 'format-astral' list the Cf code points above U+FFFF (.NET 11 data).
    # ---------------------------------------------------------------------------------------------------------
    P3 = @(
        @{ Id = 'bom';       Pattern = '\uFEFF';                                         Message = 'byte order mark (U+FEFF)' }
        @{ Id = 'cr';        Pattern = '\r';                                             Message = 'carriage return (CR); use LF line endings' }
        @{ Id = 'nul';       Pattern = '\u0000';                                         Message = 'NUL character' }
        @{ Id = 'bidi';      Pattern = '[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]'; Message = 'bidi control character' }
        @{ Id = 'tag';       Pattern = '\uDB40[\uDC00-\uDC7F]';                          Message = 'Unicode tag character (U+E0000-U+E007F)' }
        @{ Id = 'separator'; Pattern = '[\u2028\u2029]';                                 Message = 'line or paragraph separator (U+2028/U+2029)' }
        @{ Id = 'control';   Pattern = '[\u0001-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]'; Message = 'control character' }
        @{ Id = 'variation'; Pattern = '[\uFE00-\uFE0F]|\uDB40[\uDD00-\uDDEF]';          Message = 'variation selector' }
        @{ Id = 'filler';    Pattern = '[\u115F\u1160\u3164\uFFA0]';                     Message = 'Hangul filler (renders as blank)' }
        @{ Id = 'format';    Pattern = '\p{Cf}';                                         Message = 'invisible formatting character (Unicode Cf, e.g. ZWJ or zero-width space)' }
        @{ Id = 'format-astral'; Pattern = '\uD804[\uDCBD\uDCCD]|\uD80D[\uDC30-\uDC3F]|\uD82F[\uDCA0-\uDCA3]|\uD834[\uDD73-\uDD7A]'
           Message = 'invisible formatting character above U+FFFF (Unicode Cf: U+110BD, U+110CD, U+13430-U+1343F, U+1BCA0-U+1BCA3, U+1D173-U+1D17A)' }
    )

    # ---------------------------------------------------------------------------------------------------------
    # P1 - possible_secret (an approximation of the CLI warning).
    # Mirrors sophon/src/Sophon.Core/Agents/Activity/ToolArgsRedactor.cs: the 16 RedactText rules (lines
    # 120-155) and IsSensitiveKey (lines 55-72, 214-226), applied per line as
    # AgentPackageValidator.SecretLines does (persona files and README.md). Not ported: the JSON argument walk
    # (selector, pair-name and key-material rules), which only applies to tool arguments. A rule with
    # NameMustBeSecret reports only when IsSensitiveKey(name) holds; otherwise the search resumes after the
    # name, as ToolArgsRedactor.Apply does. Group is the capture holding the secret (0 = whole match).
    # Exempt: the TOOLS.md frontmatter "pins:" key lines.
    # ---------------------------------------------------------------------------------------------------------
    P1 = @{
        SensitiveKeyParts    = @(
            'password', 'passwd', 'passphrase', 'secret', 'apikey', 'privatekey', 'accesskey', 'credential',
            'authorization', 'cookie', 'connectionstring', 'sessionkey', 'signingkey', 'subscriptionkey',
            'accountkey'
        )
        SensitiveKeySuffixes = @('token', 'pass', 'pwd')
        SensitiveKeyNames    = @('pwd', 'pass', 'pat', 'otp', 'pin', 'cvv', 'cvc', 'sig')
        RedactedValue        = '^\\?["'']?(?:(?:bearer|basic|token|digest)\s+)?\[redacted\]?\\?["'']?$'
        ExemptLines          = @('^\s*pins:\s*$')
        Rules                = @(
            @{ Id = 'pem-block';      Group = 0; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----[\s\S]*?(?:-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----|\z)' }
            @{ Id = 'pem-tail';       Group = 0; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '\A[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----' }
            @{ Id = 'pem-base64';     Group = 0; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = 'LS0tLS1CRUdJTi[A-Za-z0-9+/=]*' }
            @{ Id = 'authorization';  Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '\b(?:proxy-)?authorization["'']?\s*[:=]\s*["'']?(?:(?:bearer|basic|token|digest)\s+)?([^\s"'',;]+)' }
            @{ Id = 'cookie';         Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '\b(?:set-)?cookie["'']?\s*[:=]\s*["'']?([^\r\n"'']+)' }
            @{ Id = 'bearer';         Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '\bbearer\s+([A-Za-z0-9\-._~+/]{8,}=*)' }
            @{ Id = 'basic';          Group = 1; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '\b(?i:basic)\s+(?=[A-Za-z0-9+/]*(?:[a-z][A-Z]|[0-9+/]))([A-Za-z0-9+/]{8,}={0,2})(?![A-Za-z0-9+/=])' }
            @{ Id = 'url-userinfo';   Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '\b[a-z][a-z0-9+.\-]*://[^/\s:@"'']*:([^/\s"'']+)@' }
            @{ Id = 'url-token-user'; Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '\b[a-z][a-z0-9+.\-]*://([A-Za-z0-9_\-]{20,})@' }
            @{ Id = 'query-secret';   Group = 1; NameMustBeSecret = $false; IgnoreCase = $true
               Pattern = '[?&](?:access_token|refresh_token|id_token|token|api_key|apikey|key|secret|client_secret|password|passwd|pwd|sig|signature|auth|code)=([^&#\s"'']+)' }
            @{ Id = 'token-format';   Group = 0; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '\b(?:sk-[A-Za-z0-9_\-]{16,}|(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9\-_]{20,}|xox[abposr]-[A-Za-z0-9\-]{10,}|AIza[0-9A-Za-z\-_]{35}|npm_[A-Za-z0-9]{36}|hf_[A-Za-z0-9]{30,}|(?:AKIA|ASIA)[A-Z0-9]{16}\b|eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})' }
            @{ Id = 'sshpass';        Group = 1; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '\bsshpass\s+-p\s*("[^"]*"|''[^'']*''|\S+)' }
            @{ Id = 'name-equals';    Group = 1; NameMustBeSecret = $true;  IgnoreCase = $false
               Pattern = '(?<![\w.-])(?<name>[\w.-]+)\s*=+\s*("[^"\r\n]*"?|''[^''\r\n]*''?|[^\s;&|"''=][^\s;&|]*)' }
            @{ Id = 'name-colon';     Group = 1; NameMustBeSecret = $true;  IgnoreCase = $true
               Pattern = '(?<![\w.-])(?<name>[\w.-]+)\\?["'']?\s*(?::=|:|=+>?)\s*(?:(?:bearer|basic|token|digest)\s+)?("[^"\r\n]*"?|''[^''\r\n]*''?|\\"[^"\r\n]*"?|[^\s,;&"''}\]]+)' }
            @{ Id = 'flag-value';     Group = 1; NameMustBeSecret = $true;  IgnoreCase = $false
               Pattern = '(?<![\w-])--?(?<name>[A-Za-z][\w.-]*)\s+("[^"]*"|''[^'']*''|\S+)' }
            @{ Id = 'curl-user';      Group = 1; NameMustBeSecret = $false; IgnoreCase = $false
               Pattern = '(?:^|\s)(?:-u|--user)\s+[^\s:]+:(\S+)' }
        )
    }

    # ---------------------------------------------------------------------------------------------------------
    # P5 - hosts. URL hosts use the marketplace's link-host regex (AgentPromptHeuristics.cs:81, trailing dots
    # trimmed, lower-cased); bare host tokens are names ending in one of the TLDs below. Every host must be in
    # family.psd1 AllowedHosts or LoopbackHosts. E-mail addresses are not hosts.
    # ---------------------------------------------------------------------------------------------------------
    P5 = @{
        UrlHostPattern  = 'https?://([a-z0-9.-]+)'
        BareHostPattern = '(?<![\w.@/:\\-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:io|com|org|net|dev|app|ai))(?![\w-]|\.[a-z0-9])'
        LoopbackHosts   = @('localhost', '127.0.0.1')
    }

    # ---------------------------------------------------------------------------------------------------------
    # P6 - residue a composed or hand-written file must not carry: template syntax, template comments and
    # unfinished markers. A quoted "TODO" or "TBD" (a rule naming the word) is not residue.
    # ---------------------------------------------------------------------------------------------------------
    P6 = @(
        @{ Id = 'template-tag';     Pattern = '\{\{';                                Message = 'template syntax "{{" left in the text' }
        @{ Id = 'template-comment'; Pattern = '^%% ';                                Message = 'template comment line ("%% ") left in the text' }
        @{ Id = 'marker';           Pattern = '(?<!["''`])\b(?:TODO|TBD)\b(?!["''`])'; Message = 'unfinished marker (TODO or TBD)' }
    )

    # ---------------------------------------------------------------------------------------------------------
    # SCAN-WORD - this family's own wording policy (docs/plans/2026-11-15-agents-v2-design.md section 2),
    # stricter than the scanners above. Applied per line, IgnoreCase.
    # ---------------------------------------------------------------------------------------------------------
    Word = @(
        @{
            Id      = 'auto-approve'
            Pattern = '\bauto[- ]?approv\w*'
            Message = 'write "allowed Medium-risk calls for the session" instead of "auto-approve"'
        }
        @{
            Id      = 'approval-nearby'
            Pattern = '\b(?:auto-?approve|bypass|skip|disable|circumvent|avoid|ignore)\b[^\n]{0,30}\b(?:approv\w*|confirm\w*|permissions?|consent\w*|safety checks?|guardrails?)'
            Message = 'skip/avoid/disable/ignore within 30 characters before an approval word reads as an approval bypass'
        }
        @{
            Id      = 'secret-nearby'
            Pattern = '(?:\b(?:api[ _-]?keys?|access[ _-]?tokens?|tokens?|passwords?|passwd|credentials?|secrets?|private[ _-]?keys?|cookies?)\b|\.env\b)[^\n]{0,60}\b(?:send|post|upload|exfiltrate|forward|e-?mail|transmit)\b|\b(?:send|post|upload|exfiltrate|forward|e-?mail|transmit)\b[^\n]{0,60}(?:\b(?:api[ _-]?keys?|access[ _-]?tokens?|tokens?|passwords?|passwd|credentials?|secrets?|private[ _-]?keys?|cookies?)\b|\.env\b)'
            Message = 'a secret word within 60 characters of send/post/upload/forward/email/transmit reads as exfiltration'
        }
    )
}
