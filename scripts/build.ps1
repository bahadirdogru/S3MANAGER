#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "S3MANAGER derleniyor (Windows onedir)..." -ForegroundColor Cyan

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "venv bulunamadi. Olusturuluyor..." -ForegroundColor Yellow
    python -m venv venv
}

& "venv\Scripts\python.exe" -m pip install -q -r requirements.txt -r requirements-dev.txt

& "venv\Scripts\pyinstaller.exe" s3manager.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "Derleme basarisiz." -ForegroundColor Red
    exit $LASTEXITCODE
}

$OutDir = Join-Path $Root "dist\S3MANAGER"
$OutExe = Join-Path $OutDir "S3MANAGER.exe"
if (-not (Test-Path $OutExe)) {
    Write-Host "Cikti dosyasi bulunamadi: $OutExe" -ForegroundColor Red
    exit 1
}

$SizeMb = [math]::Round(
    ((Get-ChildItem -Path $OutDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB),
    1
)
Write-Host "Basarili: $OutDir ($SizeMb MB)" -ForegroundColor Green

$ZipPath = Join-Path $Root "dist\S3MANAGER.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path $OutDir -DestinationPath $ZipPath
$ZipSizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "Arsiv: $ZipPath ($ZipSizeMb MB)" -ForegroundColor Green
