# Base Design Document — Genshin Damage Track

## 1. 開発可能性レビュー（Feasibility Review）

### 1.1 総合評価

| 項目 | 評価 |
|------|------|
| **技術的実現性** | ✅ 高い — すべてのパイプライン段階に成熟したOSSライブラリが存在する |
| **開発難易度** | ⭐⭐☆☆☆（5段階中2） — 画像処理未経験でも既存ライブラリの組み合わせで実現可能 |
| **推定コード規模** | 約 500〜800行（テスト除く） |
| **主要リスク** | OCR精度（ゲーム特有のフォント・エフェクト重畳） |

### 1.2 パイプライン段階別レビュー

#### sample_frames — 難易度: 極低

- OpenCV の `cv2.VideoCapture` で FHD 60fps動画からの等間隔フレーム抽出は**完全に標準的な操作**
- 1秒1フレームの場合、60フレームに1回読み取るだけで実装完了
- 技術的リスク: **なし**

#### crop_region_of_interest — 難易度: 低

- 固定座標でのNumPy配列スライス（`frame[y1:y2, x1:x2]`）
- FHD固定であるため、座標をハードコードまたは設定ファイルで定義可能
- パターン自動検出は後述（1.3節）
- 技術的リスク: **座標の特定作業が手動で必要**（スクリーンショットから目視で計測）

#### read_text_from_image — 難易度: 中

- **最も技術的注意が必要な段階**
- 原神のUI数値は比較的高コントラスト（白/黄色の数字 × 暗い半透明背景）
- 適切な前処理（2値化・コントラスト強調）により、OCR精度は十分確保可能
- 推奨OCRエンジン比較:

| エンジン | 精度 | 速度 | CJK対応 | 導入容易性 |
|----------|------|------|---------|-----------|
| **PaddleOCR** | ◎ | ○ | ◎ | △（依存大） |
| **EasyOCR** | ○ | △ | ◎ | ○ |
| **Tesseract** | △〜○ | ◎ | ○ | ◎ |

- **推奨: PaddleOCR**（ゲームUIテキストに対する認識精度が最も高い傾向）
- 代替: EasyOCR（導入が容易で精度も十分）
- 技術的リスク: **中** — ゲーム画面のエフェクト（パーティクル重畳）が数値認識を阻害する可能性がある。ただし、対象はUI固定領域であるため影響は限定的

#### parse_to_numeric — 難易度: 極低

- 正規表現によるパターンマッチング（例: `r"(\d[\d,]+)"`）
- OCR誤認識への防御的処理（例: `O` → `0`, `l` → `1`）
- 技術的リスク: **なし**

### 1.3 パターン自動検出の実現方法

2種類の領域パターンの自動判別は以下の方法で実現可能:

1. **両領域を同時にクロップし、OCRを実行**
2. **数値として有効な結果が得られた領域を「検出された領域」として確定**
3. **以降のフレームでは確定した領域のみを処理**

この方式はシンプルかつ堅牢であり、テンプレートマッチングやMLモデルは不要。

### 1.4 リスクと緩和策

| リスク | 影響度 | 発生確率 | 緩和策 |
|--------|--------|----------|--------|
| OCR誤認識 | 中 | 中 | 前処理（2値化、膨張処理）、OCRエンジンの信頼度スコアによるフィルタリング |
| 座標ずれ（解像度差異） | 低 | 低 | FHD固定の前提で排除。将来的に他解像度対応時は比率計算 |
| パーティクル・エフェクト重畳 | 低 | 低 | UI領域は半透明パネル上に描画されるため、ゲームエフェクトの影響は限定的 |
| 処理速度 | 低 | 低 | 1fps抽出であり、OCR処理時間は十分余裕がある |

---

## 2. アーキテクチャ設計

### 2.1 技術スタック

