#!/usr/bin/env python3
"""
Phase 6: 等高線 + 建物・道路・河川（OSM）をPDFに重ね合わせ出力
使い方:
  python3 phase6_osm.py <contour.shp> [出力PDF名] [--bbox west,south,east,north]
例（全体）:
  python3 phase6_osm.py ../output/contour_2.5m.shp ../output/map_overlay.pdf
例（部分指定、WGS84）:
  python3 phase6_osm.py ../output/contour_2.5m.shp ../output/map_overlay.pdf --bbox 132.42,34.35,132.46,34.37
"""

import sys
import numpy as np
import geopandas as gpd
import osmnx as ox
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from osgeo import osr

CRS_PLANE = "EPSG:6675"   # 平面直角第7系（広島・中国エリア）

def plane_to_wgs84_bbox(bounds, epsg=6675):
    """平面直角座標の範囲をWGS84(lon/lat)に変換"""
    src = osr.SpatialReference(); src.ImportFromEPSG(epsg)
    dst = osr.SpatialReference(); dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(src, dst)
    xmin, ymin, xmax, ymax = bounds
    sw_lon, sw_lat, _ = ct.TransformPoint(xmin, ymin)
    ne_lon, ne_lat, _ = ct.TransformPoint(xmax, ymax)
    return sw_lat, ne_lat, sw_lon, ne_lon   # south, north, west, east

def fetch_osm(south, north, west, east):
    """OSMから建物・道路・河川を取得 (osmnx 2.x: bbox=(west,south,east,north))"""
    bbox = (west, south, east, north)
    print(f"  エリア: N{north:.4f} S{south:.4f} E{east:.4f} W{west:.4f}")

    print("  建物取得中...")
    try:
        buildings = ox.features_from_bbox(bbox, tags={'building': True})
        print(f"    {len(buildings)} 件")
    except Exception as e:
        print(f"    取得失敗: {e}")
        buildings = gpd.GeoDataFrame()

    print("  道路取得中...")
    try:
        G = ox.graph_from_bbox(bbox, network_type='all')
        roads, _ = ox.graph_to_gdfs(G)
        print(f"    {len(roads)} 件")
    except Exception as e:
        print(f"    取得失敗: {e}")
        roads = gpd.GeoDataFrame()

    print("  河川取得中...")
    try:
        rivers = ox.features_from_bbox(bbox, tags={'waterway': True})
        print(f"    {len(rivers)} 件")
    except Exception as e:
        print(f"    取得失敗: {e}")
        rivers = gpd.GeoDataFrame()

    return buildings, roads, rivers

def safe_to_crs(gdf, crs):
    """CRSを統一。空のGeoDataFrameはそのまま返す"""
    if gdf is None or len(gdf) == 0:
        return gdf
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs(crs)

def draw_magnetic_lines(ax, bounds, declination_deg, interval_m=500):
    """磁北線を描画（IOF規格: 青・細線・500m間隔）"""
    angle = np.radians(declination_deg)
    xmin, ymin, xmax, ymax = bounds
    height = ymax - ymin
    for x in np.arange(xmin - height, xmax + height, interval_m):
        dx = height * np.tan(angle)
        ax.plot([x, x + dx], [ymin, ymax],
                color='#4477cc', linewidth=0.3, alpha=0.7, zorder=1)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    shp_path = Path(sys.argv[1])
    out_pdf  = Path(sys.argv[2]) if len(sys.argv) >= 3 and not sys.argv[2].startswith('--') \
               else shp_path.parent / "map_overlay.pdf"

    # --bbox オプションで部分エリア指定
    bbox_wgs84 = None
    for i, arg in enumerate(sys.argv):
        if arg == '--bbox' and i + 1 < len(sys.argv):
            w, s, e, n = map(float, sys.argv[i+1].split(','))
            bbox_wgs84 = (s, n, w, e)

    print(f"=== Phase 6: OSM重ね合わせ出力 ===")

    # 1. 等高線読み込み
    contours = gpd.read_file(shp_path)
    if contours.crs is None:
        contours = contours.set_crs("EPSG:6668")
    contours = contours.to_crs(CRS_PLANE)
    bounds_all = contours.total_bounds

    # 2. OSM取得範囲の決定
    if bbox_wgs84:
        south, north, west, east = bbox_wgs84
        # 指定bbox を平面直角に変換して描画範囲を決める
        from pyproj import Transformer
        tf = Transformer.from_crs("EPSG:4326", CRS_PLANE, always_xy=True)
        x0, y0 = tf.transform(west, south)
        x1, y1 = tf.transform(east, north)
        plot_bounds = (min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1))
        # 等高線を範囲でクリップ
        from shapely.geometry import box
        clip_box = box(*plot_bounds)
        contours = contours[contours.intersects(clip_box)]
    else:
        south, north, west, east = plane_to_wgs84_bbox(bounds_all)
        plot_bounds = bounds_all

    buildings, roads, rivers = fetch_osm(south, north, west, east)

    # 3. 座標系を統一
    buildings = safe_to_crs(buildings, CRS_PLANE)
    roads     = safe_to_crs(roads,     CRS_PLANE)
    rivers    = safe_to_crs(rivers,    CRS_PLANE)

    # 4. 磁北偏差
    try:
        from pygeomag import GeoMag
        gm = GeoMag()
        lat_c = (south + north) / 2
        lon_c = (west + east) / 2
        declination = gm.calculate(glat=lat_c, glon=lon_c, alt=0, time=2026.3).d
        print(f"  磁北偏差: {declination:.2f}°")
    except Exception:
        declination = -7.5

    # 5. 描画（A3横）
    fig, ax = plt.subplots(figsize=(16.54, 11.69))
    ax.set_aspect('equal')

    draw_magnetic_lines(ax, plot_bounds, declination, interval_m=500)    # ① 磁北線
    contours.plot(ax=ax, color='#8B5A2B', linewidth=0.4, zorder=2)       # ② 等高線
    if rivers is not None and len(rivers) > 0:
        rivers.plot(ax=ax, color='#3399ff', linewidth=0.8, zorder=3)     # ③ 河川
    if roads is not None and len(roads) > 0:
        roads.plot(ax=ax, color='#333333', linewidth=0.5, zorder=4)      # ④ 道路
    if buildings is not None and len(buildings) > 0:
        buildings.plot(ax=ax, facecolor='#aaaaaa', edgecolor='#555555',
                       linewidth=0.3, zorder=5)                          # ⑤ 建物

    ax.set_xlim(plot_bounds[0], plot_bounds[2])
    ax.set_ylim(plot_bounds[1], plot_bounds[3])
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    fig.savefig(str(out_pdf), format='pdf', dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    size_mb = out_pdf.stat().st_size / 1024 / 1024
    print(f"\n=== 完了 ===")
    print(f"出力PDF: {out_pdf}")
    print(f"ファイルサイズ: {size_mb:.1f} MB  {'✓ 60MB以下' if size_mb <= 60 else '⚠ 60MB超過'}")

if __name__ == "__main__":
    main()
