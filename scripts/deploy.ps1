# Deploiement INTELO2026/fraud-challenge
# Lancez dans PowerShell :  .\scripts\deploy.ps1
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "=== Hackathon INTELO2026 - deploiement ===" -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Installez GitHub CLI: https://cli.github.com/" -ForegroundColor Red
    exit 1
}

$authOk = $false
try {
    gh auth status *> $null
    if ($LASTEXITCODE -eq 0) { $authOk = $true }
} catch {}

if (-not $authOk) {
    Write-Host "Ouvrez le navigateur pour vous connecter a GitHub (compte admin INTELO2026)..." -ForegroundColor Yellow
    gh auth login -h github.com -p https -w
}

gh repo view INTELO2026/fraud-challenge *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creation du depot public..." -ForegroundColor Yellow
    gh repo create INTELO2026/fraud-challenge --public --description "Hackathon IT - detection fraude INTELO2026"
}

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin https://github.com/INTELO2026/fraud-challenge.git
}

git add README.md fraud_detection.py tests data scripts .github requirements.txt pytest.ini .gitignore DEPLOIEMENT.md
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Hackathon INTELO2026: defi fraude + CI"
}

git branch -M main
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK - https://github.com/INTELO2026/fraud-challenge" -ForegroundColor Green
} else {
    Write-Host "Echec du push. Verifiez droits org INTELO2026 et connexion gh." -ForegroundColor Red
    exit 1
}
