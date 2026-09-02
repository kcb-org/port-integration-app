import streamlit as st
import math
import os
import urllib.request
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import base64

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

def get_image_base64(filepath):
    try:
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        return ""

# =====================================================================
# ★ 파력 평활화 및 고다 계수 계산 엔진 (마이너스 클리핑 보정 장치 추가)
# =====================================================================
class WaveSmoothingCalculator:
    def __init__(self):
        self.g = 9.81

    def calc_wavelength(self, T, depth):
        if depth <= 0 or T <= 0: return 0.0, 0.0, []
        
        L0 = (self.g * T**2) / (2 * math.pi)
        L = L0
        history = []
        
        for i in range(1, 101):
            L_new = L0 * math.tanh(2 * math.pi * depth / L)
            history.append((i, L_new))
            if abs(L_new - L) < 0.001:
                break
            L = L_new
            
        return L, L0, history

    def calc_goda_alphas(self, H_13, H_max, h, d, slope, L):
        h_b = h + 5 * H_13 * slope
        term = 4 * math.pi * h / L if L != 0 else 0
        sinh_term = math.sinh(term) if term < 100 else float('inf')
        
        if sinh_term == 0 or sinh_term == float('inf'):
            alpha1 = 0.6
        else:
            alpha1 = 0.6 + 0.5 * (term / sinh_term)**2
            
        if h_b != 0 and d != 0:
            a2_1 = ((h_b - d) / (3 * h_b)) * ((H_max / d)**2)
            a2_2 = 2 * d / H_max if H_max != 0 else 0
            alpha2 = min(a2_1, a2_2)
            alpha2 = max(0, alpha2)
        else:
            a2_1, a2_2, alpha2 = 0, 0, 0
            
        return h_b, alpha1, alpha2, a2_1, a2_2

    def calc_smoothing_coeffs(self, l_B, theta_deg, L, alpha1, alpha2):
        theta_rad = math.radians(theta_deg)
        ratio = (l_B * math.sin(theta_rad)) / L if L != 0 else 0
        val = math.pi * ratio
        
        if val == 0:
            delta_B1 = 1.0
        else:
            delta_B1 = math.sin(val) / val
            
        if ratio >= (1/20):
            delta_B2 = 1 / (40 * ratio) if ratio != 0 else 1.0
        else:
            delta_B2 = 1.0 - 10 * ratio
            
        gamma = (alpha2 * math.cos(theta_rad)**2) / alpha1 if alpha1 != 0 else 0
        
        raw_delta_B = (delta_B1 + gamma * delta_B2) / (1 + gamma) if (1 + gamma) != 0 else 1.0
        raw_delta_BU = delta_B1
        
        # 💡 안전 장치: 마이너스 값이 발생할 경우 최소값(0.0)으로 클리핑 보정
        delta_B = max(0.0, raw_delta_B)
        delta_BU = max(0.0, raw_delta_BU)
        
        return ratio, delta_B1, delta_B2, gamma, delta_B, delta_BU


# =====================================================================
# ★ 앱 레이아웃 시작
# =====================================================================
st.set_page_config(page_title="장대케이슨 파력 평활화 검토", page_icon="🌊", layout="wide")

st.title("🌊 장대케이슨의 파력 평활화계수 자동 산정 시스템")

# ----------------------------------------------------
# 사이드바 입력 조건 내 케이슨 길이 설정 추가
# ----------------------------------------------------
with st.sidebar:
    st.header("📐 1. 케이슨 제원")
    l_B = st.number_input(r"케이슨 법선방향 길이 $l_B$ (m)", value=40.0, step=1.0)
    theta_deg = st.number_input(r"파의 입사각 $\theta$ (°)", value=30.0, step=1.0)
    
    st.markdown("---")
    st.header("📏 5. 비교용 케이슨 길이 목록 설정")
    default_lengths_str = "10, 20, 40, 50, 80, 100, 150, 200, 250, 300, 350, 400, 500, 600, 700, 800, 900, 1000"
    user_lengths_input = st.text_input("비교할 케이슨 길이 (쉼표로 구분, m)", value=default_lengths_str)
    
    st.markdown("---")
    st.header("🌊 2. 파랑 및 수심 제원")
    H_13 = st.number_input(r"유의파고 $H_{1/3}$ (m)", value=8.5, step=0.1)
    H_max = st.number_input(r"최대파고 $H_{max}$ (m)", value=15.3, step=0.1)
    T = st.number_input(r"주기 $T$ (sec)", value=15.5, step=0.1)
    
    st.markdown("---")
    design_wl = st.number_input(r"설계조위 (m)", value=0.656, step=0.01)
    h = st.number_input(r"직립벽 전면수심 $h$ (설계조위 고려, m)", value=28.656, step=0.1)
    d = st.number_input(r"사석부/피복공 수심 $d$ (m)", value=19.256, step=0.1)
    slope = st.number_input(r"해저경사", value=0.02, step=0.01)

