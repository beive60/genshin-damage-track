# コントリビューションガイド

本プロジェクトへの貢献方法について説明します。

## 開発環境のセットアップ

[README.md](README.md) の「セットアップ」セクションに従い、Windows 11 上で uv を用いた仮想環境を構築してください。

```powershell
git clone https://github.com/beive60/genshin-damage-track.git
cd genshin-damage-track
uv sync --all-extras
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

物理ハードウェアトークン（コード署名用）への依存により、ビルド・署名・リリースはローカル環境で実行します。

### 前提条件

| 項目 | 要件 |
| --- | --- |
| OS | Windows 11 |
| Python | 3.11+ |
| パッケージマネージャ | [uv](https://docs.astral.sh/uv/) |
| ビルドツール | [PyInstaller](https://pyinstaller.org/) |
| 署名ツール | Windows SDK の `signtool.exe` |
| 物理トークン | コード署名証明書が格納されたハードウェアトークン |
| リリースツール | [GitHub CLI (gh)](https://cli.github.com/) |

### 実行方法

#### 一括実行（推奨）

[`scripts/release.ps1`](scripts/release.ps1) がビルド → 署名 → リリースを順次実行します。詳細は `Get-Help .\scripts\release.ps1` を参照してください。

```powershell
.\scripts\release.ps1 -Version "0.1.0"
```

VS Code からは **Terminal → Run Task → Release** でも実行できます。

#### 個別実行

VS Code タスクで各ステップを個別に実行できます（**Terminal → Run Task**）:

| タスク | 内容 |
| --- | --- |
| **Build Executable** | `.venv-build` 上で PyInstaller ビルド |
| **Sign Executable** | `signtool` によるコード署名 |
| **Verify Signature** | 署名の検証 |

**重要**: ビルド用の仮想環境 (`.venv-build`) は開発用 (`.venv`) とは分離されます。これにより、開発用パッケージ（pytest 等）が成果物に混入することを防ぎます。

**注意**: 物理トークンが接続されていない状態で署名を実行するとエラーになります。
