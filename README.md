# genshin-damage-track

原神の星辰の幻境コンテンツにおいて、映像ストリームから累計ダメージ数値を OCR で抽出し、ショートターム DPS（秒間ダメージ）を算出・グラフ化するツールです。

## 機能概要

- FHD (1920×1080) 60fps の動画ファイルから指定レートでフレームをサンプリング
- 固定座標の関心領域 (ROI) を自動検出し、OCR で累計ダメージ数値を抽出
- 画面に表示される累計ダメージの差分から、フレーム間の与ダメージを算出
- 移動平均ウィンドウ（デフォルト: 60 フレーム ＝ 60fps 動画で 1 秒間）でショートターム DPS を計算
- パターン1（合計ダメージのみ）とパターン2（合計＋キャラクター別ダメージ）を自動判別
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
genshin-damage-track video.mp4
```

### オプション

```powershell
# サンプリングレートを 2fps に指定
genshin-damage-track video.mp4 --fps 2

# DPS 平均化区間を 120 フレーム（60fps 動画で 2 秒窓）に変更
genshin-damage-track video.mp4 --dps-interval 120

# CSV ファイルとして出力
genshin-damage-track video.mp4 --output result.csv

# グラフを生成して PNG に保存
genshin-damage-track video.mp4 --plot --plot-output graph.png

# すべてのオプションを組み合わせ
genshin-damage-track video.mp4 --fps 2 --dps-interval 60 --output result.csv --plot --plot-output graph.png
```

### デバッグ・診断

期待した結果が得られない場合、以下のオプションで詳細情報を取得できます。

```powershell
# 詳細ログを有効化（OCR 生テキスト、パース結果、ROI 座標等を表示）
genshin-damage-track video.mp4 --verbose --output result.csv

# クロップ画像を保存して ROI 座標を目視確認
genshin-damage-track video.mp4 --save-crops ./debug_crops --output result.csv

# 両方を組み合わせてフルデバッグ
genshin-damage-track video.mp4 -v --save-crops ./debug_crops --output result.csv
```

`--verbose` (`-v`) を指定すると、以下の情報がログ出力されます:

- **動画メタデータ**: 解像度、FPS、総フレーム数、サンプリング間隔
- **パターン検出**: 各プローブフレームでの OCR テキストとパース結果
- **フレーム抽出**: 各フレームの OCR 生テキスト → パース後の数値
- **ROI クロッピング**: 切り出し座標とサイズ
- **統計サマリ**: 有効 OCR フレーム数、DPS レコード数

`--save-crops` を指定すると、各フレームの切り出し画像が PNG として保存され、ROI 座標の妥当性を目視確認できます。

### CSV 出力フォーマット

```csv
timestamp_sec,dps,delta_damage,total_damage
1.0,1500.00,1500,1500
2.0,2000.00,2000,3500
3.0,1750.00,1750,5250
```

- `dps`: 平均化区間内のショートターム DPS (damage/sec)
- `delta_damage`: 直前の OCR 成功フレームからの差分ダメージ
- `total_damage`: 画面表示の累計ダメージ
- OCR が失敗したフレームはスキップされ、次の成功フレームとの差分が計算されます

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
│   └── test_orchestrator.py
└── fixtures/
    └── samples/
```

## ライセンス

[LICENSE](LICENSE) を参照してください。