| レイヤー | 技術 | 理由 |
|----------|------|------|
| 言語 | **Python 3.11+** | 画像処理・OCRエコシステムが最も充実 |
| 映像処理 | **OpenCV (cv2)** | フレーム抽出・画像前処理のデファクトスタンダード |
| OCR | **PaddleOCR** (推奨) / EasyOCR (代替) | ゲームUI認識精度 |
| 画像前処理 | **OpenCV + NumPy** | 2値化・コントラスト調整 |
| データ保存 | **CSV** (軽量) / **SQLite** (構造化) | グラフ化ツールとの互換性 |
| グラフ化 | **Matplotlib** / **Plotly** | Python標準的可視化ライブラリ |
| CLI | **Typer** | 型安全なCLIフレームワーク |
| パッケージ管理 | **uv** | 高速な依存解決 |

### 2.2 ディレクトリ構成

```
genshin-damage-track/
├── pyproject.toml
├── README.md
├── 機能要件.md
├── BASE_DESIGN.md
├── src/
│   └── genshin_damage_track/
│       ├── __init__.py
│       ├── main.py                  # CLI エントリポイント
│       ├── config.py                # 定数・座標定義・設定
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── sampler.py           # sample_frames
│       │   ├── cropper.py           # crop_region_of_interest
│       │   ├── recognizer.py        # read_text_from_image
│       │   └── parser.py            # parse_to_numeric
│       ├── models.py                # データモデル定義
│       ├── detector.py              # パターン自動検出ロジック
│       ├── orchestrator.py          # パイプライン全体の制御
│       └── visualizer.py            # グラフ化
├── tests/
│   ├── conftest.py
│   ├── test_sampler.py
│   ├── test_cropper.py
│   ├── test_recognizer.py
│   ├── test_parser.py
│   └── test_detector.py
└── fixtures/                        # テスト用サンプル画像
    └── samples/
```

### 2.3 データモデル

```python
from dataclasses import dataclass
from enum import Enum

class RegionPattern(Enum):
    """検出された領域パターン"""
    PATTERN_1 = "party_only"      # パーティ全体ダメージのみ
    PATTERN_2 = "individual_and_party"  # 個人 + パーティ全体

@dataclass
class DamageRecord:
    """1フレームから抽出されたダメージデータ"""
    timestamp_sec: float
    party_damage: int | None
    individual_damage: int | None
    character_name: str | None       # パターン2の場合のみ

@dataclass
class ExtractionResult:
    """パイプライン全体の処理結果"""
    pattern: RegionPattern
    records: list[DamageRecord]
    source_file: str
    fps_sample_rate: float
```

### 2.4 パイプラインフロー

```
                          ┌─────────────────────┐
                          │   Video File (FHD)   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │    sample_frames     │
                          │  (1fps等間隔抽出)     │
                          └──────────┬──────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │  detect_region_pattern         │
                     │  (初回: 両領域を試行→確定)      │
                     │  (2回目以降: 確定済み領域を使用)  │
                     └───────────────┬───────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ crop_region_of_interest │
                          │  (確定領域をクロップ)   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ preprocess_image     │
                          │ (2値化/コントラスト)  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ read_text_from_image │
                          │     (OCR実行)        │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  parse_to_numeric    │
                          │ (文字列→数値変換)     │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   DamageRecord       │
                          │  (結果格納)           │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  CSV / グラフ出力     │
                          └─────────────────────┘
```

### 2.5 CLIインターフェース

```bash
# 基本実行
genshin-damage-track run video.mp4

# サンプリングレート指定
genshin-damage-track run video.mp4 --fps 2

# CSV出力
genshin-damage-track run video.mp4 --output result.csv

# グラフ生成
genshin-damage-track run video.mp4 --plot --plot-output graph.png
```

### 2.6 画像前処理パイプライン（OCR精度向上のための補助処理）

OCRに渡す前に以下の前処理を行い、認識精度を向上させる:

