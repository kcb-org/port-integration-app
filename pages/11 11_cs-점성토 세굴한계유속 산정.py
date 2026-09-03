import streamlit as st
import math
import pandas as pd
import io
import base64
import re
import urllib.parse
import concurrent.futures
import textwrap

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

# =====================================================================
# ★ 데이터 및 계산 엔진
# =====================================================================

# [Method 1] 경험적 허용유속 표 데이터
EMPIRICAL_TABLE = {
    "연약한 점토 (Soft Clay)": {"min": 0.6, "max": 0.9, "desc": "다짐이 거의 안 되어 흐름에 쉽게 풀리는 상태"},
    "보통 점토 (Ordinary Clay)": {"min": 1.1, "max": 1.2, "desc": "일반적인 농수로 및 하천 제방의 상태"},
    "단단한 점토 (Stiff Clay)": {"min": 1.2, "max": 1.5, "desc": "압밀이 잘 되어 조밀하고 단단한 상태"},
    "콜로이드성 점토 (Colloidal Clay)": {"min": 1.5, "max": 1.8, "desc": "입자간 화학적 결합력이 극도로 강한 상태"}
}

# [Method 2] Smerdon & Beasley 역산 로직
def calc_smerdon_beasley(pi, n, R):
    tau_c_psf = 0.16 * (pi ** 0.84)
    tau_c_pa = tau_c_psf * 47.88
    gamma_w = 9810
    Vc = (1 / n) * (R ** (1/6)) * math.sqrt(tau_c_pa / gamma_w)
    return tau_c_psf, tau_c_pa, Vc

# [Method 3] Mirtskhoulava 계산 엔진 및 표 데이터 (한글(영어) 번역 반영)
C0_TABLE = {
    '양질 사토 (Loamy Sand)': {
        '0-0.25': {0.45: 10.8, 0.65: 7.85, 0.75: None, 0.85: None, 0.95: None},
        '0.25-0.75': {0.45: 8.83, 0.65: 5.88, 0.75: 2.94, 0.85: None, 0.95: None}
    },
    '양질 점토 (Loamy Clay)': {
        '0-0.25 (저소성, low plasticity)': {0.45: 36.3, 0.65: 30.4, 0.75: 24.5, 0.85: 21.6, 0.95: 18.6},
        '0.25-0.5 (중소성, medium plasticity)': {0.45: 33.3, 0.65: 27.5, 0.75: 22.6, 0.85: 17.7, 0.95: 14.7},
        '0.5-0.75 (고소성, high plasticity)': {0.45: None, 0.65: 24.5, 0.75: 19.6, 0.85: 15.7, 0.95: 13.7}
    },
    '점토 (Clay)': {
        '0-0.25': {0.45: 79.4, 0.65: 66.8, 0.75: 53.0, 0.85: 46.1, 0.95: 40.2},
        '0.25-0.5': {0.45: None, 0.65: 55.9, 0.75: 49.0, 0.85: 42.2, 0.95: 36.3},
        '0.5-0.75': {0.45: None, 0.65: 44.1, 0.75: 40.2, 0.85: 35.3, 0.95: 32.4}
    }
}

def get_c0_value(soil_type, li_range, porosity):
    try:
        return C0_TABLE[soil_type][li_range][porosity]
    except KeyError:
        return None

def generate_c0_html_table(sel_soil, sel_li, sel_poro, manual=False):
    rows = [
        ("양질 사토 (Loamy Sand)", "0-0.25", [10.8, 7.85, "-", "-", "-"]),
        ("양질 사토 (Loamy Sand)", "0.25-0.75", [8.83, 5.88, 2.94, "-", "-"]),
        ("양질 점토 (Loamy Clay)", "0-0.25 (저소성, low plasticity)", [36.3, 30.4, 24.5, 21.6, 18.6]),
        ("양질 점토 (Loamy Clay)", "0.25-0.5 (중소성, medium plasticity)", [33.3, 27.5, 22.6, 17.7, 14.7]),
        ("양질 점토 (Loamy Clay)", "0.5-0.75 (고소성, high plasticity)", ["-", 24.5, 19.6, 15.7, 13.7]),
        ("점토 (Clay)", "0-0.25", [79.4, 66.8, 53.0, 46.1, 40.2]),
        ("점토 (Clay)", "0.25-0.5", ["-", 55.9, 49.0, 42.2, 36.3]),
        ("점토 (Clay)", "0.5-0.75", ["-", 44.1, 40.2, 35.3, 32.4])
    ]
    html = "<table style='width:100%; border-collapse:collapse; text-align:center; font-size:14px; background-color:white; margin-top:10px;' border='1'>"
    html += "<tr style='background-color:#f1f8ff; color:#1e3a8a;'><th rowspan='2' style='padding:8px;'>토질 분류 (Soil Type)</th><th rowspan='2' style='padding:8px;'>액성지수 (Liquidity Index)</th><th colspan='5' style='padding:8px;'>공극율 (Porosity)</th></tr>"
    html += "<tr style='background-color:#f1f8ff; color:#1e3a8a;'><th style='padding:8px;'>0.45</th><th>0.65</th><th>0.75</th><th>0.85</th><th>0.95</th></tr>"
    
    poro_idx_map = {0.45: 0, 0.65: 1, 0.75: 2, 0.85: 3, 0.95: 4}
    sel_p_idx = poro_idx_map.get(sel_poro, -1) if not manual else -1
    
    prev_soil = ""
    for r_soil, r_li, vals in rows:
        html += "<tr>"
        if r_soil != prev_soil:
            rowspan = sum(1 for x in rows if x[0] == r_soil)
            html += f"<td rowspan='{rowspan}'><b>{r_soil}</b></td>"
            prev_soil = r_soil
        html += f"<td>{r_li}</td>"
        for i, val in enumerate(vals):
            is_match = (not manual) and (r_soil == sel_soil) and (r_li == sel_li) and (i == sel_p_idx)
            if is_match:
                html += f"<td style='background-color:#ffeeba; font-weight:bold; color:#d9480f; border:3px solid #d9480f; font-size:1.1em;'>{val}</td>"
            else:
                html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def calc_mirtskhoulava(h, C0, rho, rho_s, d_a):
    g = 9.81
    Cf = 0.035 * C0
    term1 = math.log10(8.8 * h / d_a)
    inner_term = (0.4 / rho) * ((rho_s - rho) * g * d_a + 0.6 * Cf)
    if inner_term < 0: return 0, Cf, term1, 0, inner_term
    term2 = math.sqrt(inner_term)
    Uc = term1 * term2
    return Uc, Cf, term1, term2, inner_term

