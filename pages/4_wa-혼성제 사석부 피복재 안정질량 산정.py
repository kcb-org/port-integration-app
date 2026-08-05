import streamlit as st
import math
import os
import urllib.request
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import base64
import re

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

# 이미지 파일을 Base64로 인코딩하는 함수 (HTML 보고서용)
def get_image_base64(filepath):
    try:
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        return ""

# =====================================================================
# ★ 공학 계산 엔진
# =====================================================================
class GravityArmorCalculator:
    def __init__(self, gamma_w):
        self.gamma_w = gamma_w  
        self.g = 9.81        

    def calc_L(self, T, d):
        L0 = (self.g * T**2) / (2 * math.pi)
        L = L0
        for _ in range(100):
            kd = 2 * math.pi * d / L
            if kd > 20: 
                break
            L_new = L0 * math.tanh(kd)
            if abs(L_new - L) < 0.001:
                break
            L = L_new
        return L

    # [결정론적 방법] 기존 수식 및 보정 로직 (100% 원본 유지)
    def calc_tanimoto_corrected(self, H, T, h_prime, l, beta, alpha_s, gamma_r, armor_type, relative_freeboard_type, B_m, hc):
        L_prime = self.calc_L(T, h_prime)
        bm_l_ratio = B_m / L_prime if L_prime > 0 else 0
        beta_rad = math.radians(beta)
        
        # 파형경사 sd 산정
        sd = (2 * math.pi * h_prime) / (self.g * (T**2))
        
        param = 4 * math.pi * h_prime / L_prime
        K1 = param / math.sinh(param) if math.sinh(param) != 0 else 1.0
        
        term1_k2 = alpha_s * (math.sin(beta_rad)**2) * (math.cos(2 * math.pi * l * math.cos(beta_rad) / L_prime)**2)
        term2_k2 = (math.cos(beta_rad)**2) * (math.sin(2 * math.pi * l * math.cos(beta_rad) / L_prime)**2)
        K2_B = max(term1_k2, term2_k2)
        
        K = K1 * K2_B
        if K <= 0.0001:  
            K = 0.0001
            
        # 상대여유고 R 자동 계산
        R = hc / H if H != 0 else 0
        
        # 상세 계산 과정을 포함한 보정계수(gamma_T) 분기식 적용
        if R <= 0.6:
            gamma_T = 1.0
            formula_str = r"1.00 \quad \text{(조건: } R \le 0.6 \text{)}"
        else:
            if armor_type == "피복석":
                if 0 <= beta <= 30:
                    val = 5.169 * sd + 0.427
                    gamma_T = min(val, 1.0)
                    formula_str = rf"\min(5.169 s_d + 0.427,\ 1.0) = \min(5.169 \times {sd:.4f} + 0.427,\ 1.0) = \min({val:.4f},\ 1.0)"
                elif 30 < beta <= 60:
                    val = 2.172 * sd + 0.682
                    gamma_T = min(val, 1.0)
                    formula_str = rf"\min(2.172 s_d + 0.682,\ 1.0) = \min(2.172 \times {sd:.4f} + 0.682,\ 1.0) = \min({val:.4f},\ 1.0)"
                else:
                    gamma_T = 1.0
                    formula_str = r"1.00 \quad \text{(적용 각도 범위 외)}"
            elif armor_type == "테트라포드":
                if 0 <= beta <= 30:
                    val = 5.444 * sd + 0.462
                    gamma_T = min(val, 1.0)
                    formula_str = rf"\min(5.444 s_d + 0.462,\ 1.0) = \min(5.444 \times {sd:.4f} + 0.462,\ 1.0) = \min({val:.4f},\ 1.0)"
                elif 30 < beta <= 60:
                    val = 3.177 * sd + 0.696
                    gamma_T = min(val, 1.0)
                    formula_str = rf"\min(3.177 s_d + 0.696,\ 1.0) = \min(3.177 \times {sd:.4f} + 0.696,\ 1.0) = \min({val:.4f},\ 1.0)"
                else:
                    gamma_T = 1.0
                    formula_str = r"1.00 \quad \text{(적용 각도 범위 외)}"
            elif armor_type == "트라이포드":
                if 0 <= beta <= 30:
                    val = 1.797 * sd + 0.685
                    gamma_T = min(val, 1.0)
                    formula_str = rf"\min(1.797 s_d + 0.685,\ 1.0) = \min(1.797 \times {sd:.4f} + 0.685,\ 1.0) = \min({val:.4f},\ 1.0)"
                else:
                    gamma_T = 1.0
                    formula_str = r"1.00 \quad \text{(적용 각도 범위 외)}"
            else:
                gamma_T = 1.0
                formula_str = "1.00"
                
        # 0.6 < R < 1.0 구간에 대한 텍스트 처리
        if 0.6 < R < 1.0:
            formula_str += r" \quad \text{(안전측 보수적용)}"

        term_a = ((1 - K) / (K**(1/3))) * (h_prime / H)
        term_b = (((1 - K)**2) / (K**(1/3))) * (h_prime / H)
        
        Ns_calc = 1.3 * term_a + 1.8 * math.exp(-1.5 * term_b)
        Ns_inner = max(1.8, Ns_calc)
        Ns = gamma_T * Ns_inner
        
        Sr = gamma_r / self.gamma_w
        M_final = (gamma_r * H**3) / ((Ns**3) * ((Sr - 1)**3))
        V_final = M_final / gamma_r
        
        return L_prime, bm_l_ratio, param, K1, K2_B, K, term_a, term_b, Ns_calc, Ns_inner, gamma_T, Ns, Sr, M_final, V_final, R, sd, formula_str

    # [신뢰성 설계법] 추가 수식 전개용 계산 엔진
    def calc_tanimoto_reliability(self, H, T, h_prime, l, beta, alpha_s, gamma_r, armor_type, B_m, hc, pf, DN, N_waves):
        L_prime = self.calc_L(T, h_prime)
        bm_l_ratio = B_m / L_prime if L_prime > 0 else 0
        beta_rad = math.radians(beta)
        sd = (2 * math.pi * h_prime) / (self.g * (T**2))
        
        param = 4 * math.pi * h_prime / L_prime
        K1 = param / math.sinh(param) if math.sinh(param) != 0 else 1.0
        term1_k2 = alpha_s * (math.sin(beta_rad)**2) * (math.cos(2 * math.pi * l * math.cos(beta_rad) / L_prime)**2)
        term2_k2 = (math.cos(beta_rad)**2) * (math.sin(2 * math.pi * l * math.cos(beta_rad) / L_prime)**2)
        K2_B = max(term1_k2, term2_k2)
        K = K1 * K2_B
        if K <= 0.0001: K = 0.0001
            
        R = hc / H if H != 0 else 0
        
        if R <= 0.6:
            gamma_T = 1.0
        else:
            if armor_type == "피복석":
                if 0 <= beta <= 30: gamma_T = min(5.169 * sd + 0.427, 1.0)
                elif 30 < beta <= 60: gamma_T = min(2.172 * sd + 0.682, 1.0)
                else: gamma_T = 1.0
            elif armor_type == "테트라포드":
                if 0 <= beta <= 30: gamma_T = min(5.444 * sd + 0.462, 1.0)
                elif 30 < beta <= 60: gamma_T = min(3.177 * sd + 0.696, 1.0)
                else: gamma_T = 1.0
            elif armor_type == "트라이포드":
                if 0 <= beta <= 30: gamma_T = min(1.797 * sd + 0.685, 1.0)
                else: gamma_T = 1.0
            else:
                gamma_T = 1.0

        term_a = ((1 - K) / (K**(1/3))) * (h_prime / H)
        term_b = (((1 - K)**2) / (K**(1/3))) * (h_prime / H)
        T_term = 1.3 * term_a + 1.8 * math.exp(-1.5 * term_b)
        
        # 해설 표 4.2-12 하중저항계수 매핑
        pf_factors = {
            45.0: (0.98, 1.01, 1.00),
            40.0: (0.96, 1.02, 1.00),
            20.0: (0.87, 1.07, 1.00),
            10.0: (0.80, 1.11, 1.00),
            5.0:  (0.75, 1.14, 1.00)
        }
        gamma_R, gamma_S, gamma_m = pf_factors.get(pf, (1.0, 1.0, 1.0))
        
        Sr = gamma_r / self.gamma_w
        Delta = Sr - 1
        
        damage_factor = (DN * math.exp(-0.3 * (1 - 500 / N_waves))) ** 0.25
        denominator = gamma_R * gamma_T * Delta * damage_factor * T_term
        
        if denominator <= 0:
            Dn = 0
            M_final = 0
            V_final = 0
        else:
            Dn = (gamma_m * gamma_S * H) / denominator
            M_final = gamma_r * (Dn ** 3)
            V_final = M_final / gamma_r
            
        return L_prime, bm_l_ratio, K, term_a, term_b, T_term, gamma_T, Sr, Delta, damage_factor, Dn, M_final, V_final, gamma_R, gamma_S, gamma_m, sd, R

    def calc_madrigal(self, H, h_b, h_s, Nod, gamma_r):
        Ns = (5.8 * (h_b / h_s) - 0.6) * (Nod**0.19)
        Sr = gamma_r / self.gamma_w
        M = (gamma_r * H**3) / ((Ns**3) * ((Sr - 1)**3))
        V = M / gamma_r
        return Ns, Sr, M, V

    def calc_brebner(self, H, Ns3, gamma_r):
        Sr = gamma_r / self.gamma_w
        M = (gamma_r * H**3) / (Ns3 * ((Sr - 1)**3))
        V = M / gamma_r
        return Sr, M, V

