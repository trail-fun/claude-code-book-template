# オリエンテーリング用ベース地図サービス 設計書

## サービス概要

オリエンテーリング競技用の地図（OMAP）を作成する際のベース地図を、簡単に生成・ダウンロードできるWebサービス。
国土地理院の高精度データを活用し、従来のOMAPを手動で作る手間を省くことを目的とする。

## ターゲットユーザー

- 一般ユーザー向け（BtoC）
- オリエンテーリング競技の地図作成者

## 主要機能

- 地図上でエリアを範囲選択
- 等高線間隔をユーザーが自由に指定
- 建物・道路・河川レイヤーの表示
- PDF（印刷用）およびGeoTIFF（GISソフト向け）でダウンロード

## データソース

### 地形・等高線
- **国土地理院 基盤地図情報 1mメッシュDEM（航空レーザ測量）**
- ダウンロードURL: https://fgd.gsi.go.jp/download/
- フォーマット: JPGIS（GML/XML形式）→ GeoTIFFに変換して使用
- カバレッジ: 現在全国約46%（未カバー地域は5mメッシュDEMにフォールバック）
- 取得方法: APIなし。**手動で事前ダウンロードしサーバーに保存**する方式（PoC段階はMacローカルに保存）

### 建物・道路・河川
- **OpenStreetMap（OSM）**
- Pythonライブラリ `osmnx` でAPIから動的取得
- 国土地理院基本項目（道路縁・水涯線・建築物外周線）より精度は落ちるが自動化可能

```python
import osmnx as ox

buildings = ox.geometries_from_bbox(north, south, east, west, tags={'building': True})
roads     = ox.graph_from_bbox(north, south, east, west, network_type='all')
water     = ox.geometries_from_bbox(north, south, east, west, tags={'waterway': True})
```

### データ取得戦略のまとめ

| データ種別 | ソース | 取得方法 |
|-----------|--------|---------|
| 等高線・地形 | 国土地理院1mDEM | 手動DL → サーバーに保存 |
| 建物 | OpenStreetMap | API動的取得（osmnx） |
| 道路 | OpenStreetMap | API動的取得（osmnx） |
| 河川 | OpenStreetMap | API動的取得（osmnx） |

## UI設計

### 画面構成
ステップ形式（ウィザード）。PC・スマホ両対応。

```
STEP1: エリア選択 → STEP2: 設定入力 → STEP3: プレビュー＆ダウンロード
```

---

### STEP1: エリア選択

```
┌─────────────────────────────┐
│  ●STEP1 ─ STEP2 ─ STEP3    │ ← 進捗表示
├─────────────────────────────┤
│                             │
│       地図（全画面）          │
│   ドラッグで範囲を選択         │
│   選択中は青い矩形を表示       │
│                             │
├─────────────────────────────┤
│ 選択範囲: 約3km × 2km        │
│ 縮尺目安: 1:10,000（A3印刷） │
│ ⚠️ 推奨縮尺を超えています      │ ← 縮尺チェック警告
│              ［次へ→］       │
└─────────────────────────────┘
```

---

### STEP2: 設定入力

```
┌─────────────────────────────┐
│  STEP1 ─ ●STEP2 ─ STEP3    │
├─────────────────────────────┤
│ 等高線間隔: [2.5m ▼]        │
│ 出力サイズ: [A3  ▼]         │
│                             │
│ 出力形式:                   │
│   ☑ PDF                    │
│   ☑ GeoTIFF                │
│   ☑ MBTiles                │
│                             │
│ 表示レイヤー:                │
│   ☑ 建物                   │
│   ☑ 道路                   │
│   ☑ 河川                   │
│   ☑ 磁北線                 │
├─────────────────────────────┤
│ ［←戻る］　　　　［次へ→］   │
└─────────────────────────────┘
```

---

### STEP3: プレビュー＆ダウンロード