# =====================================================================
# ★ 앱 레이아웃 시작
# =====================================================================
st.set_page_config(page_title="점성토 한계유속 종합 산정", page_icon="🌊", layout="wide")

st.title("🌊 점성토 세굴 한계유속 종합 산정 프로그램")
st.markdown("**엔지니어를 위한 3가지 한계유속 산정 방법 가이드 및 자동계산 툴**")
st.markdown("사질토(모래)는 '무게와 입경'으로 세굴을 버티지만, 점성토(진흙)는 입자 간의 **물리화학적 결합력(점착력)**으로 버팁니다. 현장의 데이터 보유 상황에 따라 아래 3가지 탭 중 하나를 선택하여 설계하세요.")

# 3가지 산정 방법 비교표 (초급/중급/고급) 추가
comparison_html = """
<table style="width:100%; border-collapse: collapse; text-align: left; margin-top: 15px; margin-bottom: 20px; font-size: 0.95em; border: 1px solid #dee2e6;">
    <tr style="background-color: #f1f8ff; border-bottom: 2px solid #dee2e6; text-align: center; color: #1e3a8a;">
        <th style="padding: 10px; width: 13%;">구분</th>
        <th style="padding: 10px; width: 29%;">[기본] 경험적 허용유속 표</th>
        <th style="padding: 10px; width: 29%;">[중급] 한계소류력 역산법</th>
        <th style="padding: 10px; width: 29%;">[고급] Mirtskhoulava 이론식</th>
    </tr>
    <tr style="border-bottom: 1px solid #dee2e6;">
        <td style="text-align: center; font-weight: bold; background-color: #fcfcfc;">데이터 정밀도</td>
        <td style="padding: 10px; text-align: center;">낮음 (유속을 특정 값이 아닌 범위로 제시)</td>
        <td style="padding: 10px; text-align: center;">보통 (소성지수 PI 측정값 등)</td>
        <td style="padding: 10px; text-align: center;"><span style="color:#d9480f; font-weight:bold;">최고</span> (공극율, 액성지수, 입경 등 다수 변수)</td>
    </tr>
    <tr style="border-bottom: 1px solid #dee2e6;">
        <td style="text-align: center; font-weight: bold; background-color: #fcfcfc;">특징</td>
        <td style="padding: 10px;">과거 수십 년간의 관측 결과를 통계화한 자료 적용</td>
        <td style="padding: 10px;">흙의 측정값(PI)을 기반으로 물리적인 물의 마찰력(소류력)을 계산하여 유속 역추적</td>
        <td style="padding: 10px;">물의 흐름이 진흙 표면을 때려서 입자가 떨어져 나가는 메커니즘을 실제 물리 방정식으로 구현</td>
    </tr>
    <tr style="border-bottom: 1px solid #dee2e6;">
        <td style="text-align: center; font-weight: bold; background-color: #fcfcfc;">실무 신뢰성<br>및 적용</td>
        <td style="padding: 10px;">정밀 데이터가 없는 기본계획 단계 시 <b>가장 보수적이고 안전한 결과를 담보하므로 실무 신뢰성 높음</b></td>
        <td style="padding: 10px;">적은 입력 데이터로도 결과 도출이 가능하여 일반적인 <b>실시설계에서 가장 범용적으로 신뢰받는 방법</b></td>
        <td style="padding: 10px;">정밀 세굴 평가 등에 필수적이나, <b>입력 데이터가 완벽할 때만 높은 신뢰성을 가짐</b> (조건부 신뢰성)</td>
    </tr>
</table>
<div style="font-size: 0.9em; color: #555; margin-bottom: 20px;">
💡 <b>설계 팁:</b> 실무에서는 어느 한 공식을 맹신하기보다, [중급]이나 [고급] 수식으로 도출한 유속이 [기본] 경험적 표의 상식적인 범위를 과도하게 벗어나지 않는지 <b>크로스 체크(Cross-check)</b>하는 것이 가장 안전합니다.
</div>
"""
st.markdown(comparison_html, unsafe_allow_html=True)
st.divider()

# 상단 탭 구성
tab1, tab2, tab3 = st.tabs([
    "1. [기본] 경험적 허용유속 표", 
    "2. [중급] 한계소류력 역산법", 
    "3. [고급] Mirtskhoulava 이론식"
])

