# -*- coding: utf-8 -*-
"""발표용 차트 생성. 편지 톤(살구빛) 팔레트로 통일한다."""
import json, sys, math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf']:
    font_manager.fontManager.addfont(f)
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

D = json.loads((ROOT / 'docs/assets/chart_data.json').read_text(encoding='utf-8'))
OUT = ROOT / 'docs/assets'; OUT.mkdir(parents=True, exist_ok=True)

# ── 팔레트 ─────────────────────────────────────────────────────────
# 바탕·글자는 서비스의 편지 톤을 그대로 쓰고, **데이터 마크만** 검증을 통과한 색으로 둔다.
# 브랜드 톤을 맞추려다 구분이 안 되면 차트의 의미가 없다.
#
# 검증(dataviz validate_palette, light, surface #FDF9F4):
#   2색 #eb6834,#2a78d6            ALL PASS  정상시야 ΔE 33.6 · CVD 24.7
#   3색 +#1baf7a                   ALL PASS  정상시야 ΔE 24.0
#   기존 살구 5색 램프              FAIL      정상시야 ΔE 10.1 (기준 15 미달)
PAPER, INK, BODY, MUTED = '#FDF9F4', '#2B2724', '#4A443E', '#8A8176'
LINE = '#E4DACC'
CAT1, CAT2, CAT3 = '#eb6834', '#2a78d6', '#1baf7a'   # 식별용 (검증 통과 순서)
ACCENT = CAT1                                        # 강조 = 1번 슬롯
GRAY = '#9A9187'                                     # 비강조·배제

# 부담 5구간은 **순서형(ordinal)** 이다 — 식별이 아니라 크기를 나타내므로 단일 색조 램프가 맞다.
# 누적 막대 안에 구간 명칭을 직접 적어 색만으로 구분하지 않게 한다.
BURDEN = {1: '#7A2E10', 2: '#B04A1E', 3: '#DC7A45', 4: '#F0A87C', 5: '#F6C9AC'}
NAME = {1: '최고부담', 2: '고부담', 3: '중간', 4: '저부담', 5: '부담없음'}

def fig(w, h):
    f, ax = plt.subplots(figsize=(w, h))
    f.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(LINE)
    ax.tick_params(colors=MUTED, length=0, labelsize=10)
    ax.set_axisbelow(True)
    return f, ax

def save(f, name):
    f.tight_layout(); f.savefig(OUT / name, dpi=200, facecolor=PAPER); plt.close(f)
    print('  ', name)

# ── A. 부담 분포 100% 누적 막대 ─────────────────────────────────────
CNT = {1: 464, 2: 1165, 3: 916, 4: 378, 5: 77}
tot = sum(CNT.values())
f, ax = fig(11, 3.0)
left = 0
for lv in [1, 2, 3, 4, 5]:
    pct = CNT[lv] / tot * 100
    ax.barh([0], [pct], left=left, height=0.5, color=BURDEN[lv], edgecolor=PAPER, lw=2)
    if pct > 4:
        ax.text(left + pct / 2, 0, f'{NAME[lv]}\n{pct:.1f}%', ha='center', va='center',
                fontsize=11, color='white' if lv <= 2 else INK, fontweight='bold')
    left += pct
hb = (CNT[1] + CNT[2]) / tot * 100
ax.plot([0, hb], [0.42, 0.42], color=ACCENT, lw=2.2)
ax.plot([0, 0], [0.38, 0.46], color=ACCENT, lw=2.2)
ax.plot([hb, hb], [0.38, 0.46], color=ACCENT, lw=2.2)
ax.text(hb / 2, 0.55, f'고부담군 {hb:.1f}%  ·  1,629가구', ha='center', fontsize=14,
        color=ACCENT, fontweight='bold')
ax.text(hb + (100 - hb) / 2, 0.55, f'나머지 {100-hb:.1f}%', ha='center', fontsize=12, color=MUTED)
ax.set_xlim(0, 100); ax.set_ylim(-0.45, 0.8)
ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(['0', '25', '50', '75', '100%'])
ax.text(0, -0.38, '2024 발달장애인 일과 삶 실태조사 3,000가구  ·  숫자가 작을수록 부담이 크다',
        fontsize=10, color=MUTED)