```
┌─────────────────────────────┐
│  STEP1 ─ STEP2 ─ ●STEP3    │
├─────────────────────────────┤
│                             │
│   ［ プレビュー生成 ］        │ ← 押すまで生成しない
│                             │
│   ↓ 生成後に表示             │
│                             │
│   ┌───────────────────┐    │
│   │   地図プレビュー    │    │
│   └───────────────────┘    │
│   ファイルサイズ目安: 約12MB  │
│                             │
│   ［PDF ダウンロード］        │
│   ［GeoTIFF ダウンロード］    │
│   ［MBTiles ダウンロード］    │
├─────────────────────────────┤
│ ［←戻る］                   │
└─────────────────────────────┘
```

---

### スマホ対応の考慮点

```
STEP1: ピンチ操作でズーム
       2本指ドラッグで地図移動
       1本指ドラッグで範囲選択
STEP2: 縦スクロールで設定項目を表示
STEP3: ダウンロードボタンを大きめに表示
```

---

## 技術スタック

### フロントエンド
- **React**
- **MapLibre GL JS**（地図表示・範囲選択UI）

### バックエンド
- **Python + FastAPI**
- **GDAL**（DEM処理・等高線生成）
- **osmnx**（OSMデータ取得）
- **ReportLab または QGIS headless**（PDF出力）

### インフラ（本番想定）
- **AWS EC2 + S3**（推奨構成）
- Claude Code + tmux で開発
- GitHub連携済み（SSHキー認証）

※ 現時点ではAWSは未使用。まずローカル環境でPoC（実現性検証）を行う。

## PoC方針

**PoCはPythonスクリプトで実施し、Webアプリは作らない。**

理由: 「等高線が生成できるか」「磁北線が正しく描けるか」「PDFが60MB以下に収まるか」といった技術的な疑問を早く解消するため。UIを作りながら技術検証すると、詰まったときの原因切り分けが難しくなる。

```
PoC（現在）: Pythonスクリプトで技術検証
  ↓ Phase 1〜6がすべて成功したら
本番開発: React + FastAPIでWebアプリ化
```

## インフラ構成

### PoC段階（現在）
```
Mac（ローカル）
  └── Python + GDAL（等高線生成）
  └── QGIS（表示確認）
  └── 国土地理院DEMデータ（手動DL・小エリアのみ）
```

### 本番構成A: EC2 1台構成（シンプル・最初の本番）

```
ユーザー（ブラウザ）
  ↓
EC2 1台
  ├── Nginx（Webサーバー）
  ├── React（フロントエンド）
  ├── FastAPI（バックエンド）
  └── EBS（DEMデータ保存）
```

費用: 月$20〜30程度  
メリット: シンプル・安い・管理が楽  
デメリット: 同時アクセスが増えると重くなる  
推奨時期: PoC成功後〜ユーザー数が少ない段階

### 本番構成B: EC2 + S3構成（推奨・安定運用）

```
ユーザー（ブラウザ）
  ↓
CloudFront（CDN）→ React（S3ホスティング）
  ↓
EC2（処理サーバー）
  ├── FastAPI
  └── GDAL処理
  ↓
S3（ストレージ）
  ├── DEMデータ保存
  └── 生成PDF一時保存
```

費用: 月$30〜50程度  
メリット: DEMデータをS3に逃がせるのでEC2が軽い  
デメリット: 構成がやや複雑  
推奨時期: ユーザーが増えてきた段階

### 本番構成C: フルスケール構成（将来）

```
CloudFront → React（S3ホスティング）
  ↓
API Gateway
  ↓
Lambda（軽い処理）
  ↓
EC2 or ECS（重いGDAL処理）
  ↓
S3（DEMデータ・出力ファイル）
```

費用: 月$50〜100+  
メリット: アクセス増加に対応できる  
推奨時期: 本格サービス化後

### 移行ロードマップ

```
今：Mac ローカルでPoC
  ↓ PoCが成功したら
次：構成A（EC2 1台）で本番v1
  ↓ ユーザーが増えたら
将来：構成B（EC2 + S3）に移行
  ↓ さらにスケールが必要なら
最終：構成C（フルスケール）
```

### DEMデータの容量目安

| 範囲 | 容量目安 |
|------|---------|
| 1メッシュ | 約50MB |
| 都道府県1つ | 数GB〜数十GB |
| 全国（46%分） | 数百GB〜 |

最初は対応エリアを絞る（例：関東のみ）のが現実的。

