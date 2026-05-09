# オリエンテーリング用ベース地図サービス 設計書

## サービス概要

オリエンテーリング競技用地図の下見準備を支援するWebサービス。
国土地理院タイル地図をベースに、CP候補・メモを追記してPDF出力およびサービス2への連携データを生成する。

**将来拡張**: 国土地理院DEMから生成した詳細等高線地図への切り替えに対応予定。

## ターゲットユーザー

- オリエンテーリング競技の地図作成者（下見準備用途）

## 実装状況（フェーズ1）

### デプロイ先
- **GitHub Pages**: https://trail-fun.github.io/orien-basemapmake/
- **リポジトリ**: https://github.com/trail-fun/orien-basemapmake（public）
- **デプロイ方法**: GitHub Actions（main ブランチへの push で自動デプロイ）

### 実装済み機能

| 機能 | 状態 | 備考 |
|------|------|------|
| 国土地理院タイル地図表示 | ✅ | 標準・等高線切替 |
| 縮尺・用紙・向き設定 | ✅ | A3/A4・縦/横、デフォルト A4縦 |
| 印刷範囲枠 ドラッグ移動 | ✅ | 四隅マーカー＋カーソルキー |
| CP設置（クリック/タップ） | ✅ | スタート→CP自動切替 |
| CP編集・削除 | ✅ | ダブルクリックでモーダル編集 |
| CP用途設定 | ✅ | ストレート/スコア/両用 |
| CP一覧並び替え | ✅ | PC:ドラッグ、スマホ:▲▼ボタン |
| Undo（操作取り消し） | ✅ | Ctrl+Z、最大50ステップ |
| 表示オプション | ✅ | 順番・ポイント・接続線 |
| ストレート接続線 | ✅ | 円外周から外周まで正確に描画 |
| 全体メモ・CP個別メモ | ✅ | |
| CSVインポート | ✅ | |
| GeoJSONインポート（再編集） | ✅ | 出力したファイルを読み込んで続きを編集 |
| PDF出力 | ✅ | JPEG圧縮・DPR上限1.5・zoom18 |
| PDF上のCP記号（十字付き） | ✅ | スタート△・CP○・フィニッシュ◎＋中心十字 |
| GeoJSON出力（サービス2連携用） | ✅ | |
| モバイル対応 | ✅ | ドロワー型サイドパネル・下部ツールバー |
| ルーペ（CP移動時の拡大鏡） | ✅ | 直径220px、ドラッグ中のみ表示 |

### 技術的な実装メモ

**PDF生成（`OutputView.jsx`）**
- WebGL canvas は `position:fixed` + `clientHeight` を使いビューポート制約を回避
- `fitBounds` → `project()` でクロップ座標を計算し、地理的に正確な範囲を切り抜く
- `pdfZoom: 18` で等高線が見えるズームレベルを確保
- `toDataURL('image/jpeg', 0.88)` + DPR上限1.5 でファイルサイズを削減
- CP記号はjsPDFでベクター描画（円・三角・二重円＋中心十字）

**モバイル対応（`App.css`）**
- `.app` に `height: 100dvh`（Dynamic Viewport Height）を適用。iOS Safariで`100vh`がブラウザUIを含む高さになる問題を解決
- サイドパネル：`@media (max-width: 768px)` で `position:absolute + translateX(100%)` のドロワーに切替
- 下部ツールバー：`@media (max-width: 1024px)` で `position:absolute; bottom:0; z-index:50` に表示。CP3種・Undo・出力ボタンを配置
- `env(safe-area-inset-bottom)` をツールバーの `padding-bottom` に適用（iPhone ホームインジケーター対応）

**ルーペ（`MapEditor.jsx`）**
- MapLibre インスタンスを2つ起動（メインマップ＋ルーペ用ミニマップ）
- ルーペは `opacity:0`（不可視）で常時初期化済み。CPドラッグ開始時に `classList.add('active')` で表示
- `marker.on('drag')` で `loupeRef.current.jumpTo({ center: marker.getLngLat() })` を呼び追従

---

## 主要機能

