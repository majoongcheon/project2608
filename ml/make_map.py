# -*- coding: utf-8 -*-
"""G. 연령-서비스 사각지대 다이어그램 + 대전 지역 기관 지도(OSM 타일)."""
import json, sys, math, io as _io, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs')); sys.path.insert(0, str(ROOT / 'ml'))

import numpy as np, pymysql
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, patches
from PIL import Image
import db as dbmod

for f in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf']:
    font_manager.fontManager.addfont(f)
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# make_charts.py 와 같은 팔레트 — 바탕은 편지 톤, 데이터 마크는 검증 통과 색
PAPER, INK, BODY, MUTED = '#FDF9F4', '#2B2724', '#4A443E', '#8A8176'
LINE, GRAY = '#E4DACC', '#9A9187'
CAT1, CAT2, CAT3 = '#eb6834', '#2a78d6', '#1baf7a'   # 3색 검증 ALL PASS (정상시야 ΔE 24.0)
ACCENT, GREEN = CAT1, CAT3
OUT = ROOT / 'docs/assets'

# ── G. 연령–서비스 사각지대 ────────────────────────────────────────
f, ax = plt.subplots(figsize=(11.5, 4.6))
f.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
A0, A1 = 0, 80
def band(y, x0, x1, color, label, sub, txtcol='white'):
    ax.add_patch(patches.FancyBboxPatch((x0, y), x1 - x0, 0.72,
        boxstyle='round,pad=0.02,rounding_size=0.6', facecolor=color, edgecolor='none'))
    ax.text((x0 + x1) / 2, y + 0.46, label, ha='center', fontsize=12.5,
            fontweight='bold', color=txtcol)
    ax.text((x0 + x1) / 2, y + 0.19, sub, ha='center', fontsize=10, color=txtcol)

band(2.0, 6, 18, CAT2, '청소년 방과후활동서비스', '만 6~17세  ·  553곳 · 196개 시군구')
band(1.0, 18, 65, CAT1, '발달장애인 주간활동서비스', '만 18~64세  ·  724곳 · 217개 시군구')

# 사각지대
for x0, x1, txt, sub in [(A0, 6, '만 6세 미만', '발달재활서비스\n주민센터 문의'),
                         (65, A1, '만 65세 이상', '노인장기요양 ·\n발달장애인지원센터')]:
    ax.add_patch(patches.Rectangle((x0, 0.9), x1 - x0, 1.92, facecolor='#EFE7DC',
                 edgecolor=GRAY, lw=1.2, ls=(0, (4, 3))))
    ax.text((x0 + x1) / 2, 2.35, txt, ha='center', fontsize=12, fontweight='bold', color=GRAY)
    ax.text((x0 + x1) / 2, 1.55, '사각지대', ha='center', fontsize=13,
            fontweight='bold', color=ACCENT)
    ax.text((x0 + x1) / 2, 1.15, sub, ha='center', fontsize=9.5, color=MUTED)

for x in [6, 18, 65]:
    ax.plot([x, x], [0.55, 3.05], color=INK, lw=1, ls=(0, (2, 3)), alpha=0.5)
    ax.text(x, 0.35, f'만 {x}세', ha='center', fontsize=10.5, color=INK, fontweight='bold')
ax.annotate('', xy=(A1, 0.1), xytext=(A0, 0.1),
            arrowprops=dict(arrowstyle='->', color=BODY, lw=1.4))
ax.text(A1, -0.15, '당사자 연령', ha='right', fontsize=10.5, color=BODY)
ax.set_xlim(-2, A1 + 3); ax.set_ylim(-0.5, 3.3); ax.axis('off')
ax.set_title('제도의 틈 — 만 6세 미만과 만 65세 이상은 어느 쪽에도 속하지 않는다',
             fontsize=14, color=INK, loc='left', pad=14)
ax.text(0, -0.42, '이 서비스는 사각지대를 화면에서 배제하지 않는다. 기관 3곳을 그대로 보여주며 이용 대상 조건을 함께 표시한다.',
        fontsize=10.5, color=MUTED)
f.tight_layout(); f.savefig(OUT / 'G-사각지대.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   G-사각지대.png')

