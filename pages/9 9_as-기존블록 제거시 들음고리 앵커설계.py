import streamlit as st
import math
import pandas as pd
with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

# 페이지 설정
st.set_page_config(page_title="수중 블록 인양 구조 검토", layout="wide", page_icon="🏗️")

# --- UI 제목 및 설명 ---
st.title("🏗️ 수중부 유공근고블록 및 피복블록 인양·제거 검토서")
st.markdown("케미컬 앵커(Hilti HIT-RE 500 V4, Grade 8.8), 콘크리트 파괴/부착 내력, 와이어로프 및 샤클의 안전성을 종합 검토합니다.")

# --- 사이드바: 입력부 ---
st.sidebar.header("📝 1. 블록 제원 및 하중 조건")
block_type = st.sidebar.selectbox("블록 종류", ["유공근고블록 (Type A1)", "피복블록", "기타"])
vol = st.sidebar.number_input("블록 체적 (V, m³)", value=18.58, step=0.1)
bottom_area = st.sidebar.number_input("블록 저면적 (A, m²)", value=12.50, step=0.1)
gamma_c = st.sidebar.number_input("콘크리트 단위중량 (kN/m³)", value=22.6, step=0.1)
fck = st.sidebar.number_input("콘크리트 압축강도 (fck, MPa)", value=24.0, step=1.0)

st.sidebar.header("🌊 2. 인양 계수")
suction_factor = st.sidebar.number_input("저면 부착력 계수", value=3.0, step=0.1)
additional_load_factor = st.sidebar.number_input("기타 부가하중 계수 (%)", value=5.0, step=0.5) / 100.0
dynamic_factor = st.sidebar.number_input("동적계수 (Kd)", value=1.30, step=0.1, help="파랑 및 크레인 인양 동하중")
unequal_factor = st.sidebar.number_input("앵커지점당 불균등계수 (Ku)", value=1.33, step=0.01, help="로프 편차 및 편심 고려")

st.sidebar.header("🔩 3. 앵커 및 인양 조건")
anchor_qty = st.sidebar.number_input("인양점(앵커) 개수 (N, EA)", value=4, step=1)
sling_angle = st.sidebar.number_input("슬링 로프 각도 (θ, 수평면 기준)", value=60.0, step=1.0)
# M32 추가 및 M36 기본값(index=4) 유지
anchor_spec = st.sidebar.selectbox("앵커 규격", ["M20", "M24", "M30", "M32", "M36"], index=4)
h_ef = st.sidebar.number_input("앵커 유효 매입깊이 (hef, mm)", value=500, step=10)
tau_k = st.sidebar.number_input("특성 부착강도 (τk, MPa)", value=8.0, step=0.1)

# --- 와이어로프 (IWRC 6xFi(29) B종) 및 샤클 데이터 딕셔너리 ---
wire_data = {
    "IWRC 6xFi(29) B종, D=20mm": 279.0,
    "IWRC 6xFi(29) B종, D=22mm": 338.0,
    "IWRC 6xFi(29) B종, D=24mm": 402.0,
    "IWRC 6xFi(29) B종, D=28mm": 547.0,
    "IWRC 6xFi(29) B종, D=32mm": 714.0,
    "IWRC 6xFi(29) B종, D=36mm": 904.0,
    "IWRC 6xFi(29) B종, D=40mm": 1120.0,
    "IWRC 6xFi(29) B종, D=45mm": 1410.0,
    "IWRC 6xFi(29) B종, D=50mm": 1750.0
}

shackle_data = {
    "Bow Shackle, WLL 8.5 ton": 83.4,
    "Bow Shackle, WLL 12 ton": 117.7,
    "Bow Shackle, WLL 17 ton": 166.7,
    "Bow Shackle, WLL 25 ton": 245.3,
    "Bow Shackle, WLL 35 ton": 343.4,
    "Bow Shackle, WLL 55 ton": 539.6
}

st.sidebar.header("🔗 4. 와이어로프 및 샤클")
wire_spec = st.sidebar.selectbox("와이어로프 적용 규격", list(wire_data.keys()), index=7)
wire_breaking_load = wire_data[wire_spec]
st.sidebar.info(f"선택된 공칭 파단 하중: **{wire_breaking_load} kN**")

