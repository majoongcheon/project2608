# -*- coding: utf-8 -*-
"""발표자료에 새로 필요한 그림 두 장 — 제목·해설 없이 그림 본체만.

  V18 시스템 구성 (제목 없는 아키텍처 도식)
  V19 군집별 고부담 비율 (원본 507컬럼 PAM k=3)

  PYTHONPATH=ml/.pylibs python3 ml/JSG-deck-extra-charts.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

PAPER, INK, BODY, MUTED = '#FDF9F4', '#2B2724', '#4A443E', '#8A8176'
LINE = '#E4DACC'
CAT1, CAT2, CAT3 = '#eb6834', '#2a78d6', '#1baf7a'
OUT = ROOT / 'docs/assets/발표용'

# ── V18. 시스템 구성 (제목 없음) ────────────────────────────────
f = plt.figure(figsize=(11.5, 5.4)); f.patch.set_facecolor(PAPER)
ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 115); ax.set_ylim(0, 54); ax.axis('off')


def bx(x, y, w, h, head, subs, fc='#FFFFFF', ec=LINE, lw=1.4, hs=12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3,rounding_size=0.9',
                                facecolor=fc, edgecolor=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h - 3.6, head, ha='center', va='center',
            fontsize=hs, color=INK, fontweight='bold', zorder=3)
    for i, t in enumerate(subs):
        ax.text(x + w / 2, y + h - 7.4 - i * 3.2, t, ha='center', va='center',
                fontsize=9.2, color=MUTED, zorder=3)


def ar(p1, p2, color=MUTED, lw=1.6, label=None, lx=0, ly=1.8, dashed=False):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=14, color=color,
                                 lw=lw, zorder=1, shrinkA=2, shrinkB=2,
                                 linestyle=(0, (4, 3)) if dashed else 'solid'))
    if label:
        ax.text((p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly, label, ha='center',
                va='center', fontsize=9, color=color, zorder=4,
                bbox=dict(boxstyle='round,pad=0.22', fc=PAPER, ec='none'))


bx(4, 41, 30, 11, '보호자 브라우저', ['로그인 없음 · 별명만', '7문항 · 약 2분'])
bx(4, 26, 30, 12, '프론트엔드   :9503', ['Vue 3.4 · TypeScript · Vite', 'Leaflet + OpenStreetMap'])
bx(4, 11, 30, 12, '백엔드   :9523', ['Node.js 20 · Express 4 · mysql2', '★ 확률 계산 코드가 없다'],
   ec=CAT1, lw=2.0)
bx(43, 11, 30, 12, '추론 서비스 (Python)', ['cb_burden.serve · scikit-learn', '릴리스 models/ 를 읽는다'],
   fc='#FBF1E8', ec=CAT1, lw=2.0)
bx(43, 26, 30, 12, 'MariaDB 12.1.2', ['기관 1,283곳 · 설정 · 로그', '개인 식별 정보 컬럼 없음'])
bx(82, 11, 29, 27, '오프라인 학습', ['(배포 대상 아님)', '', 'snapshot  스냅샷 고정',
                                  'train  models/runs/ 에만', 'evaluate  test 1회',
                                  'promote  배포본 교체'], fc='#F5F1EA')

ar((19, 41), (19, 38.5), label='답변 7개', lx=-7.5)
ar((19, 26), (19, 23.5), label='POST /api/v1/diagnoses', lx=0.5)
ar((34, 17), (43, 17), color=CAT1, lw=2.2, label='유닉스 소켓 · 포트 안 씀', ly=2.0)
ar((34, 32), (43, 32), color=MUTED, label='기관 조회', ly=1.8)
ar((82, 20), (73, 15.5), color=MUTED, dashed=True, label='promote 로만', ly=-2.6)
f.savefig(OUT / 'V18-시스템구성.png', dpi=200, facecolor=PAPER, bbox_inches='tight', pad_inches=0.1)
plt.close(f); print('   V18-시스템구성.png')

# ── V19. 군집별 고부담 비율 ────────────────────────────────────
CT = {0: [36, 208, 340, 206, 49], 1: [88, 330, 257, 62, 8], 2: [247, 394, 135, 34, 4]}
n = {c: sum(v) for c, v in CT.items()}
hb = {c: (v[0] + v[1]) / sum(v) * 100 for c, v in CT.items()}
overall = sum(v[0] + v[1] for v in CT.values()) / sum(n.values()) * 100

f, ax = plt.subplots(figsize=(8.4, 4.6))
f.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
for s in ('left', 'bottom'): ax.spines[s].set_color(LINE)
ax.tick_params(colors=MUTED, length=0, labelsize=11)
ax.set_axisbelow(True); ax.grid(axis='y', color=LINE, lw=0.8)

xs = [f'군집 {c}\nn={n[c]:,}' for c in (0, 1, 2)]
vals = [hb[c] for c in (0, 1, 2)]
b = ax.bar(xs, vals, width=0.55, color=['#F0A87C', '#DC7A45', '#B04A1E'])
for r, v, c in zip(b, vals, (0, 1, 2)):
    ax.text(r.get_x() + r.get_width() / 2, v + 1.6, f'{v:.1f}%',
            ha='center', fontsize=14, fontweight='bold', color=INK)
    ax.text(r.get_x() + r.get_width() / 2, v - 5.0, f'리프트 {v/overall:.2f}',
            ha='center', fontsize=10.5, color='white')
ax.axhline(overall, color=CAT2, lw=1.8, ls=(0, (4, 3)),
           label=f'전체 고부담 비율 {overall:.1f}%')
ax.set_ylabel('고부담(1~2등급) 비율 (%)', fontsize=12, color=BODY)
ax.set_ylim(0, 92)
ax.legend(frameon=False, fontsize=10.5, loc='upper left')
f.tight_layout()
f.savefig(OUT / 'V19-군집별-고부담비율.png', dpi=200, facecolor=PAPER)
plt.close(f); print('   V19-군집별-고부담비율.png')
