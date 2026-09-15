# Connect a managed runtime's updater to the existing pinned Desktop package.
# This creates only a directory junction; it never moves or replaces an app.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [Parameter(Mandatory = $true)][string]$CanonicalExe,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$installPath = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
$exePath = [IO.Path]::GetFullPath($CanonicalExe)
$packagePath = Split-Path -Parent $exePath
$releasePath = Split-Path -Parent $packagePath
$managedRelease = Join-Path $installPath 'apps\desktop\release'

if (-not (Test-Path -LiteralPath (Join-Path $installPath 'hermes_cli\main_desktop.py') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $installPath 'apps\desktop\package.json') -PathType Leaf)) {
    throw 'InstallRoot must be a complete Hermes runtime checkout with Desktop sources.'
}
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf) -or
    (Split-Path -Leaf $exePath) -ne 'Hermes.exe' -or
    (Split-Path -Leaf $packagePath) -notin @('win-unpacked', 'win-ia32-unpacked', 'win-arm64-unpacked') -or
    (Split-Path -Leaf $releasePath) -ne 'release') {
    throw 'CanonicalExe must name the existing release\win-*-unpacked\Hermes.exe package.'
}
if ($managedRelease.Equals($releasePath, [StringComparison]::OrdinalIgnoreCase)) {
    [pscustomobject]@{ ManagedRelease = $managedRelease; CanonicalRelease = $releasePath; Linked = $false; Verified = $true }
    return
}
if ($releasePath.StartsWith($managedRelease + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $managedRelease.StartsWith($releasePath + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The two release paths must not contain one another.'
}

$existing = Get-Item -LiteralPath $managedRelease -Force -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.LinkType -ne 'Junction') {
        throw 'The managed release path already exists and is not a junction. Preserve and inspect it before changing the installation.'
    }
    $linkTarget = [IO.Path]::GetFullPath(@($existing.Target)[0]).TrimEnd('\')
    if (-not $linkTarget.Equals($releasePath, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The managed release junction targets a different app. No changes were made.'
    }
} elseif ($VerifyOnly) {
    throw 'The updater cannot see the pinned Desktop package: the managed release junction is missing.'
} else {
    New-Item -ItemType Junction -Path $managedRelease -Target $releasePath | Out-Null
}

$linkedExe = Join-Path (Join-Path $managedRelease (Split-Path -Leaf $packagePath)) 'Hermes.exe'
if (-not (Test-Path -LiteralPath $linkedExe -PathType Leaf) -or
    (Get-FileHash -LiteralPath $linkedExe).Hash -ne (Get-FileHash -LiteralPath $exePath).Hash) {
    throw 'The managed updater and pinned Desktop executable did not read back identically.'
}
[pscustomobject]@{ ManagedRelease = $managedRelease; CanonicalRelease = $releasePath; Linked = $true; Verified = $true }