### 開発環境アクセス（構成A・B共通）
```
PC（自宅）  ──┐
              ├── SSH → AWS EC2（Ubuntu 22.04）
iPad（外出）──┘         └── Claude Code + tmux で常時起動
                            └── GitHub連携済み（SSHキー認証）
```

## PoC手順（Mac ローカル）

### 成功基準
各フェーズで以下を確認できればPoCは成功とみなす。

| フェーズ | 成功の条件 |
|---------|-----------|
| Phase 1 | 環境構築完了・GDALが動く |
| Phase 2 | DEMデータを取得・解凍できる |
| Phase 3 | 等高線データが生成される |
| Phase 4 | QGISで正しく表示される |
| Phase 5 | A4 PDFに出力できる |
| Phase 6 | 建物・道路が正しい位置に重なる |

### Phase 1: 環境構築
```bash
# Homebrew（未インストールの場合）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# GDAL
brew install gdal

# Pythonライブラリ
pip install gdal numpy matplotlib geopandas osmnx pygeomag
```

### Phase 2: DEMデータ取得
```
1. 国土地理院アカウント作成
   https://fgd.gsi.go.jp/download/
2. 「数値標高モデル 1mメッシュ」を選択
3. 試したいエリアを1メッシュだけDL
4. ZIPを解凍 → XMLファイルを確認
```

### Phase 3: 等高線生成（Pythonスクリプト）
```
1. XMLをGeoTIFFに変換（GDAL）
2. GeoTIFFから等高線を生成
3. 生成できたか確認
```

### Phase 4: 地図表示確認
```
1. QGISで等高線を開いて表示確認（QGISは無料）
2. 等高線の間隔・精度を確認
```

### Phase 5: PDF出力確認

コンビニA3印刷を想定した出力仕様：

```
サイズ:       A3（297mm × 420mm）
解像度:       300dpi（下限）※300dpiのA3 = 3508 × 4961px
ファイルサイズ: 60MB以下（ローソン・ファミマのネット印刷上限）
カラーモード:  CMYK（印刷向け）
```

#### 磁北線について

オリエンテーリングはコンパス基準のため、真北ではなく**磁北線**が必須。
日本では真北より約7〜9°西にズレており、エリアの座標から自動計算する。

IOF規格での磁北線仕様：
```
色:   青（細線）
線幅: 0.25〜0.35mm
間隔: 地図上で約5cm（縮尺1:10000なら実距離500m）
```

```python
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pygeomag import GeoMag
matplotlib.use('Agg')

# --- 磁北偏差の計算 ---
gm = GeoMag()
# エリア中心座標から偏差を取得
result = gm.calc(lat=35.0, lon=135.0, alt=0, date=2026.3)
declination_deg = result.d  # 例：-7.5度（西偏）

# --- 磁北線の描画関数 ---
def draw_magnetic_lines(ax, bounds, declination_deg, interval_m=500):
    angle = np.radians(declination_deg)
    xmin, ymin, xmax, ymax = bounds
    for x in np.arange(xmin - (ymax - ymin), xmax, interval_m):
        dx = (ymax - ymin) * np.tan(angle)
        ax.plot(
            [x, x + dx],
            [ymin, ymax],
            color='blue',
            linewidth=0.3,
            alpha=0.6,
            zorder=1  # 地形の下に描画
        )

# --- 等高線データ読み込み ---
contours = gpd.read_file('contour.shp')
contours = contours.to_crs('EPSG:6677')

# --- A3サイズで描画 ---
fig, ax = plt.subplots(figsize=(11.69, 16.54))

# ① 磁北線（一番下のレイヤー）
bounds = contours.total_bounds  # [xmin, ymin, xmax, ymax]
draw_magnetic_lines(ax, bounds, declination_deg, interval_m=500)

# ② 等高線・その他レイヤー
contours.plot(ax=ax, color='brown', linewidth=0.5, zorder=2)

# 余白なし・軸非表示
ax.set_axis_off()
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

# PDF出力（300dpi・A3）
fig.savefig(
    'output_A3.pdf',
    format='pdf',
    dpi=300,
    bbox_inches='tight',
    pad_inches=0
)
```

必要なライブラリを追加インストール：

```bash
pip install pygeomag
```

ファイルサイズが大きい場合は等高線を間引く：