shackle_spec = st.sidebar.selectbox("샤클 적용 규격", list(shackle_data.keys()), index=4)
shackle_wll = shackle_data[shackle_spec]
st.sidebar.info(f"선택된 안전하중: **{shackle_wll} kN**")

# --- 계산 로직 ---
# 1) 기본 하중 산정
W_air = float(vol * gamma_c)
W_add = float(W_air * additional_load_factor)
F_suction = float(bottom_area * suction_factor)
P_basic = W_air + W_add + F_suction

# 2) 총 인양하중 및 앵커 설계하중 산정
P_total = float(P_basic * dynamic_factor)
angle_rad = math.radians(float(sling_angle))

if anchor_qty > 0 and math.sin(angle_rad) > 0:
    T_req = float((P_total * unequal_factor) / (anchor_qty * math.sin(angle_rad)))
else:
    T_req = 0.001 

# 3) 안정성 검토 (안전율 및 설계강도 계산)
# 3.1 앵커 강재 인장강도 검토 (Grade 8.8 적용)
# M32의 As는 M30(561)과 M36(817)을 선형 보간하여 646.3 적용
A_s_dict = {"M20": 245.0, "M24": 353.0, "M30": 561.0, "M32": 646.3, "M36": 817.0}
A_s = A_s_dict[anchor_spec]
f_uk = 800.0  # Grade 8.8 공칭 극한인장강도 (MPa)
phi_s = 0.75  # 강재 파괴에 대한 강도감소계수

N_sk = float((A_s * f_uk) / 1000.0)  # 공칭 강재 인장강도 (kN)
N_sd = float(N_sk * phi_s)           # 설계 강재 인장강도 (kN)

sf_anchor = float(N_sd / T_req) if T_req > 0 else 0.0
is_safe_anchor = sf_anchor >= 1.0

# 3.2 콘크리트 브레이크아웃 강도 검토 (KDS 14 20 54)
k_c = 10.0  # 비균열 콘크리트 후설치 앵커 계수
phi_c = 0.65  # 콘크리트 파괴에 대한 강도감소계수

N_ck = float((k_c * math.sqrt(fck) * (h_ef ** 1.5)) / 1000.0) # 공칭 콘크리트 파괴강도 (kN)
N_cd = float(N_ck * phi_c) # 설계 콘크리트 파괴강도 (kN)

sf_concrete = float(N_cd / T_req) if T_req > 0 else 0.0
is_safe_concrete = sf_concrete >= 1.0

# 3.3 콘크리트 부착 파괴강도 검토 (Bond Failure)
# M32의 공칭 직경은 32.0 적용
d_dict = {"M20": 20.0, "M24": 24.0, "M30": 30.0, "M32": 32.0, "M36": 36.0}
d = d_dict[anchor_spec]
phi_a = 0.65  # 부착 파괴에 대한 강도감소계수

N_ak = float((tau_k * math.pi * d * h_ef) / 1000.0) # 공칭 부착강도 (kN)
N_ad = float(N_ak * phi_a) # 설계 부착강도 (kN)

sf_bond = float(N_ad / T_req) if T_req > 0 else 0.0
is_safe_bond = sf_bond >= 1.0

# 3.4 와이어로프 검토 (안전율 5 적용하여 소요 파단 하중 산출)
wire_sf_target = 5.0
req_breaking_load = float(T_req * wire_sf_target) # 소요 파단 하중
sf_wire_actual = float(wire_breaking_load / T_req) if T_req > 0 else 0.0
is_safe_wire = wire_breaking_load >= req_breaking_load

# 3.5 샤클 검토
sf_shackle = float(shackle_wll / T_req) if T_req > 0 else 0.0
is_safe_shackle = sf_shackle >= 1.0


