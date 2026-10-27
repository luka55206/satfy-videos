# Prove the Claude-in-Chrome browser just selected is the Edge on THIS PC, not the owner's other
# PC. The extension's own "isLocal" flag is NOT proof: another PC's browser on the same account
#  can report isLocal:true too, and display names drift
# ("Browser 1" / "Browser 2" / "Automation").
#
# How: first set a random marker as the page title THROUGH THE EXTENSION
#   (javascript_tool: document.title = 'NFLOCAL-<random>'), then run this. It looks for the
#   marker in this PC's Edge window titles; if the tab isn't the active one it Ctrl+Tab-cycles
#   via activate_edge_tab.ps1. A window on another machine can never show up here.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/crosspost/scripts/verify_local_browser.ps1 -Marker NFLOCAL-7Q4K2
#
# Exit 0 + "LOCAL" = the selected browser drives this PC's Edge.
# Exit 1 + "NOT_LOCAL" = wrong browser; select another deviceId (or start Edge) and re-check.
param([Parameter(Mandatory)][string]$Marker)

$titles = Get-Process msedge -ErrorAction SilentlyContinue | Where-Object MainWindowTitle | ForEach-Object MainWindowTitle
if (-not $titles) { Write-Output "NOT_LOCAL: no Edge window on this PC"; exit 1 }
if ($titles -match [regex]::Escape($Marker)) { Write-Output "LOCAL: $($titles -join ' | ')"; exit 0 }

# The marked tab may exist but not be the active one: cycle this PC's Edge tabs to find it.
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'activate_edge_tab.ps1') -TitleMatch ([regex]::Escape($Marker)) | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Output "LOCAL (after tab cycle)"; exit 0 }
Write-Output "NOT_LOCAL: marker '$Marker' is in no Edge window on this PC"
exit 1
