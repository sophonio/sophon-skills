# Buildersoft video family: roster and shared values for agents/<id>/ (registered in build/agent-src/families.psd1).
# Data only: loaded with Import-PowerShellDataFile, so no [ordered] and no expressions.
# This folder holds the family's own souls/ and fragments/soul/; it shares nothing with the development family.
# One agent, so the whenToUse sibling rule does not apply, and no fragment uses CommitTrailer or PrFooter, so
# the attribution values are absent on purpose. SkillPolicy names the marketplace skill the agent drives:
# requires.skills must equal it, its ffmpeg.* tools may be named and pinned, and requires.tools is the
# sorted union of the built-in pins and ExtraRequiredTools. message.send may be named (delivery on request)
# but never pinned. Design: docs/plans/2026-11-15-ffmpeg-video-design.md (section 3.9 and 3.10).
@{
  Id = 'video'
  FamilyMajor = 1
  FamilyVersion = '1.0.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'ai'
  RequiredTag = 'video'
  Lead = 'video-producer'
  ReadmeCaps = @{ Lead = 12288; Other = 12288 }
  SkillPolicy = @{
    Skills = @(
      @{ Name = 'ffmpeg-video'; MinVersion = '1.0.0' }
    )
    ExtraRequiredTools = @('document.upload', 'media.image', 'media.video', 'music.generate', 'video.generate')
  }
  AllowRestrictedMentions = @('message.send')
  Values = @{
    SkillName = 'ffmpeg-video'
  }
  AllowedHosts = @(
    'sophon.buildersoft.io',
    'marketplace.sophon.buildersoft.io',
    'github.com'
  )
  Credits = @{
    ffmpegskill = 'kajisho5/ffmpeg-skill (MIT, © 2026 kajisho5)'
  }
  Agents = @(
    @{
      Id = 'video-producer'
      DisplayName = 'Video Producer'
      SoulCap = 24576
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-media-ground-rules',
        '02-media-setup-check',
        '03-media-paths',
        '04-media-review',
        '05-media-delivery',
        '06-media-failures'
      )
      Credits = @('ffmpegskill')
    }
  )
}
