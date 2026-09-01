# -*- coding: utf-8 -*-
"""docs/발표자료.md 의 내용을 .pptx 로 만든다. 디자인은 편지 톤(살구빛)에 맞춘다."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

# 편지 톤 팔레트
INK   = RGBColor(0x2B, 0x27, 0x24)
BODY  = RGBColor(0x4A, 0x44, 0x3E)
MUTED = RGBColor(0x8A, 0x81, 0x76)
ACCENT= RGBColor(0xC9, 0x6F, 0x4A)     # 살구빛
PAPER = RGBColor(0xFD, 0xF9, 0xF4)
LINE  = RGBColor(0xE4, 0xDA, 0xCC)
FONT  = 'Apple SD Gothic Neo'

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
W, H = prs.slide_width, prs.slide_height


def bg(slide, color=PAPER):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def tb(slide, x, y, w, h, text, size=18, bold=False, color=BODY,
       align=PP_ALIGN.LEFT, space=8, line=1.35):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        p.line_spacing = line
        r = p.add_run(); r.text = ln
        f = r.font; f.name = FONT; f.size = Pt(size); f.bold = bold; f.color.rgb = color
    return box


def rule(slide, x, y, w, color=LINE, pt=1.2):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Pt(pt))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background(); s.shadow.inherit = False
    return s


def header(slide, num, title, sub=None):
    tb(slide, 0.9, 0.55, 1.0, 0.4, num, size=13, bold=True, color=ACCENT)
    tb(slide, 0.9, 0.92, 11.5, 0.8, title, size=30, bold=True, color=INK)
    rule(slide, 0.9, 1.78, 11.5)
    if sub:
        tb(slide, 0.9, 1.95, 11.5, 0.5, sub, size=14, color=MUTED)


def blank():
    s = prs.slides.add_slide(prs.slide_layouts[6]); bg(s); return s


def pic(slide, name, x, y, w=None, h=None):
    """docs/assets 의 차트를 넣는다. w 만 주면 비율 유지."""
    path = str(ROOT / 'docs' / 'assets' / name)
    if h is None:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    if w is None:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), height=Inches(h))
    return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))


def table(slide, x, y, rows, widths, size=13, head=True, w_total=11.5):
    """간단한 표 — 헤더 굵게, 행 사이 얇은 선."""
    cy = y
    for ri, row in enumerate(rows):
        cx = x
        for ci, cell in enumerate(row):
            wcol = widths[ci]
            tb(slide, cx, cy, wcol, 0.32, str(cell),
               size=size, bold=(head and ri == 0),
               color=INK if (head and ri == 0) else BODY, space=0)
            cx += wcol
        cy += 0.36
        if head and ri == 0:
            rule(slide, x, cy - 0.06, w_total, LINE, 1.0)
    return cy


# ─────────────────────────────────── 표지
s = blank()
rule(s, 0.9, 2.55, 2.2, ACCENT, 3)
tb(s, 0.9, 2.75, 11.5, 1.2, '곁 — 돌봄의 무게를 읽다', size=46, bold=True, color=INK)
tb(s, 0.9, 3.95, 11.5, 0.8,
   '발달장애인 보호자 돌봄부담 경량 진단 및 복지서비스 연계', size=20, color=BODY)
tb(s, 0.9, 5.6, 11.5, 0.9,
   'Pioneer 3 팀   ·   2026-09-01   ·   https://p3.sumzip.com', size=14, color=MUTED)

# ─────────────────────────────────── 1. 왜
s = blank(); header(s, '01', '왜 만들었나')
tb(s, 0.9, 2.35, 11.5, 1.4,
   '발달장애인 보호자의 돌봄부담은 본인도 자기 상태를 객관적으로 보기 어렵다.\n'
   '"다들 이 정도는 하고 산다"고 여기며 버티다 한계에 다다르는 경우가 많다.',
   size=19, color=BODY)
tb(s, 0.9, 3.5, 11.5, 0.6,
   '그런데 지원 제도는 본인이 찾아와 신청해야 작동한다.', size=19, color=BODY)
tb(s, 0.9, 4.05, 11.5, 0.6,
   '부담이 클수록 알아볼 여력이 없다는 역설이 있다.', size=21, bold=True, color=ACCENT)
rule(s, 0.9, 4.9, 11.5)
table(s, 0.9, 5.15, [
    ['짧은 설문으로', '지금의 돌봄부담이 어느 수준인지 가늠할 근거를 준다'],
    ['판단 근거를 함께', '"왜 그렇게 봤는지"를 응답으로 되짚어 준다'],
    ['즉시 연결', '부담이 크면 추가 조작 없이 가까운 접수처 3곳을 보여준다'],
], [2.6, 8.9], size=15, head=False)

# ─────────────────────────────────── 2. 데이터 (A)
s = blank(); header(s, '02', '데이터 — 2024 발달장애인 일과 삶 실태조사',
                    '전국 대표 표본 3,000가구 · 정제 후 설명변수 38개 · train 2,398 / test 602')
pic(s, 'A-부담분포.png', 0.9, 2.5, w=11.5)
tb(s, 0.9, 5.4, 11.5, 1.4,
   '고부담(1~2단계)이 1,629가구, 절반을 넘는다. 반대로 "부담 없음"은 77건뿐이다.',
   size=19, bold=True, color=INK)
tb(s, 0.9, 6.1, 11.5, 1.0,
   '돌봄부담은 예외가 아니라 기본값에 가깝다.\n'
   '척도 주의 — 숫자가 작을수록 부담이 크다. 서비스는 표시 명칭으로만 노출한다.',
   size=14, color=MUTED)

# ─────────────────────────────────── 3. Leakage (D)
s = blank(); header(s, '03', '정답이 새는 변수 6개를 일부러 버렸다',
                    '예측 대상(I13)과 같은 블록이거나 같은 것을 재는 변수')
pic(s, 'D-설명력순위.png', 0.7, 2.15, h=4.55)
tb(s, 7.9, 2.6, 4.7, 3.4,
   '버린 것 중 1위\n보호자 삶 만족도 19.06%\n\n'
   '남은 38개 중 최고(8.23%)의\n2.3배다.\n\n'
   '넣으면 성적은 오른다.\n그런데 "보호자 만족도로\n보호자 부담을 예측"하는 것은\n동어반복이다.',
   size=15, color=BODY, line=1.4)
tb(s, 7.9, 6.15, 4.7, 0.8,
   '성능을 포기하고\n도구로서의 의미를 택했다.', size=17, bold=True, color=ACCENT)

# ─────────────────────────────────── 4. 군집화 (E)
s = blank(); header(s, '04', '분석 결과 — 정확도 48%는 모델 탓이 아니다',
                    '정답(y)을 빼고 38개 설명변수만으로 군집을 찾아본 결과')
pic(s, 'E-군집화.png', 0.9, 2.35, w=11.5)
tb(s, 0.9, 6.05, 11.5, 1.2,
   '설명변수가 돌봄부담을 5구간으로 가를 만큼의 정보를 담고 있지 않다. 알고리즘을 바꿔도 오르지 않는다.\n'
   '그리고 자연스럽게 나뉘는 수는 2다 — 이 서비스가 답해야 하는 질문도 "고부담이냐 아니냐"다.',
   size=15, bold=True, color=INK)

# ─────────────────────────────────── 5. 계열 비교
s = blank(); header(s, '05', '모델 계열 비교 — 세 후보를 같은 조건에서',
                    '38변수 전체 · 같은 5-fold · 같은 지표')
table(s, 0.9, 2.6, [
    ['계열', 'macro F1', '고부담 재현율', ''],
    ['다항 로지스틱 회귀', '0.3180', '0.7636', '채택'],
    ['랜덤 포레스트', '0.2894', '0.7552', ''],
    ['엑스트라 트리', '0.2668', '0.7544', ''],
], [4.0, 2.2, 2.6, 1.6], size=16)
rule(s, 0.9, 4.2, 11.5)
tb(s, 0.9, 4.45, 11.5, 1.2,
   '트리 계열이 진 이유는 데이터 규모에 있다. 3,000건에 5개 클래스, 그중 "부담 없음"은 61건뿐이다.\n'
   '상호작용을 배우기엔 표본이 얇아 단순한 모델이 과적합을 덜 한다.', size=16, color=BODY)
tb(s, 0.9, 5.7, 11.5, 1.0,
   '부수 효과가 컸다 — 로지스틱에서는 기여 요인이 근사가 아니라 정확히 분해된다.\n'
   '"왜 이 판정인가"를 산술적으로 닫힌 형태로 설명할 수 있다.',
   size=16, bold=True, color=ACCENT)

# ─────────────────────────────────── 6. 문항 선정 기준 (C)
s = blank(); header(s, '06', '설문 문항을 7개로 정한 기준',
                    '단독 설명력 순위로 자르지 않았다 — 변수 간 중복을 반영하지 못하기 때문')
tb(s, 0.9, 2.3, 4.3, 3.4,
   '후진 제거\n\n'
   '1  38개 전체로 기준 모델\n'
   '2  덜 기여하는 변수를 하나씩 제거\n'
   '3  뺄 때마다 5-fold 로 측정\n'
   '4  아래를 깨는 순간 정지\n'
   '        F1 손실 ≤ 0.03\n'
   '        재현율 손실 ≤ 0.05\n'
   '        재현율 ≥ 0.70\n'
   '5  최소 집합 채택',
   size=14, color=BODY, space=3)
pic(s, 'C-문항수곡선.png', 5.3, 2.15, w=7.4)
tb(s, 0.9, 6.1, 11.5, 0.8,
   '성능 손실 허용치를 먼저 정하고 문항 수를 결과로 얻었다. "30문항으로 하자" 같은 사전 결정을 하지 않았다.',
   size=16, bold=True, color=ACCENT)

# ─────────────────────────────────── 6-2. 혼동행렬 근거 (B)
s = blank(); header(s, '06', '기준이 옳았는가 — 혼동행렬로 확인',
                    '선정 기준은 정지 조건이지만, 그 조건이 옳았음을 보여주는 것은 혼동행렬이다')
pic(s, 'B-혼동행렬2x2.png', 0.9, 2.25, w=11.5)
tb(s, 0.9, 5.5, 11.5, 1.6,
   '38 → 7: 31개를 버렸는데 오류 구조가 그대로다. 재현율은 오히려 0.764 → 0.784 로 올랐다.\n'
   '그런데 2×2 로만 보면 6문항도 멀쩡해 보인다 — 재현율 0.785 로 더 높다.',
   size=16, color=BODY)
tb(s, 0.9, 6.55, 11.5, 0.6,
   '왜 6에서 멈췄는지는 5구간으로 봐야 드러난다. →', size=17, bold=True, color=ACCENT)

# ─────────────────────────────────── 6-3. 5x5 대비
s = blank(); header(s, '06', '6문항은 최고부담군을 거의 못 찍는다',
                    '2×2 로는 같아 보이지만 5구간으로 보면 다르다 · 교차검증 2,398건')
pic(s, 'B-혼동행렬5x5.png', 0.75, 2.2, w=11.85)
tb(s, 0.9, 6.25, 11.5, 1.0,
   '최고부담군 재현율 0.183 → 0.054.  예측 건수 147 → 44.\n'
   '전체 정확도는 0.463 → 0.458 로 거의 같은데, 가장 도움이 절실한 구간을 가려내는 능력만 사라진다.',
   size=15.5, bold=True, color=INK)

# ─────────────────────────────────── 7. 7문항
s = blank(); header(s, '07', '채택된 7문항')
table(s, 0.9, 2.4, [
    ['#', '원 문항', '질문', '단독 설명력'],
    ['1', 'G8', '당사자는 요즘 하루하루의 일과를 어떻게 느끼고 있나요?', '3.51%'],
    ['2', 'F5', '당사자의 취업에 대해 가족들이 어느 정도 지지하고 있나요?', '3.94%'],
    ['3', 'G6', '하루 중 어느 정도의 도움이 필요한가요?', '8.23%'],
    ['4', 'I4', '가구의 생계를 주로 책임지는 분은 누구인가요?', '1.67%'],
    ['5', 'E4', '마지막 일자리를 그만둔 가장 큰 이유는?', '1.15%'],
    ['6', 'A1', '응답하시는 분은 당사자와 어떤 관계인가요?', '1.18%'],
    ['7', 'F1', '"일을 한다"는 것의 의미를 어느 정도 이해하나요?', '7.98%'],
], [0.6, 1.4, 7.5, 2.0], size=14)
rule(s, 0.9, 5.5, 11.5)
tb(s, 0.9, 5.7, 11.5, 1.2,
   '단독 1·2위(G6·F1)는 살아남았지만 3위(통상근로 가능 여부)는 탈락했다.\n'
   'F1(근로 의미 이해도)과 정보가 겹쳤기 때문이다 — 후진 제거가 중복을 걸러낸 결과다.',
   size=16, color=BODY)

# ─────────────────────────────────── 8. 14문항 실험 (F)
s = blank(); header(s, '08', '문항을 14개로 늘려 봤다가 되돌렸다',
                    '7문항으로 "고부담군입니다"라고 하면 신뢰하기 어렵다는 판단에서 출발했다')
pic(s, 'F-판정불가비교.png', 0.9, 2.3, w=11.5)
rule(s, 0.9, 6.1, 11.5)
tb(s, 0.9, 6.3, 6.6, 1.0,
   '원인은 나이 변수다. 보호자 나이는 한 살 단위 78개 범주라\n'
   '"57세"는 학습 데이터의 1.3%뿐 — 희소한 조합으로 분류되어 판정 불가가 된다.',
   size=13.5, color=BODY)
tb(s, 7.8, 6.3, 4.6, 1.0,
   '응답 부담은 늘리고, 결과를 못 받는 사람도 늘렸으며,\n정확도는 얻지 못했다 → 7문항 복귀',
   size=14, bold=True, color=ACCENT)

# ─────────────────────────────────── 9. 성능
s = blank(); header(s, '09', '성능 — 무엇을 할 수 있고 무엇을 못 하나')
tb(s, 0.9, 2.4, 5.5, 0.5, '5구간은 정확히 못 맞힌다', size=19, bold=True, color=MUTED)
tb(s, 0.9, 2.95, 5.5, 1.4,
   '정확도 47.8%\n(무작위 20% · 최빈값 38.7%)\n\n"부담 없음" 16건은 하나도 못 맞혔다',
   size=16, color=BODY)
rule(s, 6.7, 2.4, 0.02)
tb(s, 7.1, 2.4, 5.3, 0.5, '고부담 여부는 가려낸다', size=19, bold=True, color=ACCENT)
table(s, 7.1, 2.95, [
    ['재현율', '0.773'],
    ['정밀도', '0.695'],
    ['정확도', '0.696'],
], [2.2, 2.0], size=17, head=False, w_total=4.2)
rule(s, 0.9, 4.7, 11.5)
tb(s, 0.9, 4.95, 11.5, 1.0,
   '실제 고부담 보호자의 77.3%를 잡아낸다.\n'
   '그리고 고부담인 사람을 "부담 없음"으로 판정한 경우는 test 602건 중 0건이다.',
   size=18, bold=True, color=INK)
tb(s, 0.9, 6.05, 11.5, 1.0,
   '설계로 만든 결과다 — 판정 시 1·2단계 확률에 1.1배를 곱한다.\n'
   '이 값은 사람이 고른 것이 아니라 "재현율 0.73 이상 중 macro F1 최대" 규칙이 자동으로 찾았다.',
   size=15, color=MUTED)

# ─────────────────────────────────── 10. 돌봄 서비스 + 대전 지도
s = blank(); header(s, '10', '우리나라 발달장애인 돌봄 서비스',
                    '기관 데이터에 실제로 존재하는 두 제도만 안내한다')
table(s, 0.9, 2.4, [
    ['제도', '대상', '기관', '시군구'],
    ['발달장애인 주간활동서비스', '만 18~64세', '724', '217'],
    ['청소년 방과후활동서비스', '만 6~17세', '553', '196'],
], [3.5, 1.9, 1.0, 1.2], size=13, w_total=7.6)
tb(s, 0.9, 3.75, 7.4, 1.5,
   '주간활동 — 성인 발달장애인이 낮 시간에 지역사회에서 활동하도록 지원한다.\n'
   '보호자에게는 낮 시간의 돌봄 공백을 메워 주는 거의 유일한 제도다.\n\n'
   '방과후활동 — 학교가 끝난 뒤부터 보호자 퇴근까지의 공백을 다룬다.',
   size=13.5, color=BODY)
rule(s, 0.9, 5.35, 7.4)
tb(s, 0.9, 5.55, 7.4, 1.6,
   '전국 229개 시군구 중 221개 확보 (96.5%)\n'
   '미확보 8개는 "정보 준비 중 + 광역 문의처"로 안내\n\n'
   '대전은 34곳 — 중구 8 · 유성구 8 · 동구 7 · 서구 6 · 대덕구 5\n'
   '이 중 26곳이 두 유형을 모두 제공한다',
   size=13.5, color=BODY)
pic(s, 'H-대전지도.png', 8.55, 1.95, h=5.2)

# ─────────────────────────────────── 11. 사각지대 (G)
s = blank(); header(s, '11', '제도의 사각지대')
pic(s, 'G-사각지대.png', 0.9, 2.2, w=11.5)
tb(s, 0.9, 5.9, 11.5, 1.3,
   '만 65세 이상 발달장애인은 제도의 틈에 놓인다 — 장애인 서비스에서는 나이가 많고,\n'
   '노인 서비스에서는 발달장애 특성이 고려되지 않는다.',
   size=17, bold=True, color=ACCENT)
tb(s, 0.9, 6.85, 11.5, 0.6,
   '이 서비스의 목적이 사각지대 발굴이므로 화면에서 배제하지 않는다. 연령 매핑은 자격 판정이 아니다.',
   size=14, color=MUTED)

# ─────────────────────────────────── 12. 의미
s = blank(); header(s, '12', '설문으로 돌봄부담을 진단하는 의미',
                    '정확한 진단이 아니라 "말 걸기"다')
table(s, 0.9, 2.6, [
    ['하는 것', '하지 않는 것'],
    ['지금 상태를 가늠할 근거를 준다', '공식 자격을 판정한다'],
    ['"왜 그렇게 봤는지"를 응답으로 되짚어 준다', '확신을 준다'],
    ['부담이 크면 기관으로 연결한다', '서비스 신청을 대신한다'],
    ['모를 때는 모른다고 한다', '억지로 답을 낸다'],
], [6.4, 5.1], size=16)
rule(s, 0.9, 4.9, 11.5)
tb(s, 0.9, 5.15, 3.6, 1.8,
   '① 객관화의 계기\n"다들 이 정도"라고 여기던 것이\n전국 3,000가구 분포에서\n어디쯤인지 보인다.', size=14, color=BODY)
tb(s, 4.9, 5.15, 3.6, 1.8,
   '② 제도로 가는 최단 경로\n고부담이면 추가 조작 없이\n접수처 3곳이 바로 나온다.', size=14, color=BODY)
tb(s, 8.9, 5.15, 3.5, 1.8,
   '③ 2분 안에 끝난다\n부담이 큰 사람이 끝까지\n갈 수 있는 분량이어야\n의미가 있다.', size=14, color=BODY)

# ─────────────────────────────────── 13. 개인정보
s = blank(); header(s, '13', '개인정보를 받지 않는 설계',
                    '돌봄부담은 가족의 건강·장애·경제 상황이 얽힌 민감정보다')
table(s, 0.9, 2.6, [
    ['원칙', '구현'],
    ['로그인 없음', '계정 개념 자체가 없다'],
    ['이름·연락처 없음', '별명만 받고 서버로 보내지 않는다'],
    ['IP 미보관', '중복 판별용 해시만 만들고 원본은 버린다'],
    ['위치 미보관', '기관 찾기에만 쓰고 저장하지 않는다'],
    ['학습 이용은 동의제', '거부해도 진단·연계는 똑같이 제공한다'],
], [3.6, 7.9], size=16)
rule(s, 0.9, 5.3, 11.5)
tb(s, 0.9, 5.55, 11.5, 1.2,
   '저장 금지 항목은 문서에 적는 대신 컬럼 자체를 만들지 않았다.\n'
   '참조 집단 비교도 표본 30건 미만 셀은 DB 제약(CHECK n >= 30)으로 적재를 막았다.',
   size=17, bold=True, color=ACCENT)

# ─────────────────────────────────── 14. 한계
s = blank(); header(s, '14', '정직하게 남기는 한계')
table(s, 0.9, 2.5, [
    ['한계', '대응'],
    ['5구간 정확도 48%', '등급이 아니라 "고부담 여부"로 읽도록 설계'],
    ['설명변수가 5구간을 가를 정보를 못 담음', '알고리즘 문제가 아님을 군집화로 실측 확인'],
    ['최상위 설명변수를 일부러 배제', '성능보다 도구의 의미를 택한 결정. 되돌리지 않음'],
    ['자발적 이용자는 전국 대표 표본이 아님', '학습 데이터를 대체하지 않고 보완으로만 사용'],
    ['8개 시군구 데이터 미확보', '"준비 중 + 광역 문의처"로 처리'],
    ['확률 보정 미구현', '계획에 있으나 코드는 임계값 탐색만 — 미확인 항목'],
], [5.6, 5.9], size=15)

# ─────────────────────────────────── 15. 요약
s = blank(); header(s, '15', '요약')
rows = [
    ('데이터', '전국 3,000가구. 고부담이 54.3%. 정답이 새는 변수 6개를 성능을 포기하고 배제'),
    ('분석', '군집 구조 없음 — 정확도 48%는 모델이 아니라 데이터의 성질. 나뉘는 수는 2'),
    ('문항', '성능 손실 허용치를 먼저 정하고 후진 제거로 7문항. 14개로 늘렸다가 되돌림'),
    ('성능', '5구간은 못 맞히지만 고부담 여부는 재현율 0.773. 고부담→"부담없음" 오판 0건'),
    ('연계', '주간활동 724곳 · 방과후 553곳. 229개 중 221개 커버. 65세 이상도 배제 안 함'),
    ('의미', '등급을 매기는 도구가 아니라 자기 상태를 가늠하고 제도로 가는 최단 경로'),
]
y = 2.5
for k, v in rows:
    tb(s, 0.9, y, 1.6, 0.4, k, size=17, bold=True, color=ACCENT)
    tb(s, 2.6, y, 9.8, 0.7, v, size=15, color=BODY)
    y += 0.75

out = ROOT / 'docs' / '발표자료.pptx'
prs.save(str(out))
print('생성 완료:', out, '·', len(prs.slides.__iter__.__self__._sldIdLst), '슬라이드')