# =====================================================================
# 메인 화면: 엔진 호출 및 계산
# =====================================================================
calc = WaveSmoothingCalculator()

L, L0_h, hist_h = calc.calc_wavelength(T, h)
L_prime, L0_d, hist_d = calc.calc_wavelength(T, d)
h_b, alpha1, alpha2, a2_1, a2_2 = calc.calc_goda_alphas(H_13, H_max, h, d, slope, L)
ratio, delta_B1, delta_B2, gamma, delta_B, delta_BU = calc.calc_smoothing_coeffs(l_B, theta_deg, L, alpha1, alpha2)

# =====================================================================
# 결과 출력부 (순서: 1 -> 2 -> 3 -> 4 -> 5)
# =====================================================================

# ---------------------------------------------------------------------
# 1. 파력 평활화 효과의 개념 및 특징
# ---------------------------------------------------------------------
st.header("1. 파력 평활화 효과의 개념 및 특징")

st.markdown("""
<div style='background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin: 15px 0;'>
<b>파력 평활화 효과 (Wave Force Smoothing Effect)란?</b><br>
방파제 법선 방향과 파향(입사파) 사이에 위상차가 존재할 때, 길이가 긴 장대(Long) 케이슨의 각 지점에서 파력의 피크(Peak)가 동시에 작용하지 않고 시차를 두고 분산되는 현상입니다. 이로 인해 <b>케이슨 전체에 작용하는 단위 길이당 평균 수평 파력이 감소</b>하게 됩니다.
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 8, 1])
with col2:
    try:
        st.image("파력의 평활화 효과.png", caption="장대케이슨 파력 평활화 효과 개념도", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ '파력의 평활화 효과.png' 이미지 파일을 소스코드와 동일한 폴더에 넣어주세요.")

st.markdown(r"""
* **발현 조건 및 특징:**
  * **투영 길이 비:** 케이슨의 투영 길이($l_B \sin\theta$)와 파장($L$)의 비가 클수록 파력 저감 효과가 커집니다.
  * **입사각:** 수직 직각 입사파보다는 입사각($\theta$)이 큰 경사 입사파에서 효과가 뚜렷합니다.
  * **파형:** 파형의 피크가 날카롭고 솟아 있는 쇄파나 충격파 형태일 때 평활화 효과가 극대화됩니다.
* **인터록킹(Interlocking) 케이슨 구조:**
  * **장점:** 사다리꼴 형태 등으로 케이슨끼리 맞물리게 하여 일체화함으로써, 개별 거동으로 인한 사행재해(뱀모양 파괴)를 방지하고 파력을 분산시킵니다.
  * **단점:** 하나의 케이슨 파괴나 지반 부등침하시 전체 구조가 취약해질 수 있으며, 케이슨 간 시공 이음부로 인해 일체화 거동이 100% 이루어지지 않을 수 있습니다.
""")
st.divider()

# ---------------------------------------------------------------------
# 2. 평활화 계수 산정식 및 장대케이슨 설계 절차
# ---------------------------------------------------------------------
st.header("2. 평활화 계수($\\delta_B$) 산정식 및 장대케이슨 설계 절차")
st.markdown(r"""
### 가. 평활화 계수 산정 공식
일본 고다(Goda)식의 중복파압 성분($\alpha_1$)과 충격파압 성분($\alpha_2$)에 각각 다른 평활화 계수를 적용합니다.
""")
st.latex(r"\delta_{B1} = \frac{\sin(\pi \cdot l_B \sin\theta / L)}{\pi \cdot l_B \sin\theta / L} \quad (\alpha_1\text{항의 평활화계수})")
st.latex(r"\delta_{B2} = \begin{cases} \frac{L}{40 \cdot l_B \sin\theta} & (\frac{l_B \sin\theta}{L} \ge \frac{1}{20}) \\ 1.0 - 10 \left( \frac{l_B \sin\theta}{L} \right) & (\frac{l_B \sin\theta}{L} < \frac{1}{20}) \end{cases} \quad (\alpha_2\text{항의 평활화계수})")
st.latex(r"\gamma = \frac{\alpha_2 \cos^2\theta}{\alpha_1} \quad (\text{가중치})")
st.latex(r"\delta_B = \frac{\delta_{B1} + \gamma \delta_{B2}}{1 + \gamma} \quad (\text{수평파력 최종 평활화계수})")
st.latex(r"\delta_{BU} = \delta_{B1} \quad (\text{양압력 최종 평활화계수})")

st.markdown(r"""
### 나. 장대케이슨 내파 안정성 설계 절차
1. **초기 파력 계산**: 통상의 고다식을 이용하여 단위 길이당 수평파력($P_G$)과 양압력($U_G$) 계산
2. **평활화 계수 산정**: 케이슨 길이와 파랑 조건을 고려하여 $\delta_B$, $\delta_{BU}$ 도출
3. **설계 파력 적용**: 평활화 효과가 반영된 실제 작용 수평파력($P_o = \delta_B \cdot P_G$)과 양압력($U_o = \delta_{BU} \cdot U_G$) 계산
4. **활동(Sliding) 안정성 검토**: $SF_S = \frac{\mu(\omega' - U_o)}{P_o} \ge 1.2$ 검토
5. **회전(Rotation) 안정성 검토**: 편심된 파력 분포로 인한 회전 안전율($SF_R \ge 1.0$) 검토 (단, $(l_B\sin\theta)/L \le 0.5$ 이면 생략 가능)
""")
st.divider()

# ---------------------------------------------------------------------
# 3. 자동 산정 결과 요약표
# ---------------------------------------------------------------------
st.header("3. 자동 산정 결과 요약표 (현재 입력된 $l_B$ 기준)")

if ratio > 0.5:
    st.warning("⚠️ **주의:** $(l_B \sin\\theta) / L > 0.5$ 입니다. 전면 수위가 0.5H 저하될 때 작용하는 부(-)의 파력에 대한 추가 검토가 필요합니다.")

tbl_html = f"""
<table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.1em; background-color: white;" border="1">
    <tr style="background-color: #f1f8ff; color: #1e3a8a;">
        <th style="padding: 12px; border: 1px solid #ddd;">구분</th>
        <th style="padding: 12px; border: 1px solid #ddd;">결과값</th>
        <th style="padding: 12px; border: 1px solid #ddd;">비고</th>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">해당 수심의 파장</td>
        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">L = {L:.2f} m<br>L' = {L_prime:.2f} m</td>
        <td style="padding: 12px; border: 1px solid #ddd;">L: 수심 {h}m 기준 (평활화 계수용)<br>L': 수심 {d}m 기준</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">고다식 파압계수</td>
        <td style="padding: 12px; border: 1px solid #ddd;">α<sub>1</sub> = {alpha1:.3f}<br>α<sub>2</sub> = {alpha2:.3f}</td>
        <td style="padding: 12px; border: 1px solid #ddd;">중복파압(α1), 충격파압(α2) 성분</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">수평파력 평활화 계수</td>
        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #d9480f; font-size: 1.2em;">δ<sub>B</sub> = {delta_B:.3f}</td>
        <td style="padding: 12px; border: 1px solid #ddd;">수평 파력 설계 시 {delta_B*100:.1f}% 적용</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">양압력 평활화 계수</td>
        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #d9480f; font-size: 1.2em;">δ<sub>BU</sub> = {delta_BU:.3f}</td>
        <td style="padding: 12px; border: 1px solid #ddd;">양압력 설계 시 {delta_BU*100:.1f}% 적용</td>
    </tr>
</table>
"""
st.markdown(tbl_html, unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------------
# 4. 수식 전개 및 상세 계산 풀이 과정
# ---------------------------------------------------------------------
st.header("4. 수식 전개 및 상세 계산 풀이 과정")

col_p1, col_p2, col_p3 = st.columns([1, 4, 1])
with col_p2:
    try:
        st.image("설계파압 분포도.png", caption="설계파압 분포도", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ '설계파압 분포도.png' 이미지 파일을 소스코드와 동일한 폴더에 넣어주세요.")

st.markdown("### Step 1: 천해파 파장 산정 (시산법)")
st.markdown("심해파장 $L_0$를 초깃값으로 하여 $L^{(i+1)} = L_0 \\tanh\\left(\\frac{2\\pi h}{L^{(i)}}\\right)$ 공식을 통해 수렴할 때까지 반복 계산합니다.")

st.latex(rf"L_0 = \frac{{g T^2}}{{2\pi}} = \frac{{9.81 \times {T}^2}}{{2\pi}} = {L0_h:.2f} \text{{ m}}")

hist_h_str = ""
if len(hist_h) > 0:
    hist_h_str += rf"1\text{{차: }} {hist_h[0][1]:.2f} \text{{ m}} \quad "
if len(hist_h) > 1:
    hist_h_str += rf"2\text{{차: }} {hist_h[1][1]:.2f} \text{{ m}} \quad \dots \quad "
hist_h_str += rf"\text{{최종 수렴 }} L = {L:.2f} \text{{ m}}"

st.markdown(f"**[직립벽 전면수심 $h = {h}$ m 조건]**")
st.latex(hist_h_str)

hist_d_str = ""
if len(hist_d) > 0:
    hist_d_str += rf"1\text{{차: }} {hist_d[0][1]:.2f} \text{{ m}} \quad "
if len(hist_d) > 1:
    hist_d_str += rf"2\text{{차: }} {hist_d[1][1]:.2f} \text{{ m}} \quad \dots \quad "
hist_d_str += rf"\text{{최종 수렴 }} L' = {L_prime:.2f} \text{{ m}}"

st.markdown(f"**[사석부 수심 $d = {d}$ m 조건]**")
st.latex(hist_d_str)

st.markdown("---")
st.markdown("### Step 2: 고다(Goda) 파압계수 자동 산정")
st.markdown("**1) 중복파압 성분계수 ($\\alpha_1$)**")
st.latex(rf"\alpha_1 = 0.6 + \frac{{1}}{{2}} \left[ \frac{{4\pi h / L}}{{\sinh(4\pi h / L)}} \right]^2 = 0.6 + 0.5 \left[ \frac{{4\pi \times {h} / {L:.2f}}}{{\sinh(4\pi \times {h} / {L:.2f})}} \right]^2 = {alpha1:.3f}")

st.markdown("**2) 충격파압 성분계수 ($\\alpha_2$)**")
st.latex(rf"h_b = h + 5 H_{{1/3}} \tan\theta = {h} + 5 \times {H_13} \times {slope} = {h_b:.3f} \text{{ m}}")
st.latex(rf"\alpha_2 = \min \left[ \frac{{h_b - d}}{{3 h_b}} \left( \frac{{H_{{max}}}}{{d}} \right)^2, \frac{{2d}}{{H_{{max}}}} \right]")
st.latex(rf"= \min \left[ \frac{{{h_b:.3f} - {d}}}{{3 \times {h_b:.3f}}} \left( \frac{{{H_max}}}{{{d}}} \right)^2, \frac{{2 \times {d}}}{{{H_max}}} \right] = \min[{a2_1:.3f}, {a2_2:.3f}] = {alpha2:.3f}")

st.markdown("---")
st.markdown("### Step 3: 평활화 투영 길이비 및 $\\alpha_1$ 항 계수($\\delta_{B1}$)")
st.latex(rf"\text{{상대길이비}} = \frac{{l_B \sin\theta}}{{L}} = \frac{{{l_B} \times \sin({theta_deg}^\circ)}}{{{L:.2f}}} = {ratio:.4f}")
st.latex(rf"\delta_{{B1}} = \frac{{\sin(\pi \times {ratio:.4f})}}{{\pi \times {ratio:.4f}}} = {delta_B1:.4f}")

st.markdown("### Step 4: $\\alpha_2$ 항 계수($\\delta_{B2}$)")
if ratio >= (1/20):
    st.markdown(f"상대길이비({ratio:.4f}) $\ge 1/20 (0.05)$ 이므로 첫번째 공식을 적용합니다.")
    st.latex(rf"\delta_{{B2}} = \frac{{1}}{{40 \times {ratio:.4f}}} = {delta_B2:.4f}")
else:
    st.markdown(f"상대길이비({ratio:.4f}) $< 1/20 (0.05)$ 이므로 두번째 공식을 적용합니다.")
    st.latex(rf"\delta_{{B2}} = 1.0 - 10 \times {ratio:.4f} = {delta_B2:.4f}")

st.markdown("### Step 5: 가중치($\gamma$) 및 최종 평활화 계수 산출")
st.latex(rf"\gamma = \frac{{\alpha_2 \cos^2\theta}}{{\alpha_1}} = \frac{{{alpha2:.3f} \times \cos^2({theta_deg}^\circ)}}{{{alpha1:.3f}}} = {gamma:.4f}")
st.latex(rf"\delta_B = \frac{{\delta_{{B1}} + \gamma \delta_{{B2}}}}{{1 + \gamma}} = \frac{{{delta_B1:.4f} + {gamma:.4f} \times {delta_B2:.4f}}}{{1 + {gamma:.4f}}} = {delta_B:.4f}")
st.latex(rf"\delta_{{BU}} = \delta_{{B1}} = {delta_BU:.4f}")
st.divider()

# ---------------------------------------------------------------------
# 5. 케이슨 법선방향 길이에 따른 평활화 효과 비교 표 (참고 문구 디자인 및 하위 들여쓰기 수정본)
# ---------------------------------------------------------------------
import pandas as pd

st.header("5. 케이슨 법선방향 길이에 따른 평활화 효과 비교")
st.markdown(r"""
지정된 케이슨 길이별(10m ~ 1,000m) 투영 길이비와 그에 따른 **수평파력 평활화 계수 ($\delta_B$)** 및 **양압력 평활화 계수 ($\delta_{BU}$)**의 변화를 나타낸 표입니다. *(단, 계산 결과가 마이너스(-)로 산정될 경우 안정성을 고려하여 하한선인 0으로 클리핑 보정함)*
""")

try:
    length_list = [float(x.strip()) for x in user_lengths_input.split(",") if x.strip()]
    length_list = sorted(list(set(length_list)))
except Exception:
    length_list = [10, 20, 40, 50, 80, 100, 150, 200, 250, 300, 350, 400, 500, 600, 700, 800, 900, 1000]

table_data = []
sensitivity_rows_for_report = ""

for l_val in length_list:
    r_val, b1_val, b2_val, g_val, db_val, dbu_val = calc.calc_smoothing_coeffs(l_val, theta_deg, L, alpha1, alpha2)
    warning_text = " ⚠️(>0.5)" if r_val > 0.5 else ""
    
    table_data.append({
        "케이슨 길이 (l_B)": f"{l_val:g} m",
        "투영 길이비 ((l_B sinθ)/L)": f"{r_val:.4f}{warning_text}",
        "수평파력 평활화 계수 (δ_B)": f"{db_val:.4f}",
        "양압력 평활화 계수 (δ_BU)": f"{dbu_val:.4f}"
    })
    
    row_str = f"""
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;">{l_val:g} m</td>
        <td style="padding: 8px; border: 1px solid #ddd;">{r_val:.4f}{warning_text}</td>
        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: #d9480f;">{db_val:.4f}</td>
        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: #1e3a8a;">{dbu_val:.4f}</td>
    </tr>
    """
    sensitivity_rows_for_report += row_str

df_sensitivity = pd.DataFrame(table_data)
calculated_height = min(max(150, len(length_list) * 38 + 45), 800)

st.dataframe(df_sensitivity, use_container_width=True, height=calculated_height, hide_index=True)

# 💡 1번 참고 박스 (파란색 배경 적용)
st.markdown("""
<div style='background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin-top: 15px; margin-bottom: 10px; border-radius: 4px;'>
<b>참고) 케이슨 투영 길이비와 내파 안정성 검토 기준 및 마이너스(-) 계수 처리</b>
</div>
""", unsafe_allow_html=True)

st.markdown(r"- $\frac{l_B \sin\theta}{L} \le 0.5$ 인 구간: 통상의 평면적 회전(Rotation) 검토를 간략화하거나 생략할 수 있습니다.")
st.markdown(r"- $\frac{l_B \sin\theta}{L} > 0.5$ 인 구간 (⚠️ 표시 구간): 케이슨 길이가 길어져 투영 길이비가 0.5를 초과하는 경우, 편심된 파력 분포에 따른 **평면적 회전 안정성 검토** 및 전면 수위가 $0.5H$ 저하될 때 작용하는 **부(-)의 파력(Negative Wave Force) 영향**을 반드시 정밀하게 추가 검토해야 합니다.")
st.markdown(r"- **평활화 계수가 마이너스(-) 또는 다시 플러스(+)로 산정되는 현상 및 처리:**")
st.markdown(r"  &nbsp;&nbsp;&nbsp;&nbsp;* 케이슨 길이가 파장에 비해 매우 길어지면(투영 길이비가 $1.0$을 초과), 산정식의 사인($\sin$) 함수의 주기적 특성으로 인해 수학적으로 다시 플러스($+$) 값이 나타나거나 마이너스($-$) 값이 반복됩니다.")
st.markdown(r"  &nbsp;&nbsp;&nbsp;&nbsp;* 이는 물리적으로 파력의 저감 효과가 다시 발생하는 것이 아니라, **공식의 유효 범위(경호식 적용 한계)를 벗어난 수학적 결과**에 불과합니다.")
st.markdown(r"  &nbsp;&nbsp;&nbsp;&nbsp;* 따라서 **이상값이 발생하는 구간에서는 설계 파력이 왜곡되지 않도록 강제적으로 하한선인 $0$으로 클리핑(Clipping) 보정**하는 안전 장치를 적용하여 보수적으로 설계합니다.")

# 💡 2번 회전 검토 박스 (파란색 배경 적용)
st.markdown("""
<div style='background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin-top: 20px; margin-bottom: 10px; border-radius: 4px;'>
<b>🔍 장대케이슨의 '회전(Rotation)에 대한 안정성 검토' 방법</b>
</div>
""", unsafe_allow_html=True)

st.markdown("장대케이슨은 일반 케이슨과 달리 법선 방향으로 길기 때문에 파가 사각으로 입사할 때 케이슨 전체에 균일한 힘이 아니라 **시간차를 두고 편심된 분포 하중**이 작용합니다. 회전 안정성은 다음과 같은 절차로 검토합니다.")
st.markdown(r"1. **시각별 회전중심(Pivot Point) 산정**: 파랑이 케이슨 길이를 따라 순차적으로 지나갈 때, 각 시점별로 작용하는 수평파력($P_o$)과 양압력($U_o$)의 분포로부터 케이슨 저면에서의 합력 작용점(편심 거리)을 계산합니다.")
st.markdown(r"2. **모멘트 평형 검토**: 케이슨의 자중(유효중량 $\omega'$)에 의한 복원 모멘트와 편심된 파력에 의한 전복/회전 모멘트를 비교합니다.")
st.markdown(r"3. **회전 안전율($SF_R$) 산정**: 회전 모멘트에 대한 복원 모멘트의 비가 설계 기준(통상 $SF_R \ge 1.0 \sim 1.2$ 이상)을 만족하는지 확인합니다.")

st.divider()

# =====================================================================
# 보고서 다운로드용 HTML 생성 (이미지 인코딩 및 서식 정렬)
# =====================================================================
img_smooth_base64 = get_image_base64("파력의 평활화 효과.png")
img_pressure_base64 = get_image_base64("설계파압 분포도.png")

html_report_smoothing = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>장대케이슨 파력 평활화 검토 보고서</title>
    <script>
        window.MathJax = {{
            tex: {{ 
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], 
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], 
                processEscapes: true 
            }}
        }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; padding: 30px; color: #333; max-width: 1000px; margin: auto; }}
        h1 {{ text-align: center; color: #1e3a8a; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; }}
        h2 {{ color: #1e3a8a; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 40px; }}
        h3 {{ color: #1e3a8a; margin-top: 25px; }}
        .eq {{ text-align: center; font-size: 1.1em; margin: 15px 0; background: #f4f6f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; text-align: center; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; }}
        th {{ background-color: #f1f8ff; color: #1e3a8a; }}
        .info-box {{ background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin: 15px 0; }}
        .concept-img {{ max-width: 600px; height: auto; display: block; margin: 20px auto; border: 1px solid #ddd; padding: 5px; }}
    </style>
</head>
<body>
    <h1>🌊 장대케이슨 파력 평활화 자동 산정 보고서</h1>
    
    <h2>1. 파력 평활화 효과의 개념 및 특징</h2>
    <div class="info-box">
        <b>파력 평활화 효과 (Wave Force Smoothing Effect)란?</b><br>
        방파제 법선 방향과 파향(입사파) 사이에 위상차가 존재할 때, 길이가 긴 장대 케이슨의 각 지점에서 파력의 피크(Peak)가 동시에 작용하지 않고 시차를 두고 분산되어 전체 수평 파력이 감소하는 현상입니다.
    </div>
    
    <img src="{img_smooth_base64}" alt="파력 평활화 효과 개념도" class="concept-img">
    
    <ul>
        <li>케이슨의 투영 길이($l_B \\sin\\theta$)와 파장($L$)의 비가 클수록 파력 저감 효과가 커집니다.</li>
        <li>수직 직각 입사파보다는 입사각($\\theta$)이 큰 경사 입사파에서 효과가 뚜렷합니다.</li>
        <li>파형의 피크가 날카롭고 솟아 있는 쇄파나 충격파 형태일 때 평활화 효과가 큽니다.</li>
    </ul>

    <h2>2. 평활화 계수($\\delta_B$) 산정식 및 장대케이슨 설계 절차</h2>
    <h3>가. 평활화 계수 산정 공식</h3>
    <p>일본 고다(Goda)식의 중복파압 성분($\\alpha_1$)과 충격파압 성분($\\alpha_2$)에 각각 다른 평활화 계수를 적용합니다.</p>
    
    <div class="eq">$$ \\delta_{{B1}} = \\frac{{\\sin(\\pi \\cdot l_B \\sin\\theta / L)}}{{\\pi \\cdot l_B \\sin\\theta / L}} \\quad (\\alpha_1\\text{{항의 평활화계수}}) $$</div>
    <div class="eq">$$ \\delta_{{B2}} = \\begin{{cases}} \\frac{{L}}{{40 \\cdot l_B \\sin\\theta}} & \\left(\\frac{{l_B \\sin\\theta}}{{L}} \\ge \\frac{{1}}{{20}}\\right) \\\\ 1.0 - 10 \\left( \\frac{{l_B \\sin\\theta}}{{L}} \\right) & \\left(\\frac{{l_B \\sin\\theta}}{{L}} < \\frac{{1}}{{20}}\\right) \\end{{cases}} \\quad (\\alpha_2\\text{{항의 평활화계수}}) $$</div>
    <div class="eq">$$ \\gamma = \\frac{{\\alpha_2 \\cos^2\\theta}}{{\\alpha_1}} \\quad (\\text{{가중치}}) $$</div>
    <div class="eq">$$ \\delta_B = \\frac{{\\delta_{{B1}} + \\gamma \\delta_{{B2}}}}{{1 + \\gamma}} \\quad (\\text{{수평파력 최종 평활화계수}}) $$</div>
    <div class="eq">$$ \\delta_{{BU}} = \\delta_{{B1}} \\quad (\\text{{양압력 최종 평활화계수}}) $$</div>

    <h3>나. 장대케이슨 내파 안정성 설계 절차</h3>
    <ol>
        <li><b>초기 파력 계산</b>: 통상의 고다식을 이용하여 단위 길이당 수평파력($P_G$)과 양압력($U_G$) 계산</li>
        <li><b>평활화 계수 산정</b>: 케이슨 길이와 파랑 조건을 고려하여 $\delta_B$, $\delta_{{BU}}$ 도출</li>
        <li><b>설계 파력 적용</b>: 평활화 효과가 반영된 실제 작용 수평파력($P_o = \delta_B \\cdot P_G$)과 양압력($U_o = \delta_{{BU}} \\cdot U_G$) 계산</li>
        <li><b>활동(Sliding) 안정성 검토</b>: $SF_S = \\frac{{\\mu(\\omega' - U_o)}}{{P_o}} \\ge 1.2$ 검토</li>
        <li><b>회전(Rotation) 안정성 검토</b>: 편심된 파력 분포로 인한 회전 안전율($SF_R \\ge 1.0$) 검토 (단, $(l_B\\sin\\theta)/L \\le 0.5$ 이면 생략 가능)</li>
    </ol>

    <h2>3. 자동 산정 결과 요약표</h2>
    {tbl_html}

    <h2>4. 수식 전개 및 상세 계산 풀이 과정</h2>
    <img src="{img_pressure_base64}" alt="설계파압 분포도" class="concept-img">
    
    <p><b>Step 1: 천해파 파장 산정 (시산법)</b></p>
    <div class="eq">$$ L_0 = \\frac{{9.81 \\times {T}^2}}{{2\\pi}} = {L0_h:.2f} \\text{{ m}} $$</div>
    <div class="eq">$$ \\text{{수심 }} {h}\\text{{m 최종 수렴 }} L = {L:.2f} \\text{{ m}} $$</div>
    
    <p><b>Step 2: 고다(Goda) 파압계수 자동 산정</b></p>
    <div class="eq">$$ \\alpha_1 = 0.6 + 0.5 \\left[ \\frac{{4\\pi \\times {h} / {L:.2f}}}{{\\sinh(4\\pi \\times {h} / {L:.2f})}} \\right]^2 = {alpha1:.3f} $$</div>
    <div class="eq">$$ h_b = {h} + 5 \\times {H_13} \\times {slope} = {h_b:.3f} \\text{{ m}} $$</div>
    <div class="eq">$$ \\alpha_2 = \\min \\left[ \\frac{{{h_b:.3f} - {d}}}{{3 \\times {h_b:.3f}}} \\left( \\frac{{{H_max}}}{{{d}}} \\right)^2, \\frac{{2 \\times {d}}}{{{H_max}}} \\right] = {alpha2:.3f} $$</div>

    <p><b>Step 3: 평활화 투영 길이비 및 $\\alpha_1$ 항 계수($\delta_{{B1}}$)</b></p>
    <div class="eq">$$ \\text{{상대길이비}} = \\frac{{{l_B} \\times \\sin({theta_deg}^\\circ)}}{{{L:.2f}}} = {ratio:.4f} $$</div>
    <div class="eq">$$ \\delta_{{B1}} = \\frac{{\\sin(\\pi \\times {ratio:.4f})}}{{\\pi \\times {ratio:.4f}}} = {delta_B1:.4f} $$</div>
    
    <p><b>Step 4: $\\alpha_2$ 항 계수($\delta_{{B2}}$)</b></p>
    <div class="eq">$$ \\delta_{{B2}} = {delta_B2:.4f} $$</div>

    <p><b>Step 5: 가중치($\\gamma$) 및 최종 평활화 계수($\delta_B$, $\delta_{{BU}}$)</b></p>
    <div class="eq">$$ \\gamma = \\frac{{{alpha2:.3f} \\times \\cos^2({theta_deg}^\\circ)}}{{{alpha1:.3f}}} = {gamma:.4f} $$</div>
    <div class="eq">$$ \\delta_B = \\frac{{{delta_B1:.4f} + {gamma:.4f} \\times {delta_B2:.4f}}}{{1 + {gamma:.4f}}} = {delta_B:.4f} $$</div>
    <div class="eq">$$ \\delta_{{BU}} = \\delta_{{B1}} = {delta_BU:.4f} $$</div>

    <h2>5. 케이슨 법선방향 길이에 따른 평활화 효과 비교</h2>
    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.0em;" border="1">
        <tr style="background-color: #f1f8ff; color: #1e3a8a;">
            <th style="padding: 10px; border: 1px solid #ddd;">케이슨 길이 ($l_B$)</th>
            <th style="padding: 10px; border: 1px solid #ddd;">투영 길이비 ($(l_B \sin\\theta)/L$)</th>
            <th style="padding: 10px; border: 1px solid #ddd;">수평파력 평활화 계수 ($\delta_B$)</th>
            <th style="padding: 10px; border: 1px solid #ddd;">양압력 평활화 계수 ($\delta_{{BU}}$)</th>
        </tr>
        {sensitivity_rows_for_report}
    </table>
</body>
</html>
"""

st.download_button(
    label="💾 현재 화면 전체 보고서 다운로드 (.html)",
    data=html_report_smoothing.encode('utf-8'),
    file_name="장대케이슨_파력평활화_자동산정_보고서.html",
    mime="text/html",
    use_container_width=True
)
