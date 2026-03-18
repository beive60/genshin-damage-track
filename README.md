# genshin-damage-track

原神の星辰の幻境コンテンツにおいて、映像ストリームから累計ダメージ数値を OCR で抽出し、ショートターム DPS（秒間ダメージ）を算出・グラフ化するツールです。

## 機能概要

- FHD (1920×1080) 60fps の動画ファイルから指定レートでフレームをサンプリング
- 固定座標の関心領域 (ROI) を自動検出し、OCR で累計ダメージ数値を抽出
- 画面に表示される累計ダメージの差分から、フレーム間の与ダメージを算出
- 移動平均ウィンドウ（デフォルト: 60 フレーム ＝ 60fps 動画で 1 秒間）でショートターム DPS を計算
- パターン1（合計ダメージのみ: `total-only`）とパターン2（合計＋キャラクター別ダメージ: `per-character`）を `--pattern` オプションで指定可能（デフォルト: `per-character`）
- 結果を CSV ファイルおよびグラフ (PNG) として出力

### パターン

| パターン | 合計ダメージ | キャラクター別ダメージ（最大4人） |
|----------|-------------|-------------------------------|
| パターン1（合計のみ） | ✅ | — |
| パターン2（合計＋個別） | ✅ | ✅（名前・ダメージ・割合） |

#### パターン1 の表示例

```
合計ダメージ
1234567
```

#### パターン2 の表示例

```
合計ダメージ
1234567

太郎: 12345 (67%)
次郎: 678 (12%)
三郎: 90 (8%)
四郎: 10 (1%)
```

### DPS 算出ロジック

ゲーム画面には**累計ダメージ**が表示されます。ツールは以下のように DPS を算出します:

1. 各サンプリングフレームで OCR により累計ダメージを取得
2. OCR が成功した連続フレーム間のダメージ差分（デルタ）を計算
3. `DPS = デルタダメージ ÷ 経過時間（秒）`
4. 設定された平均化区間（デフォルト: 60 フレーム）で移動平均を適用

## 動作環境

- **OS**: Windows 11
- **Python**: 3.11 以上
- **パッケージマネージャ**: [uv](https://docs.astral.sh/uv/)

## 使い方

### 基本実行

```powershell
genshin-damage-track extract video.mp4
# → video.csv が生成される
```

### オプション

```powershell
# パターンを明示的に指定（デフォルト: per-character）
genshin-damage-track extract video.mp4 --pattern total-only
genshin-damage-track extract video.mp4 --pattern per-character

# サンプリングレートを 2fps に指定
genshin-damage-track extract video.mp4 --fps 2

# DPS 平均化区間を 120 フレーム（60fps 動画で 2 秒窓）に変更
genshin-damage-track extract video.mp4 --dps-interval 120

# CSV 出力先を明示的に指定（デフォルト: <動画ファイル名>.csv）
genshin-damage-track extract video.mp4 --output result.csv

# グラフを生成して PNG に保存
genshin-damage-track extract video.mp4 --plot --plot-output graph.png

# すべてのオプションを組み合わせ
genshin-damage-track extract video.mp4 --fps 2 --dps-interval 60 --output result.csv --plot --plot-output graph.png
```

### CSV からグラフを再生成

OCR によるデータ欠損を手動で修正した CSV からグラフを再生成できます。
動画パイプラインを再実行する必要はありません。

```powershell
# CSV を読み込んでグラフをインタラクティブに表示
genshin-damage-track plot result.csv

# グラフを PNG ファイルとして保存
genshin-damage-track plot result.csv --plot-output graph.png

# DPS 平均化区間をグラフタイトルに反映（デフォルト: 60）
genshin-damage-track plot result.csv --dps-interval 120 --plot-output graph.png
```

**ワークフロー例:**

1. 動画からデータを抽出（CSV が自動生成される）
   ```powershell
   genshin-damage-track extract video.mp4
   # → video.csv が生成される
   ```
2. CSV をエディタで開き、OCR 誤認識の値を手動で修正
3. 修正済み CSV からグラフを生成
   ```powershell
   genshin-damage-track plot video.csv --plot-output graph.png
   ```

### デバッグ・診断

期待した結果が得られない場合、以下のオプションで詳細情報を取得できます。

```powershell
# 詳細ログを有効化（OCR 生テキスト、パース結果、ROI 座標等を表示）
genshin-damage-track extract video.mp4 --verbose

# クロップ画像を保存して ROI 座標を目視確認
genshin-damage-track extract video.mp4 --save-crops ./debug_crops

# 両方を組み合わせてフルデバッグ
genshin-damage-track extract video.mp4 -v --save-crops ./debug_crops
```

`--verbose` (`-v`) を指定すると、以下の情報がログ出力されます:

- **動画メタデータ**: 解像度、FPS、総フレーム数、サンプリング間隔
- **パターン検出**: 使用中のパターン設定
- **フレーム抽出**: 各フレームの OCR 生テキスト → パース後の数値
- **ROI クロッピング**: 切り出し座標とサイズ
- **統計サマリ**: 有効 OCR フレーム数、DPS レコード数

`--save-crops` を指定すると、各フレームの切り出し画像が PNG として保存され、ROI 座標の妥当性を目視確認できます。

### CSV 出力フォーマット

#### パターン1（total-only）

```csv
timestamp_sec,total_damage,delta_damage,dps
1.0,1500,1500,1500.00
2.0,3500,2000,2000.00
3.0,5250,1750,1750.00
```

#### パターン2（per-character）

```csv
timestamp_sec,total_damage,delta_damage,dps,胡桃_total_damage,胡桃_delta_damage,胡桃_dps,胡桃_pct,夜蘭_total_damage,夜蘭_delta_damage,夜蘭_dps,夜蘭_pct
1.0,1500,1500,1500.00,900,,900.00,60.0,600,,600.00,40.0
2.0,3500,2000,2000.00,2100,1200,1200.00,60.0,1400,800,800.00,40.0
```

#### カラム説明

**マスターデータ（手動修正対象）:**

- `total_damage`: 画面表示の累計ダメージ
- `{name}_total_damage`: キャラクター別の累計ダメージ

**派生データ（`plot` コマンドで自動再計算）:**

- `delta_damage`: 直前の OCR 成功フレームからの差分ダメージ
- `dps`: 平均化区間内のショートターム DPS (damage/sec)
- `{name}_delta_damage`: キャラクター別の差分ダメージ
- `{name}_dps`: キャラクター別の DPS（全体 DPS × 割合）
- `{name}_pct`: キャラクター別のダメージ割合（%）
- OCR が失敗したフレームはスキップされ、次の成功フレームとの差分が計算されます
- `plot` コマンドは CSV からマスターデータのみ読み取り、派生データを再計算します

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
│   ├── test_detector.py
│   ├── test_orchestrator.py
│   └── test_visualizer.py
└── fixtures/
    └── samples/
```

## ライセンス

[LICENSE](LICENSE) を参照してください。