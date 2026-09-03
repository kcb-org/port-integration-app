import streamlit as st
import pandas as pd
import math
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64
import re
import urllib.parse
import concurrent.futures
import textwrap

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보, 이종태]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")


# =====================================================================
# ★ 1. 한글 폰트 설정
# =====================================================================
@st.cache_resource
def set_korean_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception:
            pass
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rc('font', family='NanumGothic')
    plt.rcParams['axes.unicode_minus'] = False


set_korean_font()


# =====================================================================
# ★ 2. 보고서 생성기 (HTML & LaTeX 통합)
# =====================================================================
class ReportBuilder:
    def __init__(self):
        self.html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>블록식 안벽 상세 구조계산서</title>
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script>
          MathJax = { tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], processEscapes: true } };
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body { font-family: 'Malgun Gothic', 'NanumGothic', sans-serif; line-height: 1.6; padding: 20px; color: #333; max-width: 1200px; margin: auto; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 25px; font-size: 13px; background: white; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background-color: #f4f6f8; font-weight: bold; color: #2c3e50;}
            h1 { color: #2c3e50; text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 10px;}
            h2 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 50px; font-size: 1.5em; background-color: #e8f0fe; padding-left: 10px;}
            h3 { color: #e67e22; margin-top: 25px; font-size: 1.2em;}
            .eq { background: #fdfefe; padding: 15px; border-left: 4px solid #1a73e8; margin: 15px 0; overflow-x: auto; font-size: 1.1em; border: 1px solid #e0e0e0;}
            .desc { background-color: #fbfcfc; padding: 10px; margin-bottom: 15px; border-radius: 5px; font-size: 1em;}
            .fig-container { text-align: center; margin: 20px 0; padding: 15px; background: #fff; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        </style>
        </head><body class="tex2jax_process">
        """

    def title(self, text, level=2):
        self.html += f"<h{level}>{text}</h{level}>"

    def md(self, text):
        html_out = f"<div class='desc'>"
        for line in text.split('\n'):
            if not line.strip(): continue
            line = line.replace('**', '<b>').replace('**', '</b>')
            html_out += f"<p>{line}</p>"
        html_out += "</div>"
        self.html += html_out

    def latex(self, eq):
        self.html += f"<div class='eq'>$$ {eq} $$</div>"

    def table(self, dataframe, styled=None):
        html_table = styled.to_html(justify='center') if styled is not None else dataframe.to_html(index=False,
                                                                                                   justify='center',
                                                                                                   escape=False)
        self.html += html_table.replace('\\n', '<br>')

    def html_raw(self, raw_html):
        self.html += raw_html

    def get_html(self):
        return self.html + "</body></html>"

    def get_mhtml(self):
        word_html = self.get_html()
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 25px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f4f6f8; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

        def image_replacer(match):
            b64_data = match.group(1)
            counters['img'] += 1
            img_id = f"embedded_img_{counters['img']}"
            attachments[img_id] = b64_data
            return f'<img src="cid:{img_id}" width="750" style="max-width: 100%;">'
        
        word_html = re.sub(r'src=["\']data:image/[a-zA-Z]+;base64,([^\'"]+)["\']', image_replacer, word_html)

        display_maths = re.findall(r'\$\$(.*?)\$\$', word_html, flags=re.DOTALL)
        inline_maths = re.findall(r'\$([^\$]+)\$', word_html)
        urls_to_fetch = set()
        
        def prepare_url(eq_text, is_display):
            eq_c = re.sub(r'\\text\{([^}]+)\}', lambda m: "" if re.search(r'[가-힣]', m.group(1)) else m.group(0), eq_text)
            eq_c = eq_c.replace(r'\max', 'max').replace(r'\min', 'min').replace(r'\mathbf', '')
            dpi = "110" if is_display else "100"
            return f"https://latex.codecogs.com/png.image?\\dpi{{{dpi}}}\\bg_white&space;{urllib.parse.quote(eq_c)}"
        
        for eq in display_maths: urls_to_fetch.add(prepare_url(eq.strip(), True))
        for eq in inline_maths:
            txt = eq.strip()
            if any(op in txt for op in ["\\", "=", "+", "-", "/", "times", "ge", "le", "<", ">", "^", "_"]):
                urls_to_fetch.add(prepare_url(txt, False))
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(fetch_equation_image, urls_to_fetch))

        def render_math_to_img(eq_text, is_display):
            korean_parts = []
            def kr_replacer(m):
                txt = m.group(1)
                if re.search(r'[가-힣]', txt):
                    korean_parts.append(txt)
                    return ""
                return m.group(0)
            eq_c = re.sub(r'\\text\{([^}]+)\}', kr_replacer, eq_text)
            eq_c = eq_c.replace(r'\max', 'max').replace(r'\min', 'min').replace(r'\mathbf', '')
            
            api_url = prepare_url(eq_text, is_display)
            counters['eq'] += 1
            img_id = f"eq_img_{counters['eq']}"
            b64_img = fetch_equation_image(api_url)
            
            if b64_img:
                attachments[img_id] = b64_img
                img_tag = f"<img src='cid:{img_id}' style='vertical-align: middle; border: none; max-width: 100%;'>"
            else:
                img_tag = f"<img src='{api_url}' style='vertical-align: middle; border: none; max-width: 100%;'>"
            
            kr_addon = f"<span style='margin-left:5px; font-weight:bold; color:#555;'>[{' '.join(korean_parts)}]</span>" if korean_parts else ""
            return img_tag, kr_addon

        def display_math_replacer(match):
            img_tag, kr_addon = render_math_to_img(match.group(1).strip(), True)
            return f'<table align="center" style="border-collapse: collapse; border: none; margin: 10px auto; width: 100%;"><tr><td style="border: none; padding: 0; text-align: center;">{img_tag} {kr_addon}</td></tr></table>'
        word_html = re.sub(r'\$\$(.*?)\$\$', display_math_replacer, word_html, flags=re.DOTALL)

        def inline_math_replacer(match):
            eq_text = match.group(1).strip()
            if any(op in eq_text for op in ["\\", "=", "+", "-", "/", "times", "ge", "le", "<", ">", "^", "_"]):
                img_tag, kr_addon = render_math_to_img(eq_text, False)
                return f"{img_tag}{kr_addon}"
            else:
                return f"${eq_text}$"
        word_html = re.sub(r'\$([^\$]+)\$', inline_math_replacer, word_html)
        word_html = re.sub(r'\$([a-zA-Z]+)_([a-zA-Z0-9\+\-]+)\$', r'\1<sub>\2</sub>', word_html)
        word_html = word_html.replace('$', '')

        boundary = "----=_NextPart_HTML_DOC_001"
        mhtml = f'MIME-Version: 1.0\nContent-Type: multipart/related; type="text/html"; boundary="{boundary}"\n\n'
        mhtml += f'--{boundary}\nContent-Type: text/html; charset="utf-8"\nContent-Transfer-Encoding: 8bit\n\n'
        mhtml += word_html + "\n\n"
        
        for cid, b64 in attachments.items():
            formatted_b64 = '\n'.join(textwrap.wrap(b64, 76))
            mhtml += f'--{boundary}\nContent-Type: image/png\nContent-Transfer-Encoding: base64\nContent-ID: <{cid}>\n\n{formatted_b64}\n\n'
        mhtml += f"--{boundary}--\n"
        return mhtml

# =====================================================================
# ★ 초고속 수식 이미지 다운로드 캐시 (MS Word 변환용)
# =====================================================================
@st.cache_data(show_spinner=False)
def fetch_equation_image(api_url):
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return base64.b64encode(response.read()).decode('utf-8')
    except Exception:
        return None

# =====================================================================
# ★ 3. 하중 모식도 시각화 함수
# =====================================================================

def draw_schematic(tiers_df, c_top, hwl_n, rwl_n, llw):
    fig, ax = plt.subplots(figsize=(10, 8))
    current_y = c_top
    max_b = 0.0

    valid_tiers = []
    for idx, row in tiers_df.iterrows():
        name_val = row.get("구분", None)
        if pd.isna(name_val) or str(name_val).strip().lower() in ["none", "nan", ""]:
            continue
        try:
            h_val = float(row["높이 H(m)"])
            b_val = float(row["폭 B(m)"])
            if pd.isna(h_val) or pd.isna(b_val):
                continue
        except Exception:
            continue
        valid_tiers.append(row)

    if not valid_tiers:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return f"<div class='fig-container'><img src='data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}' style='max-width:100%; height:auto;'></div>"

    # 1. 제체 블록 그리기 및 각 단별 후단 X좌표/단면 정보 수집
    tier_geoms = []

    for idx, row in enumerate(valid_tiers):
        name = str(row["구분"])
        h = float(row["높이 H(m)"])
        b = float(row["폭 B(m)"])

        top_b = float(row.get("상단폭(m)", b)) if pd.notna(row.get("상단폭(m)")) else b
        out_h = float(row.get("전면돌출(m)", 0.0)) if pd.notna(row.get("전면돌출(m)")) else 0.0
        toe_v = float(row.get("전면수직고(m)", 0.0)) if pd.notna(row.get("전면수직고(m)")) else 0.0
        rear_v = float(row.get("후단수직고(m)", 0.0)) if pd.notna(row.get("후단수직고(m)")) else 0.0

        bot_y = current_y - h
        is_first = (idx == 0)
        is_last = (idx == len(valid_tiers) - 1)

        # 블록 전면 X= -out_h, 후단 X= b - out_h
        x_rear = b - out_h
        max_b = max(max_b, x_rear)

        # 콘크리트 블록 폴리곤 그리기 (회색)
        if is_first:
            poly_points = [
                (-out_h, bot_y),
                (-out_h + b, bot_y),
                (-out_h + top_b, current_y),
                (-out_h, current_y)
            ]
            polygon = patches.Polygon(poly_points, closed=True, linewidth=1.5, edgecolor='black', facecolor='#d9d9d9',
                                      zorder=3)
            ax.add_patch(polygon)
            ax.text(-out_h + top_b / 2, current_y - h / 2, f"{name}\n(상 {top_b:.1f} / 하 {b:.1f})", ha='center',
                    va='center', fontsize=9, zorder=4)

        elif not is_last:
            rect = patches.Rectangle((-out_h, bot_y), b, h, linewidth=1.5, edgecolor='black', facecolor='#d9d9d9',
                                     zorder=3)
            ax.add_patch(rect)
            ax.text((b / 2) - out_h, bot_y + h / 2, f"{name}\n({b:.1f} x {h:.1f})", ha='center', va='center',
                    fontsize=9, zorder=4)

        else:
            slope_end_y = current_y - rear_v
            p_bottom_left = (-out_h, bot_y)
            p_bottom_right = (b - out_h, bot_y)
            p_top_right = (b - out_h, current_y)
            p_top_left = (0.0, current_y)
            p_slope_end = (0.0, slope_end_y)
            p_vert_end = (-out_h, bot_y + toe_v)

            poly_points = [p_bottom_left, p_bottom_right, p_top_right, p_top_left, p_slope_end, p_vert_end]
            polygon = patches.Polygon(poly_points, closed=True, linewidth=1.5, edgecolor='black', facecolor='#d9d9d9',
                                      zorder=3)
            ax.add_patch(polygon)

            if out_h > 0:
                ax.plot([0, 0], [bot_y, current_y], color='black', linestyle=':', linewidth=1.2, zorder=4)
                if toe_v > 0:
                    ax.text(-out_h / 2, bot_y + toe_v / 2, f"{toe_v:.1f}m\n(수직)", fontsize=8, color='darkred',
                            ha='center', va='center', zorder=4)
                if rear_v > 0:
                    ax.text(-0.1, current_y - rear_v / 2, f"{rear_v:.1f}m\n(후단)", fontsize=8, color='darkred',
                            ha='right', va='center', zorder=4)

            ax.text((b - out_h) / 2, bot_y + h / 2, f"{name}\n({b:.1f} x {h:.1f})", ha='center', va='center',
                    fontsize=9, zorder=4)

        # 레벨 표시 (좌측)
        ax.text(-out_h - 0.3, current_y, f"DL {current_y:.2f}", ha='right', va='center', fontsize=9, color='blue')
        if is_last:
            ax.text(-out_h - 0.3, bot_y, f"DL {bot_y:.2f}", ha='right', va='center', fontsize=9, color='blue')

        tier_geoms.append({
            'idx': idx, 'name': name,
            'top_y': current_y, 'bot_y': bot_y,
            'x_rear': x_rear
        })

        current_y = bot_y

    # 2. ★ 배면 사석 구간(Sub-columns) 계산 및 점선/라벨/치수 그리기 (오류 수정 핵심부)
    rubble_cols = []

    # 각 단의 배면 끝점 X좌표 수집 및 정렬
    rear_x_list = [g['x_rear'] for g in tier_geoms]
    unique_x = sorted(list(set(rear_x_list)))

    # X 좌표간 구간을 나누어 사석 기둥 생성
    for i in range(len(unique_x) - 1):
        x1 = unique_x[i]
        x2 = unique_x[i + 1]
        width = x2 - x1
        if width <= 0.01:
            continue

        # 해당 사석 기둥을 받치고 있는 단(tier)의 상단 Y고(Platform) 찾기
        sub_bot_y = c_top
        for g in tier_geoms:
            if g['x_rear'] >= x2 - 0.01:
                sub_bot_y = g['top_y']
                break

        rubble_cols.append({
            'x1': x1, 'x2': x2, 'width': width,
            'bot_y': sub_bot_y
        })

    # 사석 라벨 알파벳
    lbl_idx = 0
    rubble_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']

    for col in rubble_cols:
        x1 = col['x1']
        x2 = col['x2']
        x_center = (x1 + x2) / 2.0
        w = col['width']
        bot_y = col['bot_y']

        # 1) 수직 점선 (마루 DL +4.00부터 해당 사석 바닥까지만 정확히 연장)
        ax.plot([x2, x2], [bot_y, c_top], color='black', linestyle=':', linewidth=1.2, zorder=2)

        # 2) 마루 상단 폭 치수 표기 (예: 2.2, 1.0, 1.0)
        ax.text(x_center, c_top + 0.15, f"{w:.1f}", ha='center', va='bottom', fontsize=9, color='black')

        # 3) 잔류수위(R.W.L) 기준 수상/수중 라벨의 수직 중앙값(Y Center) 계산 및 텍스트 출력
        if bot_y >= rwl_n:
            # 사석 구간 전체가 수위 위에 있는 경우 (수상 사석만 존재)
            lbl = rubble_labels[lbl_idx % len(rubble_labels)]
            y_center = (c_top + bot_y) / 2.0
            ax.text(x_center, y_center, lbl, color='red', ha='center', va='center', fontsize=10, fontweight='bold',
                    zorder=5)
            lbl_idx += 1

        elif c_top <= rwl_n:
            # 사석 구간 전체가 수위 아래에 있는 경우 (수중 사석만 존재)
            lbl = rubble_labels[lbl_idx % len(rubble_labels)]
            y_center = (c_top + bot_y) / 2.0
            ax.text(x_center, y_center, lbl, color='black', ha='center', va='center', fontsize=10, fontweight='bold',
                    zorder=5)
            lbl_idx += 1

        else:
            # 사석 구간이 수위선에 걸쳐있는 경우 (수상/수중 분할)
            lbl_above = rubble_labels[lbl_idx % len(rubble_labels)]
            lbl_below = rubble_labels[(lbl_idx + 1) % len(rubble_labels)]

            y_above = (c_top + rwl_n) / 2.0
            y_below = (rwl_n + bot_y) / 2.0

            ax.text(x_center, y_above, lbl_above, color='red', ha='center', va='center', fontsize=10, fontweight='bold',
                    zorder=5)
            ax.text(x_center, y_below, lbl_below, color='black', ha='center', va='center', fontsize=10,
                    fontweight='bold', zorder=5)
            lbl_idx += 2

    # 마루 수평선 (DL +4.00)
    ax.plot([-0.5, max_b + 1.5], [c_top, c_top], color='black', linewidth=1.5, zorder=2)

    # 조위선 표시 (HWL, RWL, LLW)
    ax.axhline(hwl_n, color='#1f77b4', linestyle='--', linewidth=1.5, zorder=1)
    ax.text(max_b + 0.5, hwl_n, f"평상시 HWL ({hwl_n:.3f})", color='#1f77b4', va='bottom', fontsize=9)

    ax.axhline(rwl_n, color='#00b0f0', linestyle='-', linewidth=2, zorder=1)
    ax.text(max_b + 0.5, rwl_n, f"평상 잔류수위 ({rwl_n:.3f})", color='#00b0f0', va='bottom', fontsize=9, fontweight='bold')

    ax.axhline(llw, color='#0070c0', linestyle=':', linewidth=1.5, zorder=1)
    ax.text(max_b + 0.5, llw, f"L.L.W ({llw:.3f})", color='#0070c0', va='bottom', fontsize=9)

    # 여백 및 비율 설정
    ax.set_xlim(-4.0, max_b + 2.5)
    ax.set_ylim(current_y - 1.5, c_top + 1.2)
    ax.set_title("가) 하중 산정 및 단면 상세 모식도", fontsize=13, fontweight='bold', pad=15)
    ax.set_aspect('equal')
    ax.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"<div class='fig-container'><img src='data:image/png;base64,{img_b64}' style='max-width:100%; height:auto;'></div>"


# =====================================================================
# ★ 4. Streamlit UI
# =====================================================================
st.set_page_config(page_title="엑셀 완벽구현 블록식 안벽 구조계산서", layout="wide")
st.markdown("<h1 style='text-align:center;'>🧱 블록식 안벽 상세 구조계산서</h1>", unsafe_allow_html=True)
st.caption("※ 케이스별(상재하중 토압/자중 적용 여부) 하중조합 자동 연산 및 상세 출력 지원")

# 🌟 홈 화면 앱 사용설명서 추가 영역 (지진시 토압 이론 및 적용 배경 포함)
st.markdown("""
15. **15_WB**: 블록식 안벽 상세 구조계산서 자동화 및 하중조합(평상시/지진시) 검토 프로그램[cite: 1]
""")

with st.expander("👉 블록식 안벽 상세 구조계산서 자동화 시스템 앱 사용설명서 보기"):
    st.markdown(r"""
    **■ 🧱 블록식 안벽 상세 구조계산서 자동화 시스템 사용자 매뉴얼**

    이 프로그램은 항만 및 해안 구조물 중 **블록식 안벽(Block-type Quay Wall)**의 단별 제원과 지반 조건을 입력받아, 평상시 및 지진시의 각종 하중(자중, 토압, 수압, 상재하중, 견인력, 관성력, 동수압)을 자동으로 산정하고 **활동, 전도, 지지력에 대한 안정성 검토**를 수행하는 전문가용 통합 구조계산서 자동화 도구입니다[cite: 1].

    ---

    ### **Ⅰ. 블록 입력난 제원 상세 설명 (Input Data Guide)**

    좌측 사이드바의 **[블록 단별 규격]** 데이터 에디터(Data Editor)는 구조물의 핵심 단면을 결정하는 공간입니다. 각 열(Column)에 입력되는 항목의 세부 의미와 작성 방법은 다음과 같습니다[cite: 1].

    * **구분:** 각 단의 명칭을 입력합니다. (예: 상치, 1단, 2단, 3단, 4단, 5단 등)[cite: 1]
    * **높이 H(m):** 해당 블록 단의 수직 높이를 입력합니다. (단위: m)[cite: 1]
    * **폭 B(m):** 블록 단의 저면 폭(또는 대표 폭)을 입력합니다.[cite: 1]
    * **상단폭(m):** 상치콩크리트 또는 상부 단면의 윗면 폭을 입력합니다. (사다리꼴 단면 등 상하 폭이 다를 때 유용합니다.)[cite: 1]
    * **전면돌출(m):** 최하단 기초부 또는 특정 단에서 전면으로 튀어나온 돌출 길이를 입력합니다.[cite: 1]
    * **전면수직고(m):** 최하단 단면 등에서 전면 돌출부의 수직 높이 구간을 입력합니다.[cite: 1]
    * **경사비(1:N):** 단면 하부 또는 마운드 접합부의 경사 비율(1:N)을 입력합니다.[cite: 1]
    * **후단수직고(m):** 최하단 단면의 후면부 수직 높이를 입력하여 복잡한 기하학적 단면 형상을 완벽히 구현합니다[cite: 1].

    ---

    ### **Ⅱ. 주요 해석 기능 및 풀이 과정 (Calculation Process)**

    **📍 1단계: 해석 모드 및 조위 조건 설정**
    * **해석 모드:** '평상시 (Normal)' 또는 '지진시 (Earthquake)' 중 선택하여 하중 조합과 안전율 기준(평상시 1.2, 지진시 1.0)을 자동 전환합니다[cite: 1].
    * **조위 조건:** 최고고조위(H.W.L), 약최저저조위(L.L.W), 평상 잔류수위(R.W.L), 그리고 전면수심(H)을 입력하여 부력 및 수압 산정의 기준선을 설정합니다[cite: 1].

    **📍 2단계: 하중 산정 자동화 (Case별 완벽 분류)**
    * **제체 자중 및 모멘트:** 각 단별 콘크리트 단면과 배면 사석의 중량을 수상/수중 조건에 따라 분리하여 연직력($V$)과 저항모멘트($M_v$)를 정밀 산정합니다[cite: 1].
    * **토압 및 수압 산정:** 평상시 주동토압계수($K_a$)와 지진시 겉보기 진도($k'$), 지진합성각($\theta$), 그리고 수중부 토압강도를 구역별로 나누어 산출합니다[cite: 1].
    * **특수 하중 (지진시):** 지진 발생 시 제체 자체의 진동에 의한 **관성력($Eq$)**, 파도와 구조물 상호작용에 의한 **동수압($P_{dw}$)**을 완벽하게 반영합니다[cite: 1].

    ---

    ### **Ⅲ. 지진시 토압 산정 이론 및 벽면마찰각($\delta$) 적용 배경**
    """)

    st.markdown("""
    <div style="background-color: #e8f0fe; border-left: 5px solid #1a73e8; padding: 12px; margin: 10px 0; font-size: 13px; line-height: 1.6;">
      <b>※ 참고 : 항만설계기준 지진시 토압편</b><br>
      (1) 지진시의 토압은 모노베·오까베가 제안한 이론에 근거한다.<br>
      (2) 벽면마찰각<br>
      일반적으로 ±15° 이하로 한다. 뒤채움재의 내부마찰각(ø)의 1/2정도를 기준으로 한다.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(r"""
    * **모노베·오카베(M-O) 이론 배경:** 
      * 지진시 토압은 모노베·오카베가 제안한 이론에 근거하며, M-O 이론($\delta > 0$)은 쿨롬(Coulomb) 토압 이론을 지진시 동적 상황으로 확장한 것으로 벽체와 뒤채움재 사이의 마찰각($\delta$, 통상 $\Phi/2$ 또는 $\pm 15^\circ$ 전후)을 명시적으로 고려합니다.
    * **국내 항만설계기준 적용상의 특징:**
      * 일본의 경우 랜킨(Rankine)토압을 사용하지 않고 모두 쿨롬토압을 적용하므로 정합성에 문제가 없으나, 국내 항만설계기준의 경우 벽면과 가상배면이 있는 조건(케이스 제외)에서 랭킨토압을 적용하도록 되어 있어 평상시는 문제없으나 지진시 모노베·오카베 제안식과의 연계 시 벽면마찰각 고려 여부가 실무적 논란이 될 수 있습니다.
      * 공식 기준상 지진시는 모노베·오카베 제안식을 사용하여 $\delta = 15^\circ$ 등을 고려해야 하나, 설계기준의 랜킨토압 적용 원칙과 상이한 부분이 발생합니다.
    * **본 프로그램의 적용 방식 (항만시설물 설계사례집 준용):**
      * 『항만시설물 설계사례집(상권)』에 따라 평상시 및 지진시 모두 **벽면마찰각 $\delta = 0$ (랜킨토압 준용)**을 일관되게 적용하였습니다.
      * 이 경우 지진시 다소 보수적(안전측)으로 평가되어 경제성 측면에서는 불리할 수 있으나, 사례집 준용을 통한 안정성 검토의 통일성을 확보하도록 구현되었습니다.
    """)

st.sidebar.header("📁 해석 모드 및 수위 조건")
calc_mode = st.sidebar.radio("해석 모드 선택", ["평상시 (Normal)", "지진시 (Earthquake)"], index=0)

hwl_n = st.sidebar.number_input("평상시 H.W.L (m)", value=1.964, format="%.3f", step=0.001)
llw = st.sidebar.number_input("L.L.W (m)", value=0.000, format="%.3f", step=0.001)

default_rwl = llw + (hwl_n - llw) / 3.0
rwl_n = st.sidebar.number_input("평상 잔류수위 (m)", value=default_rwl, format="%.3f", step=0.001)
h_water = st.sidebar.number_input("전면수심 H (m)", value=12.000, format="%.3f", step=0.100)

c_top = st.sidebar.number_input("마루높이 (부지고, DL.m)", value=4.00, format="%.2f", step=0.01)

st.sidebar.divider()
st.sidebar.header("🧱 블록 단별 규격 (무제한 입력)")
if "tier_data" not in st.session_state:
    st.session_state.tier_data = pd.DataFrame({
        "구분": ["상치", "1단", "2단", "3단", "4단", "5단"],
        "높이 H(m)": [2.5, 2.0, 2.0, 2.0, 2.0, 2.0],
        "폭 B(m)": [3.3, 5.5, 5.5, 6.5, 7.5, 9.5],
        "상단폭(m)": [3.3, 5.5, 5.5, 6.5, 7.5, 9.5],
        "전면돌출(m)": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        "전면수직고(m)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.5],
        "경사비(1:N)": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        "후단수직고(m)": [0.0, 0.0, 0.0, 0.0, 0.0, 0.5]
    })

edited_tiers = st.sidebar.data_editor(
    st.session_state.tier_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "구분": st.column_config.TextColumn("구분", width="small"),
        "높이 H(m)": st.column_config.NumberColumn("높이", format="%.2f", width="small"),
        "폭 B(m)": st.column_config.NumberColumn("폭", format="%.2f", width="small"),
        "상단폭(m)": st.column_config.NumberColumn("상단폭", format="%.2f", width="small"),
        "전면돌출(m)": st.column_config.NumberColumn("돌출", format="%.2f", width="small"),
        "전면수직고(m)": st.column_config.NumberColumn("수직고", format="%.2f", width="small"),
        "경사비(1:N)": st.column_config.NumberColumn("경사", format="%.2f", width="small"),
        "후단수직고(m)": st.column_config.NumberColumn("후단수직고", format="%.2f", width="small"),
    }
)

st.sidebar.divider()
st.sidebar.header("🌍 지반 및 단위중량 조건")
phi = st.sidebar.number_input("내부마찰각 Φ (°)", value=40.0)
delta = st.sidebar.number_input("벽면마찰각 δ (°)", value=15.0)
kh = st.sidebar.number_input("설계수평지진계수(kh)", value=0.079, format="%.3f")
# =====================================================================
# ★ 추가할 코드: 함수 바깥에서 ka_n (평상시 주동토압계수) 미리 정의하기
# =====================================================================
ka_n = math.tan(math.radians(45 - phi / 2)) ** 2

st.sidebar.subheader("단위중량 (kN/m³)")
g_c_wet = st.sidebar.number_input("무근Con (수상)", value=22.6)
g_c_sub = st.sidebar.number_input("무근Con (수중)", value=12.6)
g_c_eq = st.sidebar.number_input("무근Con (관성력용)", value=22.6)
g_s_wet = st.sidebar.number_input("사석 (수상)", value=18.0)
g_s_sub = st.sidebar.number_input("사석 (수중)", value=10.0)
g_s_sat = st.sidebar.number_input("사석 (포화, 지진시)", value=20.0)
g_w = st.sidebar.number_input("해수 단위중량 (kN/m³)", value=10.1, format="%.1f")

st.sidebar.divider()
st.sidebar.subheader("설계 하중 및 지지력 조건")
qa_n = st.sidebar.number_input("사석 허용지지력 (평상시, kPa)", value=500.0, step=10.0)
qa_s = st.sidebar.number_input("사석 허용지지력 (지진시, kPa)", value=600.0, step=10.0)

q_n = st.sidebar.number_input("평상시 상재하중 (kPa)", value=20.0)
q_s = st.sidebar.number_input("지진시 상재하중 (kPa)", value=10.0)
mooring_t = st.sidebar.number_input("계선곡주 견인력 (kN)", value=350.0)
mooring_interval = st.sidebar.number_input("계선주 설치간격 (m)", value=15.0, format="%.2f")
mooring_h = st.sidebar.number_input("계선곡주 높이(견인력 작용점, m)", value=0.40, format="%.2f")

rep = ReportBuilder()


def o_title(t, level=2):
    if level == 1:
        st.header(t)
    elif level == 2:
        st.subheader(t)
    rep.title(t, level)


def o_md(t): st.markdown(t); rep.md(t)


def o_latex(eq): st.latex(eq); rep.latex(eq)


def o_table(df, styled=None): st.table(styled if styled else df); rep.table(df, styled)


def o_html(h): st.markdown(h, unsafe_allow_html=True); rep.html_raw(h)


# =====================================================================
# ★ 5. 정밀 연산 엔진 (CASE별 하중조합 완벽 분류 및 토압 정밀 적분 적용)
# =====================================================================

# -------------------------------------------------------------
# 토압 일치화를 위한 층별 토압강도(Pa) 사전 계산 및 적분 함수
# -------------------------------------------------------------
def get_ep_nodes(tiers_df, rwl_n, c_top, g_wet, g_sub, is_eq=False, q_val=0.0, kh=0.079, phi=40.0, delta=0.0):
    if is_eq: delta = 0.0

    # 1) 층 분할 (수위 기준)
    temp_nodes = []
    c_el = c_top
    for idx, row in tiers_df.iterrows():
        try:
            h_tier = float(row["높이 H(m)"])
        except:
            continue
        b_el = c_el - h_tier
        if c_el > rwl_n > b_el:
            temp_nodes.append({"top": c_el, "bot": rwl_n, "gamma": g_wet})
            temp_nodes.append({"top": rwl_n, "bot": b_el, "gamma": g_sub})
        else:
            g = g_wet if (c_el + b_el) / 2 > rwl_n else g_sub
            temp_nodes.append({"top": c_el, "bot": b_el, "gamma": g})
        c_el = b_el

    # 2) 지진시 합성각(theta) 계산
    c_th = 0.0
    theta_above = 0.0
    if is_eq:
        total_gamma_hi = 0.0
        total_H = 0.0
        for n in temp_nodes:
            mid_el = (n["top"] + n["bot"]) / 2.0
            h = n["top"] - n["bot"]
            if mid_el > rwl_n:
                total_gamma_hi += h * n["gamma"]
            else:
                total_H += h

        g_sat_val = 20.0
        theta_above = math.degrees(math.atan(kh))

        num_kp = 2 * (total_gamma_hi + q_val) + total_H * g_sat_val
        den_kp = 2 * (total_gamma_hi + q_val) + total_H * (g_sat_val - 10.0)
        kp_below = (num_kp / den_kp) * kh if den_kp > 0 else kh
        c_th = math.degrees(math.atan(kp_below))

    # 3) 노드별 토압강도(Pa) 산출
    nodes = []
    current_sv = 0.0

    def calc_ka(th):
        rad_phi = math.radians(phi)
        rad_theta = math.radians(th)
        rad_delta = math.radians(delta)
        num = math.cos(rad_phi - rad_theta) ** 2
        try:
            term = (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_theta)) / math.cos(rad_delta + rad_theta)
            den = math.cos(rad_theta) * math.cos(rad_delta + rad_theta) * (1 + math.sqrt(max(0, term))) ** 2
            return num / den if den > 0 else 0.0
        except:
            return 0.0

    ka_n = math.tan(math.radians(45 - phi / 2)) ** 2

    initial_ka = calc_ka(theta_above) if is_eq else ka_n
    nodes.append({"el": c_top, "pa": (q_val) * initial_ka})

    for n in temp_nodes:
        h = n["top"] - n["bot"]
        current_sv += h * n["gamma"]
        mid_el = (n["top"] + n["bot"]) / 2.0

        curr_th = 0.0
        if is_eq:
            curr_th = theta_above if mid_el > rwl_n else c_th
            ka = calc_ka(curr_th)
        else:
            ka = ka_n

        nodes.append({"el": n["bot"], "pa": (current_sv + q_val) * ka})

        # 지진시 수위선에서 주동토압계수(Ka)가 변하는 불연속점 처리
        if is_eq and abs(n["bot"] - rwl_n) < 0.001:
            ka_below = calc_ka(c_th)
            nodes.append({"el": rwl_n, "pa": (current_sv + q_val) * ka_below})

    return nodes


def integrate_ep(nodes, target_el):
    # 목표 엘리베이션(target_el)까지의 토압 면적(수평력) 및 모멘트 암 적분
    total_F = 0.0
    total_M = 0.0
    for i in range(len(nodes) - 1):
        top_node = nodes[i]
        bot_node = nodes[i + 1]

        if top_node["el"] <= target_el + 0.001:
            break

        bot_el = max(bot_node["el"], target_el)
        h = top_node["el"] - bot_el
        if h <= 0.001:
            continue

        p_top = top_node["pa"]
        orig_h = top_node["el"] - bot_node["el"]
        p_bot = p_top + (bot_node["pa"] - p_top) * (h / orig_h) if orig_h > 0 else bot_node["pa"]

        f_rect = p_top * h
        arm_rect = h / 2.0 + (bot_el - target_el)

        f_tri = 0.5 * (p_bot - p_top) * h
        arm_tri = h / 3.0 + (bot_el - target_el)

        total_F += (f_rect + f_tri)
        total_M += (f_rect * arm_rect + f_tri * arm_tri)
    return total_F, total_M


# 모든 케이스(평상/지진, 상재유무)의 토압 분포를 미리 계산
ep_nodes_n0 = get_ep_nodes(edited_tiers, rwl_n, c_top, g_s_wet, g_s_sub, False, 0.0, kh, phi, delta)
ep_nodes_nq = get_ep_nodes(edited_tiers, rwl_n, c_top, g_s_wet, g_s_sub, False, q_n, kh, phi, delta)
ep_nodes_s0 = get_ep_nodes(edited_tiers, rwl_n, c_top, g_s_wet, g_s_sub, True, 0.0, kh, phi, delta)
ep_nodes_sq = get_ep_nodes(edited_tiers, rwl_n, c_top, g_s_wet, g_s_sub, True, q_s, kh, phi, delta)

# -------------------------------------------------------------

sum_W_n, sum_W_x_n = 0.0, 0.0
sum_mass_s, sum_mass_y_s = 0.0, 0.0
prev_b = 0.0
current_elev = c_top

sum_v_sq_n, sum_mr_sq_n = 0.0, 0.0
sum_v_sq_s, sum_mr_sq_s = 0.0, 0.0
prev_b_sq = 0.0

tier_details = []
html_table_rows = ""
html_table_rows_inertia = ""
prev_mass = 0.0
prev_cg_y_rel = 0.0

rubble_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']
rubble_lbl_idx = 0

try:
    top_b = float(edited_tiers.iloc[0]["폭 B(m)"]) if not edited_tiers.empty else 0.0
except:
    top_b = 0.0

for idx, row in edited_tiers.iterrows():
    name_val = row.get("구분", None)
    if pd.isna(name_val) or str(name_val).strip().lower() in ["none", "nan", ""]:
        continue
    try:
        h = float(row["높이 H(m)"])
        b = float(row["폭 B(m)"])
        if pd.isna(h) or pd.isna(b):
            continue
    except Exception:
        continue

    name = str(name_val)
    top_elev = current_elev
    bot_elev = current_elev - h
    z_depth = c_top - bot_elev
    is_last = (idx == len(edited_tiers) - 1)

    tier_components = []
    inertia_components = []

    if idx > 0:
        tier_components.append({"sub": "상치자중" if idx == 1 else "상부자중", "basis_n": "-", "vn": sum_W_n,
                                "xn": sum_W_x_n / sum_W_n if sum_W_n > 0 else 0, "mvn": sum_W_x_n})
        inertia_components.append({"sub": "from", "basis": "이전 단 누적", "mass": prev_mass, "arm": prev_cg_y_rel + h,
                                   "mh": prev_mass * (prev_cg_y_rel + h)})

    h_above = max(0, top_elev - max(bot_elev, rwl_n))
    h_below = max(0, min(top_elev, rwl_n) - bot_elev)

    if h_above > 0:
        v_n = b * h_above * g_c_wet
        m_s = b * h_above * g_c_eq
        x = b / 2.0
        mv_n = v_n * x
        y_cm = top_elev - h_above / 2.0
        sum_W_n += v_n;
        sum_W_x_n += mv_n
        sum_mass_s += m_s;
        sum_mass_y_s += m_s * y_cm
        tier_components.append(
            {"sub": "Con수상", "basis_n": f"{b:.2f} × {h_above:.2f} × 1 × {g_c_wet:.1f}", "vn": v_n, "xn": x,
             "mvn": mv_n})
        inertia_components.append({"sub": "Con수상", "basis": f"{b:.2f} × {h_above:.2f} × 1 × {g_c_eq:.1f}", "mass": m_s,
                                   "arm": y_cm - bot_elev, "mh": m_s * (y_cm - bot_elev)})

    if h_below > 0:
        v_n = b * h_below * g_c_sub
        m_s = b * h_below * g_c_eq
        x = b / 2.0
        mv_n = v_n * x
        y_cm = bot_elev + h_below / 2.0
        sum_W_n += v_n;
        sum_W_x_n += mv_n
        sum_mass_s += m_s;
        sum_mass_y_s += m_s * y_cm
        tier_components.append(
            {"sub": "Con수중", "basis_n": f"{b:.2f} × {h_below:.2f} × 1 × {g_c_sub:.1f}", "vn": v_n, "xn": x,
             "mvn": mv_n})
        inertia_components.append({"sub": "Con수중", "basis": f"{b:.2f} × {h_below:.2f} × 1 × {g_c_eq:.1f}", "mass": m_s,
                                   "arm": y_cm - bot_elev, "mh": m_s * (y_cm - bot_elev)})

    if is_last:
        v_n_rect = 1.0 * 0.5 * 1.0 * (-g_c_sub)
        m_s_rect = 1.0 * 0.5 * 1.0 * (-g_c_eq)
        x_rect = 1.0 / 2.0
        mv_n_rect = v_n_rect * x_rect
        y_cm_rect = top_elev - 0.25
        sum_W_n += v_n_rect;
        sum_W_x_n += mv_n_rect
        sum_mass_s += m_s_rect;
        sum_mass_y_s += m_s_rect * y_cm_rect
        tier_components.append(
            {"sub": "Con공제", "basis_n": f"1.00 × 0.50 × 1 × -{g_c_sub:.2f}", "vn": v_n_rect, "xn": x_rect,
             "mvn": mv_n_rect})
        inertia_components.append(
            {"sub": "Con공제", "basis": f"1.00 × 0.50 × 1 × -{g_c_eq:.2f}", "mass": m_s_rect, "arm": y_cm_rect - bot_elev,
             "mh": m_s_rect * (y_cm_rect - bot_elev)})

        v_n_tri = 1.0 * 1.0 * 0.5 * (-g_c_sub)
        m_s_tri = 1.0 * 1.0 * 0.5 * (-g_c_eq)
        x_tri = 1.0 / 3.0
        mv_n_tri = v_n_tri * x_tri
        y_cm_tri = top_elev - 0.5 - (1.0 / 3.0)
        sum_W_n += v_n_tri;
        sum_W_x_n += mv_n_tri
        sum_mass_s += m_s_tri;
        sum_mass_y_s += m_s_tri * y_cm_tri
        tier_components.append(
            {"sub": "Con공제", "basis_n": f"1.00 × 1.00 × 1/2 × -{g_c_sub:.2f}", "vn": v_n_tri, "xn": x_tri,
             "mvn": mv_n_tri})
        inertia_components.append(
            {"sub": "Con공제", "basis": f"1.00 × 1.00 × 1/2 × -{g_c_eq:.2f}", "mass": m_s_tri, "arm": y_cm_tri - bot_elev,
             "mh": m_s_tri * (y_cm_tri - bot_elev)})

    if idx > 0:
        db = max(0, b - prev_b - (1.0 if is_last else 0.0))
        if db > 0:
            s_above = max(0, c_top - max(top_elev, rwl_n))
            s_below = max(0, min(c_top, rwl_n) - top_elev)

            if s_above > 0 or s_below > 0:
                x = prev_b + db / 2.0
                lbl_above_str = ""
                lbl_below_str = ""

                if c_top > rwl_n > top_elev:
                    lbl_above_str = rubble_labels[rubble_lbl_idx % len(rubble_labels)]
                    lbl_below_str = rubble_labels[(rubble_lbl_idx + 1) % len(rubble_labels)]
                    rubble_lbl_idx += 2
                elif top_elev >= rwl_n:
                    lbl_above_str = rubble_labels[rubble_lbl_idx % len(rubble_labels)]
                    rubble_lbl_idx += 1
                elif c_top <= rwl_n:
                    lbl_below_str = rubble_labels[rubble_lbl_idx % len(rubble_labels)]
                    rubble_lbl_idx += 1

                if s_above > 0:
                    v_n = db * s_above * g_s_wet
                    m_s = db * s_above * g_s_wet
                    mv_n = v_n * x
                    y_cm = c_top - s_above / 2.0
                    sum_W_n += v_n;
                    sum_W_x_n += mv_n
                    sum_mass_s += m_s;
                    sum_mass_y_s += m_s * y_cm
                    tier_components.append(
                        {"sub": f"사석수상({lbl_above_str})", "basis_n": f"{db:.2f} × {s_above:.2f} × 1 × {g_s_wet:.1f}",
                         "vn": v_n, "xn": x, "mvn": mv_n})
                    inertia_components.append(
                        {"sub": f"사석수상({lbl_above_str})", "basis": f"{db:.2f} × {s_above:.2f} × 1 × {g_s_wet:.1f}",
                         "mass": m_s, "arm": y_cm - bot_elev, "mh": m_s * (y_cm - bot_elev)})

                if s_below > 0:
                    v_n = db * s_below * g_s_sub
                    m_s = db * s_below * g_s_sat
                    mv_n = v_n * x
                    y_cm = top_elev + s_below / 2.0
                    sum_W_n += v_n;
                    sum_W_x_n += mv_n
                    sum_mass_s += m_s;
                    sum_mass_y_s += m_s * y_cm
                    tier_components.append(
                        {"sub": f"사석수중({lbl_below_str})", "basis_n": f"{db:.2f} × {s_below:.2f} × 1 × {g_s_sub:.1f}",
                         "vn": v_n, "xn": x, "mvn": mv_n})
                    inertia_components.append(
                        {"sub": f"사석수중({lbl_below_str})", "basis": f"{db:.2f} × {s_below:.2f} × 1 × {g_s_sat:.1f}",
                         "mass": m_s, "arm": y_cm - bot_elev, "mh": m_s * (y_cm - bot_elev)})

    xn_total = sum_W_x_n / sum_W_n if sum_W_n > 0 else 0
    rowspan = len(tier_components) + 1
    html_table_rows += f"<tr><td rowspan='{rowspan}' style='border: 1px solid #ccc; background:#fff; vertical-align:middle; text-align:center;'><b>[{name}]</b><br>DL {top_elev:.2f} ~ {bot_elev:.2f}</td>"
    for i, comp in enumerate(tier_components):
        if i > 0: html_table_rows += "<tr>"
        html_table_rows += f"<td style='border: 1px solid #ccc; padding:6px; text-align:center;'>{comp['sub']}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'><div style='font-size:11px; color:#7f8c8d; margin-bottom:3px;'>{comp['basis_n']}</div><b>{comp['vn']:.2f}</b></td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{comp['xn']:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right; font-weight:bold;'>{comp['mvn']:.2f}</td></tr>\n"
    html_table_rows += f"<tr style='background:#fdf2e9; font-weight:bold;'><td style='border: 1px solid #ccc; padding:6px; text-align:center;'>합 계</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{sum_W_n:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{xn_total:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right; color:#e67e22;'>{sum_W_x_n:.2f}</td></tr>\n"

    sum_m_s = sum(comp["mass"] for comp in inertia_components)
    sum_mh = sum(comp["mh"] for comp in inertia_components)
    prev_cg_y_rel = sum_mh / sum_m_s if sum_m_s > 0 else 0
    prev_mass = sum_m_s
    rowspan_in = len(inertia_components) + 1
    html_table_rows_inertia += f"<tr><td rowspan='{rowspan_in}' style='border: 1px solid #ccc; background:#fff; vertical-align:middle; text-align:center;'><b>[{name}]</b><br>DL {top_elev:.2f} ~ {bot_elev:.2f}</td>"
    for i, comp in enumerate(inertia_components):
        if i > 0: html_table_rows_inertia += "<tr>"
        html_table_rows_inertia += f"<td style='border: 1px solid #ccc; padding:6px; text-align:center;'>{comp['sub']}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'><div style='font-size:11px; color:#7f8c8d; margin-bottom:3px;'>{comp['basis']}</div><b>{comp['mass']:.2f}</b></td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{comp['arm']:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right; color:#1a73e8; font-weight:bold;'>{comp['mh']:.2f}</td></tr>\n"
    html_table_rows_inertia += f"<tr style='background:#e8f0fe; font-weight:bold;'><td style='border: 1px solid #ccc; padding:6px; text-align:center;'>계</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{sum_m_s:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right;'>{prev_cg_y_rel:.2f}</td><td style='border: 1px solid #ccc; padding:6px; text-align:right; color:#1a73e8;'>{sum_mh:.2f}</td></tr>\n"

    hw = max(0, rwl_n - llw)
    h_tri_total = max(0, rwl_n - max(llw, bot_elev))
    h_rect_total = max(0, llw - bot_elev) if rwl_n > llw else 0
    max_p = g_w * (rwl_n - llw) if rwl_n > llw else 0

    pw_tri = 0.5 * max_p * h_tri_total if h_tri_total > 0 else 0
    arm_tri = (h_tri_total / 3.0) + h_rect_total

    pw_rect = max_p * h_rect_total
    arm_rect = h_rect_total / 2.0

    pw_n = pw_tri + pw_rect
    mw_n = (pw_tri * arm_tri) + (pw_rect * arm_rect)

    u_n = 0.0;
    mu_n = 0.0

    # ★ 수정됨: 단일 삼각형 공식이 아닌, 산출표와 100% 동일한 사전계산 노드를 활용하여 정밀 적분 수행
    ph0_n, mh0_n = integrate_ep(ep_nodes_n0, bot_elev)
    phq_n, mhq_n = integrate_ep(ep_nodes_nq, bot_elev)
    ph0_s, mh0_s = integrate_ep(ep_nodes_s0, bot_elev)
    phq_s, mhq_s = integrate_ep(ep_nodes_sq, bot_elev)

    tr_f = mooring_t / mooring_interval if mooring_interval > 0 else 0.0
    tr_arm = (c_top + mooring_h) - bot_elev
    tr_m = tr_f * tr_arm

    eq_f = sum_mass_s * kh
    cg_y = sum_mass_y_s / sum_mass_s if sum_mass_s > 0 else bot_elev
    eq_m = eq_f * max(0, cg_y - bot_elev)

    y_val_dw = max(0.0, llw - bot_elev)
    dw_f = (7.0 / 12.0) * kh * g_w * math.sqrt(h_water) * (y_val_dw ** 1.5) if y_val_dw > 0 else 0.0
    hd_from_top = (3.0 / 5.0) * y_val_dw
    hd_from_bot = y_val_dw - hd_from_top if y_val_dw > 0 else 0.0
    dw_m = dw_f * hd_from_bot

    # ★ 상재하중(연직력 및 모멘트) 단별 산정
    is_last_tier = (idx == len(edited_tiers) - 1)
    eff_b = (b - 1.0) if is_last_tier else b
    arm_sq = 1.0 + (eff_b / 2.0) if is_last_tier else (eff_b / 2.0)

    curr_v_sq_n = q_n * eff_b
    curr_mr_sq_n = curr_v_sq_n * arm_sq

    curr_v_sq_s = q_s * eff_b
    curr_mr_sq_s = curr_v_sq_s * arm_sq
    v_sq_tier_s = curr_v_sq_s

    # ★ 지진시 상재하중 관성력(제체 위 상재하중 질량 X kh)
    eq_f_sq = curr_v_sq_s * kh
    eq_m_sq = eq_f_sq * (c_top - bot_elev)

    tier_details.append({
        "name": name, "bot_el": bot_elev, "b": b, "z": z_depth, "hw": hw,
        "pw_n": pw_n, "mw_n": mw_n, "u_n": u_n, "mu_n": mu_n,
        "v_sq_n": curr_v_sq_n, "mr_sq_n": curr_mr_sq_n, "v_sq_s": curr_v_sq_s,
        "v_sq_tier_s": v_sq_tier_s, "mr_sq_s": curr_mr_sq_s, "tr_f": tr_f,
        "tr_m": tr_m, "dw_f": dw_f, "dw_m": dw_m, "sum_W_n": sum_W_n,
        "sum_W_x_n": sum_W_x_n, "inertia_mass": sum_m_s, "inertia_arm": prev_cg_y_rel,
        "ph0_n": ph0_n, "mh0_n": mh0_n, "phq_n": phq_n, "mhq_n": mhq_n,

        "eq_f": eq_f, "eq_m": eq_m, "eq_f_sq": eq_f_sq, "eq_m_sq": eq_m_sq,

        "V_1_1": sum_W_n - u_n, "H_1_1": ph0_n + pw_n + tr_f, "Mr_1_1": sum_W_x_n + mu_n, "Mo_1_1": mh0_n + mw_n + tr_m,
        "V_1_2": sum_W_n - u_n, "H_1_2": phq_n + pw_n + tr_f, "Mr_1_2": sum_W_x_n + mu_n, "Mo_1_2": mhq_n + mw_n + tr_m,
        "V_1_3": sum_W_n + curr_v_sq_n - u_n, "H_1_3": ph0_n + pw_n + tr_f, "Mr_1_3": sum_W_x_n + curr_mr_sq_n + mu_n,
        "Mo_1_3": mh0_n + mw_n + tr_m,
        "V_1_4": sum_W_n + curr_v_sq_n - u_n, "H_1_4": phq_n + pw_n + tr_f, "Mr_1_4": sum_W_x_n + curr_mr_sq_n + mu_n,
        "Mo_1_4": mhq_n + mw_n + tr_m,

        "V_2_1": sum_W_n - u_n, "H_2_1": ph0_s + eq_f + pw_n + dw_f, "Mr_2_1": sum_W_x_n + mu_n,
        "Mo_2_1": mh0_s + eq_m + mw_n + dw_m,
        "V_2_2": sum_W_n - u_n, "H_2_2": phq_s + eq_f + pw_n + dw_f, "Mr_2_2": sum_W_x_n + mu_n,
        "Mo_2_2": mhq_s + eq_m + mw_n + dw_m,
        "V_2_3": sum_W_n + curr_v_sq_s - u_n, "H_2_3": ph0_s + eq_f + eq_f_sq + pw_n + dw_f,
        "Mr_2_3": sum_W_x_n + curr_mr_sq_s + mu_n, "Mo_2_3": mh0_s + eq_m + eq_m_sq + mw_n + dw_m,
        "V_2_4": sum_W_n + curr_v_sq_s - u_n, "H_2_4": phq_s + eq_f + eq_f_sq + pw_n + dw_f,
        "Mr_2_4": sum_W_x_n + curr_mr_sq_s + mu_n, "Mo_2_4": mhq_s + eq_m + eq_m_sq + mw_n + dw_m
    })

    current_elev = bot_elev
    prev_b = b

# =====================================================================
# ★ 누적 하중(from) 누락 오류가 완벽히 수정된 토압 산출표 생성 함수
# =====================================================================

def generate_earth_pressure_html(tiers_df, ka, q_val, rwl, c_top, g_wet, g_sub, title_text, title_color, is_eq=False,
                                 kh=0.079, phi=40.0, delta=0.0, omega=10.0):
    import math
    if is_eq:
        delta = 0.0

    temp_nodes = []
    c_el = c_top
    current_sv = 0.0
    temp_nodes.append({"el": c_el, "gamma": g_wet, "h": 0.0})
    for idx, row in tiers_df.iterrows():
        h_tier = float(row["높이 H(m)"])
        b_el = c_el - h_tier
        if c_el > rwl > b_el:
            h1 = c_el - rwl
            temp_nodes.append({"el": rwl, "gamma": g_wet, "h": h1})
            h2 = rwl - b_el
            temp_nodes.append({"el": b_el, "gamma": g_sub, "h": h2})
        else:
            g = g_wet if (c_el + b_el) / 2 > rwl else g_sub
            temp_nodes.append({"el": b_el, "gamma": g, "h": h_tier})
        c_el = b_el

    total_gamma_hi = 0.0
    total_H = 0.0
    for i in range(1, len(temp_nodes)):
        mid_el = (temp_nodes[i - 1]['el'] + temp_nodes[i]['el']) / 2.0
        if mid_el > rwl:
            total_gamma_hi += temp_nodes[i]['h'] * temp_nodes[i]['gamma']
        else:
            total_H += temp_nodes[i]['h']

    g_sat_val = 20.0
    theta_above = math.degrees(math.atan(kh))

    num_kp_0 = 2 * total_gamma_hi + total_H * g_sat_val
    den_kp_0 = 2 * total_gamma_hi + total_H * (g_sat_val - 10.0)
    kp_below_0 = (num_kp_0 / den_kp_0) * kh if den_kp_0 > 0 else kh
    theta_below_0 = math.degrees(math.atan(kp_below_0))

    num_kp_q = 2 * (total_gamma_hi + q_val) + total_H * g_sat_val
    den_kp_q = 2 * (total_gamma_hi + q_val) + total_H * (g_sat_val - 10.0)
    kp_below_q = (num_kp_q / den_kp_q) * kh if den_kp_q > 0 else kh
    theta_below_q = math.degrees(math.atan(kp_below_q))

    html = f"<div style='margin-bottom: 25px;'>"

    if is_eq:
        c_w = q_val
        c_kp = kp_below_q if c_w > 0 else kp_below_0
        c_th = theta_below_q if c_w > 0 else theta_below_0
        c_suf = "[상재하중 고려]" if c_w > 0 else "[상재하중 미고려]"

        nodes = []
        c_el = c_top
        current_sv = 0.0

        rad_phi = math.radians(phi);
        rad_theta_0 = math.radians(theta_above);
        rad_delta = math.radians(delta)
        num_ka0 = math.cos(rad_phi - rad_theta_0) ** 2
        den_ka0 = math.cos(rad_theta_0) * math.cos(rad_delta + rad_theta_0) * (1 + math.sqrt(
            (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_theta_0)) / math.cos(rad_delta + rad_theta_0))) ** 2
        ka_0 = num_ka0 / den_ka0 if den_ka0 > 0 else 0.0

        nodes.append({"el": c_el, "gamma": g_wet, "h": 0.0, "sv": current_sv, "sv_q": current_sv + c_w,
                      "pa": (current_sv + c_w if c_w > 0 else current_sv) * ka_0, "ka": ka_0})

        for idx, row in tiers_df.iterrows():
            h_tier = float(row["높이 H(m)"])
            b_el = c_el - h_tier

            if c_el > rwl > b_el:
                h1 = c_el - rwl
                current_sv += h1 * g_wet
                rad_th1 = math.radians(theta_above)
                num_ka1 = math.cos(rad_phi - rad_th1) ** 2
                den_ka1 = math.cos(rad_th1) * math.cos(rad_delta + rad_th1) * (1 + math.sqrt(
                    (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_th1)) / math.cos(rad_delta + rad_th1))) ** 2
                ka1 = num_ka1 / den_ka1 if den_ka1 > 0 else 0.0
                pa1 = (current_sv + c_w if c_w > 0 else current_sv) * ka1
                nodes.append({"el": rwl, "gamma": g_wet, "h": h1, "sv": current_sv, "sv_q": current_sv + c_w, "pa": pa1,
                              "ka": ka1})

                rad_th2 = math.radians(c_th)
                num_ka2 = math.cos(rad_phi - rad_th2) ** 2
                den_ka2 = math.cos(rad_th2) * math.cos(rad_delta + rad_th2) * (1 + math.sqrt(
                    (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_th2)) / math.cos(rad_delta + rad_th2))) ** 2
                ka2 = num_ka2 / den_ka2 if den_ka2 > 0 else 0.0
                pa2 = (current_sv + c_w if c_w > 0 else current_sv) * ka2
                nodes.append(
                    {"el": rwl, "gamma": g_sub, "h": 0.0, "sv": current_sv, "sv_q": current_sv + c_w, "pa": pa2,
                     "ka": ka2})

                h2 = rwl - b_el
                current_sv += h2 * g_sub
                pa_sub = (current_sv + c_w if c_w > 0 else current_sv) * ka2
                nodes.append(
                    {"el": b_el, "gamma": g_sub, "h": h2, "sv": current_sv, "sv_q": current_sv + c_w, "pa": pa_sub,
                     "ka": ka2})
            else:
                g = g_wet if (c_el + b_el) / 2 > rwl else g_sub
                current_sv += h_tier * g
                mid_el = (c_el + b_el) / 2.0
                curr_th_n = theta_above if mid_el > rwl else c_th
                rad_th_n = math.radians(curr_th_n)
                num_kan = math.cos(rad_phi - rad_th_n) ** 2
                den_kan = math.cos(rad_th_n) * math.cos(rad_delta + rad_th_n) * (1 + math.sqrt(
                    (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_th_n)) / math.cos(
                        rad_delta + rad_th_n))) ** 2
                kan = num_kan / den_kan if den_kan > 0 else 0.0
                pan = (current_sv + c_w if c_w > 0 else current_sv) * kan
                nodes.append(
                    {"el": b_el, "gamma": g, "h": h_tier, "sv": current_sv, "sv_q": current_sv + c_w, "pa": pan,
                     "ka": kan})
            c_el = b_el

        html += "<div style='background:#fdfefe; padding:15px; border:1px solid #ccc; margin-bottom:15px; font-size:12px;'>"
        html += f"<div style='font-size:14px; font-weight:bold; color:#333; margin-bottom:10px;'>가) 겉보기 진도(k') 및 지진합성각(θ) {c_suf}</div>"

        html += "<div style='text-align:center; padding:12px; margin-bottom:15px; background:#fff; border:1px solid #e0e0e0; font-size:13px; font-weight:bold; line-height:1.8;'>"
        html += "k' = <span style='display:inline-block; vertical-align:middle; text-align:center;'><span style='border-bottom:1px solid #000; padding:0 4px; display:block;'>2(Σγ<sub>t</sub>h<sub>i</sub> + Σγh<sub>j</sub> + ω) + γh</span><span style='padding:0 4px; display:block;'>2[Σγ<sub>t</sub>h<sub>i</sub> + Σ(γ-10)h<sub>j</sub> + ω] + (γ-10)h</span></span> × k &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; θ = tan<sup>-1</sup> k'"
        html += "</div>"

        html += "<table style='border:none; text-align:left; font-size:12px; line-height:1.6; margin-bottom:15px; margin-left: 10px;'>"
        html += "<tr><td style='border:none; padding:2px 5px;'>여기서,</td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>k'</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>겉보기 진도</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>γ<sub>t</sub></td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>잔류수위 위 흙의 단위체적중량(kN/m³)</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>h<sub>i</sub></td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>잔류수위 위 i층의 토층의 두께(m)</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>γ</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>물에 의해 포화된 흙의 공기중 단위체적중량(kN/m³)</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>h<sub>j</sub></td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>잔류수위 아래에서 토압을 산정하는 층보다 위인 j층의 토층 두께(m)</td></tr>"
        html += f"<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>ω</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>지표면의 단위면적당 재하하중(kN/m²) = &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {c_w:.2f} kN/m²</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>h</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>잔류수위 아래에서 토압을 산정하는 토층의 두께(m)</td></tr>"
        html += f"<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>k</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>진도 = &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {kh:.3f}</td></tr>"
        html += "</table>"

        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px; margin-bottom:15px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>구 분</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>h<sub>i</sub></th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>h</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>h<sub>j</sub></th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>Σγ<sub>t</sub>h<sub>i</sub></th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>Σγh<sub>j</sub>+ω</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>γh</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>Σ(γ-10)h<sub>j</sub>+ω</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>(γ-10)h</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>k'</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>θ ( ° )</th>"
        html += "</tr>"

        sum_gamma_hi_cur = 0.0
        printed_below = False

        for i, n in enumerate(nodes[1:], 1):
            n_prev = nodes[i - 1]
            level_str = f"({'+' if n['el'] >= 0 else '-'}){abs(n['el']):.3f}"
            prev_level_str = f"({'+' if n_prev['el'] >= 0 else '-'}){abs(n_prev['el']):.3f}"

            h_layer = n['h']
            is_above_rwl = ((n_prev['el'] + n['el']) / 2.0) > rwl or (n['el'] == rwl and n['gamma'] == g_wet)

            if is_above_rwl:
                if h_layer > 0:
                    sum_gamma_hi_cur += h_layer * n['gamma']
                h_layer_str = f"{h_layer:.2f}" if h_layer > 0 else "-"
                html += "<tr>"
                html += f"<td style='border:1px dotted #777;'>{prev_level_str}<br>{level_str}</td>"
                html += f"<td style='border:1px dotted #777;'>{h_layer_str}</td>"
                html += f"<td style='border:1px dotted #777;'>-</td>"
                html += f"<td style='border:1px dotted #777;'>-</td>"
                html += f"<td style='border:1px dotted #777;'>{sum_gamma_hi_cur:.2f}</td>"
                html += f"<td style='border:1px dotted #777;'>{0.00:.2f}</td>"
                html += f"<td style='border:1px dotted #777;'>{0.00:.2f}</td>"
                html += f"<td style='border:1px dotted #777;'>{0.00:.2f}</td>"
                html += f"<td style='border:1px dotted #777;'>{0.00:.2f}</td>"
                html += f"<td style='border:1px dotted #777;'>{kh:.3f}</td>"
                html += f"<td style='border:1px dotted #777;'>{theta_above:.2f}</td>"
                html += "</tr>"
            else:
                if not printed_below:
                    printed_below = True
                    first_node_el = nodes[0]['el']
                    last_node_el = nodes[-1]['el']
                    first_str = f"({'+' if first_node_el >= 0 else '-'}){abs(first_node_el):.3f}"
                    last_str = f"({'+' if last_node_el >= 0 else '-'}){abs(last_node_el):.3f}"

                    gamma_h_val = total_H * g_sat_val
                    gamma_sub_h = total_H * (g_sat_val - 10.0)

                    html += "<tr>"
                    html += f"<td style='border:1px dotted #777;'>{first_str}<br>{last_str}</td>"
                    html += f"<td style='border:1px dotted #777;'>-</td>"
                    html += f"<td style='border:1px dotted #777;'>{total_H:.2f}</td>"
                    html += f"<td style='border:1px dotted #777;'>-</td>"
                    html += f"<td style='border:1px dotted #777;'>{total_gamma_hi:.2f}</td>"
                    html += f"<td style='border:1px dotted #777;'>{c_w:.2f}</td>"
                    html += f"<td style='border:1px dotted #777;'>{gamma_h_val:.2f}</td>"
                    html += f"<td style='border:1px dotted #777;'>{c_w:.2f}</td>"
                    html += f"<td style='border:1px dotted #777;'>{gamma_sub_h:.2f}</td>"
                    html += f"<td style='border:1px dotted #777; font-weight:bold; color:#d35400;'>{c_kp:.3f}</td>"
                    html += f"<td style='border:1px dotted #777; font-weight:bold; color:#1a73e8;'>{c_th:.2f}</td>"
                    html += "</tr>"
        html += "</table></div>"

        html += "<div style='background:#fdfefe; padding:15px; border:1px solid #ccc; margin-bottom:15px; font-size:12px;'>"
        html += f"<div style='font-size:14px; font-weight:bold; color:#333; margin-bottom:10px;'>나) 지진시 주동토압계수 {c_suf}</div>"

        html += "<div style='text-align:center; padding:12px; margin-bottom:15px; background:#fff; border:1px solid #e0e0e0; font-size:13px; font-weight:bold; line-height:1.8;'>"
        html += "K<sub>ai</sub> = <span style='display:inline-block; vertical-align:middle; text-align:center;'><span style='border-bottom:1px solid #000; padding:0 4px; display:block;'>cos²(φ<sub>i</sub> - ψ - θ)</span><span style='padding:0 4px; display:block;'>cosθ · cos²ψ · cos(δ + ψ + θ) × [ 1 + √{ (sin(φ<sub>i</sub> + δ) · sin(φ<sub>i</sub> - β - θ)) / (cos(δ + ψ + θ) · cos(ψ - β)) } ]²</span></span>"
        html += "</div>"

        html += "<table style='border:none; text-align:left; font-size:12px; line-height:1.6; margin-bottom:15px; margin-left: 10px;'>"
        html += "<tr><td style='border:none; padding:2px 5px;'>여기서,</td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>φ<sub>i</sub></td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>i층 흙의 내부마찰각(°)</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>ψ</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>벽면이 연직과 이루는 각도(°) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 0.0°</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>β</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>지표면이 수평과 이루는 각도(°) &nbsp;&nbsp;&nbsp; 0.0°</td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>δ</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>흙과 벽면과의 마찰각(°) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style='color:red;'>0.0°</span></td></tr>"
        html += "<tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>θ</td><td style='border:none; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>지진합성각(°)</td></tr>"
        html += "</table>"

        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>구 분</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>φ<sub>i</sub></th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>θ</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>cos²(φ-ψ-θ)</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>cosθ</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>cos²ψ</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>cos(δ+ψ+θ)</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>sin(φ+δ)</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>sin(φ-β-θ)</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>cos(ψ-β)</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333; padding:6px;'>K<sub>ai</sub></th>"
        html += "</tr>"

        for i, n in enumerate(nodes[1:], 1):
            n_prev = nodes[i - 1]
            level_str = f"({'+' if n['el'] >= 0 else '-'}){abs(n['el']):.3f}"
            prev_level_str = f"({'+' if n_prev['el'] >= 0 else '-'}){abs(n_prev['el']):.3f}"

            is_above = ((n_prev['el'] + n['el']) / 2.0) > rwl or (n['el'] == rwl and n['gamma'] == g_wet)
            curr_theta = theta_above if is_above else c_th

            rad_phi = math.radians(phi);
            rad_theta = math.radians(curr_theta);
            rad_delta = math.radians(0.0)
            v_cos2 = math.cos(rad_phi - rad_theta) ** 2
            v_cost = math.cos(rad_theta)
            v_cos_dpt = math.cos(rad_delta + rad_theta)
            v_sin_pd = math.sin(rad_phi + rad_delta)
            v_sin_pbt = math.sin(rad_phi - rad_theta)

            num_ka_disp = math.cos(rad_phi - rad_theta) ** 2
            den_ka_disp = math.cos(rad_theta) * math.cos(rad_delta + rad_theta) * (1 + math.sqrt(
                (math.sin(rad_phi + rad_delta) * math.sin(rad_phi - rad_theta)) / math.cos(rad_delta + rad_theta))) ** 2
            calc_kai_disp = num_ka_disp / den_ka_disp if den_ka_disp > 0 else 0.0

            html += "<tr>"
            html += f"<td style='border:1px dotted #777;'>{prev_level_str}<br>{level_str}</td>"
            html += f"<td style='border:1px dotted #777;'>{phi:.1f}°</td>"
            html += f"<td style='border:1px dotted #777;'>{curr_theta:.2f}°</td>"
            html += f"<td style='border:1px dotted #777;'>{v_cos2:.3f}</td>"
            html += f"<td style='border:1px dotted #777;'>{v_cost:.3f}</td>"
            html += f"<td style='border:1px dotted #777;'>1.000</td>"
            html += f"<td style='border:1px dotted #777;'>{v_cos_dpt:.3f}</td>"
            html += f"<td style='border:1px dotted #777;'>{v_sin_pd:.3f}</td>"
            html += f"<td style='border:1px dotted #777;'>{v_sin_pbt:.3f}</td>"
            html += f"<td style='border:1px dotted #777;'>1.000</td>"
            html += f"<td style='border:1px dotted #777; font-weight:bold; color:red;'>{calc_kai_disp:.4f}</td>"
            html += "</tr>"
        html += "</table></div>"

        html += f"<div style='font-size:14px; font-weight:bold; color:#333; margin-bottom:5px; margin-top:20px;'>다) 토압강도 및 수평토압 {c_suf}</div>"
        html += f"<div style='font-size:12px; margin-bottom:10px; color:#555;'>- 토압강도 : (상재하중 = &nbsp;&nbsp;&nbsp; {c_w:.2f} kN/m²)</div>"

        html += "<div style='display: flex; gap: 20px; align-items: flex-start; background:#fdfefe; padding:15px; border:1px solid #ccc; margin-bottom:15px;'>"

        html += "<div style='flex: 1.8; min-width: 520px; font-size:12px;'>"
        html += "<div style='background:#fff; padding:10px; border:1px solid #bbb; margin-bottom:12px;'>"
        formula_str = "Pa = (Σγh + q) · Ka" if c_w > 0 else "Pa = Σγh · Ka"
        html += f"<div style='font-weight:bold; font-size:13px; margin-bottom:6px; border-bottom:2px solid #333; padding-bottom:3px;'>{formula_str}</div>"
        html += "<div style='color:#555; line-height:1.5; font-size:11px;'>"
        html += "· <b>Pa</b> : 토압강도 (kN/m²)<br>"
        html += "· <b>Σγh</b> : 토사 자중에 의한 연직응력 (kN/m²)<br>"
        if c_w > 0:
            html += f"· <b>q</b> : 상재하중 ({c_w:.2f} kN/m²)<br>"
        html += "· <b>Ka</b> : 주동토압계수 (지진시 수상/수중 분리 적용)"
        html += "</div></div>"

        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>구 분</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>γ (kN/m³)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>h(m)</th>"
        if c_w > 0:
            html += "<th style='border:1px solid #ccc; padding:6px;'>Σγh+q(kN/m²)</th>"
        else:
            html += "<th style='border:1px solid #ccc; padding:6px;'>Σγh(kN/m²)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>Ka (Kea)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>Pa(kN/m²)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>비 고</th>"
        html += "</tr>"

        for n in nodes:
            level_str = f"({'+' if n['el'] >= 0 else '-'}){abs(n['el']):.3f}"
            html += "<tr>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; color:#d35400; font-weight:bold;'>{n['gamma']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'>{n['h']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'>{n['sv_q'] if c_w > 0 else n['sv']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:red;'>{n['ka']:.4f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{n['pa']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'></td>"
            html += "</tr>"
        html += "</table>"
        html += "</div>"

        # ★ Word 호환을 위한 Matplotlib Base64 이미지 변환 적용
        fig, ax = plt.subplots(figsize=(3.4, 4.2))
        el_max = nodes[0]["el"]
        el_min = nodes[-1]["el"]
        el_range = el_max - el_min if el_max != el_min else 1.0
        max_pa = max([n["pa"] for n in nodes]) if nodes else 35.0
        
        y_vals = [n["el"] for n in nodes]
        x_vals = [n["pa"] for n in nodes]
        
        ax.fill_betweenx(y_vals, 0, x_vals, facecolor='#f0f4f8', edgecolor='#2c3e50', linewidth=1.5)
        ax.plot([0, 0], [el_min, el_max], color='black', linewidth=2)
        
        for i, n in enumerate(nodes):
            y_pos = n["el"]
            pa_val = n["pa"]
            level_str = f"({'+' if y_pos >= 0 else '-'}){abs(y_pos):.3f}"
            
            ax.text(-max_pa * 0.05, y_pos, level_str, ha='right', va='center', fontsize=9, fontweight='bold')
            if pa_val > 0.001:
                ax.annotate("", xy=(pa_val, y_pos), xytext=(0, y_pos), arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1))
                ax.text(pa_val + max_pa * 0.05, y_pos, f"{pa_val:.2f}", color='#d35400', fontsize=9, fontweight='bold', va='center')
        
        ax.set_ylim(el_min - el_range * 0.05, el_max + el_range * 0.05)
        ax.set_xlim(-max_pa * 0.3, max_pa * 1.3)
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        
        html += f"<div style='flex: 1.0; background: #fff; border: 1px solid #bbb; padding: 5px; text-align: center; overflow-x: auto;'>"
        html += f"<div style='font-size:12px; font-weight:bold; margin-bottom:5px; color:#444;'>토압강도도 (단위: kN/m²)</div>"
        html += f"<img src='data:image/png;base64,{img_b64}' style='max-width:100%; height:auto;'>"
        html += "</div></div>"


        html += f"<div style='margin-top: 15px; margin-bottom: 25px;'>"
        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th colspan='2' rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>구 분</th>"
        html += "<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>수평토압Ph(kN)</th>"
        html += "<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>팔길이y(m)</th>"
        html += "<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>모멘트<br>Mh(kN·m)</th>"
        html += "</tr>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>토압</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>높이</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>종류</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>수평력</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>거리</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>종류</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>추가</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>팔길이</th>"
        html += "</tr>"

        prev_F = 0.0;
        prev_cg = 0.0;
        row_num = 1

        for i in range(1, len(nodes)):
            n_prev = nodes[i - 1]
            n_cur = nodes[i]
            h = n_cur["h"]

            p_top = n_prev["pa"]
            p_bot = n_cur["pa"]

            components = []
            if h <= 0.001:
                continue

            # ★ 수정된 부분: 이전 층의 누적 수평력(prev_F)이 존재하면 무조건 from을 추가함 (빈 열 추가하여 오른쪽으로 한 칸 이동)
            if prev_F > 0.001:
                from_arm = h + prev_cg
                from_m = prev_F * from_arm
                components.append({"type": "from", "f": prev_F, "h": h, "add": prev_cg, "arm": from_arm, "m": from_m})

            f_top = p_top * h / 2.0
            arm_top = h * (2.0 / 3.0)
            m_top = f_top * arm_top
            components.append({"type": "tri", "row_no": row_num, "p": p_top, "h": h, "k": "1/2", "f": f_top, "dist": h,
                               "k_arm": "2/3", "arm": arm_top, "m": m_top})
            row_num += 1

            f_bot = p_bot * h / 2.0
            arm_bot = h * (1.0 / 3.0)
            m_bot = f_bot * arm_bot
            components.append({"type": "tri", "row_no": row_num, "p": p_bot, "h": h, "k": "1/2", "f": f_bot, "dist": h,
                               "k_arm": "1/3", "arm": arm_bot, "m": m_bot})
            row_num += 1

            sum_f = sum([c["f"] for c in components])
            sum_m = sum([c["m"] for c in components])
            prev_F = sum_f
            prev_cg = sum_m / sum_f if sum_f > 0 else 0.0
            components.append({"type": "sum", "f": sum_f, "arm": prev_cg, "m": sum_m})

            level_str = f"({'+' if n_cur['el'] >= 0 else '-'}){abs(n_cur['el']):.3f}"
            rowspan = len(components)
            first_row = True

            for comp in components:
                html += "<tr>"
                if first_row:
                    html += f"<td rowspan='{rowspan}' style='border:1px solid #ccc; font-weight:bold;'>{level_str}</td>"
                    first_row = False

                if comp["type"] == "from":
                    html += f"<td style='border:1px dotted #ccc; color:#777;'>from</td>"
                    prev_label = f"({'+' if n_prev['el'] >= 0 else '-'}){abs(n_prev['el']):.3f}"
                    html += f"<td colspan='2' style='border:1px dotted #ccc;'>{prev_label}</td>"
                    # ★ 누락된 <td style='border:1px dotted #ccc;'></td> 부분 추가
                    html += f"<td style='border:1px dotted #ccc;'></td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'></td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['add']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc; font-weight:bold;'>{comp['m']:.2f}</td>"
                elif comp["type"] == "tri":
                    html += f"<td style='border:1px dotted #ccc;'>{comp['row_no']}</td><td style='border:1px dotted #ccc;'>{comp['p']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k']}</td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['dist']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k_arm']}</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['m']:.2f}</td>"
                elif comp["type"] == "sum":
                    html += f"<td colspan='4' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>계</td><td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['f']:.2f}</td><td colspan='3' style='border:1px solid #ccc; background:#fbfcfc;'></td>"
                    html += f"<td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['arm']:.2f}</td><td style='border:1px solid #ccc; font-weight:bold; color:#1a73e8; background:#fbfcfc;'>{comp['m']:.2f}</td>"
                html += "</tr>"

        html += "</table></div>"

    else:
        nodes = []
        c_el = c_top
        current_sv = 0.0
        nodes.append(
            {"el": c_el, "gamma": g_wet, "h": 0.0, "sv": current_sv, "sv_q": current_sv + q_val, "pa": 0.0, "ka": ka})
        for idx, row in tiers_df.iterrows():
            h_tier = float(row["높이 H(m)"])
            b_el = c_el - h_tier
            if c_el > rwl > b_el:
                h1 = c_el - rwl
                current_sv += h1 * g_wet
                nodes.append(
                    {"el": rwl, "gamma": g_wet, "h": h1, "sv": current_sv, "sv_q": current_sv + q_val, "pa": 0.0,
                     "ka": ka})
                h2 = rwl - b_el
                current_sv += h2 * g_sub
                nodes.append(
                    {"el": b_el, "gamma": g_sub, "h": h2, "sv": current_sv, "sv_q": current_sv + q_val, "pa": 0.0,
                     "ka": ka})
            else:
                g = g_wet if (c_el + b_el) / 2 > rwl else g_sub
                current_sv += h_tier * g
                nodes.append(
                    {"el": b_el, "gamma": g, "h": h_tier, "sv": current_sv, "sv_q": current_sv + q_val, "pa": 0.0,
                     "ka": ka})
            c_el = b_el

        for n in nodes:
            n['pa'] = n['sv_q'] * ka if q_val > 0 else n['sv'] * ka

        html += f"<h3 style='color:{title_color}; font-size:1.1em; margin-bottom:5px;'>- 토압강도 : {title_text} (상재하중 = {q_val:.2f} kN/m²)</h3>"

        html += "<div style='display: flex; gap: 20px; align-items: flex-start; background:#fdfefe; padding:15px; border:1px solid #ccc; margin-bottom:15px;'>"

        html += "<div style='flex: 1.8; min-width: 520px; font-size:12px;'>"
        html += "<div style='background:#fff; padding:10px; border:1px solid #bbb; margin-bottom:12px;'>"
        formula_str = "Pa = (Σγh + q) · Ka" if q_val > 0 else "Pa = Σγh · Ka"
        html += f"<div style='font-weight:bold; font-size:13px; margin-bottom:6px; border-bottom:2px solid #333; padding-bottom:3px;'>{formula_str}</div>"
        html += "<div style='color:#555; line-height:1.5; font-size:11px;'>"
        html += "· <b>Pa</b> : 토압강도 (kN/m²)<br>"
        html += "· <b>Σγh</b> : 토사 자중에 의한 연직응력 (kN/m²)<br>"
        if q_val > 0:
            html += f"· <b>q</b> : 상재하중 ({q_val:.2f} kN/m²)<br>"
        html += "· <b>Ka</b> : 주동토압계수"
        html += "</div></div>"

        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>구 분</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>γ (kN/m³)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>h(m)</th>"
        if q_val > 0:
            html += "<th style='border:1px solid #ccc; padding:6px;'>Σγh+q(kN/m²)</th>"
        else:
            html += "<th style='border:1px solid #ccc; padding:6px;'>Σγh(kN/m²)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>Ka</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>Pa(kN/m²)</th>"
        html += "<th style='border:1px solid #ccc; padding:6px;'>비 고</th>"
        html += "</tr>"

        for n in nodes:
            level_str = f"({'+' if n['el'] >= 0 else '-'}){abs(n['el']):.3f}"
            html += "<tr>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; color:#d35400; font-weight:bold;'>{n['gamma']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'>{n['h']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'>{n['sv_q'] if q_val > 0 else n['sv']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:red;'>{n['ka']:.4f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{n['pa']:.2f}</td>"
            html += f"<td style='border:1px solid #ccc; padding:6px;'></td>"
            html += "</tr>"
        html += "</table></div>"

        # ★ Word 호환을 위한 Matplotlib Base64 이미지 변환 적용 (토압강도도)
        fig, ax = plt.subplots(figsize=(2.5, 3.5))
        el_max = nodes[0]["el"]
        el_min = nodes[-1]["el"]
        el_range = el_max - el_min if el_max != el_min else 1.0
        max_pa = max([n["pa"] for n in nodes]) if nodes else 35.0
        
        y_vals = [n["el"] for n in nodes]
        x_vals = [n["pa"] for n in nodes]
        
        ax.fill_betweenx(y_vals, 0, x_vals, facecolor='#f0f4f8', edgecolor='#2c3e50', linewidth=1.5)
        ax.plot([0, 0], [el_min, el_max], color='black', linewidth=2)
        
        for i, n in enumerate(nodes):
            y_pos = n["el"]
            pa_val = n["pa"]
            level_str = f"({'+' if y_pos >= 0 else '-'}){abs(y_pos):.3f}"
            
            # 중복 레벨 텍스트 방지 (바로 위 노드와 높이가 같으면 생략)
            is_duplicate_el = (i > 0 and abs(nodes[i - 1]['el'] - y_pos) < 0.001)
            
            if not is_duplicate_el:
                ax.text(-max_pa * 0.05, y_pos, level_str, ha='right', va='center', fontsize=8, fontweight='bold')
                
            if pa_val > 0.001:
                ax.annotate("", xy=(pa_val, y_pos), xytext=(0, y_pos), arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1))
                # 텍스트 겹침 방지 설정
                va_align = 'bottom' if is_duplicate_el else ('top' if i < len(nodes)-1 and abs(nodes[i+1]['el']-y_pos)<0.001 else 'center')
                ax.text(pa_val + max_pa * 0.05, y_pos, f"{pa_val:.2f}", color='#d35400', fontsize=8, fontweight='bold', va=va_align)
            elif not is_duplicate_el:
                ax.text(max_pa * 0.05, y_pos, "0.00", color='#d35400', fontsize=8, fontweight='bold', va='center')
                
            # 구간 번호 표시
            if i < len(nodes) - 1:
                next_y = nodes[i + 1]['el']
                if abs(y_pos - next_y) > 0.001:
                    mid_y = (y_pos + next_y) / 2.0
                    ax.text(max_pa * 0.15, mid_y, str(i + 1), color='#555', fontsize=8, va='center')
        
        ax.set_ylim(el_min - el_range * 0.05, el_max + el_range * 0.05)
        ax.set_xlim(-max_pa * 0.4, max_pa * 1.4)
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        
        html += f"<div style='flex: 1.0; background: #fff; border: 1px solid #bbb; padding: 5px; text-align: center; overflow-x: auto;'>"
        html += f"<div style='font-size:12px; font-weight:bold; margin-bottom:5px; color:#444;'>토압강도도 (단위: kN/m²)</div>"
        html += f"<img src='data:image/png;base64,{img_b64}' style='max-width:100%; height:auto;'>"
        html += "</div></div>"

        html += f"<div style='margin-top: 15px;'>"
        html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px;'>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th colspan='2' rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>구 분</th>"
        html += "<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>수평토압Ph(kN)</th>"
        html += "<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>팔길이y(m)</th>"
        html += "<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>모멘트<br>Mh(kN·m)</th>"
        html += "</tr>"
        html += "<tr style='background-color:#d9d9d9;'>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>토압</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>높이</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>종류</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>수평력</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>거리</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>종류</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>추가</th>"
        html += "<th style='border:1px dotted #777; border-bottom:1px solid #333;'>팔길이</th>"
        html += "</tr>"

        prev_F = 0.0;
        prev_cg = 0.0;
        row_num = 1
        for i in range(1, len(nodes)):
            n_prev = nodes[i - 1]
            n_cur = nodes[i]
            h = n_cur["h"]
            if h <= 0.001: continue
            p_top = n_prev["pa"]
            p_bot = n_cur["pa"]
            components = []

            # ★ 수정된 부분: 이전 층의 누적 수평력이 존재할 경우 from 추가
            if prev_F > 0.001:
                from_arm = h + prev_cg
                from_m = prev_F * from_arm
                components.append({"type": "from", "f": prev_F, "h": h, "add": prev_cg, "arm": from_arm, "m": from_m})

            f_top = p_top * h / 2.0
            arm_top = h * (2.0 / 3.0)
            m_top = f_top * arm_top
            components.append({"type": "tri", "row_no": row_num, "p": p_top, "h": h, "k": "1/2", "f": f_top, "dist": h,
                               "k_arm": "2/3", "arm": arm_top, "m": m_top})
            row_num += 1

            f_bot = p_bot * h / 2.0
            arm_bot = h * (1.0 / 3.0)
            m_bot = f_bot * arm_bot
            components.append({"type": "tri", "row_no": row_num, "p": p_bot, "h": h, "k": "1/2", "f": f_bot, "dist": h,
                               "k_arm": "1/3", "arm": arm_bot, "m": m_bot})
            row_num += 1

            sum_f = sum([c["f"] for c in components])
            sum_m = sum([c["m"] for c in components])
            prev_F = sum_f
            prev_cg = sum_m / sum_f if sum_f > 0 else 0.0
            components.append({"type": "sum", "f": sum_f, "arm": prev_cg, "m": sum_m})

            level_str = f"({'+' if n_cur['el'] >= 0 else '-'}){abs(n_cur['el']):.3f}"
            rowspan = len(components)
            first_row = True
            for comp in components:
                html += "<tr>"
                if first_row:
                    html += f"<td rowspan='{rowspan}' style='border:1px solid #ccc; font-weight:bold;'>{level_str}</td>"
                    first_row = False
                if comp["type"] == "from":
                    html += f"<td style='border:1px dotted #ccc; color:#777;'>from</td>"
                    prev_label = f"({'+' if n_prev['el'] >= 0 else '-'}){abs(n_prev['el']):.3f}"
                    html += f"<td colspan='2' style='border:1px dotted #ccc;'>{prev_label}</td>"
                    # ★ 누락된 <td style='border:1px dotted #ccc;'></td> 부분 추가
                    html += f"<td style='border:1px dotted #ccc;'></td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'></td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['add']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc; font-weight:bold;'>{comp['m']:.2f}</td>"
                elif comp["type"] == "tri":
                    html += f"<td style='border:1px dotted #ccc;'>{comp['row_no']}</td><td style='border:1px dotted #ccc;'>{comp['p']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k']}</td>"
                    html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['dist']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k_arm']}</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['m']:.2f}</td>"
                elif comp["type"] == "sum":
                    html += f"<td colspan='4' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>계</td><td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['f']:.2f}</td><td colspan='3' style='border:1px solid #ccc; background:#fbfcfc;'></td>"
                    html += f"<td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['arm']:.2f}</td><td style='border:1px solid #ccc; font-weight:bold; color:#1a73e8; background:#fbfcfc;'>{comp['m']:.2f}</td>"
                html += "</tr>"
        html += "</table></div>"

    html += "</div>"
    return html


