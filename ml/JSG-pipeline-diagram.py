# -*- coding: utf-8 -*-
"""전체 파이프라인 아키텍처 다이어그램 — 목적 → 데이터 준비 → 모델 학습 → 웹서비스.

한 칸마다 두 줄로 적는다.
  윗줄 : 무엇을 하는지 쉬운 말로
  아랫줄: 실제 객체 이름과 실측값
쉬운 말만 있으면 추적이 안 되고, 이름만 있으면 처음 보는 사람이 못 읽는다.

  PYTHONPATH=ml/.pylibs python3 ml/JSG-pipeline-diagram.py

산출: docs/JSG-전체-파이프라인-아키텍처.png · .pdf
읽기 전용 — DB·models·서비스를 건드리지 않는다.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib import font_manager

font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['pdf.fonttype'] = 42

PAPER, INK, BODY, MUTED = '#FDF9F4', '#2B2724', '#4A443E', '#8A8176'
LINE, SOFT = '#E4DACC', '#F3EAE0'
CAT1, CAT2, CAT3, PLUM = '#eb6834', '#2a78d6', '#1baf7a', '#7d4a5f'

W, H = 16.0, 9.5
f = plt.figure(figsize=(W, H)); f.patch.set_facecolor(PAPER)
ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 160); ax.set_ylim(0, 95); ax.axis('off')


def lane(y0, y1, label, sub, color):
    """왼쪽 단계 이름표와 옅은 띠."""
    ax.add_patch(Rectangle((15, y0), 143, y1 - y0, facecolor='#FBF6EF',
                           edgecolor='none', zorder=0))
    ax.add_patch(FancyBboxPatch((2, y0 + (y1 - y0) / 2 - 4.6), 11.5, 9.2,
                                boxstyle='round,pad=0.3,rounding_size=1.0',
                                facecolor=color, edgecolor='none', zorder=2))
    ax.text(7.75, y0 + (y1 - y0) / 2 + 1.4, label, ha='center', va='center',
            fontsize=12.5, color='white', fontweight='bold', zorder=3)
    ax.text(7.75, y0 + (y1 - y0) / 2 - 2.6, sub, ha='center', va='center',
            fontsize=8.5, color='white', zorder=3)


def box(x, y, w, h, head, lines, fc='#FFFFFF', ec=LINE, lw=1.3, hc=INK, hs=11.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3,rounding_size=0.9',
                                facecolor=fc, edgecolor=ec, lw=lw, zorder=2))
    cx = x + w / 2
    ax.text(cx, y + h - 3.4, head, ha='center', va='center', fontsize=hs,
            color=hc, fontweight='bold', zorder=3)
    n = len(lines)
    if n:
        hi, lo = y + h - 6.4, y + 2.2          # 머리글 아래 ~ 바닥 여백
        span = max(hi - lo, 0.1)
        gap = min(3.0, span / max(n - 1, 1)) if n > 1 else 0
        top = (hi + lo) / 2 + (n - 1) * gap / 2
        for i, t in enumerate(lines):
            ax.text(cx, top - i * gap, t, ha='center', va='center',
                    fontsize=8.6, color=MUTED, zorder=3)


def arr(p1, p2, color=MUTED, lw=1.5, dashed=False, label=None, ly=2.6):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=13,
                                 color=color, lw=lw, zorder=1, shrinkA=1, shrinkB=1,
                                 linestyle=(0, (4, 3)) if dashed else 'solid'))
    if label:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + ly, label,
                ha='center', va='center', fontsize=8.4, color=color, zorder=4,
                bbox=dict(boxstyle='round,pad=0.2', fc=PAPER, ec='none'))


# ───────────────────────────────────────────── 제목
ax.text(2, 90.5, '곁 — 돌봄의 무게를 읽다   전체 파이프라인 아키텍처',
        fontsize=21, color=INK, fontweight='bold')
ax.text(2, 86.4, '조사 원자료 507컬럼에서 출발해 7문항 웹 진단 서비스까지 — 각 칸의 윗줄은 하는 일, '
                 '아랫줄은 실제 객체 이름과 실측값이다.', fontsize=10.5, color=BODY)

# ───────────────────────────────────────────── 0. 목적
lane(70, 82, '목적', 'Why', PLUM)
box(17, 71.5, 44, 9.5, '보호자는 자기 상태를 객관적으로 보기 어렵다',
    ['"다들 이 정도는 하고 산다"고 여기며 버틴다'], fc='#F6EFF2', ec=LINE)
box(64, 71.5, 44, 9.5, '지원 제도는 본인이 찾아와 신청해야 작동한다',
    ['부담이 클수록 알아볼 여력이 없다는 역설'], fc='#F6EFF2', ec=LINE)
box(111, 71.5, 47, 9.5, '그래서 — 2분 진단 + 즉시 연계',
    ['짧은 설문으로 가늠 · 왜 그렇게 봤는지 제시 · 가까운 접수처 3곳'],
    fc='#EFE7EB', ec=PLUM, lw=1.8)
arr((61, 76.2), (64, 76.2)); arr((108, 76.2), (111, 76.2))

# ───────────────────────────────────────────── 1. 데이터 준비
lane(45, 67, '데이터 준비', 'Data Preparation', CAT2)
BW, BG = 24.6, 4.0
xs = [17 + i * (BW + BG) for i in range(5)]
box(xs[0], 47, BW, 17, '① 조사 원자료',
    ['2024 발달장애인', '일과 삶 실태조사', '', 'data/snapshots/2024.csv',
     '3,000행 × 507컬럼'], fc='#FFFFFF')
box(xs[1], 47, BW, 17, '② 변수 선별',
    ['500여 개 문항에서', '분석 가능한 항목만', '', '2024_care_burden_std09',
     '3,000행 × 45컬럼'], fc='#FFFFFF')
box(xs[2], 47, BW, 17, '③ 정제·적재',
    ['무응답 코드를 NULL 로', '통일 · 행은 안 버린다', '', 'cb_dataset_v1  43컬럼',
     '메타 4 + target 1 + 설명 38'], fc='#FFFFFF')
box(xs[3], 47, BW, 17, '④ 학습 뷰 2종',
    ['모델 계열에 따라', '결측 표현을 나눈다', '', 'v_cb_tree_v1  42열 (NULL 유지)',
     'v_cb_linear_v1  44열 (-1 + 지시자)'], fc='#FFFFFF')
box(xs[4], 47, BW, 17, '⑤ 층화 분할',
    ['target 비율을 보존해', '나누고 DB 에 못 박는다', '', 'train 2,398 / test 602',
     'cv_fold 1~5 · row_key MD5 고정'], fc='#EAF1FA', ec=CAT2, lw=1.8)
for i in range(4):
    arr((xs[i] + BW, 55.5), (xs[i + 1], 55.5))

# ───────────────────────────────────────────── 2. 모델 학습
lane(20, 42, '모델 학습', 'Model Building', CAT1)
box(xs[0], 22, BW, 17, '⑥ 누수 변수 배제',
    ['정답과 같은 것을 재는', '문항을 아예 뺀다', '', '44 후보 → 설명변수 38개',
     '배제 1위 설명력 19.06% 포기'], fc='#FFFFFF')
box(xs[1], 22, BW, 17, '⑦ 문항 축소',
    ['손실 허용치를 먼저 정하고', '하나씩 빼며 5-fold 측정', '', '후진 제거  38변수 → 7문항',
     'F1 손실 ≤ 0.03 · 재현율 ≥ 0.70'], fc='#FFFFFF')
box(xs[2], 22, BW, 17, '⑧ 변환',
    ['범주를 칸으로 펼친다', '통계는 fold 안에서만', '', '원-핫 설계행렬 53열',
     '결측은 -1 센티널'], fc='#FFFFFF')
box(xs[3], 22, BW, 17, '⑨ 학습·선택',
    ['같은 조건에서 계열 비교', '단순한 쪽이 이겼다', '', '다항 로지스틱 회귀',
     'SEED 20260901 · 5-fold'], fc='#FFFFFF')
box(xs[4], 22, BW, 17, '⑩ 최종 평가·승격',
    ['test 는 마지막에 딱 한 번', '', 'test 602건 1회 — 재현율 0.7730',
     'promote → models/  v1.0.0',
     '판정 불가 문턱 2개 동봉'], fc='#FBF1E8', ec=CAT1, lw=1.8)
for i in range(4):
    arr((xs[i] + BW, 30.5), (xs[i + 1], 30.5))
arr((xs[4] + BW / 2, 47), (xs[0] + BW / 2, 39), color=CAT2, dashed=True,
    label='train 2,398건만 학습·검증에 쓴다  ·  test 602건은 ⑩ 까지 열지 않는다', ly=1.6)

# ───────────────────────────────────────────── 3. 웹서비스
lane(3.5, 17.8, '웹서비스', 'Build & Serve', CAT3)
SW, SG = 22.0, 3.5
sx = [17 + i * (SW + SG) for i in range(5)]
box(sx[0], 4.5, SW, 11, '보호자 브라우저',
    ['로그인 없음 · 별명만', '7문항 · 약 2분'], fc='#FFFFFF')
box(sx[1], 4.5, SW, 11, '프론트엔드  :9503',
    ['Vue 3.4 · TypeScript · Vite', 'Leaflet + OpenStreetMap'], fc='#FFFFFF')
box(sx[2], 4.5, SW, 11, '백엔드  :9523',
    ['Node.js 20 · Express 4 · mysql2', '★ 확률 계산 코드가 없다'], fc='#FFFFFF', ec=CAT3, lw=1.8)
box(sx[3], 4.5, SW, 11, '추론 서비스 (Python)',
    ['cb_burden.serve · scikit-learn', '유닉스 소켓 — 포트를 안 쓴다'], fc='#EAF6F1', ec=CAT3, lw=1.8)
box(sx[4], 4.5, SW, 11, '이용자 화면 출력',
    ['표시 명칭 + 기여 요인 3개', '고부담·판정 불가면 접수처 3곳'], fc='#FFFFFF')
for i in range(4):
    arr((sx[i] + SW, 9.6), (sx[i + 1], 9.6), color=CAT3 if i >= 2 else MUTED)

box(146, 4.5, 12, 11, 'MariaDB', ['기관 1,283곳', '설정 · 로그'], fc='#FFFFFF')
arr((sx[2] + SW / 2, 16.5), (152, 16.5), color=MUTED, dashed=True, label='기관 조회', ly=1.5)
arr((xs[4] + BW / 2, 22), (sx[3] + SW / 2, 15.5), color=CAT1,
    label='배포본은 promote 로만 바뀐다  ·  기동 시 문항 집합·sklearn 버전 대조', ly=1.4)

ax.text(2, 1.2, '작성 조성기(JSG) · 2026-09-03 · 근거: data/snapshots/2024.csv 실측 · '
                'docs/1. 팀에서 채택한 모델-학습-방법.md · docs/SJH-데이터준비와-모델선정.md · '
                '생성 스크립트 ml/JSG-pipeline-diagram.py', fontsize=8.2, color=MUTED)

for ext in ('png', 'pdf'):
    dst = ROOT / f'docs/JSG-전체-파이프라인-아키텍처.{ext}'
    f.savefig(dst, dpi=200 if ext == 'png' else None, facecolor=PAPER,
              bbox_inches='tight', pad_inches=0.15)
    print('  ', dst)
plt.close(f)