```python
# 頂点を間引いてファイルサイズを削減
contours['geometry'] = contours.geometry.simplify(
    tolerance=0.0001,  # 値を大きくするほど軽くなる
    preserve_topology=True
)
```

成功の条件:
- output_A3.pdf が生成される
- ファイルサイズが60MB以下
- A3サイズで開ける（Macのプレビューで確認）
- 印刷しても線がぼやけない
- 定規で実測して縮尺が正しい
- 磁北線が斜めに等間隔で描画されている

### Phase 6: OSMデータ重ね合わせ

```python
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt

# OSMからデータ取得
north, south, east, west = 35.01, 34.99, 135.01, 134.99
buildings = ox.geometries_from_bbox(north, south, east, west, tags={'building': True})
roads_gdf = ox.graph_to_gdfs(ox.graph_from_bbox(north, south, east, west, network_type='all'), nodes=False)
rivers    = ox.geometries_from_bbox(north, south, east, west, tags={'waterway': True})

# 全レイヤーを同じ座標系に変換（ズレ防止）
crs = 'EPSG:6677'
contours  = contours.to_crs(crs)
rivers    = rivers.to_crs(crs)
roads_gdf = roads_gdf.to_crs(crs)
buildings = buildings.to_crs(crs)

# 重ね合わせて描画（下から順に）
fig, ax = plt.subplots(figsize=(21, 29.7))
contours.plot(ax=ax,  color='brown', linewidth=0.5)  # ① 等高線
rivers.plot(ax=ax,    color='blue',  linewidth=0.8)  # ② 河川
roads_gdf.plot(ax=ax, color='black', linewidth=0.5)  # ③ 道路
buildings.plot(ax=ax, color='gray',  linewidth=0.3)  # ④ 建物

fig.savefig('output.pdf', format='pdf', dpi=300)
```

成功の条件: 建物・道路・河川が正しい位置に表示され、Googleマップと見比べてズレていない

## 開発フェーズ（本番）

### Phase 1: 地図表示・範囲選択UI
- MapLibre GL JSで地図を表示
- ユーザーが矩形または多角形で範囲を選択できるUI
- 等高線間隔の入力フォーム

### Phase 2: DEMデータ取得・等高線生成
- サーバー上の1mDEMデータをGDALで読み込み
- 指定された間隔で等高線ベクターデータを生成
- 1mDEMが未カバーの場合は5mDEMにフォールバック

### Phase 3: ベクターレイヤー重ね合わせ
- osmnxで建物・道路・河川データを取得
- 等高線レイヤーに重ね合わせ

### Phase 4: PDF・GeoTIFF出力
- PDF: A3対応（コンビニ印刷想定・300dpi・60MB以下）、A4対応、縮尺指定
- GeoTIFF: レイヤー別出力（contour / buildings / roads / rivers / merged）
- 座標系: JGD2011（EPSG:6668）統一
- 解像度: 600dpi（高品質版）/ 300dpi（コンビニ印刷版）の2種類
- メタデータ: 縮尺・範囲・生成日時・DEM解像度・等高線間隔を埋め込み
- 縮尺チェック: 標準縮尺（1:4000〜1:15000）を超える場合は警告表示

### Phase 5: ユーザー登録・課金（将来）
- 未定

## カスタマーへの提供物

### サービスの一言説明
```
地図上でエリアを選んで
オリエンテーリング用ベース地図を
PDF・GeoTIFFでダウンロードできるWebアプリ
```

### ユーザーの操作フロー
```
① Webブラウザでアクセス
  ↓
② 地図上でエリアを範囲選択
  ↓
③ 等高線間隔を指定（例：2.5m）
  ↓
④ PDF または GeoTIFF を選択
  ↓
⑤ ダウンロード
```

### 提供ファイルの内容

| ファイル | 用途 | 含まれるもの |
|---------|------|------------|
| PDF | 印刷・そのまま使う | 等高線・建物・道路・河川 |
| GeoTIFF | QGISで編集 / サービス2で使う | 同上（座標情報・メタデータ付き） |

### まだ決まっていないこと
```
□ ユーザー登録の要否
□ 料金モデル
□ 地図のスタイル（色）
□ 対応エリア（全国 or 絞る）
□ ダウンロードサイズの上限
```