- 国土地理院タイル地図の表示（標準地図・等高線地図の切り替え）
- 縮尺・出力サイズ・向きの選択（A3/A4・縦/横）、デフォルトA4縦
- 印刷範囲枠の表示・ドラッグで位置調整
- CP（スタート・CP・フィニッシュ）の設置・編集（起動時スタートモード自動ON、スタート配置後CPモード自動切替）
- CP用途設定（ストレート用・スコア用・両用）
- CP一覧の並び替え（PC:ドラッグ、スマホ:▲▼ボタン）
- Undo（Ctrl+Z、最大50ステップ）
- 表示オプション（順番・ポイント・接続線）
- 全体メモ・CP個別メモの入力
- CSVからのCP一括インポート
- GeoJSONファイルの読み込みによる再編集
- PDF出力（国土地理院地図＋CP記号＋十字）
- サービス2取込用データ出力（GeoJSON）

## データソース

### フェーズ1: 国土地理院タイル地図（現在）

```
標準地図:   https://tile.maps.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
等高線地図: https://tile.maps.gsi.go.jp/xyz/relief/{z}/{x}/{y}.png
```

- APIキー不要・無料
- 出典明示で商用利用可能
- バックエンド不要（フロントエンドから直接呼び出し）

### フェーズ2: 詳細等高線地図（将来）
- **国土地理院 基盤地図情報 1mメッシュDEM（航空レーザ測量）**
- ダウンロードURL: https://fgd.gsi.go.jp/download/
- フォーマット: JPGIS（GML/XML形式）→ GeoTIFFに変換して使用
- カバレッジ: 現在全国約46%（未カバー地域は5mメッシュDEMにフォールバック）
- 取得方法: APIなし。手動で事前ダウンロードしサーバーに保存する方式

### 建物・道路・河川（フェーズ2以降）
- **OpenStreetMap（OSM）**
- Pythonライブラリ `osmnx` でAPIから動的取得

```python
import osmnx as ox

buildings = ox.geometries_from_bbox(north, south, east, west, tags={'building': True})
roads     = ox.graph_from_bbox(north, south, east, west, network_type='all')
water     = ox.geometries_from_bbox(north, south, east, west, tags={'waterway': True})
```

### データ取得戦略のまとめ

| データ種別 | フェーズ1 | フェーズ2 |
|-----------|---------|---------|
| ベース地図 | 国土地理院タイル（API） | 自作等高線地図（DEM処理） |
| 建物・道路・河川 | 不要 | OSM（osmnx） |
| 磁北線 | 不要 | pygeomag で自動計算 |

## UI設計

### 画面構成
2画面構成。PC・スマホ両対応。
エリア選択・追記作業は**同じ画面で同時・交互に操作可能**。

```
地図編集画面（印刷範囲設定・CP設置・メモ入力）
  ↓
出力画面（PDF・GeoJSON）
```

将来的に地図ソースを詳細等高線地図に切り替えても、UI構成はそのまま維持できる設計。

---

### 地図編集画面

```
┌──────────────────────────────────────┐
│ 地図種類: [標準] [等高線] [詳細🔒]   │
│ サイズ: [A3▼] 向き: [縦▼] 縮尺: [1:10,000▼] │
│ ⚠️ 推奨縮尺（1:4,000〜1:15,000）を超えています│
├──────────────────────────────────────┤
│                                      │
│         地図（全画面）                 │
│  ░░░░░┌─────────────────┐░░░░░      │
│  ░░░░░│   印刷範囲枠      │░░░░░      │
│  ░░░░░│  （ドラッグで移動）│░░░░░      │
│  ░░░░░└─────────────────┘░░░░░      │
│                                      │
├──────────────────────────────────────┤
│ CP追加: [△スタート] [○CP] [◎フィニッシュ] │
│ [📥CSVインポート]                     │
│                                      │
│ 表示オプション:                       │
│  □ 順番を表示  □ ポイントを表示       │
│  □ 接続線を表示                      │
│                                      │
│ 全体メモ: [______________________]   │
│                                      │
│ CP一覧:                              │
│  △  -    -    -     スタート [編集][🗑️]│
│  ○ CP1  両用  1・10pt ○○分岐 [編集][🗑️]│
│  ○ CP2  ストレート 2  岩の手前 [編集][🗑️]│
│  ○ CP3  スコア  20pt  崖の上  [編集][🗑️]│
│  ◎  -    -    -     ゴール  [編集][🗑️]│
├──────────────────────────────────────┤
│                       ［出力へ→］    │
└──────────────────────────────────────┘
```

