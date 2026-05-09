#!/usr/bin/env python3
"""
GeoTIFF出力スクリプト
等高線SHPとOSMデータをレイヤー別GeoTIFFにラスタライズして出力する。

使い方:
  python3 phase_geotiff.py <contour.shp> [--bbox west,south,east,north] [--res 1.0] [--dpi 300]
例:
  python3 phase_geotiff.py ../output/contour_2.5m.shp
  python3 phase_geotiff.py ../output/contour_2.5m.shp --bbox 132.43,34.355,132.46,34.370
"""

import sys
import datetime
import numpy as np
import geopandas as gpd
import osmnx as ox
from pathlib import Path
from osgeo import gdal, ogr, osr
from pyproj import Transformer

gdal.UseExceptions()

CRS_PLANE  = "EPSG:6675"   # 平面直角第7系（広島・中国エリア）
CRS_PLANE_EPSG = 6675

# レイヤー定義: (名前, RGBAカラー)
LAYER_COLORS = {
    'contour':   (139,  90,  43, 220),   # 茶色
    'rivers':    ( 51, 153, 255, 220),   # 青
    'roads':     ( 51,  51,  51, 220),   # 濃いグレー
    'buildings': (170, 170, 170, 220),   # 薄いグレー
}

def parse_args():
    args = {'shp': None, 'bbox': None, 'res': 1.0, 'dpi': 300}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--bbox':
            w, s, e, n = map(float, sys.argv[i+1].split(','))
            args['bbox'] = (w, s, e, n)
            i += 2
        elif sys.argv[i] == '--res':
            args['res'] = float(sys.argv[i+1]); i += 2
        elif sys.argv[i] == '--dpi':
            args['dpi'] = int(sys.argv[i+1]); i += 2
        else:
            args['shp'] = Path(sys.argv[i]); i += 1
    return args

def wgs84_bbox_to_plane(w, s, e, n, epsg=CRS_PLANE_EPSG):
    """WGS84のbboxを平面直角座標に変換"""
    tf = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x0, y0 = tf.transform(w, s)
    x1, y1 = tf.transform(e, n)
    return min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1)

def plane_bbox_to_wgs84(xmin, ymin, xmax, ymax, epsg=CRS_PLANE_EPSG):
    """平面直角座標のbboxをWGS84に変換"""
    tf = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lon0, lat0 = tf.transform(xmin, ymin)
    lon1, lat1 = tf.transform(xmax, ymax)
    return min(lon0,lon1), min(lat0,lat1), max(lon0,lon1), max(lat0,lat1)

def make_empty_tif(out_path, xmin, ymin, xmax, ymax, res, epsg):
    """空のRGBA GeoTIFFを作成して返す"""
    cols = int(np.ceil((xmax - xmin) / res))
    rows = int(np.ceil((ymax - ymin) / res))

    drv = gdal.GetDriverByName('GTiff')
    ds  = drv.Create(str(out_path), cols, rows, 4, gdal.GDT_Byte,
                     options=['COMPRESS=LZW', 'TILED=YES', 'ALPHA=YES'])
    ds.SetGeoTransform([xmin, res, 0, ymax, 0, -res])
    srs = osr.SpatialReference(); srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())
    # 全透明で初期化
    for b in range(1, 5):
        band = ds.GetRasterBand(b)
        band.Fill(0)
        band.SetNoDataValue(0)
    return ds

def rasterize_layer(ds, gdf, rgba):
    """GeoDataFrameをGeoTIFFデータセットにラスタライズ"""
    if gdf is None or len(gdf) == 0:
        return

    r, g, b, a = rgba
    gt   = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize

    # インメモリOGRレイヤーを作成
    mem_drv = ogr.GetDriverByName('Memory')
    mem_ds  = mem_drv.CreateDataSource('tmp')
    srs     = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())
    layer   = mem_ds.CreateLayer('tmp', srs=srs)

    # ジオメトリを追加
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        feat = ogr.Feature(layer.GetLayerDefn())
        feat.SetGeometry(ogr.CreateGeometryFromWkt(geom.wkt))
        layer.CreateFeature(feat)

    # 各バンドにラスタライズ
    for band_idx, val in enumerate([r, g, b, a], start=1):
        gdal.RasterizeLayer(ds, [band_idx], layer, burn_values=[val])

    mem_ds = None

def set_metadata(ds, contour_interval, res, bbox_wgs84, crs_epsg):
    """GeoTIFFにメタデータを埋め込む"""
    w, s, e, n = bbox_wgs84
    ds.SetMetadataItem('CONTOUR_INTERVAL_M',  str(contour_interval))
    ds.SetMetadataItem('PIXEL_SIZE_M',        str(res))
    ds.SetMetadataItem('CRS_EPSG',            str(crs_epsg))
    ds.SetMetadataItem('BBOX_WGS84_WSEN',     f'{w:.6f},{s:.6f},{e:.6f},{n:.6f}')
    ds.SetMetadataItem('DEM_SOURCE',          '国土地理院1mメッシュDEM')
    ds.SetMetadataItem('OSM_SOURCE',          'OpenStreetMap contributors')
    ds.SetMetadataItem('GENERATED',           datetime.datetime.now().isoformat())

