#!/usr/bin/env python3
"""
Phase 5: 等高線 + 磁北線をA3 PDFに出力する
使い方:
  python3 phase5_pdf.py <contour.shp> [出力PDF名]
例:
  python3 phase5_pdf.py ../output/contour_2.5m.shp ../output/map_A3.pdf
"""

import sys
import os
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

def calc_declination(lat: float, lon: float, year: float = 2026.3) -> float:
    """エリア中心の磁北偏差を取得（pygeomag使用）"""
    try:
        from pygeomag import GeoMag
        gm = GeoMag()
        result = gm.calculate(glat=lat, glon=lon, alt=0, time=year)
        return result.d
    except Exception as e:
        print(f"  警告: 磁北計算失敗({e})。デフォルト -7.5° を使用")
        return -7.5

def draw_magnetic_lines(ax, bounds, declination_deg: float, interval_m: float = 500):
    """磁北線を描画（IOF規格: 青・0.3mm相当・500m間隔）"""
    angle = np.radians(declination_deg)
    xmin, ymin, xmax, ymax = bounds
    height = ymax - ymin
    for x in np.arange(xmin - height, xmax + height, interval_m):
        dx = height * np.tan(angle)
        ax.plot(
            [x, x + dx], [ymin, ymax],
            color='#4477cc', linewidth=0.3, alpha=0.7, zorder=1,
        )

def check_scale(bounds, paper_size_mm=(420, 297)) -> tuple[float, bool]:
    """縮尺を計算し、推奨範囲（1:4000〜1:15000）内かチェック"""
    xmin, ymin, xmax, ymax = bounds
    area_w_mm = (xmax - xmin) * 1000  # m → mm
    area_h_mm = (ymax - ymin) * 1000
    scale_w = area_w_mm / paper_size_mm[0]
    scale_h = area_h_mm / paper_size_mm[1]
    scale = max(scale_w, scale_h)
    ok = 4000 <= scale <= 15000
    return scale, ok

def latlon_from_plane(xmin, ymin, xmax, ymax, epsg=6675):
    """平面直角座標系の中心座標をWGS84に変換"""
    from osgeo import osr
    src = osr.SpatialReference()
    src.ImportFromEPSG(epsg)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(4326)
    # GDAL 3.x では軸順序が (lat, lon) になるため AUTHORITY_COMPLIANT を無効化
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(src, dst)
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    lon, lat, _ = ct.TransformPoint(cx, cy)
    return lat, lon

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    shp_path = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2]) if len(sys.argv) >= 3 else shp_path.parent / "map_A3.pdf"

    print(f"=== Phase 5: PDF出力 ===")
    print(f"等高線: {shp_path}")

    # 1. 等高線読み込み
    contours = gpd.read_file(shp_path)
    if contours.crs is None:
        contours = contours.set_crs("EPSG:6668")
    # 平面直角座標系に変換（単位:m）
    # 第6系(6675): 広島・中国 / 第9系(6677): 関東
    contours = contours.to_crs("EPSG:6675")

    bounds = contours.total_bounds   # [xmin, ymin, xmax, ymax]
    print(f"  範囲: {bounds}")

    # 2. 縮尺チェック
    scale, ok = check_scale(bounds)
    print(f"  縮尺: 1:{int(scale):,}  {'✓ 推奨範囲内' if ok else '⚠ 推奨縮尺(1:4000〜1:15000)を超えています'}")

    # 3. 磁北偏差
    try:
        lat, lon = latlon_from_plane(*bounds, epsg=6675)
    except Exception:
        lat, lon = 35.0, 139.0   # フォールバック（関東）
    declination = calc_declination(lat, lon)
    print(f"  磁北偏差: {declination:.2f}°（緯度:{lat:.3f} 経度:{lon:.3f}）")

    # 4. 描画（A3横: 420mm×297mm）
    fig, ax = plt.subplots(figsize=(16.54, 11.69))   # inches (A3 landscape)
    ax.set_aspect('equal')

    # ① 磁北線（最背面）
    draw_magnetic_lines(ax, bounds, declination, interval_m=500)

    # ② 等高線
    contours.plot(ax=ax, color='#8B5A2B', linewidth=0.5, zorder=2)

    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # 5. PDF出力（300dpi）
    fig.savefig(str(out_pdf), format='pdf', dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    size_mb = out_pdf.stat().st_size / 1024 / 1024
    print(f"\n=== 完了 ===")
    print(f"出力PDF: {out_pdf}")
    print(f"ファイルサイズ: {size_mb:.1f} MB  {'✓ 60MB以下' if size_mb <= 60 else '⚠ 60MBを超えています'}")
    if size_mb > 60:
        print("  → phase5_pdf.py に --simplify オプションを追加して頂点を間引いてください")

if __name__ == "__main__":
    main()