save(f, 'A-부담분포.png')

# ── D. MI 설명력 + 배제 변수 ────────────────────────────────────────
LAB = {'help_needed_hours': '도움 필요 시간', 'understands_work_meaning': '근로 의미 이해도',
       'can_work_standard_job': '통상근로 가능', 'severe_dd_job_willingness': '최중증 취업의사',
       'family_support_for_employment': '가족 취업지지', 'daily_routine_satisfaction': '일과 만족도',
       'overall_health': '전반적 건강', 'wants_person_employed': '취업 희망',
       'past_employment_exp': '과거 취업경험', 'employment_status': '종사상 지위',
       'job_ability_mobility': '이동 능력', 'is_employed': '취업 여부',
       'job_ability_strength': '근력·체력', 'school_helpfulness': '학교교육 도움',
       'household_head_type': '가구주 유형', 'relation_to_person': '당사자와 관계',
       'last_job_quit_reason': '퇴사 이유', 'caregiver_age': '보호자 나이',
       'age_disability_suspected': '장애의심 나이', 'caregiver_life_satisfaction': '보호자 삶 만족도',
       'care_difficulty_top1': '돌봄 어려움 1순위', 'needed_care_service_type': '필요 돌봄서비스',
       'work_care_gap_hours': '월평균 돌봄공백', 'work_care_gap_exp': '근로중 돌봄공백',
       'integrated_care_awareness': '통합돌봄 인지'}
top = D['mi'][:18]
f, ax = fig(11, 6.2)
ys = np.arange(len(top))[::-1]
sel7 = set(D['selected7'])
for yy, r in zip(ys, top):
    if r['excluded']:
        c, hatch = GRAY, '///'
    elif r['feature'] in sel7:
        c, hatch = CAT1, None
    else:
        c, hatch = '#D8CFC3', None
    ax.barh([yy], [r['mi']], height=0.7, color=c, hatch=hatch, edgecolor=PAPER)
    ax.text(r['mi'] + 0.25, yy, f"{r['mi']:.2f}", va='center', fontsize=9, color=MUTED)
ax.set_yticks(ys)
ax.set_yticklabels([LAB.get(r['feature'], r['feature']) for r in top], fontsize=10, color=BODY)
ax.set_xlabel('단독 설명력  MI / H  (%)', fontsize=11, color=BODY)
ax.set_xlim(0, 21)
ax.annotate('배제 — target과 같은 것을 잼', xy=(19.06, ys[0]), xytext=(12.5, ys[0] - 2.2),
            fontsize=11, color=GRAY, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=GRAY, lw=1.4))
h = [plt.Rectangle((0, 0), 1, 1, color=CAT1),
     plt.Rectangle((0, 0), 1, 1, color='#D8CFC3'),
     plt.Rectangle((0, 0), 1, 1, color=GRAY, hatch='///')]
ax.legend(h, ['채택 7문항', '잔존(미채택)', 'Data Leakage 배제 6개'],
          frameon=False, fontsize=10, loc='lower right')
save(f, 'D-설명력순위.png')

# ── E. 군집화 — 작은 다중 패널 + 실루엣 ────────────────────────────
# 5개 구간을 한 판에 색으로 겹쳐 찍으면 서로 가려 아무것도 안 보인다.
# 구간마다 패널을 따로 두고 나머지를 회색으로 깔면 "어디에도 몰리지 않는다"가 분명해진다.
# 색은 하나만 쓰므로 5색을 구분할 필요가 없다.
P, lab, evr = D['pca'], np.array(D['pca']['label']), D['pca']['evr']
px, py = np.array(P['x']), np.array(P['y'])
f = plt.figure(figsize=(13.2, 3.65)); f.patch.set_facecolor(PAPER)
gs = f.add_gridspec(1, 6, width_ratios=[1, 1, 1, 1, 1, 1.45], wspace=0.22)
for c, lv in enumerate([1, 2, 3, 4, 5]):
    ax = f.add_subplot(gs[0, c]); ax.set_facecolor(PAPER)
    m = lab == lv
    ax.scatter(px[~m], py[~m], s=3.5, color='#DFD8CE', alpha=0.6, linewidths=0)
    ax.scatter(px[m], py[m], s=5.5, color=CAT1, alpha=0.85, linewidths=0)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect('equal')
    for sp in ax.spines.values(): sp.set_color(LINE)
    ax.set_title(f'{NAME[lv]}\nn={m.sum():,}', fontsize=11, color=INK, pad=6)