# --- 결과 렌더링 영역 ---
st.markdown("---")
st.markdown("### 📊 인양 장비 및 앵커 종합 검토 결과 요약")
summary_data = {
    "검토 항목": ["앵커 강재 인장내력", "콘크리트 파괴강도", "콘크리트 부착 파괴강도", "와이어로프 (안전율 5.0)", "샤클 (안전율 1.0)"],
    "적용 규격": [f"{anchor_spec} (Grade 8.8)", f"fck = {fck} MPa", f"τk = {tau_k} MPa", wire_spec, shackle_spec],
    "소요 장력/파단하중": [f"{T_req:.2f} kN", f"{T_req:.2f} kN", f"{T_req:.2f} kN", f"{req_breaking_load:.2f} kN (소요)", f"{T_req:.2f} kN"],
    "설계(허용)/공칭 내력": [f"{N_sd:.2f} kN", f"{N_cd:.2f} kN", f"{N_ad:.2f} kN", f"{wire_breaking_load:.2f} kN (공칭)", f"{shackle_wll:.2f} kN"],
    "계산된 안전율": [f"{sf_anchor:.2f}", f"{sf_concrete:.2f}", f"{sf_bond:.2f}", f"{sf_wire_actual:.2f}", f"{sf_shackle:.2f}"],
    "판정": [
        "🟢 OK" if is_safe_anchor else "🔴 NG",
        "🟢 OK" if is_safe_concrete else "🔴 NG",
        "🟢 OK" if is_safe_bond else "🔴 NG",
        "🟢 OK" if is_safe_wire else "🔴 NG",
        "🟢 OK" if is_safe_shackle else "🔴 NG"
    ]
}
st.table(pd.DataFrame(summary_data))

st.markdown("---")

st.markdown("### 📝 상세 구조계산 및 수식 전개 과정")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### 1) 기본하중 산정 ($P_{basic}$)")
    st.markdown(f"- **① 공기 중 자중 ($W_{{air}}$)** = $V \\times \\gamma_c$ = {vol} $\\times$ {gamma_c} = **{W_air:.2f} kN**")
    st.markdown(f"- **② 기타 부가하중 ($W_{{add}}$)** = $W_{{air}} \\times {additional_load_factor*100}\\%$ = {W_air:.2f} $\\times$ {additional_load_factor} = **{W_add:.2f} kN**")
    st.markdown(f"- **③ 저면 부착력 ($F_{{suction}}$)** = $A \\times \\text{{부착력계수}}$ = {bottom_area} $\\times$ {suction_factor} = **{F_suction:.2f} kN**")
    st.info(f"▶ **기본하중 ($P_{{basic}}$)** = ① + ② + ③ = **{P_basic:.2f} kN**")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 2) 총 인양하중 및 설계하중 산정")
    st.markdown(f"- **총 인양하중 ($P_{{total}}$)** = $P_{{basic}} \\times \\text{{동적계수}}(K_d)$")
    st.markdown(f"  = {P_basic:.2f} $\\times$ {dynamic_factor} = **{P_total:.2f} kN**")
    
    st.markdown(f"- **앵커지점당 소요 설계하중 ($T_{{req}}$)**")
    st.markdown(f"  = $\\frac{{P_{{total}} \\times \\text{{불균등계수}}(K_u)}}{{N \\times \\sin(\\theta)}}$")
    st.markdown(f"  = $\\frac{{{P_total:.2f} \\times {unequal_factor}}}{{{anchor_qty} \\times \\sin({sling_angle}^\\circ)}}$ = **{T_req:.2f} kN/EA**")
    st.success(f"▶ **앵커 및 로프 1본당 소요 장력 ($T_{{req}}$)** = **{T_req:.2f} kN**")