---

## サービス2（将来構想）：競技地図作成サービス

### 概要
サービス1で生成したGeoTIFFをベース地図として読み込み、オリエンテーリング競技地図をブラウザ上で作成・配布できるサービス。

### サービス2でできること
```
□ サービス1のGeoTIFFを読み込み
□ CP（コントロールポイント）の配置・番号付け
□ CP解説の入力
□ 立入禁止区域の描画（ポリゴン）
□ トレイルの描画（ライン）
□ 配布用PDF出力（競技者向け）
□ コース設計データの保存・共有
```

### 2サービスの関係
```
サービス1（今回）               サービス2（将来）
ベース地図生成              →   競技地図作成
GeoTIFF出力（高精度）       →   GeoTIFFを読み込み
                                CP・禁止区域・トレイル追記
                                配布用PDF出力
```

---

## サービス2を見据えたGeoTIFF設計要件

サービス1のGeoTIFF出力はサービス2との連携を前提に以下を満たす設計とする。

### 1. 座標系の統一（最重要）
```
採用: JGD2011（EPSG:6668）
      または JGD2011 平面直角座標系（EPSG:6669〜6687）

理由: 日本国内の精度がWGS84より優れる
      サービス2でCP座標を打つ際にズレが起きない
```

### 2. 解像度
```
最低: 300dpi（印刷品質）
推奨: 600dpi（競技地図レベル）
```

### 3. レイヤー別出力
1つのGeoTIFFに全部混ぜるのではなくレイヤーを分けて出力する。
サービス2側で「等高線だけ薄くする」「道路を非表示にする」などの編集が柔軟にできる。

```
output/
  ├── contour.tif      # 等高線のみ
  ├── buildings.tif    # 建物のみ
  ├── roads.tif        # 道路のみ
  ├── rivers.tif       # 河川のみ
  └── merged.tif       # 全部合成（印刷・確認用）
```

### 4. メタデータの埋め込み
```
・縮尺情報       → サービス2で「1:5000で出力」が正確にできる
・バウンディングボックス → サービス2でCP座標が範囲内かチェックできる
・生成日時
・使用DEMの解像度（1m or 5m）
・等高線間隔
```

### 5. 縮尺チェック機能
オリエンテーリング競技地図の標準縮尺は1:4000〜1:15000。
ユーザーが選択した範囲が標準縮尺に収まらない場合は警告を表示する。

```
選択範囲が広すぎる場合:
  「この範囲はA4印刷時に1:20000になります。
   オリエンテーリング地図の推奨縮尺（1:4000〜1:15000）
   を超えています。範囲を絞ることをおすすめします。」
```

## 注意事項・制約

- 国土地理院データは基本測量成果のため、**サービスで配布する場合は測量法に基づく複製・使用申請が必要**
- 申請先: 測量成果ワンストップサービス（https://www.gsi.go.jp/）
- 1mDEMは全国約46%のカバーのため、未対応エリアの案内が必要
- オリエンテーリング競技の記号（IOF規格）は本サービスでは対応しない（ベース地図のみ）
- 地図スタイル（色）は未定。今後ユーザーテストを経て決定する

## ディレクトリ構成（予定）

```
orienteering-map/
├── frontend/          # React + MapLibre GL JS
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx       # 地図表示・範囲選択
│   │   │   └── DownloadPanel.jsx # 等高線間隔・ダウンロード設定
│   │   └── App.jsx
│   └── package.json
├── backend/           # Python + FastAPI
│   ├── main.py        # APIエンドポイント
│   ├── dem.py         # DEM処理・等高線生成（GDAL）
│   ├── vector.py      # OSMデータ取得（osmnx）
│   ├── export.py      # PDF・GeoTIFF出力
│   └── requirements.txt
├── data/
│   └── dem/           # 国土地理院DEMデータ保存先
│       ├── 1m/
│       └── 5m/
└── output/            # 生成ファイル出力先
    ├── contour.tif    # 等高線のみ
    ├── buildings.tif  # 建物のみ
    ├── roads.tif      # 道路のみ
    ├── rivers.tif     # 河川のみ
    └── merged.tif     # 全レイヤー合成
```