# ----------------------------------------------------
# 탭 1: 경험적 허용유속 표 (Fortier & Scobey 원본 데이터)
# ----------------------------------------------------
with tab1:
    st.header("1. 경험적 허용유속 표 활용 (Fortier & Scobey 원본 기준)")
    
    source_html1 = """
    <div style="background-color: #f0f7ff; border: 1px solid #cce5ff; border-left: 5px solid #0056b3; padding: 15px; border-radius: 4px; margin-bottom: 15px; font-size: 0.95em;">
        <div style="font-weight: bold; color: #0056b3; margin-bottom: 8px; font-size: 1.1em;">📖 문헌 출처 및 이론적 배경</div>
        <ul style="margin-bottom: 0; padding-left: 20px; line-height: 1.6;">
            <li><b>논문명 :</b> Permissible Canal Velocities</li>
            <li><b>저 자 :</b> Samuel Fortier, Fred C. Scobey</li>
            <li><b>발행처 :</b> Transactions of the American Society of Civil Engineers (ASCE), Vol. 89, pp. 940-956 (1926)</li>
            <li><b>이론적 배경 :</b> 미국 토목학회(ASCE)에 발표된 원본 연구로, 수로 구성 토질과 흐르는 물의 상태에 따른 최대 허용 유속을 실측 기반 데이터 표로 제시하여 전 세계 공공 설계 지침의 근간이 된 표준 기준입니다.</li>
        </ul>
    </div>
    """
    st.markdown(source_html1, unsafe_allow_html=True)
    
    st.info("💡 **실무 Tip:** 수로 내 유체 성상(부유사 및 소류사 유무)에 따른 허용 유속 변화를 원문 표 그대로 정밀하게 검토할 수 있습니다.")

    FORTIER_SCOBEY_TABLE = {
        "사질 양토 (Sandy loam)": {
            "맑은 물 (Clear Water)": {"ft": 1.75, "ms": 0.53},
            "토사 함유 (Silt-Laden Water)": {"ft": 2.50, "ms": 0.76},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 1.50, "ms": 0.46}
        },
        "미사질 양토 (Silt loam)": {
            "맑은 물 (Clear Water)": {"ft": 2.00, "ms": 0.61},
            "토사 함유 (Silt-Laden Water)": {"ft": 3.00, "ms": 0.91},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 2.00, "ms": 0.61}
        },
        "대양토 (Core loam)": {
            "맑은 물 (Clear Water)": {"ft": 2.25, "ms": 0.69},
            "토사 함유 (Silt-Laden Water)": {"ft": 3.50, "ms": 1.07},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 2.25, "ms": 0.69}
        },
        "가는 모래 (Fine sand)": {
            "맑은 물 (Clear Water)": {"ft": 1.50, "ms": 0.46},
            "토사 함유 (Silt-Laden Water)": {"ft": 2.50, "ms": 0.76},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 1.50, "ms": 0.46}
        },
        "화산재 토양 (Volcanic ash)": {
            "맑은 물 (Clear Water)": {"ft": 2.50, "ms": 0.76},
            "토사 함유 (Silt-Laden Water)": {"ft": 3.50, "ms": 1.07},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 2.00, "ms": 0.61}
        },
        "단단한 점토 (Stiff clay)": {
            "맑은 물 (Clear Water)": {"ft": 3.75, "ms": 1.14},
            "토사 함유 (Silt-Laden Water)": {"ft": 5.00, "ms": 1.52},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 3.00, "ms": 0.91}
        },
        "일반 자갈 토양 (Ordinary gravel)": {
            "맑은 물 (Clear Water)": {"ft": 2.50, "ms": 0.76},
            "토사 함유 (Silt-Laden Water)": {"ft": 4.00, "ms": 1.22},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 3.75, "ms": 1.14}
        },
        "거친 자갈층 (Coarse gravel)": {
            "맑은 물 (Clear Water)": {"ft": 4.00, "ms": 1.22},
            "토사 함유 (Silt-Laden Water)": {"ft": 6.00, "ms": 1.83},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 6.50, "ms": 1.98}
        },
        "세일/단단한 토사 (Shales & Hardpan)": {
            "맑은 물 (Clear Water)": {"ft": 6.00, "ms": 1.83},
            "토사 함유 (Silt-Laden Water)": {"ft": 6.00, "ms": 1.83},
            "모래/자갈 소류사 포함 (Bedload)": {"ft": 5.00, "ms": 1.52}
        }
    }

    # Pandas DataFrame으로 변환하여 표 깨짐 원천 방지
    table_data = []
    for mat, conds in FORTIER_SCOBEY_TABLE.items():
        table_data.append({
            "수로 구성 토질 (Material)": mat,
            "맑은 물 (Clear Water)": f"{conds['맑은 물 (Clear Water)']['ft']:.2f} ft/s ({conds['맑은 물 (Clear Water)']['ms']:.2f} m/s)",
            "토사 함유 (Silt-Laden)": f"{conds['토사 함유 (Silt-Laden Water)']['ft']:.2f} ft/s ({conds['토사 함유 (Silt-Laden Water)']['ms']:.2f} m/s)",
            "모래/자갈 소류사 포함": f"{conds['모래/자갈 소류사 포함 (Bedload)']['ft']:.2f} ft/s ({conds['모래/자갈 소류사 포함 (Bedload)']['ms']:.2f} m/s)"
        })
    df_table = pd.DataFrame(table_data)

    st.subheader("📋 Fortier & Scobey 원본 허용유속 참조표")
    st.table(df_table)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ 수로 조건 선택")
        soil_keys = list(FORTIER_SCOBEY_TABLE.keys())
        default_idx = soil_keys.index("단단한 점토 (Stiff clay)")
        sel_material = st.selectbox("수로 구성 토질 선택", soil_keys, index=default_idx)
        sel_water_cond = st.radio("흐르는 물의 상태 선택", list(FORTIER_SCOBEY_TABLE[sel_material].keys()))
    
    with col2:
        st.subheader("📊 원문 기준 허용 유속 결과")
        res_ft = FORTIER_SCOBEY_TABLE[sel_material][sel_water_cond]["ft"]
        res_ms = FORTIER_SCOBEY_TABLE[sel_material][sel_water_cond]["ms"]
        
        st.success(f"### 허용 유속: {res_ms:.2f} m/s ({res_ft:.2f} ft/s)")
        st.markdown(f"**선택 토질:** {sel_material}")
        st.markdown(f"**수리 성상:** {sel_water_cond}")
        st.markdown("> **이론적 특징:** 토사(Silt)가 적당히 함유된 물은 바닥을 보호하는 점성막을 형성하여 허용유속이 증가하는 반면, 거친 소류사가 포함되면 연마 작용으로 허용유속이 감소합니다.")

