# Rules a skill package meets after it leaves this repo (build/SkillLint.psm1).
#
# Each block names the file it mirrors. Sources are pinned to sophon a431e1a64 (v2.2.2) and sophon-marketplace
# remote main b16e0a6. Copy changes from the named source file; do not edit the values by hand. The field-level
# publishing contract (name, version, description, tags, runtime, entrypoint, tools[]) stays in
# build/Build-MarketplacePackages.ps1, which mirrors the marketplace's Publishing/ManifestValidators.cs.
@{
    SophonCommit      = 'a431e1a64'
    MarketplaceCommit = 'b16e0a6'

    # ---------------------------------------------------------------------------------------------------------
    # Reserved package names.
    # Mirrors sophon-marketplace/src/Sophon.Marketplace.Api/Publishing/ReservedPackageNames.cs. Compared ignoring
    # case. System names can never be published, by anyone. Official names and prefixes are publishable only by
    # a SuperAdmin through a JWT or an smk_ key (never a linked-instance slk_ key), and the rule applies only to
    # brand-new packages. This repo is the official publisher and uploads with an smk_ key, so an Official hit is
    # a warning here; a System hit is an error.
    # ---------------------------------------------------------------------------------------------------------
    ReservedNames = @{
        System           = @(
            'sophon', 'admin', 'api', 'marketplace', 'buildersoft', 'www', 'docs', 'registry', 'official',
            'default',
            'con', 'prn', 'aux', 'nul',
            'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
            'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
        )
        Official         = @(
            'content-creator', 'customer-support', 'devops-engineer', 'finance-tracker', 'health-coach',
            'home-automation', 'personal-organizer', 'research-analyst', 'sales-assistant', 'team-coordinator',
            'email-send', 'jira', 'github', 'google-gmail', 'outlook'
        )
        OfficialPrefixes = @('sophon-', 'buildersoft-', 'official-')
    }

    # ---------------------------------------------------------------------------------------------------------
    # Manifest discriminator and permissions.
    # Mirrors sophon-marketplace Publishing/ManifestParser.cs (Discriminate: any explicit non-null type other than
    # skill, plugin or agent is manifest.unknown_type; this repo packages skills only, so only 'skill' is
    # accepted) and Publishing/ManifestValidators.cs (SkillManifestValidator, the permissions rules, applied only
    # under the "permissions" key; Sophon reads "sandbox" first and the marketplace never reads "sandbox").
    # ---------------------------------------------------------------------------------------------------------
    ManifestTypes = @('skill')
    Permissions   = @{
        MaxMemoryMb     = 4096
        # HostnamePattern(); an entry must also not contain '://', '/' or a space.
        HostnamePattern = '^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*(:\d{1,5})?$'
    }

    # ---------------------------------------------------------------------------------------------------------
    # Zip structure.
    # Mirrors sophon/src/Sophon.Skills/Marketplace/PackageArchive.cs (PackageArchiveOptions, ExtractValidated) and
    # sophon-marketplace Publishing/ZipInspector.cs + ZipEntryPaths.cs. Where the two differ the stricter value
    # wins: the client allows 5000 entries (the server 10,000); the server caps the uploaded package at 100 MiB
    # (Configuration/MarketplaceOptions.cs). The ratio is total uncompressed / total compressed over file entries.
    # A symlink entry is Unix mode S_IFLNK in the top 16 bits of ExternalAttributes.
    # ---------------------------------------------------------------------------------------------------------
    Zip = @{
        MaxEntries                = 5000
        MaxTotalUncompressedBytes = 524288000
        MaxEntryUncompressedBytes = 104857600
        MaxCompressionRatio       = 100.0
        MaxPackageBytes           = 104857600
        SymlinkModeMask           = 0xF000
        SymlinkMode               = 0xA000
    }

    # ---------------------------------------------------------------------------------------------------------
    # Tool names.
    # Pattern: sophon/src/Sophon.Core/Agents/Packaging/AgentPackageFormat.cs:63 (the stricter of it and the
    # provider rule ^[a-zA-Z0-9_.-]{1,64}$ in Sophon.Core/Models/TranscriptRepair.cs:12, so a skill tool can be
    # pinned by an agent). Every provider maps '.' to '_' and builds its lookup with ToDictionary
    # (AnthropicProvider.cs:176,221,313; OpenAiCompatibleProvider.cs:224,254), so two loaded tools that are equal
    # after that mapping fail every LLM call. An exact clash with a loaded tool fails the install with
    # TOOL_NAME_CONFLICT and silently skips the whole skill at startup (SkillEngine.cs:74-83,216-252).
    # ---------------------------------------------------------------------------------------------------------
    ToolName = @{
        Pattern   = '^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)*$'
        MaxLength = 64
    }

    # SandboxedTool.cs:100 overwrites params["tool"] with the tool name on every call.
    ReservedParameterNames = @('tool')

    # ---------------------------------------------------------------------------------------------------------
    # Parameter schema subset.
    # sophon/src/Sophon.Skills/ToolParameterValidator.cs checks enum, type, required, properties,
    # additionalProperties, items, pattern, minimum and maximum, and ignores everything else silently.
    # Sophon.Core/Skills/ToolSchemaCleaners.cs strips oneOf and allOf for Gemini and turns non-string enum values
    # into strings with type string (so the model then sends "2", which the validator rejects against [2]).
    # Keep every schema flat: one string type per node, string-only enums, items on every array.
    # ---------------------------------------------------------------------------------------------------------
    Schema = @{
        ForbiddenKeywords = @('$ref', 'oneOf', 'anyOf', 'allOf', 'not')
        Types             = @('string', 'number', 'integer', 'boolean', 'array', 'object')
    }

    # ---------------------------------------------------------------------------------------------------------
    # Moderator review assist (never blocks a publish, but a vendored tree must not trip it).
    # Mirrors sophon-marketplace Publishing/ReviewAssistGenerator.cs (HasScripts :81, HasNativeBinaries :80, the
    # isText sniff: no NUL and valid UTF-8) and Moderation/ModerationService.cs:207 (file preview cap).
    # ---------------------------------------------------------------------------------------------------------
    Vendor = @{
        DeniedExtensions = @('.sh', '.ps1', '.psm1', '.bat', '.cmd', '.exe', '.dll', '.so', '.dylib')
        PreviewCapBytes  = 262144
    }

    # ---------------------------------------------------------------------------------------------------------
    # Folder rule for this repo: a flat skill root, plus an optional lib/ (first-party code and data, flat) and
    # an optional vendor/ that is only allowed next to a vendor.lock.json. The installer writes
    # .sophon-origin.json into the install folder (sophon InstalledPackageStore.cs:43), so no dotfile may ship.
    # ---------------------------------------------------------------------------------------------------------
    Folders = @{
        LibDir        = 'lib'
        LibExtensions = @('.py', '.json')
        VendorDir     = 'vendor'
        VendorLock    = 'vendor.lock.json'
        Notices       = 'THIRD_PARTY_NOTICES.md'
        LockSchema    = 1
    }

    # ---------------------------------------------------------------------------------------------------------
    # Budget warnings (not errors). 1024 characters is a conservative provider-compatibility limit for one tool
    # description (nothing in Sophon enforces it). 48 is the chat, subagent and coding profile cap on core plus
    # pinned tools (sophon/src/Sophon.Core/Skills/ToolSelection/ToolProfile.cs:97,113,168).
    # ---------------------------------------------------------------------------------------------------------
    Budget = @{
        MaxToolDescriptionChars = 1024
        MaxToolsPerSkill        = 48
    }
}