# =====================================================================
# ★ 앱 레이아웃 시작
# =====================================================================
st.set_page_config(page_title="혼성제 사석부 피복재 안정질량 산정", page_icon="🧱", layout="wide")

st.title("혼성제 사석부 피복재 안정질량 산정식")

# ----------------------------------------------------
# 0. 사이드바 공통 입력 및 설계법 분기 제어
# ----------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설계 방법 선택")
    design_method = st.radio("방법 분기", ["결정론적 설계법", "신뢰성 설계법"], label_visibility="collapsed")
    st.markdown("---")
    st.write("**제작:** [다온기술(주), 김창보, 이종태]")
    st.write("**기반:** [혼성제 사석부 피복재 안정질량 산정 시스템]")
    st.markdown("---")

    st.header("🌊 1. 공통 설계 파랑 및 수심")
    Hs = st.number_input("설계파고 H1/3 (m)", value=8.60, step=0.1)
    Tz = st.number_input("설계주기 T1/3 (sec)", value=10.83, step=0.1)
    hs = st.number_input("구조물 전면수심 hs (m)", value=20.70, step=0.1)
    hc = st.number_input("마루높이 hc (=Rc) (m)", value=2.00, step=0.1, help="상대여유고 산정용")
    
    # 여유고 R 자동 계산 및 인덱스 처리용 분기
    R_val = hc / Hs if Hs != 0 else 0
    if R_val <= 0.6:
        cond_idx = 0
    elif R_val >= 1.0:
        cond_idx = 2
    else:
        cond_idx = 1
        
    st.info(f"💡 자동계산 상대여유고 $R = h_c / H_{{1/3}} = {R_val:.3f}$")
    
    st.markdown("---")
    st.header("🪨 2. 공통 재료 물성치")
    gamma_rock = st.number_input("피복재 단위중량 γr (kN/m³)", value=26.0, step=0.1)
    gamma_w = st.number_input("해수 단위중량 γw (kN/m³)", value=10.1, step=0.1)

    if design_method == "신뢰성 설계법":
        st.markdown("---")
        st.header("📊 3. 신뢰성 설계 인자")
        pf = st.selectbox("목표파괴확률 Pf (%)", [45.0, 40.0, 20.0, 10.0, 5.0], index=0)
        DN = st.number_input("피해율 DN", value=1.0, step=0.1, help="통상 1%인 경우 1 적용")
        N_waves = st.number_input("작용파수 N", value=500, step=10)