ax = f.add_subplot(gs[0, 5]); ax.set_facecolor(PAPER)
for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
for sp in ('left', 'bottom'): ax.spines[sp].set_color(LINE)
ax.tick_params(colors=MUTED, length=0, labelsize=9.5)
ax.grid(axis='y', color=LINE, lw=0.8); ax.set_axisbelow(True)
C = D['cluster']
ax.plot(C['k'], C['silhouette'], color=CAT2, lw=2.2, marker='o', ms=5)
ax.axhline(0.25, color=GRAY, lw=1.4, ls=(0, (4, 3)))
ax.text(10, 0.259, '0.25 미만 = 구조 없음', ha='right', fontsize=9.5, color=GRAY)
ax.scatter([2], [C['silhouette'][0]], s=150, facecolor=PAPER, edgecolor=CAT2, lw=2.4, zorder=5)
ax.annotate('k=2', (2, C['silhouette'][0]), textcoords='offset points', xytext=(9, 7),
            fontsize=12, color=CAT2, fontweight='bold')
ax.set_ylim(0, 0.3); ax.set_xlabel('군집 수 k', fontsize=10.5, color=BODY)
ax.set_title('실루엣 계수 — 나뉘는 수는 2', fontsize=11.5, color=INK, pad=6)

f.suptitle('부담 구간마다 따로 칠해 봐도 — 어느 구간도 제자리를 갖지 않는다',
           x=0.008, ha='left', fontsize=15, color=INK, fontweight='bold')
f.text(0.008, 0.015,
       f'회색은 전체 2,398건, 주황은 해당 구간.  주성분 2개로 편 좌표 — PC1 {evr[0]*100:.1f}% · PC2 {evr[1]*100:.1f}%.  '
       '어느 구간도 특정 영역에 몰리지 않는다.',
       fontsize=10.5, color=MUTED)
f.tight_layout(rect=[0, 0.06, 1, 0.90])
f.savefig(OUT / 'E-군집화.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   E-군집화.png')

# ── C. 문항 수별 성능 곡선 ─────────────────────────────────────────
# 두 지표의 범위가 크게 달라(F1 0.29~0.34 · 재현율 0.72~0.79) 한 축에 겹치면
# 변화가 뭉개진다. 위아래 두 패널로 나누고 각자 범위를 준다.
cv = sorted(D['curve'], key=lambda r: r['k'])
ks = [r['k'] for r in cv]; f1 = [r['f1'] for r in cv]; rc = [r['recall'] for r in cv]
f, axes = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True,
                       gridspec_kw={'height_ratios': [1.25, 1], 'hspace': 0.18})
f.patch.set_facecolor(PAPER)
for ax in axes:
    ax.set_facecolor(PAPER)
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'): ax.spines[sp].set_color(LINE)
    ax.tick_params(colors=MUTED, length=0, labelsize=10)
    ax.set_axisbelow(True); ax.grid(axis='y', color=LINE, lw=0.8)

ax = axes[0]
ax.plot(ks, f1, color=ACCENT, lw=2.2, marker='o', ms=4)
ax.axvline(7, color=INK, lw=1.3, ls=(0, (2, 2)))
ax.scatter([7], [0.3383], s=200, facecolor=PAPER, edgecolor=ACCENT, lw=2.8, zorder=6)
ax.annotate('k=7 채택 — F1 최고', (7, 0.3383), textcoords='offset points', xytext=(-14, 12),
            ha='right', fontsize=12, color=ACCENT, fontweight='bold')
ax.annotate('k=6 급락', (6, 0.2951), textcoords='offset points', xytext=(-18, -16),
            ha='right', fontsize=11.5, color=INK,
            arrowprops=dict(arrowstyle='->', color=INK, lw=1.3))