# ----------------------------------------------------
# 탭 2: 한계소류력 역산법
# ----------------------------------------------------
with tab2:
    st.header("2. 한계소류력 기반 유속 역산법 (Smerdon & Beasley, 1961)")
    
    # 파란색 박스로 문헌 출처 및 이론적 배경 상세 표출
    source_html2 = """
    <div style="background-color: #f0f7ff; border: 1px solid #cce5ff; border-left: 5px solid #0056b3; padding: 15px; border-radius: 4px; margin-bottom: 15px; font-size: 0.95em;">
        <div style="font-weight: bold; color: #0056b3; margin-bottom: 8px; font-size: 1.1em;">📖 문헌 출처 및 이론적 배경</div>
        <ul style="margin-bottom: 0; padding-left: 20px; line-height: 1.6;">
            <li><b>논문명 :</b> Critical Tractive Forces in Cohesive Soils</li>
            <li><b>저 자 :</b> E. T. Smerdon, R. P. Beasley</li>
            <li><b>발행처 :</b> Agricultural Engineering, Vol. 42, No. 1, pp. 26-29 (1961)</li>
            <li><b>이론적 배경 :</b> 모래와 달리 점착력으로 세굴을 버티는 점성토의 침식 저항성을 물리적 지표로 수치화한 연구입니다. 광범위한 수로(Flume) 수리실험을 통해 흙의 '소성지수(PI)'가 높을수록 흙이 버티는 물리적 마찰력인 '한계소류력(<i>τ<sub>c</sub></i>)'이 지수함수적으로 증가한다는 상관관계(<i>τ<sub>c</sub> = 0.16 × PI<sup>0.84</sup></i>)를 도출했습니다. 이 한계소류력을 Manning의 평균유속 공식과 수리학적으로 연립하여 한계유속(<i>V<sub>c</sub></i>)으로 역산하는 물리적 근거가 됩니다.</li>
        </ul>
    </div>
    """
    st.markdown(source_html2, unsafe_allow_html=True)
    
    st.info("💡 **실무 Tip:** 지반조사 보고서에 흙의 **소성지수(PI)**가 나와 있다면 이 방법을 쓰세요. 물이 바닥을 긁고 지나가는 힘(소류력)을 매닝(Manning) 공식과 엮어서 유속으로 역추적하는 매우 논리적인 실무 방식입니다.")
    
    st.markdown(r'''
    **[이론 공식 및 기호 설명]**
    흙의 소성지수를 이용해 한계소류력을 구한 뒤, 수리학적 평균 유속으로 역환산합니다.
    ''')
    st.latex(r"\tau_c = 0.16 \times (PI)^{0.84}")
    st.latex(r"V_c = \frac{1}{n} R^{1/6} \sqrt{\frac{\tau_c}{\gamma_w}}")
    
    st.markdown(r'''
    * $\tau_c$: 한계소류력 (Critical Tractive Force, 단위: psf. 이후 Pa 단위로 변환 적용)
    * $PI$: 흙의 소성지수 (Plasticity Index, %)
    * $V_c$: 한계유속 (m/s)
    * $n$: 조도계수 (Manning's roughness coefficient)
    * $R$: 경심 (Hydraulic Radius, m)
    * $\gamma_w$: 물의 단위중량 ($9810 \text{ N/m}^3$)
    ''')
    
    with st.expander("📖 조도계수(n) 및 경심(R) 실무 산정 가이드", expanded=True):
        st.markdown(r"""
        **1. 경심 (Hydraulic Radius, $R$)과 수심($h$)의 관계**
        * **정의:** 통수단면적($A$)을 물이 바닥과 닿는 둘레 길이인 윤변($P$)으로 나눈 값 ($R = A/P$)입니다. 직사각형 단면 기준 $R = \frac{B \cdot h}{B + 2h}$ 가 됩니다.
        * **해양 및 광폭하천 적용:** 바다나 폭이 매우 넓은 하천은 수심($h$)에 비해 폭($B$)이 무한대에 가깝게 넓으므로($B \gg h$), 분모의 $2h$를 무시할 수 있어 윤변 $P \approx B$가 됩니다. 따라서 **$R \approx \frac{B \cdot h}{B} = h$**가 성립하므로, **해양 설계 시에는 수심을 경심으로 그대로 대체**하여 적용합니다.

        **2. 조도계수 (Manning's $n$) 적용 기준**
        * **하천 조건 (수로 형상 및 식생 영향):**
          * **0.018 ~ 0.022**: 깨끗하고 곧게 뻗은 인공 흙수로
          * **0.025 ~ 0.030**: 잡초가 약간 있는 자연 하천 (일반적 적용값)
        * **해양 조건 (해저 퇴적물 입경 및 물리적 굴곡 영향):**
          * **0.015 ~ 0.020**: 매끄러운 점토(Mud) 및 실트(Silt) 해저면
          * **0.020 ~ 0.025**: 평탄한 모래(Sand) 해저면 (항만 및 해수유동 모델링 표준 기본값)
          * **0.025 ~ 0.035**: 자갈(Gravel)이 혼재되어 있거나, 조류에 의해 연흔(Ripples)이 심하게 발달한 굴곡진 해저면
        """)
    st.divider()

    col3, col4 = st.columns([1, 2])
    
    with col3:
        st.subheader("⚙️ 입력 조건")
        pi_val = st.number_input("소성지수 (PI, %)", value=20.0, step=1.0, help="지반조사 보고서의 Atterberg 한계 시험 결과 참조")
        n_val = st.number_input("조도계수 (Manning's n)", value=0.025, step=0.001, format="%.3f", help="점토질 하도 또는 해저면의 거칠기 (가이드 참조)")
        R_val = st.number_input("경심 또는 수심 (R, m)", value=2.0, step=0.1, help="바다 또는 광폭 하천의 경우 수심(h)과 동일하게 적용")
        
    with col4:
        st.subheader("📊 산정 결과 및 수식 전개")
        tau_psf, tau_pa, vc_calc = calc_smerdon_beasley(pi_val, n_val, R_val)
        
        st.success(f"### 최종 한계유속 (Uc) = {vc_calc:.3f} m/s")
        
        st.markdown("**Step 1. 소성지수를 이용한 한계소류력($\\tau_c$) 산정**")
        st.markdown("Smerdon & Beasley 제안식에 소성지수(PI)를 대입하여 흙이 버티는 한계소류력을 구합니다 (결과값은 psf 단위).")
        st.latex(rf"\tau_c = 0.16 \times (PI)^{{0.84}} = 0.16 \times ({pi_val:.1f})^{{0.84}} = {tau_psf:.3f} \text{{ psf}}")
        
        # \t 깨짐 방지를 위해 원시 문자열(r) 적용
        st.markdown(r"SI 단위계(Pa, $N/m^2$)로 환산 ($1 \text{ psf} = 47.88 \text{ Pa}$)")
        st.latex(rf"\tau_c \text{{ (Pa)}} = {tau_psf:.3f} \times 47.88 = {tau_pa:.2f} \text{{ Pa}}")
        
        st.markdown("**Step 2. Manning 공식을 이용한 한계유속($V_c$) 역산**")
        
        # \n 및 \t 깨짐 방지를 위해 원시 문자열(r) 적용
        st.markdown(r"소류력 공식 $\tau_c = \gamma_w \cdot R \cdot I$ 와 Manning 평균유속 공식 $V = \frac{1}{n}R^{2/3}I^{1/2}$ 을 연립하여 $V_c$에 대해 정리합니다.")
        st.latex(rf"V_c = \frac{{1}}{{{n_val:.3f}}} \times ({R_val:.1f})^{{1/6}} \times \sqrt{{\frac{{{tau_pa:.2f}}}{{9810}}}} = {vc_calc:.3f} \text{{ m/s}}")