# =====================================================================
# ★ 분기 1: 결정론적 설계법 (원본 앱 100% 완전 복원)
# =====================================================================
if design_method == "결정론적 설계법":

    # 1. 피복재 산정 공식 메커니즘 및 기호 설명
    st.header("1. 피복재 산정 공식 메커니즘 및 기호 설명")
    st.markdown("""
    **[KDS 64 10 07, 항만설계기준 내용]**
    * 다까하시(高橋) 등 은(1990)은 다니모토(谷本) 등(1982) 제안식에서 사석부 부근의 유속, 파향 등의 영향을 고려한 확장 다니모토(谷本)식을 제안하였다.   
    * 혼성제 사석부의 피복석 안정질량을 산정하는 확장 다니모토식은 피복석을 대상으로 상대여유고($R = R_C / H_{1/3}$, $R_C$는 정수면으로부터 마루까지의 여유고, $H_{1/3}$는 유의파고)가 $R = 0.6$이고, 혼성제 사석부의 경사가 1 : 2 또는 1 : 3인 조건에서 수행된 수리모      형실험 결과를 바탕으로 제안된 식으로서 혼성제의 상대여유고가 낮아 월파를 상당히 허용하는 조건에 해당된다.    
    * 따라서, 월파 등을 저감시키기 위해 상대여유고를 높게 하는 경우에는 혼성제 전면에서 중복파가 더 크게 발생하므로 혼성제 사석부의 피복석은 확장 다니모토식으로 산정된 질량보다 더 큰 질량이 필요할 수 있다.  
    * 해양수산부 해양수산과학기술진흥원 은 (2019) , 월파 등의 저감을 위해 혼성제의 상대여유고를 높게 하고, 사석부의 피복재로 인공블록이 많이 사용되는 점을 감안하여 수리모형실험을 통해 확장 다니모토식을 보완할 수 있는 보정계수를 제안하였다. 
    * 제안된 보정계수는 사석부 피복재로 피복석, 테트라포드, 트라이포드(tripod)를 사용하고 사석부의 경사를 1 : 1.5 하여 불규칙파를 적용한 수리모형실험 결과를 바탕으로 한 것이다.   
    * 그러나 해양수산부, 해양수산과학기술진흥원(2019)이 제안한 보정계수를 이용하여 혼성제 사석부의 피복재 안정질량을 산정하더라도 혼성제의 제체 형상, 수심, 파랑, 블록의 형상, 쌓는 방법 등에 따라 안정성이 다르므로 수리모형실험으로 검토하는 것이 바람직하다. 
    """)
    st.subheader("가. 확장다니모토 보정식 (해양수산부, 해양수산과학기술진흥원, 2019)")
    st.markdown("""
    **[특징 및 장단점]**
    * **주요 특징:** 파동의 간섭 및 입사 방향을 고려하는 흐름 계수($\kappa$)를 적용하며, 월파가 발생하는 조건(저여유고)과 그렇지 않은 조건을 분리하여 보정계수를 다르게 적용합니다.
    * **장점 (Pros):** 파향, 파장, 수심, 월파 여부 등 해상 환경의 물리적 특성을 가장 정밀하고 종합적으로 반영하며, 국내 설계기준(KDS)에 명시되어 실무 설계 시 신뢰성이 높습니다.
    * **단점 (Cons):** 파장($L'$)을 구하기 위해 반복 계산이 필요하고 수식 전개 과정이 복잡합니다. 마운드 어깨폭이 넓은 경우($B_M/L' \ge 0.25$) 적용성에 한계가 있습니다.
    """)
    try:
        st.image("혼성제의 표준적인 단면과 기호.png", caption="혼성제의 표준적인 단면과 기호 정의", width=650)
    except FileNotFoundError:
        st.warning("'혼성제의 표준적인 단면과 기호.png' 파일이 필요합니다.")
    st.markdown("항만 및 어항 설계기준에 명시된 안정계수 $N_S$ 산출 및 상대여유고 보정계수($\\gamma_T$)가 직접 반영된 공식입니다.")
    st.latex(r"N_S = \gamma_T \cdot \left[ \max \left\{ 1.8, 1.3 \frac{1-\kappa}{\kappa^{1/3}} \frac{h'}{H_{1/3}} + 1.8 \exp \left[ -1.5 \frac{(1-\kappa)^2}{\kappa^{1/3}} \frac{h'}{H_{1/3}} \right] \right\} \right] \quad ; \quad B_M/L' < 0.25")
    st.latex(r"M = \frac{\gamma_r \cdot H_{1/3}^3}{N_S^3 (S_r - 1)^3}")
    st.markdown(r"""
    **[기호 설명 및 적용 조건]**
    * $M$: 피복재의 안정을 확보하기 위한 최종 소요질량 (kN)
    * $N_S$: 혼성제 사석부 피복재 안정계수
    * $\kappa$: 파동의 중복 및 입사방향 조건 인자 ($\kappa = \kappa_1 \times (\kappa_2)_B$)
    * $L'$: 기초사석 마루 수심 $h'$에서의 설계 파장 (m)
    * $S_r$: 해수에 대한 피복재의 설계 상대 비중 ($\gamma_r / \gamma_w$)
    * $B_M$: 직립부 전면 사석 마운드 어깨폭 (m) (적용 조건: $B_M / L' < 0.25$)
    * $\gamma_T$: 상대여유고($R=h_c/H_{1/3}$) 및 피복재 종류에 따른 보정계수
      * (가) 상대여유고($R$)가 $R \le 0.6$ 이고 피복재가 피복석인 경우는 $\gamma_T = 1.0$ ($0^\circ \le \beta \le 60^\circ$ 범위)
      * (나) 상대여유고($R$)가 $R \ge 1.0$ 이고 피복재가 피복석인 경우는 $\gamma_T = 5.169s_d + 0.427$, $(\gamma_T)_{max} = 1.0$ ($0^\circ \le \beta \le 30^\circ$ 범위), $\gamma_T = 2.172s_d + 0.682$, $(\gamma_T)_{max} = 1.0$ ($30^\circ \le \beta \le 60^\circ$ 범위)
      * (다) 상대여유고($R$)가 $R \ge 1.0$ 이고 피복재가 테트라포드인 경우는 $\gamma_T = 5.444s_d + 0.462$, $(\gamma_T)_{max} = 1.0$ ($0^\circ \le \beta \le 30^\circ$ 범위), $\gamma_T = 3.177s_d + 0.696$, $(\gamma_T)_{max} = 1.0$ ($30^\circ \le \beta \le 60^\circ$ 범위)
      * (라) 상대여유고($R$)가 $R \ge 1.0$ 이고 피복재가 트라이포드인 경우는 $\gamma_T = 1.797s_d + 0.685$, $(\gamma_T)_{max} = 1.0$ ($0^\circ \le \beta \le 30^\circ$ 범위)
      * ※ 여기서 $s_d = 2\pi h' / (g(T_{1/3})^2)$ 이며, $T_{1/3}$은 유의파 주기임. 상대여유고($R$) $0.6 < R < 1.0$ 인 경우에는 수리모형실험으로 안정질량을 산정하는 것이 바람직하며 피복재 안정확보 측면에서 $R \ge 1.0$ 의 보정계수 사용을 고려해 볼 수 있다.
    """)
    st.divider()

    st.subheader("나. Madrigal & Valdes 식")
    st.markdown("""
    **[특징 및 장단점]**
    * **주요 특징:** 구조물이 입을 수 있는 피해 정도($N_{od}$)를 초기 피해, 허용 피해 등으로 설계자가 직접 설정하여 질량을 역산합니다.
    * **장점 (Pros):** 계산식이 매우 직관적이고 간단하며, 설계 수명이나 구조물의 중요도에 따라 허용 피해율을 유연하게 통제할 수 있습니다.
    * **단점 (Cons):** 수심비($h_b/h_s$) 등 적용 기하 조건이 다소 제한적이며, 주기($T$)나 입사각($\\beta$) 같은 주요 파랑 특성이 직접 반영되지 않아 복잡한 해역에서는 정밀도가 떨어집니다.
    """)
    try:
        st.image("Madrigal & Valdes 단면.png", caption="Madrigal & Valdés 공식 적용 단면 조건", width=650)
    except FileNotFoundError:
        st.warning("'Madrigal & Valdes 단면.png' 파일이 필요합니다.")
    st.markdown("불규칙파 및 정면 입사파 실험을 기반으로 2층 피복을 기준으로 산정하는 방식입니다. 기초부 마루 수심이 깊을수록 피복재의 소요 중량은 작게 산정됩니다.")
    st.latex(r"N_s = \left( 5.8 \frac{h_b}{h_s} - 0.6 \right) N_{od}^{0.19}")
    st.latex(r"M = \frac{\gamma_r \cdot H^3}{N_s^3 (S_r - 1)^3}")
    st.markdown("""
    **[기호 설명 및 적용 조건]**
    * $N_s$: 안정수 (Stability Number)
    * $h_b$: 기초부 피복상단의 높이 (마루 수심, m)
    * $h_s$: 구조물 전면수심 (m)
    * $N_{od}$: 피해율 (피복층의 이탈 블록 개수)
      * **0.5**: 초기피해 (피해율 1~3%) $\rightarrow$ *통상적으로 소요중량이 최대가 되는 0.5 적용*
      * **2.0**: 허용피해 (피해율 5~10%)
      * **5.0**: 심각한 피해 (피해율 20~30%)
    * **기타 제약 조건**: $0.5 < h_b / h_s < 0.8$, $7.5 < h_b / D_{n50} < 17.5$, $0.3 < B_m / h_s < 0.55$
    """)
    st.divider()

    st.subheader("다. Brebner & Donnelly 식")
    st.markdown("""
    **[특징 및 장단점]**
    * **주요 특징:** 복잡한 수식 대신 설계 파고와 수심 조건만으로 도표에서 계수를 독취하여 산정합니다.
    * **장점 (Pros):** 수계산이나 현장에서의 개략적인 빠른 검토(Preliminary Design)에 매우 용이하며, 직립벽 전면 세굴 방지용 근고방괴 설계에 직관적입니다.
    * **단점 (Cons):** 도표를 눈대중으로 읽어야 해 독취 오차가 발생할 수 있고, 완전 중복파를 가정하므로 다방향 불규칙파 환경을 현대적인 잣대로 반영하기엔 이론적 한계가 있습니다.
    """)
    try:
        st.image("Brebner & Donnelly 도표.png", caption="Brebner & Donnelly 도표", width=650)
    except FileNotFoundError:
        st.warning("'Brebner & Donnelly 도표.png' 파일이 필요합니다.")
    st.markdown("수심비($d_1/d_s$)에 따른 최소 설계 안정수($N_s^3$)를 도표를 통해 구한 뒤 산정하는 방식입니다. 기초 마운드(Foundation)와 근고공(Toe Protection)의 목적에 따라 적용하는 설계 곡선이 다릅니다.")
    st.latex(r"M = \frac{\gamma_r \cdot H^3}{N_s^3 (S_r - 1)^3}")
    st.markdown("""
    **[기호 설명]**
    * $M$: 사석의 소요 중량 (kN)
    * $\gamma_r$: 사석의 단위 중량 (kN/m³)
    * $N_s^3$: 최소 설계 안정수 (Minimum Design Stability Number). *도표의 Y축 값에서 독취.*
    * $d_s$: 구조물 전면의 총 수심 (m)
    * $d_1$: 사석 기초 마루의 수심 (m)
    * $B$: 턱(Berm)의 폭 (m). *근고방괴 조건에서는 통상 $B = 0.4d_s$ 권장.*
    """)  
    st.divider()
    st.subheader("💡 설계 공식 요약 비교표")
    tbl_compare = """
    | 구분 | 확장 다니모토 보정식 | Madrigal & Valdés 식 | Brebner & Donnelly 식 |
    | :--- | :--- | :--- | :--- |
    | **주요 접근법** | 중복파 이론 + 정밀 기하/환경 보정 | 불규칙파 물리모형 실험 (피해율 기반) | 완전 중복파 도표 (안정수 차트) |
    | **핵심 매개변수** | 유의파고, 주기, 파향, 상대여유고 | 수심비($h_b/h_s$), 피해율($N_{od}$) | 수심비($d_1/d_s$), 안정수($N_s^3$) |
    | **복잡도** | 상 (파장 반복 계산 등 연산량 많음) | 하 (단순 대입식) | 하 (도표 독취) |
    | **실무 적용성** | **국내 표준** | 피해율 통제가 필요한 대안 검토 | 개략 설계 및 단순 근고공 검토 |
    """
    st.markdown(tbl_compare)
    st.markdown("---")

    # 2. 공식별 입력제원
    st.header("2. 공식별 입력제원")

    tab1, tab2, tab3 = st.tabs(["1) 확장다니모토 보정식", "2) Madrigal & Valdés 식", "3) Brebner & Donnelly 식"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            armor_type = st.selectbox("피복재 종류 선택", ["피복석", "테트라포드", "트라이포드"])
            relative_freeboard_type = st.selectbox("상대여유고(hc/H) 범위 선택", [
                "여유고 충분 (hc/H ≤ 0.6)", 
                "저여유고 (0.6 < hc/H < 1.0)", 
                "고여유고 (hc/H ≥ 1.0)"
            ], index=cond_idx)
        with col2:
            h_prime = st.number_input("기초마루 수심 h' (m)", value=17.91, step=0.1)
            B_m = st.number_input("마운드 어깨폭 BM (m)", value=5.0, step=0.1)
            l_val = st.number_input("파 입사 보정거리 ℓ (m)", value=5.0, step=0.5)
            beta = st.number_input("파의 입사각 β (°)", value=0.0, step=1.0)
            alpha_s = st.number_input("수평 보정계수 αs", value=0.45, step=0.01)

    with tab2:
        col3, col4 = st.columns(2)
        with col3:
            h_b = st.number_input("기초부 피복상단 높이 hb (m)", value=13.77, step=0.1)
        with col4:
            Nod = st.number_input("허용 피해율 Nod", value=0.5, step=0.1, help="0.5: 초기피해(권장), 2.0: 허용피해, 5.0: 심각한피해")

    with tab3:
        # 업로드 관련 안내 문구 수정
        st.info("💡 구조물을 선택하면, 내장된 데이터 기준 수심비(d1/ds)에 따른 안정계수(Ns³)를 자동 독취합니다.")
        col5, col6 = st.columns(2)
        with col5:
            d_1 = st.number_input("사석 기초 마루의 수심 d1 (m)", value=16.00, step=0.1)
            bd_type = st.radio("적용 구조물 선택", ["Rubble Foundation", "Rubble Toe Protection"])
            # 파일 업로더(st.file_uploader) 완전히 삭제 완료
        
        # 수심비 자동 계산
        depth_ratio = d_1 / hs if hs > 0 else 0
        Ns3_val = 22.0 # 기본값 초기화
        
        with col6:
            st.markdown(f"**현재 수심비 (d1/ds):** {depth_ratio:.3f}")
            try:
                import pandas as pd
                import numpy as np
                import os
                import matplotlib.pyplot as plt
                import matplotlib.ticker as ticker
                
                df_bd = None
                
                # 내부 파일 자동 인식 (업로드 분기 제거)
                current_dir = os.path.dirname(os.path.abspath(__file__))
                candidates = [
                    "Ns3_Brebner&Donnelly.xlsx - Sheet1.csv", 
                    "Ns3_Brebner&Donnelly.csv", 
                    "Ns3_Brebner&Donnelly.xlsx"
                ]
                for cand in candidates:
                    cand_path = os.path.join(current_dir, cand)
                    if os.path.exists(cand_path):
                        if cand.endswith('.csv'):
                            df_bd = pd.read_csv(cand_path)
                        else:
                            df_bd = pd.read_excel(cand_path)
                        break
                
                if df_bd is not None:
                    x_col = df_bd.columns[0]
                    y_found = df_bd.columns[1]
                    y_toe = df_bd.columns[2] if len(df_bd.columns) > 2 else None
                    
                    df_bd[x_col] = pd.to_numeric(df_bd[x_col], errors='coerce')
                    df_bd[y_found] = pd.to_numeric(df_bd[y_found], errors='coerce')
                    if y_toe is not None:
                        df_bd[y_toe] = pd.to_numeric(df_bd[y_toe], errors='coerce')
                    
                    if bd_type == "Rubble Foundation":
                        df_clean = df_bd.dropna(subset=[x_col, y_found]).sort_values(by=x_col)
                        Ns3_val = float(np.interp(depth_ratio, df_clean[x_col], df_clean[y_found]))
                    else:
                        if y_toe is not None:
                            df_clean = df_bd.dropna(subset=[x_col, y_toe]).sort_values(by=x_col)
                            Ns3_val = float(np.interp(depth_ratio, df_clean[x_col], df_clean[y_toe]))
                        else:
                            st.warning("Toe Protection 데이터가 없습니다. Foundation 기준으로 계산합니다.")
                            df_clean = df_bd.dropna(subset=[x_col, y_found]).sort_values(by=x_col)
                            Ns3_val = float(np.interp(depth_ratio, df_clean[x_col], df_clean[y_found]))
                            
                    st.success(f"**자동 독취된 안정계수 Ns³ ({bd_type} 기준):** {Ns3_val:.2f}")
                else:
                    st.warning("⚠️ 내장된 데이터 파일을 찾을 수 없습니다. 폴더에 파일을 넣거나 값을 수동으로 입력해주세요.")
                    Ns3_val = st.number_input("도표에서 독취한 안정계수 Ns³", value=22.0, step=1.0)
                    
            except Exception as e:
                st.error(f"데이터 처리 중 오류 발생: {e}")
                Ns3_val = st.number_input("도표에서 독취한 안정계수 Ns³", value=22.0, step=1.0)
    
            # 도표 시각화 
            if 'df_clean' in locals() and not df_clean.empty:
                fig, ax = plt.subplots(figsize=(2.4, 3.6))
                
                df_found_plot = df_bd.dropna(subset=[x_col, y_found]).sort_values(by=x_col)
                ax.plot(df_found_plot[x_col], df_found_plot[y_found], 
                        linestyle='-', color='#1e3a8a', linewidth=1.0, label='Foundation')
                
                if y_toe is not None:
                    df_toe_plot = df_bd.dropna(subset=[x_col, y_toe]).sort_values(by=x_col)
                    ax.plot(df_toe_plot[x_col], df_toe_plot[y_toe], 
                            linestyle='-', color='#d9480f', linewidth=1.0, label='Toe Protection')
                
                ax.scatter([depth_ratio], [Ns3_val], color="red", zorder=5, s=20, edgecolors="white", linewidths=0.5) 
                ax.axvline(x=depth_ratio, color="red", linestyle="--", linewidth=0.5, alpha=0.6)
                ax.axhline(y=Ns3_val, color="red", linestyle="--", linewidth=0.5, alpha=0.6)
                
                ax.set_yscale('log')
                ax.set_xlim(0, 0.8)  
                ax.set_ylim(2, 500)  
                
                ax.set_xticks(np.arange(0, 0.81, 0.1))
                ax.tick_params(axis='x', labelsize=5) 
                
                y_ticks = [2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500]
                ax.set_yticks(y_ticks)
                ax.set_yticklabels([str(val) for val in y_ticks], fontsize=5)
                
                ax.grid(True, which='major', color='gray', linestyle='-', linewidth=0.3, alpha=0.4)
                
                ax.set_xlabel('$d_1 / d_s$', fontsize=6) 
                ax.set_ylabel('$N_s^3$', fontsize=6)
                ax.set_title('Brebner & Donnelly ($N_s^3$)', fontsize=7, fontweight='bold', pad=8)
                
                ax.legend(loc='upper left', fontsize=5, borderpad=0.3, labelspacing=0.3, handlelength=1.5)
                
                plt.tight_layout()
                st.pyplot(fig)

    st.markdown("---")

    # 연산 실행
    calc = GravityArmorCalculator(gamma_w=gamma_w)
    results = calc.calc_tanimoto_corrected(
        Hs, Tz, h_prime, l_val, beta, alpha_s, gamma_rock, armor_type, relative_freeboard_type, B_m, hc
    )
    L_prime, bm_l_ratio, param, K1, K2_B, K, term_a, term_b, Ns_calc, Ns_inner, gamma_T, Ns_tanimoto, Sr, M_tanimoto, V_tanimoto, R_calc, sd_calc, formula_str = results

    Ns_mad, _, M_mad, V_mad = calc.calc_madrigal(Hs, h_b, hs, Nod, gamma_rock)
    _, M_breb, V_breb = calc.calc_brebner(Hs, Ns3_val, gamma_rock)
    depth_ratio = d_1 / hs if hs > 0 else 0

    # 3. 공식별 피복재 소요안정질량(M) 최종 비교표
    st.header("3. 공식별 피복재 소요안정질량(M) 최종 비교표")
    st.success("**🧱 각 제안 구조식별 실시간 연산 결과 집계 요약**")

    tbl_html = f"""
    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.1em; background-color: white;" border="1">
        <tr style="background-color: #f1f8ff; color: #1e3a8a;">
            <th style="padding: 12px; border: 1px solid #ddd;">구분</th>
            <th style="padding: 12px; border: 1px solid #ddd;">확장다니모토 보정식</th>
            <th style="padding: 12px; border: 1px solid #ddd;">Madrigal & Valdes 식</th>
            <th style="padding: 12px; border: 1px solid #ddd;">Brebner & Donnelly 식</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>안정계수 (N<sub>S</sub> 또는 N<sub>s</sub><sup>3</sup>)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #1e3a8a;">Ns = {Ns_tanimoto:.3f}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">Ns = {Ns_mad:.3f}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">Ns³ = {Ns3_val:.1f}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>최종 소요질량 (M)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #d9480f; font-size: 1.2em;">{M_tanimoto:,.2f} kN</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{M_mad:,.2f} kN</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{M_breb:,.2f} kN</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>최종 소요체적 (V)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">{V_tanimoto:.3f} m³</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{V_mad:.3f} m³</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{V_breb:.3f} m³</td>
        </tr>
    </table>
    """
    st.markdown(tbl_html, unsafe_allow_html=True)
    st.markdown("---")

    # 4. 수식 전개 및 상세 계산 풀이 과정
    st.header("4. 수식 전개 및 상세 계산 풀이 과정")

    st.subheader("가. 확장다니모토 보정식 상세 연산")
    st.info(f"💡 보정 조건: **{armor_type}** / **{relative_freeboard_type}** (R = {R_calc:.3f}, $s_d$ = {sd_calc:.4f}, 입사각 $\\beta$ = {beta:.1f}°) → 보정계수 $\\gamma_T = {gamma_T:.3f}$ 적용")

    st.markdown("**Step 1: 파형 지표 및 상대 비중 산정**")
    st.markdown(f"설계파 수심 조건 $h' = {h_prime}$ m에서의 파장 반복산정 결과 $L' = {L_prime:.2f}$ m")
    st.latex(rf"S_r = \frac{{\gamma_r}}{{\gamma_w}} = \frac{{{gamma_rock:.2f}}}{{{gamma_w:.2f}}} = {Sr:.3f}")

    st.markdown("**Step 2: 적용범위 조건 검토 ($B_M / L' < 0.25$)**")
    if bm_l_ratio < 0.25:
        st.success(f"✔️ 조건 만족: $B_M / L' = {B_m:.2f} / {L_prime:.2f} = {bm_l_ratio:.3f} < 0.25$")
    else:
        st.error(f"❌ 조건 불만족: $B_M / L' = {B_m:.2f} / {L_prime:.2f} = {bm_l_ratio:.3f} \\ge 0.25$")

    st.markdown("**Step 3: 중복파 인자 $\kappa$ 계수 전개**")
    # 수정: 백슬래시를 하나(\)만 사용하도록 변경
    st.latex(r"\kappa_1 = \frac{4\pi h'/L'}{\sinh(4\pi h'/L')}")
    # 수정: f-string(rf"...") 내에서 백슬래시 하나(\)만 사용
    st.latex(rf"\kappa_1 = \frac{{{param:.4f}}}{{\sinh({param:.4f})}} = {K1:.4f}")
    st.markdown(f"입사각 $\\beta = {beta}^\circ$, 보정거리 $\\ell = {l_val}$ m 대입에 따른 $(\\kappa_2)_B = {K2_B:.4f}$")
    # 수정: f-string(rf"...") 내에서 백슬래시 하나(\)만 사용
    st.latex(rf"\kappa = \kappa_1 \times (\kappa_2)_B = {K1:.4f} \times {K2_B:.4f} = {K:.4f}")

    st.markdown("**Step 4: 파형경사($s_d$) 산정**")
     
    # 1. 기호 공식 (r"..." 유지)
    st.latex(r"s_d = \frac{2\pi h'}{g(T_{1/3})^2}")
    # 2. 숫자 대입 공식 (f"..." 사용 및 모든 LaTeX 명령어 앞에 백슬래시 2개 적용)
    st.latex(f"s_d = \\frac{{2 \\times \\pi \\times {h_prime}}}{{9.81 \\times ({Tz})^2}} = {sd_calc:.4f}")  

    st.markdown("**Step 5: 상대여유고($R$) 및 보정계수($\\gamma_T$) 결정**")
    st.latex(rf"R = \frac{{h_c}}{{H_{{1/3}}}} = \frac{{{hc}}}{{{Hs}}} = {R_calc:.3f}")
    st.markdown(f"해당 구간의 보정 세부 계산 근거 공식:")
    st.latex(rf"\gamma_T = {formula_str} = {gamma_T:.3f}")
    if 0.6 < R_calc < 1.0:
        st.warning("⚠️ 상대여유고가 $0.6 < R < 1.0$ 구간에 해당하므로 수리모형실험 수행이 권장되나, 본 연산에서는 사석부의 구조적 안정성 확보 측면을 고려하여 고여유고($R \\ge 1.0$) 보정계수 기준을 연계 설계치로 보수적 적용하였습니다.")

    st.markdown("**Step 6: 안정계수($N_S$) 결정**")
    st.latex(r"N_S = \gamma_T \cdot \left[ \max \left\{ 1.8, 1.3 \frac{1-\kappa}{\kappa^{1/3}} \frac{h'}{H_{1/3}} + 1.8 \exp \left[ -1.5 \frac{(1-\kappa)^2}{\kappa^{1/3}} \frac{h'}{H_{1/3}} \right] \right\} \right]")
    st.markdown(f"매개변수 1항 치환: $\\frac{{1-\\kappa}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} = {term_a:.4f}$")
    st.markdown(f"매개변수 2항 치환: $\\frac{{(1-\\kappa)^2}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} = {term_b:.4f}$")
    st.latex(rf"\text{{내부 산출값}} = 1.3({term_a:.4f}) + 1.8 \exp[-1.5({term_b:.4f})] = {Ns_calc:.3f}")
    st.markdown(f"$\implies \max(1.8,\ {Ns_calc:.3f}) = {Ns_inner:.3f}$")
    st.markdown(f"$\implies$ 최종 $N_S = \\gamma_T \\times {Ns_inner:.3f} = {gamma_T:.3f} \\times {Ns_inner:.3f} = {Ns_tanimoto:.3f}$")

    st.markdown("**Step 7: 소요질량 산정**")
    st.latex(rf"M = \frac{{{gamma_rock:.2f} \times {Hs}^3}}{{{Ns_tanimoto:.3f}^3 \times ({Sr:.3f} - 1)^3}} = {M_tanimoto:,.2f} \text{{ kN}} \quad (V = {V_tanimoto:.3f} \text{{ m}}^3)")
    st.divider()

    st.subheader("나. Madrigal & Valdes 식 상세 연산")
    st.markdown("**Step 1: 안정계수($N_s$) 결정**")
    st.latex(rf"N_s = \left( 5.8 \times \frac{{{h_b:.2f}}}{{{hs:.2f}}} - 0.6 \right) \times {Nod}^{0.19}")
    st.latex(rf"N_s = \left( 5.8 \times {h_b/hs:.3f} - 0.6 \right) \times {Nod**0.19:.3f} = {Ns_mad:.3f}")
    st.markdown("**Step 2: 소요질량 산정**")
    st.latex(rf"M = \frac{{{gamma_rock:.2f} \times {Hs}^3}}{{{Ns_mad:.3f}^3 \times ({Sr:.3f} - 1)^3}} = {M_mad:,.2f} \text{{ kN}} \quad (V = {V_mad:.3f} \text{{ m}}^3)")
    st.divider()

    st.subheader("다. Brebner & Donnelly 식 상세 연산")
    st.markdown("**Step 1: 수심비 기반 계수 자동 독취 적용**")
    st.markdown(f"수심비 d1/ds = {d_1:.2f} / {hs:.2f} = {depth_ratio:.3f} 조건에 대하여 CSV 도표 데이터 보간을 통해 산출된 최소 안정계수 Ns³ = {Ns3_val:.2f}")
    st.markdown("**Step 2: 소요질량 산정**")
    st.latex(rf"M = \frac{{{gamma_rock:.2f} \times {Hs}^3}}{{{Ns3_val:.2f} \times ({Sr:.3f} - 1)^3}} = {M_breb:,.2f} \text{{ kN}} \quad (V = {V_breb:.3f} \text{{ m}}^3)")

    st.markdown("---")
  
    # 종합 HTML 보고서 동적 생성 및 다운로드 (수식 깨짐 원천 방지 및 기호 안정화)
    img1_base64 = get_image_base64("혼성제의 표준적인 단면과 기호.png")
    img2_base64 = get_image_base64("Madrigal & Valdes 단면.png")
    img3_base64 = get_image_base64("Brebner & Donnelly 도표.png")

    if bm_l_ratio < 0.25:
        chk_class = "success-box"
        chk_text = f"✔️ 조건 만족: B<sub>M</sub> / L' = {B_m:.2f} / {L_prime:.2f} = {bm_l_ratio:.3f} &lt; 0.25"
    else:
        chk_class = "warning-box"
        chk_text = f"❌ 조건 불만족: B<sub>M</sub> / L' = {B_m:.2f} / {L_prime:.2f} = {bm_l_ratio:.3f} &ge; 0.25"

    warning_msg = ""
    if 0.6 < R_calc < 1.0:
        warning_msg = "<div class='warning-box'>⚠️ 상대여유고가 0.6 &lt; R &lt; 1.0 구간에 해당하므로 수리모형실험 수행이 권장되나, 본 연산에서는 사석부의 구조적 안정성 확보 측면을 고려하여 고여유고(R &ge; 1.0) 보정계수 기준을 연계 설계치로 보수적 적용하였습니다.</div>"

    formula_str_escaped = formula_str.replace("\\", "\\\\")

    full_html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>혼성제 사석부 피복재 안정질량 산정 보고서</title>
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
            h3 {{ color: #1e3a8a; background-color: #f8f9fa; padding: 10px; border-left: 5px solid #1e3a8a; margin-top: 25px; }}
            .eq {{ text-align: center; font-size: 1.1em; margin: 15px 0; background: #f4f6f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            .info-box {{ background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin: 15px 0; }}
            .success-box {{ background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; color: #155724; }}
            .warning-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; color: #856404; }}
            img {{ max-width: 80%; height: auto; display: block; margin: 20px auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; text-align: center; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; }}
            th {{ background-color: #f1f8ff; color: #1e3a8a; }}
            ul, p {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <h1>🧱 혼성제 사석부 피복재 안정질량 산정 보고서</h1>
        
        <h2>1. 피복재 산정 공식 메커니즘 및 기호 설명</h2>
        
        <p><b>[KDS 64 10 07, 항만설계기준 내용]</b></p>
        <ul>
            <li>다까하시(高橋) 등 은(1990)은 다니모토(谷本) 등(1982) 제안식에서 사석부 부근의 유속, 파향 등의 영향을 고려한 확장 다니모토(谷本)식을 제안하였다.</li>
            <li>혼성제 사석부의 피복석 안정질량을 산정하는 확장 다니모토식은 피복석을 대상으로 상대여유고(R = R<sub>C</sub> / H<sub>1/3</sub>, R<sub>C</sub>는 정수면으로부터 마루까지의 여유고, H<sub>1/3</sub>는 유의파고)가 R = 0.6이고, 혼성제 사석부의 경사가 1 : 2 또는 1 : 3인 조건에서 수행된 수리모형실험 결과를 바탕으로 제안된 식으로서 혼성제의 상대여유고가 낮아 월파를 상당히 허용하는 조건에 해당된다.</li>
            <li>따라서, 월파 등을 저감시키기 위해 상대여유고를 높게 하는 경우에는 혼성제 전면에서 중복파가 더 크게 발생하므로 혼성제 사석부의 피복석은 확장 다니모토식으로 산정된 질량보다 더 큰 질량이 필요할 수 있다.</li>
            <li>해양수산부 해양수산과학기술진흥원 은 (2019) , 월파 등의 저감을 위해 혼성제의 상대여유고를 높게 하고, 사석부의 피복재로 인공블록이 많이 사용되는 점을 감안하여 수리모형실험을 통해 확장 다니모토식을 보완할 수 있는 보정계수를 제안하였다.</li>
            <li>제안된 보정계수는 사석부 피복재로 피복석, 테트라포드, 트라이포드(tripod)를 사용하고 사석부의 경사를 1 : 1.5 하여 불규칙파를 적용한 수리모형실험 결과를 바탕으로 한 것이다.</li>
            <li>그러나 해양수산부, 해양수산과학기술진흥원(2019)이 제안한 보정계수를 이용하여 혼성제 사석부의 피복재 안정질량을 산정하더라도 혼성제의 제체 형상, 수심, 파랑, 블록의 형상, 쌓는 방법 등에 따라 안정성이 다르므로 수리모형실험으로 검토하는 것이 바람직하다.</li>
        </ul>

        <h3>가. 확장다니모토 보정식 (해양수산부, 해양수산과학기술진흥원, 2019)</h3>
        <p><b>[특징 및 장단점]</b></p>
        <ul>
            <li><b>주요 특징:</b> 파동의 간섭 및 입사 방향을 고려하는 흐름 계수(&kappa;)를 적용하며, 월파가 발생하는 조건(저여유고)과 그렇지 않은 조건을 분리하여 보정계수를 다르게 적용합니다.</li>
            <li><b>장점 (Pros):</b> 파향, 파장, 수심, 월파 여부 등 해상 환경의 물리적 특성을 가장 정밀하고 종합적으로 반영하며, 국내 설계기준(KDS)에 명시되어 실무 설계 시 신뢰성이 높습니다.</li>
            <li><b>단점 (Cons):</b> 파장(L')을 구하기 위해 반복 계산이 필요하고 수식 전개 과정이 복잡합니다. 마운드 어깨폭이 넓은 경우(B<sub>M</sub>/L' &ge; 0.25) 적용성에 한계가 있습니다.</li>
        </ul>
        <img src="{img1_base64}" alt="확장다니모토식 단면도">
        <p>항만 및 어항 설계기준에 명시된 안정계수 N<sub>S</sub> 산출 및 상대여유고 보정계수(&gamma;<sub>T</sub>)가 직접 반영된 공식입니다.</p>
        <div class="eq">$$ N_S = \\gamma_T \\cdot \\left[ \\max \\left\\lbrace 1.8,\\ 1.3 \\frac{{1-\\kappa}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} + 1.8 \\exp \\left[ -1.5 \\frac{{(1-\\kappa)^2}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} \\right] \\right\\rbrace \\right] \\quad ; \\quad B_M/L' < 0.25 $$</div>
        <div class="eq">$$ M = \\frac{{\\gamma_r \\cdot H_{{1/3}}^3}}{{N_S^3 (S_r - 1)^3}} $$</div>
        <p><b>[기호 설명 및 적용 조건]</b></p>
        <ul>
            <li>M: 피복재의 안정을 확보하기 위한 최종 소요질량 (kN)</li>
            <li>N<sub>S</sub>: 혼성제 사석부 피복재 안정계수</li>
            <li>&kappa;: 파동의 중복 및 입사방향 조건 인자 (&kappa; = &kappa;<sub>1</sub> &times; (&kappa;<sub>2</sub>)<sub>B</sub>)</li>
            <li>L': 기초사석 마루 수심 h'에서의 설계 파장 (m)</li>
            <li>S<sub>r</sub>: 해수에 대한 피복재의 설계 상대 비중 (&gamma;<sub>r</sub> / &gamma;<sub>w</sub>)</li>
            <li>B<sub>M</sub>: 직립부 전면 사석 마운드 어깨폭 (m) (적용 조건: B<sub>M</sub> / L' &lt; 0.25)</li>
            <li>&gamma;<sub>T</sub>: 상대여유고(R = h<sub>c</sub>/H<sub>1/3</sub>) 및 피복재 종류에 따른 보정계수</li>
            <li>(가) 상대여유고(R)가 R &le; 0.6 이고 피복재가 피복석인 경우는 &gamma;<sub>T</sub> = 1.0 (0&deg; &le; &beta; &le; 60&deg; 범위)</li>
            <li>(나) 상대여유고(R)가 R &ge; 1.0 이고 피복재가 피복석인 경우는 &gamma;<sub>T</sub> = 5.169s<sub>d</sub> + 0.427, (&gamma;<sub>T</sub>)<sub>max</sub> = 1.0 (0&deg; &le; &beta; &le; 30&deg; 범위)</li>
            <li>(다) 상대여유고(R)가 R &ge; 1.0 이고 피복재가 테트라포드인 경우는 &gamma;<sub>T</sub> = 5.444s<sub>d</sub> + 0.462, (&gamma;<sub>T</sub>)<sub>max</sub> = 1.0 (0&deg; &le; &beta; &le; 30&deg; 범위)</li>
            <li>(라) 상대여유고(R)가 R &ge; 1.0 이고 피복재가 트라이포드인 경우는 &gamma;<sub>T</sub> = 1.797s<sub>d</sub> + 0.685, (&gamma;<sub>T</sub>)<sub>max</sub> = 1.0 (0&deg; &le; &beta; &le; 30&deg; 범위)</li>
            <li>※ 여기서 s<sub>d</sub> = 2&pi;h' / (g(T<sub>1/3</sub>)<sup>2</sup>) 이며, T<sub>1/3</sub>은 유의파 주기임. 상대여유고(R) 0.6 &lt; R &lt; 1.0 인 경우에는 수리모형실험으로 안정질량을 산정하는 것이 권장됨.</li>
        </ul>
        
        <h3>나. Madrigal & Valdes 식</h3>
        <p><b>[특징 및 장단점]</b></p>
        <ul>
            <li><b>주요 특징:</b> 구조물이 입을 수 있는 피해 정도(N<sub>od</sub>)를 초기 피해, 허용 피해 등으로 설계자가 직접 설정하여 질량을 역산합니다.</li>
            <li><b>장점 (Pros):</b> 계산식이 매우 직관적이고 간단하며, 설계 수명이나 구조물의 중요도에 따라 허용 피해율을 유연하게 통제할 수 있습니다.</li>
            <li><b>단점 (Cons):</b> 수심비(h<sub>b</sub>/h<sub>s</sub>) 등 적용 기하 조건이 다소 제한적이며, 주기(T)나 입사각(&beta;) 같은 주요 파랑 특성이 직접 반영되지 않아 복잡한 해역에서는 정밀도가 떨어집니다.</li>
        </ul>
        <img src="{img2_base64}" alt="Madrigal 단면도">
        <div class="eq">$$ N_s = \\left( 5.8 \\frac{{h_b}}{{h_s}} - 0.6 \\right) N_{{od}}^{{0.19}} $$</div>
        <div class="eq">$$ M = \\frac{{\\gamma_r \\cdot H^3}}{{N_s^3 (S_r - 1)^3}} $$</div>
        <p><b>[기호 설명 및 적용 조건]</b></p>
        <ul>
            <li>N<sub>s</sub>: 안정수 (Stability Number)</li>
            <li>h<sub>b</sub>: 기초부 피복상단의 높이 (마루 수심, m)</li>
            <li>h<sub>s</sub>: 구조물 전면수심 (m)</li>
            <li>N<sub>od</sub>: 피해율 (피복층의 이탈 블록 개수) (0.5: 초기피해, 2.0: 허용피해, 5.0: 심각한 피해)</li>
        </ul>
        
        <h3>다. Brebner & Donnelly 식</h3>
        <p><b>[특징 및 장단점]</b></p>
        <ul>
            <li><b>주요 특징:</b> 복잡한 수식 대신 설계 파고와 수심 조건만으로 도표에서 계수를 독취하여 산정합니다.</li>
            <li><b>장점 (Pros):</b> 수계산이나 현장에서의 개략적인 빠른 검토에 매우 용이하며, 직립벽 전면 세굴 방지용 근고방괴 설계에 직관적입니다.</li>
        </ul>
        <img src="{img3_base64}" alt="Brebner 도표">
        <div class="eq">$$ M = \\frac{{\\gamma_r \\cdot H^3}}{{N_s^3 (S_r - 1)^3}} $$</div>
        <p><b>[기호 설명]</b></p>
        <ul>
            <li>M: 사석의 소요 중량 (kN)</li>
            <li>&gamma;<sub>r</sub>: 사석의 단위 중량 (kN/m³)</li>
            <li>N<sub>s</sub><sup>3</sup>: 최소 설계 안정수. 도표의 Y축 값에서 독취.</li>
            <li>d<sub>s</sub>: 구조물 전면의 총 수심 (m), d<sub>1</sub>: 사석 기초 마루의 수심 (m)</li>
        </ul>
        
        <br>
        <h3>💡 설계 공식 요약 비교표</h3>
        <table>
            <tr style="background-color: #f1f8ff; color: #1e3a8a;">
                <th>구분</th><th>확장 다니모토 보정식</th><th>Madrigal & Valdés 식</th><th>Brebner & Donnelly 식</th>
            </tr>
            <tr>
                <td><b>주요 접근법</b></td><td>중복파 이론 + 정밀 기하/환경 보정</td><td>불규칙파 물리모형 실험 (피해율 기반)</td><td>완전 중복파 도표 (안정수 차트)</td>
            </tr>
            <tr>
                <td><b>핵심 매개변수</b></td><td>유의파고, 주기, 파향, 상대여유고</td><td>수심비(h<sub>b</sub>/h<sub>s</sub>), 피해율(N<sub>od</sub>)</td><td>수심비(d<sub>1</sub>/d<sub>s</sub>), 안정수(N<sub>s</sub><sup>3</sup>)</td>
            </tr>
            <tr>
                <td><b>실무 적용성</b></td><td><b>국내 표준</b></td><td>피해율 통제가 필요한 대안 검토</td><td>개략 설계 및 단순 근고공 검토</td>
            </tr>
        </table>
        
        <h2>2. 공식별 피복재 소요안정질량(M) 최종 비교표</h2>
        {tbl_html}
        
        <h2>3. 수식 전개 및 상세 계산 풀이 과정</h2>
        
        <h3>가. 확장다니모토 보정식 상세 연산</h3>
        <div class="info-box">💡 보정 조건: <b>{armor_type}</b> / <b>{relative_freeboard_type}</b> (R = {R_calc:.3f}, s<sub>d</sub> = {sd_calc:.4f}, 입사각 &beta; = {beta:.1f}&deg;) &rarr; 보정계수 &gamma;<sub>T</sub> = {gamma_T:.3f} 적용</div>
        
        <p><b>Step 1: 파형 지표 및 상대 비중 산정</b></p>
        <p>설계파 수심 조건 h' = {h_prime} m에서의 파장 반복산정 결과 L' = {L_prime:.2f} m</p>
        <div class="eq">$$ S_r = \\frac{{\\gamma_r}}{{\\gamma_w}} = \\frac{{{gamma_rock:.2f}}}{{{gamma_w:.2f}}} = {Sr:.3f} $$</div>
        
        <p><b>Step 2: 적용범위 조건 검토 (B<sub>M</sub> / L' &lt; 0.25)</b></p>
        <div class="{chk_class}">{chk_text}</div>

        <p><b>Step 3: 중복파 인자 &kappa; 계수 전개</b></p>
        <div class="eq">$$ \\kappa_1 = \\frac{{4\\pi h'/L'}}{{\\sinh(4\\pi h'/L')}} = \\frac{{{param:.4f}}}{{\\sinh({param:.4f})}} = {K1:.4f} $$</div>
        <p>입사각 &beta; = {beta}&deg;, 보정거리 &#8467; = {l_val} m 대입에 따른 (&kappa;<sub>2</sub>)<sub>B</sub> = {K2_B:.4f}</p>
        <div class="eq">$$ \\kappa = \\kappa_1 \\times (\\kappa_2)_B = {K1:.4f} \\times {K2_B:.4f} = {K:.4f} $$</div>
        
        <p><b>Step 4: 파형경사(s<sub>d</sub>) 산정</b></p>
        <div class="eq">$$ s_d = \\frac{{2\\pi h'}}{{g(T_{{1/3}})^2}} = \\frac{{2 \\times \\pi \\times {h_prime}}}{{9.81 \\times ({Tz})^2}} = {sd_calc:.4f} $$</div>

        <p><b>Step 5: 상대여유고(R) 및 보정계수(&gamma;<sub>T</sub>) 결정</b></p>
        <div class="eq">$$ R = \\frac{{h_c}}{{H_{{1/3}}}} = \\frac{{{hc}}}{{{Hs}}} = {R_calc:.3f} $$</div>
        <p>해당 구간의 보정 세부 계산 근거 공식:</p>
        <div class="eq">$$ \\gamma_T = {formula_str_escaped} = {gamma_T:.3f} $$</div>
        {warning_msg}

        <p><b>Step 6: 안정계수(N<sub>S</sub>) 결정</b></p>
        <div class="eq">$$ N_S = \\gamma_T \\cdot \\left[ \\max \\left\\lbrace 1.8,\\ 1.3 \\frac{{1-\\kappa}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} + 1.8 \\exp \\left[ -1.5 \\frac{{(1-\\kappa)^2}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} \\right] \\right\\rbrace \\right] $$</div>
        <p>매개변수 1항 치환:</p>
        <div class="eq">$$ \\frac{{1-\\kappa}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} = {term_a:.4f} $$</div>
        <p>매개변수 2항 치환:</p>
        <div class="eq">$$ \\frac{{(1-\\kappa)^2}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} = {term_b:.4f} $$</div>
        <div class="eq">$$ \\text{{내부 산출값}} = 1.3({term_a:.4f}) + 1.8 \\exp[-1.5({term_b:.4f})] = {Ns_calc:.3f} $$</div>
        <div class="eq">$$ \\implies \\max(1.8,\\ {Ns_calc:.3f}) = {Ns_inner:.3f} $$</div>
        <div class="eq">$$ \\implies \\text{{최종 }} N_S = \\gamma_T \\times {Ns_inner:.3f} = {gamma_T:.3f} \\times {Ns_inner:.3f} = {Ns_tanimoto:.3f} $$</div>
        
        <p><b>Step 7: 소요질량 산정</b></p>
        <div class="eq">$$ M = \\frac{{{gamma_rock:.2f} \\times {Hs}^3}}{{{Ns_tanimoto:.3f}^3 \\times ({Sr:.3f} - 1)^3}} = {M_tanimoto:,.2f} \\text{{ kN}} \\quad (V = {V_tanimoto:.3f} \\text{{ m}}^3) $$</div>

        <hr>

        <h3>나. Madrigal & Valdes 식 상세 연산</h3>
        <p><b>Step 1: 안정계수(N<sub>s</sub>) 결정</b></p>
        <div class="eq">$$ N_s = \\left( 5.8 \\times \\frac{{{h_b:.2f}}}{{{hs:.2f}}} - 0.6 \\right) \\times {Nod}^{{0.19}} = \\left( 5.8 \\times {h_b/hs:.3f} - 0.6 \\right) \\times {Nod**0.19:.3f} = {Ns_mad:.3f} $$</div>
        <p><b>Step 2: 소요질량 산정</b></p>
        <div class="eq">$$ M = \\frac{{{gamma_rock:.2f} \\times {Hs}^3}}{{{Ns_mad:.3f}^3 \\times ({Sr:.3f} - 1)^3}} = {M_mad:,.2f} \\text{{ kN}} \\quad (V = {V_mad:.3f} \\text{{ m}}^3) $$</div>

        <hr>

        <h3>다. Brebner & Donnelly 식 상세 연산</h3>
        <p><b>Step 1: 수심비 기반 계수 자동 독취 적용</b></p>
        <p>수심비 d<sub>1</sub>/d<sub>s</sub> = {d_1:.2f} / {hs:.2f} = {depth_ratio:.3f} 조건에 대하여 데이터 보간을 통해 산출된 최소 안정계수 N<sub>s</sub><sup>3</sup> = {Ns3_val:.2f}</p>
        <p><b>Step 2: 소요질량 산정</b></p>
        <div class="eq">$$ M = \\frac{{{gamma_rock:.2f} \\times {Hs}^3}}{{{Ns3_val:.2f} \\times ({Sr:.3f} - 1)^3}} = {M_breb:,.2f} \\text{{ kN}} \\quad (V = {V_breb:.3f} \\text{{ m}}^3) $$</div>

    </body>
    </html>
    """

    st.download_button(
        label="💾 현재 화면 전체 보고서 다운로드 (.html)",
        data=full_html_report.encode('utf-8'),
        file_name="혼성제_사석부_피복재_안정질량_통합보고서.html",
        mime="text/html",
        help="클릭하시면 현재 화면에 표출된 공식, 이미지 단면도, 비교표 및 풀이 과정이 모두 포함된 HTML 보고서를 저장합니다.",
        use_container_width=True
    )
# =====================================================================
# ★ 분기 2: 신뢰성 설계법 (확장 다니모토 보정식 독립 실행)
# =====================================================================
else:
    st.header("1. 신뢰성 설계법 공식 메커니즘 및 기호 설명(확장 다니모토 보정식)")
    st.markdown("항만 및 어항 설계기준 해설(KDS 64 10 07)에 제시된 신뢰성 설계법 기반의 수식 인자 연산 체계입니다.")
    st.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k")
    st.latex(r"R_k = \gamma_T \cdot \Delta D_n \left[ D_N \cdot e^{-0.3(1-500/N)} \right]^{0.25} \cdot \left[ 1.3 \frac{1-\kappa}{\kappa^{1/3}} \frac{h'}{H_{1/3}} + 1.8 \exp \left( -1.5 \frac{(1-\kappa)^2}{\kappa^{1/3}} \frac{h'}{H_{1/3}} \right) \right]")
    st.latex(r"S_k = H_{1/3}")
    
    st.markdown("""
    **[기호 설명]**
    * $h'$: 기초사석 마운드(피복재 제외)의 마루수심(m)
    * $D_N$: 피해율 (= 1%)
    * $D_n$: 피복재의 대표 공칭직경 (= $(M/\\rho_r)^{1/3}$, m)
    * $M$: 피복재 소요 질량 (kN)
    * $N$: 작용 파수 (= 500)
    * $\Delta$: 해수 대비 피복재의 설계 상대 비중차 ($S_r - 1$)
    * $\kappa$: 중복파 조건 인자, $\gamma_T$: 상대여유고 보정계수
    * $\gamma_R, \gamma_S, \gamma_m$: 목표 파괴확률별 설계 하중저항계수 (KDS 해설 표 4.2-12 기준 반영)
    """)
    
    try:
        st.image("스도등하중저항계수.png", caption="해설 표 4.2-12 스도(須藤) 등(1995)의 식에 의한 혼성제의 피복석 질량산정에 사용하는 하중저항계수", width=800)
    except FileNotFoundError:
        st.warning("'스도등하중저항계수.png' 파일이 필요합니다. 첨부하신 이미지를 소스코드와 동일한 폴더에 해당 이름으로 저장해 주세요.")
        
    st.divider()
    
    st.header("2. 공식별 입력제원 (신뢰성 설계 전용)")
    col1, col2 = st.columns(2)
    with col1:
        armor_type = st.selectbox("피복재 종류 선택", ["피복석", "테트라포드", "트라이포드"], key="rel_armor")
        relative_freeboard_type = st.selectbox("상대여유고(hc/H) 범위 선택", [
            "여유고 충분 (hc/H ≤ 0.6)", 
            "저여유고 (0.6 < hc/H < 1.0)", 
            "고여유고 (hc/H ≥ 1.0)"
        ], index=(0 if R_val<=0.6 else (2 if R_val>=1.0 else 1)), key="rel_rf")
    with col2:
        h_prime = st.number_input("기초마루 수심 h' (m)", value=17.91, step=0.1, key="rel_hp")
        B_m = st.number_input("마운드 어깨폭 BM (m)", value=5.0, step=0.1, key="rel_bm")
        l_val = st.number_input("파 입사 보정거리 ℓ (m)", value=5.0, step=0.5, key="rel_l")
        beta = st.number_input("파의 입사각 β (°)", value=0.0, step=1.0, key="rel_beta")
        alpha_s = st.number_input("수평 보정계수 αs", value=0.45, step=0.01, key="rel_alpha")
        
    st.markdown("---")
    
    # 신뢰성 엔진 연산 수행
    calc = GravityArmorCalculator(gamma_w=gamma_w)
    L_prime, bm_l_ratio, K, term_a, term_b, T_term, gamma_T, Sr, Delta, damage_factor, Dn, M_rel, V_rel, gamma_R, gamma_S, gamma_m, sd_calc, R_calc = calc.calc_tanimoto_reliability(Hs, Tz, h_prime, l_val, beta, alpha_s, gamma_rock, armor_type, B_m, hc, pf, DN, N_waves)
    
    st.header("3. 신뢰성 설계법 소요안정질량(M) 연산 결과")
    st.success(f"**🧱 확장다니모토 보정식 (신뢰성 설계) 최종 소요질량: {M_rel:,.2f} kN (소요체적: {V_rel:.3f} m³)**")
    
    tbl_rel_html = f"""
    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.1em; background-color: white;" border="1">
        <tr style="background-color: #f1f8ff; color: #1e3a8a;">
            <th style="padding: 12px; border: 1px solid #ddd;">구분</th>
            <th style="padding: 12px; border: 1px solid #ddd;">확장다니모토 보정식 (신뢰성 설계)</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>하중저항계수 세트</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #1e3a8a;">γ<sub>R</sub> = {gamma_R}, γ<sub>S</sub> = {gamma_S}, γ<sub>m</sub> = {gamma_m} (P<sub>f</sub> = {pf}%)</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>피복재 공칭직경 (D<sub>n</sub>)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #1e3a8a;">Dn = {Dn:.3f} m</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>최종 소요질량 (M)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: #d9480f; font-size: 1.2em;">{M_rel:,.2f} kN</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>최종 소요체적 (V)</b></td>
            <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">{V_rel:.3f} m³</td>
        </tr>
    </table>
    """
    st.markdown(tbl_rel_html, unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("4. 수식 전개 및 상세 계산 풀이 과정 (신뢰성)")
    st.markdown("**Step 1: 목표파괴확률 기반 계수 결정**")
    st.markdown(f"선택한 목표파괴확률 $P_f = {pf}\\%$ 에 의거하여 매핑된 하중저항계수 값: $\gamma_R = {gamma_R}$, $\gamma_S = {gamma_S}$, $\gamma_m = {gamma_m}$")
    
    st.markdown("**Step 2: 주요 파형 특성 및 중복파 조건 연산**")
    st.markdown(f"수심 조건 기반 산출 설계 파장 $L' = {L_prime:.2f}$ m, 계산된 복합 중복파 유효 계수 $\kappa = {K:.4f}$")
    
    st.markdown("**Step 3: 보정계수 및 공식 세부항 분기 연산**")
    st.markdown(f"상대여유고 $R = {R_calc:.3f}$ 및 피복재 [{armor_type}] 조건에 대응하는 설계 보정계수 $\gamma_T = {gamma_T:.3f}$")
    st.latex(rf"\text{{피해율 항 연산값}} = \left[ {DN} \times \exp\left( -0.3 \times \left(1 - \frac{{500}}{{{N_waves}}}\right) \right) \right]^{{{0.25}}} = {damage_factor:.4f}")
    st.latex(rf"\text{{Tanimoto 함수 괄호 항}} = 1.3({term_a:.4f}) + 1.8 \exp[-1.5({term_b:.4f})] = {T_term:.4f}")
    
    st.markdown("**Step 4: 한계 상태 방정식 역산을 통한 공칭 두께 및 중량 도출**")
    st.latex(rf"D_n = \frac{{\gamma_m \cdot \gamma_S \cdot H_{{1/3}}}}{{\gamma_R \cdot \gamma_T \cdot \Delta \cdot (\text{{피해율 항}}) \cdot (\text{{Tanimoto 항}})}} = {Dn:.3f} \text{{ m}}")
    st.latex(rf"M = \gamma_r \cdot D_n^3 = {gamma_rock} \times ({Dn:.3f})^3 = {M_rel:,.2f} \text{{ kN}}")

    # 신뢰성 설계 전용 HTML 보고서 구성 (화면 내용 100% 일치 및 수식 깨짐 방지)
    full_html_report_rel = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>혼성제 사석부 피복재 안정질량 산정 보고서 (신뢰성 설계법)</title>
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
            .eq {{ text-align: center; font-size: 1.1em; margin: 15px 0; background: #f4f6f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; text-align: center; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; }}
            th {{ background-color: #f1f8ff; color: #1e3a8a; }}
            ul, p {{ margin-bottom: 10px; }}
            img {{ max-width: 80%; height: auto; display: block; margin: 20px auto; }}
        </style>
    </head>
    <body>
        <h1>🧱 혼성제 사석부 피복재 안정질량 산정 보고서 (신뢰성 설계법)</h1>
        
        <h2>1. 신뢰성 설계법 공식 메커니즘 및 기호 설명(확장 다니모토 보정식)</h2>
        <p>항만 및 어항 설계기준 해설(KDS 64 10 07)에 제시된 신뢰성 설계법 기반의 수식 인자 연산 체계입니다.</p>
        <div class="eq">$$ \\gamma_R \\cdot R_k \\ge \\gamma_m \\cdot \\gamma_S \\cdot S_k $$</div>
        <div class="eq">$$ R_k = \\gamma_T \\cdot \\Delta D_n \\left[ D_N \\cdot e^{{-0.3(1-500/N)}} \\right]^{{0.25}} \\cdot \\left[ 1.3 \\frac{{1-\\kappa}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} + 1.8 \\exp \\left( -1.5 \\frac{{(1-\\kappa)^2}}{{\\kappa^{{1/3}}}} \\frac{{h'}}{{H_{{1/3}}}} \\right) \\right] $$</div>
        <div class="eq">$$ S_k = H_{{1/3}} $$</div>
        
        <p><b>[기호 설명]</b></p>
        <ul>
            <li>$h'$: 기초사석 마운드(피복재 제외)의 마루수심(m)</li>
            <li>$D_N$: 피해율 (= 1%)</li>
            <li>$D_n$: 피복재의 대표 공칭직경 (= $(M/\\rho_r)^{{1/3}}$, m)</li>
            <li>$M$: 피복재 소요 질량 (kN)</li>
            <li>$N$: 작용 파수 (= 500)</li>
            <li>$\Delta$: 해수 대비 피복재의 설계 상대 비중차 ($S_r - 1$)</li>
            <li>$\kappa$: 중복파 조건 인자, $\gamma_T$: 상대여유고 보정계수</li>
            <li>$\gamma_R, \gamma_S, \gamma_m$: 목표 파괴확률별 설계 하중저항계수 (KDS 해설 표 4.2-12 기준 반영)</li>
        </ul>
        
        <h2>2. 신뢰성 설계 산정 결과표</h2>
        {tbl_rel_html}
        
        <h2>3. 수식 전개 및 상세 계산 풀이 과정 (신뢰성)</h2>
        <p><b>Step 1: 목표파괴확률 기반 계수 결정</b></p>
        <p>선택한 목표파괴확률 $P_f = {pf}\\%$ 에 의거하여 매핑된 하중저항계수 값: $\\gamma_R = {gamma_R}$, $\\gamma_S = {gamma_S}$, $\\gamma_m = {gamma_m}$</p>
        
        <p><b>Step 2: 주요 파형 특성 및 중복파 조건 연산</b></p>
        <p>수심 조건 기반 산출 설계 파장 $L' = {L_prime:.2f}$ m, 계산된 복합 중복파 유효 계수 $\\kappa = {K:.4f}$</p>
        
        <p><b>Step 3: 보정계수 및 공식 세부항 분기 연산</b></p>
        <p>상대여유고 $R = {R_calc:.3f}$ 및 피복재 [{armor_type}] 조건에 대응하는 설계 보정계수 $\\gamma_T = {gamma_T:.3f}$</p>
        <div class="eq">$$ \\text{{피해율 항 연산값}} = \\left[ {DN} \\times \\exp\\left( -0.3 \\times \\left(1 - \\frac{{500}}{{{N_waves}}}\\right) \\right) \\right]^{{0.25}} = {damage_factor:.4f} $$</div>
        <div class="eq">$$ \\text{{Tanimoto 함수 괄호 항}} = 1.3({term_a:.4f}) + 1.8 \\exp[-1.5({term_b:.4f})] = {T_term:.4f} $$</div>
        
        <p><b>Step 4: 한계 상태 방정식 역산을 통한 공칭 두께 및 중량 도출</b></p>
        <div class="eq">$$ D_n = \\frac{{\\gamma_m \\cdot \\gamma_S \\cdot H_{{1/3}}}}{{\\gamma_R \\cdot \\gamma_T \\cdot \\Delta \\cdot (\\text{{피해율 항}}) \\cdot (\\text{{Tanimoto 항}})}} = {Dn:.3f} \\text{{ m}} $$</div>
        <div class="eq">$$ M = \\gamma_r \\cdot D_n^3 = {gamma_rock} \\times ({Dn:.3f})^3 = {M_rel:,.2f} \\text{{ kN}} \\quad (V = {V_rel:.3f} \\text{{ m}}^3) $$</div>
    </body>
    </html>
    """
    
    st.download_button(
        label="💾 현재 화면 전체 보고서 다운로드 (.html)",
        data=full_html_report_rel.encode('utf-8'),
        file_name="혼성제_사석부_피복재_신뢰성설계_통합보고서.html",
        mime="text/html",
        use_container_width=True
    )