ax.set_ylabel('macro F1', fontsize=12, color=BODY)
ax.set_ylim(0.28, 0.355)
ax.set_title('줄일수록 좋아졌다 — 38개는 오히려 과적합', fontsize=15, color=INK, loc='left', pad=12)

ax = axes[1]
ax.plot(ks, rc, color=CAT2, lw=2.2, marker='s', ms=4)
ax.axhline(0.70, color=GRAY, lw=1.4, ls=(0, (4, 3)))
ax.text(37.6, 0.706, '하한 0.70 — 한 번도 깨지 않았다', fontsize=10, color=GRAY, va='bottom', ha='left')
ax.axvline(7, color=INK, lw=1.3, ls=(0, (2, 2)))
ax.scatter([7], [0.7843], s=200, facecolor=PAPER, edgecolor=CAT2, lw=2.8, zorder=6)
ax.set_ylabel('고부담 재현율', fontsize=12, color=BODY)
ax.set_ylim(0.68, 0.82)
ax.invert_xaxis()
ax.set_xlabel('문항 수  (왼쪽 38개에서 오른쪽으로 하나씩 제거해 간다)', fontsize=12, color=BODY)
f.tight_layout(); f.savefig(OUT / 'C-문항수곡선.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   C-문항수곡선.png')

# ── F. 7문항 vs 14문항 — 지표 4종 ─────────────────────────────────
# 막대 두 개짜리 차트는 아래가 비어 슬라이드가 허전했다.
# 표로 따로 두던 지표를 차트 안으로 들여 한 판에서 읽히게 한다.
# (제목, 7문항, 14문항, 표기형식, 아래 한 줄 평)
METRICS = [
    ('macro F1 (test)', 0.3416, 0.3420, '{:.4f}',  '차이 0.0004 — 사실상 같다'),
    ('고부담 재현율',     0.7730, 0.7669, '{:.4f}',  '7문항이 오히려 높다'),
    ('판정 불가 비율',    2.49,   4.20,   '{:.2f}%', '낮을수록 좋다 — 14문항이 1.7배'),
    ('원-핫 열 수',      53,     224,    '{:.0f}',  '낮을수록 단순하다 — 4.2배 차이'),
]
f, axes = plt.subplots(1, 4, figsize=(12.6, 4.3))
f.patch.set_facecolor(PAPER)
for ax, (title, v7, v14, fmt, note) in zip(axes, METRICS):
    ax.set_facecolor(PAPER)
    for sp in ('top', 'right', 'left'): ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_color(LINE)
    ax.tick_params(colors=BODY, length=0, labelsize=11.5, pad=6)
    b = ax.bar(['7문항', '14문항'], [v7, v14], width=0.52, color=[CAT1, CAT2])
    top = max(v7, v14)
    for r, v in zip(b, [v7, v14]):
        ax.text(r.get_x() + r.get_width() / 2, v + top * 0.045, fmt.format(v),
                ha='center', fontsize=13.5, fontweight='bold', color=INK)
    ax.set_ylim(0, top * 1.32); ax.set_yticks([])
    ax.set_title(title, fontsize=13, color=INK, pad=12)
    # 한 줄 평은 눈금 라벨 아래에 둔다 — 겹치지 않게 축 좌표로 배치
    ax.text(0.5, -0.155, note, ha='center', va='top', fontsize=10.5,
            color=MUTED, transform=ax.transAxes)
f.suptitle('문항을 두 배로 늘렸을 때 — 성능은 그대로, 판정 불가만 1.7배',
           x=0.008, ha='left', fontsize=14.5, color=INK, fontweight='bold')
f.tight_layout(rect=[0, 0.10, 1, 0.90])
f.savefig(OUT / 'F-판정불가비교.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   F-판정불가비교.png')