# =====================================================================
# ★ 잔류수압 분포 모식도가 추가된 수압 산정 함수 (들여쓰기 오류 수정)
# =====================================================================
def generate_water_pressure_html(tiers_df, hwl, llw, rwl, c_top, g_w=10.0):
    hw = max(0, rwl - llw)
    max_pw = g_w * hw

    # 1) 잔류수위 산정 (들여쓰기 제거)
    html = f"""<div style='margin-bottom: 25px;'>
<h3 style='color:#1a73e8; font-size:1.1em; margin-bottom:5px;'>1) 잔류수위(상시, 지진시)</h3>
<div style='background:#fdfefe; padding:10px; border:1px solid #ccc;'>
- 잔류수위(R.W.L) = ({hwl:.3f} - {llw:.3f}) × 1/3 = <b>DL.({'+' if rwl >= 0 else '-'}){abs(rwl):.3f} m</b><br>
- 전면수위(Approx.L.L.W) = <b>DL.(±){abs(llw):.3f} m</b><br>
- 잔류수위차(h<sub>w</sub>) = {rwl:.3f} - {llw:.3f} = <b>{hw:.3f} m</b>
</div>
</div>
"""

    bot_el_last = c_top - tiers_df["높이 H(m)"].astype(float).sum()

    # -----------------------------------------------------------------
    # ★ 잔류수압 분포도 (PNG 이미지) 생성 로직 (MS Word 완벽 호환)
    # -----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(2.5, 2.5))
    el_max = rwl + 0.5
    el_min = bot_el_last - 0.5
    el_range = el_max - el_min if el_max != el_min else 1.0

    y_vals = [rwl, llw, bot_el_last]
    x_vals = [0.0, max_pw, max_pw]

    ax.fill_betweenx(y_vals, 0, x_vals, facecolor='#e1f5fe', edgecolor='#0277bd', linewidth=1.5)
    ax.plot([0, 0], [el_min, el_max], color='black', linewidth=2)

    nodes_wp = [
        {"el": rwl, "pw": 0.0, "is_llw": False},
        {"el": llw, "pw": max_pw, "is_llw": True},
        {"el": bot_el_last, "pw": max_pw, "is_llw": False}
    ]

    for n in nodes_wp:
        y_pos = n['el']
        pw_val = n['pw']
        level_str = f"({'+' if y_pos >= 0 else '-'}){abs(y_pos):.3f}"
        
        ax.text(-max_pw * 0.05, y_pos, level_str, ha='right', va='center', fontsize=9, fontweight='bold')
        
        if pw_val > 0.001:
            ax.annotate("", xy=(pw_val, y_pos), xytext=(0, y_pos), arrowprops=dict(arrowstyle="->", color="#0277bd", lw=1))
            va_align = 'top' if n['is_llw'] else 'bottom'
            ax.text(pw_val + max_pw * 0.05, y_pos, f"{pw_val:.2f}", color='#d35400', fontsize=9, fontweight='bold', va=va_align)
        else:
            ax.text(max_pw * 0.05, y_pos, "0.00", color='#d35400', fontsize=9, fontweight='bold', va='center')

    ax.set_ylim(el_min - el_range * 0.05, el_max + el_range * 0.05)
    ax.set_xlim(-max_pw * 0.4, max_pw * 1.4)
    ax.axis('off')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')

    svg_html = f"<div style='font-size:12px; font-weight:bold; margin-bottom:5px; color:#444;'>잔류수압 분포도 (단위: kN/m²)</div>"
    svg_html += f"<img src='data:image/png;base64,{img_b64}' style='max-width:100%; height:auto;'>"

    # -----------------------------------------------------------------
    # ★ 2. 잔류수압 표 (줄간격 넓힘) + 분포도 HTML 통합 반환
    # -----------------------------------------------------------------
    html += f"""<div style='margin-bottom: 25px;'>
<h3 style='color:#1a73e8; font-size:1.1em; margin-bottom:5px;'>2) 잔류수압 산정 및 분포도</h3>
<div style='display: flex; gap: 20px; align-items: flex-start; background:#fdfefe; padding:15px; border:1px solid #ccc;'>

<!-- 왼쪽: 수압 산정 표 -->
<div style='flex: 1.5; min-width: 400px;'>
<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px; margin-top: 15px;'>
<tr style='background-color:#d9d9d9;'>
<!-- 🔹 th(제목 줄)의 상하 패딩을 12px로 증가 -->
<th style='border:1px dotted #ccc; padding:12px 8px;'>구 분</th>
<th style='border:1px dotted #ccc; padding:12px 8px;'>γ<sub>w</sub>(kN/m³)</th>
<th style='border:1px dotted #ccc; padding:12px 8px;'>h<sub>w</sub>(m)</th>
<th style='border:1px dotted #ccc; padding:12px 8px;'>P<sub>w</sub>(kN/m²)</th>
<th style='border:1px dotted #ccc; padding:12px 8px;'>비 고</th>
</tr>
<tr>
<!-- 🔹 td(내용 줄)의 상하 패딩을 18px로 대폭 늘려 줄간격 확보 -->
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold;'>({'+' if rwl >= 0 else '-'}){abs(rwl):.3f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>{g_w:.2f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>0.000</td>
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold;'>0.00</td>
<td style='border:1px solid #ccc; padding:18px 8px;'></td>
</tr>
<tr>
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold;'>(±){abs(llw):.3f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>{g_w:.2f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>{hw:.3f}</td>
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold; color:#1a73e8;'>{max_pw:.2f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'></td>
</tr>
<tr>
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold;'>({'+' if bot_el_last >= 0 else '-'}){abs(bot_el_last):.3f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>{g_w:.2f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'>{hw:.3f}</td>
<td style='border:1px solid #ccc; padding:18px 8px; font-weight:bold; color:#1a73e8;'>{max_pw:.2f}</td>
<td style='border:1px solid #ccc; padding:18px 8px;'></td>
</tr>
</table>
</div>

<!-- 오른쪽: 수압 분포 모식도 (SVG) -->
<div style='flex: 1.0; background: #fff; border: 1px solid #bbb; padding: 5px; text-align: center; overflow-x: auto;'>
{svg_html}
</div>

</div>
</div>
"""

    # 3) 잔류수압에 의한 수평력 표 생성 (이하 기존 수식 로직 유지)
    html += "<div style='margin-bottom: 25px;'>"
    html += "<h3 style='color:#1a73e8; font-size:1.1em; margin-bottom:5px;'>3) 잔류수압에 의한 수평력</h3>"
    html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px;'>"
    html += """<tr style='background-color:#d9d9d9;'>
<th colspan='2' rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>구 분</th>
<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>잔류수압 Pw(kN)</th>
<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>팔길이 y(m)</th>
<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>모멘트<br>Mh(kN·m)</th>
</tr>
<tr style='background-color:#d9d9d9;'>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>수압</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>높이</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>종류</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>수평력</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>거리</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>종류</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>추가</th>
<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>팔길이</th>
</tr>
"""

    html += f"<tr><td colspan='2' style='border:1px dotted #ccc;'>({'+' if rwl >= 0 else '-'}){abs(rwl):.3f}</td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td><td style='border:1px dotted #ccc; color:#aaa;'>0.00</td></tr>"

    prev_F = 0.0
    prev_cg = 0.0
    c_el = c_top
    first_block = True

    for idx, row in tiers_df.iterrows():
        h = float(row["높이 H(m)"])
        b_el = c_el - h

        if b_el >= rwl:
            c_el = b_el
            continue

        components = []
        top_el_for_block = min(c_el, rwl)
        height_for_block = top_el_for_block - b_el

        from_label = f"({'+' if rwl >= 0 else '-'}){abs(rwl):.3f}" if first_block else f"({'+' if c_el >= 0 else '-'}){abs(c_el):.3f}"
        from_arm = height_for_block + prev_cg
        from_M = prev_F * from_arm
        components.append({
            "type": "from", "label": "from", "label_val": from_label,
            "f": prev_F, "h": height_for_block, "add": prev_cg, "arm": from_arm, "m": from_M
        })
        first_block = False

        sum_f = prev_F
        sum_m = from_M

        tri_top = min(top_el_for_block, rwl)
        tri_bot = max(b_el, llw)
        if tri_top > tri_bot:
            p_top = g_w * (rwl - tri_top)
            p_bot = g_w * (rwl - tri_bot)
            h_tri = tri_top - tri_bot

            if p_top > 0.001:
                f_rect = p_top * h_tri
                arm_rect = h_tri / 2.0 + (tri_bot - b_el)
                m_rect = f_rect * arm_rect
                components.append(
                    {"type": "comp", "label": f"({'+' if tri_top >= 0 else '-'}){abs(tri_top):.3f}", "p": p_top,
                     "h": h_tri, "k": "1", "f": f_rect, "dist": h_tri, "k_arm": "1/2", "arm": arm_rect, "m": m_rect})
                sum_f += f_rect
                sum_m += m_rect

            if (p_bot - p_top) > 0.001:
                f_tri = (p_bot - p_top) * h_tri * 0.5
                arm_tri = h_tri / 3.0 + (tri_bot - b_el)
                m_tri = f_tri * arm_tri
                label = f"(±)0.000" if abs(tri_bot) < 0.001 else f"({'+' if tri_bot >= 0 else '-'}){abs(tri_bot):.3f}"
                components.append(
                    {"type": "comp", "label": label, "p": p_bot - p_top, "h": h_tri, "k": "1/2", "f": f_tri,
                     "dist": h_tri, "k_arm": "1/3", "arm": arm_tri, "m": m_tri})
                sum_f += f_tri
                sum_m += m_tri

        rect_top = min(top_el_for_block, llw)
        rect_bot = b_el
        if rect_top > rect_bot:
            h_rect = rect_top - rect_bot
            f_rect2 = max_pw * h_rect
            arm_rect2 = h_rect / 2.0
            m_rect2 = f_rect2 * arm_rect2
            label = f"({'+' if rect_bot >= 0 else '-'}){abs(rect_bot):.3f}"
            components.append(
                {"type": "comp", "label": label, "p": max_pw, "h": h_rect, "k": "1", "f": f_rect2, "dist": h_rect,
                 "k_arm": "1/2", "arm": arm_rect2, "m": m_rect2})
            sum_f += f_rect2
            sum_m += m_rect2

        prev_F = sum_f
        prev_cg = sum_m / sum_f if sum_f > 0 else 0
        components.append({"type": "sum", "f": sum_f, "arm": prev_cg, "m": sum_m})

        rowspan = len(components)
        first_row = True
        for comp in components:
            if first_row:
                html += f"<tr><td rowspan='{rowspan}' style='border:1px solid #ccc; font-weight:bold;'>({'+' if b_el >= 0 else '-'}){abs(b_el):.3f}</td>"
                first_row = False
            else:
                html += "<tr>"

            if comp["type"] == "from":
                html += f"<td style='border:1px dotted #ccc; color:#777;'>from</td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['label_val']}</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'></td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'>{comp['add']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc; font-weight:bold;'>{comp['m']:.2f}</td></tr>"

            elif comp["type"] == "comp":
                html += f"<td style='border:1px dotted #ccc;'>{comp['label']}</td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['p']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['h']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k']}</td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['f']:.2f}</td>"
                html += f"<td style='border:1px dotted #ccc;'>{comp['dist']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['k_arm']}</td><td style='border:1px dotted #ccc;'></td><td style='border:1px dotted #ccc;'>{comp['arm']:.2f}</td><td style='border:1px dotted #ccc;'>{comp['m']:.2f}</td></tr>"

            elif comp["type"] == "sum":
                html += f"<td colspan='4' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>계</td>"
                html += f"<td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['f']:.2f}</td>"
                html += f"<td colspan='3' style='border:1px solid #ccc; background:#fbfcfc;'></td>"
                html += f"<td style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{comp['arm']:.2f}</td>"
                html += f"<td style='border:1px solid #ccc; font-weight:bold; color:#1a73e8; background:#fbfcfc;'>{comp['m']:.2f}</td></tr>"

        c_el = b_el

    html += "</table></div>"
    return html


