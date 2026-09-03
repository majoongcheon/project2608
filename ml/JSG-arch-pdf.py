# -*- coding: utf-8 -*-
"""심사·타 팀 발표용 — 아키텍처와 모델 작동 설명 PDF.

대상: 심사 교수님(대학원 수준) + 타 팀(학부·동료 수준).
용어는 그대로 쓰되 처음 나올 때 한 줄로 풀고, 설계 결정과 맞바꿈을 중심에 둔다.

  PYTHONPATH=ml/.pylibs python3 ml/JSG-arch-pdf.py

산출: docs/JSG-아키텍처와-모델설명-발표용.pdf (8쪽) + docs/assets/발표용/pdf-preview/*.png
읽기 전용 — DB·models·서비스를 건드리지 않는다.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib import font_manager

font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['pdf.fonttype'] = 42          # 폰트 임베드 — 다른 PC 에서도 깨지지 않는다

PAPER, INK, BODY, MUTED = '#FDF9F4', '#2B2724', '#4A443E', '#8A8176'
LINE, SOFT = '#E4DACC', '#F3EAE0'
CAT1, CAT2, CAT3 = '#eb6834', '#2a78d6', '#1baf7a'
PLUM = '#7d4a5f'

W, H = 13.333, 7.5
PREV = ROOT / 'docs/assets/발표용/pdf-preview'; PREV.mkdir(parents=True, exist_ok=True)
pages = []


def page(title, kicker=None, foot=None):
    f = plt.figure(figsize=(W, H)); f.patch.set_facecolor(PAPER)
    ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis('off'); ax.set_facecolor(PAPER)
    if kicker:
        ax.text(5, 93.5, kicker, fontsize=11, color=CAT1, fontweight='bold')
    ax.text(5, 87.5, title, fontsize=25, color=INK, fontweight='bold', va='center')
    ax.plot([5, 95], [83.2, 83.2], color=LINE, lw=1.4)
    if foot:
        ax.text(5, 3.2, foot, fontsize=9, color=MUTED)
    return f, ax


def box(ax, x, y, w, h, lines, fc=SOFT, ec=LINE, fs=11, tc=INK, bold_first=True, lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.35,rounding_size=1.1',
                                facecolor=fc, edgecolor=ec, lw=lw, zorder=2))
    if isinstance(lines, str): lines = [lines]
    n = len(lines)
    # 줄 간격은 상자 높이에 맞춰 줄인다 — 고정 간격이면 줄이 많을 때 상자 밖으로 넘친다
    gap = min(4.2, (h - 2.2) / max(n - 1, 1))
    top = y + h / 2 + (n - 1) * gap / 2
    for i, t in enumerate(lines):
        ax.text(x + w / 2, top - i * gap, t, ha='center', va='center', zorder=3,
                fontsize=fs if i == 0 else fs - 1.5,
                color=tc if i == 0 else MUTED,
                fontweight='bold' if (i == 0 and bold_first) else 'normal')


def arrow(ax, p1, p2, color=MUTED, lw=1.6, style='-|>', label=None, lx=0, ly=0, dashed=False):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14,
                                 color=color, lw=lw, zorder=1,
                                 linestyle=(0, (4, 3)) if dashed else 'solid',
                                 shrinkA=2, shrinkB=2))
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly
        ax.text(mx, my, label, fontsize=9.5, color=color, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.25', fc=PAPER, ec='none'), zorder=4)


def table(ax, x, y, widths, rows, fs=10.5, rowh=5.2, head=True):
    """rows[0] 이 머리글. 왼쪽 정렬 표."""
    total = sum(widths)
    for r, row in enumerate(rows):
        yy = y - r * rowh
        if r == 0 and head:
            ax.add_patch(Rectangle((x, yy - rowh * 0.42), total, rowh * 0.84,
                                   facecolor=SOFT, edgecolor='none', zorder=1))
        elif r % 2 == 0:
            ax.add_patch(Rectangle((x, yy - rowh * 0.42), total, rowh * 0.84,
                                   facecolor='#FBF6EF', edgecolor='none', zorder=1))
        cx = x
        for c, cell in enumerate(row):
            ax.text(cx + 1.0, yy, cell, fontsize=fs, va='center', zorder=3,
                    color=INK if (r == 0 or c == 0) else BODY,
                    fontweight='bold' if r == 0 else 'normal')
            cx += widths[c]
        ax.plot([x, x + total], [yy - rowh * 0.42, yy - rowh * 0.42], color=LINE, lw=0.8, zorder=2)


def bullets(ax, x, y, items, fs=11.5, gap=5.0, color=BODY):
    for i, t in enumerate(items):
        # 앞이 공백으로 시작하면 앞 항목의 이어지는 줄로 보고 글머리표를 찍지 않는다
        cont = t.startswith(' ')
        if not cont:
            ax.text(x, y - i * gap, '·', fontsize=fs + 3, color=CAT1, va='center')
        ax.text(x + 1.6, y - i * gap, t.strip() if cont else t,
                fontsize=fs, color=MUTED if cont else color, va='center')


# ══════════════════════════════════════════════════════════ 1. 표지
f = plt.figure(figsize=(W, H)); f.patch.set_facecolor(PAPER)
ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')
ax.add_patch(Rectangle((0, 0), 1.6, 100, facecolor=CAT1, edgecolor='none'))
ax.text(8, 68, '곁 — 돌봄의 무게를 읽다', fontsize=17, color=CAT1, fontweight='bold')
ax.text(8, 58, '시스템 아키텍처와', fontsize=40, color=INK, fontweight='bold')
ax.text(8, 48, '모델 작동 원리', fontsize=40, color=INK, fontweight='bold')
ax.plot([8, 52], [42, 42], color=LINE, lw=2)
ax.text(8, 35, '발달장애인 보호자 돌봄부담 경량 진단 + 지도 기반 복지서비스 연계',
        fontsize=13, color=BODY)
ax.text(8, 30, '배포본 v1.0.0 · 7문항 다항 로지스틱 회귀 · 판정 불가 설계',
        fontsize=13, color=BODY)
box(ax, 8, 13, 40, 10,
    ['이 문서가 답하는 두 가지',
     '① 무엇이 어디서 계산하는가   ② 한 건이 어떤 순서로 처리되는가'],
    fc='#FBF1E8', ec=LINE, fs=12)
ax.text(58, 22, 'Pioneer 3 팀', fontsize=13, color=INK, fontweight='bold')
ax.text(58, 18, '2026-09-03  ·  https://p3.sumzip.com', fontsize=11, color=MUTED)
ax.text(58, 14, '근거: 실행 중인 서비스 실측 · test 602건 1회 평가', fontsize=10.5, color=MUTED)
pages.append(f)

# ══════════════════════════════════════════════════════════ 2. 아키텍처
f, ax = page('시스템 아키텍처 — 판정은 한 곳에서만 한다', '1 / 시스템 구성',
             '포트는 팀에 배정된 두 개(9503 · 9523)만 쓴다. 추론 서비스는 포트를 열지 않는다.')

box(ax, 6, 68, 26, 10, ['브라우저 (보호자)', '로그인 없음 · 별명만 · 2분 소요'], fc='#FFFFFF', fs=13)
box(ax, 6, 51, 26, 11, ['프론트엔드  :9503',
                        'Vue 3.4 · TypeScript · Vite · Pinia',
                        'Leaflet + OpenStreetMap (API 키 불필요)'], fs=13)
box(ax, 6, 33, 26, 11, ['백엔드  :9523',
                        'Node.js 20 · Express 4 · mysql2',
                        '★ 확률 계산 코드가 없다'], fs=13, ec=CAT1, lw=2.0)
box(ax, 6, 13, 26, 11, ['추론 서비스 (Python 3.11)',
                        'cb_burden.serve · scikit-learn',
                        '릴리스 models/ 를 읽는다'], fc='#FBF1E8', ec=CAT1, fs=13, lw=2.0)

arrow(ax, (19, 68), (19, 62.5), label='답변 7개', lx=-9)
arrow(ax, (19, 51), (19, 44.5), label='POST /api/v1/diagnoses', lx=-1, ly=0)
arrow(ax, (19, 33), (19, 24.5), color=CAT1, lw=2.2,
      label='유닉스 소켓  run/cb-inference.sock', lx=1)

box(ax, 40, 33, 24, 11, ['MariaDB 12.1.2',
                         '기관 1,283곳 · 설정 · 이벤트 로그',
                         '개인 식별 정보 컬럼 없음'], fs=13)
arrow(ax, (32, 38.5), (40, 38.5), style='<|-|>')

box(ax, 40, 51, 24, 11, ['nginx  ·  p3.sumzip.com',
                         'HTTP → HTTPS 리다이렉트'], fs=13)
arrow(ax, (32, 56.5), (40, 56.5), style='<|-|>')

box(ax, 71, 13, 24, 31,
    ['오프라인 학습 (배포 대상 아님)', '', 'snapshot  스냅샷 고정',
     'train     models/runs/ 에만 기록', 'evaluate  test 602건 · 단 1회',
     'promote   배포본 교체', '', 'Python + scikit-learn + pytest'],
    fc='#F5F1EA', ec=LINE, fs=12.5)
arrow(ax, (71, 22), (32, 19), color=MUTED, dashed=True, label='릴리스 승격으로만 바뀐다', ly=2.4)

ax.text(6, 8.5, '★ 백엔드에는 softmax·확률 계산 코드가 존재하지 않는다. 폴백 경로를 제거해 '
                '"두 경로가 서로 다른 답을 내는" 실패 양식을 구조적으로 없앴다.',
        fontsize=11.5, color=CAT1)
pages.append(f)

# ══════════════════════════════════════════════════════════ 3. 설계 결정
f, ax = page('아키텍처 설계 결정 네 가지 — 무엇을 얻고 무엇을 포기했나', '2 / 설계 근거',
             'FR·SC 는 명세(specs/001-care-burden-map/spec.md)의 요구사항·성공기준 번호다.')
table(ax, 5, 76, [22, 30, 24, 20], [
    ['결정', '이유', '포기한 것', '검증'],
    ['판정 경로 단일화', '두 구현이 갈리면 조용히 틀린 답이', '파이썬이 죽으면', '5각도 확인 —'],
    ['(TS 이식본 제거)', '나간다. 백엔드에서 계산 능력 자체를 뺐다', '판정이 안 나온다', '끄면 판정 불가'],
    ['유닉스 소켓', '팀 배정 포트가 2개뿐. 네트워크에', '원격 분리 배포', '건당 약 2ms'],
    ['(포트 미사용)', '노출되지 않아 외부에서 닿을 수 없다', '불가', 'CPU 시간 증가 확인'],
    ['기동 시 대조 게이트', '문항 집합·sklearn 버전이 어긋나면', '기동 실패로', '불일치 시'],
    ['', '조용히 틀린 판정이 나간다', '서비스 중단', '백엔드가 뜨지 않음'],
    ['개인정보 미보관', '저장 금지 항목은 컬럼 자체를 만들지', '재방문 이력·', '두 테이블 공통'],
    ['(원칙 III · FR-032)', '않는다. 로그인·계정 개념이 없다', '개인화', '컬럼 0개'],
], fs=10.5, rowh=4.6)

ax.text(5, 32, '실패해도 안전한 쪽으로 넘어진다', fontsize=15, color=INK, fontweight='bold')
box(ax, 5, 12, 42, 16,
    ['추론 서비스가 응답하지 않으면',
     '', '판정 = 없음 · 판정 불가 문구 표시',
     '그러나 기관 안내 3곳은 그대로 나간다 (FR-021j)',
     '기여 요인·참조 비교는 내지 않는다 (FR-011c)'],
    fc='#FBF1E8', ec=CAT1, fs=12.5, lw=1.8)
box(ax, 52, 12, 43, 16,
    ['응답 계약 검사',
     '', '추론 서비스의 응답 필드가 약속과 다르면',
     '판정으로 쓰지 않고 안내 경로로 넘긴다.',
     '2026-09-02 오전, 필드 불일치로 오류 없이 화면이',
     '비는 사고가 있었다 — 그 재발을 막는 장치다.'],
    fc='#FFFFFF', ec=LINE, fs=12.5)
pages.append(f)

# ══════════════════════════════════════════════════════════ 4. 모델 파이프라인
f, ax = page('모델 처리 — 한 건이 지나는 일곱 단계', '3 / 추론 파이프라인',
             '배포본 v1.0.0 · 다항 로지스틱 회귀 · 7문항 → 원-핫 53열 → 5구간 softmax')

STEPS = [
    ('①  결측 표현', '무응답을 -1 센티널로 (대치하지 않는다)'),
    ('②  원-핫 인코딩', '7문항 → 설계행렬 53열'),
    ('③  선형결합 + softmax', '계수 내적 → 5구간 확률'),
    ('④  희소성 계산', '각 응답의 학습 빈도에 log 를 씌워 평균'),
    ('⑤  판정 불가 판단', '확신도·희소성 두 문턱을 함께 본다'),
    ('⑥  구간 결정', '확률 × 결정 가중치 [1.1, 1.1, 1, 1, 1] 의 argmax'),
    ('⑦  기여 요인 분해', '해당 구간 기준 상위 3개 (Saabas)'),
]
y0 = 74
for i, (t, s) in enumerate(STEPS):
    yy = y0 - i * 8.6
    fc = '#FBF1E8' if i in (4, 5) else SOFT
    ec = CAT1 if i in (4, 5) else LINE
    box(ax, 5, yy, 46, 6.4, [f'{t}    {s}'], fc=fc, ec=ec, fs=11.5, bold_first=False)
    if i < len(STEPS) - 1:
        arrow(ax, (28, yy), (28, yy - 2.2), lw=1.2)

box(ax, 57, 60, 38, 20,
    ['입력  Input', '', '답변 7개  [4, 4, 5, 1, 없음, 3, 1]',
     '일과 만족 4 · 가족 지지 4 · 도움 시간 5',
     '가구주 1 · 퇴사 이유 없음 · 관계 3 · 일 이해 1'], fc='#FFFFFF', fs=12.5)
box(ax, 57, 33, 38, 24,
    ['처리  Process — 실제 값', '',
     '확률   [1.9, 20.8, 42.9, 28.8, 5.6] %',
     '최대확률  0.429   ≥ 0.32392  통과',
     '희소성   -1.138   ≥ -2.43427 통과',
     '가중치 적용 후 argmax → 내부 라벨 3'], fc='#FFFFFF', fs=12.5)
box(ax, 57, 10, 38, 20,
    ['출력  Output', '', '표시 명칭  "중간부담군"',
     '기여 요인  가족의 취업 지지 +0.242 …',
     '참조 비교 4개 · 기관 안내(고부담·판정 불가일 때)'], fc='#FBF1E8', ec=CAT1, fs=12.5)
arrow(ax, (76, 60), (76, 57.5)); arrow(ax, (76, 33), (76, 30.5))
pages.append(f)

# ══════════════════════════════════════════════════════════ 5. 왜 로지스틱
f, ax = page('왜 다항 로지스틱 회귀인가 — 성능이 아니라 성능이 같아서', '4 / 모델 선택',
             '전부 train 2,398건 · DB 에 물리 저장된 5-fold · test 602건 미사용 조건에서 측정')
table(ax, 5, 76, [30, 18, 18, 29], [
    ['비교', '규모', '결과', '함의'],
    ['단일 7종 + 앙상블 4종', '11구성 × 2문항셋', '로지스틱 1등', '문항 수와 무관하게 유지'],
    ['반복 CV + 부트스트랩 재측정', '9구성 · 2,000회', '이긴 구성 0개', '차이가 잡음과 같은 크기'],
    ['인코딩 6종', '순서형 처리 변경', '1종만 통과', '진행 중 · 배포본 미변경'],
], fs=11, rowh=5.4)

ax.text(5, 50, '기준선이 스스로 흔들리는 폭', fontsize=14, color=INK, fontweight='bold')
box(ax, 5, 30, 43, 17,
    ['반복별 macro F1   0.3388 · 0.3366 · 0.3388 · 0.3276 · 0.3320',
     '', '표준편차  0.0049',
     '쫓던 차이(0.006 ~ 0.014)가 기준선 자신이',
     '분할만 바꿔도 흔들리는 폭과 같은 크기였다.'], fc='#FBF1E8', ec=CAT1, fs=12.5, lw=1.8)

ax.text(52, 50, '선형 모델이 준 부수 효과', fontsize=14, color=INK, fontweight='bold')
bullets(ax, 53, 45, [
    '표본이 얇다 — 3,000건 · 5클래스 · 5등급은 61건뿐.',
    '   상호작용을 배우기엔 부족해 단순한 쪽이 덜 과적합한다.',
    '기여 요인이 근사가 아니라 정확히 분해된다.',
    '   "왜 이 판정인가" 를 산술적으로 닫힌 형태로 낸다.',
    '학습 0.2초 — 재현·재학습 비용이 사실상 없다.',
], fs=11.5, gap=4.6)

box(ax, 5, 10, 90, 15,
    ['정직하게 남기는 것',
     '',
     '실험 여섯 개(정규화 15조합 · 문항 14개 · 서열 모델 · 변수 38개 · 학습곡선 · 라벨 재정의)를 같은 조건에서 돌렸고',
     '다섯 폴드에서 95% 로 말하는 데 필요한 |t| ≥ 2.776 을 넘긴 실험은 하나도 없다.',
     '모델 쪽에서 넘을 수 있는 벽이 아니라는 뜻이며, 이는 배포본이 이 데이터의 한계에 근접해 있다는 근거이기도 하다.'],
    fc='#FFFFFF', ec=LINE, fs=11.5)
pages.append(f)

# ══════════════════════════════════════════════════════════ 6. 판정 불가
f, ax = page('판정 불가 — 모르는 것을 모른다고 말하는 설계', '5 / 핵심 설계',
             'test 602건 기준. 임계값은 models/uncertainty_v1.json 에서 읽는다(FR-009c).')
box(ax, 5, 62, 43, 17,
    ['두 개의 문턱을 함께 본다', '',
     '확신도  max p  <  0.32392   →  "확신 부족"',
     '희소성  rarity <  -2.43427  →  "드문 응답 조합"',
     '둘 중 하나만 걸려도 판정하지 않는다.'], fc='#FBF1E8', ec=CAT1, fs=12.5, lw=1.8)
box(ax, 52, 62, 43, 17,
    ['판정 불가여도 기관 안내는 나간다', '',
     'test 602건 중 판정 불가 15건 (2.49%)',
     '그 15명의 실제 부담은 최고 4 · 고 4 · 중간 4 · 저 2 · 없음 1',
     '→ 여덟 명이 실제 고부담이었다 (FR-021j 안전망)'], fc='#FFFFFF', ec=LINE, fs=12.5)

ax.text(5, 54, '문턱이 임의의 값이 아닌 근거 — 확신도가 오르면 실제 정확도도 오른다',
        fontsize=14, color=INK, fontweight='bold')
table(ax, 5, 47, [22, 16, 18], [
    ['확신도 구간', '건수', '정확도'],
    ['0.3 ~ 0.4', '80', '43.8 %'],
    ['0.4 ~ 0.5', '272', '45.6 %'],
    ['0.5 ~ 0.6', '191', '52.9 %'],
    ['0.6 ~ 0.7', '38', '57.9 %'],
    ['0.7 이상', '6', '66.7 %'],
], fs=11, rowh=5.0)

box(ax, 62, 14, 33, 30,
    ['희소성 조건이 실제로 하는 일', '',
     '무작위로 만든 응답 300건',
     '   → 63.0% 가 판정 불가',
     '',
     '실제 조사 응답 300건',
     '   → 2.0% 가 판정 불가',
     '',
     '실제 응답은 문항끼리 앞뒤가 맞는다.',
     '무작위 조합은 학습에서 본 적이 없다.'], fc='#F5F1EA', ec=LINE, fs=12)
ax.text(5, 11, '설계 의도 — 정확도 48%인 모델을 서비스로 쓸 수 있게 만든 것이 이 장치다. '
               '못 맞히는 응답자를 억지로 분류하는 대신 판정을 보류하고 상담·기관 안내로 넘긴다.',
        fontsize=11.5, color=CAT1)
pages.append(f)

# ══════════════════════════════════════════════════════════ 7. 성능과 한계
f, ax = page('성능과 한계 — 무엇을 할 수 있고 무엇을 못 하나', '6 / 평가',
             'test 602건은 모든 결정이 끝난 뒤 단 한 번만 사용했다(cv_fold 는 NULL).')
box(ax, 5, 58, 43, 21,
    ['할 수 있는 것 — 고부담 여부', '',
     '고부담 재현율      0.7730',
     '고부담 정밀도      0.695',
     '이진 정확도        0.696',
     '고부담을 "부담 없음" 으로 오판    0건'], fc='#FBF1E8', ec=CAT1, fs=13, lw=1.8)
box(ax, 52, 58, 43, 21,
    ['못 하는 것 — 5구간 정밀 판정', '',
     '5구간 정확도       48.7 %  (판정된 587건 기준)',
     'macro F1           0.3416',
     '"부담 없음" 16건    한 건도 못 맞힘',
     '한 칸 빗나감 41.4% · 두 칸 이상 9.9%'], fc='#FFFFFF', ec=LINE, fs=13)

ax.text(5, 50, '정확도가 낮은 이유를 데이터로 답했다', fontsize=14, color=INK, fontweight='bold')
table(ax, 5, 44, [34, 18, 38], [
    ['측정', '값', '읽는 법'],
    ['실루엣 계수 (최고 k=2)', '0.1233', '0.25 미만 — 뚜렷한 군집 구조가 없다'],
    ['ARI (군집 ↔ 부담 구간)', '0.027', '군집 축은 부담이 아니다'],
    ['PCA 제1주성분 설명력', '12.9 %', '데이터를 관통하는 축이 없다'],
    ['같은 7문항 응답 조합', '62.9 %', '고부담 여부에서조차 라벨이 갈린다'],
    ['변수를 38개로 늘리면', '0.3141', '기준 0.3364보다 내려간다'],
], fs=11, rowh=5.0)

ax.text(5, 11.5, '주의 — 실루엣 계수는 "잘 뭉쳤는가" 를 잴 뿐 "의미 있게 나뉘었는가" 는 재지 못한다. '
                 '군집 프로파일은 발견된 유형이지 검증된 유형이 아니다.', fontsize=11.5, color=MUTED)
ax.text(5, 7.5, '그리고 이 연구는 인과 설명(Causal Explanation)을 하지 않았다. '
                '1회 횡단면 조사로는 "왜 부담이 생기는가" 에 답할 수 없다.', fontsize=11.5, color=PLUM)
pages.append(f)

# ══════════════════════════════════════════════════════════ 8. 재현성
f, ax = page('재현성과 무결성 — 같은 답이 다시 나오는가', '7 / 운영',
             '모델만 저장하면 배포처에서 전처리를 손으로 재현해야 하고, 조금만 달라도 성능이 조용히 무너진다.')
table(ax, 5, 76, [26, 36, 32], [
    ['항목', '무엇을 고정했나', '어긋나면'],
    ['난수', 'SEED = 20260901 (계획서의 42 를 실측으로 정정)', '같은 데이터에서 다른 모델'],
    ['분할', 'split · cv_fold 를 DB 컬럼에 물리 저장', '이전 실험과 비교 불가'],
    ['행 순서', 'row_key = 행 내용 MD5 로 고정', '분할이 재현되지 않음'],
    ['라이브러리', '기동 시 sklearn 버전 대조', '백엔드가 뜨지 않는다'],
    ['문항 집합', '기동 시 백엔드 ↔ 추론 대조', '백엔드가 뜨지 않는다'],
    ['전처리', '전처리와 모델을 한 릴리스로 묶어 promote', '배포처 재현 불일치'],
], fs=11, rowh=5.0)

ax.text(5, 36, '"고쳤다" 와 "그 코드가 돌고 있다" 는 다른 말이다', fontsize=14,
        color=INK, fontweight='bold')
bullets(ax, 6, 33, [
    '백엔드에 확률 계산 코드가 존재하지 않음을 코드 전수로 확인',
    '추론 서비스를 중지하면 판정이 나오지 않고, 되살리면 다시 나온다',
    '요청마다 파이썬 프로세스의 CPU 시간이 증가한다 (건당 약 2ms)',
    '파이썬이 읽는 릴리스 파일만 바꾸자 공개 사이트의 답이 바뀌었고, 되돌리자 복귀했다',
], fs=11.5, gap=4.6)

box(ax, 5, 6.5, 90, 10,
    ['활용 — 데이터로 시작해 데이터로 답한다',
     '의사결정 대안 : 고부담이면 추가 조작 없이 가까운 접수처 3곳을 제시한다',
     '시스템 모듈   : 전처리 + 모델을 하나의 릴리스로 묶어 API 뒤에 두었다 · 골든 3,000건 패리티 · pytest 75건'],
    fc='#FBF1E8', ec=CAT1, fs=12, lw=1.8)
pages.append(f)

# ══════════════════════════════════════════════════════════ 저장
dst = ROOT / 'docs/JSG-아키텍처와-모델설명-발표용.pdf'
with PdfPages(dst) as pdf:
    for i, f in enumerate(pages, 1):
        pdf.savefig(f, facecolor=PAPER)
        f.savefig(PREV / f'p{i}.png', dpi=110, facecolor=PAPER)
        plt.close(f)
print(f'{len(pages)}쪽 → {dst}')