# ── 대전 지역 기관 지도 (OSM 타일) ─────────────────────────────────
con = dbmod.connect(); cur = con.cursor()
cur.execute("""SELECT f.name, f.lat, f.lng, g.sigungu_name,
        GROUP_CONCAT(s.service_type ORDER BY s.service_type) t
      FROM cb_facility_v1 f
      JOIN cb_region_v1 g ON g.region_code = f.region_code
      JOIN cb_facility_service_v1 s ON s.facility_id = f.facility_id
     WHERE g.sido_name = '대전광역시'
     GROUP BY f.facility_id""")
rows = cur.fetchall(); con.close()
print(f'   대전 기관 {len(rows)}곳')

lats = np.array([r[1] for r in rows]); lngs = np.array([r[2] for r in rows])
pad = 0.028
w, e = lngs.min() - pad, lngs.max() + pad
s_, n_ = lats.min() - pad, lats.max() + pad

Zm = 11
def deg2tile(lat, lon, z):
    lat_r = math.radians(lat); nn = 2 ** z
    return ((lon + 180) / 360 * nn, (1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * nn)
def tile2deg(x, y, z):
    nn = 2 ** z
    lon = x / nn * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / nn))))
    return lat, lon

x0f, y0f = deg2tile(n_, w, Zm); x1f, y1f = deg2tile(s_, e, Zm)
x0, x1 = int(math.floor(x0f)), int(math.floor(x1f))
y0, y1 = int(math.floor(y0f)), int(math.floor(y1f))
TS = 256
canvas = Image.new('RGB', ((x1 - x0 + 1) * TS, (y1 - y0 + 1) * TS), '#F2EFE9')
ok = 0
for tx in range(x0, x1 + 1):
    for ty in range(y0, y1 + 1):
        url = f'https://tile.openstreetmap.org/{Zm}/{tx}/{ty}.png'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'p3-sumzip-presentation/1.0'})
            img = Image.open(_io.BytesIO(urllib.request.urlopen(req, timeout=15).read())).convert('RGB')
            canvas.paste(img, ((tx - x0) * TS, (ty - y0) * TS)); ok += 1
        except Exception as ex:
            print('     타일 실패', tx, ty, type(ex).__name__)
print(f'   OSM 타일 {ok}장 합성 (zoom {Zm})')

lat_tl, lon_tl = tile2deg(x0, y0, Zm)
lat_br, lon_br = tile2deg(x1 + 1, y1 + 1, Zm)

f, ax = plt.subplots(figsize=(7.6, 8.2))
f.patch.set_facecolor(PAPER)
ax.imshow(canvas, extent=[lon_tl, lon_br, lat_br, lat_tl], alpha=0.62, aspect='auto')

both = [r for r in rows if ',' in (r[4] or '')]
day  = [r for r in rows if r[4] == 'DAY_ACTIVITY']
aft  = [r for r in rows if r[4] == 'AFTERSCHOOL_YOUTH']
# 색과 모양을 함께 쓴다 — 색만으로 구분하지 않는다
for grp, col, mk, lb in [(day, CAT1, 'o', f'주간활동 전용 ({len(day)})'),
                         (aft, CAT3, '^', f'방과후 전용 ({len(aft)})'),
                         (both, CAT2, 's', f'두 유형 모두 ({len(both)})')]:
    if grp:
        ax.scatter([r[2] for r in grp], [r[1] for r in grp], s=110, marker=mk,
                   color=col, edgecolor='white', linewidth=1.6, zorder=5, label=lb)

for gu, la, ln in [('유성구', 36.3620, 127.3560), ('대덕구', 36.3860, 127.4270),
                   ('동구', 36.3320, 127.4480), ('중구', 36.3130, 127.4090),
                   ('서구', 36.3300, 127.3620)]:
    ax.text(ln, la, gu, fontsize=13, color=INK, fontweight='bold', ha='center',
            zorder=6, bbox=dict(boxstyle='round,pad=0.25', facecolor=PAPER, edgecolor='none', alpha=0.78))

ax.set_xlim(w, e); ax.set_ylim(s_, n_)
ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values(): sp.set_color(LINE)
ax.legend(frameon=True, fontsize=10.5, loc='lower left', facecolor=PAPER, edgecolor=LINE, framealpha=0.92)
ax.set_title(f'대전광역시 신청 접수처 {len(rows)}곳', fontsize=15, color=INK, loc='left', pad=12)
ax.text(0.5, -0.035, '© OpenStreetMap 기여자  ·  발급 키 없이 표시', transform=ax.transAxes,
        fontsize=8.5, color=MUTED, ha='center')
f.tight_layout(); f.savefig(OUT / 'H-대전지도.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   H-대전지도.png')