def generate_surcharge_html(tiers_df, q_val, c_top):
    html = "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px; margin-bottom: 25px;'>"
    html += "<tr style='background-color:#d9d9d9;'>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>구 분</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>기준점</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>P(kN) 산식</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>연직력 P(kN)</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>모멘트 Mᵥ(kN·m) 산식</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>모멘트 Mᵥ(kN·m)</th>"
    html += "<th style='border:1px solid #ccc; padding:8px;'>비고</th>"
    html += "</tr>"

    current_elev = c_top
    for idx, row in tiers_df.iterrows():
        h = float(row["높이 H(m)"])
        b = float(row["폭 B(m)"])
        bot_elev = current_elev - h
        is_last = (idx == len(tiers_df) - 1)

        if is_last:
            eff_b = b - 1.0
            p_val = q_val * eff_b
            arm = 1.0 + (eff_b / 2.0)
            arm_str = f"1.0 + {eff_b:.2f} / 2"
        else:
            eff_b = b
            p_val = q_val * eff_b
            arm = eff_b / 2.0
            arm_str = f"{eff_b:.2f} / 2"

        mv_val = p_val * arm

        sign_str = "+" if bot_elev >= 0 else "-"
        level_str = f"DL({sign_str}){abs(bot_elev):.2f}"

        html += "<tr>"
        html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px;'>항외측 TOE</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px;'>{q_val:.2f} × {eff_b:.2f}</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{p_val:.2f}</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px;'>{p_val:.2f} × ({arm_str})</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#1a73e8;'>{mv_val:.2f}</td>"
        html += f"<td style='border:1px solid #ccc; padding:6px;'></td>"
        html += "</tr>"

        current_elev = bot_elev

    html += "</table>"
    return html


