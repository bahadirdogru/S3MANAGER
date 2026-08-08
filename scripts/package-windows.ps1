#Requires -Version 5.1
param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "S3MANAGER paketleniyor (Windows) v$Version..." -ForegroundColor Cyan

& "$PSScriptRoot\build.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:VERSION = $Version
& makensis "/DAPP_VERSION=$Version" "$PSScriptRoot\installer\windows.nsi"
if ($LASTEXITCODE -ne 0) {
    Write-Host "NSIS derlemesi basarisiz. NSIS kurulu mu? (choco install nsis)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$PortableZip = Join-Path $Root "dist\S3MANAGER-$Version-windows-portable.zip"
if (Test-Path $PortableZip) { Remove-Item $PortableZip -Force }
Compress-Archive -Path (Join-Path $Root "dist\S3MANAGER") -DestinationPath $PortableZip

$Setup = Join-Path $Root "dist\S3MANAGER-$Version-windows-setup.exe"
Write-Host "Installer: $Setup" -ForegroundColor Green
Write-Host "Portable:  $PortableZip" -ForegroundColor Green