---

### 印刷範囲枠の操作

```
設定変更時の挙動:
  サイズ・向き変更 → 枠の縦横が切り替わる（中心維持）
  縮尺変更        → 枠のサイズが変わる（中心維持）

枠の選択・移動・微調整:
  PC:     クリックで選択 → ドラッグで移動
          カーソルキーで微調整（↑↓←→: 約1m・Shift+カーソル: 約10m）
  スマホ: タップで選択 → ドラッグで移動
          矢印ボタンで微調整（1タップ: 約1m・長押し: 連続移動）
```

---

### PC・スマホ操作対応表

| 操作 | PC | スマホ |
|------|-----|--------|
| 地図ズーム | スクロール | ピンチ |
| 地図移動 | ドラッグ | 2本指ドラッグ |
| 印刷枠選択 | クリック | タップ |
| 印刷枠移動 | ドラッグ | ドラッグ |
| 印刷枠微調整 | カーソルキー | 矢印ボタン |
| CP配置 | クリック | タップ |
| CP選択 | クリック | タップ |
| CP移動 | ドラッグ | ドラッグ |
| CP微調整 | カーソルキー | 矢印ボタン |
| 緯度経度入力 | キーボード入力 | テンキー入力 |
| CSVインポート | ファイル選択 | ファイル選択 |
| パネルスクロール | スクロール | 縦スクロール |

---

### CP種類・用途・表示

| 種類 | 記号 | 番号 | 用途 | 地図上の表示 |
|------|------|------|------|------------|
| スタート | △ | なし | - | △のみ |
| CP | ○ | あり（内部管理のみ） | ストレート/スコア/両用 | ○＋順番/ポイント（オプション） |
| フィニッシュ | ◎ | なし | - | ◎のみ |

**表示オプション（ON/OFF選択）**
```
□ ストレートの順番を表示（数字のみ・「番」は表示しない）
□ スコアのポイントを表示
□ ストレートのCPを繋ぐ接続線を表示
```

**地図上の見た目（全オプションON）**
```
△
 ↓（線）
○  →  ○
1     2

      ○
     20pt

◎
```

---

### CP設置方法（3種類）

**① 地図上のマウスクリック**
```
ツールバーで種類を選択（△/○/◎）→ 地図上をクリックで配置
CPは自動採番（CP1, CP2...）
```

**② 緯度経度の直接入力**
```
「CP追加」→ 入力フォーム
  種類: [○CP ▼]
  緯度: [35.0000]
  経度: [135.0000]
  ［配置］
```

**③ CSVからのインポート**
```
フォーマット:
type,lat,lng,usage,order,score,memo
start,35.001,135.001,,,スタート地点
cp,35.002,135.002,both,1,10,○○の分岐
cp,35.003,135.003,score,,20,崖の上
finish,35.004,135.004,,,ゴール
```

---

### CP修正方法（3種類）

**① マウスでドラッグ**
```
CPをクリックで選択（ハイライト表示）→ ドラッグで移動 → ドロップで確定
```

**② カーソルキーで微調整**
```
CPをクリックで選択
カーソルキー（↑↓←→）: 小移動（約1m）
Shift＋カーソルキー:    大移動（約10m）
```

**③ 緯度経度の直接入力**
```
CPをクリックで選択 → サイドパネルの緯度経度を直接編集
```

---

### 出力画面

```
┌──────────────────────────────────────┐
│  地図編集 ─ ●出力                    │
├──────────────────────────────────────┤
│   ┌──────────────────────────────┐   │
│   │   地図プレビュー               │   │
│   │   （CP・メモ・接続線含む）      │   │
│   └──────────────────────────────┘   │
│                                      │
│  ［PDF ダウンロード］                  │
│  ［サービス2用データ出力（GeoJSON）］   │
│                                      │
│  ※出典：国土地理院                    │
├──────────────────────────────────────┤
│ ［←戻る］                            │
└──────────────────────────────────────┘
```

---

