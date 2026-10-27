# Single-clip dev/test wrapper (mirrors blender-physics run.ps1).
#   ./run.ps1 -Scene grow_ball                      full 9:16 render with sound
#   ./run.ps1 -Scene grow_ball -Fast -Still -Frame 2500    quick low-res PNG check
#   ./run.ps1 -Scene grow_ball -Orient both -SceneArgs @('--growth','8')
param(
    [Parameter(Mandatory = $true)][string]$Scene,
    [ValidateSet('vertical', 'horizontal', 'both')][string]$Orient = 'vertical',
    [switch]$Fast,
    [switch]$Still,
    [int]$Frame = -1,
    [string[]]$SceneArgs = @()
)

$root = $PSScriptRoot
$scenePath = Join-Path $root "scenes\$Scene.py"
if (-not (Test-Path $scenePath)) {
    Write-Error "scene not found: $scenePath"; exit 1
}

$env:NF_FAST = if ($Fast) { '1' } else { '' }
$env:NF_ORIENT = $Orient

$pyArgs = @($scenePath, '--')
if ($Still) { $pyArgs += '--still' }
if ($Frame -ge 0) { $pyArgs += @('--frame', "$Frame") }
$pyArgs += $SceneArgs

python @pyArgs
exit $LASTEXITCODE
