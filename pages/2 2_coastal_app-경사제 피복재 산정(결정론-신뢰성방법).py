import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
import os
import urllib.request
import matplotlib.font_manager as fm
import io
import base64
import re
import concurrent.futures
with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보, 유현상, 이종태, 나제민]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")
# ★ 1. 화면 꽉 차게 만들기 (Streamlit 최상단 필수 설정)
st.set_page_config(page_title="항만 케이슨 토압 산정 시스템", layout="wide")

# =====================================================================
# ★ 한글 폰트 설정 (보고서 가독성용)
# =====================================================================
@st.cache_resource
def set_korean_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve(font_url, font_path)
        except Exception: pass
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rc('font', family='NanumGothic')
    plt.rcParams['axes.unicode_minus'] = False 

set_korean_font()

# =====================================================================
# ★ 초고속 수식 이미지 다운로드 캐시 (전역)
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
# ★ 보고서 생성기 (그림 찌그러짐 방지 + 초고속 렌더링)
# =====================================================================
class ReportBuilder:
    def __init__(self):
        self.html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>토압 산정 통합 구조계산서</title>
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script>
          MathJax = {
            tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], processEscapes: true },
            options: { ignoreHtmlClass: "tex2jax_ignore", processHtmlClass: "tex2jax_process" }
          };
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body { font-family: 'Malgun Gothic', 'NanumGothic', sans-serif; line-height: 1.6; padding: 20px; color: #333; max-width: 1200px; margin: auto; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 14px; background: white; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            th { background-color: #f4f6f8; font-weight: bold; color: #333;}
            h1 { color: #2c3e50; text-align: center; }
            h2 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 40px;}
            h3 { color: #2c3e50; margin-top: 25px; }
            h4 { color: #34495e; font-weight: bold; margin-top: 20px;}
            .eq { background: #f8f9fa; padding: 15px; border-left: 4px solid #1a73e8; margin: 15px 0; overflow-x: auto; font-size: 1.1em;}
            .figure { text-align: center; margin: 20px 0; }
            p { margin: 8px 0; }
            ul { margin-top: 5px; margin-bottom: 15px; padding-left: 20px; }
            li { margin-bottom: 8px; }
            .info-box { background-color: #e8f0fe; border-left: 4px solid #1a73e8; padding: 15px; margin: 15px 0; }
            .success-box { background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; }
        </style>
        </head><body class="tex2jax_process">
        """
    
    def title(self, text, level=2):
        self.html += f"<h{level}>{text}</h{level}>"

    def md(self, text):
        html_out = ""
        in_list = False
        in_sub_list = False
        
        for line in text.split('\n'):
            if not line.strip(): continue
            leading_spaces = len(line) - len(line.lstrip())
            content = line.strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            
            if content.startswith('#### '):
                html_out += f"<h4>{content[5:]}</h4>\n"
                continue
            elif content.startswith('### '):
                html_out += f"<h3>{content[4:]}</h3>\n"
                continue
            elif content.startswith('## '):
                html_out += f"<h2>{content[3:]}</h2>\n"
                continue

            if content.startswith('* ') or content.startswith('- '):
                clean_content = content[2:]
                if leading_spaces >= 2:
                    if not in_list: html_out += "<ul>\n"; in_list = True
                    if not in_sub_list: html_out += "<ul style='margin-top:0; margin-bottom:0;'>\n"; in_sub_list = True
                    html_out += f"<li style='list-style-type:circle;'>{clean_content}</li>\n"
                else:
                    if in_sub_list: html_out += "</ul>\n"; in_sub_list = False
                    if not in_list: html_out += "<ul>\n"; in_list = True
                    html_out += f"<li>{clean_content}</li>\n"
            else:
                if in_sub_list: html_out += "</ul>\n"; in_sub_list = False
                if in_list: html_out += "</ul>\n"; in_list = False
                if content.startswith('> '): html_out += f"<blockquote style='border-left: 3px solid #ccc; margin-left: 10px; padding-left: 10px; color: #555;'>{content[2:]}</blockquote>\n"
                else: html_out += f"<p>{content}</p>\n"
                    
        if in_sub_list: html_out += "</ul>\n"
        if in_list: html_out += "</ul>\n"
        self.html += html_out

    def info(self, text):
        content = text.replace('\n', '<br>')
        content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
        self.html += f"<div class='info-box'>{content}</div>"
        
    def success(self, text):
        content = text.replace('\n', '<br>')
        content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
        self.html += f"<div class='success-box'>{content}</div>"

    def latex(self, eq):
        self.html += f"<div class='eq'>$$ {eq} $$</div>"

    def table(self, dataframe, styled=None):
        if styled is not None:
            try: html_table = styled.to_html(justify='center')
            except Exception: html_table = dataframe.to_html(index=False, justify='center', escape=False)
        else:
            html_table = dataframe.to_html(index=False, justify='center', escape=False)
        self.html += html_table.replace('\\n', '<br>')

    def fig(self, figure):
        buf = io.BytesIO()
        figure.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        # ★ 워드 그림 찢어짐 방지: 기존 width=750 속성 완전 삭제
        self.html += f"<div class='figure'><img src='data:image/png;base64,{encoded}' style='max-width:100%;'></div>"

    def static_img(self, img_path, caption=""):
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            # ★ 워드 그림 찢어짐 방지: 기존 width=750 속성 완전 삭제
            self.html += f"<div class='figure'><img src='data:image/png;base64,{encoded}' style='max-width:100%;'><p><b>{caption}</b></p></div>"

    def get_html(self):
        return self.html + "</body></html>"

def render_fast_download(rep_obj, filename_base):
    st.divider()
    st.header("🖨️ 통합 구조계산서 다운로드")
    st.info("💡 **초고속 병렬 다운로드 엔진 적용:** MS Word 다운로드 시 수식과 삽도가 고해상도로 내장되며, 1~2초 이내에 즉시 생성됩니다.")
    
    with st.spinner("Word 보고서용 수식과 그림을 고속 병렬 변환 중입니다..."):
        report_html = rep_obj.get_html()
        word_html = report_html
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 20px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f2f2f2; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

        # ★ MS Word 삽도(그림) 세로 찢어짐 현상 100% 차단 
        # (<img> 태그 통째로 잡아내서 1x1 테이블로 래핑 + 폭 고정)
        def image_replacer(match):
            b64_data = match.group(1)
            counters['img'] += 1
            img_id = f"fig_img_{counters['img']}"
            attachments[img_id] = b64_data
            return f'<table align="center" style="border-collapse: collapse; border: none; margin: 10px auto;"><tr><td style="border: none; padding: 0; text-align: center;"><img src="cid:{img_id}" width="650"></td></tr></table>'
        
        word_html = re.sub(r'<img[^>]+src=[\'"]data:image/png;base64,([^\'"]+)[\'"][^>]*>', image_replacer, word_html)

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

        # EP.py 전용 잔여 첨자(기호) 강제 치환
        word_html = word_html.replace("$\\Delta H$", "ΔH").replace("$\\Phi$", "Φ").replace("$\\delta$", "δ").replace("$\\beta$", "β").replace("$\\Theta$", "Θ")
        word_html = word_html.replace("$\\zeta$", "ζ").replace("$\\Psi$", "Ψ").replace("$\\xi'$", "ξ'")
        word_html = re.sub(r'\$([a-zA-Z]+)_([a-zA-Z0-9\+\-]+)\$', r'\1<sub>\2</sub>', word_html)
        word_html = word_html.replace('$', '')

        boundary = "----=_NextPart_HTML_DOC_001"
        mhtml = f'MIME-Version: 1.0\nContent-Type: multipart/related; type="text/html"; boundary="{boundary}"\n\n'
        mhtml += f'--{boundary}\nContent-Type: text/html; charset="utf-8"\nContent-Transfer-Encoding: 8bit\n\n'
        mhtml += word_html + "\n\n"
        
        for cid, b64 in attachments.items():
            mhtml += f'--{boundary}\nContent-Type: image/png\nContent-Transfer-Encoding: base64\nContent-ID: <{cid}>\n\n{b64}\n\n'
        mhtml += f"--{boundary}--\n"
        
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 구조계산서 다운로드 (HTML 웹용)", data=report_html.encode('utf-8'), file_name=f"{filename_base}.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button("📝 구조계산서 다운로드 (MS Word용)", data=mhtml.encode('utf-8'), file_name=f"{filename_base}.doc", mime="application/msword", use_container_width=True)

# =====================================================================
# ★ 초정밀 계산 엔진 (쿨롱 및 활동쐐기 이론 반영) - (지워진 부분 복구)
# =====================================================================
class UltimateCaissonEngine:
    def __init__(self, phi, delta_base):
        self.phi = phi
        self.delta_base = delta_base
        self.phi_r = math.radians(self.phi)
        self.delta_r = math.radians(self.delta_base)
        self.beta_r = math.radians(0.0)

    def calc_exact_angles(self, kh):
        theta_r = math.atan(kh)
        p, d, b = self.phi_r, self.delta_r, self.beta_r
        psi_w_r = math.radians(0.0)
        
        ang_X = p + d + psi_w_r - b 
        term1 = -math.tan(ang_X)
        
        root_num = math.cos(psi_w_r + d + theta_r) * math.sin(p + d)
        root_den = math.cos(psi_w_r - b) * math.sin(p - b - theta_r)
        root_val = math.sqrt(max(0, root_num / root_den))
        
        term2 = (1.0 / math.cos(ang_X)) * root_val
        cot_zeta_minus_beta = term1 + term2
        
        zeta_rad = math.atan(1.0 / cot_zeta_minus_beta) + b
        zeta_deg = math.degrees(zeta_rad)
        
        xi_prime = 90.0 + self.phi - zeta_deg
        psi_calc = 90.0 - xi_prime
        
        return {
            'zeta': zeta_deg, 'xi_prime': xi_prime, 'psi_calc': psi_calc,
            'tan_xi_prime': math.tan(math.radians(xi_prime)),
            'term1': term1, 'term2': term2, 'root_val': root_val, 'ang_X_deg': math.degrees(ang_X),
            'root_num': root_num, 'root_den': root_den, 'cot_val': cot_zeta_minus_beta
        }

    def calc_kah(self, delta_deg, psi_w_deg, kh):
        p, b = self.phi_r, self.beta_r
        d = math.radians(delta_deg)
        psi_w = math.radians(psi_w_deg)
        theta = math.atan(kh)
        
        num = (math.cos(p - psi_w - theta))**2
        den_base = math.cos(theta) * (math.cos(psi_w))**2 * math.cos(d + psi_w + theta)
        in_root = (math.sin(p + d) * math.sin(p - b - theta)) / (math.cos(d + psi_w + theta) * math.cos(psi_w - b))
        
        kai = num / (den_base * (1 + math.sqrt(max(0, in_root)))**2)
        kah = kai * math.cos(d + psi_w)
        
        return kai, kah

st.sidebar.header("📁 케이슨 안벽 종류 선택")
project_source = st.sidebar.radio("입력 기준", ["일반부두(단일토층)", "컨테이너부두(이중토층, 항만설계사례집)"])

# =====================================================================
# 🟢 [분기 1] 일반부두(단일토층) (장보고 용역)
# =====================================================================
if project_source == "일반부두(단일토층)":
    st.sidebar.divider()
    st.sidebar.header("⚙️ 설계 조건 설정 (일반부두)")
    case_type = st.sidebar.radio("해석 상태", ["평상시 (Normal)", "지진시 (Seismic)"])
    q_type = st.sidebar.radio("상재하중 유/무", ["상재하중 有 (Case B)", "상재하중 無 (Case A)"])

    st.sidebar.divider()
    st.sidebar.header("📋 단면 제원")
    c_top = st.sidebar.number_input("부지고 (DL.m)", value=4.50)
    c_mid = st.sidebar.number_input("케이슨 상단고 (DL.m)", value=1.80)
    c_bot = st.sidebar.number_input("케이슨 바닥고 (DL.m)", value=-10.50)

    super_w = st.sidebar.number_input("상치폭 (m)", value=4.0)
    caisson_w = st.sidebar.number_input("케이슨 폭 (m)", value=8.0)
    front_toe_l = st.sidebar.number_input("전면 토우길이 (m)", value=1.0)
    rear_toe_l = st.sidebar.number_input("후면 토우길이 (m)", value=1.0)

    toe_bot = st.sidebar.number_input("Toe 하단고 (DL.m)", value=-10.50)
    toe_hf = st.sidebar.number_input("Toe 앞높이 (m)", value=0.50)
    toe_hb = st.sidebar.number_input("Toe 뒤높이 (m)", value=0.50)

    st.sidebar.divider()
    st.sidebar.header("🌍 지반 및 하중 조건")
    phi_in = st.sidebar.number_input("내부마찰각 φ (°)", value=40.0)
    delta_in = st.sidebar.number_input("기본 벽면마찰각 δ (°)", value=15.0)
    gwl_n = st.sidebar.number_input("평상시 잔류수위", value=0.982)
    gwl_s = st.sidebar.number_input("지진시 잔류수위", value=2.19)
    kh_in = st.sidebar.number_input("지진계수 kh", value=0.107, format="%.3f", step=0.001) 
    q_n = st.sidebar.number_input("평상시 상재 (kPa)", value=20.0)
    q_s = st.sidebar.number_input("지진시 상재 (kPa)", value=10.0)

    g_wet = st.sidebar.number_input("습윤단위중량 γ_t", value=18.0)
    g_sat = st.sidebar.number_input("포화단위중량 γ_sat", value=20.0)
    g_sub = st.sidebar.number_input("수중단위중량 γ_sub", value=10.0)

    st.markdown("<h1 style='text-align:center;'>⚓ 일반부두 케이슨 토압산정 구조계산서</h1><hr>", unsafe_allow_html=True)
    st.caption("현재 적용 데이터: **일반부두(단일토층) (단일 토층 기준)**")
    st.divider()

    # --- 핵심 로직 분리 (UI 출력 & 통합 보고서 생성 공용) ---
    def generate_general(current_case_type, render_ui=True, rep_obj=None):
        def out_md(text, col=None):
            if render_ui:
                if col is not None: col.markdown(text)
                else: st.markdown(text)
            if rep_obj: rep_obj.md(text)
        def out_write(text, col=None):
            if render_ui:
                if col is not None: col.write(text)
                else: st.write(text)
            if rep_obj: rep_obj.md(text)
        def out_latex(eq, col=None):
            if render_ui:
                if col is not None: col.latex(eq)
                else: st.latex(eq)
            if rep_obj: rep_obj.latex(eq)
        def out_info(text, col=None):
            if render_ui:
                if col is not None: col.info(text)
                else: st.info(text)
            if rep_obj: rep_obj.info(text)
        def out_success(text, col=None):
            if render_ui:
                if col is not None: col.success(text)
                else: st.success(text)
            if rep_obj: rep_obj.success(text)
        def out_title(text, level, col=None):
            if render_ui:
                target = col if col is not None else st
                if level==1: target.header(text)
                elif level==2: target.subheader(text)
                elif level==3: target.markdown(f"### {text}")
            if rep_obj: rep_obj.title(text, level=level)
        def out_table(df, styled=None, col=None):
            if render_ui:
                target = col if col is not None else st
                target.table(styled if styled is not None else df)
            if rep_obj: rep_obj.table(df, styled=styled)
        def out_fig(f, col=None):
            if render_ui:
                target = col if col is not None else st
                target.pyplot(f)
            if rep_obj: rep_obj.fig(f)
        def out_img(img, cap, col=None):
            if render_ui:
                target = col if col is not None else st
                try: target.image(img, caption=cap, use_container_width=True)
                except Exception: target.info(f"💡 '{img}' 이미지를 실행 파일과 동일한 폴더에 위치시키면 삽도가 표시됩니다.")
            if rep_obj: rep_obj.static_img(img, caption=cap)
        def out_div():
            if render_ui: st.divider()
            if rep_obj: rep_obj.html += "<hr>"

        engine = UltimateCaissonEngine(phi_in, delta_in)
        
        is_seis = "지진시" in current_case_type
        curr_gwl = gwl_s if is_seis else gwl_n
        curr_q = (q_s if is_seis else q_n) if "有" in q_type else 0.0

        if is_seis:
            kh_above = kh_in 
            w_top = g_wet * max(0, c_top - curr_gwl)
            h_layer = max(0, curr_gwl - c_bot)
            num = 2 * (w_top + curr_q) + (g_sat * h_layer)
            den = 2 * (w_top + curr_q) + (g_sub * h_layer)
            k_prime = (num / den) * kh_in if den > 0 else kh_in
            kh_below = k_prime 
        else:
            kh_above = 0.0
            k_prime = 0.0
            kh_below = 0.0
            w_top = 0.0

        arm_toe = front_toe_l + caisson_w + rear_toe_l
        arm_virt = front_toe_l + caisson_w
        arm_wedge = front_toe_l + caisson_w + (rear_toe_l / 3.0)

        geo = engine.calc_exact_angles(kh_below)
        h_rise = rear_toe_l * geo['tan_xi_prime'] 
        toe_top_dl = toe_bot + toe_hb
        intersect_dl = toe_top_dl + h_rise

        kai_1_above, kah_1_above = engine.calc_kah(delta_in, 0.0, kh_above)  
        kai_1_below, kah_1_below = engine.calc_kah(delta_in, 0.0, kh_below)  
        kai_2, kah_2 = engine.calc_kah(phi_in, geo['psi_calc'], kh_below)    
        kai_3, kah_3 = engine.calc_kah(delta_in, 0.0, kh_below)              

        out_title("1. 설계 조건 요약", level=1)
        
        t_above = math.degrees(math.atan(kh_above))
        t_below = math.degrees(math.atan(kh_below))
        
        col_s1, col_s2 = st.columns(2) if render_ui else (None, None)
        
        out_md("**[기하 구조 및 수위]**", col=col_s1)
        df_s1 = pd.DataFrame({
            "구분": ["상치폭 / 케이슨폭", "전면 / 후면 토우길이", "케이슨 상단고 / 바닥고", "Toe 상단고", "적용 잔류수위"],
            "제원": [f"{super_w:.1f}m / {caisson_w:.1f}m", f"{front_toe_l:.1f}m / {rear_toe_l:.1f}m", f"DL {c_mid:.2f}m / DL {c_bot:.2f}m", f"DL {toe_top_dl:.2f}m", f"DL {curr_gwl:.2f}m"]
        })
        out_table(df_s1, col=col_s1)

        out_md("**[지반 상수 및 하중]**", col=col_s2)
        applied_kh_label = f"수상 {kh_above:.4f} (Θ={t_above:.2f}°) / 수중 {kh_below:.4f} (Θ={t_below:.2f}°)" if is_seis else "0.0000 (Θ=0.00°)"
        df_s2 = pd.DataFrame({
            "구분": ["내부마찰각(φ)", "벽면마찰각(δ)", "적용 상재하중(q)", "적용 지진계수(k, k') 및 합성각(Θ)", "단위중량(wet/sat/sub)"],
            "값": [f"{phi_in}°", f"{delta_in}°", f"{curr_q:.1f} kPa", applied_kh_label, f"{g_wet}/{g_sat}/{g_sub} kN/m³"]
        })
        out_table(df_s2, col=col_s2)

        out_div()

        if is_seis:
            out_title("1-1. 지진시 겉보기 진도($k'$) 산정 근거 (항만설계기준 정밀식)", level=2)
            out_md(r"**항만 및 어항설계기준(KDS)에 따라 수중부 지반의 간극수압, 유효응력 및 상/하부 토층과 상재하중을 모두 고려한 정밀 겉보기 진도식을 적용합니다.**")
            out_latex(r"k' = \frac{2(\sum \gamma_t h_i + \sum \gamma_{sat} h_j + \omega) + \gamma_{sat} h}{2[\sum \gamma_t h_i + \sum (\gamma - 10) h_j + \omega] + (\gamma - 10)h} k")
            
            out_md("""
            **[공식 기호 상세 설명]**
            * $k'$: 겉보기 진도 (수중부 지진토압 산정용 보정 진도)
            * $k$: 설계 진도 (지진계수, $k_h$)
            * $\\omega$: 지표면의 단위면적당 재하하중 (적용 상재하중)
            * $\\gamma_t$: 잔류수위 위 토층의 습윤 단위체적중량
            * $\\gamma_{sat}$: 잔류수위 아래 포화된 흙의 공기 중 단위체적중량
            * $\\gamma - 10$: 물의 단위중량을 편의상 $10kN/m^3$로 가정한 흙의 수중 단위체적중량($\\gamma_{sub}$)
            * $h_i$: 잔류수위 위 $i$번째 토층의 두께 ($m$)
            * $h_j$: 잔류수위 아래이면서 토압을 산정하는 대상 층보다 위에 있는 $j$번째 토층 두께 ($m$)
            * $h$: 잔류수위 아래에서 대상 토압을 산정하고자 하는 토층의 두께 ($m$)
            """)
            
            out_md("**[수중부 레벨별 겉보기 진도 산정 상세 내역]**")
            out_md(f"**① 공통 적용값($\\sum\\gamma_t h_i + \\omega$) 상세 계산**\n"
                   f"- 잔류수위 상부 토층 두께 = 부지고({c_top:.2f}) - 잔류수위({curr_gwl:.3f}) = **{max(0, c_top - curr_gwl):.3f} m**\n"
                   f"- 상부토층 중량($\\sum\\gamma_t h_i$) = 습윤단위중량({g_wet}) $\\times$ 두께({max(0, c_top - curr_gwl):.3f}) = **{w_top:.2f} kPa**\n"
                   f"- 공통 적용값 = 상부토층 중량({w_top:.2f}) + 상재하중({curr_q:.2f}) = **{w_top + curr_q:.2f} kPa**")
            out_write(f"**② 심도별 겉보기 진도 산출 표** (적용 $k_h$ = {kh_in:.4f}, $\\gamma_{{sat}}$ = {g_sat}, $\\gamma_{{sub}}$ = {g_sub})")
            
            k_levels = []
            for label, depth in [("잔류수위", curr_gwl), ("파괴면접점", intersect_dl), ("Toe상단", toe_top_dl), ("케이슨바닥", c_bot)]:
                if depth >= curr_gwl: continue
                h_z = curr_gwl - depth
                term_top = 2 * (w_top + curr_q)
                term_sat = g_sat * h_z
                term_sub = g_sub * h_z
                num_z = term_top + term_sat
                den_z = term_top + term_sub
                k_z = (num_z / den_z) * kh_in
                k_levels.append({
                    "위치": label, 
                    "심도(DL.m)": depth, 
                    "수중두께 h(m)": h_z, 
                    "분자(관성력비례)": f"{num_z:.2f} (=2*{w_top+curr_q:.2f}) + {term_sat:.2f}(={g_sat}*{h_z:.3f})",
                    "분모(유효응력비례)": f"{den_z:.2f} (=2*{w_top+curr_q:.2f}) + {term_sub:.2f}(={g_sub}*{h_z:.3f})",
                    "증폭비": f"{(num_z/den_z):.4f}", 
                    "겉보기진도(k')": k_z
                })
            
            if k_levels:
                df_k = pd.DataFrame(k_levels)
                out_table(df_k, styled=df_k.style.format({"심도(DL.m)": "{:.2f}", "수중두께 h(m)": "{:.2f}", "겉보기진도(k')": "{:.4f}"}))
                
            out_info(f"👉 **구조물 전체의 활동/전도 안정성 검토(주동토압계수 산출)를 위해, 파괴면이 도달하는 최대 심도인 '케이슨 바닥(DL {c_bot:.2f}m)' 기준의 대표 겉보기 진도 **$k' = {kh_below:.4f}$** 를 설계 기준치로 일괄 적용합니다.**")
            out_div()

        out_title("2. 케이슨에 작용하는 토압 (개념 및 원리)", level=1)
        col_img1, col_img2 = st.columns(2) if render_ui else (None, None)
        out_img("활동쐐기.png", "[그림 1] 뒷굽판 길이에 따른 활동쐐기 형성 원리", col=col_img1)
        out_img("케이슨 토압개념도.png", "[그림 2] 뒷굽판이 짧은 경우의 케이슨 토압 개념도", col=col_img2)

        out_md("""
        #### 1) 활동쐐기(Sliding Wedge) 형성의 기본 원리
        뒷굽판(Heel)이 있는 중력식 구조물은 뒷굽판의 길이에 따라 파괴면(활동면)이 형성되는 양상이 달라지며, 이는 토압 산정 방식의 기준이 됩니다.
        * **(a) 뒷굽판이 긴 경우:** 뒷굽판 끝단에서 발생하는 활동쐐기가 케이슨의 뒷면(연직면)과 만나지 않고 지표면으로 직접 향합니다. 이 경우, 뒷굽판 상부의 흙은 구조물과 일체로 거동하는 것으로 간주하여 흙 자체의 무게를 구조물의 자중에 포함시킵니다. 파괴면이 흙 내부에서만 형성되므로 마찰각은 흙의 **내부마찰각($\\phi$)**을 적용합니다.
        * **(b) 뒷굽판이 짧은 경우:** 활동쐐기가 뒷면 연직면과 교차하게 됩니다. 구조물과 배면토 사이의 상호작용이 복합적으로 발생하므로 구간을 나누어 토압을 산정해야 합니다.

        #### 2) 케이슨 구간별 토압 산정 상세
        뒷굽판으로 인해 배면 형상이 꺾인 경우(Broken Backface), Coulomb의 토압 이론을 바탕으로 각 단면별로 작용하는 주동토압($P_1, P_2, P_3$)을 분할 산정합니다. 이때 각 작용면의 특성에 따라 **벽면마찰각($\\delta$)의 적용 기준이 상이**함에 유의해야 합니다.

        * **① $P_1$ 구간 (직립면 상부):** 콘크리트(구조물)와 배면토(흙) 사이의 경계면이므로 **벽면마찰각($\\delta$)**을 적용합니다. 벽체 경사각 $\\alpha = 0^\\circ$로 설정하여 일반적인 주동토압과 동일한 원리로 계산합니다.
        * **② $P_2$ 구간 (가상 경사면 쐐기부):** 본체 뒷면과 뒷굽판 끝을 연결하는 가상의 파괴면(Virtual Sliding Plane)입니다. 흙과 흙 사이의 입자 간 마찰이 지배적이므로 벽면마찰각이 아닌 흙의 **내부마찰각($\\phi$)**을 적용합니다. 연직면에 대해 가상벽면사각 $\\Psi$만큼 기울어진 경사면($\\alpha = \\Psi$)으로 해석하며, 가상면 안쪽의 흙(활동쐐기 내부)은 구조물 자중에 포함시켜 활동 및 전도 저항력에 기여하는 것으로 산정합니다.
        * **③ $P_3$ 구간 (뒷굽판 단부 수직면):** 다시 뒷굽판 콘크리트와 흙이 만나게 되므로 **벽면마찰각($\\delta$)**을 적용합니다. $\\alpha = 0^\\circ$이며 심도(Depth)가 깊기 때문에 토압 강도가 단면 내에서 가장 크게 나타납니다.
        """)
        out_div()

        out_title(f"3. {current_case_type} 일반부두 케이슨 토압산정 구조계산서", level=1)
        col_f1, col_f2 = st.columns([2.0, 1.2]) if render_ui else (None, None)

        out_md("#### 1) 주동붕괴각 및 활동쐐기각 산출 근거", col=col_f1)
        
        if is_seis:
            out_md(r"**① 주동붕괴각($\zeta$) 공식 (지진시: Mononobe-Okabe 이론)**", col=col_f1)
            out_latex(r"\cot(\zeta-\beta) = -\tan(\Phi+\delta-\beta) + \sec(\Phi+\delta-\beta)\sqrt{\frac{\cos(\delta+\Theta)\sin(\Phi+\delta)}{\cos(-\beta)\sin(\Phi-\beta-\Theta)}}", col=col_f1)
            theta_above = math.degrees(math.atan(kh_above))
            theta_below = math.degrees(math.atan(kh_below))
            out_write(fr"- 수상부 지진합성각 $\Theta_{{above}} = \tan^{{-1}}({kh_above:.4f}) = \mathbf{{{theta_above:.2f}^\circ}}$", col=col_f1)
            out_write(fr"- 수중부 지진합성각 $\Theta_{{below}} = \tan^{{-1}}({kh_below:.4f}) = \mathbf{{{theta_below:.2f}^\circ}}$ (파괴면 계산 기준)", col=col_f1)
            theta_val = theta_below
        else:
            out_md(r"**① 주동붕괴각($\zeta$) 공식 (상시/평상시: Coulomb 이론)**", col=col_f1)
            out_latex(r"\cot(\zeta-\beta) = -\tan(\Phi+\delta-\beta) + \sec(\Phi+\delta-\beta)\sqrt{\frac{\cos\delta\sin(\Phi+\delta)}{\cos(-\beta)\sin(\Phi-\beta)}}", col=col_f1)
            theta_val = 0.0

        out_md("""
        **[공식 기호 설명]**
        * $\\zeta$: 주동붕괴각 (파괴면이 수평면과 이루는 각도)
        * $\\Phi$: 흙의 내부마찰각
        * $\\delta$: 벽면마찰각 (구조물과 흙 사이의 마찰각)
        * $\\beta$: 배면 지표면의 경사각 (본 계산에서는 $0^\\circ$ 적용)
        * $\\Theta$: 지진합성각 (수평진도 $k_h$에 의해 결정, $\\Theta = \\tan^{-1}(k_h)$)
        """, col=col_f1)

        out_md(r"**[주동붕괴각 상세 계산 과정]**", col=col_f1)
        out_info(fr"- 적용치: $\Phi={phi_in}^\circ, \delta={delta_in}^\circ, \beta=0^\circ, \Theta={theta_val:.2f}^\circ$", col=col_f1)
        out_write(fr"- 근호 안 분자 = $\cos({delta_in}^\circ+{theta_val:.2f}^\circ) \cdot \sin({phi_in}^\circ+{delta_in}^\circ) = \mathbf{{{geo['root_num']:.4f}}}$", col=col_f1)
        out_write(fr"- 근호 안 분모 = $\cos(0^\circ) \cdot \sin({phi_in}^\circ-0^\circ-{theta_val:.2f}^\circ) = \mathbf{{{geo['root_den']:.4f}}}$", col=col_f1)
        out_write(fr"- $\sqrt{{\text{{분자}}/\text{{분모}}}} = \mathbf{{{geo['root_val']:.4f}}}$", col=col_f1)
        out_write(fr"- 제1항 ($-\tan(\Phi+\delta-\beta)$) = $\mathbf{{{geo['term1']:.4f}}}$", col=col_f1)
        out_write(fr"- 제2항 ($\sec(\Phi+\delta-\beta) \cdot \sqrt{{\dots}}$) = $\mathbf{{{geo['term2']:.4f}}}$", col=col_f1)
        out_write(fr"- $\cot(\zeta) = {geo['term1']:.4f} + {geo['term2']:.4f} = \mathbf{{{geo['cot_val']:.4f}}}$", col=col_f1)
        out_write(fr"- $\zeta = \cot^{{-1}}({geo['cot_val']:.4f}) = \mathbf{{{geo['zeta']:.2f}^\circ}}$", col=col_f1)
        
        out_md(r"**② 활동쐐기각($\xi'$) 및 가상벽면사각($\Psi$) 산정**", col=col_f1)
        out_latex(r"\xi' = 90^\circ + \Phi - \zeta \quad / \quad \Psi = 90^\circ - \xi'", col=col_f1)
        out_write(fr"- 활동쐐기각 $\xi' = 90 + {phi_in} - {geo['zeta']:.2f} = \mathbf{{{geo['xi_prime']:.2f}^\circ}}$", col=col_f1)
        out_write(fr"- 가상벽면사각 $\Psi = 90 - {geo['xi_prime']:.2f} = \mathbf{{{geo['psi_calc']:.2f}^\circ}}$", col=col_f1)

        out_md(r"**③ 파괴면 접점 상승 높이($\Delta H$)**", col=col_f1)
        out_latex(r"\Delta H = L_{toe(후면)} \times \tan(\xi')", col=col_f1)
        out_write(fr"- 상승 높이 $\Delta H = {rear_toe_l:.2f}\text{{m}} \times \tan({geo['xi_prime']:.2f}^\circ) = \mathbf{{{h_rise:.2f}\text{{m}}}}$", col=col_f1)
        out_success(fr"👉 파괴면 접점 = Toe상단(DL {toe_top_dl:.2f}) + {h_rise:.2f} = **DL {intersect_dl:.2f}m**", col=col_f1)
        
        out_md("#### 2) 구간별 주동토압계수($K_{ah}$) 산정", col=col_f1)
        out_md(r"**① 주동토압계수($K_{ah}$) 공식 (쿨롱 공식)**", col=col_f1)
        out_latex(r"K_{{ah}} = K_{{ai}} \cdot \cos(\delta + \Psi) = \frac{\cos^2(\Phi-\theta-\Psi) \cdot \cos(\delta+\Psi)}{\cos\theta \cos^2\Psi \cos(\delta+\Psi+\theta) \left[ 1 + \sqrt{\frac{\sin(\Phi+\delta)\sin(\Phi-\beta-\theta)}{\cos(\delta+\Psi+\theta)\cos(\Psi-\beta)}} \right]^2}", col=col_f1)
        out_md(r"**② 구역별 주동토압계수 산출 결과 상세**", col=col_f1)
        out_write(fr"- **수상부 (연직벽):** $\Phi = {phi_in}^\circ, \delta = {delta_in}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_above:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_1_above:.4f}, \quad \mathbf{{K_{{ah}}(k_h) = {kah_1_above:.4f}}}$", col=col_f1)
        out_write(fr"- **수중부 (상단연직벽):** $\Phi = {phi_in}^\circ, \delta = {delta_in}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_1_below:.4f}, \quad \mathbf{{K_{{ah}}(k') = {kah_1_below:.4f}}}$", col=col_f1)
        out_write(fr"- **수중부 (가상배면 쐐기):** $\Phi = {phi_in}^\circ, \delta = \Phi, \Psi = {geo['psi_calc']:.2f}^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_2:.4f}, \quad \mathbf{{K_{{ah}}(k') = {kah_2:.4f}}}$", col=col_f1)
        out_write(fr"- **수중부 (토우 연직벽):** $\Phi = {phi_in}^\circ, \delta = {delta_in}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_3:.4f}, \quad \mathbf{{K_{{ah}}(k') = {kah_3:.4f}}}$", col=col_f1)

        out_md("**[파괴면 및 쐐기 제원 요약]**", col=col_f2)
        summary_geo = pd.DataFrame({
            "항목": ["Toe 바닥고", "Toe 상단(기점)", "적용 마찰각(Φ/δ)", "가상벽면각(Ψ)", "파괴면 접점레벨"],
            "제원": [f"DL {toe_bot:.2f}m", f"DL {toe_top_dl:.2f}m", f"{phi_in}° / {delta_in}°", f"{geo['psi_calc']:.2f}°", f"DL {intersect_dl:.2f}m"]
        })
        out_table(summary_geo, col=col_f2)

        out_md("**[파괴면 보조 삽도 (상세표시)]**", col=col_f2)
        fig_sk, ax_sk = plt.subplots(figsize=(4, 4.5))
        ax_sk.plot([0, 0], [toe_bot-1, intersect_dl+1.5], 'k-', lw=3)
        ax_sk.fill([0, rear_toe_l, rear_toe_l, 0], [toe_bot, toe_bot, toe_top_dl, toe_top_dl], color='lightgray', ec='black')
        ax_sk.plot([rear_toe_l, 0], [toe_top_dl, intersect_dl], 'r--', lw=2.5)
        ax_sk.text(0, intersect_dl, f" DL {intersect_dl:.2f} ", color='red', ha='right', va='bottom', fontweight='bold')
        ax_sk.text(rear_toe_l, toe_top_dl, f" DL {toe_top_dl:.2f}", color='blue', ha='left', va='center')
        ax_sk.text(rear_toe_l/2, toe_bot-0.2, f"L={rear_toe_l}m", ha='center', va='top', fontsize=9)
        
        ax_sk.annotate('', xy=(0, intersect_dl), xytext=(0, toe_top_dl), arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
        ax_sk.text(-0.05, (intersect_dl + toe_top_dl)/2, f"ΔH={h_rise:.2f}m", ha='right', va='center', color='green', fontweight='bold', fontsize=10)
        
        ax_sk.plot([0, rear_toe_l+0.3], [toe_top_dl, toe_top_dl], 'b:', lw=1.2)
        ax_sk.text(rear_toe_l - 0.05, toe_top_dl + 0.1, f"ξ'={geo['xi_prime']:.2f}°", color='red', ha='right', va='bottom', fontsize=9)
        ax_sk.text(0.05, intersect_dl - 0.4, f"Ψ={geo['psi_calc']:.2f}°", color='red', ha='left', va='top', fontsize=9)
        
        ax_sk.axis('off')
        out_fig(fig_sk, col=col_f2)

        out_div()

        out_title("4. 심도별 수평/연직토압 강도 산정표", level=2)
        nodes = [
            (1, "부지고(상)", c_top, 0, 0, kah_1_above, delta_in, 0.0),
            (2, "케이슨상단", c_mid, g_wet, c_top - c_mid, kah_1_above, delta_in, 0.0),
            (3, "잔류수위(상)", curr_gwl, g_wet, c_mid - curr_gwl, kah_1_above, delta_in, 0.0),
            (4, "잔류수위(하)", curr_gwl, 0, 0, kah_1_below, delta_in, 0.0),
            (5, "파괴면접점(상)", intersect_dl, g_sub, curr_gwl - intersect_dl, kah_1_below, delta_in, 0.0),
            (6, "파괴면접점(하)", intersect_dl, 0, 0, kah_2, phi_in, geo['psi_calc']), 
            (7, "Toe상단(상)", toe_top_dl, g_sub, intersect_dl - toe_top_dl, kah_2, phi_in, geo['psi_calc']), 
            (8, "Toe상단(하)", toe_top_dl, 0, 0, kah_3, delta_in, 0.0),           
            (9, "케이슨바닥", c_bot, g_sub, toe_top_dl - c_bot, kah_3, delta_in, 0.0)
        ]
        table_rows = []
        cum_sig = 0.0
        for n, lbl, dl, gamma, h, kah, d, psi in nodes:
            if gamma > 0: cum_sig += gamma * h
            ph = (cum_sig + curr_q) * kah
            pv = ph * math.tan(math.radians(d + psi))
            table_rows.append({"Node": n, "위치": lbl, "심도(DL.m)": dl, "Σγh(kPa)": cum_sig, "Kah": kah, "ph(kN/m²)": ph, "pv(kN/m²)": pv})
        df_na = pd.DataFrame(table_rows).set_index("Node")
        
        out_table(df_na, styled=df_na.style.format({"심도(DL.m)": "{:.2f}", "Σγh(kPa)": "{:.2f}", "Kah": "{:.4f}", "ph(kN/m²)": "{:.3f}", "pv(kN/m²)": "{:.3f}"}))

        out_title("5. 구간별 수평력 및 모멘트 산정표", level=2)
        out_info(f"**💡 연직토압 팔거리(x) 작용점 산출식 상세:**\n"
                 f"- **상단부 연직벽 (지표면~파괴면접점):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) = **{arm_virt:.1f}m**\n"
                 f"- **파괴면 쐐기부 (파괴면접점~Toe상단):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) + 후면({rear_toe_l:.1f})/3 = **{arm_wedge:.2f}m**\n"
                 f"- **토우하단부 (Toe상단~바닥):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) + 후면({rear_toe_l:.1f}) = **{arm_toe:.1f}m**")

        segments = [
            (f"지표면 ~ 케이슨상단\n(DL {c_top:.2f} ~ {c_mid:.2f}m)", c_top, c_mid, kah_1_above, delta_in, 0.0, arm_virt),
            (f"케이슨상단 ~ 잔류수위\n(DL {c_mid:.2f} ~ {curr_gwl:.2f}m)", c_mid, curr_gwl, kah_1_above, delta_in, 0.0, arm_virt),
            (f"잔류수위 ~ 파괴면접점\n(DL {curr_gwl:.2f} ~ {intersect_dl:.2f}m)", curr_gwl, intersect_dl, kah_1_below, delta_in, 0.0, arm_virt),
            (f"파괴면접점 ~ Toe상단\n(DL {intersect_dl:.2f} ~ {toe_top_dl:.2f}m)", intersect_dl, toe_top_dl, kah_2, phi_in, geo['psi_calc'], arm_wedge), 
            (f"Toe상단 ~ 케이슨바닥\n(DL {toe_top_dl:.2f} ~ {c_bot:.2f}m)", toe_top_dl, c_bot, kah_3, delta_in, 0.0, arm_toe)             
        ]
        
        f_rows = []
        cum_sig = 0.0
        for lbl, z_t, z_b, kah, d, psi, arm_x in segments:
            h = z_t - z_b
            if h <= 0: continue
            tan_dp = math.tan(math.radians(d + psi))
            p_t = (cum_sig + curr_q) * kah
            cum_sig += (g_wet if z_t > curr_gwl else g_sub) * h
            p_b = (cum_sig + curr_q) * kah
            
            ph1, arm_y1 = p_t * h, (z_b - c_bot) + (h/2.0)
            pv1 = ph1 * tan_dp 
            mh1, mv1 = ph1 * arm_y1, pv1 * arm_x
            f_rows.append({"구분": lbl, "종류": "1(사각)", "Ph": ph1, "Pv": pv1, "y(수평팔)": arm_y1, "팔길이(x)": arm_x, "Mh": mh1, "Mv": mv1})
            
            ph2, arm_y2 = 0.5 * (p_b - p_t) * h, (z_b - c_bot) + (h/3.0)
            pv2 = ph2 * tan_dp 
            mh2, mv2 = ph2 * arm_y2, pv2 * arm_x
            f_rows.append({"구분": "", "종류": "2(삼각)", "Ph": ph2, "Pv": pv2, "y(수평팔)": arm_y2, "팔길이(x)": arm_x, "Mh": mh2, "Mv": mv2})
            
            f_rows.append({"구분": "▶ 합 계", "종류": "-", "Ph": ph1+ph2, "Pv": pv1+pv2, "y(수평팔)": None, "팔길이(x)": None, "Mh": mh1+mh2, "Mv": mv1+mv2})

        df_final = pd.DataFrame(f_rows)
        styled_df = df_final.style.set_properties(**{'white-space': 'pre-wrap', 'text-align': 'center'}).format(
            {"Ph": "{:.2f}", "Pv": "{:.2f}", "y(수평팔)": "{:.2f}", "팔길이(x)": "{:.2f}", "Mh": "{:.2f}", "Mv": "{:.2f}"}, na_rep=""
        )
        out_table(df_final, styled=styled_df)

        df_sums = df_final[df_final["구분"] == "▶ 합 계"]
        out_success(f"✅ **최종 합계 결과:**\n\n수평력 $\\Sigma P_h = {df_sums['Ph'].sum():.2f}$ kN/m, 수평모멘트 $\\Sigma M_h = {df_sums['Mh'].sum():.2f}$ kN·m/m\n\n연직력 $\\Sigma P_v = {df_sums['Pv'].sum():.2f}$ kN/m, 연직모멘트 $\\Sigma M_v = {df_sums['Mv'].sum():.2f}$ kN·m/m")

        out_title("6. 케이슨 모식도 및 수평토압 분포도", level=2)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), sharey=True, gridspec_kw={'width_ratios': [1.2, 1]})
        
        # --- ax1: 케이슨 모식도 ---
        x_ft = 0
        x_fw = front_toe_l
        x_rw = front_toe_l + caisson_w
        x_rt = front_toe_l + caisson_w + rear_toe_l
        
        cx = [x_ft, x_rt, x_rt, x_rw, x_rw, x_fw, x_fw, x_ft, x_ft]
        cy = [toe_bot, toe_bot, toe_bot + toe_hb, toe_bot + toe_hb, c_mid, c_mid, toe_bot + toe_hf, toe_bot + toe_hf, toe_bot]
        
        ax1.plot(cx, cy, 'k-', lw=2)
        ax1.fill(cx, cy, color='lightgray', alpha=0.5, label='케이슨')
        
        # 상치콘크리트 도식화
        sx = [x_fw, x_fw + super_w, x_fw + super_w, x_fw, x_fw]
        sy = [c_mid, c_mid, c_top, c_top, c_mid]
        ax1.plot(sx, sy, 'k-', lw=1.5)
        ax1.fill(sx, sy, color='darkgray', alpha=0.7, label='상치콘크리트')
        
        ax1.plot([x_fw + super_w, x_rt + 3], [c_top, c_top], 'brown', lw=2, label='부지고')
        ax1.axhline(curr_gwl, color='cyan', ls='--', lw=1.5, label='잔류수위')
        ax1.plot([x_rw, x_rt], [intersect_dl, toe_top_dl], 'r--', lw=2, label='파괴면 접점/활동면')
        
        ax1.text((x_fw + x_rw)/2, (c_bot + c_mid)/2, f"케이슨 폭 = {caisson_w:.1f}m\n벽체고 = {c_mid-c_bot:.2f}m", ha='center', va='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec='gray'))
        ax1.text((x_fw + x_fw + super_w)/2, (c_mid + c_top)/2, f"상치폭 = {super_w:.1f}m\n상치고 = {c_top-c_mid:.2f}m", ha='center', va='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec='gray'))
        ax1.text(x_ft + front_toe_l/2, toe_bot - 0.6, f"전면토우\n{front_toe_l:.1f}m", ha='center', va='top', fontsize=8, color='blue')
        ax1.text(x_rw + rear_toe_l/2, toe_bot - 0.6, f"후면토우\n{rear_toe_l:.1f}m", ha='center', va='top', fontsize=8, color='blue')
        ax1.text(x_rw + 0.2, intersect_dl, f"◀ 파괴접점 DL {intersect_dl:.2f}m\n  (상승고 ΔH={h_rise:.2f}m)", color='red', ha='left', va='center', fontsize=8, fontweight='bold')

        ax1.set_xlim(-1, x_rt + 3)
        ax1.set_ylim(c_bot - 2, c_top + 2)
        ax1.set_xlabel("폭 (m)")
        ax1.set_ylabel("심도 (DL.m)")
        ax1.set_title("케이슨 구조 모식도 (제원 매핑)")
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, linestyle=':', alpha=0.6)

        # --- ax2: 수평토압 분포도 ---
        nodes_plot = [
            (c_top, kah_1_above), (c_mid, kah_1_above), 
            (curr_gwl, kah_1_above), (curr_gwl, kah_1_below), 
            (intersect_dl, kah_1_below), (intersect_dl, kah_2), 
            (toe_top_dl, kah_2), (toe_top_dl, kah_3), 
            (c_bot, kah_3)
        ]
        pz, pp = [], []
        cs, pz_old = 0.0, c_top
        for z, kah in nodes_plot:
            if z < pz_old:
                cs += (g_wet if pz_old > curr_gwl else g_sub) * (pz_old - z)
                pz_old = z
            pz.append(z)
            pp.append((cs + curr_q) * kah)
        
        ax2.plot([0, 0], [c_bot, c_top], 'k-', lw=3)
        ax2.fill_betweenx(pz, 0, pp, color='orange', alpha=0.3)
        ax2.plot(pp, pz, 'r-', lw=1.5)
        for i, (p, z) in enumerate(zip(pp, pz)):
            if p > 0.01: ax2.text(p + max(pp)*0.03, z, f"{p:.1f}", va='center', fontsize=8, color='red')
        for z in sorted(list(set(pz))):
            ax2.axhline(z, color='gray', ls=':', lw=0.8)
        
        ax2.set_xlabel("토압 강도 (kN/m²)")
        ax2.set_title("수평토압 분포 모식도")
        
        out_fig(fig)

    # 1. 화면 UI 출력 (일반부두)
    generate_general(case_type, render_ui=True, rep_obj=None)

    # 2. 통합 보고서 생성 백그라운드 구동 (분할 없이 순차 출력)
    integrated_rep = ReportBuilder()
    integrated_rep.html += "<h1 style='text-align:center;'>⚓ 일반부두 케이슨 토압산정 통합 구조계산서</h1><hr>"
    integrated_rep.md("*현재 적용 데이터: **일반부두(단일토층) (단일 토층 기준)***")
    for ct in ["평상시 (Normal)", "지진시 (Seismic)"]:
        integrated_rep.html += f"<h2 style='color:#2c3e50; background-color:#e8f0fe; padding:10px;'>■ 해석 상태: {ct}</h2>"
        generate_general(ct, render_ui=False, rep_obj=integrated_rep)

    render_fast_download(integrated_rep, "일반부두_케이슨_토압산정구조계산서")

# =====================================================================
# 🔵 [분기 2] 컨테이너부두(이중토층, 항만설계사례집)
# =====================================================================
else:
    st.sidebar.divider()
    st.sidebar.header("⚙️ 설계 조건 설정 (컨테이너 안벽)")
    case_type = st.sidebar.radio("해석 상태 (하중조건)", ["평상시 (Normal)", "폭풍시 (Storm)", "지진시 (Seismic)"])
    q_type = st.sidebar.radio("상재하중 유/무", ["상재하중 有 (Case B)", "상재하중 無 (Case A)"])
    crane_type = st.sidebar.radio("크레인 유무", ["크레인 있음 (O)", "크레인 없음 (X)"])

    st.sidebar.divider()
    st.sidebar.header("📋 단면 제원")
    c_top = st.sidebar.number_input("부지고 (DL.m)", value=4.00)
    super_f_top = st.sidebar.number_input("상치전면 상단고 (DL.m)", value=4.00)
    super_r_top = st.sidebar.number_input("상치후면 상단고 (DL.m) [토층경계]", value=2.20)
    super_r_bot = st.sidebar.number_input("상치후면 하단고 (DL.m)", value=1.20)
    c_mid = st.sidebar.number_input("케이슨 상단고 (DL.m)", value=1.20)
    c_bot = st.sidebar.number_input("케이슨 바닥고 (DL.m)", value=-20.60)

    super_w = st.sidebar.number_input("상치폭 (m)", value=8.2)
    caisson_w = st.sidebar.number_input("케이슨 폭 (m)", value=18.4)
    front_toe_l = st.sidebar.number_input("전면 토우길이 (m)", value=2.0)
    rear_toe_l = st.sidebar.number_input("후면 토우길이 (m)", value=2.0)

    toe_bot = st.sidebar.number_input("Toe 하단고 (DL.m)", value=-20.60)
    toe_hf = st.sidebar.number_input("Toe 앞높이 (m)", value=0.60)
    toe_hb = st.sidebar.number_input("Toe 뒤높이 (m)", value=0.60)

    st.sidebar.divider()
    st.sidebar.header("🌍 지반 조건")
    st.sidebar.markdown("**[토층 1 : 부지고 ~ 상치후면상단]**")
    phi_1 = st.sidebar.number_input("토층1 내부마찰각 φ (°)", value=30.0)
    delta_1 = st.sidebar.number_input("토층1 벽면마찰각 δ (°)", value=0.0)
    st.sidebar.markdown("**[토층 2 : 상치후면상단 아래]**")
    phi_2 = st.sidebar.number_input("토층2 내부마찰각 φ (°)", value=40.0)
    delta_2 = st.sidebar.number_input("토층2 벽면마찰각 δ (°)", value=15.0)

    st.sidebar.markdown("**[단위중량]**")
    g_wet = st.sidebar.number_input("습윤단위중량 γ_t", value=18.0)
    g_sat = st.sidebar.number_input("포화단위중량 γ_sat", value=20.0)
    g_sub = st.sidebar.number_input("수중단위중량 γ_sub", value=10.0)

    st.sidebar.divider()
    st.sidebar.header("🌊 하중 및 수위 조건 상세")
    st.sidebar.markdown("**[상재하중 (q, kPa)]**")
    q_n_o = st.sidebar.number_input("평상시 (크레인O)", value=10.0)
    q_n_x = st.sidebar.number_input("평상시 (크레인X)", value=20.0)
    q_st_o = st.sidebar.number_input("폭풍시 (크레인O)", value=5.0)
    q_st_x = st.sidebar.number_input("폭풍시 (크레인X)", value=10.0)
    q_s_o = st.sidebar.number_input("지진시 (크레인O)", value=5.0)
    q_s_x = st.sidebar.number_input("지진시 (크레인X)", value=10.0)

    st.sidebar.markdown("**[수위 및 지진계수]**")
    curr_gwl = st.sidebar.number_input("잔류수위 (DL.m)", value=0.953, format="%.3f")
    kh_in = st.sidebar.number_input("지진계수 kh", value=0.123, format="%.3f", step=0.001) 

    st.markdown("<h1 style='text-align:center;'>⚓ 컨테이너부두 케이슨 토압산정 구조계산서</h1><hr>", unsafe_allow_html=True)
    st.caption("현재 적용 데이터: **컨테이너부두(이중토층, 항만설계사례집) (이층 지반, 3가지 하중조건 완벽 반영)**")
    st.divider()

    # --- 핵심 로직 분리 ---
    def generate_container(current_case_type, render_ui=True, rep_obj=None):
        def out_md(text, col=None):
            if render_ui:
                if col is not None: col.markdown(text)
                else: st.markdown(text)
            if rep_obj: rep_obj.md(text)
        def out_write(text, col=None):
            if render_ui:
                if col is not None: col.write(text)
                else: st.write(text)
            if rep_obj: rep_obj.md(text)
        def out_latex(eq, col=None):
            if render_ui:
                if col is not None: col.latex(eq)
                else: st.latex(eq)
            if rep_obj: rep_obj.latex(eq)
        def out_info(text, col=None):
            if render_ui:
                if col is not None: col.info(text)
                else: st.info(text)
            if rep_obj: rep_obj.info(text)
        def out_success(text, col=None):
            if render_ui:
                if col is not None: col.success(text)
                else: st.success(text)
            if rep_obj: rep_obj.success(text)
        def out_title(text, level, col=None):
            if render_ui:
                target = col if col is not None else st
                if level==1: target.header(text)
                elif level==2: target.subheader(text)
                elif level==3: target.markdown(f"### {text}")
            if rep_obj: rep_obj.title(text, level=level)
        def out_table(df, styled=None, col=None):
            if render_ui:
                target = col if col is not None else st
                target.table(styled if styled is not None else df)
            if rep_obj: rep_obj.table(df, styled=styled)
        def out_fig(f, col=None):
            if render_ui:
                target = col if col is not None else st
                target.pyplot(f)
            if rep_obj: rep_obj.fig(f)
        def out_img(img, cap, col=None):
            if render_ui:
                tgt = col if col is not None else st
                try: tgt.image(img, caption=cap, use_container_width=True)
                except Exception: tgt.info(f"💡 '{img}' 이미지를 실행 파일과 동일한 폴더에 위치시키면 삽도가 표시됩니다.")
            if rep_obj: rep_obj.static_img(img, caption=cap)
        def out_div():
            if render_ui: st.divider()
            if rep_obj: rep_obj.html += "<hr>"

        has_crane = "있음" in crane_type
        
        if "평상시" in current_case_type:
            base_q = q_n_o if has_crane else q_n_x
            is_seis = False
        elif "폭풍시" in current_case_type:
            base_q = q_st_o if has_crane else q_st_x
            is_seis = False
        else:
            base_q = q_s_o if has_crane else q_s_x
            is_seis = True

        curr_q = base_q if "有" in q_type else 0.0

        out_info(f"**💡 상재하중 적용 기준**\n"
                 f"- 컨테이너 안벽 설계 시 하중 상태(**{current_case_type}**)와 크레인 가동 여부(**{crane_type}**)에 따라 배면의 기본 상재하중 기준이 달라집니다.\n"
                 f"- 또한 활동 및 전도 안전율의 최악의 조건을 찾기 위해 **상재하중 유/무({q_type})**를 반드시 교차 검토해야 합니다.\n"
                 f"- 현재 설정에 의해 적용되는 등분포 상재하중은 **{curr_q} kPa** 이며, 적용 잔류수위는 **DL {curr_gwl:.3f} m** 입니다.")

        engine_layer1 = UltimateCaissonEngine(phi_1, delta_1)
        engine_layer2 = UltimateCaissonEngine(phi_2, delta_2)

        if is_seis:
            kh_above = kh_in 
            w_top = g_wet * max(0, c_top - curr_gwl)
            h_layer = max(0, curr_gwl - c_bot)
            num = 2 * (w_top + curr_q) + (g_sat * h_layer)
            den = 2 * (w_top + curr_q) + (g_sub * h_layer)
            k_prime = (num / den) * kh_in if den > 0 else kh_in
            kh_below = k_prime 
        else:
            kh_above = 0.0
            k_prime = 0.0
            kh_below = 0.0
            w_top = 0.0

        arm_toe = front_toe_l + caisson_w + rear_toe_l
        arm_virt = front_toe_l + caisson_w
        arm_wedge = front_toe_l + caisson_w + (rear_toe_l / 3.0)

        geo = engine_layer2.calc_exact_angles(kh_below) 
        h_rise = rear_toe_l * geo['tan_xi_prime'] 
        toe_top_dl = toe_bot + toe_hb
        intersect_dl = toe_top_dl + h_rise

        kai_L1_above, kah_L1_above = engine_layer1.calc_kah(delta_1, 0.0, kh_above)
        kai_L2_above, kah_L2_above = engine_layer2.calc_kah(delta_2, 0.0, kh_above)
        kai_L2_below, kah_L2_below = engine_layer2.calc_kah(delta_2, 0.0, kh_below)
        kai_L2_wedge, kah_L2_wedge = engine_layer2.calc_kah(phi_2, geo['psi_calc'], kh_below)
        kai_L2_toe,   kah_L2_toe   = engine_layer2.calc_kah(delta_2, 0.0, kh_below)

        out_title("1. 설계 조건 요약", level=1)
        
        t_above = math.degrees(math.atan(kh_above))
        t_below = math.degrees(math.atan(kh_below))
        
        col_s1, col_s2 = st.columns(2) if render_ui else (None, None)
        
        out_md("**[기하 구조 및 수위]**", col=col_s1)
        df_s1 = pd.DataFrame({
            "구분": ["상치폭 / 케이슨폭", "상치후면 상/하단고 (토층경계)", "케이슨 상단고 / 바닥고", "Toe 상단고", "적용 잔류수위"],
            "제원": [f"{super_w:.1f}m / {caisson_w:.1f}m", f"DL {super_r_top:.2f}m / DL {super_r_bot:.2f}m", f"DL {c_mid:.2f}m / DL {c_bot:.2f}m", f"DL {toe_top_dl:.2f}m", f"DL {curr_gwl:.3f}m"]
        })
        out_table(df_s1, col=col_s1)

        out_md("**[지반 상수 및 하중]**", col=col_s2)
        applied_kh_label = f"수상 {kh_above:.4f} (Θ={t_above:.2f}°) / 수중 {kh_below:.4f} (Θ={t_below:.2f}°)" if is_seis else "0.0000 (Θ=0.00°)"
        df_s2 = pd.DataFrame({
            "구분": ["토층1 (상) φ / δ", "토층2 (하) φ / δ", "적용 상재하중(q)", "적용 지진계수(k, k') 및 합성각(Θ)", "단위중량(wet/sat/sub)"],
            "값": [f"{phi_1}° / {delta_1}°", f"{phi_2}° / {delta_2}°", f"{curr_q:.1f} kPa", applied_kh_label, f"{g_wet}/{g_sat}/{g_sub} kN/m³"]
        })
        out_table(df_s2, col=col_s2)

        out_div()

        if is_seis:
            out_title("1-1. 지진시 겉보기 진도($k'$) 산정 근거 (항만설계기준 정밀식)", level=2)
            out_md(r"**항만 및 어항설계기준(KDS)에 따라 수중부 지반의 간극수압, 유효응력 및 상/하부 토층과 상재하중을 모두 고려한 정밀 겉보기 진도식을 적용합니다.**")
            out_latex(r"k' = \frac{2(\sum \gamma_t h_i + \sum \gamma_{sat} h_j + \omega) + \gamma_{sat} h}{2[\sum \gamma_t h_i + \sum (\gamma - 10) h_j + \omega] + (\gamma - 10)h} k")
            
            out_md("""
            **[공식 기호 상세 설명]**
            * $k'$: 겉보기 진도 (수중부 지진토압 산정용 보정 진도)
            * $k$: 설계 진도 (지진계수, $k_h$)
            * $\\omega$: 지표면의 단위면적당 재하하중 (적용 상재하중)
            * $\\gamma_t$: 잔류수위 위 토층의 습윤 단위체적중량
            * $\\gamma_{sat}$: 잔류수위 아래 포화된 흙의 공기 중 단위체적중량
            * $\\gamma - 10$: 물의 단위중량을 편의상 $10kN/m^3$로 가정한 흙의 수중 단위체적중량($\\gamma_{sub}$)
            * $h_i$: 잔류수위 위 $i$번째 토층의 두께 ($m$)
            * $h_j$: 잔류수위 아래이면서 토압을 산정하는 대상 층보다 위에 있는 $j$번째 토층 두께 ($m$)
            * $h$: 잔류수위 아래에서 대상 토압을 산정하고자 하는 토층의 던께 ($m$)
            """)
            
            out_md("**[수중부 레벨별 겉보기 진도 산정 상세 내역]**")
            out_md(f"**① 공통 적용값($\\sum\\gamma_t h_i + \\omega$) 상세 계산**\n"
                   f"- 잔류수위 상부 토층 두께 = 부지고({c_top:.2f}) - 잔류수위({curr_gwl:.3f}) = **{max(0, c_top - curr_gwl):.3f} m**\n"
                   f"- 상부토층 중량($\\sum\\gamma_t h_i$) = 습윤단위중량({g_wet}) $\\times$ 두께({max(0, c_top - curr_gwl):.3f}) = **{w_top:.2f} kPa**\n"
                   f"- 공통 적용값 = 상부토층 중량({w_top:.2f}) + 상재하중({curr_q:.2f}) = **{w_top + curr_q:.2f} kPa**")
            out_write(f"**② 심도별 겉보기 진도 산출 표** (적용 $k_h$ = {kh_in:.4f}, $\\gamma_{{sat}}$ = {g_sat}, $\\gamma_{{sub}}$ = {g_sub})")
            
            k_levels = []
            for label, depth in [("잔류수위", curr_gwl), ("파괴면접점", intersect_dl), ("Toe상단", toe_top_dl), ("케이슨바닥", c_bot)]:
                if depth >= curr_gwl: continue
                h_z = curr_gwl - depth
                term_top = 2 * (w_top + curr_q)
                term_sat = g_sat * h_z
                term_sub = g_sub * h_z
                num_z = term_top + term_sat
                den_z = term_top + term_sub
                k_z = (num_z / den_z) * kh_in
                k_levels.append({
                    "위치": label, 
                    "심도(DL.m)": depth, 
                    "수중두께 h(m)": h_z, 
                    "분자(관성력비례)": f"{num_z:.2f} (=2*{w_top+curr_q:.2f}) + {term_sat:.2f}(={g_sat}*{h_z:.3f})",
                    "분모(유효응력비례)": f"{den_z:.2f} (=2*{w_top+curr_q:.2f}) + {term_sub:.2f}(={g_sub}*{h_z:.3f})",
                    "증폭비": f"{(num_z/den_z):.4f}", 
                    "겉보기진도(k')": k_z
                })
            
            if k_levels:
                df_k = pd.DataFrame(k_levels)
                out_table(df_k, styled=df_k.style.format({"심도(DL.m)": "{:.2f}", "수중두께 h(m)": "{:.2f}", "겉보기진도(k')": "{:.4f}"}))
                
            out_info(f"👉 **구조물 전체의 활동/전도 안정성 검토(주동토압계수 산출)를 위해, 파괴면이 도달하는 최대 심도인 '케이슨 바닥(DL {c_bot:.2f}m)' 기준의 대표 겉보기 진도 **$k' = {kh_below:.4f}$** 를 설계 기준치로 일괄 적용합니다.**")
            out_div()

        out_title("2. 케이슨에 작용하는 토압 (개념 및 원리)", level=1)
        col_img1, col_img2 = st.columns(2) if render_ui else (None, None)
        out_img("활동쐐기.png", "[그림 1] 뒷굽판 길이에 따른 활동쐐기 형성 원리", col=col_img1)
        out_img("케이슨 토압개념도.png", "[그림 2] 뒷굽판이 짧은 경우의 케이슨 토압 개념도", col=col_img2)

        out_md("""
        #### 1) 활동쐐기(Sliding Wedge) 형성의 기본 원리
        뒷굽판(Heel)이 있는 중력식 구조물은 뒷굽판의 길이에 따라 파괴면(활동면)이 형성되는 양상이 달라지며, 이는 토압 산정 방식의 기준이 됩니다.
        * **(a) 뒷굽판이 긴 경우:** 뒷굽판 끝단에서 발생하는 활동쐐기가 케이슨의 뒷면(연직면)과 만나지 않고 지표면으로 직접 향합니다. 이 경우, 뒷굽판 상부의 흙은 구조물과 일체로 거동하는 것으로 간주하여 흙 자체의 무게를 구조물의 자중에 포함시킵니다. 파괴면이 흙 내부에서만 형성되므로 마찰각은 흙의 **내부마찰각($\\phi$)**을 적용합니다.
        * **(b) 뒷굽판이 짧은 경우:** 활동쐐기가 뒷면 연직면과 교차하게 됩니다. 구조물과 배면토 사이의 상호작용이 복합적으로 발생하므로 구간을 나누어 토압을 산정해야 합니다.

        #### 2) 케이슨 구간별 토압 산정 상세
        뒷굽판으로 인해 배면 형상이 꺾인 경우(Broken Backface), Coulomb의 토압 이론을 바탕으로 각 단면별로 작용하는 주동토압($P_1, P_2, P_3$)을 분할 산정합니다. 이때 각 작용면의 특성에 따라 **벽면마찰각($\\delta$)의 적용 기준이 상이**함에 유의해야 합니다.

        * **① $P_1$ 구간 (직립면 상부):** 콘크리트(구조물)와 배면토(흙) 사이의 경계면이므로 **벽면마찰각($\\delta$)**을 적용합니다. 벽체 경사각 $\\alpha = 0^\\circ$로 설정하여 일반적인 주동토압과 동일한 원리로 계산합니다.
        * **② $P_2$ 구간 (가상 경사면 쐐기부):** 본체 뒷면과 뒷굽판 끝을 연결하는 가상의 파괴면(Virtual Sliding Plane)입니다. 흙과 흙 사이의 입자 간 마찰이 지배적이므로 벽면마찰각이 아닌 흙의 **내부마찰각($\\phi$)**을 적용합니다. 연직면에 대해 가상벽면사각 $\\Psi$만큼 기울어진 경사면($\\alpha = \\Psi$)으로 해석하며, 가상면 안쪽의 흙(활동쐐기 내부)은 구조물 자중에 포함시켜 활동 및 전도 저항력에 기여하는 것으로 산정합니다.
        * **③ $P_3$ 구간 (뒷굽판 단부 수직면):** 다시 뒷굽판 콘크리트와 흙이 만나게 되므로 **벽면마찰각($\\delta$)**을 적용합니다. $\\alpha = 0^\\circ$이며 심도(Depth)가 깊기 때문에 토압 강도가 단면 내에서 가장 크게 나타납니다.
        """)
        out_div()

        out_title(f"3. {current_case_type} 컨테이너부두 케이슨 토압산정 구조계산서", level=1)
        col_f1, col_f2 = st.columns([2.0, 1.2]) if render_ui else (None, None)

        out_md("#### 1) 주동붕괴각 및 활동쐐기각 산출 근거 (하부 주 지지층 기준)", col=col_f1)
        
        if is_seis:
            out_md(r"**① 주동붕괴각($\zeta$) 공식 (지진시: Mononobe-Okabe 이론)**", col=col_f1)
            out_latex(r"\cot(\zeta-\beta) = -\tan(\Phi+\delta-\beta) + \sec(\Phi+\delta-\beta)\sqrt{\frac{\cos(\delta+\Theta)\sin(\Phi+\delta)}{\cos(-\beta)\sin(\Phi-\beta-\Theta)}}", col=col_f1)
            theta_above = math.degrees(math.atan(kh_above))
            theta_below = math.degrees(math.atan(kh_below))
            out_write(fr"- 수상부 지진합성각 $\Theta_{{above}} = \tan^{{-1}}({kh_above:.4f}) = \mathbf{{{theta_above:.2f}^\circ}}$", col=col_f1)
            out_write(fr"- 수중부 지진합성각 $\Theta_{{below}} = \tan^{{-1}}({kh_below:.4f}) = \mathbf{{{theta_below:.2f}^\circ}}$ (파괴면 계산 기준)", col=col_f1)
            theta_val = theta_below
        else:
            out_md(r"**① 주동붕괴각($\zeta$) 공식 (상시/평상시: Coulomb 이론)**", col=col_f1)
            out_latex(r"\cot(\zeta-\beta) = -\tan(\Phi+\delta-\beta) + \sec(\Phi+\delta-\beta)\sqrt{\frac{\cos\delta\sin(\Phi+\delta)}{\cos(-\beta)\sin(\Phi-\beta)}}", col=col_f1)
            theta_val = 0.0

        out_md("""
        **[공식 기호 설명]**
        * $\\zeta$: 주동붕괴각 (파괴면이 수평면과 이루는 각도)
        * $\\Phi$: 흙의 내부마찰각
        * $\\delta$: 벽면마찰각 (구조물과 흙 사이의 마찰각)
        * $\\beta$: 배면 지표면의 경사각 (본 계산에서는 $0^\\circ$ 적용)
        * $\\Theta$: 지진합성각 (수평진도 $k_h$에 의해 결정, $\\Theta = \\tan^{-1}(k_h)$)
        """, col=col_f1)

        out_md(r"**[주동붕괴각 상세 계산 과정]**", col=col_f1)
        out_info(fr"- 적용치: $\Phi={phi_2}^\circ, \delta={delta_2}^\circ, \beta=0^\circ, \Theta={theta_val:.2f}^\circ$", col=col_f1)
        out_write(fr"- 근호 안 분자 = $\cos({delta_2}^\circ+{theta_val:.2f}^\circ) \cdot \sin({phi_2}^\circ+{delta_2}^\circ) = \mathbf{{{geo['root_num']:.4f}}}$", col=col_f1)
        out_write(fr"- 근호 안 분모 = $\cos(0^\circ) \cdot \sin({phi_2}^\circ-0^\circ-{theta_val:.2f}^\circ) = \mathbf{{{geo['root_den']:.4f}}}$", col=col_f1)
        out_write(fr"- $\sqrt{{\text{{분자}}/\text{{분모}}}} = \mathbf{{{geo['root_val']:.4f}}}$", col=col_f1)
        out_write(fr"- 제1항 ($-\tan(\Phi+\delta-\beta)$) = $\mathbf{{{geo['term1']:.4f}}}$", col=col_f1)
        out_write(fr"- 제2항 ($\sec(\Phi+\delta-\beta) \cdot \sqrt{{\dots}}$) = $\mathbf{{{geo['term2']:.4f}}}$", col=col_f1)
        out_write(fr"- $\cot(\zeta) = {geo['term1']:.4f} + {geo['term2']:.4f} = \mathbf{{{geo['cot_val']:.4f}}}$", col=col_f1)
        out_write(fr"- $\zeta = \cot^{{-1}}({geo['cot_val']:.4f}) = \mathbf{{{geo['zeta']:.2f}^\circ}}$", col=col_f1)
        
        out_md(r"**② 활동쐐기각($\xi'$) 및 가상벽면사각($\Psi$) 산정**", col=col_f1)
        out_latex(r"\xi' = 90^\circ + \Phi - \zeta \quad / \quad \Psi = 90^\circ - \xi'", col=col_f1)
        out_write(fr"- 활동쐐기각 $\xi' = 90 + {phi_2} - {geo['zeta']:.2f} = \mathbf{{{geo['xi_prime']:.2f}^\circ}}$", col=col_f1)
        out_write(fr"- 가상벽면사각 $\Psi = 90 - {geo['xi_prime']:.2f} = \mathbf{{{geo['psi_calc']:.2f}^\circ}}$", col=col_f1)

        out_md(r"**③ 파괴면 접점 상승 높이($\Delta H$)**", col=col_f1)
        out_latex(r"\Delta H = L_{toe(후면)} \times \tan(\xi')", col=col_f1)
        out_write(fr"- 상승 높이 $\Delta H = {rear_toe_l:.2f}\text{{m}} \times \tan({geo['xi_prime']:.2f}^\circ) = \mathbf{{{h_rise:.2f}\text{{m}}}}$", col=col_f1)
        out_success(fr"👉 파괴면 접점 = Toe상단(DL {toe_top_dl:.2f}) + {h_rise:.2f} = **DL {intersect_dl:.2f}m**", col=col_f1)
        out_write("---", col=col_f1)

        out_md("#### 2) 구간별 주동토압계수($K_{ah}$) 산정", col=col_f1)
        out_md(r"**① 주동토압계수($K_{ah}$) 공식**", col=col_f1)
        out_latex(r"K_{{ah}} = K_{{ai}} \cdot \cos(\delta + \Psi) = \frac{\cos^2(\Phi-\theta-\Psi) \cdot \cos(\delta+\Psi)}{\cos\theta \cos^2\Psi \cos(\delta+\Psi+\theta) \left[ 1 + \sqrt{\frac{\sin(\Phi+\delta)\sin(\Phi-\beta-\theta)}{\cos(\delta+\Psi+\theta)\cos(\Psi-\beta)}} \right]^2}", col=col_f1)
        out_md(r"**② 구역별 주동토압계수 산출 결과 상세**", col=col_f1)
        out_write(fr"- **토층1 (수상부 연직벽):** $\Phi = {phi_1}^\circ, \delta = {delta_1}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_above:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_L1_above:.4f}, \quad \mathbf{{K_{{ah}} = {kah_L1_above:.4f}}}$", col=col_f1)
        out_write(fr"- **토층2 (수상부 연직벽):** $\Phi = {phi_2}^\circ, \delta = {delta_2}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_above:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_L2_above:.4f}, \quad \mathbf{{K_{{ah}} = {kah_L2_above:.4f}}}$", col=col_f1)
        out_write(fr"- **토층2 수중부 (연직벽):** $\Phi = {phi_2}^\circ, \delta = {delta_2}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_L2_below:.4f}, \quad \mathbf{{K_{{ah}} = {kah_L2_below:.4f}}}$", col=col_f1)
        out_write(fr"- **토층2 쐐기부 (가상배면):** $\Phi = {phi_2}^\circ, \delta = \Phi, \Psi = {geo['psi_calc']:.2f}^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_L2_wedge:.4f}, \quad \mathbf{{K_{{ah}} = {kah_L2_wedge:.4f}}}$", col=col_f1)
        out_write(fr"- **토층2 토우부 (연직벽):** $\Phi = {phi_2}^\circ, \delta = {delta_2}^\circ, \Psi = 0^\circ, \mathbf{{\Theta = {t_below:.2f}^\circ}} \rightarrow K_{{ai}} = {kai_L2_toe:.4f}, \quad \mathbf{{K_{{ah}} = {kah_L2_toe:.4f}}}$", col=col_f1)

        out_md("**[파괴면 및 쐐기 제원 요약]**", col=col_f2)
        summary_geo = pd.DataFrame({
            "항목": ["Toe 바닥고", "Toe 상단(기점)", "하부 마찰각(Φ/δ)", "가상벽면각(Ψ)", "파괴면 접점레벨"],
            "제원": [f"DL {toe_bot:.2f}m", f"DL {toe_top_dl:.2f}m", f"{phi_2}° / {delta_2}°", f"{geo['psi_calc']:.2f}°", f"DL {intersect_dl:.2f}m"]
        })
        out_table(summary_geo, col=col_f2)

        out_md("**[파괴면 보조 삽도 (상세표시)]**", col=col_f2)
        fig_sk, ax_sk = plt.subplots(figsize=(4, 4.5))
        ax_sk.plot([0, 0], [toe_bot-1, c_top+1], 'k-', lw=3)
        ax_sk.fill([0, rear_toe_l, rear_toe_l, 0], [toe_bot, toe_bot, toe_top_dl, toe_top_dl], color='lightgray', ec='black', label='Toe')
        ax_sk.plot([rear_toe_l, 0], [toe_top_dl, intersect_dl], 'r--', lw=2.5, label='Failure Plane')
        
        ax_sk.text(0, intersect_dl, f" DL {intersect_dl:.2f} ", color='red', ha='right', va='bottom', fontweight='bold')
        ax_sk.text(rear_toe_l, toe_top_dl, f" DL {toe_top_dl:.2f}", color='blue', ha='left', va='center')
        ax_sk.text(rear_toe_l/2, toe_bot-0.2, f"L={rear_toe_l}m", ha='center', va='top', fontsize=9)
        
        ax_sk.annotate('', xy=(0, intersect_dl), xytext=(0, toe_top_dl), arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
        ax_sk.text(-0.05, (intersect_dl + toe_top_dl)/2, f"ΔH={h_rise:.2f}m", ha='right', va='center', color='green', fontweight='bold', fontsize=10)
        
        ax_sk.plot([0, rear_toe_l+0.3], [toe_top_dl, toe_top_dl], 'b:', lw=1.2)
        ax_sk.text(rear_toe_l - 0.05, toe_top_dl + 0.1, f"ξ'={geo['xi_prime']:.2f}°", color='red', ha='right', va='bottom', fontsize=9)
        ax_sk.text(0.05, intersect_dl - 0.4, f"Ψ={geo['psi_calc']:.2f}°", color='red', ha='left', va='top', fontsize=9)
        
        ax_sk.axhline(super_r_top, color='blue', ls=':', label='토층 경계')
        ax_sk.axhline(curr_gwl, color='cyan', ls=':', label='잔류수위')
        ax_sk.text(0, super_r_top, f" DL {super_r_top:.2f}", color='blue', ha='left', va='bottom', fontsize=8)
        
        ax_sk.axis('off')
        out_fig(fig_sk, col=col_f2)

        out_div()

        out_title("4. 심도별 수평/연직토압 강도 산정표", level=2)
        nodes = [
            (1, "부지고(상)", c_top, 0, 0, kah_L1_above, delta_1, 0.0),
            (2, "토층경계(상)", super_r_top, g_wet, c_top - super_r_top, kah_L1_above, delta_1, 0.0),
            (3, "토층경계(하)", super_r_top, 0, 0, kah_L2_above, delta_2, 0.0), 
            (4, "잔류수위(상)", curr_gwl, g_wet, super_r_top - curr_gwl, kah_L2_above, delta_2, 0.0),
            (5, "잔류수위(하)", curr_gwl, 0, 0, kah_L2_below, delta_2, 0.0),
            (6, "파괴면접점(상)", intersect_dl, g_sub, curr_gwl - intersect_dl, kah_L2_below, delta_2, 0.0),
            (7, "파괴면접점(하)", intersect_dl, 0, 0, kah_L2_wedge, phi_2, geo['psi_calc']), 
            (8, "Toe상단(상)", toe_top_dl, g_sub, intersect_dl - toe_top_dl, kah_L2_wedge, phi_2, geo['psi_calc']), 
            (9, "Toe상단(하)", toe_top_dl, 0, 0, kah_L2_toe, delta_2, 0.0),           
            (10, "케이슨바닥", c_bot, g_sub, toe_top_dl - c_bot, kah_L2_toe, delta_2, 0.0)
        ]
        table_rows = []
        cum_sig = 0.0
        for n, lbl, dl, gamma, h, kah, d, psi in nodes:
            if gamma > 0: cum_sig += gamma * h
            ph = (cum_sig + curr_q) * kah
            pv = ph * math.tan(math.radians(d + psi))
            table_rows.append({"Node": n, "위치": lbl, "심도(DL.m)": dl, "Σγh(kPa)": cum_sig, "Kah": kah, "ph(kN/m²)": ph, "pv(kN/m²)": pv})
        df_na = pd.DataFrame(table_rows).set_index("Node")
        
        out_table(df_na, styled=df_na.style.format({"심도(DL.m)": "{:.2f}", "Σγh(kPa)": "{:.2f}", "Kah": "{:.4f}", "ph(kN/m²)": "{:.3f}", "pv(kN/m²)": "{:.3f}"}))

        out_title("5. 구간별 수평력 및 모멘트 산정표", level=2)
        out_info(f"**💡 연직토압 팔거리(x) 작용점 산출식 상세:**\n"
                 f"- **상단부 연직벽 (지표면~파괴면접점):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) = **{arm_virt:.1f}m**\n"
                 f"- **파괴면 쐐기부 (파괴면접점~Toe상단):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) + 후면({rear_toe_l:.1f})/3 = **{arm_wedge:.2f}m**\n"
                 f"- **토우하단부 (Toe상단~바닥):** 전면({front_toe_l:.1f}) + 폭({caisson_w:.1f}) + 후면({rear_toe_l:.1f}) = **{arm_toe:.1f}m**")

        segments = [
            (f"지표면 ~ 토층경계\n(DL {c_top:.2f} ~ {super_r_top:.2f}m)", c_top, super_r_top, kah_L1_above, delta_1, 0.0, arm_virt),
            (f"토층경계 ~ 잔류수위\n(DL {super_r_top:.2f} ~ {curr_gwl:.3f}m)", super_r_top, curr_gwl, kah_L2_above, delta_2, 0.0, arm_virt),
            (f"잔류수위 ~ 파괴면접점\n(DL {curr_gwl:.3f} ~ {intersect_dl:.2f}m)", curr_gwl, intersect_dl, kah_L2_below, delta_2, 0.0, arm_virt),
            (f"파괴면접점 ~ Toe상단\n(DL {intersect_dl:.2f} ~ {toe_top_dl:.2f}m)", intersect_dl, toe_top_dl, kah_L2_wedge, phi_2, geo['psi_calc'], arm_wedge), 
            (f"Toe상단 ~ 케이슨바닥\n(DL {toe_top_dl:.2f} ~ {c_bot:.2f}m)", toe_top_dl, c_bot, kah_L2_toe, delta_2, 0.0, arm_toe)             
        ]
        
        f_rows = []
        cum_sig = 0.0
        for lbl, z_t, z_b, kah, d, psi, arm_x in segments:
            h = z_t - z_b
            if h <= 0: continue
            tan_dp = math.tan(math.radians(d + psi))
            p_t = (cum_sig + curr_q) * kah
            cum_sig += (g_wet if z_t > curr_gwl else g_sub) * h
            p_b = (cum_sig + curr_q) * kah
            
            ph1, arm_y1 = p_t * h, (z_b - c_bot) + (h/2.0)
            pv1 = ph1 * tan_dp 
            mh1, mv1 = ph1 * arm_y1, pv1 * arm_x
            f_rows.append({"구분": lbl, "종류": "1(사각)", "Ph": ph1, "Pv": pv1, "y(수평팔)": arm_y1, "팔길이(x)": arm_x, "Mh": mh1, "Mv": mv1})
            
            ph2, arm_y2 = 0.5 * (p_b - p_t) * h, (z_b - c_bot) + (h/3.0)
            pv2 = ph2 * tan_dp 
            mh2, mv2 = ph2 * arm_y2, pv2 * arm_x
            f_rows.append({"구분": "", "종류": "2(삼각)", "Ph": ph2, "Pv": pv2, "y(수평팔)": arm_y2, "팔길이(x)": arm_x, "Mh": mh2, "Mv": mv2})
            
            f_rows.append({"구분": "▶ 합 계", "종류": "-", "Ph": ph1+ph2, "Pv": pv1+pv2, "y(수평팔)": None, "팔길이(x)": None, "Mh": mh1+mh2, "Mv": mv1+mv2})

        df_final = pd.DataFrame(f_rows)
        styled_df = df_final.style.set_properties(**{'white-space': 'pre-wrap', 'text-align': 'center'}).format(
            {"Ph": "{:.2f}", "Pv": "{:.2f}", "y(수평팔)": "{:.2f}", "팔길이(x)": "{:.2f}", "Mh": "{:.2f}", "Mv": "{:.2f}"}, na_rep=""
        )
        out_table(df_final, styled=styled_df)

        df_sums = df_final[df_final["구분"] == "▶ 합 계"]
        out_success(f"✅ **최종 합계 결과 ({current_case_type}, 상재하중 {q_type.split()[1]}):**\n\n수평력 $\\Sigma P_h = {df_sums['Ph'].sum():.2f}$ kN/m, 수평모멘트 $\\Sigma M_h = {df_sums['Mh'].sum():.2f}$ kN·m/m\n\n연직력 $\\Sigma P_v = {df_sums['Pv'].sum():.2f}$ kN/m, 연직모멘트 $\\Sigma M_v = {df_sums['Mv'].sum():.2f}$ kN·m/m")

        out_title("6. 케이슨 모식도 및 수평토압 분포도 (이층지반 단차 표출)", level=2)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), sharey=True, gridspec_kw={'width_ratios': [1.2, 1]})
        
        # --- ax1: 케이슨 모식도 ---
        x_ft = 0
        x_fw = front_toe_l
        x_rw = front_toe_l + caisson_w
        x_rt = front_toe_l + caisson_w + rear_toe_l
        
        cx = [x_ft, x_rt, x_rt, x_rw, x_rw, x_fw, x_fw, x_ft, x_ft]
        cy = [toe_bot, toe_bot, toe_bot + toe_hb, toe_bot + toe_hb, c_mid, c_mid, toe_bot + toe_hf, toe_bot + toe_hf, toe_bot]
        
        ax1.plot(cx, cy, 'k-', lw=2)
        ax1.fill(cx, cy, color='lightgray', alpha=0.5, label='케이슨')
        
        # 상치콘크리트 
        x_step = x_fw + super_w
        sx = [x_fw, x_rw, x_rw, x_step, x_step, x_fw, x_fw]
        sy = [c_mid, c_mid, super_r_top, super_r_top, super_f_top, super_f_top, c_mid]
        ax1.plot(sx, sy, 'k-', lw=1.5)
        ax1.fill(sx, sy, color='darkgray', alpha=0.7, label='상치콘크리트')

        ax1.plot([x_step, x_rt + 5], [c_top, c_top], 'brown', lw=2, label='부지고')
        ax1.axhline(super_r_top, color='blue', ls=':', lw=1.5, label='토층경계')
        ax1.axhline(curr_gwl, color='cyan', ls='--', lw=1.5, label='잔류수위')
        ax1.plot([x_rw, x_rt], [intersect_dl, toe_top_dl], 'r--', lw=2, label='파괴면 접점/활동면')
        
        ax1.text((x_fw + x_rw)/2, (c_bot + c_mid)/2, f"케이슨 폭 = {caisson_w:.1f}m\n벽체고 = {c_mid-c_bot:.2f}m", ha='center', va='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec='gray'))
        ax1.text((x_fw + x_step)/2, (c_mid + super_f_top)/2, f"상치폭 = {super_w:.1f}m\n상단 = DL {super_f_top:.2f}m", ha='center', va='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec='gray'))
        ax1.text((x_step + x_rw)/2, (c_mid + super_r_top)/2, f"후면폭 = {caisson_w - super_w:.1f}m\n상단 = DL {super_r_top:.2f}m", ha='center', va='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec='gray'))
        ax1.text(x_ft + front_toe_l/2, toe_bot - 0.6, f"전면토우\n{front_toe_l:.1f}m", ha='center', va='top', fontsize=8, color='blue')
        ax1.text(x_rw + rear_toe_l/2, toe_bot - 0.6, f"후면토우\n{rear_toe_l:.1f}m", ha='center', va='top', fontsize=8, color='blue')
        ax1.text(x_rw + 0.2, intersect_dl, f"◀ 파괴접점 DL {intersect_dl:.2f}m\n  (상승고 ΔH={h_rise:.2f}m)", color='red', ha='left', va='center', fontsize=8, fontweight='bold')

        ax1.set_xlim(-1, x_rt + 5)
        ax1.set_ylim(c_bot - 2, super_f_top + 2)
        ax1.set_xlabel("폭 (m)")
        ax1.set_ylabel("심도 (DL.m)")
        ax1.set_title("케이슨 구조 모식도 (제원 매핑)")
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, linestyle=':', alpha=0.6)

        # --- ax2: 수평토압 분포도 ---
        nodes_plot = [
            (c_top, kah_L1_above), (super_r_top, kah_L1_above), 
            (super_r_top, kah_L2_above), (curr_gwl, kah_L2_above), 
            (curr_gwl, kah_L2_below), (intersect_dl, kah_L2_below), 
            (intersect_dl, kah_L2_wedge), (toe_top_dl, kah_L2_wedge), 
            (toe_top_dl, kah_L2_toe), (c_bot, kah_L2_toe)
        ]
        pz, pp = [], []
        cs, pz_old = 0.0, c_top
        for z, kah in nodes_plot:
            if z < pz_old:
                cs += (g_wet if pz_old > curr_gwl else g_sub) * (pz_old - z)
                pz_old = z
            pz.append(z)
            pp.append((cs + curr_q) * kah)
            
        ax2.plot([0, 0], [c_bot, c_top], 'k-', lw=3)
        ax2.fill_betweenx(pz, 0, pp, color='orange', alpha=0.3)
        ax2.plot(pp, pz, 'r-', lw=1.5)
        for i, (p, z) in enumerate(zip(pp, pz)):
            if p > 0.01: ax2.text(p + max(pp)*0.03, z, f"{p:.1f}", va='center', fontsize=8, color='red')
        for z in sorted(list(set(pz))):
            ax2.axhline(z, color='gray', ls=':', lw=0.8)
        
        ax2.set_xlabel("토압 강도 (kN/m²)")
        ax2.set_title("수평토압 분포 모식도")
        
        out_fig(fig)

    # 1. 화면 UI 출력
    generate_container(case_type, render_ui=True, rep_obj=None)

    # 2. 통합 보고서 생성 백그라운드 구동 (분할 없이 순차 출력)
    integrated_rep = ReportBuilder()
    integrated_rep.html += "<h1 style='text-align:center;'>⚓ 컨테이너부두 케이슨 토압산정 통합 구조계산서</h1><hr>"
    integrated_rep.md("*현재 적용 데이터: **컨테이너부두(이중토층, 항만설계사례집) (이층 지반, 3가지 하중조건 완벽 반영)***")
    for ct in ["평상시 (Normal)", "폭풍시 (Storm)", "지진시 (Seismic)"]:
        integrated_rep.html += f"<h2 style='color:#2c3e50; background-color:#e8f0fe; padding:10px;'>■ 해석 상태: {ct}</h2>"
        generate_container(ct, render_ui=False, rep_obj=integrated_rep)

    render_fast_download(integrated_rep, "컨테이너부두_케이슨_토압산정구조계산서")
