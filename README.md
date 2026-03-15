# genshin-damage-track

原神の星辰の幻境コンテンツにおいて、映像ストリームからダメージ数値をリアルタイムで抽出し、時間経過に伴う変化をグラフ化するツールです。

## 機能概要

- FHD (1920×1080) 60fps の動画ファイルから指定レートでフレームをサンプリング
- 固定座標の関心領域 (ROI) を自動検出し、OCR でダメージ数値を抽出
- パーティ全体ダメージ（パターン1）または個人＋パーティダメージ（パターン2）を自動判別
- 結果を CSV ファイルおよびグラフ (PNG) として出力

### パターン

| パターン | パーティダメージ | 個人ダメージ | キャラクター名 |
|----------|----------------|-------------|--------------|
| パターン1（パーティのみ） | ✅ | — | — |
| パターン2（個人＋パーティ） | ✅ | ✅ | ✅ |

## 動作環境

- **OS**: Windows 11
- **Python**: 3.11 以上
- **パッケージマネージャ**: [uv](https://docs.astral.sh/uv/)

## セットアップ

### 1. uv のインストール

PowerShell を開き、以下を実行します。

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

インストール後、ターミナルを再起動して `uv` コマンドが使えることを確認します。

```powershell
uv --version
```

### 2. リポジトリのクローン

```powershell
git clone https://github.com/beive60/genshin-damage-track.git
cd genshin-damage-track
```

### 3. 仮想環境の作成と依存パッケージのインストール

```powershell
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

> **補足**: `uv venv` は `.venv` ディレクトリに Python 仮想環境を作成します。`.[dev]` を指定することで、テスト用の依存パッケージ（pytest 等）も同時にインストールされます。

## 使い方

### 基本実行

```powershell
genshin-damage-track run video.mp4
```

### オプション

```powershell
# サンプリングレートを 2fps に指定
genshin-damage-track run video.mp4 --fps 2

# CSV ファイルとして出力
genshin-damage-track run video.mp4 --output result.csv

# グラフを生成して PNG に保存
genshin-damage-track run video.mp4 --plot --plot-output graph.png

# すべてのオプションを組み合わせ
genshin-damage-track run video.mp4 --fps 2 --output result.csv --plot --plot-output graph.png
```

### CSV 出力フォーマット

```csv
timestamp_sec,party_damage,individual_damage,character_name
0.0,,,
1.0,12345,,
2.0,24680,13500,胡桃
3.0,,,
```

- 数値が検出されなかったフレームは空欄（null）で表現されます
- パターン1 の場合、`individual_damage` と `character_name` は常に空欄です

## テストの実行

```powershell
uv pip install -e ".[dev]"
python -m pytest tests/ -v
```

## プロジェクト構成

```
genshin-damage-track/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── src/
│   └── genshin_damage_track/
│       ├── __init__.py
│       ├── main.py              # CLI エントリポイント
│       ├── config.py            # 定数・座標定義
│       ├── models.py            # データモデル
│       ├── detector.py          # パターン自動検出
│       ├── orchestrator.py      # パイプライン制御
│       ├── visualizer.py        # CSV/グラフ出力
│       └── pipeline/
│           ├── __init__.py
│           ├── sampler.py       # フレーム抽出
│           ├── cropper.py       # ROI クロッピング
│           ├── recognizer.py    # OCR 実行
│           └── parser.py        # 数値変換
├── tests/
│   ├── conftest.py
│   ├── test_sampler.py
│   ├── test_cropper.py
│   ├── test_recognizer.py
│   ├── test_parser.py
│   └── test_detector.py
└── fixtures/
    └── samples/
```

## ライセンス

[LICENSE](LICENSE) を参照してください。