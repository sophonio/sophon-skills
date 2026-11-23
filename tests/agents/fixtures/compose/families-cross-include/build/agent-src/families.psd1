# Composer fixture: two families. Each family's souls and fragments live beside its family file.
@{
  Families = @(
    @{ Id = 'one'; Path = 'build/agent-src/family.psd1' }
    @{ Id = 'two'; Path = 'build/agent-src/families/two/family.psd1' }
  )
}
