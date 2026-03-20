<#
.SYNOPSIS
    ローカル環境でビルド・署名・リリースを一括実行する。

.DESCRIPTION
    以下の 3 ステップを順次実行する:
        1. .venv-build 仮想環境を再作成し PyInstaller でスタンドアロン exe を生成
        2. signtool で物理トークンを用いたコード署名と検証
        3. git tag 作成と gh release によるアセットアップロード

    物理ハードウェアトークンが接続されていない場合、ステップ 2 で失敗する。

.PARAMETER Version
    リリースバージョン文字列 (例: "0.1.0")。
    git tag には "v" プレフィックスが自動付与される。

.EXAMPLE
    .\scripts\release.ps1 -Version "0.1.0"

.NOTES
    前提条件: uv, PyInstaller, signtool, gh CLI がパス上に存在すること。
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

# Helper function to check for command existence
function Assert-CommandExists {
    param($command)
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command '$command' not found in PATH. Please install it and try again."
    }
}

try {
    Write-Host "=== 0/5: Check Prerequisites ===" -ForegroundColor Cyan
    "uv", "signtool", "gh" | ForEach-Object { Assert-CommandExists $_ }
    Write-Host "All prerequisites found."

    Write-Host "=== 1/5: Build ===" -ForegroundColor Cyan

    # クリーンなビルド用仮想環境を作成
    if (Test-Path .venv-build) { Remove-Item -Recurse -Force .venv-build }
    $env:UV_PROJECT_ENVIRONMENT = ".venv-build"
    uv sync
    uv run --with pyinstaller pyinstaller genshin-damage-track.spec --noconfirm
    Remove-Item Env:\UV_PROJECT_ENVIRONMENT

    Write-Host "=== 2/5: Sign ===" -ForegroundColor Cyan

    signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a ".\dist\genshin-damage-track.exe"
    signtool verify /pa ".\dist\genshin-damage-track.exe"

    Write-Host "=== 3/5: Zip Artifacts ===" -ForegroundColor Cyan

    $stagingDir = ".\dist\release"
    $zipFileName = "genshin-damage-track-v$($Version).zip"
    $zipPath = ".\dist\$zipFileName"

    # Clean and create staging directory
    if (Test-Path $stagingDir) { Remove-Item -Recurse -Force $stagingDir }
    New-Item -ItemType Directory -Path $stagingDir

    # Copy files to the staging directory
    Copy-Item -Path ".\dist\genshin-damage-track.exe" -Destination $stagingDir
    Copy-Item -Path ".\README.md" -Destination $stagingDir
    Copy-Item -Path ".\LICENSE" -Destination $stagingDir

    # Create the archive from the staging directory's contents
    Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath -Force

    # Clean up the staging directory
    Remove-Item -Recurse -Force $stagingDir

    Write-Host "Created release zip: $zipPath"

    Write-Host "=== 4/5: Release ===" -ForegroundColor Cyan

    Write-Host "Checking GitHub CLI authentication status..."
    gh auth status
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI not authenticated. Please run 'gh auth login' and try again."
    }
    Write-Host "GitHub CLI is authenticated."

    git tag "v$Version"
    git push origin "v$Version"
    
    gh release create "v$Version" $zipPath --title "Release v$Version" --generate-notes

    Write-Host "=== 5/5: Done ===" -ForegroundColor Green
    Write-Host "Released v$Version successfully."
}
catch {
    Write-Host "`nError during release process:" -ForegroundColor Red
    Write-Host "  - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
