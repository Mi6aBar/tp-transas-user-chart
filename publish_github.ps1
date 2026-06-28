# Publish to GitHub (run once after: gh auth login)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Gh = 'C:\Program Files\GitHub CLI\gh.exe'
if (-not (Test-Path $Gh)) {
    $Gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
}
if (-not $Gh) {
    throw 'GitHub CLI not found. Install: winget install GitHub.cli'
}

& $Gh auth status | Out-Null

git branch -M main

$remoteExists = git remote get-url origin 2>$null
if (-not $remoteExists) {
    & $Gh repo create Mi6aBar/tp-transas-user-chart --public `
        --description "T&P CHART MASTER - portable ECDIS user charts from ADC T&P (Transas, Furuno, JRC). Developer: t.me/mishabar | Project: t.me/sea_apks" `
        --source . --remote origin --push 2>$null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin https://github.com/Mi6aBar/tp-transas-user-chart.git
        git push -u origin main
    }
} else {
    git push -u origin main
}

& $Gh repo edit Mi6aBar/tp-transas-user-chart `
    --description "T&P CHART MASTER - portable ECDIS user charts from ADC T&P (Transas, Furuno, JRC). Developer: t.me/mishabar | Project: t.me/sea_apks"

$Exe = Join-Path (Split-Path $Root -Parent) 'T&P_Program_v1.1\TP_Chart_Master.exe'
if (Test-Path $Exe) {
    $notes = @"
T&P CHART MASTER v1.1

- Transas .aiz (route + world)
- Furuno BETA / BETA2 (.xml folders, 200 points per file)
- JRC JAN-7201/9201 .csv
- Route PDF auto-watcher, notice list, RU/EN UI

Developer: https://t.me/mishabar
Project: https://t.me/sea_apks
"@
    & $Gh release create v1.1 --title "v1.1 - T&P CHART MASTER" --notes $notes $Exe
}

Write-Host "Done: https://github.com/Mi6aBar/tp-transas-user-chart"
