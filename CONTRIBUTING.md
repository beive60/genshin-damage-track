# コントリビューションガイド

本プロジェクトへの貢献方法について説明します。

## 開発環境のセットアップ

[README.md](README.md) の「セットアップ」セクションに従い、Windows 11 上で uv を用いた仮想環境を構築してください。

```powershell
git clone https://github.com/beive60/genshin-damage-track.git
cd genshin-damage-track
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

## 開発フロー

1. `main` ブランチから作業ブランチを作成する
2. コードを変更し、テストを追加・更新する
3. `python -m pytest tests/ -v` で全テストが通ることを確認する
4. Pull Request を作成する

```powershell
git checkout -b feature/your-feature
# コードの変更
python -m pytest tests/ -v
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature
```

## コーディング規約

- Python 3.11+ の型ヒントを使用する
- `from __future__ import annotations` を各モジュールの先頭に記述する
- docstring は英語で記述する（NumPy/Google スタイル）
- テストは `tests/` ディレクトリに `test_<module>.py` の命名規則で配置する

## テストの実行

```powershell
# 全テスト実行
python -m pytest tests/ -v

# カバレッジ付き実行
python -m pytest tests/ -v --cov=genshin_damage_track --cov-report=term-missing
```

---

## ローカルビルド・リリース手順

物理ハードウェアトークン（コード署名用）への依存により、クラウド CI/CD 上での完全自動化が困難なため、ローカル環境でのビルド・署名・リリースの手順を以下に定義します。

手動介入を最小限に抑え、ヒューマンエラーを排除するためにスクリプトベースのパイプラインを採用します。

### 前提条件

| 項目 | 要件 |
|------|------|
| OS | Windows 11 |
| Python | 3.11+ |
| パッケージマネージャ | [uv](https://docs.astral.sh/uv/) |
| ビルドツール | [PyInstaller](https://pyinstaller.org/) |
| 署名ツール | Windows SDK の `signtool.exe` |
| 物理トークン | コード署名証明書が格納されたハードウェアトークン |
| リリースツール | [GitHub CLI (gh)](https://cli.github.com/) |

### ステップ 1: 隔離環境でのビルド

ホスト OS の環境汚染を防ぐため、クリーンな仮想環境上で PyInstaller を実行し、スタンドアロン実行ファイルを生成します。

```powershell
# クリーンなビルド用仮想環境を作成
uv venv .venv-build
.venv-build\Scripts\activate

# 依存パッケージと PyInstaller をインストール
uv pip install .
uv pip install pyinstaller

# スタンドアロン実行ファイルを生成
pyinstaller --onefile --name genshin-damage-track src/genshin_damage_track/main.py

# 生成物の確認
dir dist\genshin-damage-track.exe
```

> **重要**: ビルド用の仮想環境 (`.venv-build`) は開発用 (`.venv`) とは分離してください。これにより、開発用パッケージ（pytest 等）が成果物に混入することを防ぎます。

### ステップ 2: 物理トークンを用いたコード署名

手動での署名操作を排除し、`signtool.exe` による CLI ベースの署名を行います。

```powershell
# 物理トークンが接続されていることを確認した上で実行
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a ".\dist\genshin-damage-track.exe"
```

| パラメータ | 説明 |
|-----------|------|
| `/tr` | RFC 3161 タイムスタンプサーバーの URL |
| `/td sha256` | タイムスタンプのダイジェストアルゴリズム |
| `/fd sha256` | ファイルのダイジェストアルゴリズム |
| `/a` | 適切な証明書を自動選択 |

署名の検証:

```powershell
signtool verify /pa ".\dist\genshin-damage-track.exe"
```

### ステップ 3: GitHub CLI によるリリース

Web ブラウザでの手動アップロードを廃止し、`gh` コマンドでリリースを作成します。

```powershell
# バージョンタグを作成
git tag v0.1.0
git push origin v0.1.0

# リリースを作成し、署名済み実行ファイルをアップロード
gh release create v0.1.0 ".\dist\genshin-damage-track.exe" --title "Release v0.1.0" --generate-notes
```

### 一括実行スクリプト

上記のステップ 1〜3 を一括で実行する PowerShell スクリプトの例です。

```powershell
# release.ps1 — ローカルビルド・署名・リリースの一括実行スクリプト
param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

Write-Host "=== Step 1: Build ===" -ForegroundColor Cyan

# クリーンなビルド用仮想環境を作成
if (Test-Path .venv-build) { Remove-Item -Recurse -Force .venv-build }
uv venv .venv-build
& .venv-build\Scripts\activate.ps1
uv pip install .
uv pip install pyinstaller
pyinstaller --onefile --name genshin-damage-track src/genshin_damage_track/main.py

Write-Host "=== Step 2: Sign ===" -ForegroundColor Cyan

signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a ".\dist\genshin-damage-track.exe"
signtool verify /pa ".\dist\genshin-damage-track.exe"

Write-Host "=== Step 3: Release ===" -ForegroundColor Cyan

git tag "v$Version"
git push origin "v$Version"
gh release create "v$Version" ".\dist\genshin-damage-track.exe" --title "Release v$Version" --generate-notes

Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Released v$Version successfully."
```

使用例:

```powershell
.\release.ps1 -Version "0.1.0"
```

> **注意**: 物理トークンが接続されていない状態でスクリプトを実行すると、ステップ 2 の署名処理でエラーが発生します。トークンが正しく接続されていることを確認してから実行してください。
