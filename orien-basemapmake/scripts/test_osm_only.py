#!/usr/bin/env python3
"""
OSM取得テスト（DEMなし）
皇居周辺の小エリアで建物・道路・河川を取得してPNG出力
"""
import osmnx as ox
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

out = Path(__file__).parent.parent / "output" / "test_osm.png"
out.parent.mkdir(exist_ok=True)

# 皇居周辺（約1km四方）
# osmnx 2.x: bbox = (west, south, east, north)
north, south, east, west = 35.692, 35.682, 139.757, 139.745
bbox = (west, south, east, north)

print("建物取得中...")
buildings = ox.features_from_bbox(bbox, tags={'building': True})
print(f"  建物: {len(buildings)} 件")

print("道路取得中...")
G = ox.graph_from_bbox(bbox, network_type='all')
roads, _ = ox.graph_to_gdfs(G)
print(f"  道路: {len(roads)} 件")

print("河川取得中...")
rivers = ox.features_from_bbox(bbox, tags={'waterway': True})
print(f"  河川: {len(rivers)} 件")

fig, ax = plt.subplots(figsize=(10, 10))
if len(rivers) > 0:
    rivers.plot(ax=ax, color='#3399ff', linewidth=1.0)
roads.plot(ax=ax, color='#222222', linewidth=0.5)
if len(buildings) > 0:
    buildings.plot(ax=ax, color='#888888', linewidth=0.3)

ax.set_axis_off()
plt.tight_layout()
fig.savefig(str(out), dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"\n出力: {out}")