# =====================================================================
# ★ 검토단면에 DL 검토높이 표기가 추가된 CASE별 하중집계 테이블 생성 함수
# =====================================================================

def generate_case_summary_table(case_title, case_key, tiers_details):
    html = f"<div style='margin-top: 15px;'><b>■ {case_title}</b></div>"
    html += "<table style='width:100%; border-collapse: collapse; font-size:12px; text-align:center; border: 2px solid #333; margin-top:5px; margin-bottom:15px;'>"
    html += "<tr style='background-color:#f4f6f8;'><th style='border:1px solid #ccc; padding:6px;'>검토단면</th><th style='border:1px solid #ccc; padding:6px;'>ΣV (kN) 산정근거 및 합계</th><th style='border:1px solid #ccc; padding:6px;'>ΣH (kN) 산정근거 및 합계</th><th style='border:1px solid #ccc; padding:6px;'>ΣMr (kN·m) 산정근거 및 합계</th><th style='border:1px solid #ccc; padding:6px;'>ΣMo (kN·m) 산정근거 및 합계</th></tr>"

    for t in tiers_details:
        v_val = t['V_' + case_key]
        h_val = t['H_' + case_key]
        mr_val = t['Mr_' + case_key]
        mo_val = t['Mo_' + case_key]

        # 평상시 CASE 분기
        if case_key == "1_1":
            v_str = f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"토압(상재無) {t['ph0_n']:.2f}"] if t['ph0_n'] > 0 else []
            if t['pw_n'] > 0: h_parts.append(f"잔류수압 {t['pw_n']:.2f}")
            if t['tr_f'] > 0: h_parts.append(f"견인력 {t['tr_f']:.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_str = f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"토압모멘트(無) {t['mh0_n']:.2f}"] if t['mh0_n'] > 0 else []
            if t['mw_n'] > 0: mo_parts.append(f"잔류수압모멘트 {t['mw_n']:.2f}")
            if t['tr_m'] > 0: mo_parts.append(f"견인력모멘트 {t['tr_m']:.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "1_2":
            v_str = f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"토압(상재有) {t['phq_n']:.2f}"] if t['phq_n'] > 0 else []
            if t['pw_n'] > 0: h_parts.append(f"잔류수압 {t['pw_n']:.2f}")
            if t['tr_f'] > 0: h_parts.append(f"견인력 {t['tr_f']:.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_str = f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"토압모멘트(有) {t['mhq_n']:.2f}"] if t['mhq_n'] > 0 else []
            if t['mw_n'] > 0: mo_parts.append(f"잔류수압모멘트 {t['mw_n']:.2f}")
            if t['tr_m'] > 0: mo_parts.append(f"견인력모멘트 {t['tr_m']:.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "1_3":
            v_parts = [f"자중 {t['sum_W_n']:.2f}"]
            if t['v_sq_n'] > 0: v_parts.append(f"상재연직 {t['v_sq_n']:.2f}")
            v_str = f"<b>{v_val:.2f}</b> (" + " + ".join(v_parts) + ")" if len(v_parts) > 1 else f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"토압(상재無) {t['ph0_n']:.2f}"] if t['ph0_n'] > 0 else []
            if t['pw_n'] > 0: h_parts.append(f"잔류수압 {t['pw_n']:.2f}")
            if t['tr_f'] > 0: h_parts.append(f"견인력 {t['tr_f']:.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_parts = [f"자중모멘트 {t['sum_W_x_n']:.2f}"]
            if t['mr_sq_n'] > 0: mr_parts.append(f"상재모멘트 {t['mr_sq_n']:.2f}")
            mr_str = f"<b>{mr_val:.2f}</b> (" + " + ".join(mr_parts) + ")" if len(mr_parts) > 1 else f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"토압모멘트(無) {t['mh0_n']:.2f}"] if t['mh0_n'] > 0 else []
            if t['mw_n'] > 0: mo_parts.append(f"잔류수압모멘트 {t['mw_n']:.2f}")
            if t['tr_m'] > 0: mo_parts.append(f"견인력모멘트 {t['tr_m']:.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "1_4":
            v_parts = [f"자중 {t['sum_W_n']:.2f}"]
            if t['v_sq_n'] > 0: v_parts.append(f"상재연직 {t['v_sq_n']:.2f}")
            v_str = f"<b>{v_val:.2f}</b> (" + " + ".join(v_parts) + ")" if len(v_parts) > 1 else f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"토압(상재有) {t['phq_n']:.2f}"] if t['phq_n'] > 0 else []
            if t['pw_n'] > 0: h_parts.append(f"잔류수압 {t['pw_n']:.2f}")
            if t['tr_f'] > 0: h_parts.append(f"견인력 {t['tr_f']:.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_parts = [f"자중모멘트 {t['sum_W_x_n']:.2f}"]
            if t['mr_sq_n'] > 0: mr_parts.append(f"상재모멘트 {t['mr_sq_n']:.2f}")
            mr_str = f"<b>{mr_val:.2f}</b> (" + " + ".join(mr_parts) + ")" if len(mr_parts) > 1 else f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"토압모멘트(有) {t['mhq_n']:.2f}"] if t['mhq_n'] > 0 else []
            if t['mw_n'] > 0: mo_parts.append(f"잔류수압모멘트 {t['mw_n']:.2f}")
            if t['tr_m'] > 0: mo_parts.append(f"견인력모멘트 {t['tr_m']:.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        # ★ 지진시 CASE 4개로 분기
        elif case_key == "2_1":
            v_str = f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"동토압(無) {t.get('ph0_s', 0.0):.2f}", f"관성력(제체) {t.get('eq_f', 0.0):.2f}"]
            if t.get('pw_n', 0.0) > 0: h_parts.append(f"잔류수압 {t.get('pw_n', 0.0):.2f}")
            if t.get('dw_f', 0.0) > 0: h_parts.append(f"동수압 {t.get('dw_f', 0.0):.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_str = f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"동토압모멘트(無) {t.get('mh0_s', 0.0):.2f}", f"관성모멘트(제체) {t.get('eq_m', 0.0):.2f}"]
            if t.get('mw_n', 0.0) > 0: mo_parts.append(f"잔류수압모멘트 {t.get('mw_n', 0.0):.2f}")
            if t.get('dw_m', 0.0) > 0: mo_parts.append(f"동수압모멘트 {t.get('dw_m', 0.0):.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "2_2":
            v_str = f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"동토압(有) {t.get('phq_s', 0.0):.2f}", f"관성력(제체) {t.get('eq_f', 0.0):.2f}"]
            if t.get('pw_n', 0.0) > 0: h_parts.append(f"잔류수압 {t.get('pw_n', 0.0):.2f}")
            if t.get('dw_f', 0.0) > 0: h_parts.append(f"동수압 {t.get('dw_f', 0.0):.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_str = f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"동토압모멘트(有) {t.get('mhq_s', 0.0):.2f}", f"관성모멘트(제체) {t.get('eq_m', 0.0):.2f}"]
            if t.get('mw_n', 0.0) > 0: mo_parts.append(f"잔류수압모멘트 {t.get('mw_n', 0.0):.2f}")
            if t.get('dw_m', 0.0) > 0: mo_parts.append(f"동수압모멘트 {t.get('dw_m', 0.0):.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "2_3":
            v_parts = [f"자중 {t['sum_W_n']:.2f}"]
            if t.get('v_sq_s', 0.0) > 0: v_parts.append(f"상재연직 {t.get('v_sq_s', 0.0):.2f}")
            v_str = f"<b>{v_val:.2f}</b> (" + " + ".join(v_parts) + ")" if len(v_parts) > 1 else f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"동토압(無) {t.get('ph0_s', 0.0):.2f}", f"관성력(제체) {t.get('eq_f', 0.0):.2f}"]
            if t.get('eq_f_sq', 0.0) > 0: h_parts.append(f"관성력(상재) {t.get('eq_f_sq', 0.0):.2f}")
            if t.get('pw_n', 0.0) > 0: h_parts.append(f"잔류수압 {t.get('pw_n', 0.0):.2f}")
            if t.get('dw_f', 0.0) > 0: h_parts.append(f"동수압 {t.get('dw_f', 0.0):.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_parts = [f"자중모멘트 {t['sum_W_x_n']:.2f}"]
            if t.get('mr_sq_s', 0.0) > 0: mr_parts.append(f"상재모멘트 {t.get('mr_sq_s', 0.0):.2f}")
            mr_str = f"<b>{mr_val:.2f}</b> (" + " + ".join(mr_parts) + ")" if len(mr_parts) > 1 else f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"동토압모멘트(無) {t.get('mh0_s', 0.0):.2f}", f"관성모멘트(제체) {t.get('eq_m', 0.0):.2f}"]
            if t.get('eq_m_sq', 0.0) > 0: mo_parts.append(f"관성모멘트(상재) {t.get('eq_m_sq', 0.0):.2f}")
            if t.get('mw_n', 0.0) > 0: mo_parts.append(f"잔류수압모멘트 {t.get('mw_n', 0.0):.2f}")
            if t.get('dw_m', 0.0) > 0: mo_parts.append(f"동수압모멘트 {t.get('dw_m', 0.0):.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        elif case_key == "2_4":
            v_parts = [f"자중 {t['sum_W_n']:.2f}"]
            if t.get('v_sq_s', 0.0) > 0: v_parts.append(f"상재연직 {t.get('v_sq_s', 0.0):.2f}")
            v_str = f"<b>{v_val:.2f}</b> (" + " + ".join(v_parts) + ")" if len(v_parts) > 1 else f"<b>{v_val:.2f}</b> (자중)"
            h_parts = [f"동토압(有) {t.get('phq_s', 0.0):.2f}", f"관성력(제체) {t.get('eq_f', 0.0):.2f}"]
            if t.get('eq_f_sq', 0.0) > 0: h_parts.append(f"관성력(상재) {t.get('eq_f_sq', 0.0):.2f}")
            if t.get('pw_n', 0.0) > 0: h_parts.append(f"잔류수압 {t.get('pw_n', 0.0):.2f}")
            if t.get('dw_f', 0.0) > 0: h_parts.append(f"동수압 {t.get('dw_f', 0.0):.2f}")
            h_str = f"<b>{h_val:.2f}</b> (" + " + ".join(h_parts) + ")"
            mr_parts = [f"자중모멘트 {t['sum_W_x_n']:.2f}"]
            if t.get('mr_sq_s', 0.0) > 0: mr_parts.append(f"상재모멘트 {t.get('mr_sq_s', 0.0):.2f}")
            mr_str = f"<b>{mr_val:.2f}</b> (" + " + ".join(mr_parts) + ")" if len(mr_parts) > 1 else f"<b>{mr_val:.2f}</b> (자중모멘트)"
            mo_parts = [f"동토압모멘트(有) {t.get('mhq_s', 0.0):.2f}", f"관성모멘트(제체) {t.get('eq_m', 0.0):.2f}"]
            if t.get('eq_m_sq', 0.0) > 0: mo_parts.append(f"관성모멘트(상재) {t.get('eq_m_sq', 0.0):.2f}")
            if t.get('mw_n', 0.0) > 0: mo_parts.append(f"잔류수압모멘트 {t.get('mw_n', 0.0):.2f}")
            if t.get('dw_m', 0.0) > 0: mo_parts.append(f"동수압모멘트 {t.get('dw_m', 0.0):.2f}")
            mo_str = f"<b>{mo_val:.2f}</b> (" + " + ".join(mo_parts) + ")"

        bot_el = t['bot_el']
        sign_str = "+" if bot_el >= 0 else "-"
        tier_display_name = f"{t['name']}<br><span style='font-weight:normal; font-size:11px; color:#333;'>(DL({sign_str}){abs(bot_el):.2f})</span>"

        html += f"<tr><td style='border:1px solid #ccc; font-weight:bold;'>{tier_display_name}</td>"
        html += f"<td style='border:1px solid #ccc; text-align:left; padding-left:10px;'>{v_str}</td>"
        html += f"<td style='border:1px solid #ccc; text-align:left; padding-left:10px;'>{h_str}</td>"
        html += f"<td style='border:1px solid #ccc; text-align:left; padding-left:10px;'>{mr_str}</td>"
        html += f"<td style='border:1px solid #ccc; text-align:left; padding-left:10px;'>{mo_str}</td></tr>"

    return html + "</table>"

def generate_sliding_table(cases_info, tiers_details, fs_allow=1.2, mu_cc=0.5, mu_cb=0.6):
    html = "<div style='margin-top: 15px;'><b>■ 활동 안정 검토</b></div>"
    html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px; margin-top:5px; margin-bottom:20px;'>"
    html += "<tr style='background-color:#d9d9d9;'><th colspan='2' style='border:1px solid #ccc; padding:6px;'>구 분</th><th style='border:1px solid #ccc;'>ΣV (kN)</th><th style='border:1px solid #ccc;'>ΣH (kN)</th><th style='border:1px solid #ccc;'>μ</th><th style='border:1px solid #ccc;'>Fs</th><th style='border:1px solid #ccc;'>S.F</th><th style='border:1px solid #ccc;'>판정</th><th style='border:1px solid #ccc;'>비고</th></tr>"

    for c_label, c_key in cases_info:
        rowspan = len(tiers_details)
        first_row = True
        for idx, t in enumerate(tiers_details):
            v_val = t['V_' + c_key]
            h_val = t['H_' + c_key]

            # ★ 최하단(사석과 접하는 면)은 0.6, 나머지는 콘크리트 상호간 0.5 적용
            current_mu = mu_cb if idx == len(tiers_details) - 1 else mu_cc

            fs_val = (v_val * current_mu) / h_val if h_val > 0 else 99.9
            is_ok = "O.K" if fs_val >= fs_allow else "N.G"
            col_ok = "blue" if is_ok == "O.K" else "red"

            level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"

            html += "<tr>"
            if first_row:
                display_label = f"CASE {c_key.replace('_', '-')}"
                html += f"<td rowspan='{rowspan}' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{display_label}</td>"
                first_row = False

            html += f"<td style='border:1px dotted #ccc;'>{level_str}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{v_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{h_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc; color:red; font-weight:bold;'>{current_mu:.1f}</td>"
            html += f"<td style='border:1px dotted #ccc; font-weight:bold;'>{fs_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{fs_allow:.1f}</td>"
            html += f"<td style='border:1px dotted #ccc; font-weight:bold; color:{col_ok};'>{is_ok}</td>"
            html += "<td style='border:1px dotted #ccc;'></td></tr>"

    return html + "</table>"

def generate_overturning_table(cases_info, tiers_details, fs_allow=1.2):
    html = "<div style='margin-top: 15px;'><b>■ 전도 안정 검토</b></div>"
    html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px; margin-top:5px; margin-bottom:20px;'>"
    html += "<tr style='background-color:#d9d9d9;'><th colspan='2' style='border:1px solid #ccc; padding:6px;'>구 분</th><th style='border:1px solid #ccc;'>ΣMv (kN·m)</th><th style='border:1px solid #ccc;'>ΣMh (kN·m)</th><th style='border:1px solid #ccc;'>Fs</th><th style='border:1px solid #ccc;'>S.F</th><th style='border:1px solid #ccc;'>판정</th><th style='border:1px solid #ccc;'>비고</th></tr>"

    for c_label, c_key in cases_info:
        rowspan = len(tiers_details)
        first_row = True
        for t in tiers_details:
            mr_val = t['Mr_' + c_key]
            mo_val = t['Mo_' + c_key]
            fs_val = mr_val / mo_val if mo_val > 0 else 99.9
            is_ok = "O.K" if fs_val >= fs_allow else "N.G"
            col_ok = "blue" if is_ok == "O.K" else "red"

            level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"

            html += "<tr>"
            if first_row:
                display_label = f"CASE {c_key.replace('_', '-')}"
                html += f"<td rowspan='{rowspan}' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{display_label}</td>"
                first_row = False

            html += f"<td style='border:1px dotted #ccc;'>{level_str}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{mr_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{mo_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc; font-weight:bold;'>{fs_val:.2f}</td>"
            html += f"<td style='border:1px dotted #ccc;'>{fs_allow:.1f}</td>"
            html += f"<td style='border:1px dotted #ccc; font-weight:bold; color:{col_ok};'>{is_ok}</td>"
            html += "<td style='border:1px dotted #ccc;'></td></tr>"

    return html + "</table>"


# =====================================================================
# ★ 지지력 검토 표 생성 함수 (활동Fs, 전도Fs 항목 삭제 반영)
# =====================================================================
def generate_bearing_table(cases_info, target_tier, qa_allow=500.0, mu=0.6):
    html = "<div style='margin-top: 15px;'><b>■ 지지력 검토</b></div>"
    html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px; margin-top:5px; margin-bottom:20px;'>"
    html += "<tr style='background-color:#d9d9d9;'><th rowspan='2' colspan='2' style='border:1px solid #ccc; padding:6px;'>구 분</th><th colspan='" + str(
        len(cases_info)) + "' style='border:1px solid #ccc;'>평상시</th><th rowspan='2' style='border:1px solid #ccc;'>비 고</th></tr>"
    html += "<tr style='background-color:#d9d9d9;'>"
    for _, c_key in cases_info:
        display_label = f"CASE {c_key.replace('_', '-')}"
        html += f"<th style='border:1px solid #ccc; padding:4px;'>{display_label}</th>"
    html += "</tr>"

    b = target_tier['b']

    # ★ 표에 출력될 행(Row) 정의에서 '활동Fs', '전도Fs' 2줄 삭제
    rows_def = [
        ("Mv(kN·m)", "Mr_", "{:.2f}", "저항모멘트의 합"),
        ("Mh(kN·m)", "Mo_", "{:.2f}", "전도모멘트의 합"),
        ("V(kN)", "V_", "{:.2f}", "연직력의 합"),
        ("H(kN)", "H_", "{:.2f}", "수평력의 합"),
        ("x (m)", "calc_x", "{:.2f}", ""),
        ("B (m)", "const_b", "{:.2f}", "제체의 폭"),
        ("e (m)", "calc_e", "{:.2f}", "전합력의 편심량"),
        ("B/6 (m)", "const_b6", "{:.2f}", ""),
        ("지지력 분포", "calc_dist", "{}", ""),
        ("B' (m)", "calc_b_prime", "{:.2f}", "분포폭"),
        ("q max(kN/m²)", "calc_qmax", "{:.2f}", "사석기초"),
        ("q min(kN/m²)", "calc_qmin", "{:.2f}", "사석기초"),
    ]

    for label, key_type, fmt, remark in rows_def:
        html += f"<tr><td colspan='2' style='border:1px solid #ccc; font-weight:bold; background:#fbfcfc;'>{label}</td>"
        for _, c_key in cases_info:
            v_val = target_tier['V_' + c_key]
            h_val = target_tier['H_' + c_key]
            mr_val = target_tier['Mr_' + c_key]
            mo_val = target_tier['Mo_' + c_key]

            x_val = (mr_val - mo_val) / v_val if v_val > 0 else 0.0
            e_val = (b / 2.0) - x_val
            b6_val = b / 6.0

            if abs(e_val) <= b6_val:
                dist_str = "사다리꼴"
                b_prime = b
                qmax = (v_val / b) * (1.0 + (6.0 * e_val / b))
                qmin = (v_val / b) * (1.0 - (6.0 * e_val / b))
            else:
                dist_str = "삼각형"
                b_prime = 3.0 * x_val
                qmax = (2.0 * v_val) / b_prime if b_prime > 0 else 0.0
                qmin = 0.0

            if key_type == "Mr_":
                val_out = fmt.format(mr_val)
            elif key_type == "Mo_":
                val_out = fmt.format(mo_val)
            elif key_type == "V_":
                val_out = fmt.format(v_val)
            elif key_type == "H_":
                val_out = fmt.format(h_val)
            elif key_type == "calc_x":
                val_out = fmt.format(x_val)
            elif key_type == "const_b":
                val_out = fmt.format(b)
            elif key_type == "calc_e":
                val_out = fmt.format(e_val)
            elif key_type == "const_b6":
                val_out = fmt.format(b6_val)
            elif key_type == "calc_dist":
                val_out = dist_str
            elif key_type == "calc_b_prime":
                val_out = fmt.format(b_prime)
            elif key_type == "calc_qmax":
                val_out = fmt.format(qmax)
            elif key_type == "calc_qmin":
                val_out = fmt.format(qmin)

            html += f"<td style='border:1px solid #ccc;'>{val_out}</td>"
        html += f"<td style='border:1px solid #ccc; color:#555;'>{remark}</td></tr>"

    return html + "</table>"


def generate_formula_html():
    def get_formula_img(type_idx):
        fig, ax = plt.subplots(figsize=(2.5, 1.2))
        if type_idx == 1:
            ax.plot([0, 1], [0, 0], 'k-', lw=2)
            ax.add_patch(patches.Rectangle((0.3, 0), 0.4, 0.6, fill=False, lw=1.5))
            ax.annotate("", xy=(0.5, 0), xytext=(0.5, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
            ax.text(0.5, 0.55, "ΣV", ha='center', va='bottom', fontweight='bold')
            ax.annotate("", xy=(0.3, 0.3), xytext=(0.1, 0.3), arrowprops=dict(arrowstyle="->", lw=1.5))
            ax.text(0.05, 0.3, "ΣH", ha='right', va='center', fontweight='bold')
        elif type_idx == 2:
            ax.plot([0, 1], [0, 0], 'k-', lw=2)
            ax.add_patch(patches.Rectangle((0.3, 0), 0.4, 0.6, fill=False, lw=1.5))
            ax.annotate("", xy=(0.3, 0), xytext=(0.2, 0.3), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.5", lw=1.5))
            ax.text(0.15, 0.35, "ΣMv", ha='center', fontweight='bold')
            ax.annotate("", xy=(0.7, 0), xytext=(0.8, 0.3), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.5", lw=1.5))
            ax.text(0.85, 0.35, "ΣMh", ha='center', fontweight='bold')
        elif type_idx == 3:
            ax.plot([0, 1], [0.8, 0.8], 'k-', lw=1.5)
            ax.add_patch(patches.Polygon([[0.1, 0.8], [0.9, 0.8], [0.9, 0.5], [0.1, 0.6]], fill=True, facecolor='#f0f4f8', edgecolor='black'))
            ax.text(0.5, 0.9, "e ≤ B/6", ha='center', fontsize=9)
            ax.plot([0, 1], [0.3, 0.3], 'k-', lw=1.5)
            ax.add_patch(patches.Polygon([[0.1, 0.3], [0.7, 0.3], [0.7, 0.0]], fill=True, facecolor='#f0f4f8', edgecolor='black'))
            ax.text(0.5, 0.4, "e > B/6", ha='center', fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.1, 1)
        ax.axis('off')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"

    html = "<div style='display: flex; flex-direction: row; gap: 15px; margin-bottom: 25px; align-items: stretch;'>"

    html += "<div style='flex: 1; border: 1px solid #333; background: #fff; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;'>"
    html += "<div>"
    html += "<b style='font-size: 14px; color: #2c3e50;'>- 활동에 대한 안전율</b><br><br>"
    html += "<div style='font-size: 14px; font-weight: bold;'><i>Fs</i> = ( ΣV / ΣH ) × μ</div><br>"
    html += "<div style='font-size: 12px; line-height: 1.5; color: #444;'>"
    html += "<b>ΣV</b> : 연직력 합 (kN)<br>"
    html += "<b>ΣH</b> : 수평력 합 (kN)<br>"
    html += "<b>μ</b> : 마찰계수"
    html += "</div></div>"
    html += f"<div style='text-align: center; margin-top: 15px;'><img src='{get_formula_img(1)}' style='border:1px solid #eee; max-width:180px;'></div></div>"

    html += "<div style='flex: 1; border: 1px solid #333; background: #fff; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;'>"
    html += "<div>"
    html += "<b style='font-size: 14px; color: #2c3e50;'>- 전도에 대한 안전율</b><br><br>"
    html += "<div style='font-size: 14px; font-weight: bold;'><i>Fs</i> = ΣMv / ΣMh</div><br>"
    html += "<div style='font-size: 12px; line-height: 1.5; color: #444;'>"
    html += "<b>ΣMv</b> : 연직력에 의한 모멘트 합 (kN·m)<br>"
    html += "<b>ΣMh</b> : 수평력에 의한 모멘트 합 (kN·m)"
    html += "</div></div>"
    html += f"<div style='text-align: center; margin-top: 15px;'><img src='{get_formula_img(2)}' style='border:1px solid #eee; max-width:180px;'></div></div>"

    html += "<div style='flex: 1.3; border: 1px solid #333; background: #fff; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;'>"
    html += "<div>"
    html += "<b style='font-size: 14px; color: #2c3e50;'>- 사석마운드 지지력 검토</b><br><br>"
    html += "<div style='font-size: 12px; line-height: 1.5; color: #444;'>"
    html += "<i>x</i> = ( ΣMv - ΣMh ) / ΣV , &nbsp;&nbsp; <i>e</i> = B/2 - <i>x</i><br>"
    html += "<i>q<sub>max / min</sub></i> = ( ΣV / B ) · ( 1 ± 6<i>e</i> / B )<br><br>"
    html += "· <i>e</i> ≤ B/6 의 경우 : 사다리꼴 분포<br>"
    html += "· <i>e</i> &gt; B/6 의 경우 : 삼각형 분포 (B' = 3<i>x</i>, <i>q<sub>max</sub></i> = 2ΣV / B')<br><br>"
    html += "<b>ΣV</b> : 연직력 합 (kN), &nbsp;<b>B</b> : 저판의 폭 (m), &nbsp;<b>e</b> : 전합력의 편심량 (m)"
    html += "</div></div>"
    html += f"<div style='text-align: center; margin-top: 15px;'><img src='{get_formula_img(3)}' style='border:1px solid #eee; max-width:220px;'></div></div>"

    html += "</div>"
    return html


# =====================================================================
# ★ 6. 출력부
# =====================================================================

o_title("안정검토 결과 요약", level=1)

is_eq_mode = ("지진시" in calc_mode)
if is_eq_mode:
    cases_summary_list = [("CASE 2-1", "2_1"), ("CASE 2-2", "2_2"), ("CASE 2-3", "2_3"), ("CASE 2-4", "2_4")]
else:
    cases_summary_list = [("CASE 1-1", "1_1"), ("CASE 1-2", "1_2"), ("CASE 1-3", "1_3"), ("CASE 1-4", "1_4")]

mu_cc = 0.5  # 콘크리트 상호간 마찰계수
mu_cb = 0.6  # 콘크리트-사석 마찰계수

min_sl = 999.0; min_sl_case = ""; min_sl_tier = ""
min_ot = 999.0; min_ot_case = ""; min_ot_tier = ""
max_q = 0.0; max_q_case = ""; max_q_tier = ""

for c_label, c_key in cases_summary_list:
    formatted_case_name = f"CASE {c_key.replace('_', '-')}"

    for idx, t in enumerate(tier_details):
        v_v = t['V_' + c_key]
        h_v = t['H_' + c_key]
        mr_v = t['Mr_' + c_key]
        mo_v = t['Mo_' + c_key]
        b_w = t['b']

        # ★ 최하단 여부에 따라 마찰계수 차등 적용
        current_mu = mu_cb if idx == len(tier_details) - 1 else mu_cc

        sl_v = (v_v * current_mu) / h_v if h_v > 0 else 99.9
        ot_v = mr_v / mo_v if mo_v > 0 else 99.9

        x_v = (mr_v - mo_v) / v_v if v_v > 0 else 0.0
        e_v = (b_w / 2.0) - x_v
        if abs(e_v) <= b_w / 6.0:
            q_v = (v_v / b_w) * (1.0 + (6.0 * e_v / b_w))
        else:
            b_p = 3.0 * x_v
            q_v = (2.0 * v_v) / b_p if b_p > 0 else 0.0

        if sl_v < min_sl:
            min_sl = sl_v
            min_sl_case = f"{formatted_case_name} ({t['name']})"
        if ot_v < min_ot:
            min_ot = ot_v
            min_ot_case = f"{formatted_case_name} ({t['name']})"
        if q_v > max_q:
            max_q = q_v
            max_q_case = f"{formatted_case_name} ({t['name']})"

allow_fs = 1.0 if is_eq_mode else 1.2
allow_qa = qa_s if is_eq_mode else qa_n

summary_html = f"""
<div style='margin-bottom: 25px;'>
<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:13px;'>
<tr style='background-color:#d9d9d9;'>
   <th style='border:1px solid #ccc; padding:8px;'>검토 항목</th>
   <th style='border:1px solid #ccc; padding:8px;'>계산값 (최소/최대)</th>
   <th style='border:1px solid #ccc; padding:8px;'>허용기준</th>
   <th style='border:1px solid #ccc; padding:8px;'>판정</th>
   <th style='border:1px solid #ccc; padding:8px;'>비고 (최소안전율/최대반력 발생 CASE)</th>
</tr>
<tr>
   <td style='border:1px solid #ccc; font-weight:bold;'>활동에 대한 안전율</td>
   <td style='border:1px solid #ccc; font-weight:bold;'>{min_sl:.2f}</td>
   <td style='border:1px solid #ccc;'>≥ {allow_fs:.1f}</td>
   <td style='border:1px solid #ccc; color:blue; font-weight:bold;'>{'O.K' if min_sl >= allow_fs else 'N.G'}</td>
   <td style='border:1px solid #ccc;'>{min_sl_case}</td>
</tr>
<tr>
   <td style='border:1px solid #ccc; font-weight:bold;'>전도에 대한 안전율</td>
   <td style='border:1px solid #ccc; font-weight:bold;'>{min_ot:.2f}</td>
   <td style='border:1px solid #ccc;'>≥ {allow_fs:.1f}</td>
   <td style='border:1px solid #ccc; color:blue; font-weight:bold;'>{'O.K' if min_ot >= allow_fs else 'N.G'}</td>
   <td style='border:1px solid #ccc;'>{min_ot_case}</td>
</tr>
<tr>
   <td style='border:1px solid #ccc; font-weight:bold;'>사석마운드 지반반력</td>
   <td style='border:1px solid #ccc; font-weight:bold;'>{max_q:.2f} kPa</td>
   <td style='border:1px solid #ccc;'>≤ {allow_qa:.1f} kPa</td>
   <td style='border:1px solid #ccc; color:blue; font-weight:bold;'>{'O.K' if max_q <= allow_qa else 'N.G'}</td>
   <td style='border:1px solid #ccc;'>{max_q_case}</td>
</tr>
</table>
</div>
"""
o_html(summary_html)

o_title("1. 설계조건", level=1)
design_cond_html = f"""
<div style='background:#fbfcfc; padding:15px; border: 1px solid #ccc; border-radius:5px; font-size:14px;'>
<table style='width:100%; border-collapse: collapse; text-align:center; border: 1px solid #ccc; background:#fff;'>
<tr style='background-color: #e8f0fe; color:#1a73e8;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>1) 설계조위</th></tr>
<tr><td style='border: 1px solid #ccc; padding: 6px; width:33%; font-weight:bold;'>평상시 H.W.L</td><td colspan='2' style='border: 1px solid #ccc;'>{hwl_n:.3f} m</td></tr>
<tr><td style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>L.L.W</td><td colspan='2' style='border: 1px solid #ccc;'>{llw:.3f} m</td></tr>
<tr><td style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>평상 잔류수위</td><td colspan='2' style='border: 1px solid #ccc;'>{rwl_n:.3f} m</td></tr>

<tr style='background-color: #e8f0fe; color:#1a73e8;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>2) 재료조건</th></tr>
<tr>
      <td rowspan='3' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>단위중량 (kN/m³)</td>
      <td style='border: 1px solid #ccc;'>무근Con</td>
      <td style='border: 1px solid #ccc;'>수상 {g_c_wet} / 수중 {g_c_sub} / 관성력용 {g_c_eq}</td>
</tr>
<tr>
      <td style='border: 1px solid #ccc;'>사석</td>
      <td style='border: 1px solid #ccc;'>수상 {g_s_wet} / 수중 {g_s_sub} / 포화 {g_s_sat}</td>
</tr>
<tr>
      <td style='border: 1px solid #ccc;'>해수 단위중량</td>
      <td style='border: 1px solid #ccc;'>{g_w} kN/m³</td>
</tr>
<tr>
      <td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>뒷채움재 내부마찰각(Φ)</td>
      <td style='border: 1px solid #ccc;'>{phi}°</td>
</tr>
<tr>
      <td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>흙과 벽면의 마찰각(δ)</td>
      <td style='border: 1px solid #ccc;'>{delta}°</td>
</tr>
<tr>
      <td rowspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>마찰계수(μ)</td>
      <td style='border: 1px solid #ccc; padding: 6px;'>콘크리트 상호간</td>
      <td style='border: 1px solid #ccc;'>0.5</td>
</tr>
<tr>
      <td style='border: 1px solid #ccc; padding: 6px;'>콘크리트와 사석간</td>
      <td style='border: 1px solid #ccc;'>0.6</td>
</tr>

<tr style='background-color: #e8f0fe; color:#1a73e8;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>3) 하중조건</th></tr>
<tr><td rowspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>상재하중 (kPa)</td><td style='border: 1px solid #ccc;'>평상시</td><td style='border: 1px solid #ccc;'>{q_n}</td></tr>
<tr><td style='border: 1px solid #ccc;'>지진시</td><td style='border: 1px solid #ccc;'>{q_s}</td></tr>
<tr><td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>견인력 (kN)</td><td style='border: 1px solid #ccc;'>{mooring_t}</td></tr>
<tr style='background-color: #e8f0fe; color:#1a73e8;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>4) 내진조건</th></tr>
<tr><td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>설계수평지진계수 (Kh)</td><td style='border: 1px solid #ccc;'>{kh:.3f}</td></tr>

<tr style='background-color: #e8f0fe; color:#1a73e8;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>5) 사용하중조합</th></tr>
<tr><td rowspan='4' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>평상시</td><td style='border: 1px solid #ccc;'>CASE 1-1</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 토압(상재하중無) + 잔류수압 + 견인력</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 1-2</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 토압(상재하중有) + 잔류수압 + 견인력</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 1-3</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 상재하중 + 토압(상재하중無) + 잔류수압 + 견인력</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 1-4</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 상재하중 + 토압(상재하중有) + 잔류수압 + 견인력</td></tr>

<tr><td rowspan='4' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>지진시</td><td style='border: 1px solid #ccc;'>CASE 2-1</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 동토압(상재無) + 잔류수압 + 관성력(제체) + 동수압</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 2-2</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 동토압(상재有) + 잔류수압 + 관성력(제체) + 동수압</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 2-3</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 상재하중 + 동토압(상재無) + 잔류수압 + 관성력(제체+상재) + 동수압</td></tr>
<tr><td style='border: 1px solid #ccc;'>CASE 2-4</td><td style='border: 1px solid #ccc; text-align:left; padding-left:15px;'>자중 + 상재하중 + 동토압(상재有) + 잔류수압 + 관성력(제체+상재) + 동수압</td></tr>
<tr style='background-color: #fdf2e9; color:#e67e22;'><th colspan='3' style='border: 1px solid #ccc; padding: 8px;'>6) 허용안전율 및 허용지지력</th></tr>
<tr><td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>평상시</td><td style='border: 1px solid #ccc;'>활동 ≥ 1.2, 전도 ≥ 1.2, 허용지지력 ≤ {qa_n} kPa</td></tr>
<tr><td colspan='2' style='border: 1px solid #ccc; padding: 6px; font-weight:bold;'>지진시</td><td style='border: 1px solid #ccc;'>활동 ≥ 1.0, 전도 ≥ 1.0, 허용지지력 ≤ {qa_s} kPa</td></tr>
</table>
</div>
"""
o_html(design_cond_html)

if "평상시" in calc_mode:
    o_title("2. 하중 산정 모식도", level=1)
    o_html(draw_schematic(edited_tiers, c_top, hwl_n, rwl_n, llw))

    o_title("3. 제체 자중 산정표", level=1)
    o_html(
        f"<table style='width:100%; border-collapse: collapse; font-size:13px; text-align:center; border: 2px solid #333;'><tr style='background-color: #f4f6f8;'><th>구분 (단면)</th><th>상세 구분</th><th>연직력 V (kN)</th><th>팔길이 x (m)</th><th>모멘트 Mv (kN·m)</th></tr>{html_table_rows}</table>")

    o_title("4. 잔류수압", level=1)
    o_html(generate_water_pressure_html(edited_tiers, hwl_n, llw, rwl_n, c_top, g_w))

    o_title("5. 상재하중 (연직력 작용)", level=1)
    o_html(generate_surcharge_html(edited_tiers, q_n, c_top))

    o_title("6. 평상시 토압 상세", level=1)
    ka_n = math.tan(math.radians(45 - phi / 2)) ** 2
    o_latex(fr"K_a = \tan^2\left(45^\circ - \frac{{\Phi}}{{2}}\right) = \mathbf{{{ka_n:.4f}}}")
    o_html(generate_earth_pressure_html(edited_tiers, ka_n, 0.0, rwl_n, c_top, g_s_wet, g_s_sub, "상재하중 미고려", "#7f8c8d"))
    o_html(generate_earth_pressure_html(edited_tiers, ka_n, q_n, rwl_n, c_top, g_s_wet, g_s_sub, "상재하중 고려", "#1f77b4"))

    o_title("7. 견인력", level=1)
    o_html(f"""
    <div style='margin-bottom: 25px;'>
        <h3 style='color:#1a73e8; font-size:1.1em; margin-bottom:5px;'>1) 견인력 산정</h3>
        <div style='background:#fdfefe; padding:10px; border:1px solid #ccc; font-size:13px;'>
           P<sub>k</sub> = {mooring_t:.2f} kN / {mooring_interval:.2f} m = <b>{mooring_t / mooring_interval:.2f} kN/m</b>
        </div>
    </div>
    """)

    h_tr = "<div style='margin-bottom: 25px;'><h3 style='color:#1a73e8; font-size:1.1em; margin-bottom:5px;'>2) 견인력에 의한 수평력</h3>"
    h_tr += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:12px;'>"
    h_tr += "<tr style='background-color:#d9d9d9;'>"
    h_tr += "<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>구 분</th>"
    h_tr += "<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>견인력Pk(kN)<br>수평력</th>"
    h_tr += "<th colspan='4' style='border:1px dotted #ccc; border-bottom:1px dotted #ccc;'>팔길이y(m)</th>"
    h_tr += "<th rowspan='2' style='border:1px dotted #ccc; border-bottom:1px solid #333;'>모멘트<br>Mh(kN·m)</th>"
    h_tr += "</tr>"
    h_tr += "<tr style='background-color:#d9d9d9;'>"
    h_tr += "<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>거리</th>"
    h_tr += "<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>종류</th>"
    h_tr += "<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>추가</th>"
    h_tr += "<th style='border:1px dotted #ccc; border-bottom:1px solid #333;'>팔길이</th>"
    h_tr += "</tr>"

    for t in tier_details:
        level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"
        dist_val = (c_top - t['bot_el'])
        arm_val = dist_val + mooring_h
        m_val = t['tr_f'] * arm_val

        h_tr += "<tr>"
        h_tr += f"<td style='border:1px solid #ccc; font-weight:bold;'>{level_str}</td>"
        h_tr += f"<td style='border:1px dotted #ccc;'>{t['tr_f']:.2f}</td>"
        h_tr += f"<td style='border:1px dotted #ccc;'>{dist_val:.2f}</td>"
        h_tr += f"<td style='border:1px dotted #ccc;'>+</td>"
        h_tr += f"<td style='border:1px dotted #ccc; color:red;'>{mooring_h:.2f}</td>"
        h_tr += f"<td style='border:1px dotted #ccc; font-weight:bold;'>{arm_val:.2f}</td>"
        h_tr += f"<td style='border:1px dotted #ccc; font-weight:bold; color:#1a73e8;'>{m_val:.2f}</td>"
        h_tr += "</tr>"

    h_tr += "</table></div>"
    o_html(h_tr)

    o_title("8. 평상시 하중집계 및 안정검토 (CASE별)", level=1)

    o_title("가. CASE별 하중조합", level=2)
    # 이미지와 똑같은 형태의 하중조합 행렬(Matrix) 표 삽입
    case_matrix_html = """
        <table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:13px; margin-bottom: 25px;'>
            <tr style='background-color:#d5e8f5;'>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>구 분</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>자중</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>상재하중</th>
                <th colspan='2' style='border:1px solid #333; padding:8px;'>토압</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>잔류수압</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>견인력</th>
            </tr>
            <tr style='background-color:#d5e8f5;'>
                <th style='border:1px solid #333; padding:8px;'>상재하중無</th>
                <th style='border:1px solid #333; padding:8px;'>상재하중有</th>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 1</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 2</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 3</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 4</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
        </table>
        """
    o_html(case_matrix_html)

    o_title("나. CASE별 하중집계", level=2)
    o_html(generate_case_summary_table("CASE 1 (자중+토압(無)+잔류+견인) 하중집계", "1_1", tier_details))
    o_html(generate_case_summary_table("CASE 2 (자중+토압(有)+잔류+견인) 하중집계", "1_2", tier_details))
    o_html(generate_case_summary_table("CASE 3 (자중+상재+토압(無)+잔류+견인) 하중집계", "1_3", tier_details))
    o_html(generate_case_summary_table("CASE 4 (자중+상재+토압(有)+잔류+견인) 하중집계", "1_4", tier_details))

    o_title("다. 안정검토", level=2)
    o_title("1) 안정검토 공식", level=3)
    o_html(generate_formula_html())

    o_title("2) 안정검토 결과", level=3)
    # 평상시 CASE 검토를 4개로 확장
    cases_list = [
        ("CASE 1", "1_1"),
        ("CASE 2", "1_2"),
        ("CASE 3", "1_3"),
        ("CASE 4", "1_4")
    ]

    o_html(generate_sliding_table(cases_list, tier_details, fs_allow=1.2, mu_cc=0.5, mu_cb=0.6))
    o_html(generate_overturning_table(cases_list, tier_details, fs_allow=1.2))

    bottom_tier_detail = tier_details[-1]
    o_html(generate_bearing_table(cases_list, bottom_tier_detail, qa_allow=qa_n, mu=0.6))

else:
    o_title("2. 하중 산정 모식도", level=1)
    o_html(draw_schematic(edited_tiers, c_top, hwl_n, rwl_n, llw))

    o_title("3. 제체 자중 산정표", level=1)
    o_html(
        f"<table style='width:100%; border-collapse: collapse; font-size:13px; text-align:center; border: 2px solid #333;'><tr style='background-color: #f4f6f8;'><th>구분 (단면)</th><th>상세 구분</th><th>연직력 V (kN)</th><th>팔길이 x (m)</th><th>모멘트 Mv (kN·m)</th></tr>{html_table_rows}</table>")

    o_title("4. 잔류수압", level=1)
    o_html(generate_water_pressure_html(edited_tiers, hwl_n, llw, rwl_n, c_top, g_w))

    o_title("5. 상재하중 (연직력 작용)", level=1)
    o_html(generate_surcharge_html(edited_tiers, q_s, c_top))

    o_title("6. 지진시 동토압 상세", level=1)

    o_title("1) 상재하중이 없는 경우", level=2)
    o_html(generate_earth_pressure_html(
        tiers_df=edited_tiers, ka=ka_n, q_val=0.0, rwl=rwl_n, c_top=c_top,
        g_wet=g_s_wet, g_sub=g_s_sub, title_text="지진시 주동토압 (상재하중 미고려)",
        title_color="#7f8c8d", is_eq=True, kh=kh, phi=phi, delta=delta, omega=q_s
    ))

    if q_s > 0.0:
        o_title("2) 상재하중이 있는 경우", level=2)
        o_html(generate_earth_pressure_html(
            tiers_df=edited_tiers, ka=ka_n, q_val=q_s, rwl=rwl_n, c_top=c_top,
            g_wet=g_s_wet, g_sub=g_s_sub, title_text="지진시 주동토압 (상재하중 고려)",
            title_color="#e67e22", is_eq=True, kh=kh, phi=phi, delta=delta, omega=q_s
        ))

    o_title("7. 제체 관성력 산정표", level=1)
    o_html(f"<div style='font-size:12px; font-weight:bold; margin-bottom:5px;'>- 제체 질량 및 수평모멘트 산정 (부력 미고려)</div>")
    o_html(
        f"<table style='width:100%; border-collapse: collapse; font-size:13px; text-align:center; border: 2px solid #333; margin-bottom:20px;'><tr style='background-color: #f4f6f8;'><th>구분 (단면)</th><th>상세 구분</th><th>제체 질량 (kN)</th><th>중심위치 y (m)</th><th>수평모멘트 Mh (kN·m)</th></tr>{html_table_rows_inertia}</table>")

    inertia_html_1 = "<div style='font-size:12px; font-weight:bold; margin-bottom:5px;'>1) 제체중량에 의한 관성력(부력을 고려하지 않은 중량)</div>"
    inertia_html_1 += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px; margin-bottom:20px;'>"
    inertia_html_1 += "<tr style='background-color:#d9d9d9;'>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>구 분</th>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>설계수평<br>지진계수 kh</th>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>연직력 V<br>(산정 근거 및 합계, kN)</th>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>관성력 V × kh<br>(kN)</th>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>중심위치 y<br>(m)</th>"
    inertia_html_1 += "<th style='border:1px solid #ccc; padding:6px;'>모멘트 Mh<br>(kN·m)</th>"
    inertia_html_1 += "</tr>"

    for t in tier_details:
        level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"
        v_val = t['inertia_mass']
        y_val = t['inertia_arm']
        f_val = v_val * kh
        m_val = f_val * y_val

        inertia_html_1 += "<tr>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px;'>{kh:.3f}</td>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px; text-align:right; padding-right:15px;'><div style='font-size:11px; color:#7f8c8d; margin-bottom:2px;'>제체 질량 합계</div><b>{v_val:,.2f}</b></td>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#d35400;'>{f_val:,.2f}</td>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px;'>{y_val:.2f}</td>"
        inertia_html_1 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#1a73e8;'>{m_val:,.2f}</td>"
        inertia_html_1 += "</tr>"

    inertia_html_1 += "</table>"
    o_html(inertia_html_1)

    inertia_html_2 = "<div style='font-size:12px; font-weight:bold; margin-bottom:5px;'>2) 상재하중에 의한 관성력</div>"
    inertia_html_2 += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px; margin-bottom:15px;'>"
    inertia_html_2 += "<tr style='background-color:#d9d9d9;'>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>구 분</th>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>설계수평<br>지진계수 kh</th>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>연직력 V<br>(산정 근거 및 합계, kN)</th>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>관성력 V × kh<br>(kN)</th>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>중심위치 y<br>(m)</th>"
    inertia_html_2 += "<th style='border:1px solid #ccc; padding:6px;'>모멘트 Mh<br>(kN·m)</th>"
    inertia_html_2 += "</tr>"

    for t in tier_details:
        level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"
        v_sq = t.get('v_sq_tier_s', 0.0)
        y_sq = c_top - t['bot_el']
        f_sq = v_sq * kh
        m_sq = f_sq * y_sq

        inertia_html_2 += "<tr>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px;'>{kh:.3f}</td>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px; text-align:right; padding-right:15px;'><div style='font-size:11px; color:#7f8c8d; margin-bottom:2px;'>상재하중 연직력</div><b>{v_sq:,.2f}</b></td>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#d35400;'>{f_sq:,.2f}</td>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px;'>{y_sq:.2f}</td>"
        inertia_html_2 += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#1a73e8;'>{m_sq:,.2f}</td>"
        inertia_html_2 += "</tr>"

    inertia_html_2 += "</table>"
    o_html(inertia_html_2)

    o_title("8. 동수압", level=1)
    o_html("<div style='font-size:14px; font-weight:bold; color:#333; margin-bottom:10px;'>1) 동수압 산정</div>")
    o_latex(
        r"P_{dw} = \int_{0}^{y} \frac{7}{8} k \gamma_w H^{1/2} y^{1/2} dy = \pm \frac{7}{8} k \gamma_w H^{1/2} \left(\frac{2}{3} y^{3/2}\right) = \pm \frac{7}{12} k \gamma_w H^{1/2} y^{3/2} \quad , \quad h_{dw} = \frac{3}{5} y")

    dw_desc_html = f"""
    <div style='background:#fdfefe; padding:15px; border:1px solid #ccc; margin-bottom:15px; font-size:12px;'>
    <table style='border:none; text-align:left; font-size:12px; line-height:1.6; margin-left: 10px;'>
    <tr><td style='border:none; padding:2px 5px;'>여기서,</td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>P<sub>dw</sub></td><td style='border:1px solid #ccc; padding:2px 5px;'>:</td><td style='border:none; padding:2px 5px;'>동수압의 합력(kN)</td></tr>
    <tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>k</td><td style='border:1px solid #px 5px;'>:</td><td style='border:none; padding:2px 5px;'>설계수평지진계수 ( = {kh:.3f} )</td></tr>
    <tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>γ<sub>w</sub></td><td style='border:1px solid #px 5px;'>:</td><td style='border:none; padding:2px 5px;'>물의 단위중량 ( = {g_w:.2f} )</td></tr>
    <tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>H</td><td style='border:1px solid #px 5px;'>:</td><td style='border:none; padding:2px 5px;'>전면수심(m) ( = {h_water:.2f} )</td></tr>
    <tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>h<sub>dw</sub></td><td style='border:1px solid #px 5px;'>:</td><td style='border:none; padding:2px 5px;'>수면부터 동수압 합력의 작용점까지 거리(m)</td></tr>
    <tr><td style='border:none;'></td><td style='border:none; padding:2px 5px; border:1px solid #ddd;'>h<sub>dw</sub>'</td><td style='border:1px solid #px 5px;'>:</td><td style='border:none; padding:2px 5px;'>제체 하단으로부터 동수압 합력의 작용점까지의 거리(m)</td></tr>
    </table>
    </div>
    """
    o_html(dw_desc_html)

    dw_table_html = "<div style='font-size:12px; font-weight:bold; margin-bottom:5px;'>2) 동수압에 의한 수평력</div>"
    dw_table_html += "<table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:11px; margin-bottom:15px;'>"
    dw_table_html += "<tr style='background-color:#d9d9d9;'>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>구 분</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>k</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>γ<sub>w</sub><br>(kN/m³)</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>H<br>(m)</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>y<br>(m)</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>P<sub>dw</sub><br>(kN)</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>h<sub>dw</sub>'<br>(m)</th>"
    dw_table_html += "<th style='border:1px solid #ccc; padding:6px;'>Mdw<br>(kN·m)</th>"
    dw_table_html += "</tr>"

    row_count = len(tier_details)
    for idx, t in enumerate(tier_details):
        level_str = f"({'+' if t['bot_el'] >= 0 else '-'}){abs(t['bot_el']):.3f}"
        y_val = max(0.0, llw - t['bot_el'])
        pdw_val = (7.0 / 12.0) * kh * g_w * math.sqrt(h_water) * (y_val ** 1.5) if y_val > 0 else 0.0
        hd_from_top = (3.0 / 5.0) * y_val
        hd_from_bot = y_val - hd_from_top if y_val > 0 else 0.0
        mdw_val = pdw_val * hd_from_bot

        t['dw_f'] = pdw_val
        t['dw_m'] = mdw_val

        dw_table_html += "<tr>"
        dw_table_html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold;'>{level_str}</td>"
        if idx == 0:
            dw_table_html += f"<td rowspan='{row_count}' style='border:1px solid #ccc; vertical-align:middle;'>{kh:.3f}</td>"
            dw_table_html += f"<td rowspan='{row_count}' style='border:1px solid #ccc; vertical-align:middle;'>{g_w:.2f}</td>"
            dw_table_html += f"<td rowspan='{row_count}' style='border:1px solid #ccc; vertical-align:middle;'>{h_water:.2f}</td>"
        dw_table_html += f"<td style='border:1px solid #ccc; padding:6px;'>{y_val:.2f}</td>"
        dw_table_html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#d35400;'>{pdw_val:.2f}</td>"
        dw_table_html += f"<td style='border:1px solid #ccc; padding:6px;'>{hd_from_bot:.2f}</td>"
        dw_table_html += f"<td style='border:1px solid #ccc; padding:6px; font-weight:bold; color:#1a73e8;'>{mdw_val:.2f}</td>"
        dw_table_html += "</tr>"

    dw_table_html += "</table>"
    o_html(dw_table_html)

    o_title("9. 지진시 하중집계 및 안정검토 (CASE별)", level=1)

    o_title("가. CASE별 하중조합", level=2)
    # 이미지와 똑같은 형태의 지진시 하중조합 행렬(Matrix) 표 삽입
    case_matrix_eq_html = """
        <table style='width:100%; border-collapse: collapse; text-align:center; border: 2px solid #333; font-size:13px; margin-bottom: 25px;'>
            <tr style='background-color:#d5e8f5;'>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>구 분</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>자중</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>상재하중</th>
                <th colspan='2' style='border:1px solid #333; padding:8px;'>토압</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>잔류수압</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>견인력</th>
                <th colspan='2' style='border:1px solid #333; padding:8px;'>관성력</th>
                <th rowspan='2' style='border:1px solid #333; padding:8px;'>동수압</th>
            </tr>
            <tr style='background-color:#d5e8f5;'>
                <th style='border:1px solid #333; padding:8px;'>상재하중無</th>
                <th style='border:1px solid #333; padding:8px;'>상재하중有</th>
                <th style='border:1px solid #333; padding:8px;'>제체</th>
                <th style='border:1px solid #333; padding:8px;'>상재하중</th>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 2-1</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>-</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 2-2</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>-</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 2-3</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>-</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
            <tr>
                <td style='border:1px solid #333; padding:8px; font-weight:bold; background-color:#eaeaea;'>CASE 2-4</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'></td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>-</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
                <td style='border:1px solid #333; padding:8px;'>○</td>
            </tr>
        </table>
        """
    o_html(case_matrix_eq_html)

    o_title("나. CASE별 하중집계", level=2)
    o_html(generate_case_summary_table("CASE 2-1 하중집계", "2_1", tier_details))
    o_html(generate_case_summary_table("CASE 2-2 하중집계", "2_2", tier_details))
    o_html(generate_case_summary_table("CASE 2-3 하중집계", "2_3", tier_details))
    o_html(generate_case_summary_table("CASE 2-4 하중집계", "2_4", tier_details))

    o_title("다. 안정검토", level=2)
    o_title("1) 안정검토 공식", level=3)
    o_html(generate_formula_html())

    o_title("2) 안정검토", level=3)
    cases_list_eq = [
        ("CASE 2-1", "2_1"),
        ("CASE 2-2", "2_2"),
        ("CASE 2-3", "2_3"),
        ("CASE 2-4", "2_4")
    ]

    o_html(generate_sliding_table(cases_list_eq, tier_details, fs_allow=1.0, mu_cc=0.5, mu_cb=0.6))
    o_html(generate_overturning_table(cases_list_eq, tier_details, fs_allow=1.0))

    bottom_tier_detail = tier_details[-1]
    o_html(generate_bearing_table(cases_list_eq, bottom_tier_detail, qa_allow=qa_s, mu=0.6))

# =====================================================================
# ★ 10. 통합 보고서 다운로드 렌더링
# =====================================================================
def render_fast_download(rep_obj, filename_base):
    st.divider()
    st.header("🖨️ 종합 구조계산서 다운로드")
    st.info("💡 **초고속 병렬 다운로드 엔진 적용:** HTML 웹용 및 MS Word용 보고서를 즉시 생성합니다.")
    with st.spinner("보고서용 수식과 그림을 변환 중입니다..."):
        report_html = rep_obj.get_html()
        mhtml_data = rep_obj.get_mhtml()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 구조계산서 다운로드 (HTML웹용)", data=report_html.encode('utf-8'), file_name=f"{filename_base}.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button("📝 구조계산서 다운로드 (MS Word용)", data=mhtml_data.encode('utf-8'), file_name=f"{filename_base}.doc", mime="application/msword", use_container_width=True)

filename_suffix = "평상시" if "평상시" in calc_mode else "지진시"
render_fast_download(rep, f"블록식_안벽_구조계산서_{filename_suffix}")
