# Publish to GitHub (run once after: gh auth login)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

gh auth status | Out-Null

git branch -M main

gh repo create Mi6aBar/tp-transas-user-chart --public `
  --description "T&P TRANSAS USER CHART - portable .aiz builder. Developer: t.me/mishabar | Project: t.me/sea_apks" `
  --source . --remote origin --push 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote remove origin 2>$null
    git remote add origin https://github.com/Mi6aBar/tp-transas-user-chart.git
    git push -u origin main
}

$Exe = Join-Path (Split-Path $Root -Parent) 'T&P_Program\TP_Transas.exe'
if (Test-Path $Exe) {
    gh release create v1.0 --title "v1.0" --notes "T&P TRANSAS USER CHART v1.0`nDeveloper: t.me/mishabar`nProject: t.me/sea_apks" $Exe
}

Write-Host "Done: https://github.com/Mi6aBar/tp-transas-user-chart"
