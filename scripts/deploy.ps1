# Déploiement INTELO2026/fraud-challenge — à lancer une fois connecté à GitHub
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Hackathon INTELO2026 — déploiement ===" -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Installez GitHub CLI: https://cli.github.com/" -ForegroundColor Red
    exit 1
}

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Connexion GitHub requise (navigateur)..." -ForegroundColor Yellow
    gh auth login -h github.com -p https -w
}

Write-Host "Vérification du dépôt distant..." -ForegroundColor Gray
$repoExists = gh repo view INTELO2026/fraud-challenge 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Création du dépôt public INTELO2026/fraud-challenge ..." -ForegroundColor Yellow
    gh repo create INTELO2026/fraud-challenge --public --description "Hackathon IT — détection de fraude (INTELO2026)"
}

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin https://github.com/INTELO2026/fraud-challenge.git
}

git add README.md fraud_detection.py tests data scripts .github requirements.txt pytest.ini .gitignore DEPLOIEMENT.md
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Hackathon INTELO2026: défi fraude + CI"
}

git branch -M main
git push -u origin main

Write-Host ""
Write-Host "OK — Dépôt en ligne:" -ForegroundColor Green
Write-Host "https://github.com/INTELO2026/fraud-challenge"
Write-Host ""
Write-Host "Prochaines étapes manuelles sur GitHub (Settings):" -ForegroundColor Yellow
Write-Host "  1. Actions → autoriser workflows sur PR depuis forks"
Write-Host "  2. Branches → protéger main + exiger le check CI"
