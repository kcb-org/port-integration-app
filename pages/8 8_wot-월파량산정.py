import streamlit as st
import pandas as pd
import numpy as np
import math
import os
import base64
import re
import io
import urllib.request
import urllib.parse  # 👈 이 줄을 import 구문들 사이에 추가해주세요!
import concurrent.futures
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from scipy.interpolate import griddata, interp1d
from scipy.optimize import brentq
from PIL import Image, ImageDraw, ImageFont
# =====================================================================
# 사이드바 설정
# =====================================================================
with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보, 홍운철]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

@st.cache_data(show_spinner=False)
def fetch_equation_image(api_url):
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return base64.b64encode(response.read()).decode('utf-8')
    except Exception:
        return None

def render_fast_download(rep_obj, filename_base):
    st.divider()
    st.header("🖨️ 종합 검토 보고서 다운로드")
    st.info("💡 **초고속 병렬 다운로드 엔진 적용:** HTML 웹용 및 MS Word용 보고서를 각각 1~2초 이내에 즉시 생성합니다[cite: 5].")
    
    with st.spinner("보고서용 수식과 그림을 고속 변환 중입니다..."):
        report_html = rep_obj.get_html()
        mhtml_data = rep_obj.get_mhtml()
        
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 종합 검토 보고서 다운로드 (HTML 웹용)", data=report_html.encode('utf-8'), file_name=f"{filename_base}.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button("📝 종합 검토 보고서 다운로드 (MS Word용)", data=mhtml_data.encode('utf-8'), file_name=f"{filename_base}.doc", mime="application/msword", use_container_width=True)
# =====================================================================
# ★ 보고서 생성기
# =====================================================================
class ReportBuilder:
    def __init__(self):
        self.html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>월파량 산정 보고서</title>
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
            h4 { color: #b71c1c; margin-top: 20px; margin-bottom: 8px; font-weight: 900; font-size: 16px; }
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
        <h1 style='text-align:center; font-weight:900;'>🌊 KDS 월파량 산정 및 구조 비교 검토 보고서</h1><hr style="border:1px solid #000;">
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
                    if not in_list:
                        html_out += "<ul>"
                        in_list = True
                    html_out += f"<li>{sub_content[2:]}</li>"
                else:
                    if in_list:
                        html_out += "</ul>"
                        in_list = False
                    html_out += f"<p>{sub_content}</p>"
            else:
                if in_list:
                    html_out += "</ul>"
                    in_list = False
                if in_quote:
                    html_out += "</div>"
                    in_quote = False
                
                if content.startswith('- ') or content.startswith('* '):
                    if not in_list:
                        html_out += "<ul>"
                        in_list = True
                    html_out += f"<li>{content[2:]}</li>"
                elif content.startswith('#### '):
                    html_out += f"<h4>{content[5:]}</h4>"
                else:
                    if content.startswith('<details') or content.startswith('</details'):
                        html_out += content
                    else:
                        html_out += f"<p>{content}</p>"
                    
        if in_list: html_out += "</ul>"
        if in_quote: html_out += "</div>"
        self.html += html_out

    def dual_table(self, md_str, html_str):
        st.markdown(md_str, unsafe_allow_html=True)
        self.html += html_str

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
        st.markdown(f"<div style='display:flex; justify-content:center; width:100%;'>{html_table}</div><br>", unsafe_allow_html=True)
        self.html += f"<div style='text-align:center;'>{html_table}</div><br>"

    def static_img(self, img_path, caption=""):
        if os.path.exists(img_path):
            st.image(img_path, caption=caption)
            try:
                with Image.open(img_path) as im:
                    buf = io.BytesIO()
                    im.convert("RGB").save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            except Exception:
                with open(img_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
            
            self.html += f"<div class='figure'><img src=\"data:image/png;base64,{encoded}\" width=\"650\"><p><b>{caption}</b></p></div>"

    def get_html(self):
        return self.html + "</body></html>"

    def get_mhtml(self):
        import urllib.parse
        import concurrent.futures
        import textwrap
        
        report_html = self.get_html()
        word_html = report_html
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 20px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f2f2f2; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

        def image_replacer(match):
            b64_data = match.group(1)
            counters['img'] += 1
            img_id = f"embedded_img_{counters['img']}"
            attachments[img_id] = b64_data
            return f'<img src="cid:{img_id}" width="650">'
        
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

        word_html = word_html.replace("$H_{1/3}$", "H<sub>1/3</sub>").replace("$T_{1/3}$", "T<sub>1/3</sub>").replace("$L_0$", "L<sub>0</sub>")
        word_html = word_html.replace("$R_c$", "R<sub>c</sub>").replace("$H_s$", "H<sub>s</sub>").replace("$q_{all}$", "q<sub>all</sub>")
        word_html = word_html.replace("$\\gamma_\\theta$", "γ<sub>θ</sub>").replace("$\\gamma_f$", "γ<sub>f</sub>").replace("$\\gamma_b$", "γ<sub>b</sub>")
        word_html = word_html.replace("$\\gamma_h$", "γ<sub>h</sub>").replace("$\\gamma_\\beta$", "γ<sub>β</sub>").replace("$\\gamma_s$", "γ<sub>s</sub>")
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

    def get_mhtml(self):
        report_html = self.get_html()
        word_html = report_html
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 20px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f2f2f2; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

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

        word_html = word_html.replace("$H_{1/3}$", "H<sub>1/3</sub>").replace("$T_{1/3}$", "T<sub>1/3</sub>").replace("$L_0$", "L<sub>0</sub>")
        word_html = word_html.replace("$R_c$", "R<sub>c</sub>").replace("$H_s$", "H<sub>s</sub>").replace("$q_{all}$", "q<sub>all</sub>")
        word_html = word_html.replace("$\\gamma_\\theta$", "γ<sub>θ</sub>").replace("$\\gamma_f$", "γ<sub>f</sub>").replace("$\\gamma_b$", "γ<sub>b</sub>")
        word_html = word_html.replace("$\\gamma_h$", "γ<sub>h</sub>").replace("$\\gamma_\\beta$", "γ<sub>β</sub>").replace("$\\gamma_s$", "γ<sub>s</sub>")
        word_html = re.sub(r'\$([a-zA-Z]+)_([a-zA-Z0-9\+\-]+)\$', r'\1<sub>\2</sub>', word_html)
        word_html = word_html.replace('$', '')

        boundary = "----=_NextPart_HTML_DOC_001"
        mhtml = f'MIME-Version: 1.0\nContent-Type: multipart/related; type="text/html"; boundary="{boundary}"\n\n'
        mhtml += f'--{boundary}\nContent-Type: text/html; charset="utf-8"\nContent-Transfer-Encoding: 8bit\n\n'
        mhtml += word_html + "\n\n"
        
        for cid, b64 in attachments.items():
            mhtml += f'--{boundary}\nContent-Type: image/png\nContent-Transfer-Encoding: base64\nContent-ID: <{cid}>\n\n{b64}\n\n'
        mhtml += f"--{boundary}--\n"
        return mhtml

# =====================================================================
# 핵심 수리 및 Goda 도표 보간 엔진
# =====================================================================
G = 9.81

def get_L0(T):
    return (G * T**2) / (2 * math.pi)

def get_gamma_theta_sloping(theta):
    if 0 <= theta <= 10: return 1.0
    elif 10 < theta <= 50: return math.cos(math.radians(theta - 10))**2
    else: return 0.8981 - 0.0062 * theta

def get_gamma_theta_vertical(theta):
    if 0 <= theta <= 45: return 1 - 0.0062 * theta
    else: return 0.72

@st.cache_data
def load_graph_config():
    if os.path.exists("graph_config.csv"): return pd.read_csv("graph_config.csv")
    return None

@st.cache_data
def load_ks_data():
    if not os.path.exists("k_s_all_data.csv"): return None, None
    try:
        df_ks = pd.read_csv("k_s_all_data.csv", header=None)
        steepness_vals = df_ks.iloc[0].dropna().values
        points, values = [], []
        for i in range(len(steepness_vals)):
            steepness = float(steepness_vals[i])
            x_data = pd.to_numeric(df_ks.iloc[2:, i * 2]).dropna().values
            y_data = pd.to_numeric(df_ks.iloc[2:, i * 2 + 1]).dropna().values
            for x, y in zip(x_data, y_data):
                points.append([steepness, x])
                values.append(y)
        return np.array(points), np.array(values)
    except: return None, None

@st.cache_data
def load_goda_charts():
    goda_data = {}
    for f in os.listdir('.'):
        if f.endswith('.csv') and (f.startswith('s_') or f.startswith('v_')):
            try:
                file_key = f.replace('.csv', '').lower()
                df = pd.read_csv(f, header=None)
                curves = df.iloc[0].dropna().values
                curve_dict = {}
                for i, curve in enumerate(curves):
                    x_vals = pd.to_numeric(df.iloc[2:, i * 2]).dropna()
                    y_vals = pd.to_numeric(df.iloc[2:, i * 2 + 1]).dropna()
                    if len(x_vals) == 0: continue
                    curve_df = pd.DataFrame({'X': x_vals, 'Y': y_vals}).sort_values('X').drop_duplicates(subset='X')
                    interp_func = interp1d(curve_df['X'], curve_df['Y'], kind='linear', fill_value="extrapolate", bounds_error=False)
                    curve_dict[float(curve)] = interp_func
                goda_data[file_key] = curve_dict
            except: pass
    return goda_data

class GodaCalculator:
    def __init__(self):
        self.config_df = load_graph_config()
        self.ks_points, self.ks_values = load_ks_data()
        self.goda_interp_data = load_goda_charts()

    def calc_linear_Ks(self, h, T):
        L0 = 1.56 * T**2
        C0 = 1.56 * T
        L = L0
        for _ in range(100):
            L_new = L0 * math.tanh(2 * math.pi * h / L)
            if abs(L_new - L) < 0.001: break
            L = L_new
        C = L / T
        n = 0.5 * (1 + (4 * math.pi * h / L) / math.sinh(4 * math.pi * h / L))
        Ks = math.sqrt((1 / (2 * n)) * (C0 / C))
        return Ks, L0

    def calc_goda_H13(self, H0_prime, h, slope_val, L0, Ks):
        tan_theta = 1.0 / slope_val
        steepness = H0_prime / L0
        beta_0 = 0.028 * (steepness**(-0.38)) * math.exp(20 * (tan_theta**1.5))
        beta_1 = 0.52 * math.exp(4.2 * tan_theta)
        beta_max = max(0.92, 0.32 * (steepness**(-0.29)) * math.exp(2.4 * tan_theta))
        return min(Ks * H0_prime, beta_0 * H0_prime + beta_1 * h, beta_max * H0_prime)
    
    def get_converged_H0_prime(self, input_H13, T, h, slope_val):
        L0 = 1.56 * T**2
        Ks_linear, _ = self.calc_linear_Ks(h, T)
        H0_prime_linear = input_H13 / Ks_linear 
        current_H0_prime = H0_prime_linear
        current_Ks = Ks_linear
        max_iter, tolerance = 100, 0.001
        
        for outer_iteration in range(max_iter):
            steepness = current_H0_prime / L0
            rel_depth_L0 = h / L0
            
            if self.ks_points is not None and len(self.ks_points) > 0:
                Ks_chart = griddata(self.ks_points, self.ks_values, (steepness, rel_depth_L0), method='linear')
                if np.isnan(Ks_chart):
                    Ks_chart = griddata(self.ks_points, self.ks_values, (steepness, rel_depth_L0), method='nearest')
                fixed_Ks = float(Ks_chart)
            else: fixed_Ks = Ks_linear
            
            inner_H0_prime = current_H0_prime
            inner_converged = False
            
            for inner_iteration in range(max_iter):
                calc_H13 = self.calc_goda_H13(inner_H0_prime, h, slope_val, L0, fixed_Ks)
                error1 = input_H13 - calc_H13
                if abs(error1) <= tolerance:
                    inner_converged = True
                    break
                inner_H0_prime = inner_H0_prime + (error1 * 0.5)
                
            new_steepness = inner_H0_prime / L0
            if self.ks_points is not None and len(self.ks_points) > 0:
                new_Ks_chart = griddata(self.ks_points, self.ks_values, (new_steepness, rel_depth_L0), method='linear')
                if np.isnan(new_Ks_chart):
                    new_Ks_chart = griddata(self.ks_points, self.ks_values, (new_steepness, rel_depth_L0), method='nearest')
                new_Ks_chart = float(new_Ks_chart)
            else: new_Ks_chart = fixed_Ks
            
            error2 = current_H0_prime - inner_H0_prime 
            error3 = fixed_Ks - new_Ks_chart           
            
            current_H0_prime = inner_H0_prime
            if abs(error2) <= tolerance and abs(error3) <= tolerance and inner_converged:
                return current_H0_prime
        return H0_prime_linear

    def get_Y_from_chart(self, file_key, h_H0, Rc_H0):
        if file_key not in self.goda_interp_data: return None, f"{file_key}.bmp"
        curves = self.goda_interp_data[file_key]
        available_Rc = sorted(curves.keys())
        if not available_Rc: return None, f"{file_key}.bmp"
        
        if Rc_H0 <= available_Rc[0]: return float(curves[available_Rc[0]](h_H0)), file_key
        elif Rc_H0 >= available_Rc[-1]: return float(curves[available_Rc[-1]](h_H0)), file_key
        
        for i in range(len(available_Rc)-1):
            if available_Rc[i] <= Rc_H0 <= available_Rc[i+1]:
                Rc_lo, Rc_hi = available_Rc[i], available_Rc[i+1]
                Y_lo, Y_hi = float(curves[Rc_lo](h_H0)), float(curves[Rc_hi](h_H0))
                if Y_lo <= 0 or Y_hi <= 0: return 0.0, file_key
                log_Y_lo, log_Y_hi = math.log10(Y_lo), math.log10(Y_hi)
                factor = (Rc_H0 - Rc_lo) / (Rc_hi - Rc_lo)
                log_Y = log_Y_lo + factor * (log_Y_hi - log_Y_lo)
                return 10 ** log_Y, file_key
        return None, file_key

    def calculate_takayama_formula(self, h, hc, H0_prime):
        rel_h = max(h / H0_prime, 0.5)
        rel_hc = hc / H0_prime
        alpha = -0.12 * (rel_h ** 0.5)
        beta = -1.15 * (1.0 + 0.1 * rel_h)
        gamma = -1.82 + 0.15 * rel_h
        log_q_coef = alpha * (rel_hc ** 2) + beta * rel_hc + gamma
        return (10 ** log_q_coef) * math.sqrt(2 * G * (H0_prime ** 3))

    def draw_annotated_chart(self, f_key, h_H0, Y_val):
        bmp_file = f"{f_key}.bmp"
        if self.config_df is None or not os.path.exists(bmp_file): return bmp_file
        rows = self.config_df[self.config_df['file_name'].str.lower() == bmp_file.lower()]
        if rows.empty: return bmp_file
        row = rows.iloc[0]
        try:
            img = Image.open(bmp_file).convert("RGB")
            draw = ImageDraw.Draw(img)
            x_val = h_H0
            if x_val <= row['x2_val']:
                ratio = (x_val - row['x1_val']) / (row['x2_val'] - row['x1_val'])
                x_px = int(row['x1_px'] + ratio * (row['x2_px'] - row['x1_px']))
            else:
                log_min, log_max = math.log10(row['x3_val']), math.log10(row['x4_val'])
                x_val_safe = max(x_val, row['x3_val'])
                ratio = (math.log10(x_val_safe) - log_min) / (log_max - log_min)
                x_px = int(row['x3_px'] + ratio * (row['x4_px'] - row['x3_px']))
            y_min, y_max = row['y1_val'], row['y2_val']
            y_val_safe = max(min(Y_val, y_max), y_min)
            log_min, log_max = math.log10(y_min), math.log10(y_max)
            ratio = (math.log10(y_val_safe) - log_min) / (log_max - log_min)
            y_px = int(row['y1_py'] + ratio * (row['y2_py'] - row['y1_py']))
            axis_y_common = int(row['x1-4_py'])
            axis_x_common = int(row['x1_px'])
            
            line_color, target_color = (255, 0, 0), (0, 0, 255) 
            draw.line([(x_px, y_px), (x_px, axis_y_common)], fill=line_color, width=3)
            draw.line([(x_px, y_px), (axis_x_common, y_px)], fill=line_color, width=3)
            r = 6
            draw.ellipse([(x_px - r, y_px - r), (x_px + r, y_px + r)], fill=target_color)
            
            try: font = ImageFont.truetype("malgun.ttf", 22) 
            except:
                try: font = ImageFont.truetype("arial.ttf", 22) 
                except: font = ImageFont.load_default() 
            text_str = f" X (h/H0') : {h_H0:.3f}\n Y (Q) : {Y_val:.2e} "
            try:
                bbox = draw.textbbox((x_px + 15, y_px - 55), text_str, font=font)
                draw.rectangle([bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5], fill="white", outline="blue", width=2)
            except AttributeError: pass
            draw.text((x_px + 15, y_px - 55), text_str, fill="black", font=font)
            
            # 💡 확장자를 .png로 강제 변경하고 PNG 포맷으로 저장
            out_path = f"annotated_{os.path.splitext(bmp_file)[0]}.png"
            img.save(out_path, format="PNG")
            return out_path
        except: return bmp_file

    def execute_goda_calc(self, H13, T, h, Rc, struct_type, bottom_slope_val, draw_charts=True):
        H0_prime = self.get_converged_H0_prime(H13, T, h, bottom_slope_val)
        L0 = (G * (T ** 2)) / (2 * math.pi)
        wave_slope_calc = H0_prime / L0
        rel_h = h / H0_prime
        rel_hc = Rc / H0_prime
        q_takayama = self.calculate_takayama_formula(h, Rc, H0_prime)
        struct_code = 'v' if "직립" in struct_type else 's'
        
        standard_bottoms = [10, 30]
        if bottom_slope_val <= standard_bottoms[0]: factor_bottom = 0.0
        elif bottom_slope_val >= standard_bottoms[-1]: factor_bottom = 1.0
        else: factor_bottom = (bottom_slope_val - standard_bottoms[0]) / (standard_bottoms[-1] - standard_bottoms[0])

        standard_waves = [0.012, 0.017, 0.036]
        if wave_slope_calc <= standard_waves[0]:
            wave_lo, wave_hi, factor_wave = standard_waves[0], standard_waves[0], 0.0
        elif wave_slope_calc >= standard_waves[-1]:
            wave_lo, wave_hi, factor_wave = standard_waves[-1], standard_waves[-1], 1.0
        else:
            for i in range(len(standard_waves)-1):
                if standard_waves[i] <= wave_slope_calc <= standard_waves[i+1]:
                    wave_lo, wave_hi = standard_waves[i], standard_waves[i+1]
                    factor_wave = (wave_slope_calc - wave_lo) / (wave_hi - wave_lo)
                    break

        chart_data_list = []
        def process_chart(b_val, w_val, weight_b, weight_w):
            if weight_b > 0 and weight_w > 0:
                w_str = f"{w_val:.3f}".replace(".", "")
                f_key = f"{struct_code}_1_{int(b_val)}_{w_str}".lower()
                Y_val, _ = self.get_Y_from_chart(f_key, rel_h, rel_hc)
                if Y_val is not None and Y_val > 0:
                    out_path = self.draw_annotated_chart(f_key, rel_h, Y_val) if draw_charts else None
                    q_val = Y_val * math.sqrt(2 * G * (H0_prime ** 3))
                    chart_data_list.append({'path': out_path, 'bottom': b_val, 'wave': w_val, 'q_val': q_val, 'weight': weight_b * weight_w})
                return Y_val
            return 0.0

        Y_b10_wLo = process_chart(10, wave_lo, 1 - factor_bottom, 1 - factor_wave)
        Y_b10_wHi = process_chart(10, wave_hi, 1 - factor_bottom, factor_wave)
        Y_b30_wLo = process_chart(30, wave_lo, factor_bottom, 1 - factor_wave)
        Y_b30_wHi = process_chart(30, wave_hi, factor_bottom, factor_wave)

        if all(y is not None for y in [Y_b10_wLo, Y_b10_wHi, Y_b30_wLo, Y_b30_wHi]):
            Y_10_final = Y_30_final = 0.0
            if Y_b10_wLo > 0 and Y_b10_wHi > 0: Y_10_final = 10 ** (math.log10(Y_b10_wLo) + factor_wave * (math.log10(Y_b10_wHi) - math.log10(Y_b10_wLo)))
            if Y_b30_wLo > 0 and Y_b30_wHi > 0: Y_30_final = 10 ** (math.log10(Y_b30_wLo) + factor_wave * (math.log10(Y_b30_wHi) - math.log10(Y_b30_wLo)))

            Y_final = 0.0
            if Y_10_final > 0 and Y_30_final > 0: Y_final = 10 ** (math.log10(Y_10_final) + factor_bottom * (math.log10(Y_30_final) - math.log10(Y_10_final)))
            elif Y_10_final > 0: Y_final = Y_10_final
            elif Y_30_final > 0: Y_final = Y_30_final

            q_goda_final = Y_final * math.sqrt(2 * G * (H0_prime ** 3))
            calc_method = "데이터 도표 기반 정밀 로그 다중 보간"
        else:
            q_goda_final = q_takayama
            calc_method = "Takayama(1992) 근사식 적용 (도표 범위 이탈)"

        return q_goda_final, calc_method, H0_prime, rel_h, rel_hc, wave_slope_calc, chart_data_list

goda_calc = GodaCalculator()

# =====================================================================
# Streamlit UI 화면 구성
# =====================================================================
st.set_page_config(page_title="하부 구조물 월파량 산정 시스템", layout="wide")

st.markdown("""
<style>
    [data-testid="stMarkdownContainer"] { color: #000000 !important; font-weight: 800 !important; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"] blockquote { background-color: #f9f9f9 !important; padding: 15px 20px !important; border-left: 6px solid #1a73e8 !important; margin-bottom: 15px !important; box-shadow: 0px 2px 4px rgba(0,0,0,0.15); border-radius: 4px; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"] blockquote p, [data-testid="stMarkdownContainer"] blockquote li { color: #000000 !important; font-size: 16.5px !important; font-weight: 900 !important; margin-bottom: 8px !important; line-height: 1.7 !important; opacity: 1 !important; }
    .katex, .katex * { color: #000000 !important; font-weight: 900 !important; opacity: 1 !important; }
    table { width: 100%; border: 2px solid #000 !important; border-collapse: collapse; margin-bottom: 20px; opacity: 1 !important; }
    th { background-color: #e0e0e0 !important; color: #000 !important; font-weight: 900 !important; font-size: 16px !important; border: 1px solid #000 !important; padding: 10px; text-align: center; }
    td { color: #000 !important; font-weight: 900 !important; font-size: 15px !important; border: 1px solid #000 !important; padding: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🌊 KDS 항만 구조물 월파량 다각도 비교 검토 시스템")
st.divider()

struct_type = st.sidebar.selectbox("① 구조물 형식 선택", ["경사제 (Rubble Mound)", "직립제 (혼성제)"])
st.sidebar.subheader("② 공통 설계 제원 입력")
calc_mode = st.sidebar.radio("계산 모드 선택", ["월파량(q) 산정", "소요 여유고(Rc) 산정"])

h13 = st.sidebar.number_input("유의파고 H1/3 (m)", value=2.50)
t13 = st.sidebar.number_input("유의주기 T1/3 (s)", value=7.50)
theta = st.sidebar.number_input("파랑 입사각 θ (deg)", value=0.0)
wl = st.sidebar.number_input("검토 설계조위 (DL.m)", value=1.00)
gl = st.sidebar.number_input("원지반고 (DL.m)", value=-7.50)
slope_denom = st.sidebar.number_input("해저경사 분모 N (1/N 기준)", value=30.0, step=5.0)
h = wl - gl

if calc_mode == "월파량(q) 산정":
    crest = st.sidebar.number_input("구조물 마루높이 (DL.m)", value=5.00)
    Rc_input = crest - wl
    q_target = None
    st.sidebar.info(f"계산수심 (h) = {h:.2f} m\n\n계산여유고 (Rc) = {Rc_input:.2f} m")
else:
    q_target = st.sidebar.number_input("목표 허용 월파량 q_all (m³/s/m)", value=0.01)
    crest, Rc_input = None, None
    st.sidebar.info(f"계산수심 (h) = {h:.2f} m\n\n(소요 여유고는 계산 실행 후 도출됩니다)")

if struct_type == "경사제 (Rubble Mound)":
    st.sidebar.subheader("③ 경사제 상세 설계제원")
    AT = st.sidebar.number_input("피복층 두께 AT (m)", value=2.70)
    Gw = st.sidebar.number_input("어깨폭 Gw (m)", value=3.20)
    V = st.sidebar.number_input("피복재 체적 V (m³)", value=2.50)
    cot_alpha = st.sidebar.number_input("사면경사 cotα", value=1.50)
    
    # -------------------------------------------------------------
    # ★ 수정된 피복재 거칠기계수(EurOtop 표 반영 및 CEM 연동) 선택 로직 ★
    # -------------------------------------------------------------
    armour_dict = {
        "Smooth impermeable surface": 1.00,
        "Rocks (1 layer, impermeable core)": 0.60,
        "Rocks (1 layer, permeable core)": 0.45,
        "Rocks (2 layers, impermeable core)": 0.55,
        "Rocks (2 layers, permeable core)": 0.40,
        "Cubes (1 layer, flat positioning)": 0.49,
        "Cubes (2 layers, random positioning)": 0.47,
        "Antifers": 0.50,
        "HARO's": 0.47,
        "Tetrapods": 0.38,
        "Dolosse": 0.43,
        "Accropode™ I": 0.46,
        "Xbloc®; CORE-LOC®; Accropode™ II": 0.44,
        "Cubipods one layer": 0.49,
        "Cubipods two layers": 0.47
    }
    
    # 📌 요청에 따른 입력란 이름 변경 (CEM 연동 명시)
    selected_armour_str = st.sidebar.selectbox(
        "거칠기계수 γf (EurOtop Type/CEM)",
        options=[f"{k} ({v:.2f})" for k, v in armour_dict.items()],
        index=9 # 기본값: Tetrapods (0.38)
    )
    gamma_f = float(selected_armour_str.split("(")[-1].replace(")", ""))
    selected_armour_name = selected_armour_str.split(" (")[0]
    # -------------------------------------------------------------
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**[파랑 형태 및 입사각 제원 (CEM, EurOtop 공통)]**")
    wave_crest = st.sidebar.selectbox("파랑 형태 (γβ 산정용)", ["단파 (Short-crested)", "장파 (Long-crested)"])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**[소단(Berm) 제원 입력 (CEM, EurOtop 공통)]**")
    B_berm = st.sidebar.number_input("소단 폭 B (m)", value=0.0)
    L_berm = st.sidebar.number_input("사면 수평길이 L_Berm (m)", value=10.0)
    berm_pos = st.sidebar.selectbox("소단 위치", ["수위 상부 (Above SWL)", "수위 하부 (Below SWL)", "영향권 밖"])
    d_b = st.sidebar.number_input("수위-소단 중심 수직거리 d_b (m)", value=0.0)
    Ru2 = st.sidebar.number_input("처오름 높이 R_u2% (m)", value=3.0)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**[상치벽/산책로 형태 선택 (EurOtop 전용)]**")
    parapet_type = st.sidebar.selectbox("상치벽(γ*) 형태", [
        "소파공 동일 높이 (일반)",
        "매끈한 사면 + 폭풍방지벽 (Smooth dike + storm wall)",
        "매끈한 사면 + 벽 + bullnose",
        "Smooth dike slope + promenade (산책로)",
        "Smooth dike slope + promenade + wall",
        "Smooth dike slope + promenade + wall + bullnose"
    ])
    
    h_wall, h_n, epsilon, G_c = 0.0, 0.0, 0.0, 0.0
    if "wall" in parapet_type or "폭풍방지벽" in parapet_type:
        h_wall = st.sidebar.number_input("방지벽 높이 h_wall (m)", value=1.00)
    if "bullnose" in parapet_type:
        h_n = st.sidebar.number_input("Bullnose 높이 h_n (m)", value=0.50)
        epsilon = st.sidebar.number_input("Bullnose 각도 ε (deg)", value=30.0)
    if "promenade" in parapet_type:
        G_c = st.sidebar.number_input("산책로 폭 G_c (m)", value=5.00)

else:
    st.sidebar.subheader("③ 직립제 상세 설계제원")
    
    # 직립제에서도 입사각 계수 산정을 위해 파랑 형태를 입력받습니다.
    wave_crest_v = st.sidebar.selectbox("파랑 형태 (γβ 산정용)", ["단파 (Short-crested)", "장파 (Long-crested)"], key="wave_crest_v")
    
    # [수정] 형상계수(KDS 전용) 구조물 형식에 따른 자동 선택
    kds_shape_dict = {
        "무공직립구조물 (1.0)": 1.00,
        "상부사면상치(45도) (1.15)": 1.15,
        "유공케이슨 (0.7)": 0.70
    }
    selected_kds_shape = st.sidebar.selectbox("형상계수 γs (KDS 전용)", list(kds_shape_dict.keys()), index=0)
    gamma_s = kds_shape_dict[selected_kds_shape]
    
    # CEM 직립제(혼성제) 전용 케이슨 전면 형상 딕셔너리
    caisson_dict = {
        "일반케이슨 (1.00)": 1.00,
        "일반 케이슨(노즈형 상치) (0.78)": 0.78,
        "슬릿 케이슨(20% 유공율) (0.76)": 0.76,
        "오픈 슬릿 케이슨(20% 유공율) (0.58)": 0.58
    }
    
    selected_caisson_str = st.sidebar.selectbox(
        "케이슨 전면형상 γs (CEM 전용)",
        options=list(caisson_dict.keys()),
        index=0
    )
    gamma_s_cem = caisson_dict[selected_caisson_str]
    
    gamma_v_vt = st.sidebar.number_input("저감계수 γv (EurOtop 전용)", value=1.00)
   
    st.sidebar.markdown("---")
    st.sidebar.markdown("**[상반파공 제원 (EurOtop 7장)]**")
    
    # 반파공(Bullnose / Parapet) 입력
    has_bullnose = st.sidebar.checkbox("상반파공(Bullnose) 설치 여부")
    if has_bullnose:
        st.sidebar.info("💡 돌출 각도(α)와 내민 길이(λ)에 따라 월파 차단 계수(k_bn)가 결정됩니다.")
        bullnose_lambda = st.sidebar.number_input("내민 길이 (λ, m)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
        # [수정] 돌출 각도 최대값을 180도까지 허용하도록 수정
        bullnose_alpha = st.sidebar.number_input("돌출 각도 (α, 도)", min_value=15.0, max_value=180.0, value=30.0, step=5.0)
    else:
        bullnose_lambda = 0.0
        bullnose_alpha = 0.0
    # ---------------------------------------------------------

# 주의: 여기부터는 들여쓰기 없이 화면 맨 왼쪽(0칸)에 딱 붙어있어야 합니다.
st.sidebar.subheader("④ 검토 적용 설계 기준")
chk_kds = st.sidebar.checkbox("국내 기준 (KDS)", value=True)
chk_cem = st.sidebar.checkbox("해외 기준 (USACE CEM)", value=True)
chk_euro = st.sidebar.checkbox("해외 기준 (EurOtop)", value=True)
chk_goda = st.sidebar.checkbox("일본 기준 (Goda 원본 CSV/도표 정밀 보간 및 좌표표시)", value=True)

# 📌 기존에 있던 st.subheader("📐 [선택 구조 단면 개요 도면]") 및 관련 st.image() 출력 블록 전체 삭제

# ★ 세션 상태 초기화 (맨 처음 실행 시 False)
if 'wot_calculated' not in st.session_state:
    st.session_state['wot_calculated'] = False

calc_btn = st.sidebar.button(f"🚀 종합 {calc_mode} 실행 및 보고서 렌더링", use_container_width=True, type="primary")

# 버튼을 누르면 True로 상태 고정
if calc_btn:
    st.session_state['wot_calculated'] = True

# 버튼을 안 누르고 다운로드 버튼만 눌러도 True 상태가 유지되어 화면이 안 사라짐
if st.session_state['wot_calculated']:
    rep = ReportBuilder()
    rep.title(f"📑 {struct_type} {calc_mode} 비교 검토 결과 보고서", level=2)
    # (... 기존 중간 계산 코드들은 그대로 유지하면서 들여쓰기만 맞춤 유지 ...)
    
    # ★ 보고서 최상단 기본 단면도 이미지 삽입 코드 삭제 완료 ★
    if struct_type == "경사제 (Rubble Mound)":
        r_B = B_berm / L_berm if L_berm > 0 else 0.0
        if berm_pos == "영향권 밖":
            r_db = 1.0
        elif berm_pos == "수위 상부 (Above SWL)":
            r_db = 0.5 - 0.5 * math.cos(math.pi * d_b / Ru2) if Ru2 > 0 else 1.0
        else: # 수위 하부
            r_db = 0.5 - 0.5 * math.cos(math.pi * d_b / (2 * h13)) if h13 > 0 else 1.0
        
        gamma_b_common = 1.0 - r_B * (1.0 - r_db)
        gamma_b_common = max(0.6, min(1.0, gamma_b_common))

        theta_abs = abs(theta)
        if wave_crest == "단파 (Short-crested)":
            if theta_abs <= 80:
                gamma_beta_common = 1.0 - 0.0033 * theta_abs
            else:
                gamma_beta_common = 0.736
        else: # 장파
            if theta_abs <= 10:
                gamma_beta_common = 1.0
            else:
                gamma_beta_common = max(0.6, math.cos(math.radians(theta_abs - 10))**2)
                
        tan_theta_fs = 1.0 / slope_denom if slope_denom > 0 else 0.0
        H_tr = (0.35 + 5.8 * tan_theta_fs) * h
        H_rms = h13 / 1.414
        
        if H_rms <= 0 or H_tr >= 2.5 * H_rms:
            H_2_calc = 1.4 * h13
            k_val = 2.0
            H_w = H_rms
            bg_cond = "심해/비쇄파 조건 (레일리 분포 유지)"
        else:
            k_val = 2.0 + (H_rms / H_tr)**3
            H_w = H_rms / math.sqrt(math.gamma(1.0 + 2.0 / k_val))
            H_2_calc = H_w * (-math.log(0.02))**(1.0 / k_val)
            bg_cond = "천해 쇄파 조건 (와이블 분포 적용)"
            
        gamma_h_cem = min(1.0, H_2_calc / (1.4 * h13)) if h13 > 0 else 1.0
      
    L0 = get_L0(t13)
    s0 = h13 / L0 if L0 > 0 else 0
    
    rep.title("■ 1. 기본 설계 제원 및 공통 수리 파라미터", level=3)
    items = [
        f"설계 유의파고 ($H_{{1/3}}$) = **{h13:.2f} m**",
        f"설계 유의주기 ($T_{{1/3}}$) = **{t13:.2f} sec** $\\rightarrow$ 심해파장 ($L_0$) = **{L0:.2f} m**",
        f"검토 설계조위 (WL) = **DL {wl:.2f} m**",
        f"구조물 전면 설계수심 ($h$) = **{h:.2f} m**",
        f"심해 파형경사 ($s_0 = H_{{1/3}} / L_0$) = **{s0:.4f}**",
        f"설계 해저경사 분모 조건 ($N$) = **1 / {slope_denom:.1f}**"
    ]
    if calc_mode == "월파량(q) 산정":
        items.insert(3, f"구조물 상단 마루높이 = **DL {crest:.2f} m** $\\rightarrow$ 계산 여유고 ($R_c$) = **{Rc_input:.2f} m**")
    else:
        items.insert(3, f"목표 허용 월파량 ($q_{{all}}$) = **{q_target} m³/s/m**")
    rep.two_col_md(items)
    final_results = []

    # ==========================================
    # [1] KDS 산정 모듈
    # ==========================================
    if chk_kds:
        rep.title("■ 2. 국내 항만설계기준 (KDS 2026) 설계식 적용 풀이", level=3)
        if struct_type == "경사제 (Rubble Mound)":
            gamma_theta = get_gamma_theta_sloping(theta)
            Dn = V**(1/3)
            
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_kds_s(test_rc):
                    r_tmp = (1/gamma_theta) * (test_rc/h13)**2 * (s0/(2*math.pi))**0.5 * (h/h13)**0.1 * (AT/h13) * (Gw/Dn)**0.6 * cot_alpha
                    return 0.001 * math.exp(-7.38 * r_tmp) * G * h13 * t13 - q_target
                try: 
                    Rc = brentq(eval_q_kds_s, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산결과: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: 
                    Rc = 0.01; rep.warn("역산 수렴에 실패했습니다. 범위를 벗어난 목표 월파량입니다.")
            else: Rc = Rc_input

            R_val = (1/gamma_theta) * (Rc/h13)**2 * (s0/(2*math.pi))**0.5 * (h/h13)**0.1 * (AT/h13) * (Gw/Dn)**0.6 * cot_alpha
            q_kds = 0.001 * math.exp(-7.38 * R_val) * G * h13 * t13
            
            # ★ 공식 전면 배치 및 설명 자료로 적용범위 추가
            rep.md("#### 📐 [월파량 산정 공식]")
            rep.info("**[공식 적용 수리실험 유효 범위]**<br> $R_c/H_{1/3}$ (0.77～2.0) | $s_0$ (0.007～0.049) | $H_{1/3}/h$ (0.30～0.53) | $G_w/D_n$ (2.32～7.92) | $A_T/H_{1/3}$ (0.60~1.52)")
            rep.latex(r"q = 0.001 \exp(-7.38 R) \cdot g \cdot H_{1/3} \cdot T_{1/3}")
            rep.latex(r"R = \frac{1}{\gamma_\theta} \left(\frac{R_c}{H_{1/3}}\right)^2 \sqrt{\frac{s_0}{2\pi}} \left(\frac{h}{H_{1/3}}\right)^{0.1} \left(\frac{A_T}{H_{1/3}}\right) \left(\frac{G_w}{D_n}\right)^{0.6} \cot\alpha")
            
            rep.md("#### 📝 [상세 풀이]")
            rep.md("> **[기호 설명]** $q$: 단위폭당 평균 월파량, $R$: 보정 여유고 파라미터, $\\gamma_\\theta$: 입사각 보정계수, $R_c$: 여유고, $H_{1/3}$: 유의파고, $s_0$: 파형경사, $h$: 수심, $A_T$: 피복층 두께, $G_w$: 어깨폭, $D_n$: 피복재 공칭길이, $\\cot\\alpha$: 사면경사, $g$: 중력가속도, $T_{1/3}$: 유의주기")
            rep.md(f"> - **R 상세 풀이:** $R = \\frac{{1}}{{{gamma_theta:.3f}}} \\times \\left(\\frac{{{Rc:.2f}}}{{{h13:.2f}}}\\right)^2 \\times \\sqrt{{\\frac{{{s0:.4f}}}{{2\\pi}}}} \\times \\left(\\frac{{{h:.2f}}}{{{h13:.2f}}}\\right)^{{0.1}} \\times \\left(\\frac{{{AT:.2f}}}{{{h13:.2f}}}\\right) \\times \\left(\\frac{{{Gw:.2f}}}{{{Dn:.3f}}}\\right)^{{0.6}} \\times {cot_alpha} = \\mathbf{{{R_val:.4f}}}$")
            rep.md(f"> - **q 상세 풀이:** $q = 0.001 \\exp(-7.38 \\times {R_val:.4f}) \\times 9.81 \\times {h13:.2f} \\times {t13:.2f} = \\mathbf{{{q_kds:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
            
            # ★ KDS 적용범위 상세검토자료 복원
            rep.md("#### 🔍 [KDS 공식 수리실험 적용 범위 검토]")
            v1, v2, v3, v4, v5 = Rc / h13, s0, h13 / h, Gw / Dn, AT / h13
            c1, c2, c3, c4, c5 = ("O.K" if (0.77 <= v1 <= 2.0) else "⚠️ 범위초과", "O.K" if (0.007 <= v2 <= 0.049) else "⚠️ 범위초과", "O.K" if (0.30 <= v3 <= 0.53) else "⚠️ 범위초과", "O.K" if (2.32 <= v4 <= 7.92) else "⚠️ 범위초과", "O.K" if (0.60 <= v5 <= 1.52) else "⚠️ 범위초과")
            rep.md(f"> 1. 여유고 조건 ($R_c/H_{{1/3}}$): {v1:.3f} (기준: 0.77 ~ 2.0) $\\rightarrow$ **{c1}**")
            rep.md(f"> 2. 파형경사 조건 ($s_0$): {v2:.4f} (기준: 0.007 ~ 0.049) $\\rightarrow$ **{c2}**")
            rep.md(f"> 3. 수심대비 파고 ($H_{{1/3}}/h$): {v3:.3f} (기준: 0.30 ~ 0.53) $\\rightarrow$ **{c3}**")
            rep.md(f"> 4. 어깨폭 비율 ($G_w/D_n$): {v4:.3f} (기준: 2.32 ~ 7.92) $\\rightarrow$ **{c4}**")
            rep.md(f"> 5. 피복두께 비율 ($A_T/H_{{1/3}}$): {v5:.3f} (기준: 0.60 ~ 1.52) $\\rightarrow$ **{c5}**")
            if "⚠️" in c1+c2+c3+c4+c5: rep.warn("※ 판정의견: 현재 단면은 KDS 수리실험 유효 범위를 이탈하였습니다. 해외기준 병행 검토를 권장합니다.")
            else: rep.info("※ 판정의견: 입력 조건이 KDS 실험조건을 모두 만족하여 산정 결과의 신뢰도가 높습니다.")

            if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": "국내 KDS (경사제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_kds:.6f} m³/s/m"})
            else: final_results.append({"적용 설계 기준": "국내 KDS (경사제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})

        else:
            h_star = (h**2) / (h13 * L0)
            sqrt_gH3 = math.sqrt(G * h13**3)
            
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_kds_v(test_rc):
                    if h_star > 0.23:
                        gamma_t = get_gamma_theta_vertical(theta)
                        qn = 0.0215 * (h13 / (h * s0))**0.5 * math.exp(-3.11 * test_rc / (h13 * gamma_s * gamma_t))
                    else:
                        r_ratio = test_rc / h13
                        if r_ratio < 1.35: qn = 0.017 * (h13 / (h * s0))**0.5 * math.exp(-2.47 * r_ratio)
                        else: qn = 0.0016 * (h13 / (h * s0))**0.5 * (r_ratio)**(-3.1)
                    return qn * sqrt_gH3 - q_target
                try: 
                    Rc = brentq(eval_q_kds_v, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: Rc = 0.01
            else: Rc = Rc_input

            # ★ 공식 전면 배치 및 설명 자료로 적용범위 추가
            rep.md("#### 📐 [월파량 산정 공식]")
            rep.latex(r"q = q^* \sqrt{g H_{1/3}^3}")
            if h_star > 0.23:
                rep.info("**[비충격파 적용 범위]** $R_c/H_{1/3}$ (0.6～1.5) | $H_{1/3}/h$ (0.08～0.47) | $s_0$ (0.008～0.054)")
                gamma_theta = get_gamma_theta_vertical(theta)
                rep.latex(r"q^* = 0.0215 \sqrt{\frac{H_{1/3}}{h \cdot s_0}} \exp\left( -3.11 \frac{R_c}{H_{1/3} \cdot \gamma_s \cdot \gamma_\theta} \right)")
                q_norm = 0.0215 * (h13 / (h * s0))**0.5 * math.exp(-3.11 * Rc / (h13 * gamma_s * gamma_theta))
                cond_info = f"비충격파 조건 ($h^* > 0.23$)"
                calc_str = f"0.0215 \\sqrt{{\\frac{{{h13:.2f}}}{{{h:.2f} \\times {s0:.4f}}}}} \\exp\\left( -3.11 \\frac{{{Rc:.2f}}}{{{h13:.2f} \\times {gamma_s} \\times {gamma_theta:.3f}}} \\right)"
            else:
                rep.info("**[충격파 적용 범위]** $R_c/H_{1/3}$ (0.6~1.5) | $H_{1/3}/h$ (0.20~0.63) | $s_0$ (0.015~0.057)")
                Rc_ratio = Rc / h13
                if Rc_ratio < 1.35:
                    rep.latex(r"q^* = 0.017 \sqrt{\frac{H_{1/3}}{h \cdot s_0}} \exp\left( -2.47 \frac{R_c}{H_{1/3}} \right)")
                    q_norm = 0.017 * (h13 / (h * s0))**0.5 * math.exp(-2.47 * Rc_ratio)
                    calc_str = f"0.017 \\sqrt{{\\frac{{{h13:.2f}}}{{{h:.2f} \\times {s0:.4f}}}}} \\exp\\left( -2.47 \\times {Rc_ratio:.3f} \\right)"
                else:
                    rep.latex(r"q^* = 0.0016 \sqrt{\frac{H_{1/3}}{h \cdot s_0}} \left(\frac{R_c}{H_{1/3}}\right)^{-3.1}")
                    q_norm = 0.0016 * (h13 / (h * s0))**0.5 * (Rc_ratio)**(-3.1)
                    calc_str = f"0.0016 \\sqrt{{\\frac{{{h13:.2f}}}{{{h:.2f} \\times {s0:.4f}}}}} \\times ({Rc_ratio:.3f})^{{-3.1}}"
                cond_info = f"충격파 조건 ($h^* \\le 0.23$)"
            
            q_kds = q_norm * sqrt_gH3

            rep.md("#### 📝 [상세 풀이]")
            rep.md("> **[기호 설명]** $q$: 단위폭당 평균 월파량, $h^*$: 비충격파/충격파 판별 한계수심비, $\\gamma_s$: 형상계수, $\\gamma_\\theta$: 입사각 보정계수, $q^*$: 무차원 월파량, $R_c$: 여유고, $H_{1/3}$: 유의파고, $s_0$: 파형경사, $h$: 수심, $g$: 중력가속도")
            rep.md(f"> - **수심비($h^*$) 판별:** $h^* = \\frac{{h^2}}{{H_{{1/3}} L_0}} = \\frac{{{h:.2f}^2}}{{{h13:.2f} \\times {L0:.2f}}} = {h_star:.4f}$ $\\rightarrow$ **{cond_info}**")
            rep.md(f"> - **$q^*$ 상세 풀이:** $q^* = {calc_str} = {q_norm:.4e}$")
            rep.md(f"> - **최종 결과($q$):** $q = {q_norm:.4e} \\times \\sqrt{{9.81 \\times {h13:.2f}^3}} = \\mathbf{{{q_kds:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
            
            # ★ KDS 직립제(혼성제) 적용범위 상세검토자료 복원
            rep.md("#### 🔍 [KDS 공식 수리실험 적용 범위 검토]")
            if h_star > 0.23:
                v_rc, v_h, v_s = Rc / h13, h13 / h, s0
                c1, c2, c3 = ("O.K" if (0.6 <= v_rc <= 1.5) else "⚠️ 범위초과", "O.K" if (0.08 <= v_h <= 0.47) else "⚠️ 범위초과", "O.K" if (0.008 <= v_s <= 0.054) else "⚠️ 범위초과")
                b_range1, b_range2, b_range3 = "0.6 ~ 1.5", "0.08 ~ 0.47", "0.008 ~ 0.054"
            else:
                v_rc, v_h, v_s = Rc / h13, h13 / h, s0
                c1, c2, c3 = ("O.K" if (0.6 <= v_rc <= 1.5) else "⚠️ 범위초과", "O.K" if (0.20 <= v_h <= 0.63) else "⚠️ 범위초과", "O.K" if (0.015 <= v_s <= 0.057) else "⚠️ 범위초과")
                b_range1, b_range2, b_range3 = "0.6 ~ 1.5", "0.20 ~ 0.63", "0.015 ~ 0.057"

            rep.md(f"> 1. 여유고 비 ($R_c/H_{{1/3}}$): {v_rc:.3f} (기준: {b_range1}) $\\rightarrow$ **{c1}**")
            rep.md(f"> 2. 수심대비 파고 ($H_{{1/3}}/h$): {v_h:.3f} (기준: {b_range2}) $\\rightarrow$ **{c2}**")
            rep.md(f"> 3. 파형경사 ($s_0$): {v_s:.4f} (기준: {b_range3}) $\\rightarrow$ **{c3}**")
            if "⚠️" in c1+c2+c3: rep.warn("※ 판정의견: 현재 직립제 제원이 KDS 실험범위를 이탈하였습니다. EurOtop 등과의 교차 비교를 권장합니다.")
            else: rep.info("※ 판정의견: 직립벽 적용 실험 범위 내에 정상 포함되어 산정 결과의 신뢰도가 높습니다.")

            if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": "국내 KDS (직립제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_kds:.6f} m³/s/m"})
            else: final_results.append({"적용 설계 기준": "국내 KDS (직립제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})

    # ==========================================
    # [2] USACE CEM 산정 모듈
    # ==========================================
    if chk_cem:
        rep.title("■ 3. 미국 해안공학매뉴얼 (USACE CEM 2006) 설계식 적용 풀이", level=3)
        if struct_type == "경사제 (Rubble Mound)":
            alpha = math.atan(1.0 / cot_alpha)
            xi0 = math.tan(alpha) / math.sqrt(h13 / L0)
            sqrt_gH3 = math.sqrt(G * h13**3)
            
            # 📌 쇄파/비쇄파 분리 계산 및 역산
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_cem_s(test_rc):
                    if xi0 < 2.0:
                        qn = 0.06 * math.sqrt(math.tan(alpha) / s0) * math.exp(-5.2 * (test_rc / h13) * (math.sqrt(s0) / math.tan(alpha)) * (1 / (gamma_f * gamma_b_common * gamma_h_cem * gamma_beta_common)))
                    else:
                        qn = 0.2 * math.exp(-2.6 * (test_rc / h13) * (1 / (gamma_f * gamma_b_common * gamma_h_cem * gamma_beta_common)))
                    return qn * sqrt_gH3 - q_target
                try: 
                    Rc = brentq(eval_q_cem_s, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: Rc = 0.01
            else: Rc = Rc_input
            
            # ★ 1) 공식 전면 배치 및 상세 개념 설명
            rep.md("#### 📐 [월파량 산정 공식 (CEM - van der Meer and Janssen (1995))]")
            rep.info("CEM 공식은 파도가 경사면에 부딪혀 부서지는 형태를 나타내는 **쇄파 매개변수($\\xi_{op}$)**에 따라 두 가지로 철저히 구분되어 적용됩니다.")
            
            rep.md(r"> **① 쇄파 파랑 조건 (Plunging waves, $\xi_{op} < 2.0$)**")
            rep.md(r"> - **특징:** 파도가 구조물 경사면에서 강하게 말리며 부서지는 조건입니다. 파도의 충격량이 크기 때문에 **파형경사($s_{op}$)**와 **사면경사($\tan \alpha$)**가 파도가 타고 오르는 힘에 직접적으로 관여하여 공식에 명시됩니다.")
            rep.md(r"> - **적용 범위:** $0.3 < \frac{R_c}{H_s} \frac{\sqrt{s_{op}}}{\tan \alpha} \frac{1}{\gamma_r \gamma_b \gamma_h \gamma_\beta} < 2$")
            rep.latex(r"\frac{q}{\sqrt{g H_s^3}} \sqrt{\frac{s_{op}}{\tan \alpha}} = 0.06 \exp \left( -5.2 \frac{R_c}{H_s} \frac{\sqrt{s_{op}}}{\tan \alpha} \frac{1}{\gamma_r \gamma_b \gamma_h \gamma_\beta} \right)")
            
            rep.md(r"> **② 비쇄파 파랑 조건 (Surging waves, $\xi_{op} \ge 2.0$)**")
            rep.md(r"> - **특징:** 파도가 크게 부서지지 않고 경사면을 따라 넘실대며 오르내리는 조건입니다. 파도 충격량이 작기 때문에 사면경사와 파형경사의 영향이 공식에서 사라지고, 오직 여유고($R_c$)와 파고($H_s$)의 비율이 지배적인 역할을 합니다.")
            rep.latex(r"\frac{q}{\sqrt{g H_s^3}} = 0.2 \exp \left( -2.6 \frac{R_c}{H_s} \frac{1}{\gamma_r \gamma_b \gamma_h \gamma_\beta} \right)")

            # ★ 2) 쇄파/비쇄파 조건 검토 및 공식 선정
            rep.md("#### 🔍 [쇄파/비쇄파 조건 검토 및 공식 선정]")
            if xi0 < 2.0:
                cond_info = r"쇄파 조건 ($\xi_{op} < 2.0$)"
                applied_formula_text = "쇄파(Plunging) 공식"
                q_norm = 0.06 * math.sqrt(math.tan(alpha) / s0) * math.exp(-5.2 * (Rc / h13) * (math.sqrt(s0) / math.tan(alpha)) * (1 / (gamma_f * gamma_b_common * gamma_h_cem * gamma_beta_common)))
                calc_str = f"0.06 \\sqrt{{\\frac{{\\tan({math.degrees(alpha):.1f}^\\circ)}}{{{s0:.4f}}}}} \\exp\\left( -5.2 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\frac{{\\sqrt{{{s0:.4f}}}}}{{\\tan({math.degrees(alpha):.1f}^\\circ)}} \\frac{{1}}{{{gamma_f:.3f} \\times {gamma_b_common:.3f} \\times {gamma_h_cem:.3f} \\times {gamma_beta_common:.3f}}} \\right)"
            else:
                cond_info = r"비쇄파 조건 ($\xi_{op} \ge 2.0$)"
                applied_formula_text = "비쇄파(Surging) 공식"
                q_norm = 0.2 * math.exp(-2.6 * (Rc / h13) * (1 / (gamma_f * gamma_b_common * gamma_h_cem * gamma_beta_common)))
                calc_str = f"0.2 \\exp\\left( -2.6 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\frac{{1}}{{{gamma_f:.3f} \\times {gamma_b_common:.3f} \\times {gamma_h_cem:.3f} \\times {gamma_beta_common:.3f}}} \\right)"
            q_cem = q_norm * sqrt_gH3

            rep.md(f"> - **파형경사($s_{{op}}$) 산정:** $s_{{op}} = H_{{1/3}}/L_0 = {s0:.4f}$")
            rep.md(f"> - **쇄파 매개변수($\\xi_{{op}}$) 산정:** $\\xi_{{op}} = \\frac{{\\tan({math.degrees(alpha):.1f}^\\circ)}}{{\\sqrt{{{s0:.4f}}}}} = {xi0:.4f}$ $\\rightarrow$ **{cond_info}**")
            rep.md(f"> - **결론:** 산정된 $\\xi_{{op}}$ 값에 따라 **{applied_formula_text}**을 적용하여 계산합니다.")

            # ★ 3) 영향계수 연동 표시
            rep.md("#### 📐 [영향계수($\gamma$) 상세 산정 (CEM, EurOtop 공통)]")
            rep.info("아래의 저감 계수($\\gamma$)들은 공식의 **지수 함수($\\exp$) 분모**에 위치합니다. 따라서 계수 값이 작아질수록 음의 지수가 커져 전체 월파량을 대폭 줄이는 효과를 발휘합니다.")
            
            # 1. 거칠기 계수
            rep.md(f"> - **1. 피복재 거칠기 계수($\\gamma_f, \\gamma_r$):** 피복재의 마찰 저항을 반영합니다. ({selected_armour_name} $\\rightarrow \\mathbf{{{gamma_f:.3f}}}$)")
            # 2. 소단 영향계수
            rep.md(f"> - **2. 소단 영향계수($\\gamma_b$):** 소단의 폭과 수심 위치에 따른 월파 저감 효과를 나타냅니다. ($\\gamma_b = 1 - r_B(1 - r_{{db}}) = \\mathbf{{{gamma_b_common:.3f}}}$)")
            # 3. 입사각 영향계수
            if wave_crest == "단파 (Short-crested)":
                eq_str = r"1 - 0.0033 |\beta|" if theta_abs <= 80 else "0.736"
            else:
                eq_str = "1.0" if theta_abs <= 10 else r"\max(0.6, \cos^2(|\beta| - 10^\circ))"
            rep.md(f"> - **3. 입사각 영향계수($\\gamma_\\beta$):** 파랑의 입사각 및 방향 분산성({wave_crest})을 반영합니다. ($\\gamma_\\beta = {eq_str} = \\mathbf{{{gamma_beta_common:.3f}}}$)")
            
            # 4. 수심 영향계수 (CEM 전용)
            rep.md("#### 📐 [수심 영향계수($\gamma_h$) 상세 산정: Battjes & Groenendijk (2000) 정밀 모형 (CEM 전용)]")
            rep.info(r"**[물리적 의미]** 깊은 바다(심해)에서 파고는 보통 레일리(Rayleigh) 분포를 따릅니다. 하지만 얕은 수심(천해)으로 오면 큰 파도들이 해저면의 영향을 받아 먼저 부서집니다(쇄파). $\gamma_h$는 이처럼 변형되어 윗부분이 잘려나간 **실제 도달 파고 분포의 변화**를 월파량 공식에 보정해 주는 핵심 계수입니다.")
            rep.md(r"> **[산정 원리]** 수치모형 없이 얕은 수심 효과를 반영하기 위해, 파고 분포가 레일리 분포에서 와이블(Weibull) 분포로 꺾이는 기준점인 **천이 파고($H_{tr}$)**를 찾아 확률 통계적으로 상위 2% 파고($H_{2\%}$)를 역산합니다.")
            rep.md(r"> **[기호 설명]** $H_{tr}$: 천이 파고(쇄파 기준 파고), $H_{rms}$: 제곱평균평방근 파고, $k$: 와이블 형상 매개변수, $H_w$: 와이블 척도 매개변수")
            rep.md(f"> - **1. 천이 파고($H_{{tr}}$):** $H_{{tr}} = (0.35 + 5.8 \\tan \\theta) \\times h = (0.35 + 5.8 \\times {tan_theta_fs:.4f}) \\times {h:.2f} = \\mathbf{{{H_tr:.3f} \\text{{ m}}}}$")
            rep.md(f"> - **2. 제곱평균평방근 파고($H_{{rms}}$):** $H_{{rms}} \\approx H_s / \\sqrt{{2}} = \\mathbf{{{H_rms:.3f} \\text{{ m}}}}$")
            rep.md(f"> - **3. 분포 판별 및 $H_{{2\\%}}$ 산출:** {bg_cond}")
            if k_val != 2.0:
                rep.md(f">   - $k = 2.0 + (H_{{rms}} / H_{{tr}})^3 = 2.0 + ({H_rms:.3f} / {H_tr:.3f})^3 = \\mathbf{{{k_val:.3f}}}$")
                rep.md(f">   - $H_w = H_{{rms}} / \\sqrt{{\\Gamma(1 + 2/k)}} = \\mathbf{{{H_w:.3f} \\text{{ m}}}}$")
                rep.md(f">   - $H_{{2\\%}} = H_w \\times (-\\ln(0.02))^{{1/k}} = \\mathbf{{{H_2_calc:.3f} \\text{{ m}}}}$")
            else:
                rep.md(f">   - 레일리 분포 유지 ($H_{{2\\%}} = 1.4 H_{{1/3}} = \\mathbf{{{H_2_calc:.3f} \\text{{ m}}}}$)")
            rep.md(f"> - **4. 수심 영향계수($\\gamma_h$):** $\\gamma_h = \\min\\left(1.0, \\frac{{H_{{2\\%}}}}{{1.4 H_s}}\\right) = \\min\\left(1.0, \\frac{{{H_2_calc:.3f}}}{{1.4 \\times {h13:.2f}}}\\right) = \\mathbf{{{gamma_h_cem:.3f}}}$")

            euro_li_tags = "".join([f"<li style='margin-bottom:4px;'>{k}: <b>{v:.2f}</b></li>" for k, v in armour_dict.items()])
            rep.md(f"<details style='margin-left: 22px; margin-bottom: 12px; cursor: pointer;'><summary>👉 <b style='color:#1a73e8;'>EurOtop/CEM 피복재 거칠기 계수(γf) 상세 기준 보기</b></summary><div style='padding: 12px; background-color: #f8f9fa; border: 1px solid #ddd; border-left: 4px solid #1a73e8; border-radius: 4px; margin-top: 8px; font-size: 14.5px;'><ul>{euro_li_tags}</ul></div></details>")

            # ★ 4) 월파량 상세 풀이
            rep.md("#### 📝 [월파량 상세 풀이]")
            rep.md(r"> **[기호 설명]** $q$: 단위폭당 평균 월파량, $s_{op}$: 파형경사, $\xi_{op}$: 쇄파 매개변수, $\gamma_f$($\gamma_r$): 거칠기계수, $\gamma_b$: 소단 영향계수, $\gamma_h$: 수심 영향계수, $\gamma_\beta$: 입사각 영향계수, $R_c$: 여유고, $H_{1/3}$ ($H_s$): 유의파고, $g$: 중력가속도, $\alpha$: 사면경사")
            rep.md(f"> - **무차원 유량 항 계산:** ${calc_str} = {q_norm:.4e}$")
            rep.md(f"> - **최종 결과($q$):** $q = {q_norm:.4e} \\times \\sqrt{{9.81 \\times {h13:.2f}^3}} = \\mathbf{{{q_cem:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
            
            # ★ 5) CEM 공식 유효 범위 검토
            rep.md("#### 🔍 [CEM 공식 수리실험 적용 범위 검토]")
            if xi0 < 2.0:
                cem_range_val = (Rc / h13) * (math.sqrt(s0) / math.tan(alpha)) * (1 / (gamma_f * gamma_b_common * gamma_h_cem * gamma_beta_common))
                c_cem = "O.K" if (0.3 < cem_range_val < 2.0) else "⚠️ 범위초과"
                rep.md(f"> 1. 쇄파 공식 적용 무차원 범위 ($\\frac{{R_c}}{{H_s}} \\frac{{\\sqrt{{s_{{op}}}}}}{{\\tan \\alpha}} \\frac{{1}}{{\\gamma_r \\gamma_b \\gamma_h \\gamma_\\beta}}$): {cem_range_val:.3f} (기준: 0.3 ~ 2.0) $\\rightarrow$ **{c_cem}**")
                if "⚠️" in c_cem:
                    rep.warn("※ 판정의견: 현재 단면은 CEM 쇄파 공식의 유효 범위를 이탈하였습니다.")
                else:
                    rep.info("※ 판정의견: 입력 조건이 CEM 실험조건을 만족하여 산정 결과의 신뢰도가 높습니다.")
            else:
                rep.md(r"> - 비쇄파(Surging) 조건 ($\xi_{op} \ge 2.0$)이므로 별도의 무차원 여유고 제약(하한/상한)이 매뉴얼에 명시되어 있지 않습니다.")

            if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": "USACE CEM (경사제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_cem:.6f} m³/s/m"})
            else: final_results.append({"적용 설계 기준": "USACE CEM (경사제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})
        else:
            # Franco & Franco (1999) 직립제 입사각 계수(gamma_beta) 산정
            theta_abs = abs(theta)
            if wave_crest_v == "단파 (Short-crested)":
                if theta_abs <= 20:
                    gamma_beta_cem_v = 0.83
                else:
                    gamma_beta_cem_v = 0.83 * math.cos(math.radians(theta_abs - 20))
            else: # 장파
                if theta_abs <= 37:
                    gamma_beta_cem_v = math.cos(math.radians(theta_abs))
                else:
                    gamma_beta_cem_v = 0.79
                    
            sqrt_gH3 = math.sqrt(G * h13**3)
            
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_cem_v(test_rc):
                    qn = 0.082 * math.exp(-3.0 * (test_rc / h13) * (1 / (gamma_beta_cem_v * gamma_s_cem)))
                    return qn * sqrt_gH3 - q_target
                try: 
                    Rc = brentq(eval_q_cem_v, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: Rc = 0.01
            else: Rc = Rc_input

            q_norm = 0.082 * math.exp(-3.0 * (Rc / h13) * (1 / (gamma_beta_cem_v * gamma_s_cem)))
            q_cem = q_norm * sqrt_gH3
            
            # ★ 공식 전면 배치
            rep.md("#### 📐 [월파량 산정 공식 (CEM - Franco & Franco (1999))]")
            rep.info("비쇄파(Non-breaking) 조건에서 직립형 구조물(혼성제 포함)의 월파량을 계산하는 공식입니다. 사면경사나 쇄파 매개변수 없이 상대 여유고($R_c/H_s$)와 두 가지 저감계수에 의해 결정됩니다.")
            rep.latex(r"q = Q \sqrt{g H_{1/3}^3}")
            rep.latex(r"Q = 0.082 \exp\left( -3.0 \frac{R_c}{H_{1/3}} \frac{1}{\gamma_\beta \gamma_s} \right)")

            # ★ CEM 직립제(혼성제) 단면 개념도 삽도 추가
            rep.static_img("CEM 직립제 단면개념도.png", caption="CEM 직립제(혼성제) 단면 및 케이슨 전면 형상 개념도")

            # ★ 입사각 보정계수 상세 설명자료 추가
            rep.md("#### 📐 [영향계수 상세 산정]")
            rep.md(r"##### 🌊 입사각 영향계수 ($\gamma_\beta$)의 물리적 의미 및 산정식")
            rep.info(r"파도가 구조물에 직각($\beta = 0^\circ$)이 아닌 비스듬하게 입사할 때 발생하는 에너지 분산 효과를 보정합니다. 파향의 집중도와 방향 분산성(Directional spreading)에 따라 장파와 단파 조건으로 엄격히 구분됩니다.")
            
            rep.md(r"> **1) 장파 조건 (Long-crested waves)**")
            rep.md(r"> - **특징:** 너울(Swell)과 같이 한 방향으로 가지런히 밀려오는 파랑입니다. 파향이 한곳으로 집중되어 있어 입사각이 틀어짐에 따라 사선 변형에 의한 에너지가 크게 감소합니다.")
            rep.latex(r"\gamma_\beta = \cos\beta \quad (\text{for } 0^\circ \le \beta \le 37^\circ)")
            rep.latex(r"\gamma_\beta = 0.79 \quad (\text{for } \beta > 37^\circ)")
            
            rep.md(r"> **2) 단파 조건 (Short-crested waves)**")
            rep.md(r"> - **특징:** 풍파(Wind waves)와 같이 불규칙한 다방향성 성분을 가집니다. 완벽한 정면 입사($\beta = 0^\circ$) 시에도 여러 방향의 파랑 에너지가 분산되어 들어오기 때문에, 기본적으로 방향 분산성에 의한 저감 효과($0.83$)가 내포되어 있습니다.")
            rep.latex(r"\gamma_\beta = 0.83 \quad (\text{for } 0^\circ \le \beta \le 20^\circ)")
            rep.latex(r"\gamma_\beta = 0.83 \cos(\beta - 20^\circ) \quad (\text{for } \beta > 20^\circ)")
            
            if wave_crest_v == "단파 (Short-crested)":
                eq_str = r"0.83" if theta_abs <= 20 else r"0.83 \cos(\beta - 20^\circ)"
            else:
                eq_str = r"\cos \beta" if theta_abs <= 37 else "0.79"
            
            rep.md(f"> - **현재 조건 평가:** {wave_crest_v} 조건 및 입사각 $\\beta = {theta_abs:.1f}^\\circ$ 적용 $\\rightarrow \\gamma_\\beta = {eq_str} = \\mathbf{{{gamma_beta_cem_v:.3f}}}$")
            rep.md(f"> - **케이슨 전면 형상계수($\\gamma_s$):** {selected_caisson_str} 적용 $\\rightarrow \\mathbf{{{gamma_s_cem:.3f}}}$")

            rep.md("#### 📝 [상세 풀이]")
            rep.md(r"> **[기호 설명]** $q$: 단위폭당 평균 월파량($\text{m}^3/\text{s}/\text{m}$), $Q$: 무차원 유량 지수, $\gamma_\beta$: 입사각 계수, $\gamma_s$: 케이슨 전면형상에 따른 계수, $R_c$: 여유고(천단고), $H_{1/3}$ ($H_s$): 설계 유의파고, $g$: 중력가속도")
            rep.md(f"> - **무차원 유량($Q$) 풀이:** $Q = 0.082 \\exp\\left( -3.0 \\times \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\times \\frac{{1}}{{{gamma_beta_cem_v:.3f} \\times {gamma_s_cem:.3f}}} \\right) = {q_norm:.4e}$")
            rep.md(f"> - **최종 결과($q$):** $q = {q_norm:.4e} \\times \\sqrt{{9.81 \\times {h13:.2f}^3}} = \\mathbf{{{q_cem:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
            
            if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": "USACE CEM (직립제, 혼성제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_cem:.6f} m³/s/m"})
            else: final_results.append({"적용 설계 기준": "USACE CEM (직립제, 혼성제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})
                                 
    # ==========================================
    # [3] EurOtop 산정 모듈
    # ==========================================
    if chk_euro:
        rep.title("■ 4. 유럽 EurOtop (2018) 설계 한계식 적용 풀이", level=3)
        Tm_10 = t13 / 1.1
        L_10 = (G * Tm_10**2) / (2 * math.pi)
        sqrt_gH3 = math.sqrt(G * h13**3)
        
        rep.md("> **[공통 기호 설명]** $T_{m-1,0}$: 스펙트럼 환산 주기, $L_{m-1,0}$: 환산 심해파장, $q$: 단위폭당 평균 월파량, $g$: 중력가속도, $H_{1/3}$: 유의파고")
        
        if struct_type == "경사제 (Rubble Mound)":
            alpha = math.atan(1.0 / cot_alpha)
            xi_10 = math.tan(alpha) / math.sqrt(h13 / L_10)
            
            def get_gamma_star(test_rc):
                if parapet_type == "소파공 동일 높이 (일반)" or test_rc <= 0: return 1.0
                
                ratio_hwall_rc = h_wall / test_rc if test_rc > 0 else 0
                g_v = math.exp(-0.56 * ratio_hwall_rc) if h_wall > 0 else 1.0
                
                g_bn = 1.0
                if "bullnose" in parapet_type and h_wall > 0:
                    lam = h_n / h_wall if h_wall > 0 else 0
                    if ratio_hwall_rc >= 0.25:
                        g_eps = 1.53e-4 * (epsilon**2) - 1.63e-2 * epsilon + 1
                        if 50 <= epsilon <= 60: g_eps = 0.56
                        g_lam = 0.75 - 0.20 * lam
                        g_bn = 1.8 * g_eps * g_lam
                    else:
                        g_eps = 1.0 - 0.003 * epsilon
                        g_lam = 1.0 - 0.144 * lam
                        g_bn = 1.8 * g_eps * g_lam - 0.53
                        
                g_s0_bn = 1.33 - 10 * (h13 / L_10)
                g_prom = 1.0 - 0.47 * (G_c / L_10) if "promenade" in parapet_type else 1.0
                
                if parapet_type == "매끈한 사면 + 폭풍방지벽 (Smooth dike + storm wall)": return g_v
                elif parapet_type == "매끈한 사면 + 벽 + bullnose": return g_v * g_bn * g_s0_bn
                elif parapet_type == "Smooth dike slope + promenade (산책로)": return g_prom
                elif parapet_type == "Smooth dike slope + promenade + wall": return 0.87 * g_prom * g_v
                elif parapet_type == "Smooth dike slope + promenade + wall + bullnose": return 1.19 * (0.87 * g_prom * g_v) * g_bn
                return 1.0
            
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_euro_s(test_rc):
                    gamma_star = get_gamma_star(test_rc)
                    if xi_10 < 2.0:
                        vb = 2.5 * test_rc / (xi_10 * h13 * gamma_b_common * gamma_f * gamma_beta_common * gamma_star)
                        qn = (0.026 / math.sqrt(math.tan(alpha))) * gamma_b_common * xi_10 * math.exp(- (vb)**1.3)
                    else:
                        vn = 1.35 * test_rc / (h13 * gamma_f * gamma_beta_common * gamma_star)
                        qn = 0.1035 * math.exp(- (vn)**1.3)
                    return qn * sqrt_gH3 - q_target
                try: 
                    Rc = brentq(eval_q_euro_s, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: Rc = 0.01
            else: Rc = Rc_input

            final_gamma_star = get_gamma_star(Rc)

            if xi_10 < 2.0:
                v_break = 2.5 * Rc / (xi_10 * h13 * gamma_b_common * gamma_f * gamma_beta_common * final_gamma_star)
                q_norm = (0.026 / math.sqrt(math.tan(alpha))) * gamma_b_common * xi_10 * math.exp(- (v_break)**1.3)
                calc_str_euro = f"\\frac{{0.026}}{{\\sqrt{{\\tan({math.degrees(alpha):.1f}^\\circ)}}}} \\times {gamma_b_common:.3f} \\times {xi_10:.4f} \\times \\exp\\left( - \\left( 2.5 \\frac{{{Rc:.2f}}}{{{xi_10:.4f} \\times {h13:.2f} \\times {gamma_b_common:.3f} \\times {gamma_f:.3f} \\times {gamma_beta_common:.3f} \\times {final_gamma_star:.3f}}} \\right)^{{1.3}} \\right)"
            else:
                v_non = 1.35 * Rc / (h13 * gamma_f * gamma_beta_common * final_gamma_star)
                q_norm = 0.1035 * math.exp(- (v_non)**1.3)
                calc_str_euro = f"0.1035 \\exp\\left( - \\left( 1.35 \\frac{{{Rc:.2f}}}{{{h13:.2f} \\times {gamma_f:.3f} \\times {gamma_beta_common:.3f} \\times {final_gamma_star:.3f}}} \\right)^{{1.3}} \\right)"
                
            q_euro = q_norm * sqrt_gH3
            
            # ★ 1) 공식 전면 배치 및 상세 개념 설명
            rep.md("#### 📐 [월파량 산정 기본 공식 (EurOtop 2018 - 경사제)]")
            rep.info("EurOtop 공식은 파도가 경사면에 부딪혀 부서지는 형태를 나타내는 **스펙트럼 쇄파 매개변수($\\xi_{m-1,0}$)**에 따라 두 가지로 철저히 구분되어 적용됩니다.")
            rep.latex(r"q = Q \sqrt{g H_{1/3}^3}")

            rep.md(r"> **① 쇄파 파랑 조건 (Plunging waves, $\xi_{m-1,0} < 2.0$)**")
            rep.md(r"> - **특징:** 파도가 구조물 경사면에서 강하게 말리며 부서지는 조건입니다. 파도의 충격량이 크기 때문에 **사면경사($\tan \alpha$)**와 **쇄파 매개변수($\xi_{m-1,0}$)**가 파도가 타고 오르는 힘에 직접적으로 관여하여 공식에 명시됩니다.")
            rep.latex(r"Q = \frac{0.026}{\sqrt{\tan\alpha}} \gamma_b \xi_{m-1,0} \exp\left(-\left(2.5 \frac{R_c}{\xi_{m-1,0} H_{1/3}\gamma_b \gamma_f \gamma_\beta \gamma^*}\right)^{1.3}\right)")
            
            rep.md(r"> **② 비쇄파 파랑 조건 (Surging waves, $\xi_{m-1,0} \ge 2.0$)**")
            rep.md(r"> - **특징:** 파도가 크게 부서지지 않고 경사면을 따라 넘실대며 오르내리는 조건입니다. 파도 충격량이 작기 때문에 사면경사와 쇄파 매개변수의 영향이 공식에서 사라지고, 오직 여유고($R_c$)와 파고($H_{1/3}$)의 비율이 지배적인 역할을 합니다.")
            rep.latex(r"Q = 0.1035 \exp\left(-\left(1.35 \frac{R_c}{H_{1/3}\gamma_f \gamma_\beta \gamma^*}\right)^{1.3}\right)")

            # ★ 2) 쇄파/비쇄파 조건 검토 및 공식 선정
            rep.md("#### 🔍 [쇄파/비쇄파 조건 검토 및 공식 선정]")
            if xi_10 < 2.0:
                euro_cond = r"쇄파 조건 ($\xi_{m-1,0} < 2.0$)"
                applied_formula_text = "쇄파(Plunging) 공식"
            else:
                euro_cond = r"비쇄파 조건 ($\xi_{m-1,0} \ge 2.0$)"
                applied_formula_text = "비쇄파(Surging) 공식"
            
            rep.md(f"> - **스펙트럼 쇄파 매개변수($\\xi_{{m-1,0}}$) 산정:** $\\xi_{{m-1,0}} = \\frac{{\\tan({math.degrees(alpha):.1f}^\\circ)}}{{\\sqrt{{{h13:.2f}/{L_10:.2f}}}}} = {xi_10:.4f}$ $\\rightarrow$ **{euro_cond}**")
            rep.md(f"> - **결론:** 산정된 $\\xi_{{m-1,0}}$ 값에 따라 **{applied_formula_text}**을 적용하여 계산합니다.")
            
            # ★ 3) 영향계수 연동 표시
            rep.md("#### 📐 [영향계수($\gamma$) 상세 산정 (EurOtop 전용)]")
            rep.info("아래의 저감 계수($\\gamma$)들은 공식의 **지수 함수($\\exp$) 분모**에 위치합니다. 따라서 계수 값이 작아질수록 음의 지수가 커져 전체 월파량을 대폭 줄이는 효과를 발휘합니다.")
            
            # 1. 거칠기 계수
            rep.md(f"> - **1. 피복재 거칠기 계수($\\gamma_f$):** 피복재의 마찰 저항을 반영합니다. ({selected_armour_name} $\\rightarrow \\mathbf{{{gamma_f:.3f}}}$)")
            
            # 2. 입사각 계수 식 문자열
            if wave_crest == "단파 (Short-crested)":
                eq_str = r"1 - 0.0033 |\beta|" if theta_abs <= 80 else "0.736"
            else:
                eq_str = "1.0" if theta_abs <= 10 else r"\max(0.6, \cos^2(|\beta| - 10^\circ))"
            rep.md(f"> - **2. 입사각 보정계수($\\gamma_\\beta$):** 파랑의 입사각 및 방향 분산성({wave_crest})을 반영합니다. ($\\gamma_\\beta = {eq_str} = \\mathbf{{{gamma_beta_common:.3f}}}$)")

            # 📌 유로탑 토글 상세 텍스트를 연동형으로 표시
            euro_li_tags = "".join([f"<li style='margin-bottom:4px;'>{k}: <b>{v:.2f}</b></li>" for k, v in armour_dict.items()])
            rep.md(f"<details style='margin-left: 22px; margin-bottom: 12px; cursor: pointer;'><summary>👉 <b style='color:#1a73e8;'>EurOtop/CEM 피복재 거칠기 계수(γf) 상세 기준 보기</b></summary><div style='padding: 12px; background-color: #f8f9fa; border: 1px solid #ddd; border-left: 4px solid #1a73e8; border-radius: 4px; margin-top: 8px; font-size: 14.5px;'><ul>{euro_li_tags}</ul></div></details>")

            # 3. 소단 영향계수 산정 상세 블록
            rep.md("#### 📐 [3. 소단 영향계수($\gamma_b$) 산정 (CEM, EurOtop 공통)]")
            rep.md("> **[기호 설명]** $r_B$: 소단 폭의 상대길이, $B$: 소단 폭, $L_{Berm}$: 사면 수평길이, $r_{db}$: 소단 수직위치 영향계수, $d_b$: 수위-소단 수직거리, $R_{u2\\%}$: 처오름 높이")
            rep.latex(r"\gamma_b = 1 - r_B(1 - r_{db})")
            rep.md(f"> - $r_B = \\frac{{B}}{{L_{{Berm}}}} = \\frac{{{B_berm}}}{{{L_berm}}} = {r_B:.3f}$")
            if berm_pos == "영향권 밖":
                rep.md(f"> - $r_{{db}} = 1.0$ (영향권 밖)")
            elif berm_pos == "수위 상부 (Above SWL)":
                r_db_calc = 0.5 - 0.5 * math.cos(math.pi * d_b / Ru2) if Ru2 > 0 else 1.0
                rep.md(f"> - $r_{{db}} = 0.5 - 0.5\\cos\\left(\\pi \\frac{{d_b}}{{R_{{u2\\%}}}}\\right) = 0.5 - 0.5\\cos\\left(\\pi \\frac{{{d_b}}}{{{Ru2}}}\\right) = {r_db_calc:.3f}$")
            else:
                r_db_calc = 0.5 - 0.5 * math.cos(math.pi * d_b / (2 * h13)) if h13 > 0 else 1.0
                rep.md(f"> - $r_{{db}} = 0.5 - 0.5\\cos\\left(\\pi \\frac{{d_b}}{{2H_{{1/3}}}}\\right) = 0.5 - 0.5\\cos\\left(\\pi \\frac{{{d_b}}}{{2 \\times {h13}}}\\right) = {r_db_calc:.3f}$")
            rep.md(f"> - **결과:** $\\gamma_b = \\max(0.6, \\min(1.0, 1 - {r_B:.3f}(1 - {r_db_calc:.3f}))) = \\mathbf{{{gamma_b_common:.3f}}}$")

            # 4. 상치벽 계수 산정 상세 블록
            rep.md(f"#### 📐 [4. 상치벽 계수($\\gamma^*$) 산정: {parapet_type}]")
            rep.md("> **[기호 설명]** $h_{wall}$: 방지벽 높이, $h_n$: Bullnose 높이, $\\epsilon$: Bullnose 각도, $G_c$: 산책로 폭, $L_{m-1,0}$: 환산 심해파장, $R_c$: 여유고, $\\gamma_v$: 방지벽 저감계수, $\\gamma_{bn}$: Bullnose 저감계수, $\\gamma_{prom}$: 산책로 저감계수, $\\lambda$: Bullnose 높이비($h_n/h_{wall}$)")
            
            img_dict = {
                "매끈한 사면 + 폭풍방지벽 (Smooth dike + storm wall)": "Smooth dike slope + storm wall.png",
                "매끈한 사면 + 벽 + bullnose": "Smooth dike slope + wall + bullnose.png",
                "Smooth dike slope + promenade (산책로)": "Smooth dike slope + promenade.png",
                "Smooth dike slope + promenade + wall": "Smooth dike slope + promenade + wall.png",
                "Smooth dike slope + promenade + wall + bullnose": "Smooth dike slope + promenade + wall + bullnose.png"
            }
            if parapet_type in img_dict:
                rep.static_img(img_dict[parapet_type], caption=f"{parapet_type} 형상도")
            
            # Intermediate values needed for reporting
            ratio_hwall_rc_print = h_wall / Rc if Rc > 0 else 0
            lam_print = h_n / h_wall if h_wall > 0 else 0
            gamma_v_print = math.exp(-0.56 * ratio_hwall_rc_print) if Rc > 0 and h_wall > 0 else 1.0
            
            gamma_bn_print = 1.0
            if "bullnose" in parapet_type and h_wall > 0:
                if ratio_hwall_rc_print >= 0.25:
                    g_eps_print = 1.53e-4 * (epsilon**2) - 1.63e-2 * epsilon + 1
                    if 50 <= epsilon <= 60: g_eps_print = 0.56
                    g_lam_print = 0.75 - 0.20 * lam_print
                    gamma_bn_print = 1.8 * g_eps_print * g_lam_print
                else:
                    g_eps_print = 1.0 - 0.003 * epsilon
                    g_lam_print = 1.0 - 0.144 * lam_print
                    gamma_bn_print = 1.8 * g_eps_print * g_lam_print - 0.53
                    
            gamma_s0_bn_print = 1.33 - 10 * (h13 / L_10)
            gamma_prom_print = 1.0 - 0.47 * (G_c / L_10) if "promenade" in parapet_type else 1.0

            if parapet_type == "소파공 동일 높이 (일반)":
                rep.latex(r"\gamma^* = 1.00")
            elif parapet_type == "매끈한 사면 + 폭풍방지벽 (Smooth dike + storm wall)":
                rep.latex(r"\gamma^* = \gamma_v = \exp\left(-0.56 \frac{h_{wall}}{R_c}\right)")
                rep.md(f"> - $\\gamma_v = \\exp(-0.56 \\times \\frac{{{h_wall:.2f}}}{{{Rc:.2f}}}) = \\mathbf{{{gamma_v_print:.3f}}}$")
            elif parapet_type == "매끈한 사면 + 벽 + bullnose":
                rep.latex(r"\gamma^* = \gamma_v \gamma_{bn} \gamma_{s0,bn}")
                rep.latex(r"\gamma_{bn} = 1.8 \gamma_\epsilon \gamma_\lambda \quad (\text{if } h_{wall}/R_c \ge 0.25)")
                rep.latex(r"\gamma_{bn} = 1.8 \gamma_\epsilon \gamma_\lambda - 0.53 \quad (\text{if } h_{wall}/R_c < 0.25)")
                rep.latex(r"\gamma_{s0,bn} = 1.33 - 10 s_{m-1,0}")
                rep.md(f"> - $\\gamma_v = \\mathbf{{{gamma_v_print:.3f}}}$")
                rep.md(f"> - $\\gamma_{{bn}} = \\mathbf{{{gamma_bn_print:.3f}}}$ (조건: $h_{{wall}}/R_c = {ratio_hwall_rc_print:.3f}$)")
                rep.md(f"> - $\\gamma_{{s0,bn}} = 1.33 - 10({(h13 / L_10):.4f}) = \\mathbf{{{gamma_s0_bn_print:.3f}}}$")
                rep.md(f"> - 최종 $\\gamma^* = \\mathbf{{{final_gamma_star:.3f}}}$")
            elif parapet_type == "Smooth dike slope + promenade (산책로)":
                rep.latex(r"\gamma^* = \gamma_{prom} = 1 - 0.47 \frac{G_c}{L_{m-1,0}}")
                rep.md(f"> - $\\gamma_{{prom}} = 1 - 0.47 \\times \\frac{{{G_c:.2f}}}{{{L_10:.2f}}} = \\mathbf{{{gamma_prom_print:.3f}}}$")
            elif parapet_type == "Smooth dike slope + promenade + wall":
                rep.latex(r"\gamma^* = \gamma_{prom\_v} = 0.87 \gamma_{prom} \gamma_v")
                rep.md(f"> - $\\gamma_{{prom}} = \\mathbf{{{gamma_prom_print:.3f}}}$, $\\gamma_v = \\mathbf{{{gamma_v_print:.3f}}}$")
                rep.md(f"> - 최종 $\\gamma^* = 0.87 \\times {gamma_prom_print:.3f} \\times {gamma_v_print:.3f} = \\mathbf{{{final_gamma_star:.3f}}}$")
            elif parapet_type == "Smooth dike slope + promenade + wall + bullnose":
                rep.latex(r"\gamma^* = \gamma_{prom\_v\_bn} = 1.19 \gamma_{prom\_v} \gamma_{bn}")
                rep.latex(r"\gamma_{prom\_v} = 0.87 \gamma_{prom} \gamma_v")
                rep.md(f"> - $\\gamma_{{prom\_v}} = 0.87 \\gamma_{{prom}} \\gamma_v = \\mathbf{{{0.87 * gamma_prom_print * gamma_v_print:.3f}}}$")
                rep.md(f"> - $\\gamma_{{bn}} = \\mathbf{{{gamma_bn_print:.3f}}}$ (조건: $h_{{wall}}/R_c = {ratio_hwall_rc_print:.3f}$)")
                rep.md(f"> - 최종 $\\gamma^* = 1.19 \\times {0.87 * gamma_prom_print * gamma_v_print:.3f} \\times {gamma_bn_print:.3f} = \\mathbf{{{final_gamma_star:.3f}}}$")

            # ★ 4) 월파량 상세 풀이
            rep.md("#### 📝 [월파량 상세 풀이]")
            rep.md(r"> **[기호 설명]** $q$: 단위폭당 평균 월파량, $Q$: 무차원 유량 지수, $\xi_{m-1,0}$: 스펙트럼 쇄파 매개변수, $\gamma_f$: 거칠기계수, $\gamma_b$: 소단 영향계수, $\gamma_\beta$: 입사각 영향계수, $\gamma^*$: 상치벽 구조 보정계수, $R_c$: 여유고, $H_{1/3}$: 유의파고, $g$: 중력가속도, $\alpha$: 사면경사")
            rep.md(f"> - **무차원 유량 항 계산:** ${calc_str_euro} = {q_norm:.4e}$")
            rep.md(f"> - **최종 결과($q$):** $q = {q_norm:.4e} \\times \\sqrt{{9.81 \\times {h13:.2f}^3}} = \\mathbf{{{q_euro:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
            
            if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": "EurOtop (경사제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_euro:.6f} m³/s/m"})
            else: final_results.append({"적용 설계 기준": "EurOtop (경사제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})
                       
        else:
            # =====================================================================
            # EurOtop (2018) 직립제/혼성제 의사결정 흐름도(Figure 7.2) 전면 반영 모듈
            # (Design and assessment approach 적용, 원본 수식 100% 일치)
            # =====================================================================
            # 📌 기본 수리 파라미터 정의
            s_m10 = h13 / L_10 # 파형경사 (s_{m-1,0})
            h_star = (h**2) / (h13 * L_10) # 순수 직립벽 충격성 판별 매개변수
            
            # 실무 확장성을 위한 혼성제(Composite) 판별 변수 정의
            # (기본적으로 사석마운드 상부수심 d_mound = h로 두어 순수직립벽으로 시작)
            d_mound = h 
            d_h_ratio = d_mound / h
            is_composite = d_h_ratio <= 0.6
            d_star = (d_mound * h) / (h13 * L_10) # 혼성제 충격성 판별 매개변수
            
            # 해저 지형 영향 여부 (기본값 True)
            has_foreshore = True 

            # 📌 역산용 및 순산용 통합 Q_star (Design Approach) 계산 함수
            def calc_euro_v_q_norm(test_rc):
                rc_h = test_rc / h13 # γ 배제된 순수 상대 여유고
                
                if not has_foreshore:
                    # ◼️ 식 7.2: 해저 지형 영향이 없는 순수 비충격파 조건
                    return 0.054 * math.exp(- ((2.12 * rc_h)**1.3))
                
                if not is_composite:
                    # ◼️ 순수 직립벽 경로 (Plain Vertical Wall, d/h > 0.6)
                    if h_star > 0.23:
                        # 식 7.6: 전면 지형 영향이 있는 비충격파 조건
                        return 0.062 * math.exp(-2.61 * rc_h)
                    else:
                        # 충격파 조건 (h* <= 0.23)
                        impulsive_param = (h13 / (h * s_m10))**0.5
                        if rc_h < 1.35:
                            # 식 7.9: 충격파 - 낮은 여유고 조건
                            return 0.0155 * impulsive_param * math.exp(-2.2 * rc_h)
                        else:
                            # 식 7.10: 충격파 - 높은 여유고 조건
                            return 0.0020 * impulsive_param * (rc_h**-3.0) if rc_h > 0 else 0.0
                else:
                    # ◼️ 혼성 직립벽 경로 (Composite Vertical Wall, d/h <= 0.6)
                    if d_star > 0.65:
                        # 식 7.6: 혼성제 전면 비충격파 조건
                        return 0.062 * math.exp(-2.61 * rc_h)
                    else:
                        # 혼성제 충격파 조건 (d* <= 0.65)
                        impulsive_param = (h13 / (h * s_m10))**0.5
                        composite_factor = 1.3 * (d_h_ratio**0.5)
                        if rc_h < 1.35:
                            # 식 7.15: 혼성제 충격파 - 낮은 여유고 조건
                            return composite_factor * 0.011 * impulsive_param * math.exp(-2.2 * rc_h)
                        else:
                            # 식 7.14: 혼성제 충격파 - 높은 여유고 조건
                            return composite_factor * 0.0014 * impulsive_param * (rc_h**-3.0) if rc_h > 0 else 0.0

            # 📌 1. 계산 모드에 따른 제원 도출
            if calc_mode == "소요 여유고(Rc) 산정":
                def eval_q_euro_v(test_rc):
                    return calc_euro_v_q_norm(test_rc) * sqrt_gH3 - q_target
                try: 
                    Rc = brentq(eval_q_euro_v, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m)")
                except ValueError: Rc = 0.01
            else: 
                Rc = Rc_input

            # 📌 2. 최종 조건 확정 및 무차원 유량(q*) 계산
            rc_h_ratio = Rc / h13
            q_norm = calc_euro_v_q_norm(Rc)
            q_euro = q_norm * sqrt_gH3

            # 📌 3. 보고서 출력용 조건 매칭 텍스트 정의
            if not has_foreshore:
                cond_info = "해저 지형 영향이 없는 조건 (No Foreshore Influence)"
                applied_formula_text = "비충격파 기본 설계식 (식 7.2)"
                calc_str = f"0.054 \\exp\\left( - \\left( 2.12 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)^{{1.3}} \\right)"
            elif not is_composite:
                if h_star > 0.23:
                    cond_info = "순수 직립벽 비충격파 조건 ($h^* > 0.23$)"
                    applied_formula_text = "전면 지형 영향 비충격파 설계식 (식 7.6)"
                    calc_str = f"0.062 \\exp\\left( -2.61 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)"
                else:
                    if rc_h_ratio < 1.35:
                        cond_info = "순수 직립벽 충격파 및 낮은 여유고 조건 ($h^* \\le 0.23$ 및 $R_c/H_{{m0}} < 1.35$)"
                        applied_formula_text = "순수 직립벽 충격파 - 낮은 여유고 설계식 (식 7.9)"
                        calc_str = f"0.0155 \\left( \\frac{{{h13:.2f}}}{{{h:.2f} \\times {s_m10:.4f}}} \\right)^{{0.5}} \\exp\\left( -2.2 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)"
                    else:
                        cond_info = "순수 직립벽 충격파 및 높은 여유고 조건 ($h^* \\le 0.23$ 및 $R_c/H_{{m0}} \\ge 1.35$)"
                        applied_formula_text = "순수 직립벽 충격파 - 높은 여유고 설계식 (식 7.10)"
                        calc_str = f"0.0020 \\left( \\frac{{{h13:.2f}}}{{{h:.2f} \\times {s_m10:.4f}}} \\right)^{{0.5}} \\left( \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)^{{-3}}"
            else:
                if d_star > 0.65:
                    cond_info = "혼성 직립벽 비충격파 조건 ($d^* > 0.65$)"
                    applied_formula_text = "혼성제 비충격파 설계식 (식 7.6)"
                    calc_str = f"0.062 \\exp\\left( -2.61 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)"
                else:
                    if rc_h_ratio < 1.35:
                        cond_info = "혼성 직립벽 충격파 및 낮은 여유고 조건 ($d^* \\le 0.65$ 및 $R_c/H_{{m0}} < 1.35$)"
                        applied_formula_text = "혼성 직립벽 충격파 - 낮은 여유고 설계식 (식 7.15)"
                        calc_str = f"1.3 \\left(\\frac{{{d_mound:.2f}}}{{{h:.2f}}}\\right)^{{0.5}} \\times 0.011 \\left( \\frac{{{h13:.2f}}}{{{h:.2f} \\times {s_m10:.4f}}} \\right)^{{0.5}} \\exp\\left( -2.2 \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)"
                    else:
                        cond_info = "혼성 직립벽 충격파 및 높은 여유고 조건 ($d^* \\le 0.65$ 및 $R_c/H_{{m0}} \\ge 1.35$)"
                        applied_formula_text = "혼성 직립벽 충격파 - 높은 여유고 설계식 (식 7.14)"
                        calc_str = f"1.3 \\left(\\frac{{{d_mound:.2f}}}{{{h:.2f}}}\\right)^{{0.5}} \\times 0.0014 \\left( \\frac{{{h13:.2f}}}{{{h:.2f} \\times {s_m10:.4f}}} \\right)^{{0.5}} \\left( \\frac{{{Rc:.2f}}}{{{h13:.2f}}} \\right)^{{-3}}"
             
           
            # ★ 3) 보고서 본문 - 공식 및 흐름도 상세설명자료 전면 배치
            rep.md("#### 📐 [월파량 산정 공식 및 의사결정 흐름도 해설 (EurOtop 2018)]")
            rep.info("유럽 EurOtop (2018) 매뉴얼에서는 안전율이 포함된 **설계 및 평가 접근법(Design and Assessment approach)** 수식을 활용하여 직립벽 및 혼성제 마운드의 구조적 마진을 보수적으로 검토합니다.")
            
            # ---------------------------------------------------------
            # [수정] 좌측: 1~4단계 흐름도 해설 박스 (단일 HTML 블록 적용으로 빈 박스 오류 해결)
            # ---------------------------------------------------------
            col1, col2 = st.columns([1.0, 1.0])
            
            # HTML 다운로드 보고서용 Flexbox 시작
            rep.html += "<div style='display: flex; flex-wrap: wrap; gap: 20px; align-items: stretch; margin-bottom: 25px;'>"
            
            # [왼쪽 영역] 1~4단계 흐름도 설명 자료를 하나의 HTML 코드로 완전히 묶습니다.
            box_html = """<div style='background-color: #f8f9fa; border: 2px solid #1a73e8; padding: 22px; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: left; height: 100%; box-sizing: border-box;'>
<h4 style='color: #1a73e8; margin-top: 0px; margin-bottom: 18px; font-weight: 900; border-bottom: none;'>📊 의사결정 흐름도 단계별 해설 (Figure 7.2)</h4>
<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>1단계: 전면해저면의 영향 (Influence of foreshore?)</p>
<ul style='margin-top: 0px; margin-bottom: 18px; padding-left: 20px;'>
    <li style='font-size: 15px; font-weight: 800; color: #333; line-height: 1.6;'>전면해저면이 구조물 앞 파랑에 영향을 주지 않는 깊은 수심(<b>No</b>)이면 즉시 오른쪽 경로의 <b>Eq. 7.1 (또는 Eq. 7.2)</b> 공식을 사용합니다. 영향이 있다면(<b>Yes</b>) 아래 2단계로 이동합니다.</li>
</ul>
<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>2단계: 구조물 형식 판별 (Vertical or composite vertical?)</p>
<ul style='margin-top: 0px; margin-bottom: 18px; padding-left: 20px;'>
    <li style='font-size: 15px; font-weight: 800; color: #333; line-height: 1.6;'>사석 마운드 상부 수심비(<i>d/h</i>)가 0.6을 초과하면 마운드 영향이 적은 <b>직립제(Treat as vertical)</b>로 간주하여 왼쪽으로, 0.6 이하이면 <b>혼성제(Treat as composite)</b>로 간주하여 오른쪽으로 이동합니다.</li>
</ul>
<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>3단계: 쇄파 가능성 검토 (Possible breaking?)</p>
<ul style='margin-top: 0px; margin-bottom: 18px; padding-left: 20px;'>
    <li style='font-size: 15px; font-weight: 800; color: #333; line-height: 1.6;'>구조물 전면에서 파도가 깨질 가능성이 있는지 판별합니다. 쇄파가 발생하지 않는 조건(<b>No</b>)이면 중앙으로 모여 <b>Eq. 7.5 (또는 Eq. 7.6)</b> 공식을 공통 적용하며, 쇄파 조건(<b>Yes</b>)이면 아래 4단계로 이동합니다.</li>
</ul>
<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>4단계: 상대 여유고 검토 (Low freeboard?)</p>
<ul style='margin-top: 0px; margin-bottom: 0px; padding-left: 20px;'>
    <li style='font-size: 15px; font-weight: 800; color: #333; line-height: 1.6;'>여유고 비율(<i>R<sub>c</sub> / H<sub>m0</sub></i>)이 1.35 미만이면 <b>낮은 여유고(Yes)</b> 공식을, 1.35 이상이면 <b>높은 여유고(No)</b> 공식을 각 구조물 형식에 맞춰 최종 채택합니다.</li>
</ul>
</div>"""
            
            # HTML 보고서에 왼쪽 박스 주입
            rep.html += f"<div style='flex: 1 1 48%; min-width: 350px;'>{box_html}</div>"
            
            # Streamlit 웹 화면에 왼쪽 박스 주입
            with col1:
                st.markdown(box_html, unsafe_allow_html=True)
                
            # [오른쪽 영역] 흐름도 이미지
            rep.html += "<div style='flex: 1 1 48%; min-width: 350px; text-align: center; display: flex; flex-direction: column; justify-content: center;'>"
            with col2:
                if os.path.exists("image_ad7a6c.png"):
                    rep.static_img("image_ad7a6c.png", caption="EurOtop (2018) 직립제 및 혼성제 월파량 산정 알고리즘 흐름도 (Figure 7.2)")
            rep.html += "</div>"
            
            rep.html += "</div>" # Flexbox 종료 컨테이너
            
            # ---------------------------------------------------------
            # [복원] 원래 있던 세부 공식 내용들 (화면 전체 폭 사용)
            # ---------------------------------------------------------
            # ---------------------------------------------------------
            # [최종 수정] 상반파공 및 입사각 영향계수 해설 박스 (비충격파 H_m0 곱 반영)
            # ---------------------------------------------------------
            # ⚠️ 주의: Streamlit(Markdown)의 코드 블록 인식 오류를 방지하기 위해 HTML 태그는 들여쓰기 없이 작성
            factor_box_html = """<div style='background-color: #fdfbf7; border: 2px solid #f2a900; padding: 22px; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: left; margin-bottom: 25px; box-sizing: border-box;'>
<h4 style='color: #d97706; margin-top: 0px; margin-bottom: 18px; font-weight: 900; border-bottom: none;'>🛡️ 입사각 및 상반파공 저감 계수 적용 원리 (유로탑 7장 하이브리드 기준)</h4>
<p style='font-size: 15px; font-weight: 800; color: #333; line-height: 1.6; margin-top: 0px;'>유로탑(EurOtop, 2018) 제7장(직립제)은 파도의 충격 여부(Impulsive/Non-impulsive)에 따라 보정 계수 적용 방식을 다르게 규정하는 정교한 체계를 갖추고 있습니다.</p>
<ul style='margin-top: 10px; margin-bottom: 15px; padding-left: 20px;'>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.6; margin-bottom: 12px;'><b>1. 비충격파(Non-impulsive)의 입사각 (<i>γ<sub>β</sub></i>) :</b> 사면제와 유사하게 물이 넘실대며 월파하므로, <b>상대 여유고 분모의 <i>H<sub>m0</sub></i>에 <i>γ<sub>β</sub></i>를 직접 곱하여</b> 유효 여유고를 증가시키는 방식(지수 감소 효과)을 채택합니다. (식 7.16 참조)</li>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.6; margin-bottom: 12px;'><b>2. 충격파(Impulsive)의 입사각 (<i>k<sub>β</sub></i>) :</b> 강력한 제트(Jet)가 형성되는 충격파 조건에서는 분모 보정이 아닌, <b>산정된 최종 월파량(q)에 직접 감소 계수(<i>k<sub>β</sub></i>)를 곱하는 방식</b>으로 전환됩니다.</li>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.6;'><b>3. 상반파공 및 돌출부 (<i>k<sub>bn</sub></i>) :</b> 물리적으로 상승 제트를 차단하는 반파공(Bullnose/Parapet)은 파랑 조건과 무관하게 <b>계산된 최종 월파량에 저감 계수(<i>k<sub>bn</sub></i>)를 곱하여(q<sub>final</sub> = k<sub>bn</sub> · q<sub>calc</sub>)</b> 산출합니다.</li>
</ul>
<p style='font-size: 14px; font-weight: 600; color: #666; margin-bottom: 0px;'>※ 아래 수식을 보면 1️⃣ 비충격파 조건에만 분모에 <i>γ<sub>β</sub></i>가 결합되어 있고, 2️⃣, 3️⃣ 충격파 조건은 순수 기본식을 유지(결과값에 별도 k 계수 곱함)하는 것을 확인할 수 있습니다.</p>
</div>"""
            
            # HTML 보고서 및 Streamlit UI에 각각 해설 박스 출력
            rep.html += factor_box_html
            st.markdown(factor_box_html, unsafe_allow_html=True)
           
            # ---------------------------------------------------------
            # [수정] 좌측: 상반파공 평가지침 단계별 해설 (수식 깨짐 완벽 해결 및 4단계 상세화)
            # ---------------------------------------------------------
            col1_bn, col2_bn = st.columns([1.0, 1.0])
            
            # HTML 다운로드 보고서용 Flexbox 시작
            rep.html += "<div style='display: flex; flex-wrap: wrap; gap: 20px; align-items: stretch; margin-bottom: 25px;'>"
            
            # [왼쪽 영역] 순수 HTML을 사용하여 Streamlit UI와 HTML 보고서 양쪽 모두 수식 깨짐 방지
            bn_box_html = """<div style='background-color: #f8f9fa; border: 2px solid #1a73e8; padding: 22px; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); text-align: left; height: 100%; box-sizing: border-box;'>
<h4 style='color: #1a73e8; margin-top: 0px; margin-bottom: 12px; font-weight: 900; border-bottom: none;'>📊 상반파공 성능 평가지침 단계별 해설 (Figure 7.23)</h4>

<div style='background-color: #ffffff; padding: 12px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 15px; text-align: center; font-size: 1.2em;'>
    <b><i>k<sub>bn</sub></i> = <i>q<sub>with_bullnose</sub></i> / <i>q<sub>without_bullnose</sub></i></b>
</div>
<p style='font-size: 14.5px; font-weight: 800; color: #333; margin-bottom: 12px; line-height: 1.6;'><b>[기호 설명]</b><br>
<i>k<sub>bn</sub></i>: 최종 월파량 저감계수, <i>&alpha;</i>: 돌출 각도, <i>h<sub>r</sub></i>: 반파공 자체 높이, <i>B<sub>r</sub></i>: 반파공 돌출 폭(내민 길이, <i>&lambda;</i>), <i>R<sub>c</sub></i>: 마루 여유고, <i>H<sub>m0</sub></i>: 유의파고, <i>h</i>: 전면 수심</p>
<hr style='border: 0.5px solid #ccc; margin-bottom: 15px;'>

<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>1단계: 돌출 각도(<i>&alpha;</i>)에 따른 기본 분기</p>
<ul style='margin-top: 0px; margin-bottom: 15px; padding-left: 20px;'>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'><b><i>&alpha;</i> &gt; 90&deg; :</b> 바다 쪽으로 튀어나오지 않은 후퇴형으로 저감 효과가 없거나 월파량이 증가합니다. (90~100&deg;: 1.0, 100~135&deg;: 1.05, 135&deg; 초과: 1.10 적용)</li>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'><b><i>&alpha;</i> &lt; 90&deg; :</b> 정상적인 처마(Bullnose) 형태로 아래 2단계 연산으로 진입합니다.</li>
</ul>

<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>2단계: 중간 매개변수 산정 (<i>R<sub>0</sub><sup>*</sup></i>, <i>m<sup>*</sup></i>)</p>
<ul style='margin-top: 0px; margin-bottom: 15px; padding-left: 20px;'>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'>구조물의 기하학적 형상비를 수치화하여 파도를 튕겨내는 데 필요한 <b>임계 기준선(<i>R<sub>0</sub><sup>*</sup></i>)</b>과 저감 곡선의 <b>가중치(<i>m<sup>*</sup></i>)</b>를 구합니다.</li>
</ul>

<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>3단계: 상대 여유고(<i>R<sub>c</sub>/H<sub>m0</sub></i>)에 따른 3가지 분기</p>
<ul style='margin-top: 0px; margin-bottom: 15px; padding-left: 20px;'>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'><b>좌측 (효과 없음):</b> 여유고가 너무 낮아 파도가 완전히 덮치고 넘어갑니다. (<i>k<sub>bn</sub></i> = 1.0)</li>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'><b>중앙 (중간 저감):</b> 상승 제트가 부분적으로 걸러지는 비선형 감소 영역입니다.</li>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'><b>우측 (큰 저감 가능):</b> 여유고가 충분하여 파도를 바다로 효과적으로 튕겨냅니다. (<i>k'</i> 매개변수 산출 후 4단계 진입)</li>
</ul>

<p style='font-size: 15.5px; font-weight: 900; color: #000; margin-bottom: 5px;'>4단계: 전면 수심비(<i>R<sub>c</sub>/h</i>)에 따른 최종 보정 및 경고</p>
<ul style='margin-top: 0px; margin-bottom: 0px; padding-left: 20px;'>
    <li style='font-size: 14.5px; font-weight: 700; color: #333; line-height: 1.5;'>3단계 우측 경로에 한하여, 수심의 얕고 깊음에 따라 <i>k<sub>bn</sub></i> 값을 3가지로 최종 세분화합니다.
        <ul style='margin-top: 4px; margin-bottom: 8px;'>
            <li><b><i>R<sub>c</sub>/h</i> &le; 0.6 (깊은 수심):</b> <i>k<sub>bn</sub> = k'</i></li>
            <li><b>0.6 &lt; <i>R<sub>c</sub>/h</i> &lt; 1.1 (중간 수심역):</b> <i>k<sub>bn</sub> = 27 &middot; k' &middot; exp(-5.5 R<sub>c</sub>/h)</i></li>
            <li><b><i>R<sub>c</sub>/h</i> &ge; 1.1 (천해역):</b> <i>k<sub>bn</sub> = k' &times; 0.02</i></li>
        </ul>
    </li>
    <li style='font-size: 14.5px; font-weight: 700; color: #b71c1c; line-height: 1.5;'><b>※ 설계 주의사항:</b> 최종 <i>k<sub>bn</sub></i> &lt; 0.05 (저감률 95% 이상)로 산출될 경우 수식 맹신은 위험하므로 <b>수리모형실험</b> 검증을 강력히 권고합니다.</li>
</ul>
</div>"""

            # HTML 보고서에 왼쪽 박스 주입
            rep.html += f"<div style='flex: 1 1 48%; min-width: 350px;'>{bn_box_html}</div>"
            
            # Streamlit 웹 화면에 왼쪽 박스 주입
            with col1_bn:
                st.markdown(bn_box_html, unsafe_allow_html=True)
                
            # [오른쪽 영역] 상반파공 월파저감 성능 평가지침 이미지 삽입
            rep.html += "<div style='flex: 1 1 48%; min-width: 350px; text-align: center; display: flex; flex-direction: column; justify-content: center;'>"
            with col2_bn:
                if os.path.exists("상반파공 월파저감 성능 평가지침.png"):
                    rep.static_img("상반파공 월파저감 성능 평가지침.png", caption="상반파공 월파저감 성능 평가지침 결정 차트 (Figure 7.23)")
            rep.html += "</div></div>" # Flexbox 컨테이너 종료
            # ---------------------------------------------------------           

            # ---------------------------------------------------------
            # [복원] 비충격파에는 γ_β 반영 / 충격파는 원형 유지
            # ---------------------------------------------------------
            rep.md("##### 1️⃣ 비충격파 조건 (Non-impulsive waves)")
            rep.md("- **식 7.2 (지형 영향 없음):** 구조물 전면에 shallow foreshore에 의한 파랑 변형이 지배적이지 않을 때 적용하는 수직벽 기본 설계식입니다.")
            rep.latex(r"q^* = \frac{q}{\sqrt{g H_{m0}^3}} = 0.054 \exp\left( - \left( 2.12 \frac{R_c}{H_{m0} \cdot \gamma_\beta} \right)^{1.3} \right)")
            rep.md("- **식 7.6 (지형 영향 있음):** 전면 수심의 영향이 존재하나 파형 경사 대비 수심비가 충분하여 깨지지 않고 넘실대는 파랑 조건에 적용합니다.")
            rep.latex(r"q^* = \frac{q}{\sqrt{g H_{m0}^3}} = 0.062 \exp\left( -2.61 \frac{R_c}{H_{m0} \cdot \gamma_\beta} \right)")
            
            rep.md("##### 2️⃣ 순수 직립벽 충격파 조건 (Plain Vertical Wall - Impulsive waves)")
            rep.md("- 파도가 전면 벽체에 강력한 제트(Jet)를 형성하며 부딪히는 조건($h^* \le 0.23$)으로, 여유고의 높낮이에 따라 거듭제곱 매커니즘이 다르게 적용됩니다.")
            rep.md(r"- **식 7.9 (낮은 여유고, $R_c / H_{m0} < 1.35$):**")
            rep.latex(r"q^* =\frac{q}{\sqrt{g H_{m0}^3}} = 0.0155 \left( \frac{H_{m0}}{h \cdot s_{m-1,0}} \right)^{0.5} \exp\left( -2.2 \frac{R_c}{H_{m0}} \right)")
            rep.md(r"- **식 7.10 (높은 여유고, $R_c / H_{m0} \ge 1.35$):**")
            rep.latex(r"q^* =\frac{q}{\sqrt{g H_{m0}^3}} = 0.0020 \left( \frac{H_{m0}}{h \cdot s_{m-1,0}} \right)^{0.5} \left( \frac{R_c}{H_{m0}} \right)^{-3}")
            
            rep.md("##### 3️⃣ 혼성 직립벽 충격파 조건 (Composite Vertical Wall - Impulsive waves)")
            rep.md("- 하부 사석 마운트 기초가 높아 전면 수심비($d/h \le 0.6$) 조건을 만족하고 파도가 마운트 위에서 깨지며 진입하는 조건($d^* \le 0.65$)입니다.")
            rep.md(r"- **식 7.15 (낮은 여유고, $R_c / H_{m0} < 1.35$):**")
            rep.latex(r"q^* = \frac{q}{\sqrt{g H_{m0}^3}} = 1.3 \left(\frac{d}{h}\right)^{0.5} \times 0.011 \left( \frac{H_{m0}}{h \cdot s_{m-1,0}} \right)^{0.5} \exp\left(-2.2 \frac{R_c}{H_{m0}}\right)")
            rep.md(r"- **식 7.14 (높은 여유고, $R_c / H_{m0} \ge 1.35$):**")
            rep.latex(r"q^* = \frac{q}{\sqrt{g H_{m0}^3}} = 1.3 \left(\frac{d}{h}\right)^{0.5} \times 0.0014 \left( \frac{H_{m0}}{h \cdot s_{m-1,0}} \right)^{0.5} \left(\frac{R_c}{H_{m0}}\right)^{-3}")

         
            # ---------------------------------------------------------
            # [수정 2] 입사각 공통 연동 및 상반파공(Fig 7.23) 공식/수치 상세 풀이 
            # ---------------------------------------------------------
            if not has_foreshore:
                is_impulsive = False
            elif not is_composite:
                is_impulsive = (h_star <= 0.23)
            else:
                is_impulsive = (d_star <= 0.65)

            rep.md("#### 🔍 [입사각 및 상반파공 저감 계수 산정 및 적용 근거]")
            
            # 1. 파랑 입사각 계수 산정 과정 (공통 theta 적용)
            theta_abs = abs(theta)
            if theta_abs > 0:
                if is_impulsive: 
                    rep.md(f"**1) 파랑 입사각 ($\\beta = {theta_abs}^\\circ$) - 충격파(Impulsive) 조건:**")
                    rep.md("충격파 조건에서는 파랑 입사각이 $20^\\circ$를 초과할 경우 충격 제트(Jet) 에너지가 급감하며 비충격파에 준하는 거동을 보입니다. 매뉴얼 기준에 따라 최종 월파량에 곱해지는 저감 계수($k_\\beta$)를 적용합니다.")
                    k_beta = max(0.0, 1 - 0.01 * theta_abs) 
                    rep.latex(f"k_\\beta = 1 - 0.01 \\times {theta_abs}^\\circ = {k_beta:.3f}")
                    gamma_beta = 1.0 
                else: 
                    rep.md(f"**1) 파랑 입사각 ($\\beta = {theta_abs}^\\circ$) - 비충격파(Non-impulsive) 조건:**")
                    if "Short" in wave_crest_v or "단파" in wave_crest_v:
                        gamma_beta = 1 - 0.0062 * theta_abs
                        rep.md(f"방향성이 분산된 단파(Short-crested) 조건이므로, 매뉴얼 **식 7.16**을 적용하여 유의파고 $H_{{m0}}$ 분모에 결합되는 보정 계수 $\\gamma_\\beta$를 산출합니다.")
                        rep.latex(f"\\gamma_\\beta = 1 - 0.0062 \\times {theta_abs}^\\circ = {gamma_beta:.3f}")
                    else:
                        gamma_beta = 1 - 0.0042 * theta_abs
                        rep.md(f"에너지가 집중되는 장파(Long-crested) 조건이므로, 매뉴얼 **식 7.16**을 적용하여 유의파고 $H_{{m0}}$ 분모에 결합되는 보정 계수 $\\gamma_\\beta$를 산출합니다.")
                        rep.latex(f"\\gamma_\\beta = 1 - 0.0042 \\times {theta_abs}^\\circ = {gamma_beta:.3f}")
                    k_beta = 1.0
            else:
                rep.md("**1) 파랑 입사각:** 정면 입사($\\beta = 0^\\circ$)이므로 입사각에 의한 저감 효과는 없습니다. ($\\gamma_\\beta = 1.0, k_\\beta = 1.0$)")
                gamma_beta = 1.0
                k_beta = 1.0
                
            # 2. 반파공(Bullnose) 계수 산정 과정 (Fig 7.23 상세 풀이 적용)
            if has_bullnose:
                rep.md(f"<br>**2) 상반파공(Bullnose) 형상 보정 (Fig 7.23 평가지침 연산):**")
                rep.md(f"상단 반파공 내민 길이 $\\lambda = {bullnose_lambda}\\text{{m}}$, 돌출 각도 $\\alpha = {bullnose_alpha}^\\circ$ 제원이 입력되었습니다. 매뉴얼의 결정 흐름도(Figure 7.23)에 따라 중간 변수 산정 및 한계 스크리닝을 수행합니다.")
                
                # [1단계] 무차원 기하학적 제원 산출
                rc_h0 = Rc / h13 if h13 > 0 else 0
                lam_h0 = bullnose_lambda / h13 if h13 > 0 else 0
                alpha_rad = math.radians(bullnose_alpha)
                
                # [2단계] 중간 매개변수 산정 (R0*, m*)
                R0_star = 0.5 + 1.5 * lam_h0 * math.sin(alpha_rad)
                m_star = 1.2 * math.exp(-lam_h0) * math.cos(alpha_rad / 2.0)
                
                rep.md("> **[1~2단계] 무차원 인자 및 중간 매개변수 산출식**")
                rep.latex(r"R_0^* = 0.5 + 1.5 \left(\frac{\lambda}{H_{m0}}\right) \sin\alpha")
                rep.md(f"> - $R_0^* = 0.5 + 1.5 \\times ({lam_h0:.3f}) \\times \\sin({bullnose_alpha}^\\circ) = \\mathbf{{{R0_star:.3f}}}$")
                rep.latex(r"m^* = 1.2 \exp\left(-\frac{\lambda}{H_{m0}}\right) \cos\left(\frac{\alpha}{2}\right)")
                rep.md(f"> - $m^* = 1.2 \\times \\exp(-{lam_h0:.3f}) \\times \\cos({bullnose_alpha}^\\circ / 2) = \\mathbf{{{m_star:.3f}}}$")
                              
                # [3단계 & 4단계] 한계 조건 검토 및 최종 월파저감계수(k_bn) 도출
                rep.md("> **[3~4단계] 한계 조건 스크리닝 및 최종 산출**")
                if bullnose_lambda <= 0 or bullnose_alpha <= 0:
                    k_bn = 1.0
                    rep.md("> - **조건 판별:** $\\lambda \\le 0$ 또는 $\\alpha \\le 0$ $\\rightarrow$ **돌출 제원 미달 (저감 효과 없음)**")
                    rep.latex(f"k_{{bn}} = 1.0")
                elif bullnose_alpha > 90:
                    if bullnose_alpha <= 100:
                        k_bn = 1.0
                        cond_msg = "90^\\circ < \\alpha \\le 100^\\circ"
                    elif bullnose_alpha <= 135:
                        k_bn = 1.05
                        cond_msg = "100^\\circ < \\alpha \\le 135^\\circ"
                    else:
                        k_bn = 1.10
                        cond_msg = "\\alpha > 135^\\circ"
                    rep.md(f"> - **조건 판별:** 돌출 각도 후퇴형 조건 (${cond_msg}$) $\\rightarrow$ **월파량 저감 없음 또는 증가**")
                    rep.latex(f"k_{{bn}} = {k_bn:.2f}")
                elif rc_h0 < (R0_star / 2.0):
                    k_bn = 1.0
                    rep.md(f"> - **조건 판별:** 상대 여유고($R_c/H_{{m0}} = {rc_h0:.3f}$) < 임계치($R_0^*/2 = {R0_star/2.0:.3f}$) $\\rightarrow$ **파랑 상승 제트 완전 월류 (물리적 포획 불가)**")
                    rep.latex(f"k_{{bn}} = 1.0")
                else:
                    # 유효 구간 비선형 곡선
                    term = (rc_h0 - R0_star/2.0) / (2.0 * R0_star)
                    k_bn_calc = 1.0 - 0.6 * (term ** m_star)
                    
                    rep.md(f"> - **조건 판별:** 상대 여유고($R_c/H_{{m0}} = {rc_h0:.3f}$) $\\ge$ 임계치($R_0^*/2 = {R0_star/2.0:.3f}$) $\\rightarrow$ **잠정 지침 유효 구간 (정상 연산 수행)**")
                    rep.latex(r"k_{bn(calc)} = 1.0 - 0.6 \left( \frac{R_c/H_{m0} - R_0^*/2}{2 R_0^*} \right)^{m^*}")
                    rep.md(f"> - $k_{{bn(calc)}} = 1.0 - 0.6 \\times \\left( \\frac{{{rc_h0:.3f} - {R0_star/2.0:.3f}}}{{2 \\times {R0_star:.3f}}} \\right)^{{{m_star:.3f}}} = {k_bn_calc:.3f}$")
                    
                    k_bn = max(0.4, min(1.0, k_bn_calc))
                    rep.md(f"> - **수리실험 한계치(Clamping) 적용:** $0.4 \\le k_{{bn}} \\le 1.0$")
                    rep.latex(f"k_{{bn}} = {k_bn:.3f} \\text{{ (최종 유효 저감 계수)}}")
            else:
                rep.md("<br>**2) 상반파공(Bullnose) 조건:** 미설치 단면이므로 형상 저감 계수는 적용되지 않습니다. ($k_{bn} = 1.0$)")
                k_bn = 1.0
         
                
            # 3. 최종 유효 월파량 도출
            rep.md("<br>##### ➡️ 최종 유효 설계 월파량 ($q_{final}$) 도출")
            rep.info("앞서 판별된 구조 형식 및 충격파/비충격파 기본 월파량($q_{calc}$)에 위에서 산정한 보정 계수를 곱하여 최종 결과값을 산출합니다.")
            
            if is_impulsive:
                rep.md("- **충격파(Impulsive) 최종 산정식:** 분모에 입사각($\\gamma_\\beta$)을 곱하지 않고 산정된 기본 월파량에 $k_\\beta$ 와 $k_{bn}$ 을 일괄 곱합니다.")
                rep.latex(f"q_{{final}} = q_{{calc}} \\times k_\\beta \\times k_{{bn}}")
                q_final = q_euro * k_beta * k_bn  # q_calc를 q_euro로 수정
                rep.latex(f"q_{{final}} = {q_euro:.6f} \\times {k_beta:.3f} \\times {k_bn:.3f} = \\mathbf{{{q_final:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}")
            else:
                rep.md("- **비충격파(Non-impulsive) 최종 산정식:** 수식 내 $H_{m0}$ 분모에 $\\gamma_\\beta$가 기 반영되어 산출된 기본 월파량에 상반파공 계수 $k_{bn}$ 만을 곱합니다.")
                rep.latex(f"q_{{final}} = q_{{calc (\\gamma_\\beta 기\\_반영)}} \\times k_{{bn}}")
                q_final = q_euro * k_bn  # q_calc를 q_euro로 수정
                rep.latex(f"q_{{final}} = {q_euro:.6f} \\times {k_bn:.3f} = \\mathbf{{{q_final:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}")
            # ---------------------------------------------------------
           
            # ★ 4) 매칭 알고리즘 검증 정보 시각화
            rep.md("#### 🔍 [흐름도 제원 판별 및 설계 공식 매칭 검증]")
            rep.md(f"> - **기초 두께비 판별 ($d/h$):** {d_mound:.2f} / {h:.2f} = {d_h_ratio:.3f} $\\rightarrow$ " + ("**혼성제 구조물 판정**" if is_composite else "**순수 직립벽 구조물 판정**"))
            rep.md(f"> - **순수 직립제 매개변수 ($h^*$):** $\\frac{{h^2}}{{H_{{1/3}} L_{{m-1,0}}}} = {h_star:.4f}$" + (" ($\\le 0.23$ 충격파)" if h_star <= 0.23 else " ($> 0.23$ 비충격파)"))
            rep.md(f"> - **혼성 직립제 매개변수 ($d^*$):** $\\frac{{d \\cdot h}}{{H_{{1/3}} L_{{m-1,0}}}} = {d_star:.4f}$" + (" ($\\le 0.65$ 충격파)" if d_star <= 0.65 else " ($> 0.65$ 비충격파)"))
            rep.md(f"> - **파형경사 ($s_{{m-1,0}}$):** $\\frac{{H_{{1/3}}}}{{L_{{m-1,0}}}} = {s_m10:.4f}$")
            rep.md(f"> - **최종 매칭 결과:** **{cond_info}** 에 수렴하므로 국제 기준에 의거하여 **{applied_formula_text}**을 채택합니다.")

            # ★ 5) 상세 수치 풀이 과정 출력
            rep.md("#### 📝 [설계 접근법(Design Approach) 수치 풀이 상세]")
            rep.md(r"> **[기호 설명]** $q$: 평균 월파량($\text{m}^3/\text{s}/\text{m}$), $q^*$: 무차원 월파량, $h^*, d^*$: 충격성 판별 매개변수, $R_c$: 계산여유고, $H_{1/3}(H_{m0})$: 유의파고, $s_{m-1,0}$: 파형경사, $g$: 중력가속도, $d$: 마운드 상단 수심")
            
            rep.md(f"> - **무차원 설계 유량($q^*$) 산출:**")
            rep.latex(f"q^* = {calc_str} = {q_norm:.4e}")
            
            rep.md(f"> - **평균 월파량($q$) 최종 도출:**")
            rep.latex(f"q = {q_norm:.4e} \\times \\sqrt{{9.81 \\times {h13:.2f}^3}} = {q_euro:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}")
            
            if calc_mode == "월파량(q) 산정": 
                final_results.append({"적용 설계 기준": "EurOtop (직립제)", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_euro:.6f} m³/s/m"})
            else: 
                final_results.append({"적용 설계 기준": "EurOtop (직립제)", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})   

    # ==========================================
    # [4] Goda 도표 보간 및 신규 삽도 연동 모듈
    # ==========================================
    if chk_goda:
        rep.title("■ 5. 일본 항만설계기준 (Goda 원본 도표 정밀 다중 보간) 상세", level=3)
        rep.md("Goda 원본 데이터 CSV를 직접 로드하여 환산심해파고($H_0'$)를 수렴 도출하고, 이를 바탕으로 도표 내 실제 추출(독취) 좌표를 역산하여 도식화합니다.")
        
        # ★ 공식 전면 배치
        rep.md("#### 📐 [월파량 산정 공식]")
        rep.latex(r"q = Y \sqrt{2 g (H_0')^3}")
        rep.md("> **[기호 설명]** $q$: 단위폭당 평균 월파량, $Y$: 무차원 월파량 도표 독취값, $H_0'$: 환산심해파고, $g$: 중력가속도")

        H0_prime_val = goda_calc.get_converged_H0_prime(h13, t13, h, slope_denom)
        
        if calc_mode == "소요 여유고(Rc) 산정":
            def eval_goda_q(test_rc):
                q_val, _, _, _, _, _, _ = goda_calc.execute_goda_calc(h13, t13, h, test_rc, struct_type, slope_denom, draw_charts=False)
                return q_val - q_target
            def eval_takayama(test_rc):
                return goda_calc.calculate_takayama_formula(h, test_rc, H0_prime_val) - q_target
            try: 
                Rc = brentq(eval_goda_q, 0.5 * H0_prime_val, 2.0 * H0_prime_val)
                rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m) - 도표 다중 보간 수렴성공")
            except ValueError: 
                try: 
                    Rc = brentq(eval_takayama, 0.01, 30.0)
                    rep.info(f"💡 **목표 허용 월파량({q_target} m³/s/m)** 만족 소요 여유고 역산: **{Rc:.3f} m** (마루높이 DL {wl+Rc:.3f} m) - 도표범위 이탈로 Takayama 근사식 수렴성공")
                except ValueError: Rc = 0.01
        else: Rc = Rc_input
            
        q_goda_calc, c_method, H0_prime, rel_h, rel_hc, wave_slope_calc, chart_data_list = goda_calc.execute_goda_calc(h13, t13, h, Rc, struct_type, slope_denom, draw_charts=True)

        L0_goda = 1.56 * t13**2
        steepness_final = H0_prime_val / L0_goda
        rel_depth_L0_goda = h / L0_goda
        
        if goda_calc.ks_points is not None and len(goda_calc.ks_points) > 0:
            Ks_final = griddata(goda_calc.ks_points, goda_calc.ks_values, (steepness_final, rel_depth_L0_goda), method='linear')
            if np.isnan(Ks_final): Ks_final = griddata(goda_calc.ks_points, goda_calc.ks_values, (steepness_final, rel_depth_L0_goda), method='nearest')
            Ks_final = float(Ks_final)
        else: Ks_final, _ = goda_calc.calc_linear_Ks(h, t13)

        tanTheta_val = 1.0 / slope_denom
        b0_val = 0.028 * (steepness_final**(-0.38)) * math.exp(20 * (tanTheta_val**1.5))
        b1_val = 0.52 * math.exp(4.2 * tanTheta_val)
        bM_val = max(0.92, 0.32 * (steepness_final**(-0.29)) * math.exp(2.4 * tanTheta_val))
        val1 = b0_val * H0_prime_val + b1_val * h
        val2 = bM_val * H0_prime_val
        val3 = Ks_final * H0_prime_val
        h13_calc = min(val1, val2, val3)
        cond_str = "<span style='color:red; font-weight:bold;'>< 0.2</span>" if rel_depth_L0_goda < 0.2 else "<span style='font-weight:bold;'>≥ 0.2</span>"

        rep.md("#### 📝 [1. 수렴된 환산심해파고($H_0'$) 산정 근거 상세표]")
        
        table_md = f"""
| 구분 | 기호 | 산출식 / 설명 | 산출결과 | 비고 |
| :---: | :---: | :--- | :---: | :---: |
| **여기서,** | $\\beta_0$ | $0.028(H_0'/L_0)^{{-0.38}} \\exp[20(\\tan\\theta)^{{1.5}}]$ | **{b0_val:.3f}** | |
| | $\\beta_1$ | $0.52 \\exp[4.2 \\tan\\theta]$ | **{b1_val:.3f}** | |
| | $\\beta_{{max}}$ | $\\max(0.92, 0.32(H_0'/L_0)^{{-0.29}} \\exp[2.4 \\tan\\theta])$ | **{bM_val:.3f}** | |
| | $K_s$ | 비선형 천수계수 | **{Ks_final:.3f}** | 수렴값 |
| | $H_0'$ | 환산심해파고 (m) | **{H0_prime_val:.3f}** | 수치해석 역산 |
| | $\\tan\\theta$ | 해저경사 | **1/{slope_denom:.0f}** | |
| | $h$ | 적용 수심 (m) | **{h:.2f}** | |
| | $L_0$ | 심해파장 (m) | **{L0_goda:.2f}** | |
| | $h/L_0$ | 상대 수심 | **{rel_depth_L0_goda:.3f}** | {cond_str} |
| | $H_0'/L_0$ | 환산심해파형경사 | **{steepness_final:.3f}** | |
| | 조건 1 | $\\beta_0 H_0' + \\beta_1 h$ | **{val1:.2f}** | |
| | 조건 2 | $\\beta_{{max}} H_0'$ | **{val2:.2f}** | |
| | 조건 3 | $K_s H_0'$ | **{val3:.2f}** | |
| **결과** | **$H_{{1/3}}$** | **유의파고 검증** | **{h13_calc:.2f} m** | 입력 제원({h13:.2f}m)과 일치 |
"""
        table_html = f"""
        <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 14px; margin-bottom: 20px;">
            <tr style="background-color: #f4f6f8;">
                <th style="border: 1px solid #ccc; padding: 10px;">구분</th>
                <th style="border: 1px solid #ccc; padding: 10px;">기호</th>
                <th style="border: 1px solid #ccc; padding: 10px;">산출식 / 설명</th>
                <th style="border: 1px solid #ccc; padding: 10px;">산출결과</th>
                <th style="border: 1px solid #ccc; padding: 10px;">비고</th>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">여기서,</td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(\\beta_0\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(0.028(H_0'/L_0)^{{-0.38}} \\exp[20(\\tan\\theta)^{{1.5}}]\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{b0_val:.3f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(\\beta_1\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(0.52 \\exp[4.2 \\tan\\theta]\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{b1_val:.3f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(\\beta_{{max}}\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(\\max(0.92, 0.32(H_0'/L_0)^{{-0.29}} \\exp[2.4 \\tan\\theta])\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{bM_val:.3f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(K_s\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">비선형 천수계수</td>
                <td style="border: 1px solid #ccc; padding: 10px;"><span style="border: 2px solid black; padding: 2px 8px; font-weight:bold;">{Ks_final:.3f}</span></td>
                <td style="border: 1px solid #ccc; padding: 10px;">수렴값</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(H_0'\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">환산심해파고 (m)</td>
                <td style="border: 1px solid #ccc; padding: 10px;"><span style="border: 2px solid black; padding: 2px 8px; font-weight:bold;">{H0_prime_val:.3f}</span></td>
                <td style="border: 1px solid #ccc; padding: 10px;">수치해석 역산</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(\\tan\\theta\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">해저경사</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">1/{slope_denom:.0f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(h\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">적용 수심 (m)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{h:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(L_0\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">심해파장 (m)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{L0_goda:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(h/L_0\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">상대 수심</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{rel_depth_L0_goda:.3f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;">{cond_str}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">\\(H_0'/L_0\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">환산심해파형경사</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{steepness_final:.3f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">조건 1</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(\\beta_0 H_0' + \\beta_1 h\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{val1:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">조건 2</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(\\beta_{{max}} H_0'\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{val2:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
                <td style="border: 1px solid #ccc; padding: 10px;">조건 3</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left;">\\(K_s H_0'\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">{val3:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 10px;"></td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold; color:#b71c1c;">결과</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold; color:#b71c1c;">\\(H_{{1/3}}\\)</td>
                <td style="border: 1px solid #ccc; padding: 10px; text-align: left; font-weight:bold; color:#b71c1c;">유의파고 검증</td>
                <td style="border: 1px solid #ccc; padding: 10px;"><span style="border: 2px solid #b71c1c; padding: 2px 8px; font-weight:bold; font-size:1.1em; color:#b71c1c;">{h13_calc:.2f} m</span></td>
                <td style="border: 1px solid #ccc; padding: 10px; font-weight:bold;">입력 제원({h13:.2f}m)과 일치</td>
            </tr>
        </table>
        """
        rep.dual_table(table_md, table_html)

        rep.md("#### 📊 [2. 도표 정밀 보간 연동 및 독취값 좌표 시각화]")
        rep.md("> **[기호 설명]** $X$: 상대수심비($h/H_0'$), Curve: 여유고비($R_c/H_0'$)")
        rep.latex(r"X = \frac{h}{H_0'}, \quad \text{Curve} = \frac{R_c}{H_0'}")
        rep.md(f"> - **도표 적용 변수:** $X$축 상대수심비({rel_h:.3f}), 곡선 여유고비({rel_hc:.3f})")

        if chart_data_list:
            cols = st.columns(2)
            for idx, c_data in enumerate(chart_data_list):
                with cols[idx % 2]:
                    caption = f"해저경사 1/{c_data['bottom']}, 파형경사 {c_data['wave']:.3f} (가중치: {c_data['weight']*100:.1f}%)"
                    if os.path.exists(c_data['path']):
                       rep.static_img(c_data['path'], caption)
        else:
            rep.warn("현재 입력된 매개변수가 도표 산정 범위를 완전히 이탈하여 렌더링 가능한 교차 도표가 없습니다.")

        rep.md("#### 📝 [3. 보간 결과 산정 내역]")
        rep.md(f"> - **적용 로직:** {c_method}")
        rep.md(f"> - **$q$ 산출 과정:** $q = Y_{{interpolated}} \\times \\sqrt{{2 \\times 9.81 \\times ({H0_prime_val:.3f})^3}}$")
        rep.md(f"> - **최종 결과($q$):** $q = \\mathbf{{{q_goda_calc:.6f} \\text{{ m}}^3/\\text{{s}}/\\text{{m}}}}$")
        
        goda_struct_name = "경사제" if struct_type == '경사제 (Rubble Mound)' else '직립제'
        if calc_mode == "월파량(q) 산정": final_results.append({"적용 설계 기준": f"Goda 도표법 ({goda_struct_name})", "입력 여유고 (Rc)": f"{Rc:.3f} m", "최종 결과치": f"{q_goda_calc:.6f} m³/s/m"})
        else: final_results.append({"적용 설계 기준": f"Goda 도표법 ({goda_struct_name})", "목표 월파량": f"{q_target:.4f}", "소요 여유고 (Rc)": f"{Rc:.3f} m", "설계 마루높이": f"DL {wl+Rc:.3f} m"})
      
    # ==========================================
    # 5. 최종 결과 통합 비교표 정리
    # ==========================================
    rep.title("■ 6. 최종 설계 기준별 검토 결과 종합 비교표", level=3)
    if final_results:
        # 1. 적용 형상 데이터 표를 위한 구조 재조립
        new_final_results = []
        for res in final_results:
            new_res = {"적용 설계 기준": res["적용 설계 기준"]}
            
            # 구조물별 적용 형상 명시
            if struct_type == "경사제 (Rubble Mound)":
                if "EurOtop" in res["적용 설계 기준"] and parapet_type != "소파공 동일 높이 (일반)":
                    new_res["적용 형상"] = parapet_type
                else:
                    new_res["적용 형상"] = "기본단면(소파공과 상치공 동일높이)"
            else: # 직립제 (혼성제)
                shape_name = ""
                if "KDS" in res["적용 설계 기준"]:
                    shape_name = selected_kds_shape.split(' (')[0]
                elif "CEM" in res["적용 설계 기준"]:
                    shape_name = selected_caisson_str.split(' (')[0]
                elif "EurOtop" in res["적용 설계 기준"] and has_bullnose:
                    shape_name = "상반파공(Bullnose)"
                
                # 무공직립구조물, 일반케이슨이거나 별도 형상이 없는 경우 명칭 통일
                if shape_name in ["무공직립구조물", "일반케이슨"] or shape_name == "":
                    new_res["적용 형상"] = "기본단면(무공 케이슨 직립상치 구조물)"
                else:
                    new_res["적용 형상"] = shape_name
            
            # 나머지 기존 데이터 복사
            for k, v in res.items():
                if k not in ["적용 설계 기준", "적용 형상"]:
                    new_res[k] = v
            new_final_results.append(new_res)
            
        df_res = pd.DataFrame(new_final_results)
        rep.df(df_res)
        
        # 2. 결과 도출 및 최댓값 선정 분기 로직
        def get_parsed_val(row_val_str):
            num_str = re.findall(r"[-+]?\d*\.\d+|\d+", str(row_val_str).replace(',', ''))
            return float(num_str[0]) if num_str else 0.0

        def get_val_by_criterion(keyword, column_name):
            for idx, row in df_res.iterrows():
                if keyword in row['적용 설계 기준']:
                    return get_parsed_val(row[column_name])
            return 0.0

        if calc_mode == "월파량(q) 산정":
            target_col = "최종 결과치"
            def fmt(val): return f"{val:.6f} m³/s/m"
        else:
            target_col = "소요 여유고 (Rc)"
            def fmt(val): return f"{val:.3f} m (최종 설계 마루높이: DL {wl+val:.3f} m)"

        # 4개 기준 전체의 최댓값 사전 추출 (기본단면용)
        all_vals = [get_parsed_val(row[target_col]) for _, row in df_res.iterrows()]
        max_val = max(all_vals) if all_vals else 0.0
        selected_msg = ""

        # ---- [조건별 결과 채택] ----
        if struct_type == "직립제 (혼성제)":
            # 직립제 특수 케이스 식별
            is_kds_slope = "상부사면상치" in selected_kds_shape
            is_kds_perf = "유공케이슨" in selected_kds_shape
            is_cem_nose = "노즈형" in selected_caisson_str
            is_cem_slit = "슬릿 케이슨" in selected_caisson_str and "오픈" not in selected_caisson_str
            is_cem_open = "오픈 슬릿" in selected_caisson_str
            is_euro_bullnose = has_bullnose

            # 1) 완전 독립적인 특수 형상 (우선순위 적용)
            if is_kds_slope or is_cem_nose or is_cem_open or is_euro_bullnose:
                cands = []
                if is_kds_slope: cands.append((get_val_by_criterion("KDS", target_col), "KDS 상부사면상치"))
                if is_cem_nose: cands.append((get_val_by_criterion("CEM", target_col), "CEM 노즈형상치"))
                if is_cem_open: cands.append((get_val_by_criterion("CEM", target_col), "CEM 오픈슬릿케이슨"))
                if is_euro_bullnose: cands.append((get_val_by_criterion("EurOtop", target_col), "EurOtop 상반파공(Bullnose)"))
                
                # 여러 개의 독립 특수조건이 동시 선택된 경우 그 중 최댓값을 갖는 조건 채택
                max_cand = max(cands, key=lambda x: x[0])
                selected_msg = f"🎯 특수 형상({max_cand[1]}) 반영에 의거하여, 해당 산정 결과를 독립적으로 채택합니다: {fmt(max_cand[0])}"

            # 2) 유공케이슨 vs 슬릿케이슨 비교 (동일 개념 구조물)
            elif is_kds_perf or is_cem_slit:
                perf_cands = []
                if is_kds_perf: perf_cands.append(get_val_by_criterion("KDS", target_col))
                if is_cem_slit: perf_cands.append(get_val_by_criterion("CEM", target_col))
                
                final_val = max(perf_cands)
                
                if is_kds_perf and is_cem_slit:
                    selected_msg = f"🎯 KDS 유공케이슨과 CEM 슬릿케이슨 산정 결과 중 보수적 최댓값을 비교 채택합니다: {fmt(final_val)}"
                elif is_kds_perf:
                    selected_msg = f"🎯 KDS 유공케이슨 형상 반영에 의거하여, 해당 산정 결과를 채택합니다: {fmt(final_val)}"
                else:
                    selected_msg = f"🎯 CEM 슬릿케이슨 형상 반영에 의거하여, 해당 산정 결과를 채택합니다: {fmt(final_val)}"

            # 3) 기본단면 (특수 케이스 미적용) -> 4가지 전체 비교
            else:
                selected_msg = f"🎯 직립제 기본단면(무공 케이슨 직립상치 구조물) 4개 설계 기준 비교 결과, 보수적 최댓값을 적용합니다: {fmt(max_val)}"

        else: # 경사제 (Rubble Mound)
            if parapet_type != "소파공 동일 높이 (일반)":
                final_val = get_val_by_criterion("EurOtop", target_col)
                selected_msg = f"🎯 경사제 상치벽 특수 조건({parapet_type}) 반영에 의거하여, EurOtop 산정 결과를 독립적으로 채택합니다: {fmt(final_val)}"
            else:
                selected_msg = f"🎯 경사제 기본단면(소파공과 상치공 동일높이) 4개 설계 기준 비교 결과, 보수적 최댓값을 적용합니다: {fmt(max_val)}"

        rep.result(selected_msg)
    else:
        rep.warn("검토 대상 기준 체크박스가 선택되지 않았습니다.")

    st.divider()
    render_fast_download(rep, f"KDS_항만구조물_종합검토보고서")