### サービス2への出力データ（GeoJSON）

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "created_at": "2026-05-08",
    "scale": "1:10000",
    "output_size": "A3",
    "orientation": "portrait",
    "memo": "全体メモのテキスト"
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "type": "start",
        "number": null,
        "usage": null,
        "order": null,
        "score": null,
        "memo": "スタート地点"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [135.001, 35.001]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "type": "cp",
        "number": 1,
        "usage": "both",
        "order": 1,
        "score": 10,
        "memo": "○○の分岐"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [135.002, 35.002]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "type": "finish",
        "number": null,
        "usage": null,
        "order": null,
        "score": null,
        "memo": "ゴール"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [135.004, 35.004]
      }
    }
  ]
}
```

---

### スマホ対応の考慮点（実装済み）

```
レイアウト:
  PC (>1024px):  地図＋右サイドパネル（300px固定）の2カラム
  スマホ/タブレット (≤1024px):
    地図が全画面。右上の「☰設定」ボタンでサイドパネルをドロワー表示
    地図下部に常時表示の操作バー（CP3種・Undo・出力）

下部操作バー (≤1024px):
  ┌─────────────────────────────────────┐
  │ [△ST] [○CP] [◎FN] [↩] [出力→]    │
  └─────────────────────────────────────┘
  position:absolute; bottom:0; z-index:50

ルーペ（拡大鏡）:
  CPをドラッグすると指の上に直径220pxのルーペが表示される
  ルーペはMapLibreの第2インスタンスで zoom:18 固定
  ドラッグ終了で自動非表示

CP一覧の並び替え:
  PC:     ドラッグ&ドロップ（⠿ハンドルをドラッグ）
  スマホ: ▲▼ボタンで1行ずつ移動

地図操作:
  ピンチ操作でズーム（2本指回転は無効化）
  ドラッグで地図移動
  1本指タップでCP配置

技術的注意点:
  iOS Safariの100vh問題 → height:100dvh を使用
  ホームインジケーター → padding-bottom:env(safe-area-inset-bottom)
  MapLibre回転無効化 → touchZoomRotate.disableRotation()
```

---

### 国土地理院タイルのURL

```
標準地図:   https://tile.maps.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
等高線地図: https://tile.maps.gsi.go.jp/xyz/relief/{z}/{x}/{y}.png
```

利用規約: 出典明示すれば商用利用可能。PDF・画面上に「出典：国土地理院」の記載が必要。

---

## 技術スタック

### フェーズ1（実装済み）
- **Vite + React**（フロントエンドのみ・バックエンド不要）
- **MapLibre GL JS**（地図表示・CP マーカー・印刷枠・ルーペ用2インスタンス）
- **国土地理院タイルAPI**（標準地図・等高線地図）
- **jsPDF**（ブラウザ上でPDF生成、CPシンボルはベクター描画）
- **GitHub Pages**（静的ホスティング、GitHub Actions で自動デプロイ）
- vite.config.js: `base: '/orien-basemapmake/'`、`server: { host: true, allowedHosts: true }`

### フェーズ2（将来）
**フロントエンド追加**
- MapLibre GL JS（詳細等高線地図の表示）

**バックエンド追加**
- **Python + FastAPI**
- **GDAL**（DEM処理・等高線生成）
- **osmnx**（OSMデータ取得）
- **pygeomag**（磁北偏差の自動計算）

### インフラ（本番想定）
- **AWS EC2 + S3**（推奨構成）
- Claude Code + tmux で開発
- GitHub連携済み（SSHキー認証）

※ 現時点ではAWSは未使用。まずローカル環境でPoC（実現性検証）を行う。

## PoC方針

**フェーズ1: 国土地理院タイル地図ベースのWebアプリをまず作る**

理由: 等高線生成（GDAL処理）の技術的難易度が高いため、まず使えるサービスを早く作ることを優先する。国土地理院タイル地図はAPIで即座に利用可能で、フロントエンドのみで実装できる。

```
フェーズ1（現在優先）:
  国土地理院タイル地図 + CP候補追記 + PDF/GeoJSON出力
  → React（フロントエンドのみ）で実装可能
  → バックエンド不要・すぐ作れる

フェーズ2（将来）:
  自作詳細等高線地図への切り替え対応
  → PoCで技術検証後に追加
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