# ----------------------------------------------------
# 탭 3: Mirtskhoulava 이론식
# ----------------------------------------------------
with tab3:
    st.header("3. 점성토 전용 한계유속 이론식 (Mirtskhoulava, 1988)")
    
    # 파란색 박스로 문헌 출처 및 이론적 배경 상세 표출
    source_html3 = """
    <div style="background-color: #f0f7ff; border: 1px solid #cce5ff; border-left: 5px solid #0056b3; padding: 15px; border-radius: 4px; margin-bottom: 15px; font-size: 0.95em;">
        <div style="font-weight: bold; color: #0056b3; margin-bottom: 8px; font-size: 1.1em;">📖 문헌 출처 및 이론적 배경</div>
        <ul style="margin-bottom: 0; padding-left: 20px; line-height: 1.6;">
            <li><b>논문명 :</b> Osnovy fiziki i mekhaniki erozii rusel (Basic physics and mechanics of channel erosion)</li>
            <li><b>저 자 :</b> C. E. Mirtskhoulava (※ 영문 해설 참조: Hoffmans & Verheij의 Scour Manual 등)</li>
            <li><b>발행처 :</b> Gidrometeoizdat, Leningrad (1988)</li>
            <li><b>이론적 배경 :</b> 물의 난류 흐름이 점성토 표면에 지속적인 맥동(Pulsation) 응력을 가할 때, 흙이 피로 파괴(Fatigue Rupture)를 일으켜 덩어리째 떨어져 나가는(Detaching Aggregates) 현상을 수학적으로 완벽히 모델링한 역학 공식입니다. 흙의 종류, 액성지수(Liquidity Index), 공극률에 따른 물리화학적 결합력인 포화 점착력(<i>C<sub>0</sub></i>)을 한계유속 공식에 직접 반영하여 산정합니다.</li>
        </ul>
    </div>
    """
    st.markdown(source_html3, unsafe_allow_html=True)
    
    st.info("💡 **실무 Tip:** 흙의 공극율, 액성지수(LI) 등 물리적 특성을 가장 디테일하게 수식에 반영하는 방법입니다. 주로 교량 세굴이나 주요 항만 구조물 설계 시 **정밀 검토용**으로 가장 널리 사용됩니다.")
    
    st.markdown('''
    **[이론 공식 및 기호 설명]**
    물의 흐름이 점성토 표면에 지속적인 맥동(Pulsation) 응력을 가해 흙 입자가 덩어리째 떨어져 나가는(Flaking) 메커니즘을 수학적으로 모델링한 공식입니다.
    ''')
    st.latex(r"U_{c} = \log\left(\frac{8.8h}{d_{a}}\right) \sqrt{\left[ \frac{0.4}{\rho} \left\{ (\rho_{s}-\rho)gd_{a} + 0.6C_{f} \right\} \right]}")
    
    st.markdown('''
    * $U_c$: 한계유속 (Critical Velocity, m/s)
    * $h$: 수심 (m)
    * $d_a$: 점성토 기준 입경 (통상 **0.004 m** 적용)
    * $\rho$: 물의 밀도 (해수의 경우 1.03 적용)
    * $\rho_s$: 흙 입자의 밀도 (통상 2.69 적용)
    * $g$: 중력가속도 (9.81 $m/s^2$)
    * $C_f$: 파괴에 저항하는 전단응력 ($C_f = 0.035 \times C_0$)
    * $C_0$: 흙의 점착력 (kPa). 토질 분류, 액성지수(Liquidity Index), 공극율을 바탕으로 산정.
    ''')
    st.divider()
    
    col5, col6 = st.columns([1, 2])
    
    with col5:
        st.subheader("⚙️ 설계 조건 입력")
        h3 = st.number_input("수심 h (m)", value=5.0, step=0.1, key="h3")
        
        with st.expander("고급 설정 (밀도 및 입경)"):
            rho3 = st.number_input("해수 밀도 ρ", value=1.03, step=0.01, key="rho3")
            rhos3 = st.number_input("흙 입자 밀도 ρs", value=2.69, step=0.01, key="rhos3")
            da3 = st.number_input("기준 입경 da (m)", value=0.004, format="%.4f", key="da3")
        
