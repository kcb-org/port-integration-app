import streamlit as st
import pandas as pd
import math
import os
import base64
import re
import io
import urllib.request
import concurrent.futures
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# ★ 화면 꽉 차게 만들기 (Streamlit 최상단 필수 설정)
st.set_page_config(page_title="파고 전달율 산정 시스템", layout="wide")

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

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
# ★ 보고서 생성기 
# =====================================================================
class ReportBuilder:
    def __init__(self):
        self.html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>파고 전달율 산정 보고서</title>
        <script>
          window.MathJax = {
            tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], processEscapes: true },
            options: { ignoreHtmlClass: "tex2jax_ignore", processHtmlClass: "tex2jax_process" }
          };
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body { font-family: 'Malgun Gothic', 'NanumGothic', sans-serif; line-height: 1.6; padding: 20px; color: #000000; max-width: 1200px; margin: auto; font-weight: 700;}
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 15px; background: white; color: #000000; border: 2px solid #000; margin-left: auto; margin-right: auto;}
            th, td { border: 1px solid #000; padding: 12px; text-align: center; font-weight: 800; color: #000000;}
            th { background-color: #e0e0e0; font-weight: 900; color: #000;}
            h2 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 30px; font-weight: 900; font-size: 22px; }
            h3 { color: #2c3e50; margin-top: 25px; margin-bottom: 10px; font-weight: 900; font-size: 18px; }
            p { font-size: 15.5px; font-weight: 800; color: #000000; margin-bottom: 6px; }
            .eq { background: #f8f9fa; padding: 10px; border-left: 4px solid #1a73e8; margin: 10px 0; overflow-x: auto; font-size: 1.15em; color: #000000; font-weight: bold;}
            .info-box { background-color: #e8f0fe; border-left: 4px solid #1a73e8; padding: 12px; margin: 10px 0; color: #000000; font-weight: 800; }
            .warn-box { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 10px 0; color: #000000; font-weight: 800; }
            .figure { text-align: center; margin: 20px 0; }
            .two-col-list { column-count: 2; column-gap: 30px; list-style-position: inside; margin: 5px 0 15px 0; padding-left: 5px; }
            .two-col-list li { margin-bottom: 6px; font-size: 15px; font-weight: 800; color: #000000; }
            .calc-step { background: #fdfdfd; padding: 12px 15px; border-left: 5px solid #4caf50; margin-bottom: 12px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .calc-step p { margin: 4px 0; font-size: 15px; line-height: 1.7; color: #000000 !important; font-weight: 900 !important; }
            .calc-step ul { margin: 4px 0 8px 20px; }
            .calc-step li { margin-bottom: 8px; font-size: 15.5px; font-weight: 900; color: #000000; }
            .calc-step b { color: #1b5e20; font-weight: 900;}
            .final-result { font-size: 18px; font-weight: 900; color: #b71c1c; background: #ffebee; padding: 15px; border-radius: 5px; display: inline-block; margin-top: 10px; border: 1px solid #b71c1c;}
            mjx-container { color: #000000 !important; font-weight: bold !important; }
        </style>
        </head><body class="tex2jax_process">
        <h1 style='text-align:center; font-weight:900;'>🌊 KDS 전달파고 산정 시스템 보고서</h1><hr style="border:1px solid #000;">
        """
    
    def title(self, text, level=2):
        st.markdown(f"{'#' * level} **{text}**")
        self.html += f"<h{level}>{text}</h{level}>"

    def md(self, text):
        st.markdown(text, unsafe_allow_html=True)
        safe_text = text.replace('₩', '\\')
        html_out = ""
        in_list = False
        in_quote = False
        for line in safe_text.split('\n'):
            line_stripped = line.strip()
            if not line_stripped: continue
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line_stripped)
            
            if content.startswith('> '):
                if not in_quote:
                    html_out += "<div class='calc-step'>"
                    in_quote = True
                
                sub_content = content[2:].strip()
                if sub_content.startswith('- '):
                    if not in_list: html_out += "<ul>"; in_list = True
                    html_out += f"<li>{sub_content[2:]}</li>"
                else:
                    if in_list: html_out += "</ul>"; in_list = False
                    html_out += f"<p>{sub_content}</p>"
            else:
                if in_list: html_out += "</ul>"; in_list = False
                if in_quote: html_out += "</div>"; in_quote = False
                
                if content.startswith('- ') or content.startswith('* '):
                    if not in_list: html_out += "<ul>"; in_list = True
                    html_out += f"<li>{content[2:]}</li>"
                else:
                    html_out += f"<p>{content}</p>"
                    
        if in_list: html_out += "</ul>"
        if in_quote: html_out += "</div>"
        
        self.html += html_out

    def two_col_md(self, items):
        col1, col2 = st.columns(2)
        half = (len(items) + 1) // 2
        with col1:
            for item in items[:half]: st.markdown(f"- **{item}**")
        with col2:
            for item in items[half:]: st.markdown(f"- **{item}**")
        
        self.html += "<ul class='two-col-list'>"
        for item in items:
            safe_item = item.replace('₩', '\\')
            safe_item = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_item)
            self.html += f"<li>{safe_item}</li>"
        self.html += "</ul>"

    def info(self, text):
        st.info(text)
        self.html += f"<div class='info-box'>{text}</div>"

    def warn(self, text):
        st.warning(text)
        self.html += f"<div class='warn-box'>{text}</div>"

    def latex(self, eq):
        st.latex(eq)
        safe_eq = eq.replace('₩', '\\')
        self.html += f"<div class='eq'>$$ {safe_eq} $$</div>"

    def result(self, text):
        st.success(text)
        self.html += f"<div style='text-align:center;'><span class='final-result'>{text}</span></div><br>"

    def df(self, dataframe):
        html_table = dataframe.to_html(index=False, justify='center', escape=False)
        st.markdown(f"<div style='display:flex; justify-content:center; width:100%;'>{html_table}</div>", unsafe_allow_html=True)
        self.html += f"<div style='text-align:center;'>{html_table}</div>"

    def static_img(self, img_path, caption=""):
        if os.path.exists(img_path):
            st.image(img_path, caption=caption)
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            # ★ 워드 그림 찢어짐 방지 처리 완료
            self.html += f"<div class='figure'><img src='data:image/png;base64,{encoded}' style='max-width:100%; height:auto;'><p><b>{caption}</b></p></div>"

    def get_html(self):
        return self.html + "</body></html>"

# =====================================================================
# ★ 다운로드 렌더링 엔진 (초고속 병렬 + Word 호환)
# =====================================================================
def render_fast_download(rep_obj, filename_base):
    st.divider()
    st.header("🖨️ 통합 구조계산서 다운로드")
    st.info("💡 **초고속 병렬 다운로드 엔진 적용:** MS Word 다운로드 시 수식과 삽도가 고해상도로 내장되며, 1~2초 이내에 즉시 생성됩니다.")
    
    with st.spinner("Word 보고서용 수식과 그림을 고속 병렬 변환 중입니다..."):
        import urllib.parse
        
        report_html = rep_obj.get_html()
        word_html = report_html
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 20px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f2f2f2; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

        # 이미지 래핑하여 세로로 찢어지는 현상 완벽 방어
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

        # 잔여 첨자(기호) 강제 치환
        word_html = word_html.replace("$H_{1/3}$", "H<sub>1/3</sub>").replace("$T_z$", "T<sub>z</sub>").replace("$h_{1/3, peak}$", "h<sub>1/3, peak</sub>")
        word_html = word_html.replace("$H_0'$", "H<sub>0</sub>'").replace("$H_s$", "H<sub>s</sub>").replace("$T_{1/3}$", "T<sub>1/3</sub>")
        word_html = word_html.replace("$\\Delta$", "Δ").replace("$\\alpha$", "α").replace("$\\alpha_s$", "α<sub>s</sub>").replace("$\\alpha_{row}$", "α<sub>row</sub>")
        word_html = word_html.replace("$K_T$", "K<sub>T</sub>").replace("$H_T$", "H<sub>T</sub>").replace("$L_{1/3}$", "L<sub>1/3</sub>")
        word_html = word_html.replace("$R_c$", "R<sub>c</sub>").replace("$A_T$", "A<sub>T</sub>").replace("$h_s$", "h<sub>s</sub>")
        word_html = word_html.replace("$D_n$", "D<sub>n</sub>")
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
        st.download_button("📄 전달파고 산정 보고서 다운로드 (HTML 웹용)", data=report_html.encode('utf-8'), file_name=f"{filename_base}.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button("📝 전달파고 산정 보고서 다운로드 (MS Word용)", data=mhtml.encode('utf-8'), file_name=f"{filename_base}.doc", mime="application/msword", use_container_width=True)

# =====================================================================
# 1. 물리 계산 코어 엔진 
# =====================================================================
class HydroPhysics:
    @staticmethod
    def solve_wavelength(T, h):
        if h <= 0: return 0.0
        g = 9.81
        L0 = (g * T**2) / (2 * math.pi)
        L = L0
        for _ in range(15):
            kh = 2 * math.pi * h / L
            tanh_kh = math.tanh(kh)
            f_L = L - L0 * tanh_kh
            df_L = 1 + L0 * (2 * math.pi * h / (L**2)) * (1 - tanh_kh**2)
            L_new = L - f_L / df_L
            if abs(L_new - L) < 0.0001: return L_new
            L = L_new
        return L

class TransmissionCalc:
    @staticmethod
    def calc_vertical(R, H13, T13, h, d):
        L13 = HydroPhysics.solve_wavelength(T13, h)
        s = H13 / L13 if L13 > 0 else 0
        R_H = R / H13 if H13 > 0 else 0
        d_h = d / h if h > 0 else 0
        
        warnings = []
        if s == 0:
            Kt = 0
            term1_val = 0
            term2_val = 0
        else:
            R_H_safe = max(R_H, 0.0) 
            exp_inner = -1.67 * (R_H_safe ** 0.36) * (s ** -0.24)
            term1_val = 3.17 * math.exp(exp_inner)
            term2_val = 0.014 * ((1 - d_h) ** 2)
            Kt = math.sqrt((term1_val ** 2) + term2_val)
            
        if not (0.3 <= R_H <= 2.6): warnings.append(f"R/H1/3 적용범위(0.3~2.6) 이탈: {R_H:.2f}")
        if not (0.02 <= s <= 0.05): warnings.append(f"파형경사(s) 적용범위(0.02~0.05) 이탈: {s:.4f}")
        if not (0.5 <= d_h <= 1.0): warnings.append(f"d/h 적용범위(0.5~1.0) 이탈: {d_h:.2f}")

        return {
            "L13": L13, "s": s, "R_H": R_H, "R_H_safe": max(R_H, 0.0), "d_h": d_h,
            "term1": term1_val, "term2": term2_val,
            "Kt": Kt, "Ht": Kt * H13,
            "warnings": warnings
        }

    @staticmethod
    def calc_sloping(R, H13, T13, h, W, Dn):
        L13 = HydroPhysics.solve_wavelength(T13, h)
        s = H13 / L13 if L13 > 0 else 0
        R_H = R / H13 if H13 > 0 else 0
        H_h = H13 / h if h > 0 else 0
        W_Dn = W / Dn if Dn > 0 else 0
        
        alpha_s = 5 * s + 0.233
        alpha_row = 0.0143 * W_Dn - 0.0331
        
        Kt_calc = alpha_s - 0.31 * R_H - alpha_row
        Kt = max(Kt_calc, 0.06)
        
        warnings = []
        if not (0.015 <= s <= 0.044): warnings.append(f"파형경사(s) 적용범위(0.015~0.044) 이탈: {s:.4f}")
        if not (0.6 <= R_H <= 2.0): warnings.append(f"R/H1/3 적용범위(0.6~2.0) 이탈: {R_H:.2f}")
        if not (0.1 <= H_h <= 0.38): warnings.append(f"H1/3/h 적용범위(0.1~0.38) 이탈: {H_h:.2f}")
        if not (2.32 <= W_Dn <= 5.12): warnings.append(f"W/Dn 적용범위(2.32~5.12) 이탈: {W_Dn:.2f}")

        return {
            "L13": L13, "s": s, "R_H": R_H, "H_h": H_h, "W_Dn": W_Dn,
            "alpha_s": alpha_s, "alpha_row": alpha_row, "Kt_calc": Kt_calc,
            "Kt": Kt, "Ht": Kt * H13,
            "warnings": warnings
        }

    @staticmethod
    def calc_submerged(Rc, H13, T13, h, W, AT, sub_type):
        L13 = HydroPhysics.solve_wavelength(T13, h)
        Rc_h = Rc / h if h > 0 else 0
        Rc_H = Rc / H13 if H13 > 0 else 0
        H_L = H13 / L13 if L13 > 0 else 0
        W_L = W / L13 if L13 > 0 else 0
        hs = h - Rc
        AT_hs = AT / hs if hs > 0 else 0
        
        warnings = []
        if sub_type == "투과형 단면":
            if not (0.1 <= Rc_h <= 0.2): warnings.append(f"Rc/h 적용범위(0.1~0.2) 이탈: {Rc_h:.2f}")
            if not (0.2 <= Rc_H <= 1.0): warnings.append(f"Rc/H1/3 적용범위(0.2~1.0) 이탈: {Rc_H:.2f}")
            if not (0.01 <= H_L <= 0.06): warnings.append(f"H1/3/L1/3 적용범위(0.01~0.06) 이탈: {H_L:.4f}")
            if not (0.04 <= W_L <= 1.5): warnings.append(f"W/L1/3 적용범위(0.04~1.5) 이탈: {W_L:.2f}")
            if AT_hs <= 0.5: warnings.append(f"AT/hs 적용범위(>0.5) 이탈: {AT_hs:.2f}")
            c1, c2, c3, c4, c5 = 0.380, 0.095, 0.072, -0.188, 0.013
        elif sub_type == "경사형 단면":
            if not (0.1 <= Rc_h <= 0.33): warnings.append(f"Rc/h 적용범위(0.1~0.33) 이탈: {Rc_h:.2f}")
            if not (0.2 <= Rc_H <= 1.0): warnings.append(f"Rc/H1/3 적용범위(0.2~1.0) 이탈: {Rc_H:.2f}")
            if not (0.01 <= H_L <= 0.065): warnings.append(f"H1/3/L1/3 적용범위(0.01~0.065) 이탈: {H_L:.4f}")
            if not (0.05 <= W_L <= 1.5): warnings.append(f"W/L1/3 적용범위(0.05~1.5) 이탈: {W_L:.2f}")
            if AT_hs > 0.5: warnings.append(f"AT/hs 적용범위(<=0.5) 이탈: {AT_hs:.2f}")
            c1, c2, c3, c4, c5 = 0.278, 0.146, 0.075, -0.205, -0.015
        else: # 불투과형 단면
            if not (0.1 <= Rc_h <= 0.25): warnings.append(f"Rc/h 적용범위(0.1~0.25) 이탈: {Rc_h:.2f}")
            if not (0.2 <= Rc_H <= 1.0): warnings.append(f"Rc/H1/3 적용범위(0.2~1.0) 이탈: {Rc_H:.2f}")
            if not (0.01 <= H_L <= 0.065): warnings.append(f"H1/3/L1/3 적용범위(0.01~0.065) 이탈: {H_L:.4f}")
            if not (0.05 <= W_L <= 1.5): warnings.append(f"W/L1/3 적용범위(0.05~1.5) 이탈: {W_L:.2f}")
            c1, c2, c3, c4, c5 = 0.483, 0.093, 0.019, -0.157, -0.376
        
        term1 = c1 * math.exp(Rc_h)
        term2 = c2 * math.exp(Rc_H)
        term3 = c3 * math.log(H_L) if H_L > 0 else 0
        term4 = c4 * math.log(W_L) if W_L > 0 else 0
        
        Kt_calc = term1 + term2 + term3 + term4 + c5
        Kt = max(Kt_calc, 0.01)
        
        return {
            "L13": L13, "Rc_h": Rc_h, "Rc_H": Rc_H, "H_L": H_L, "W_L": W_L, "AT_hs": AT_hs,
            "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
            "term1": term1, "term2": term2, "term3": term3, "term4": term4,
            "Kt_calc": Kt_calc, "Kt": Kt, "Ht": Kt * H13,
            "warnings": warnings
        }

# =====================================================================
# 3. Streamlit UI 메인
# =====================================================================
st.markdown("""
<style>
    [data-testid="stMarkdownContainer"] { color: #000000 !important; font-weight: 800 !important; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"] blockquote { background-color: #f9f9f9 !important; padding: 15px 20px !important; border-left: 6px solid #1a73e8 !important; margin-bottom: 15px !important; box-shadow: 0px 2px 4px rgba(0,0,0,0.15); border-radius: 4px; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"] blockquote p, [data-testid="stMarkdownContainer"] blockquote li, [data-testid="stMarkdownContainer"] blockquote span { color: #000000 !important; font-size: 16.5px !important; font-weight: 900 !important; margin-bottom: 8px !important; line-height: 1.7 !important; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"] blockquote ul { margin-top: 5px !important; margin-bottom: 10px !important; opacity: 1 !important; }
    .katex, .katex * { color: #000000 !important; font-weight: 900 !important; opacity: 1 !important; }
    table { width: 100%; border: 2px solid #000 !important; border-collapse: collapse; margin-bottom: 20px; opacity: 1 !important; }
    th { background-color: #e0e0e0 !important; color: #000 !important; font-weight: 900 !important; font-size: 16px !important; border: 1px solid #000 !important; padding: 10px; text-align: center; }
    td { color: #000 !important; font-weight: 900 !important; font-size: 15px !important; border: 1px solid #000 !important; padding: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🌊 KDS 구조물 파고 전달율 산정 시스템")
st.divider()

c_type = st.sidebar.selectbox("① 구조물 형식 선택", ["직립혼성제 (무공)", "테트라포드 피복 경사제", "수중구조물 (잠제, 인공리프)"])

if c_type == "직립혼성제 (무공)":
    st.sidebar.subheader("② 기초 제원 입력")
    h13 = st.sidebar.number_input("유의파고 H1/3 (m)", value=3.00, key='v_h13')
    t13 = st.sidebar.number_input("유의주기 T1/3 (sec)", value=10.00, key='v_t13')
    h_val = st.sidebar.number_input("제체 전면 수심 h (m)", value=15.00, key='v_h')

    st.sidebar.subheader("③ 조위 및 마루높이 설정")
    water_level = st.sidebar.number_input("설계조위 (DL.m)", value=0.00, step=0.10, key='v_wl')
    crest_elev = st.sidebar.number_input("마루높이 (DL.m)", value=3.00, step=0.10, key='v_ce')
    r_val = crest_elev - water_level
    st.sidebar.info(f"계산된 여유고 R = {r_val:.2f} m")

    st.sidebar.subheader("④ 직립제 상세 제원")
    d_val = st.sidebar.number_input("근고부 상단 수심 d (m)", value=10.00, key='v_d')

elif c_type == "테트라포드 피복 경사제":
    st.sidebar.subheader("② 기초 제원 입력")
    h13 = st.sidebar.number_input("유의파고 H1/3 (m)", value=4.00, key='s_h13')
    t13 = st.sidebar.number_input("유의주기 T1/3 (sec)", value=11.00, key='s_t13')
    h_val = st.sidebar.number_input("제체 전면 수심 h (m)", value=15.00, key='s_h')

    st.sidebar.subheader("③ 조위 및 마루높이 설정")
    water_level = st.sidebar.number_input("설계조위 (DL.m)", value=0.00, step=0.10, key='s_wl')
    crest_elev = st.sidebar.number_input("마루높이 (DL.m)", value=4.00, step=0.10, key='s_ce')
    r_val = crest_elev - water_level
    st.sidebar.info(f"계산된 여유고 R = {r_val:.2f} m")

    st.sidebar.subheader("④ 경사제 상세 제원")
    w_val = st.sidebar.number_input("상치콘크리트 전면 피복재 어깨폭 W (m)", value=5.00, key='s_w')
    v_val = st.sidebar.number_input("테트라포드 체적 V (m³)", value=5.00, key='s_v')
    dn_val = round(v_val ** (1/3), 3)
    st.sidebar.info(f"계산된 공칭길이 Dn = V^(1/3) = {dn_val} m")

elif c_type == "수중구조물 (잠제, 인공리프)":
    st.sidebar.subheader("② 수중 단면 형식")
    sub_type = st.sidebar.selectbox("단면 형식", ["투과형 단면", "경사형 단면", "불투과형 단면"], key='u_sub')
    
    st.sidebar.subheader("③ 기초 제원 입력")
    h13 = st.sidebar.number_input("유의파고 H1/3 (m)", value=3.00, key='u_h13')
    t13 = st.sidebar.number_input("유의주기 T1/3 (sec)", value=8.00, key='u_t13')
    h_val = st.sidebar.number_input("제체 전면 수심 h (m)", value=10.00, key='u_h')

    st.sidebar.subheader("④ 조위 및 마루수심 설정")
    water_level = st.sidebar.number_input("설계조위 (DL.m)", value=0.00, step=0.10, key='u_wl')
    crest_elev = st.sidebar.number_input("마루높이 (DL.m)", value=-1.50, step=0.10, key='u_ce')
    r_val = water_level - crest_elev
    st.sidebar.info(f"계산된 마루수심 Rc = {r_val:.2f} m")

    st.sidebar.subheader("⑤ 수중구조물 상세 제원")
    w_val = st.sidebar.number_input("마루폭 W (m)", value=20.00, key='u_w')
    at_val = 0.0
    if sub_type in ["투과형 단면", "경사형 단면"]:
        default_at = 5.0 if sub_type == "투과형 단면" else 4.0
        at_val = st.sidebar.number_input("피복층 두께 A_T (m)", value=default_at, key='u_at')

if 'kt_calculated' not in st.session_state:
    st.session_state['kt_calculated'] = False

calc_btn = st.sidebar.button("🚀 전달파고 산정 및 보고서 생성", use_container_width=True, type="primary")

if calc_btn:
    st.session_state['kt_calculated'] = True

if st.session_state['kt_calculated']:
    rep = ReportBuilder()
    rep.title(f"📑 {c_type} 파고 전달율($K_T$) 및 전달파고($H_T$) 산정", level=2)

    if c_type == "직립혼성제 (무공)":
        res = TransmissionCalc.calc_vertical(r_val, h13, t13, h_val, d_val)
        
        rep.title("■ 1. 기본 파라미터 산정", level=3)
        items = [
            f"유의파고 ($H_{{1/3}}$) = **{h13:.2f} m**",
            f"유의주기 ($T_{{1/3}}$) = **{t13:.2f} sec** $\\rightarrow$ 유의파장 ($L_{{1/3}}$) = **{res['L13']:.2f} m**",
            f"여유고 ($R$) = **{r_val:.2f} m**",
            f"파형경사 ($s = H_{{1/3}} / L_{{1/3}}$) = {h13:.2f} / {res['L13']:.2f} = **{res['s']:.4f}**",
            f"상대 여유고 ($R / H_{{1/3}}$) = {r_val:.2f} / {h13:.2f} = **{res['R_H']:.2f}**",
            f"상대 근고수심 ($d / h$) = {d_val:.2f} / {h_val:.2f} = **{res['d_h']:.2f}**"
        ]
        rep.two_col_md(items)
        
        if res['warnings']:
            for w in res['warnings']: rep.warn(w)

        rep.title("■ 2. 공식 및 기호 설명", level=3)
        rep.static_img("무공직립혼성제 전달율 실험단면.png", "참고 그림 4.4-45 무공 직립혼성제의 파고 전달율 산정을 위한 실험단면")
        rep.latex(r"K_T = \sqrt{\left\{ 3.17 \exp \left[ -1.67 \left(\frac{R}{H_{1/3}}\right)^{0.36} s^{-0.24} \right] \right\}^2 + 0.014\left(1 - \frac{d}{h}\right)^2}")
        
        symbols = [
            "$K_T$: 파고 전달율", "$R$: 여유고 (m)", "$H_{1/3}$: 유의파고 (m)", 
            "$L_{1/3}$: 유의파 파장 (m)", "$s$: 파형경사 ($=H_{1/3}/L_{1/3}$)", 
            "$d$: 근고부 상단 수심 (m)", "$h$: 제체 전면 수심 (m)",
            "**[적용 범위]**", 
            "$R/H_{1/3} = 0.3 \sim 2.6$", 
            "$s = 0.02 \sim 0.05$", 
            "$d/h = 0.5 \sim 1.0$"
        ]
        rep.two_col_md(symbols)
        rep.md("<p style='font-size:15px; color:#333; font-weight:800;'>※ 우변의 첫 번째 항은 월파 전달율, 두 번째 항은 제체 투과파 전달율을 의미합니다.</p>")

        rep.title("■ 3. 상세 계산 과정", level=3)
        check1 = "<span style='color:blue;'>만족</span>" if (0.3 <= res['R_H_safe'] <= 2.6) else "<span style='color:red;'>범위 이탈</span>"
        check2 = "<span style='color:blue;'>만족</span>" if (0.02 <= res['s'] <= 0.05) else "<span style='color:red;'>범위 이탈</span>"
        check3 = "<span style='color:blue;'>만족</span>" if (0.5 <= res['d_h'] <= 1.0) else "<span style='color:red;'>범위 이탈</span>"
        
        rep.md(f"> **(1) 적용 범위 검토**")
        rep.md(f"> - $R / H_{{1/3}} = {r_val:.2f} / {h13:.2f} = {res['R_H_safe']:.2f}$ ({check1})")
        rep.md(f"> - $s = {h13:.2f} / {res['L13']:.2f} = {res['s']:.4f}$ ({check2})")
        rep.md(f"> - $d / h = {d_val:.2f} / {h_val:.2f} = {res['d_h']:.2f}$ ({check3})")
        
        rep.md(f"> **(2) 월파 전달항 (제1항) 산정**")
        rep.md(f"> - $3.17 \\exp [ -1.67 (R / H_{{1/3}})^{{0.36}} s^{{-0.24}} ] = 3.17 \\exp [ -1.67 ({r_val:.2f} / {h13:.2f})^{{0.36}} ({res['s']:.4f})^{{-0.24}} ] = \\mathbf{{{res['term1']:.4f}}}$")
        
        rep.md(f"> **(3) 투과파 전달항 (제2항) 산정**")
        rep.md(f"> - $0.014 ( 1 - d / h )^2 = 0.014 ( 1 - {d_val:.2f} / {h_val:.2f} )^2 = \\mathbf{{{res['term2']:.4f}}}$")
        
        rep.md(f"> **(4) 최종 파고 전달율 ($K_T$) 산정**")
        rep.md(f"> - $K_T = \\sqrt{{(\\text{{제1항}})^2 + (\\text{{제2항}})}} = \\sqrt{{({res['term1']:.4f})^2 + {res['term2']:.4f}}} = \\mathbf{{{res['Kt']:.3f}}}$")

    elif c_type == "테트라포드 피복 경사제":
        res = TransmissionCalc.calc_sloping(r_val, h13, t13, h_val, w_val, dn_val)
        
        rep.title("■ 1. 기본 파라미터 산정", level=3)
        items = [
            f"유의파장 ($L_{{1/3}}$) = **{res['L13']:.2f} m**", 
            f"여유고 ($R$) = **{r_val:.2f} m**",
            f"파형경사 ($s = H_{{1/3}} / L_{{1/3}}$) = {h13:.2f} / {res['L13']:.2f} = **{res['s']:.4f}**", 
            f"상대 여유고 ($R / H_{{1/3}}$) = {r_val:.2f} / {h13:.2f} = **{res['R_H']:.2f}**",
            f"상대 수심 ($H_{{1/3}} / h$) = {h13:.2f} / {h_val:.2f} = **{res['H_h']:.2f}**", 
            f"상대 피복재 어깨폭 ($W / D_n$) = {w_val:.2f} / {dn_val:.3f} = **{res['W_Dn']:.2f}**"
        ]
        rep.two_col_md(items)
        
        if res['warnings']:
            for w in res['warnings']: rep.warn(w)

        rep.title("■ 2. 공식 및 기호 설명", level=3)
        rep.static_img("경사제 전달율 실험단면.png", "참고 그림 4.4-44 경사제의 파고 전달율 산정을 위한 실험단면")
        rep.latex(r"K_T = \alpha_s - 0.31(R/H_{1/3}) - \alpha_{row} \quad (\text{단, } (K_T)_{min} = 0.06)")
        rep.latex(r"\alpha_s = 5s + 0.233 \quad / \quad \alpha_{row} = 0.0143(W/D_n) - 0.0331")
        
        symbols = [
            "$K_T$: 파고 전달율", "$\\alpha_s$: 파형경사 영향항", "$\\alpha_{row}$: 피복재 어깨폭 영향항", 
            "$R$: 여유고 (m)", "$s$: 파형경사 ($=H_{1/3}/L_{1/3}$)", "$W$: 피복재 어깨폭 (m)", 
            "$D_n$: 피복재 공칭길이 ($V^{1/3}$, m)", "$V$: 피복재 체적 ($m^3$)",
            "**[적용 범위]**",
            "$s = 0.015 \sim 0.044$",
            "$R/H_{1/3} = 0.6 \sim 2.0$",
            "$H_{1/3}/h = 0.1 \sim 0.38$",
            "$W/D_n = 2.32 \sim 5.12$"
        ]
        rep.two_col_md(symbols)

        rep.title("■ 3. 상세 계산 과정", level=3)
        check1 = "<span style='color:blue;'>만족</span>" if (0.015 <= res['s'] <= 0.044) else "<span style='color:red;'>범위 이탈</span>"
        check2 = "<span style='color:blue;'>만족</span>" if (0.6 <= res['R_H'] <= 2.0) else "<span style='color:red;'>범위 이탈</span>"
        check3 = "<span style='color:blue;'>만족</span>" if (0.1 <= res['H_h'] <= 0.38) else "<span style='color:red;'>범위 이탈</span>"
        check4 = "<span style='color:blue;'>만족</span>" if (2.32 <= res['W_Dn'] <= 5.12) else "<span style='color:red;'>범위 이탈</span>"
        
        rep.md(f"> **(1) 적용 범위 검토**")
        rep.md(f"> - $s = {h13:.2f} / {res['L13']:.2f} = {res['s']:.4f}$ ({check1})")
        rep.md(f"> - $R / H_{{1/3}} = {r_val:.2f} / {h13:.2f} = {res['R_H']:.2f}$ ({check2})")
        rep.md(f"> - $H_{{1/3}} / h = {h13:.2f} / {h_val:.2f} = {res['H_h']:.2f}$ ({check3})")
        rep.md(f"> - $W / D_n = {w_val:.2f} / {dn_val:.3f} = {res['W_Dn']:.2f}$ ({check4})")
        
        rep.md(f"> **(2) 파형경사 영향항 ($\\alpha_s$) 산정**")
        rep.md(f"> - $\\alpha_s = 5 (H_{{1/3}} / L_{{1/3}}) + 0.233 = 5 \\times ({h13:.2f} / {res['L13']:.2f}) + 0.233 = \\mathbf{{{res['alpha_s']:.4f}}}$")
        
        rep.md(f"> **(3) 피복재 어깨폭 영향항 ($\\alpha_{{row}}$) 산정**")
        rep.md(f"> - $\\alpha_{{row}} = 0.0143 (W / D_n) - 0.0331 = 0.0143 \\times ({w_val:.2f} / {dn_val:.3f}) - 0.0331 = \\mathbf{{{res['alpha_row']:.4f}}}$")
        
        rep.md(f"> **(4) 최종 파고 전달율 ($K_T$) 산정**")
        rep.md(f"> - $K_T = \\alpha_s - 0.31 (R / H_{{1/3}}) - \\alpha_{{row}} = {res['alpha_s']:.4f} - 0.31 ({r_val:.2f} / {h13:.2f}) - {res['alpha_row']:.4f} = \\mathbf{{{res['Kt_calc']:.3f}}}$")
        rep.md(f"> - **최종 산정 (최소값 0.06 적용)**: $K_T = \\max({res['Kt_calc']:.3f}, 0.06) = \\mathbf{{{res['Kt']:.3f}}}$")

    elif c_type == "수중구조물 (잠제, 인공리프)":
        res = TransmissionCalc.calc_submerged(r_val, h13, t13, h_val, w_val, at_val, sub_type)
        
        rep.title("■ 1. 기본 파라미터 산정", level=3)
        items = [
            f"유의파장 ($L_{{1/3}}$) = **{res['L13']:.2f} m**", 
            f"마루수심 ($R_c$) = **{r_val:.2f} m**",
            f"상대 마루수심 ($R_c / h$) = {r_val:.2f} / {h_val:.2f} = **{res['Rc_h']:.4f}**", 
            f"상대 파고 ($R_c / H_{{1/3}}$) = {r_val:.2f} / {h13:.2f} = **{res['Rc_H']:.4f}**",
            f"파형경사 ($H_{{1/3}} / L_{{1/3}}$) = {h13:.2f} / {res['L13']:.2f} = **{res['H_L']:.4f}**", 
            f"상대 마루폭 ($W / L_{{1/3}}$) = {w_val:.2f} / {res['L13']:.2f} = **{res['W_L']:.4f}**"
        ]
        if sub_type in ["투과형 단면", "경사형 단면"]:
            items.append(f"피복층 두께비 ($A_T / h_s$) = {at_val:.2f} / {(h_val - r_val):.2f} = **{res['AT_hs']:.4f}**")
        rep.two_col_md(items)
        
        if res['warnings']:
            for w in res['warnings']: rep.warn(w)

        rep.title("■ 2. 공식 및 기호 설명", level=3)
        rep.static_img("수중구조물 전달율 실험단면.png", "참고 그림 4.4-46 수중구조물의 파고 전달율 산정을 위한 구조형식")
        
        c5_str = f"+ {res['c5']:.3f}" if res['c5'] > 0 else f"- {abs(res['c5']):.3f}"
        rep.latex(fr"K_T = {res['c1']:.3f}\exp\left(\frac{{R_c}}{{h}}\right) + {res['c2']:.3f}\exp\left(\frac{{R_c}}{{H_{{1/3}}}}\right) + {res['c3']:.3f}\ln\left(\frac{{H_{{1/3}}}}{{L_{{1/3}}}}\right) {res['c4']:.3f}\ln\left(\frac{{W}}{{L_{{1/3}}}}\right) {c5_str}")
        
        symbols = [
            "$K_T$: 파고 전달율", "$R_c$: 마루수심 (m)", "$H_{1/3}$: 유의파고 (m)", 
            "$L_{1/3}$: 유의파 파장 (m)", "$h$: 제체 전면 수심 (m)", "$W$: 구조물 마루폭 (m)", 
            "$A_T$: 피복층 두께 (m)", "$h_s$: 구조물 전체 높이 ($h-R_c$)",
            "**[적용 범위]**"
        ]
        
        if sub_type == "투과형 단면":
            symbols.extend(["$0.1 \le R_c/h \le 0.2$", "$0.2 \le R_c/H_{1/3} \le 1.0$", "$0.01 \le H_{1/3}/L_{1/3} \le 0.06$", "$0.04 \le W/L_{1/3} \le 1.5$", "$A_T/h_s > 0.5$"])
        elif sub_type == "경사형 단면":
            symbols.extend(["$0.1 \le R_c/h \le 0.33$", "$0.2 \le R_c/H_{1/3} \le 1.0$", "$0.01 \le H_{1/3}/L_{1/3} \le 0.065$", "$0.05 \le W/L_{1/3} \le 1.5$", "$A_T/h_s \le 0.5$"])
        else:
            symbols.extend(["$0.1 \le R_c/h \le 0.25$", "$0.2 \le R_c/H_{1/3} \le 1.0$", "$0.01 \le H_{1/3}/L_{1/3} \le 0.065$", "$0.05 \le W/L_{1/3} \le 1.5$"])
            
        rep.two_col_md(symbols)

        rep.title("■ 3. 상세 계산 과정", level=3)
        
        check1 = "<span style='color:blue;'>만족</span>" if res['warnings'] == [] or not any("Rc/h" in w for w in res['warnings']) else "<span style='color:red;'>범위 이탈</span>"
        check2 = "<span style='color:blue;'>만족</span>" if res['warnings'] == [] or not any("Rc/H1/3" in w for w in res['warnings']) else "<span style='color:red;'>범위 이탈</span>"
        check3 = "<span style='color:blue;'>만족</span>" if res['warnings'] == [] or not any("H1/3/L1/3" in w for w in res['warnings']) else "<span style='color:red;'>범위 이탈</span>"
        check4 = "<span style='color:blue;'>만족</span>" if res['warnings'] == [] or not any("W/L1/3" in w for w in res['warnings']) else "<span style='color:red;'>범위 이탈</span>"
        
        rep.md(f"> **(1) 적용 범위 검토**")
        rep.md(f"> - $R_c / h = {r_val:.2f} / {h_val:.2f} = {res['Rc_h']:.4f}$ ({check1})")
        rep.md(f"> - $R_c / H_{{1/3}} = {r_val:.2f} / {h13:.2f} = {res['Rc_H']:.4f}$ ({check2})")
        rep.md(f"> - $H_{{1/3}} / L_{{1/3}} = {h13:.2f} / {res['L13']:.2f} = {res['H_L']:.4f}$ ({check3})")
        rep.md(f"> - $W / L_{{1/3}} = {w_val:.2f} / {res['L13']:.2f} = {res['W_L']:.4f}$ ({check4})")
        if sub_type in ["투과형 단면", "경사형 단면"]:
            check5 = "<span style='color:blue;'>만족</span>" if res['warnings'] == [] or not any("AT/hs" in w for w in res['warnings']) else "<span style='color:red;'>범위 이탈</span>"
            rep.md(f"> - $A_T / h_s = {at_val:.2f} / {(h_val - r_val):.2f} = {res['AT_hs']:.4f}$ ({check5})")

        rep.md(f"> **(2) 수식 제1항 산정**")
        rep.md(f"> - $c_1 \\exp(R_c / h) = {res['c1']:.3f} \\exp({r_val:.2f} / {h_val:.2f}) = \\mathbf{{{res['term1']:.4f}}}$")
        
        rep.md(f"> **(3) 수식 제2항 산정**")
        rep.md(f"> - $c_2 \\exp(R_c / H_{{1/3}}) = {res['c2']:.3f} \\exp({r_val:.2f} / {h13:.2f}) = \\mathbf{{{res['term2']:.4f}}}$")
        
        rep.md(f"> **(4) 수식 제3항 산정**")
        rep.md(f"> - $c_3 \\ln(H_{{1/3}} / L_{{1/3}}) = {res['c3']:.3f} \\ln({h13:.2f} / {res['L13']:.2f}) = \\mathbf{{{res['term3']:.4f}}}$")
        
        rep.md(f"> **(5) 수식 제4항 산정**")
        rep.md(f"> - $c_4 \\ln(W / L_{{1/3}}) = {res['c4']:.3f} \\ln({w_val:.2f} / {res['L13']:.2f}) = \\mathbf{{{res['term4']:.4f}}}$")
        
        rep.md(f"> **(6) 최종 파고 전달율 ($K_T$) 산정**")
        rep.md(f"> - $K_T = (\\text{{제1항}}) + (\\text{{제2항}}) + (\\text{{제3항}}) + (\\text{{제4항}}) + (\\text{{상수항}}) = {res['term1']:.4f} + {res['term2']:.4f} + {res['term3']:.4f} + {res['term4']:.4f} {c5_str} = \\mathbf{{{res['Kt_calc']:.3f}}}$")
        rep.md(f"> - **최종 산정 (최소값 0.01 적용)**: $K_T = \\max({res['Kt_calc']:.3f}, 0.01) = \\mathbf{{{res['Kt']:.3f}}}$")

    rep.title("■ 4. 최종 전달파고($H_T$) 결과", level=3)
    rep.latex(r"H_T = K_T \times H_{1/3}")
    rep.result(f"최종 전달파고 $H_T = {res['Kt']:.3f} \\times {h13:.2f} = {res['Ht']:.2f}\\text{{ m}}$")
    
    df_summary = pd.DataFrame([{
        "구조물 형식": c_type + (f" ({sub_type})" if c_type == "수중구조물 (잠제, 인공리프)" else ""),
        "입사 유의파고(H1/3)": f"{h13:.2f} m",
        "파고 전달율(Kt)": f"{res['Kt']:.3f}",
        "최종 전달파고(Ht)": f"{res['Ht']:.2f} m"
    }])
    rep.df(df_summary)

    render_fast_download(rep, f"전달파고_산정보고서_{'수중구조물' if '수중' in c_type else '방파제'}")