```python
def preprocess_for_ocr(cropped: np.ndarray) -> np.ndarray:
    """OCR前処理: グレースケール → 2値化 → ノイズ除去"""
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    # 適応的2値化（半透明背景に有効）
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    # 微小ノイズ除去
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return cleaned
```

---

## 3. 出力仕様

### 3.1 CSV出力フォーマット

```csv
timestamp_sec,party_damage,individual_damage,character_name
0.0,,,
1.0,12345,,
2.0,24680,,
3.0,,,
```

パターン2の場合:

```csv
timestamp_sec,party_damage,individual_damage,character_name
0.0,,,
1.0,12345,6789,胡桃
2.0,24680,13500,胡桃
3.0,,,
```

### 3.2 グラフ出力

- X軸: 経過時間（秒）
- Y軸: ダメージ値
- パターン2の場合: 個人ダメージとパーティダメージを2系列で表示
- null期間はグラフ上で欠損（途切れ）として表現

---

## 4. 依存パッケージ

```toml
[project]
name = "genshin-damage-track"
requires-python = ">=3.11"
dependencies = [
    "opencv-python>=4.9",
    "paddleocr>=2.7",        # OCRエンジン（推奨）
    "paddlepaddle>=2.6",     # PaddleOCRの依存
    "numpy>=1.26",
    "matplotlib>=3.8",
    "typer>=0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[project.scripts]
genshin-damage-track = "genshin_damage_track.main:app"
```

---

## 5. 開発ロードマイル

### Phase 1: 基盤構築（最小実行可能パイプライン）

- [ ] プロジェクト初期化（pyproject.toml, ディレクトリ構成）
- [ ] `sample_frames` — 動画からのフレーム抽出
- [ ] `crop_region_of_interest` — 固定座標クロッピング（座標は仮値）
- [ ] `read_text_from_image` — OCR実行（PaddleOCR統合）
- [ ] `parse_to_numeric` — 文字列→数値変換
- [ ] 単体テスト（各ステップ）

### Phase 2: 自動検出とデータ出力

- [ ] パターン自動検出ロジック（detector.py）
- [ ] パイプラインオーケストレーション（orchestrator.py）
- [ ] CSV出力
- [ ] CLIエントリポイント

### Phase 3: 可視化と品質向上

- [ ] グラフ生成（visualizer.py）
- [ ] OCR前処理チューニング（実際のゲーム画面での精度検証）
- [ ] 座標の確定（実際のスクリーンショットから計測）
- [ ] エッジケース対応（エフェクト重畳時のフォールバック）

---

## 6. 座標定義（要実測）

以下の座標は、実際のゲーム画面スクリーンショットから計測して確定する必要がある。暫定的にプレースホルダーを定義する。

```python
# config.py — FHD (1920x1080) 基準
REGIONS = {
    "pattern_1": {
        "party_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # 要実測
    },
    "pattern_2": {
        "party_damage":      {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # 要実測
        "individual_damage": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # 要実測
        "character_name":    {"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # 要実測
    },
}
```

**座標特定方法**: ゲーム内で星の幻境をプレイ中にスクリーンショットを取得し、画像ビューアで数値表示領域のピクセル座標を手動計測する。

---

## 7. 結論

本プロジェクトは**技術的に十分に実現可能**である。

- すべてのパイプライン段階に成熟したPythonライブラリが存在する
- 最大の技術課題であるOCR精度も、対象領域が固定UIであるため前処理で十分対処可能
- 画像処理の専門知識がなくても、OpenCV + OCRライブラリのAPIレベルの知識で開発可能
- コード規模は500〜800行程度であり、個人開発として妥当な規模

**開発開始にあたっての前提条件**:
1. 実際のゲーム画面スクリーンショットを少なくとも数枚用意すること（パターン1・2それぞれ）
2. スクリーンショットからROI座標を計測すること
3. PaddleOCR（またはEasyOCR）の環境構築を行うこと
