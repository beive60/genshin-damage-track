# genshin-damage-track

原神の星辰の幻境コンテンツ「DPS計測かかし++」において、映像ストリームから累計ダメージ数値を OCR で抽出し、ショートターム DPS（秒間ダメージ）を算出・グラフ化するツールです。

## 機能概要

DPS計測かかし++（Kosmos氏投稿、ステージGUID：13031458938）の動画ファイルを入力として、以下の処理を行います:

- FHD (1920×1080) 60fps の動画ファイルから指定レートでフレームをサンプリング
- 累計ダメージ数値を抽出
- 画面に表示される累計ダメージの差分から、フレーム間の与ダメージを算出
- 瞬間 DPS（差分ダメージ ÷ 経過時間）をデフォルトで出力。`--dps-interval N`（N > 1）を指定すると N サンプルの移動平均 DPS に切替可能
- パターン1（合計ダメージのみ: `total-only`）とパターン2（合計＋キャラクター別ダメージ: `per-character`）を `--pattern` オプションで指定可能（デフォルト: `per-character`）
- 結果を CSV ファイルおよびグラフ (PNG) として出力

### 表示パターンの違い

| パターン | 合計ダメージ | キャラクター別ダメージ |
| --- | --- | --- |
| 簡易表示（合計のみ） | x | — |
| 詳細表示（合計＋個別） | x | x |

![簡易表示](./assets/簡易表示.png)
![詳細表示](./assets/詳細表示.png)

### DPS 算出ロジック

ゲーム画面には累計ダメージが表示されます。ツールは以下のように DPS を算出します:

1. 各サンプリングフレームで OCR により累計ダメージを取得
2. OCR が成功した連続フレーム間のダメージ差分（デルタ）を計算
3. `DPS = デルタダメージ ÷ 経過時間（秒）`（瞬間 DPS）
4. `--dps-interval N`（N > 1）指定時、N サンプルの移動平均を適用（デフォルト: 1 = 瞬間 DPS）

## 動作環境

- **OS**: Windows 11

## インストール

[Releases](https://github.com/beive60/genshin-damage-track/releases) ページから最新の `genshin-damage-track.exe` をダウンロードし、任意のフォルダに配置してください。

## 使い方

### 基本実行

```powershell
.\genshin-damage-track.exe extract video.mp4
# -> video.csv が生成される
```

### `extract` コマンドのオプション

| オプション | 説明 | デフォルト |
| --- | --- | --- |
| `--pattern` | 表示パターン（`total-only` \| `per-character`） | `per-character` |
| `--fps` | サンプリングレート（fps） | `4` |
| `--dps-interval` | DPS 平均化区間（サンプル数）。1 = 瞬間 DPS | `1` |
| `--output` | CSV 出力先パス | `<動画ファイル名>.csv` |
| `--plot` | グラフをウィンドウで表示する | ― |
| `--plot-output` | グラフの PNG 出力先パス | ― |
| `--verbose`, `-v` | 詳細ログを表示 | ― |
| `--save-crops` | クロップ画像の保存先ディレクトリ | ― |

#### 使用例

```powershell
# サンプリングレートを 2fps に指定
.\genshin-damage-track.exe extract video.mp4 --fps 2

# 移動平均 DPS（120 サンプル区間）で CSV とグラフを同時出力
.\genshin-damage-track.exe extract video.mp4 --dps-interval 120 --output result.csv --plot --plot-output graph.png
```

### `plot` コマンド

OCR によるデータ欠損を手動で修正した CSV からグラフを再生成できます。
動画パイプラインを再実行する必要はありません。

```powershell
.\genshin-damage-track.exe plot <csv_file> [オプション]
```

| オプション | 説明 | デフォルト |
| --- | --- | --- |
| `--dps-interval` | DPS 平均化区間（サンプル数） | `1` |
| `--plot` | グラフをウィンドウで表示する | ― |
| `--plot-output` | グラフの PNG 出力先パス | ― |

#### 使用例

```powershell
# グラフをインタラクティブに表示
.\genshin-damage-track.exe plot result.csv

# 移動平均 DPS でグラフを PNG に保存
.\genshin-damage-track.exe plot result.csv --dps-interval 120 --plot-output graph.png
```

**ワークフロー例:**

1. 動画からデータを抽出（CSV が自動生成される）

   ```powershell
   .\genshin-damage-track.exe extract video.mp4
   # -> video.csv が生成される
   ```

2. CSV をエディタで開き、OCR 誤認識の値を手動で修正
3. 修正済み CSV からグラフを生成

   ```powershell
   .\genshin-damage-track.exe plot video.csv --plot-output graph.png
   ```

### デバッグ・診断

期待した結果が得られない場合、`extract` コマンドの以下のオプションで詳細情報を取得できます。

| オプション | 出力内容 |
| --- | --- |
| `--verbose`, `-v` | 動画メタデータ、パターン検出、OCR 生テキスト → パース結果、ROI 座標、統計サマリ |
| `--save-crops <dir>` | 各フレームの切り出し画像を PNG として保存（ROI 座標の目視確認用） |

#### 使用例

```powershell
# フルデバッグ（詳細ログ + クロップ画像保存）
.\genshin-damage-track.exe extract video.mp4 -v --save-crops ./debug_crops
```

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

## ライセンス

[LICENSE](LICENSE) を参照してください。
