#Requires -Version 5.1
param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-MakensisPath {
    $cmd = Get-Command makensis -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($path in @(
        "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
        "$env:ProgramFiles\NSIS\makensis.exe",
        "$env:ChocolateyInstall\tools\NSIS\makensis.exe"
    )) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

Write-Host "S3MANAGER paketleniyor (Windows) v$Version..." -ForegroundColor Cyan

& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$makensis = Get-MakensisPath
if (-not $makensis) {
    Write-Host "makensis bulunamadi. NSIS kurulu mu? https://nsis.sourceforge.io/" -ForegroundColor Red
    exit 1
}

$env:VERSION = $Version
& $makensis "/DAPP_VERSION=$Version" "$PSScriptRoot\installer\windows.nsi"
if ($LASTEXITCODE -ne 0) {
    Write-Host "NSIS derlemesi basarisiz. NSIS kurulu mu? https://nsis.sourceforge.io/" -ForegroundColor Red
    exit $LASTEXITCODE
}

$PortableZip = Join-Path $Root "dist\S3MANAGER-$Version-windows-portable.zip"
if (Test-Path $PortableZip) { Remove-Item $PortableZip -Force }
Compress-Archive -Path (Join-Path $Root "dist\S3MANAGER") -DestinationPath $PortableZip

$Setup = Join-Path $Root "dist\S3MANAGER-$Version-windows-setup.exe"
Write-Host "Installer: $Setup" -ForegroundColor Green
Write-Host "Portable:  $PortableZip" -ForegroundColor Green