def merge_tifs(layer_paths, merged_path, metadata=None):
    """RGBAレイヤーTIFを合成してmerged.tifを作成"""
    ref = gdal.Open(str(layer_paths[0]))
    cols, rows = ref.RasterXSize, ref.RasterYSize
    gt, proj   = ref.GetGeoTransform(), ref.GetProjection()
    ref = None

    drv  = gdal.GetDriverByName('GTiff')
    out  = drv.Create(str(merged_path), cols, rows, 4, gdal.GDT_Byte,
                      options=['COMPRESS=LZW', 'TILED=YES', 'ALPHA=YES'])
    out.SetGeoTransform(gt)
    out.SetProjection(proj)
    if metadata:
        out.SetMetadata(metadata)

    # 白背景で初期化
    for b in [1, 2, 3]:
        out.GetRasterBand(b).Fill(255)
    out.GetRasterBand(4).Fill(255)

    # 各レイヤーをアルファブレンドで合成
    for path in layer_paths:
        src = gdal.Open(str(path))
        for b in range(1, 4):   # RGB
            src_arr = src.GetRasterBand(b).ReadAsArray().astype(np.float32)
            alp_arr = src.GetRasterBand(4).ReadAsArray().astype(np.float32) / 255.0
            dst_arr = out.GetRasterBand(b).ReadAsArray().astype(np.float32)
            blended = src_arr * alp_arr + dst_arr * (1 - alp_arr)
            out.GetRasterBand(b).WriteArray(blended.astype(np.uint8))
        src = None

    out.FlushCache()
    out = None
    print(f"  合成完了: {merged_path.name}")

def main():
    args = parse_args()
    if args['shp'] is None:
        print(__doc__); sys.exit(1)

    out_dir = args['shp'].parent
    res     = args['res']

    print(f"=== GeoTIFF出力 (解像度:{res}m/px) ===")

    # 1. 等高線読み込み・座標変換
    contours = gpd.read_file(args['shp'])
    if contours.crs is None:
        contours = contours.set_crs("EPSG:6668")
    contours = contours.to_crs(CRS_PLANE)

    # 等高線間隔を推定（ファイル名から）
    try:
        interval = float(args['shp'].stem.split('_')[1].replace('m',''))
    except Exception:
        interval = 2.5

    # 2. 出力範囲の確定
    if args['bbox']:
        w, s, e, n = args['bbox']
        xmin, ymin, xmax, ymax = wgs84_bbox_to_plane(w, s, e, n)
        from shapely.geometry import box
        contours = contours[contours.intersects(box(xmin, ymin, xmax, ymax))]
    else:
        xmin, ymin, xmax, ymax = contours.total_bounds
        w, s, e, n = plane_bbox_to_wgs84(xmin, ymin, xmax, ymax)

    print(f"  範囲: WGS84 N{n:.4f} S{s:.4f} E{e:.4f} W{w:.4f}")
    bbox_osm = (w, s, e, n)
    osm_bbox = (w, s, e, n)   # (west,south,east,north)

    # 3. OSMデータ取得
    def safe_crs(gdf):
        if gdf is None or len(gdf) == 0:
            return gpd.GeoDataFrame()
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        return gdf.to_crs(CRS_PLANE)

    print("OSMデータ取得中...")
    try:
        buildings = safe_crs(ox.features_from_bbox(osm_bbox, tags={'building': True}))
        print(f"  建物: {len(buildings)} 件")
    except Exception as e:
        print(f"  建物取得失敗: {e}"); buildings = gpd.GeoDataFrame()

    try:
        G = ox.graph_from_bbox(osm_bbox, network_type='all')
        roads = safe_crs(ox.graph_to_gdfs(G)[0])
        print(f"  道路: {len(roads)} 件")
    except Exception as e:
        print(f"  道路取得失敗: {e}"); roads = gpd.GeoDataFrame()

    try:
        rivers = safe_crs(ox.features_from_bbox(osm_bbox, tags={'waterway': True}))
        print(f"  河川: {len(rivers)} 件")
    except Exception as e:
        print(f"  河川取得失敗: {e}"); rivers = gpd.GeoDataFrame()

    # 4. レイヤー別GeoTIFF出力
    layers = {
        'contour':   contours,
        'buildings': buildings,
        'roads':     roads,
        'rivers':    rivers,
    }
    tif_paths = []

    for name, gdf in layers.items():
        out_path = out_dir / f"{name}.tif"
        print(f"ラスタライズ中: {name}.tif ...")
        ds = make_empty_tif(out_path, xmin, ymin, xmax, ymax, res, CRS_PLANE_EPSG)
        rasterize_layer(ds, gdf, LAYER_COLORS[name])
        set_metadata(ds, interval, res, (w, s, e, n), CRS_PLANE_EPSG)
        ds.FlushCache(); ds = None
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  → {out_path.name}  ({size_mb:.1f} MB)")
        tif_paths.append(out_path)

    # 5. merged.tif を合成（メタデータも引き継ぐ）
    print("merged.tif を合成中...")
    merged_path = out_dir / "merged.tif"
    meta = {
        'CONTOUR_INTERVAL_M': str(interval),
        'PIXEL_SIZE_M':       str(res),
        'CRS_EPSG':           str(CRS_PLANE_EPSG),
        'BBOX_WGS84_WSEN':    f'{w:.6f},{s:.6f},{e:.6f},{n:.6f}',
        'DEM_SOURCE':         '国土地理院1mメッシュDEM',
        'OSM_SOURCE':         'OpenStreetMap contributors',
        'LAYERS':             'contour,buildings,roads,rivers',
        'GENERATED':          datetime.datetime.now().isoformat(),
    }
    merge_tifs(tif_paths, merged_path, metadata=meta)
    size_mb = merged_path.stat().st_size / 1024 / 1024
    print(f"  → merged.tif  ({size_mb:.1f} MB)")

    print(f"\n=== 完了 ===")
    print(f"出力先: {out_dir}/")
    for p in tif_paths + [merged_path]:
        print(f"  {p.name}")

if __name__ == "__main__":
    main()