# ── B. k별 혼동행렬 ────────────────────────────────────────────────
CF = D['confusion']
f, axes = plt.subplots(1, 3, figsize=(12.6, 4.3))
f.patch.set_facecolor(PAPER)
for ax, k in zip(axes, ['38', '7', '6']):
    cm = np.array(CF[k]['cm2'], dtype=float)
    pct = cm / cm.sum(axis=1, keepdims=True) * 100
    ax.set_facecolor(PAPER)
    ax.imshow(pct, cmap='OrRd', vmin=0, vmax=100, alpha=0.85)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f'{int(cm[i,j])}\n{pct[i,j]:.0f}%', ha='center', va='center',
                    fontsize=13, fontweight='bold',
                    color='white' if pct[i, j] > 55 else INK)
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(['고부담\n예측', '아님\n예측'], fontsize=10, color=BODY)
    ax.set_yticklabels(['실제\n고부담', '실제\n아님'], fontsize=10, color=BODY)
    ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    star = '  ← 채택' if k == '7' else ''
    ax.set_title(f'{k}문항{star}\n재현율 {CF[k]["recall"]:.3f} · F1 {CF[k]["macro_f1"]:.4f}',
                 fontsize=12, color=ACCENT if k == '7' else INK, pad=10,
                 fontweight='bold' if k == '7' else 'normal')
f.suptitle('문항을 31개 버려도 오류 구조가 그대로다 — 교차검증 2,398건 기준',
           x=0.012, ha='left', fontsize=14, color=INK, fontweight='bold')
f.tight_layout(rect=[0, 0.04, 1, 0.93])
f.savefig(OUT / 'B-혼동행렬2x2.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   B-혼동행렬2x2.png')

# 5×5 — k=7 vs k=6. 2×2 로는 둘이 거의 같아 보이지만 5구간으로 보면 다르다.
f, axes = plt.subplots(1, 2, figsize=(12.8, 5.6))
f.patch.set_facecolor(PAPER)
n5 = [NAME[v] for v in [1, 2, 3, 4, 5]]
for ax, k in zip(axes, ['7', '6']):
    cm5 = np.array(CF[k]['cm5'], dtype=float)
    row = cm5 / cm5.sum(axis=1, keepdims=True) * 100
    ax.set_facecolor(PAPER)
    ax.imshow(row, cmap='OrRd', vmin=0, vmax=75, alpha=0.85)
    for i2 in range(5):
        for j2 in range(5):
            ax.text(j2, i2, f'{int(cm5[i2,j2])}', ha='center', va='center', fontsize=11,
                    fontweight='bold' if i2 == j2 else 'normal',
                    color='white' if row[i2, j2] > 48 else INK)
    ax.set_xticks(range(5)); ax.set_yticks(range(5))
    ax.set_xticklabels(n5, fontsize=9.5, color=BODY)
    ax.set_yticklabels(n5, fontsize=9.5, color=BODY)
    ax.set_xlabel('예측', fontsize=10.5, color=BODY)
    if k == '7': ax.set_ylabel('실제', fontsize=10.5, color=BODY)
    ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
    # 최고부담 행을 강조 — 여기가 무너진다
    ax.add_patch(plt.Rectangle((-0.5, -0.5), 5, 1, fill=False,
                 edgecolor=ACCENT if k == '7' else '#8C3D1E', lw=2.6))
    rec1 = cm5[0, 0] / cm5[0].sum()
    ax.set_title(f'{k}문항{"  ← 채택" if k == "7" else ""}\n'
                 f'최고부담군 재현율 {rec1:.3f}  ·  macro F1 {CF[k]["macro_f1"]:.4f}',
                 fontsize=12.5, color=ACCENT if k == '7' else INK, pad=10,
                 fontweight='bold')
f.suptitle('2×2 로는 둘이 같아 보이지만 — 6문항은 최고부담군을 거의 못 찍는다',
           x=0.012, ha='left', fontsize=14.5, color=INK, fontweight='bold')
f.text(0.012, 0.015,
       '최고부담군으로 예측한 건수  7문항 147건 → 6문항 44건.  가장 도움이 절실한 구간을 따로 가려내지 못하게 된다.  교차검증 2,398건 기준',
       fontsize=10.5, color=MUTED)
f.tight_layout(rect=[0, 0.05, 1, 0.92])
f.savefig(OUT / 'B-혼동행렬5x5.png', dpi=200, facecolor=PAPER); plt.close(f)
print('   B-혼동행렬5x5.png')

print('차트 생성 완료')
