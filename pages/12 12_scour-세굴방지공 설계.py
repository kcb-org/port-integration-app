import streamlit as st
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from PIL import Image, ImageEnhance
import os
import urllib.request
import io
import base64
import re
import matplotlib.font_manager as fm

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

# =====================================================================
# ★ 한글 폰트 깨짐 방지
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
# ★ 보고서 생성기 (수식 깨짐 완벽 방지 + 마크다운 렌더러 탑재)
# =====================================================================
class ReportBuilder:
    def __init__(self):
        self.html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>세굴방지공 단면제원 계산 보고서</title>
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
            h2 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 40px;}
            h3 { color: #2c3e50; margin-top: 25px; }
            h4 { color: #34495e; font-weight: bold; margin-top: 20px;}
            .eq { background: #f8f9fa; padding: 15px; border-left: 4px solid #1a73e8; margin: 15px 0; overflow-x: auto; font-size: 1.1em;}
            .figure { text-align: center; margin: 20px 0; }
            p { margin: 8px 0; }
            ul { margin-top: 5px; margin-bottom: 15px; padding-left: 20px; }
            li { margin-bottom: 8px; }
            .info-box { background-color: #e8f0fe; border-left: 4px solid #1a73e8; padding: 15px; margin: 15px 0; }
            .success-box { background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; color: #155724; }
            .error-box { background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; color: #721c24; }
            .warning-box { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; color: #856404; }
            .metric-container { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; }
            .metric-box { flex: 1; min-width: 150px; padding: 15px; background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        </style>
        </head><body class="tex2jax_process">
        <h1 style='text-align:center;'>🌊 항외측 세굴방지공 단면제원 자동 산정 보고서</h1><hr>
        """
    
    def _fmt(self, text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', str(text))
        return text.replace('\n', '<br>')

    def title(self, text, level=2):
        st.markdown(f"{'#' * level} {text}")
        self.html += f"<h{level}>{text}</h{level}>"

    def md(self, text):
        st.markdown(text)
        html_out = ""
        in_list = False
        for line in text.split('\n'):
            if not line.strip(): continue
            content = line.strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            
            if content.startswith('* '):
                if not in_list:
                    html_out += "<ul>\n"
                    in_list = True
                html_out += f"<li>{content[2:]}</li>\n"
            else:
                if in_list:
                    html_out += "</ul>\n"
                    in_list = False
                if content.startswith('> '):
                    html_out += f"<blockquote style='border-left: 3px solid #ccc; margin-left: 10px; padding-left: 10px; color: #555;'>{content[2:]}</blockquote>\n"
                else:
                    html_out += f"<p>{content}</p>\n"
                    
        if in_list: html_out += "</ul>\n"
        self.html += html_out

    def info(self, text):
        st.info(text)
        self.html += f"<div class='info-box'>{self._fmt(text)}</div>"

    def success(self, text):
        st.success(text)
        self.html += f"<div class='success-box'>{self._fmt(text)}</div>"

    def error(self, text):
        st.error(text)
        self.html += f"<div class='error-box'>{self._fmt(text)}</div>"

    def warning(self, text):
        st.warning(text)
        self.html += f"<div class='warning-box'>{self._fmt(text)}</div>"

    def latex(self, eq):
        st.latex(eq)
        self.html += f"<div class='eq'>$$ {eq} $$</div>"

    def table(self, dataframe):
        st.table(dataframe)
        self.html += dataframe.to_html(index=False, justify='center', escape=False)

    def metric(self, label, value):
        st.metric(label, value)
        self.html += f"<div class='metric-box'><b>{label}</b><br><span style='font-size:1.4em; color:#1a73e8; font-weight:bold;'>{value}</span></div>"

    def fig(self, figure):
        st.pyplot(figure)
        buf = io.BytesIO()
        figure.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        self.html += f"<div class='figure'><img src='data:image/png;base64,{encoded}' style='max-width:800px; width:100%; height:auto;'></div>"

    def image_pil(self, img_obj, caption=""):
        st.image(img_obj, use_container_width=True)
        buf = io.BytesIO()
        img_obj.save(buf, format='PNG')
        encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
        self.html += f"<div class='figure'><img src='data:image/png;base64,{encoded}' style='max-width:800px; width:100%; height:auto;'><p><b>{caption}</b></p></div>"

    def get_html(self):
        return self.html + "</body></html>"


# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="세굴방지공 단면제원 계산", layout="wide", page_icon="🌊")

# --- [안전 함수] 3제곱근 계산 (복소수 에러 방지) ---
def safe_cbrt(x):
    return np.sign(x) * (abs(x)**(1.0/3.0))

# --- [함수] 항만설계기준 분산관계식 시산법 파장(L) 산출 ---
def calc_wave_length(T, h):
    T = max(abs(T), 0.1) # 0초 이하 방지
    h = max(abs(h), 0.1) # 0m 이하 방지
    g = 9.81
    L0 = (g * (T**2)) / (2 * math.pi)
    L_curr = L0
    for _ in range(100):
        L_new = L0 * math.tanh(2 * math.pi * h / L_curr)
        if abs(L_new - L_curr) < 0.0001:
            break
        L_curr = L_new
    return max(L_curr, 0.001)

st.title("🌊 항외측 세굴방지공 단면제원 자동 계산")
st.markdown("### 산정 결과값(-) 표시 및 직립제/경사제 로직 완벽 분리")

# ★ 여기서부터 보고서 기록 객체 초기화
rep = ReportBuilder()

# ==========================================
# ★ 전체결과 요약표가 들어갈 자리 확보 (st.empty)
# ==========================================
summary_placeholder = st.empty()

# ==========================================
# 2. 입력부 (사이드바)
# ==========================================
st.sidebar.header("설계파랑 및 지반 제원 입력")
raw_H = st.sidebar.number_input("유의파고 H_s (m)", value=4.10, format="%.2f")
raw_T = st.sidebar.number_input("유의주기 T_s (sec)", value=10.83, format="%.2f")
raw_h = st.sidebar.number_input("현재 설계수심 h (m)", value=22.51, format="%.2f")
ds_input = st.sidebar.number_input("저질 평균입경 d_s (m)", value=0.00006, format="%.6f")

# 🌟 에러 방지: 사용자가 음수를 넣어도 계산은 절대값(양수)으로 처리하도록 보정
H_input = max(abs(raw_H), 0.01)
T_input = max(abs(raw_T), 0.1)
h_bed = max(abs(raw_h), 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("구조물 및 보호공 조건")

structure_type = st.sidebar.radio("구조물 형식", ["직립제 (Vertical)", "경사제 (Rubble Mound)"])
location_type = st.sidebar.radio("적용 구간 (C.E.M 세굴심 산정용)", ["제두부 (Head)", "제간부 (Trunk)"])

Cu_input = 1.0 # 변수 초기화
if structure_type == "직립제 (Vertical)":
    if location_type == "제두부 (Head)":
        head_shape = st.sidebar.radio("제두부 형상", ["사각형 (Square)", "원형 (Circular)"])
        wave_condition = "비쇄파 규칙파 (Sumer & Fredsoe)"
    else:
        head_shape = "N/A"
        wave_condition = st.sidebar.radio("파랑 조건", ["비쇄파 규칙파 (Xie)", "비쇄파 불규칙파 (Hughes & Fowler)"])
else: # 경사제일 경우
    head_shape = "N/A"
    wave_condition = "N/A"
    st.sidebar.markdown("---")
    st.sidebar.subheader("경험계수 입력 (경사제)")
    Cu_input = st.sidebar.number_input("경험계수 C_u (표 참조)", value=1.00, step=0.1, format="%.2f")

protection_type = st.sidebar.radio("보호공 형식", ["매설형 (Buried Type)", "사석마운드형 (Berm Type)"])
r_stone = st.sidebar.number_input("피복재 공칭직경 r (d_n50, m)", value=1.5, step=0.1)
B_width = st.sidebar.number_input("구조물 폭 또는 직경 B (m)", value=15.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("수립자/조류속 및 Isbash 공식 제원")
gamma_r = st.sidebar.number_input("사석 단위중량 gamma_r (kN/m^3)", value=26.0, step=0.1)
gamma_w = st.sidebar.number_input("해수 단위중량 gamma_w (kN/m^3)", value=10.10, step=0.01)
isbash_y = st.sidebar.number_input("Isbash 계수 y (매설: 0.86 / 돌출: 1.2)", value=0.86, step=0.01)
theta_angle = st.sidebar.number_input("사면경사 theta (도)", value=33.69, step=0.01)
z_depth = st.sidebar.number_input("속도 산정 수심 z (m, 해수면=0)", value=-5.0, step=0.1)
v_tidal = st.sidebar.number_input("설계 조류속 V_c (m/s)", value=1.50, step=0.1)

# ==========================================
# 3. 기본 수리 제원 선계산
# ==========================================
g_val = 9.81
L0_val = (g_val * (T_input**2)) / (2 * math.pi)
L_init = calc_wave_length(T_input, h_bed)

kh_init = 2 * math.pi * h_bed / L_init
sinh_kh = math.sinh(kh_init) if math.sinh(kh_init) != 0 else 0.001
tanh_kh = math.tanh(kh_init) if math.tanh(kh_init) != 0 else 0.001

n_val = 0.5 * (1 + (2 * kh_init) / sinh_kh)
Ks_val = math.sqrt(abs(1 / (tanh_kh * 2 * n_val)))
H0_prime = H_input / Ks_val

u_bottom = (math.pi * H_input) / (T_input * sinh_kh)
term_z = 2 * math.pi * (z_depth + h_bed) / L_init
u_z = (math.pi * H_input / T_input) * (math.cosh(term_z) / sinh_kh)

# ==========================================
# 4. 1. 원지반 세굴여부 판정
# ==========================================
rep.title("1. 원지반 세굴여부 판정", level=2)

rep.title("가. 환산심해파고($H_0'$) 산정 과정", level=3)
col_a1, col_a2 = st.columns(2)
with col_a1:
    rep.latex(rf"L_0 = \frac{{g T_s^2}}{{2\pi}} = {L0_val:.2f} \, m")
    rep.latex(rf"L = L_0 \tanh(2\pi h / L) \approx {L_init:.2f} \, m")
with col_a2:
    rep.latex(rf"K_s = \sqrt{{1 / (\tanh kh \cdot 2n)}} \approx {Ks_val:.4f}")
    rep.latex(rf"H_0' = H_s / K_s = {H0_prime:.2f} \, m")

rep.title("나. 이동한계 수심($h_i$) 산정 상세과정", level=3)

def run_sato_tanaka_details(alpha):
    h_curr = 15.0 
    rows = []
    for i in range(1, 11):
        L = calc_wave_length(T_input, h_curr)
        constant = alpha * ((ds_input / L0_val)**(1/3))
        term = (H0_prime / L0_val) / constant * (H_input / H0_prime)
        h_next = L * math.asinh(term) / (2 * math.pi)
        
        diff = abs(h_curr - h_next)
        rows.append({
            "회차": i,
            "가정수심(m)": round(h_curr, 3),
            "파장(m)": round(L, 3),
            "산정수심(m)": round(h_next, 3),
            "오차": round(diff, 5)
        })
        if diff < 0.001: break
        h_curr = h_next
    return h_curr, pd.DataFrame(rows)

h_surf, df_surf = run_sato_tanaka_details(1.35)
h_full, df_full = run_sato_tanaka_details(2.40)

tab1, tab2 = st.tabs(["표층 이동한계 (α=1.35)", "완전 이동한계 (α=2.40)"])
with tab1:
    rep.html += "<h4>■ 표층 이동한계 (α=1.35)</h4>"
    rep.table(df_surf)
    rep.success(f"최종 표층이동 한계수심 ($h_s$): **{h_surf:.2f} m**")
with tab2:
    rep.html += "<h4>■ 완전 이동한계 (α=2.40)</h4>"
    rep.table(df_full)
    rep.success(f"최종 완전이동 한계수심 ($h_c$): **{h_full:.2f} m**")

rep.title("다. 원지반 세굴 여부 최종 판정", level=3)

rep.html += "<div class='metric-container'>"
col_h1, col_h2, col_h3 = st.columns(3)
with col_h1: rep.metric("현재 설계수심 ($h$)", f"{h_bed:.2f} m")
with col_h2: rep.metric("표층이동 한계수심 ($h_s$)", f"{h_surf:.2f} m")
with col_h3: rep.metric("완전이동 한계수심 ($h_c$)", f"{h_full:.2f} m")
rep.html += "</div>"

rep.title("[판정 결과]", level=4)
if h_bed <= h_surf:
    rep.latex(rf"h \, ({h_bed:.2f} \, \text{{m}}) \le h_s \, ({h_surf:.2f} \, \text{{m}})")
    rep.error("🚨 **세굴방지공 설치 필요** (현재 수심이 표층이동 한계수심보다 얕거나 같습니다.)")
    scour_status = "필요"
else:
    rep.latex(rf"h \, ({h_bed:.2f} \, \text{{m}}) > h_s \, ({h_surf:.2f} \, \text{{m}})")
    rep.success("✅ **원지반 안정 / 보강 불필요** (현재 수심이 표층이동 한계수심보다 깊어 세굴이 발생하지 않습니다.)")
    scour_status = "불필요"

# ==========================================
# 5. 2. 세굴방지공 계획
# ==========================================
st.markdown("---")
rep.html += "<hr>"
rep.title("2. 세굴방지공 계획", level=2)

# 변수 초기화
Sm_val = 0.0 
d_final = 0.0
W_final_ton = 0.0
B_sp = 0.0
thickness = 0.0
control_factor = "-"

if scour_status == "필요":
    rep.title("가. 세굴방지공 규격검토 (Isbash 공식 적용)", level=3)
    
    S_r = gamma_r / gamma_w
    if S_r <= 1.0: S_r = 1.01 
    
    theta_rad = math.radians(theta_angle)
    cos_sin = math.cos(theta_rad) - math.sin(theta_rad)
    if cos_sin <= 0.01: cos_sin = 0.01 
    
    denom_W = 48 * (g_val**3) * (isbash_y**6) * ((S_r - 1.0)**3) * (cos_sin**3)
    
    rep.title("1) 파랑에 의한 규격 검토", level=4)
    rep.md(f"**가) 파랑에 의한 수립자 속도($U_z$) 산정** (수심 z = {z_depth:.2f}m)")
    rep.latex(rf"U_z = \frac{{\pi H}}{{T}} \frac{{\cosh[2\pi(z+h)/L]}}{{\sinh(2\pi h/L)}}")
    rep.latex(rf"U_z = \frac{{\pi \times {H_input:.2f}}}{{{T_input:.2f}}} \times \frac{{\cosh[2\pi({z_depth:.2f} + {h_bed:.2f})/{L_init:.2f}]}}{{\sinh(2\pi \times {h_bed:.2f} / {L_init:.2f})}} = {u_z:.4f} \, m/s")
    
    W_wave_kN = (math.pi * gamma_r * (u_z**6)) / denom_W
    W_wave_ton = W_wave_kN / g_val
    V_wave_m3 = W_wave_kN / gamma_r
    d_wave = safe_cbrt((6.0 * W_wave_kN) / (math.pi * gamma_r))
    
    rep.md("**나) 피복석 소요 중량($W$) 및 규격($d$) 산정**")
    rep.latex(rf"S_r = \frac{{\gamma_r}}{{\gamma_w}} = \frac{{{gamma_r:.3f}}}{{{gamma_w:.3f}}} = {S_r:.4f}")
    rep.latex(r"W = \frac{\pi \gamma_r U_z^6}{48 g^3 y^6 (S_r - 1)^3 (\cos\theta - \sin\theta)^3}")
    rep.latex(rf"W = \frac{{\pi \times {gamma_r:.2f} \times ({u_z:.4f})^6}}{{48 \times ({g_val})^3 \times ({isbash_y})^6 \times ({S_r:.4f} - 1)^3 \times (\cos{theta_angle}^\circ - \sin{theta_angle}^\circ)^3}} = {W_wave_kN:.4f} \, kN")
    rep.latex(rf"d = \left( \frac{{6W}}{{\pi \gamma_r}} \right)^{{1/3}} = \left( \frac{{6 \times {W_wave_kN:.4f}}}{{\pi \times {gamma_r:.2f}}} \right)^{{1/3}} = {d_wave:.3f} \, m")
    
    rep.title("2) 조류에 의한 규격 검토", level=4)
    rep.md("**가) 설계 조류속($V_c$) 적용**")
    rep.latex(rf"V_c = {v_tidal:.2f} \, m/s \quad \text{{(설계 적용 조류속)}}")
    
    W_current_kN = (math.pi * gamma_r * (v_tidal**6)) / denom_W
    W_current_ton = W_current_kN / g_val
    V_current_m3 = W_current_kN / gamma_r
    d_current = safe_cbrt((6.0 * W_current_kN) / (math.pi * gamma_r))
    
    rep.md("**나) 피복석 소요 중량($W$) 및 규격($d$) 산정**")
    rep.latex(r"W = \frac{\pi \gamma_r V_c^6}{48 g^3 y^6 (S_r - 1)^3 (\cos\theta - \sin\theta)^3}")
    rep.latex(rf"W = \frac{{\pi \times {gamma_r:.2f} \times ({v_tidal:.2f})^6}}{{48 \times ({g_val})^3 \times ({isbash_y})^6 \times ({S_r:.4f} - 1)^3 \times (\cos{theta_angle}^\circ - \sin{theta_angle}^\circ)^3}} = {W_current_kN:.4f} \, kN")
    rep.latex(rf"d = \left( \frac{{6W}}{{\pi \gamma_r}} \right)^{{1/3}} = \left( \frac{{6 \times {W_current_kN:.4f}}}{{\pi \times {gamma_r:.2f}}} \right)^{{1/3}} = {d_current:.3f} \, m")
    
    rep.title("3) 최종 규격 결정 (파랑 vs 조류 비교)", level=4)
    
    comp_data = {
        "구분": ["파랑 (Wave)", "조류 (Tidal Current)"],
        "적용 유속 (m/s)": [f"{u_z:.4f}", f"{v_tidal:.2f}"],
        "소요 직경 d (m)": [f"{d_wave:.3f}", f"{d_current:.3f}"],
        "소요 중량 W (kN)": [f"{W_wave_kN:.3f}", f"{W_current_kN:.3f}"],
        "소요 중량 W (ton)": [f"{W_wave_ton:.3f}", f"{W_current_ton:.3f}"],
        "소요 부피 V (m³(루베))": [f"{V_wave_m3:.3f}", f"{V_current_m3:.3f}"]
    }
    df_comp = pd.DataFrame(comp_data).set_index("구분")
    rep.table(df_comp)
    
    d_final = max(d_wave, d_current)
    W_final_kN = max(W_wave_kN, W_current_kN)
    W_final_ton = max(W_wave_ton, W_current_ton)
    V_final_m3 = max(V_wave_m3, V_current_m3)
    control_factor = "파랑 (Wave)" if d_wave >= d_current else "조류 (Tidal Current)"
    
    rep.info(f"**💡 결정 지배 요소:** {control_factor}\n\n**최종 필요 소요 직경 (d):** {d_final:.3f} m  /  **최종 필요 소요 중량 (W):** {W_final_kN:.3f} kN ({W_final_ton:.3f} ton, **{V_final_m3:.3f} m³**)\n\n*(설계 적용 피복재 공칭직경 r = {r_stone:.2f} m)*")

    rep.title("나. 세굴심도($S_m$) 산정 상세", level=3)
    
    if structure_type == "직립제 (Vertical)":
        if location_type == "제두부 (Head)":
            # =====================================================================
            # 💡 [상세설명 추가] 직립제 제두부
            # =====================================================================
            with st.expander("💡 [상세 설명] 직립제 제두부 세굴심도 공식 및 주요 기호", expanded=False):
                rep.md("""
                **1. Keulegan-Carpenter 수 ($KC$)**
                * **정의:** 파랑에 의한 물입자의 최대 이동 거리와 구조물 폭($B$)의 비율을 나타내는 무차원 수입니다.
                * **물리적 의미:** 제두부 주변에서 **말굽형 와류(Horseshoe Vortex)**와 **후류 와류(Wake Vortex)**가 얼마나 강하게 발달하는지 결정하는 핵심 지표입니다. $KC$ 값이 클수록 와류가 강해져 세굴이 깊어집니다.
                * $u_{bottom}$ (m/s): 수평 바닥 최대 유속. 파랑 에너지가 해저면에 도달하여 모래 입자를 움직이는 왕복성 유속의 진폭입니다.
                * $T_s$ (sec): 유의주기. 파랑이 한 번 왕복하는 데 걸리는 시간입니다.
                * $B$ (m): 구조물의 폭 또는 직경. (폭이 좁을수록 유체가 구조물을 타고 넘으면서 와류가 쉽게 분리되어 $KC$가 커집니다.)

                **2. 제두부 형상에 따른 계수 적용**
                * 사각형(Square) 단면이 원형(Circular) 단면보다 유체의 흐름을 더 급격하게 분리(Flow Separation)시키므로, 와류가 더 강하게 발생합니다. 따라서 사각형 단면일 때 세굴심도가 더 깊게 산정되도록 서로 다른 수식을 적용합니다.
                """)
                
            KC = (u_bottom * T_input) / B_width
            
            rep.title("1) Keulegan-Carpenter 수 (KC) 산정", level=4)
            rep.latex(rf"KC = \frac{{u_{{bottom}} T_s}}{{B}} = \frac{{{u_bottom:.3f} \times {T_input:.2f}}}{{{B_width}}} = {KC:.3f}")
            
            rep.title("2) 구간별 세굴깊이($S_m$) 산정 과정", level=4)
            if head_shape == "사각형 (Square)":
                Sm_ratio = -0.09 + 0.123 * KC
                rep.latex(r"\frac{S_m}{B} = -0.09 + 0.123 \cdot KC \quad \text{(식 VI-5-258)}")
            else: 
                Sm_ratio = -0.02 + 0.04 * KC
                rep.latex(r"\frac{S_m}{B} = -0.02 + 0.04 \cdot KC \quad \text{(식 VI-5-257)}")
                
            Sm_val = round(B_width * Sm_ratio, 2)
            rep.latex(rf"S_m = {B_width} \times ({Sm_ratio:.4f}) = {Sm_val:.2f} \, m")
            
            if Sm_val < 0:
                rep.warning(f"계산된 세굴심($S_m$)이 {Sm_val:.2f}m로 음수이므로, 물리적으로 세굴이 발생하지 않음을 참조합니다.")
                
        else: # 제간부 (Trunk)
            if "Xie" in wave_condition:
                # =====================================================================
                # 💡 [상세설명 추가] 직립제 제간부 - Xie
                # =====================================================================
                with st.expander("💡 [상세 설명] Xie 공식 기호 및 물리적 원리", expanded=False):
                    rep.md("""
                    **비쇄파 규칙파 조건에서의 세굴 (Xie, 1981, 1985)**
                    * **원리:** 직립제 전면에서는 들어오는 입사파와 부딪혀 나가는 반사파가 중첩되어 파동이 제자리에서 진동하는 **중복파(Standing Wave)**를 형성합니다. 이 수식은 중복파의 마디(Node, 수평 유속이 최대가 되는 지점)에서 발생하는 최대 세굴 깊이를 산정합니다.
                    * $H_s$ (m): 유의파고. 파랑 에너지를 대표하는 지표입니다.
                    * $kh$ (rad): 파수($k=2\pi/L$)와 수심($h$)의 곱. 수심 대비 파장이 얼마나 긴지를 나타내는 무차원 변수입니다.
                    * $\sinh(kh)$: 파랑 에너지가 바닥 깊은 곳까지 얼마나 전달되는지를 결정하는 쌍곡선 함수입니다. 수심이 깊어질수록($kh$가 커질수록) 바닥에 미치는 파랑 에너지가 급격히 감소하므로 분모에 위치하여 세굴심을 줄이는 역할을 합니다.
                    """)
                    
                rep.title("Xie (1981, 1985) 산정 과정", level=4)
                Sm_val_raw = (0.4 * H_input) / (math.sinh(kh_init)**1.35)
                Sm_val = round(Sm_val_raw, 2)
                rep.latex(r"S_m = \frac{0.4 \cdot H_s}{[\sinh(kh)]^{1.35}} = " + f"{Sm_val:.2f} \, m")
            else:
                # =====================================================================
                # 💡 [상세설명 추가] 직립제 제간부 - Hughes and Fowler
                # =====================================================================
                with st.expander("💡 [상세 설명] Hughes and Fowler 공식 기호 및 물리적 원리", expanded=False):
                    rep.md("""
                    **비쇄파 불규칙파 조건에서의 세굴 (Hughes and Fowler, 1991)**
                    * **원리:** 실제 해상 상태와 가장 유사한 불규칙파 스펙트럼 에너지를 기반으로 계산합니다. 해저면 부근에서 발생하는 수평바닥유속의 제곱평균제곱근(rms)의 최대치인 $(U_{rms})_m$를 도출하여 세굴심을 구합니다.
                    * $T_p$ (sec): 피크 주기 ($1.05 \\times T_s$). 불규칙파 스펙트럼에서 에너지가 가장 집중된 주기를 사용합니다.
                    * $ \\bar{d}$ ($=h / gT_p^2$): 주기와 중력가속도 대비 현재 수심을 나타내는 무차원 수심 변수입니다.
                    * $H_{mo}$ (m): 영차모멘트 파고. 불규칙파 스펙트럼의 전체 면적(에너지)을 기반으로 산출된 파고입니다. (아래 Thompson and Vincent 도표를 통해 유의파고에서 환산)
                    * $(U_{rms})_m$ (m/s): 불규칙 중복파동에 의해 발생하는 해저면 최대 수평 유속입니다. 이 값이 클수록 해저면의 모래 입자가 강하게 교란되어 세굴이 깊어집니다.
                    """)
                    
                rep.title("Hughes and Fowler (1991) 산정 과정", level=4)
                Tp = 1.05 * T_input
                Lp = calc_wave_length(Tp, h_bed) 
                kp = 2 * math.pi / Lp
                kph = kp * h_bed
                
                rep.latex(r"T_p = 1.05 T_s = " + f"{Tp:.2f} \, s, \quad k_p = 2\pi/L_p = {kp:.5f}")
                validity_str = "O.K" if 0.05 < kph < 3.0 else "N.G"
                rep.latex(r"(U_{rms})_m \text{ 적용 판별 } (k_p h) = " + f"{kph:.4f} \quad (0.05 < k_p h < 3.0) \rightarrow \mathbf{{{validity_str}}}")

                d_bar = h_bed / (g_val * (Tp**2))
                
                load_success = False
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    csv_path = os.path.join(current_dir, "tav_data_all.csv")
                    
                    df_raw = pd.read_csv(csv_path, header=None)
                    series_names = df_raw.iloc[0].ffill().astype(str)
                    data_tav = df_raw.iloc[2:].reset_index(drop=True)
                    data_tav = data_tav.apply(pd.to_numeric, errors='coerce')
                    
                    avg_cols = [i for i, name in enumerate(series_names) if "average" in name.lower()]
                    
                    if len(avg_cols) >= 2:
                        x_raw = data_tav.iloc[:, avg_cols[0]].dropna().values
                        y_raw = data_tav.iloc[:, avg_cols[1]].dropna().values
                    else:
                        x_raw = data_tav.iloc[:, 2].dropna().values
                        y_raw = data_tav.iloc[:, 3].dropna().values

                    x_unique, unique_idx = np.unique(x_raw, return_index=True)
                    y_unique = y_raw[unique_idx]
                    
                    x_user = x_unique
                    y_user = y_unique
                    load_success = True
                except Exception as e:
                    rep.warning(f"🚨 'tav_data_all.csv' 파일 로드 실패. 앱 파일 경로를 확인해주세요. (에러: {e})")
                    x_user = np.array([
                        0.0013, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 
                        0.01, 0.012, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06
                    ])
                    y_user = np.array([
                        1.475, 1.340, 1.245, 1.185, 1.145, 1.118, 1.097, 1.082, 1.071, 
                        1.062, 1.047, 1.033, 1.022, 1.016, 1.012, 1.008, 1.005, 1.003
                    ])
                
                if x_user.min() <= d_bar <= x_user.max():
                    pchip = PchipInterpolator(x_user, y_user)
                    Hs_ratio_raw = float(pchip(d_bar))
                else:
                    Hs_ratio_raw = float(np.interp(d_bar, x_user, y_user))
                
                Hs_ratio = round(Hs_ratio_raw, 2)
                Hmo = H_input / Hs_ratio
                
                rep.md(f"**$H_{{mo}}$ 산정 (Thompson and Vincent 1985 도표 적용)**")
                rep.latex(r"\bar{d} = \frac{d}{g T_p^2} = " + f"{d_bar:.3e}")
                rep.latex(r"H_s / H_{mo} = " + f"{Hs_ratio:.2f} \quad \text{{(도표 적용)}}")
                rep.latex(r"H_{mo} = \frac{H_s}{H_s / H_{mo}} = \frac{" + f"{H_input:.2f}" + r"}{" + f"{Hs_ratio:.2f}" + r"} = " + f"{Hmo:.2f} \, m")
                
                fig, ax = plt.subplots(figsize=(7, 6.5))
                
                if load_success:
                    unique_series = series_names.unique()
                    
                    for series in unique_series:
                        s_name = str(series).strip()
                        cols = [i for i, name in enumerate(series_names) if name == series]
                        
                        if len(cols) >= 2:
                            ex = data_tav.iloc[:, cols[0]].dropna().values
                            ey = data_tav.iloc[:, cols[1]].dropna().values
                            if len(ex) < 2: continue
                            
                            ex_u, eu_idx = np.unique(ex, return_index=True)
                            ey_u = ey[eu_idx]
                            
                            try:
                                p_curve = PchipInterpolator(ex_u, ey_u)
                                x_smooth = np.logspace(np.log10(ex_u.min()), np.log10(ex_u.max()), 100)
                                y_smooth = p_curve(x_smooth)
                            except:
                                x_smooth, y_smooth = ex_u, ey_u
                                p_curve = None
                                
                            s_name_lower = s_name.lower()
                            
                            if "maximum" in s_name_lower:
                                ax.plot(x_smooth, y_smooth, 'k-', linewidth=1.5, zorder=2)
                                x_tgt = 0.002
                                try: y_ptr = float(p_curve(x_tgt)) if p_curve else ey_u[len(ey_u)//3]
                                except: y_ptr = ey_u[len(ey_u)//3]
                                
                                ax.annotate('MAXIMUM\n$H_s/H_{mo}$', xy=(x_tgt, y_ptr), xytext=(0.0003, 1.62),
                                            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.05", color='black', lw=1.2),
                                            fontsize=11, ha='center', va='center', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
                                            
                            elif "average" in s_name_lower:
                                ax.plot(x_smooth, y_smooth, 'k-', linewidth=1.8, label='AVERAGE Curve', zorder=3)
                                x_tgt = 0.002
                                try: y_ptr = float(p_curve(x_tgt)) if p_curve else ey_u[1]
                                except: y_ptr = ey_u[1]
                                
                                ax.annotate('AVERAGE\n$H_s/H_{mo}$', xy=(x_tgt, y_ptr), xytext=(0.0003, 1.40),
                                            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.1", color='black', lw=1.2),
                                            fontsize=11, ha='center', va='center', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
                                            
                            elif s_name.replace('.', '').isdigit():
                                ax.plot(x_smooth, y_smooth, 'k-', linewidth=0.8, alpha=0.8, zorder=1)
                                mid_idx = int(len(x_smooth) * 0.45) if len(x_smooth) > 10 else len(ex_u)//2
                                x_mid = x_smooth[mid_idx]
                                y_mid = y_smooth[mid_idx]
                                
                                eps_val = s_name.replace("0.", ".")
                                ax.text(x_mid, y_mid, f"$\\epsilon={eps_val}$", fontsize=9, rotation=45, 
                                        ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', pad=0.1, alpha=0.8))

                    ax.text(0.012, 1.25, "PRE-BREAKING", fontsize=11, ha='left', va='center')
                    ax.annotate('', xy=(0.005, 1.15), xytext=(0.011, 1.25), 
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.15", color='black', lw=1.0, alpha=0.9))
                
                ax.plot(d_bar, Hs_ratio, 'bo', markersize=6, zorder=5)
                ax.axvline(x=d_bar, color='b', linestyle='--', alpha=0.8, linewidth=1.5, zorder=4)
                ax.axhline(y=Hs_ratio, color='b', linestyle='--', alpha=0.8, linewidth=1.5, zorder=4)
                
                ax.text(d_bar * 1.05, Hs_ratio + 0.015, f"({d_bar:.2e}, {Hs_ratio:.2f})", 
                        color='blue', fontsize=11, fontweight='bold', ha='left', va='bottom',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9), zorder=6)
                
                ax.set_xscale('log')
                ax.set_xlim(1e-4, 1e-1)
                ax.set_ylim(0.9, 1.7)
                
                ax.tick_params(axis='both', which='major', direction='in', length=8, width=1.5, labelsize=11)
                ax.tick_params(axis='both', which='minor', direction='in', length=4, width=1)
                for spine in ax.spines.values():
                    spine.set_linewidth(1.5)
                
                ax.set_xlabel(r'$\bar{d} = d / g T_p^2$', fontsize=13)
                ax.set_ylabel(r'$H_s / H_{mo}$', fontsize=13)
                ax.grid(False)
                
                col_graph, _ = st.columns([1, 1]) 
                with col_graph:
                    rep.fig(fig)

                term1 = math.sqrt(2) / (4 * math.pi * math.cosh(kph))
                term2 = 0.54 * math.cosh((1.5 - kph) / 2.8)
                Urms_m = (g_val * kp * Tp * Hmo) * term1 * term2
                
                rep.md("**수평바닥유속의 rms 및 세굴심도 산정**")
                rep.latex(r"(U_{rms})_m = \frac{\sqrt{2}}{4\pi \cosh(k_p h)} \times \left[ 0.54 \cosh\left(\frac{1.5 - k_p h}{2.8}\right) \right] \times g k_p T_p H_{mo}")
                rep.latex(r"(U_{rms})_m = " + f"{Urms_m:.4f} \, m/s")
                
                Sm_val_raw = (Urms_m * Tp * 0.05) / (math.sinh(kph)**0.35)
                Sm_val = round(Sm_val_raw, 2)
                rep.latex(r"S_m = (U_{rms})_m T_p \frac{0.05}{[\sinh(k_p h)]^{0.35}} = " + f"{Sm_val:.2f} \, m")
                
    else: # 경사제
        # =====================================================================
        # 💡 [상세설명 추가] 경사제 (C.E.M. 경험식)
        # =====================================================================
        with st.expander("💡 [상세 설명] 경사제 세굴심도 공식 및 기호 물리적 의미", expanded=False):
            rep.md("""
            **경사제 세굴심 산정 (C.E.M. 경험식)**
            * **원리:** 직립제와 달리 경사제는 사석 틈새로 파랑 에너지를 흡수하여 반사율이 낮습니다. 따라서 중복파보다는 입사파의 쇄파(Breaking) 여부와 구조물의 경사도 등이 세굴에 더 큰 영향을 미치며, 이를 반영한 경험식을 사용합니다.
            * $C_u$ (-): 경험계수. 구조물의 피복재 형상, 파랑의 입사 각도, 쇄파 여부 등에 따라 실험적으로 결정되는 값입니다. 구조물 주변의 난류 강도를 보정하는 역할을 합니다.
            * $T_p$ (s): 피크 주기 ($1.05 \\times T_s$). 파랑 에너지가 가장 집중된 주기를 사용합니다.
            * $h$ (m): 현재 설계 수심.
            * $\\frac{T_p \sqrt{g H_s}}{h}$: 무차원 파랑-수심 변수. 파랑의 궤도 운동 에너지가 수심을 뚫고 해저면에 도달하는 강도를 수치화한 척도입니다. 이 값이 커질수록 수심 대비 파랑의 작용이 강력하다는 뜻이므로 세굴이 깊게 산정됩니다.
            """)
            
        if location_type == "제두부 (Head)":
            rep.title("경사제 제두부 세굴심도 산정 과정", level=4)
        else:
            rep.title("경사제 제간부 세굴심도 산정 과정 (제두부와 동일 수식 반영)", level=4)
            
        Tp = 1.05 * T_input
        rep.latex(rf"T_p = 1.05 T_s = 1.05 \times {T_input:.2f} = {Tp:.2f} \, s")
        
        term = (Tp * math.sqrt(abs(g_val * H_input))) / h_bed
        Sm_ratio = 0.01 * Cu_input * (term**1.5)
        Sm_val_raw = H_input * Sm_ratio
        Sm_val = round(Sm_val_raw, 2)
        
        rep.latex(r"\frac{S_m}{H_s} = 0.01 C_u \left( \frac{T_p \sqrt{g H_s}}{h} \right)^{3/2}")
        rep.latex(rf"\frac{{S_m}}{{H_s}} = 0.01 \times {Cu_input:.2f} \times \left( \frac{{{Tp:.2f} \times \sqrt{{{g_val} \times {H_input:.2f}}}}}{{{h_bed:.2f}}} \right)^{{1.5}} = {Sm_ratio:.4f}")
        rep.latex(rf"S_m = {H_input:.2f} \times {Sm_ratio:.4f} = {Sm_val:.2f} \, m")

    final_sm_for_design = max(0.0, Sm_val)
    rep.success(f"**최종 산정 최대 세굴심도 ($S_m$): {Sm_val:.2f} m**")

    # 🌟 다. 세굴방지 보강폭 및 두께 산정
    rep.title("다. 세굴방지 보강폭($B_{sp}$) 및 두께($t$) 산정", level=3)
    width_coeff = 2.0 if "매설형" in protection_type else 3.0
    
    B_sp = width_coeff * final_sm_for_design
    thickness = 2.0 * r_stone
    
    rep.md(f"**적용 보호공 형식:** {protection_type}")
    rep.latex(rf"B_{{sp}} = {int(width_coeff)} \times \max(0, S_m) = {B_sp:.2f} \, m")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        rep.info(f"**최종 보강폭 ($B_{{sp}}$): {B_sp:.2f} m**")
    with col_res2:
        rep.info(f"**최종 설계두께 ($t = 2r$): {thickness:.2f} m**")

    # ==========================================
    # 선명한 이미지(`image_efd977.png`) Crop & 보정
    # ==========================================
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(current_dir, "image_efd977.png")
        
        img = Image.open(img_path)
        w, h = img.size
        
        enhancer_contrast = ImageEnhance.Contrast(img)
        img = enhancer_contrast.enhance(1.2)  
        
        enhancer_sharpness = ImageEnhance.Sharpness(img)
        img = enhancer_sharpness.enhance(1.8) 
        
        if "매설형" in protection_type:
            cropped_img = img.crop((0, 0, int(w * 0.49), h)) 
        else:
            cropped_img = img.crop((int(w * 0.51), 0, w, h))
            
        rep.md(f"**[{protection_type.split(' ')[0]} 산정 기준 삽도 (보정됨)]**")
        
        col_img1, col_img2, col_img3 = st.columns([1.2, 1.5, 1.2])
        with col_img2:
            rep.image_pil(cropped_img)
            
    except FileNotFoundError:
        rep.warning(f"설계 삽도 이미지 파일('image_efd977.png')을 찾을 수 없습니다. 파이썬 스크립트와 동일한 폴더에 위치시켜 주세요.")

else:
    rep.md("원지반이 안정하여 추가적인 보강 계획이 필요하지 않습니다.")

# ==========================================
# ★ 전체결과 요약표 렌더링
# ==========================================
with summary_placeholder.container():
    rep.title("📋 전체 산정 결과 요약", level=2)
    
    if scour_status == "필요":
        sum_data = {
            "구 분": [
                "구조물 / 보호공 형식", 
                "원지반 세굴여부", 
                "지배 외력 (파랑 vs 조류)", 
                "최종 필요 소요 직경 (d)", 
                "최종 필요 소요 중량 (W)", 
                "최대 세굴심도 (S_m)", 
                "세굴방지공 최종 보강폭 (B_sp)", 
                "세굴방지공 설계두께 (t)"
            ],
            "산 정 결 과": [
                f"{structure_type.split(' ')[0]} / {protection_type.split(' ')[0]}",
                "보강 필요 🚨",
                "파랑 (Wave)" if "파랑" in control_factor else "조류 (Tidal Current)",
                f"{d_final:.3f} m",
                f"{W_final_ton:.3f} ton",
                f"{Sm_val:.2f} m",
                f"{B_sp:.2f} m",
                f"{thickness:.2f} m"
            ]
        }
        df_summary = pd.DataFrame(sum_data).set_index("구 분")
        rep.table(df_summary)
    else:
        rep.success("✅ **원지반 안정 / 보강 불필요** (현재 수심이 표층이동 한계수심보다 깊어 세굴방지공이 불필요합니다.)")
    st.markdown("---")
    rep.html += "<hr>"

# --- 최종 통합 HTML 보고서 다운로드 버튼 ---
st.divider()
st.download_button(
    label="📄 통합 산정 보고서 다운로드 (.html)",
    data=rep.get_html(),
    file_name=f"세굴방지공_단면제원_자동산정_보고서.html",
    mime="text/html",
    help="클릭 시 수식이 완벽히 복원된 HTML 형태의 보고서를 다운로드합니다."
)