# ----------------------------------------------------
# 탭 3: Mirtskhoulava 이론식 내 UI 입력부 변경 사항
# ----------------------------------------------------
# (기존 soil_type 입력 코드를 아래와 같이 교체)
        st.markdown("---")
        st.markdown("**지반 조사 데이터 (C0 매칭용)**")
        soil_type = st.selectbox("토질 분류 (Soil Type)", ["양질 사토 (Loamy Sand)", "양질 점토 (Loamy Clay)", "점토 (Clay)"], index=1)
        
        # 선택된 토질에 맞는 액성지수 옵션 필터링
        li_options = list(C0_TABLE[soil_type].keys())
        li_range = st.selectbox("액성지수 (Liquidity Index)", li_options, index=1 if len(li_options)>1 else 0)
        
        poro_options = [0.45, 0.65, 0.75, 0.85, 0.95]
        porosity = st.selectbox("공극율 (Porosity)", poro_options, index=3)
        
        manual_c0 = st.checkbox("점착력(C0) 수동 입력")
        if manual_c0:
            c0_input = st.number_input("점착력 C0 (kPa)", value=17.7, step=0.1)
        else:
            c0_input = get_c0_value(soil_type, li_range, porosity)
            if c0_input is None:
                st.error("⚠️ 해당 조건의 C0 값이 표에 없습니다.")
                c0_input = 0.0
            else:
                st.success(f"매칭된 C0 값: {c0_input} kPa")
                
    with col6:
        st.subheader("📊 산정 결과 및 수식 전개")
        if c0_input > 0:
            Uc3, Cf3, term1_3, term2_3, inner3 = calc_mirtskhoulava(h3, c0_input, rho3, rhos3, da3)
            
            st.success(f"### 최종 한계유속 (Uc) = {Uc3:.3f} m/s")
            
            st.markdown("**Step 1: 지반조사 매칭 근거 및 점착력($C_0$) 산정**")
            if manual_c0:
                match_reason = f"사용자 수동 입력: 점착력 <b>C<sub>0</sub> = {c0_input:.1f} kPa</b> 적용"
                st.info(f"사용자 수동 입력: 점착력 **$C_0 = {c0_input:.1f}$ kPa** 적용")
            else:
                match_reason = f"매칭 결과: <b>{soil_type} / LI: {li_range} / 공극율: {porosity}</b> &rarr; <b>C<sub>0</sub> = {c0_input:.1f} kPa</b> 자동 독취"
                st.info(f"매칭 결과: **{soil_type} / LI: {li_range} / 공극율: {porosity}** &rarr; **$C_0 = {c0_input:.1f}$ kPa** 자동 독취")
            
            # HTML 근거 표 화면 출력
            c0_html_table = generate_c0_html_table(soil_type, li_range, porosity, manual_c0)
            st.markdown(c0_html_table, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("**Step 2: 파괴에 저항하는 전단응력($C_f$) 산정**")
            st.latex(rf"C_f = 0.035 \times C_0 = 0.035 \times {c0_input:.2f} = {Cf3:.4f}")
            
            st.markdown("**Step 3: 수심 및 입경에 따른 대수항 산출**")
            st.latex(rf"\log\left(\frac{{8.8 \times h}}{{d_a}}\right) = \log\left(\frac{{8.8 \times {h3}}}{{{da3}}}\right) = {term1_3:.4f}")
            
            st.markdown("**Step 4: 제곱근 내부 응력항 산출**")
            st.latex(rf"\text{{Inner}} = \frac{{0.4}}{{{rho3}}} \left\{{ ({rhos3} - {rho3}) \times 9.81 \times {da3} + 0.6 \times {Cf3:.4f} \right\}} = {inner3:.4f}")
            
            st.markdown("**Step 5: 최종 한계유속($U_c$) 도출**")
            st.latex(rf"U_c = {term1_3:.4f} \times \sqrt{{{inner3:.4f}}} = {Uc3:.3f} \text{{ m/s}}")

            # =========================================================
            # ★ 핵심 추가: 보고서에 출력할 통합 HTML 변수 (method3_detail) 생성
            # =========================================================
            method3_detail = f"""
            <div class="result-box">최종 한계유속 (Uc) = {Uc3:.3f} m/s</div>
            
            <h3>수식 전개 및 상세 연산 과정</h3>
            <div class="eq">$$ U_{{c}} = \\log\\left(\\frac{{8.8h}}{{d_{{a}}}}\\right) \\sqrt{{\\left[ \\frac{{0.4}}{{\\rho}} \\left\\{{ (\\rho_{{s}}-\\rho)gd_{{a}} + 0.6C_{{f}} \\right\\}} \\right]}} $$</div>
            
            <p class="step-title">Step 1. 지반조사 매칭 근거 및 점착력($C_0$) 산정</p>
            <div class="info-box">💡 {match_reason}</div>
            {c0_html_table}
            
            <p class="step-title" style="margin-top:20px;">Step 2. 파괴에 저항하는 전단응력($C_f$) 산정</p>
            <div class="eq">$$ C_f = 0.035 \\times C_0 = 0.035 \\times {c0_input:.2f} = {Cf3:.4f} $$</div>
            
            <p class="step-title">Step 3. 수심 및 입경에 따른 대수항 산출</p>
            <div class="eq">$$ \\log\\left(\\frac{{8.8 \\times h}}{{d_a}}\\right) = \\log\\left(\\frac{{8.8 \\times {h3}}}{{{da3}}}\\right) = {term1_3:.4f} $$</div>
            
            <p class="step-title">Step 4. 제곱근 내부 응력항 산출</p>
            <div class="eq">$$ \\text{{Inner}} = \\frac{{0.4}}{{{rho3}}} \\left\\{{ ({rhos3} - {rho3}) \\times 9.81 \\times {da3} + 0.6 \\times {Cf3:.4f} \\right\\}} = {inner3:.4f} $$</div>
            
            <p class="step-title">Step 5. 최종 한계유속($U_c$) 도출</p>
            <div class="eq">$$ U_c = {term1_3:.4f} \\times \\sqrt{{{inner3:.4f}}} = {Uc3:.3f} \\text{{ m/s}} $$</div>
            """

# =====================================================================
# ★ 통합 보고서용 Fortier & Scobey 참조표 HTML 생성
# =====================================================================
report_table_html = """
<table style="width:100%; border-collapse: collapse; text-align: center; margin: 15px 0; font-size: 0.9em;">
    <tr style="background-color: #eff6ff; color: #1e3a8a;">
        <th style="border: 1px solid #ddd; padding: 8px;">수로 구성 토질 (Material)</th>
        <th style="border: 1px solid #ddd; padding: 8px;">맑은 물 (Clear Water)</th>
        <th style="border: 1px solid #ddd; padding: 8px;">토사 함유 (Silt-Laden)</th>
        <th style="border: 1px solid #ddd; padding: 8px;">모래/자갈 소류사 포함</th>
    </tr>
"""
for mat, conds in FORTIER_SCOBEY_TABLE.items():
    c1 = f"{conds['맑은 물 (Clear Water)']['ft']:.2f} ft/s ({conds['맑은 물 (Clear Water)']['ms']:.2f} m/s)"
    c2 = f"{conds['토사 함유 (Silt-Laden Water)']['ft']:.2f} ft/s ({conds['토사 함유 (Silt-Laden Water)']['ms']:.2f} m/s)"
    c3 = f"{conds['모래/자갈 소류사 포함 (Bedload)']['ft']:.2f} ft/s ({conds['모래/자갈 소류사 포함 (Bedload)']['ms']:.2f} m/s)"
    
    # 사용자가 선택한 행은 시각적으로 강조
    is_selected = (mat == sel_material)
    row_style = "background-color: #f0fdf4; font-weight: bold; border: 1px solid #bbf7d0;" if is_selected else "border: 1px solid #ddd;"
    
    report_table_html += f"""
    <tr style="{row_style}">
        <td style="padding: 8px; text-align: left;">{mat}</td>
        <td style="padding: 8px;">{c1}</td>
        <td style="padding: 8px;">{c2}</td>
        <td style="padding: 8px;">{c3}</td>
    </tr>
    """
report_table_html += "</table>"

# =====================================================================
# ★ [고급] 관련 변수 안전 초기화 (NameError 방지용) -> 이 위치에 추가하세요!
# =====================================================================
if 'method3_detail' not in locals():
    method3_detail = "<div class='result-box' style='background-color:#f8d7da; color:#721c24;'>[고급] Mirtskhoulava 계산 결과가 아직 없습니다. 탭 3을 먼저 확인해주세요.</div>"
    h3 = 0.0
    soil_type = "미정"
    li_range = "미정"
    porosity = 0.0
    rho3 = 1025.0
    rhos3 = 2650.0
    da3 = 0.0
    manual_c0 = True
    c0_input = 0.0
    Cf3 = 0.0
    term1_3 = 0.0
    inner3 = 0.0
    Uc3 = 0.0

# =====================================================================
# ★ 통합 HTML 템플릿 구성 (Raw f-string 적용으로 LaTeX 백슬래시 깨짐 방지)
# =====================================================================
html_report = rf"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>점성토 세굴 한계유속 통합 산정 보고서</title>
    <script>
        window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] }} }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; padding: 30px; color: #333; max-width: 1000px; margin: auto; }}
        h1 {{ color: #1e3a8a; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; text-align: center; margin-bottom: 30px; }}
        h2 {{ color: #2563eb; margin-top: 40px; border-bottom: 2px solid #ddd; padding-bottom: 5px; font-size: 1.3em; }}
        h3 {{ color: #1e3a8a; font-size: 1.05em; margin-top: 20px; }}
        .result-box {{ background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px; border-radius: 5px; font-size: 1.2em; font-weight: bold; color: #166534; text-align: center; margin: 15px 0; }}
        .info-box {{ background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 12px; margin: 12px 0; font-size: 0.95em; }}
        .source-box {{ background-color: #f0f7ff; border: 1px solid #cce5ff; border-left: 5px solid #0056b3; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 0.9em; line-height: 1.5; }}
        .eq {{ background: #f8fafc; padding: 10px; border-radius: 5px; text-align: center; margin: 12px 0; overflow-x: auto; border: 1px solid #e2e8f0; }}
        .step-title {{ font-weight: bold; color: #333; margin-bottom: 5px; font-size: 1.0em; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; text-align: center; font-size: 0.9em; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background-color: #eff6ff; color: #1e3a8a; }}
    </style>
</head>
<body>
    <h1>🌊 점성토 세굴 한계유속 통합 산정 보고서</h1>
    
    <p>사질토(모래)는 '무게와 입경'으로 세굴을 버티지만, 점성토(진흙)는 입자 간의 <b>물리화학적 결합력(점착력)</b>으로 버팁니다. 현장의 데이터 보유 상황에 따른 3가지 산정 방법의 비교 결과 및 상세 계산 결과는 다음과 같습니다.</p>
    
    <h2>종합 비교 및 방법론 선택 가이드</h2>
    {comparison_html}
    
    <h2>1. [기본] 경험적 허용유속 표 산정 (Fortier & Scobey 원본 기준)</h2>
    <div class="source-box">
        <b>📖 문헌 출처 및 이론적 배경:</b><br>
        &bull; <b>논문명:</b> Permissible Canal Velocities (Transactions of the ASCE, Vol. 89, pp. 940-956, 1926)<br>
        &bull; <b>저자:</b> Samuel Fortier, Fred C. Scobey<br>
        &bull; <b>특징:</b> 수로 구성 토질과 흐르는 물의 상태에 따른 최대 허용 유속을 실측 기반 데이터 표로 제시한 표준 기준입니다.
    </div>
    <div class="info-box">
        <b>선택된 수로 토질:</b> {sel_material}<br>
        <b>흐르는 물의 상태:</b> {sel_water_cond}
    </div>
    
    <h3>📋 Fortier & Scobey 원본 허용유속 전체 참조표</h3>
    {report_table_html}
    
    <div class="result-box">적용 허용 유속 = {res_ms:.2f} m/s ({res_ft:.2f} ft/s)</div>
    
    <h2>2. [중급] 한계소류력 기반 유속 역산법 (Smerdon & Beasley, 1961)</h2>
    <div class="source-box">
        <b>📖 문헌 출처 및 이론적 배경:</b><br>
        &bull; <b>논문명:</b> Critical Tractive Forces in Cohesive Soils (Agricultural Engineering, Vol. 42, No. 1, pp. 26-29, 1961)<br>
        &bull; <b>저자:</b> E. T. Smerdon, R. P. Beasley<br>
        &bull; <b>특징:</b> 소성지수(PI)와 지수가공된 한계소류력($\tau_c = 0.16 \cdot PI^{{0.84}}$)의 상관관계를 도출하고, Manning 공식과 연립하여 한계유속을 역산합니다.
    </div>
    <table>
        <tr><th>소성지수 (PI)</th><th>조도계수 (n)</th><th>경심 (R)</th></tr>
        <tr><td>{pi_val:.1f} %</td><td>{n_val:.3f}</td><td>{R_val:.1f} m</td></tr>
    </table>
    
    <div class="result-box">최종 한계유속 (Uc) = {vc_calc:.3f} m/s</div>
    
    <h3>수식 전개 및 상세 연산 과정</h3>
    <p class="step-title">Step 1. 소성지수를 이용한 한계소류력($\tau_c$) 산정</p>
    <div class="eq">$$ \tau_c = 0.16 \times (PI)^{{0.84}} = 0.16 \times ({pi_val:.1f})^{{0.84}} = {tau_psf:.3f} \text{{ psf}} $$</div>
    <div class="eq">$$ \tau_c \text{{ (Pa)}} = {tau_psf:.3f} \times 47.88 = {tau_pa:.2f} \text{{ Pa}} $$</div>
    
    <p class="step-title">Step 2. Manning 공식을 이용한 한계유속($V_c$) 역산</p>
    <div class="eq">$$ V_c = \frac{{1}}{{n}} R^{{1/6}} \sqrt{{\frac{{\tau_c}}{{\gamma_w}}}} = \frac{{1}}{{{n_val:.3f}}} \times ({R_val:.1f})^{{1/6}} \times \sqrt{{\frac{{{tau_pa:.2f}}}{{9810}}}} = {vc_calc:.3f} \text{{ m/s}} $$</div>
    
    <h2>3. [고급] 점성토 전용 한계유속 이론식 (Mirtskhoulava, 1988)</h2>
    <div class="source-box">
        <b>📖 문헌 출처 및 이론적 배경:</b><br>
        &bull; <b>논문명:</b> Osnovy fiziki i mekhaniki erozii rusel (Gidrometeoizdat, Leningrad, 1988)<br>
        &bull; <b>저자:</b> C. E. Mirtskhoulava<br>
        &bull; <b>특징:</b> 난류 맥동에 의한 피로 파괴로 점성토 입자가 덩어리째 떨어져 나가는 메커니즘을 물리 방정식으로 구현한 정밀 이론식입니다.
    </div>
    <table>
        <tr><th>수심 (h)</th><th>토질 분류</th><th>Liquidity Index</th><th>공극율</th><th>해수 밀도(ρ)</th><th>흙 밀도(ρs)</th><th>입경(da)</th></tr>
        <tr>
            <td>{h3:.1f} m</td>
            <td>{soil_type if not manual_c0 else '수동입력'}</td>
            <td>{li_range if not manual_c0 else '-'}</td>
            <td>{porosity if not manual_c0 else '-'}</td>
            <td>{rho3:.2f}</td>
            <td>{rhos3:.2f}</td>
            <td>{da3:.4f} m</td>
        </tr>
    </table>
    
    {method3_detail}
    
</body>
</html>
"""
# =====================================================================
# ★ 초고속 수식 이미지 다운로드 캐시 및 MHTML 변환 엔진 (MS Word 호환)
# =====================================================================
@st.cache_data(show_spinner=False)
def fetch_equation_image(api_url):
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return base64.b64encode(response.read()).decode('utf-8')
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def convert_html_to_mhtml(html_content):
    word_html = html_content
    attachments = {}
    counters = {'img': 0, 'eq': 0}

    word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
    word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 25px;"')
    word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f1f8ff; text-align: center;">')
    word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

    def image_replacer(match):
        b64_data = match.group(1)
        counters['img'] += 1
        img_id = f"embedded_img_{counters['img']}"
        attachments[img_id] = b64_data
        return f'<img src="cid:{img_id}" style="max-width: 100%; height: auto;">'
    
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
    
    mhtml_body = word_html.replace("<html", "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word'")
    mhtml_body = mhtml_body.replace("<head>", "<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'>")
    
    mhtml += mhtml_body + "\n\n"
    for cid, b64 in attachments.items():
        formatted_b64 = '\n'.join(textwrap.wrap(b64, 76))
        mhtml += f'--{boundary}\nContent-Type: image/png\nContent-Transfer-Encoding: base64\nContent-ID: <{cid}>\n\n{formatted_b64}\n\n'
    mhtml += f"--{boundary}--\n"
    return mhtml

# =====================================================================
# ★ 통합 보고서 다운로드 렌더링 (HTML웹용 및 MS Word용 양방향 제공)
# =====================================================================
st.divider()
st.header("🖨️ 종합 산정 보고서 다운로드")
st.info("💡 **초고속 병렬 다운로드 엔진 적용:** 화면에 구성된 모든 비교표와 3가지 산정 방법론 결과가 포함된 HTML 및 MS Word용 보고서를 즉시 생성합니다.")

with st.spinner("보고서용 수식과 표를 변환 중입니다..."):
    mhtml_data = convert_html_to_mhtml(html_report)

col_d1, col_d2 = st.columns(2)
with col_d1:
    st.download_button(
        label="📄 산정 보고서 다운로드 (HTML웹용)", 
        data=html_report.encode('utf-8'), 
        file_name="점성토_한계유속_통합_산정보고서.html", 
        mime="text/html", 
        use_container_width=True
    )
with col_d2:
    st.download_button(
        label="📝 산정 보고서 다운로드 (MS Word용)", 
        data=mhtml_data.encode('utf-8'), 
        file_name="점성토_한계유속_통합_산정보고서.doc", 
        mime="application/msword", 
        use_container_width=True
    )