with col_b:
    st.markdown("#### 3) 케미컬 앵커 및 콘크리트 안정성 검토")
    st.markdown("**① 앵커 강재 인장강도 검토 (Grade 8.8)**")
    st.markdown(f"- 공칭 응력 단면적 ($A_s$) = {A_s} $mm^2$, 공칭 인장강도 ($f_{{uk}}$) = 800 MPa")
    st.markdown(f"- 강도감소계수 ($\\phi_s$) = {phi_s}")
    st.markdown(f"- 설계 강재 인장강도 ($N_{{s,d}}$) = $\\phi_s \\times (A_s \\times f_{{uk}}) \\times 10^{{-3}}$ = **{N_sd:.2f} kN**")
    st.markdown(f"▶ **안전성 확인**: $\\frac{{N_{{s,d}}}}{{T_{{req}}}}$ = $\\frac{{{N_sd:.2f}}}{{{T_req:.2f}}}$ = **{sf_anchor:.2f} $\\ge$ 1.0 ({'안전' if is_safe_anchor else 'NG'})**")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("**② 콘크리트 브레이크아웃 파괴강도 검토**")
    st.markdown(f"- 비균열 콘크리트 계수 ($k_c$) = 10.0, 강도감소계수 ($\\phi_c$) = {phi_c}")
    st.markdown(f"- 공칭 파괴강도 ($N_{{c,k}}$) = $10.0 \\times \\sqrt{{{fck}}} \\times {h_ef}^{{1.5}} \\times 10^{{-3}}$ = {N_ck:.2f} kN")
    st.markdown(f"- 설계 파괴강도 ($N_{{c,d}}$) = $\\phi_c \\times N_{{c,k}}$ = {phi_c} $\\times$ {N_ck:.2f} = **{N_cd:.2f} kN**")
    st.markdown(f"▶ **안전성 확인**: $\\frac{{N_{{c,d}}}}{{T_{{req}}}}$ = $\\frac{{{N_cd:.2f}}}{{{T_req:.2f}}}$ = **{sf_concrete:.2f} $\\ge$ 1.0 ({'안전' if is_safe_concrete else 'NG'})**")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("**③ 콘크리트 부착 파괴강도 검토**")
    st.markdown(f"- 공칭 직경 ($d$) = {d} mm, 특성 부착강도 ($\\tau_k$) = {tau_k} MPa")
    st.caption("※ 특성 부착강도는 제원표 상에는 콘크리트 강도(C20/25 등)와 건조/습윤 상태에 따라 다양한 부착강도(일반적으로 10~15MPa 이상)가 제시되어 있으나, 본 검토서는 기존 구조물의 강도가 낮고(18MPa) 수중(Water-saturated) 환경이라는 제원표 상의 악조건(강도 저감 요소)을 모두 고려하여, 가장 안전하고 보수적인 수치로 환산 적용하였음.")
    st.markdown(f"- 강도감소계수 ($\\phi_a$) = {phi_a}")
    st.markdown(f"- 설계 부착강도 ($N_{{a,d}}$) = $\\phi_a \\times (\\tau_k \\cdot \\pi \\cdot d \\cdot h_{{ef}}) \\times 10^{{-3}}$ = **{N_ad:.2f} kN**")
    st.markdown(f"▶ **안전성 확인**: $\\frac{{N_{{a,d}}}}{{T_{{req}}}}$ = $\\frac{{{N_ad:.2f}}}{{{T_req:.2f}}}$ = **{sf_bond:.2f} $\\ge$ 1.0 ({'안전' if is_safe_bond else 'NG'})**")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 4) 와이어로프 및 샤클 규격 검토")
    st.markdown(f"**① 와이어로프 규격 선정 및 안전성 (IWRC 6×Fi(29) B종)**")
    st.markdown(f"- 안전율 ($SF$) = **{wire_sf_target}** 적용")
    st.markdown(f"- **소요 파단 하중 ($P_{{req}}$)** = $T_{{req}} \\times SF$ = {T_req:.2f} $\\times$ {wire_sf_target} = **{req_breaking_load:.2f} kN**")
    st.markdown(f"- **적용 규격의 공칭 파단 하중 ($P_{{nom}}$)** = **{wire_breaking_load:.2f} kN**")
    st.markdown(f"▶ **안전성 확인**: $P_{{nom}} \\ge P_{{req}}$ ({wire_breaking_load:.2f} $\\ge$ {req_breaking_load:.2f}) **({'안전' if is_safe_wire else 'NG'})**")
    
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"**② 샤클 규격 선정 및 안전성**")
    st.markdown(f"- 적용 규격의 안전하중 ($WLL$) = **{shackle_wll:.2f} kN**")
    st.markdown(f"▶ **안전성 확인**: $WLL \\ge T_{{req}}$ ({shackle_wll:.2f} $\\ge$ {T_req:.2f}) **({'안전' if is_safe_shackle else 'NG'})**")
