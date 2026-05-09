#!/usr/bin/env python3
"""
Phase 3: 国土地理院1mDEM(GML/XML)から等高線を生成する
使い方:
  python3 phase3_contour.py <XMLファイルまたはフォルダ> [等高線間隔m]
例:
  python3 phase3_contour.py ../data/dem/1m/ 2.5
"""

import sys
import re
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path

def parse_fgd_xml(xml_path: Path) -> dict:
    """国土地理院FGD GML(XML)をパースしてDEM情報を返す"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {
        'gml': 'http://www.opengis.net/gml/3.2',
        'fgd': 'http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema',
    }

    # バウンディングボックス取得
    env = root.find('.//gml:Envelope', ns)
    lower = env.find('gml:lowerCorner', ns).text.split()
    upper = env.find('gml:upperCorner', ns).text.split()
    lat_min, lon_min = float(lower[0]), float(lower[1])
    lat_max, lon_max = float(upper[0]), float(upper[1])

    # グリッドサイズ取得 (high は 0-indexed なので+1)
    high = root.find('.//gml:high', ns).text.split()
    cols = int(high[0]) + 1
    rows = int(high[1]) + 1

    # startPoint: データが始まるグリッド位置 (x=col, y=row)
    sp_elem = root.find('.//gml:startPoint', ns)
    if sp_elem is not None:
        sx, sy = map(int, sp_elem.text.split())
        offset = sy * cols + sx
    else:
        offset = 0

    # 標高データ取得
    tuple_list = root.find('.//gml:tupleList', ns).text.strip()
    elevations = []
    for line in tuple_list.splitlines():
        line = line.strip()
        if not line:
            continue
        val = line.split(',')[-1]
        elev = float(val)
        elevations.append(elev if elev > -9000 else np.nan)

    # startPoint 以前は NaN で埋める
    full = np.full(rows * cols, np.nan, dtype=np.float32)
    end  = offset + len(elevations)
    full[offset:end] = elevations

    data = full.reshape(rows, cols)

    return {
        'data': data,
        'lat_min': lat_min, 'lat_max': lat_max,
        'lon_min': lon_min, 'lon_max': lon_max,
        'rows': rows, 'cols': cols,
    }

def dem_to_geotiff(dem_info: dict, out_tif: Path):
    """DEM情報をGeoTIFF(WGS84)として保存"""
    from osgeo import gdal, osr

    data   = dem_info['data']
    rows, cols = data.shape
    lat_min, lat_max = dem_info['lat_min'], dem_info['lat_max']
    lon_min, lon_max = dem_info['lon_min'], dem_info['lon_max']

    pixel_w = (lon_max - lon_min) / cols
    pixel_h = (lat_max - lat_min) / rows

    drv = gdal.GetDriverByName('GTiff')
    ds  = drv.Create(str(out_tif), cols, rows, 1, gdal.GDT_Float32,
                     options=['COMPRESS=LZW', 'TILED=YES'])

    # 左上隅 + ピクセルサイズ（北から南なのでpixel_hは負）
    ds.SetGeoTransform([lon_min, pixel_w, 0, lat_max, 0, -pixel_h])

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(6668)   # JGD2011
    ds.SetProjection(srs.ExportToWkt())

    band = ds.GetRasterBand(1)
    band.WriteArray(np.flipud(data))   # 北が上になるよう反転
    band.SetNoDataValue(-9999)
    ds.FlushCache()
    ds = None

def merge_geotiffs(tif_files: list[Path], merged_tif: Path):
    """複数GeoTIFFをVRT経由でモザイク合成"""
    from osgeo import gdal

    vrt_path = merged_tif.with_suffix('.vrt')
    vrt_options = gdal.BuildVRTOptions(resampleAlg='bilinear')
    vrt = gdal.BuildVRT(str(vrt_path), [str(f) for f in tif_files], options=vrt_options)
    vrt.FlushCache()
    vrt = None

    gdal.Translate(str(merged_tif), str(vrt_path),
                   format='GTiff', creationOptions=['COMPRESS=LZW', 'TILED=YES'])
    vrt_path.unlink(missing_ok=True)
    print(f"  モザイク完了: {merged_tif.name}")

def generate_contours(dem_tif: Path, contour_shp: Path, interval: float):
    """DEMから等高線シェープファイルを生成"""
    from osgeo import gdal, ogr, osr

    src_ds = gdal.Open(str(dem_tif))
    band   = src_ds.GetRasterBand(1)

    drv     = ogr.GetDriverByName('ESRI Shapefile')
    if contour_shp.exists():
        drv.DeleteDataSource(str(contour_shp))
    dst_ds  = drv.CreateDataSource(str(contour_shp))

    srs = osr.SpatialReference()
    srs.ImportFromWkt(src_ds.GetProjection())
    layer = dst_ds.CreateLayer('contour', srs=srs)

    # 標高属性フィールド
    field_def = ogr.FieldDefn('elev', ogr.OFTReal)
    layer.CreateField(field_def)

    gdal.ContourGenerate(band, interval, 0, [], 0, 0, layer, -1, 0)
    dst_ds.FlushCache()
    dst_ds = None
    src_ds = None
    print(f"  等高線生成完了: {contour_shp.name}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    interval   = float(sys.argv[2]) if len(sys.argv) >= 3 else 2.5

    out_dir = Path(__file__).parent.parent / 'output'
    out_dir.mkdir(exist_ok=True)

    # XMLファイルを列挙
    if input_path.is_dir():
        xml_files = sorted(input_path.glob('**/*.xml'))
    else:
        xml_files = [input_path]

    if not xml_files:
        print(f'XMLファイルが見つかりません: {input_path}')
        sys.exit(1)

    print(f'=== Phase 3: 等高線生成 (間隔:{interval}m, ファイル数:{len(xml_files)}) ===')

    # XML → GeoTIFF
    tif_files = []
    for i, xml_file in enumerate(xml_files, 1):
        out_tif = out_dir / (xml_file.stem + '.tif')
        print(f'[{i}/{len(xml_files)}] 変換中: {xml_file.name}')
        try:
            dem_info = parse_fgd_xml(xml_file)
            dem_to_geotiff(dem_info, out_tif)
            tif_files.append(out_tif)
        except Exception as e:
            print(f'  スキップ({e})')

    if not tif_files:
        print('変換できるファイルがありませんでした')
        sys.exit(1)

    # モザイク合成
    if len(tif_files) == 1:
        merged_tif = tif_files[0]
    else:
        merged_tif = out_dir / 'dem_merged.tif'
        print(f'モザイク合成中... ({len(tif_files)}枚)')
        merge_geotiffs(tif_files, merged_tif)

    # 等高線生成
    contour_shp = out_dir / f'contour_{interval}m.shp'
    print('等高線生成中...')
    generate_contours(merged_tif, contour_shp, interval)

    print(f'\n=== 完了 ===')
    print(f'DEM GeoTIFF : {merged_tif}')
    print(f'等高線 SHP  : {contour_shp}')
    print(f'\n次: python3 phase5_pdf.py {contour_shp}')

if __name__ == '__main__':
    main()
