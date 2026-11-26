# repo-science: a synthetic 12-row assay table (data/assay.csv) with a repeated experimental unit id (a3) and one NA
# (b6), and an evidence bundle (evidence/bundle-planted.json) whose claim says 1.6 where its analysis says 1.5.
# The bundle's analysis record was produced by the statistics skill, so only the claimed number is planted. The two
# schema names in the bundle start with the JSON escape \u0073: the scenario lint forbids that product word in a
# fixture file, and the parsed value is the exact schema name the evidence skill requires.
@{
  Description = 'Synthetic assay table with a repeated unit id and one NA, and an evidence bundle with one planted number mismatch'
  Patches = @{}
}
