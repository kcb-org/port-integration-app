import streamlit as st
import math
import pandas as pd
import urllib.request
import urllib.parse
import base64
import re
import textwrap
import concurrent.futures

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

# =====================================================================
# ★ 통합 보고서 MHTML 변환 엔진 (수식 정렬 및 Word 호환 완벽 보정)
# =====================================================================
@st.cache_data(show_spinner=False)
def fetch_equation_image(api_url):
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return base64.b64encode(response.read()).decode('utf-8')
    except Exception:
        return None

def convert_html_to_mhtml(html_content):
    word_html = html_content
    attachments = {}
    counters = {'img': 0, 'eq': 0}

    word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)
    word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 25px;"')
    word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #F8FAFC; text-align: center; color: #1E3A8A;">')
    word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')
    word_html = re.sub(r'(<img[^>]+)style=["\'][^"\']*["\']([^>]*>)', r'\1\2', word_html)
    
    def image_replacer(match):
        b64_data = match.group(1)
        counters['img'] += 1
        img_id = f"embedded_img_{counters['img']}"
        attachments[img_id] = b64_data
        return f'src="cid:{img_id}" width="500"' 
    
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
            img_tag = f"<img src='cid:{img_id}' style='vertical-align: -0.3em; border: none;'>"
        else:
            img_tag = f"<img src='{api_url}' style='vertical-align: -0.3em; border: none;'>"
        
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
# 페이지 설정 및 UI
# =====================================================================
st.set_page_config(page_title="수중 블록 인양 구조 검토", layout="wide", page_icon="🏗️")

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
anchor_spec = st.sidebar.selectbox("앵커 규격", ["M20", "M24", "M30", "M32", "M36"], index=4)
h_ef = st.sidebar.number_input("앵커 유효 매입깊이 (hef, mm)", value=500, step=10)
tau_k = st.sidebar.number_input("특성 부착강도 (τk, MPa)", value=8.0, step=0.1)

wire_data = {
    "IWRC 6xFi(29) B종, D=20mm": 279.0, "IWRC 6xFi(29) B종, D=22mm": 338.0,
    "IWRC 6xFi(29) B종, D=24mm": 402.0, "IWRC 6xFi(29) B종, D=28mm": 547.0,
    "IWRC 6xFi(29) B종, D=32mm": 714.0, "IWRC 6xFi(29) B종, D=36mm": 904.0,
    "IWRC 6xFi(29) B종, D=40mm": 1120.0, "IWRC 6xFi(29) B종, D=45mm": 1410.0,
    "IWRC 6xFi(29) B종, D=50mm": 1750.0
}

shackle_data = {
    "Bow Shackle, WLL 8.5 ton": 83.4, "Bow Shackle, WLL 12 ton": 117.7,
    "Bow Shackle, WLL 17 ton": 166.7, "Bow Shackle, WLL 25 ton": 245.3,
    "Bow Shackle, WLL 35 ton": 343.4, "Bow Shackle, WLL 55 ton": 539.6
}

st.sidebar.header("🔗 4. 와이어로프 및 샤클")
wire_spec = st.sidebar.selectbox("와이어로프 적용 규격", list(wire_data.keys()), index=7)
wire_breaking_load = wire_data[wire_spec]
st.sidebar.info(f"선택된 공칭 파단 하중: **{wire_breaking_load} kN**")

shackle_spec = st.sidebar.selectbox("샤클 적용 규격", list(shackle_data.keys()), index=4)
shackle_wll = shackle_data[shackle_spec]
st.sidebar.info(f"선택된 안전하중: **{shackle_wll} kN**")

# --- 계산 로직 ---
W_air = float(vol * gamma_c)
W_add = float(W_air * additional_load_factor)
F_suction = float(bottom_area * suction_factor)
P_basic = W_air + W_add + F_suction

P_total = float(P_basic * dynamic_factor)
angle_rad = math.radians(float(sling_angle))

if anchor_qty > 0 and math.sin(angle_rad) > 0:
    T_req = float((P_total * unequal_factor) / (anchor_qty * math.sin(angle_rad)))
else:
    T_req = 0.001 

A_s_dict = {"M20": 245.0, "M24": 353.0, "M30": 561.0, "M32": 646.3, "M36": 817.0}
A_s = A_s_dict[anchor_spec]
f_uk = 800.0  
phi_s = 0.75  

N_sk = float((A_s * f_uk) / 1000.0)  
N_sd = float(N_sk * phi_s)           

sf_anchor = float(N_sd / T_req) if T_req > 0 else 0.0
is_safe_anchor = sf_anchor >= 1.0

k_c = 10.0  
phi_c = 0.65  

N_ck = float((k_c * math.sqrt(fck) * (h_ef ** 1.5)) / 1000.0) 
N_cd = float(N_ck * phi_c) 

sf_concrete = float(N_cd / T_req) if T_req > 0 else 0.0
is_safe_concrete = sf_concrete >= 1.0

d_dict = {"M20": 20.0, "M24": 24.0, "M30": 30.0, "M32": 32.0, "M36": 36.0}
d = d_dict[anchor_spec]
phi_a = 0.65  

N_ak = float((tau_k * math.pi * d * h_ef) / 1000.0) 
N_ad = float(N_ak * phi_a) 

sf_bond = float(N_ad / T_req) if T_req > 0 else 0.0
is_safe_bond = sf_bond >= 1.0

wire_sf_target = 5.0
req_breaking_load = float(T_req * wire_sf_target) 
sf_wire_actual = float(wire_breaking_load / T_req) if T_req > 0 else 0.0
is_safe_wire = wire_breaking_load >= req_breaking_load

sf_shackle = float(shackle_wll / T_req) if T_req > 0 else 0.0
is_safe_shackle = sf_shackle >= 1.0

# --- 화면 출력 영역 ---
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
df_summary = pd.DataFrame(summary_data)
st.table(df_summary)

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

# =====================================================================
# ★ 통합 HTML 템플릿 생성 및 다운로드 UI
# =====================================================================
st.markdown("---")
st.subheader("🖨️ 구조 검토서 다운로드")

with st.spinner("보고서용 수식을 변환 중입니다..."):
    # 요약 표 HTML로 변환
    html_summary_table = df_summary.to_html(index=False, justify='center', escape=False).replace(
        '<table', '<table style="width:100%; border-collapse: collapse; text-align:center;" border="1"'
    )

    # HTML 템플릿 (Raw f-string 적용하여 수식 깨짐 방지 및 부착강도 설명 추가)
    html_report = rf"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
    <meta charset="utf-8">
    <title>수중 블록 인양 구조 검토서</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; color: #333; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; color: #1E3A8A; border-bottom: 3px solid #1E3A8A; padding-bottom: 10px; }}
        h2 {{ color: #2563EB; margin-top: 30px; border-left: 5px solid #2563EB; padding-left: 10px; }}
        h3 {{ color: #1E293B; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; font-size: 0.95em; background: #fff; }}
        th, td {{ border: 1px solid #CBD5E1; padding: 10px; text-align: center; }}
        th {{ background-color: #F8FAFC; color: #1E3A8A; font-weight: bold; }}
        .box {{ background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
        .math-box {{ background-color: #ffffff; padding: 15px; border: 1px solid #E2E8F0; border-radius: 5px; margin-top: 10px; margin-bottom: 20px; }}
        p {{ margin: 8px 0; }}
        .caption {{ font-size: 0.85em; color: #64748B; margin-top: 5px; margin-bottom: 10px; line-height: 1.4; background-color: #F1F5F9; padding: 10px; border-radius: 4px; border-left: 3px solid #94A3B8; }}
    </style>
    </head>
    <body>
        <h1>🏗️ 수중부 유공근고블록 및 피복블록 인양·제거 검토서</h1>
        
        <h2>1. 입력 제원 및 하중 조건</h2>
        <div class="box">
            <ul>
                <li><strong>블록 종류 :</strong> {block_type}</li>
                <li><strong>블록 체적 (V) :</strong> {vol:.2f} m³ | <strong>저면적 (A) :</strong> {bottom_area:.2f} m²</li>
                <li><strong>콘크리트 단위중량 (&gamma;<sub>c</sub>) :</strong> {gamma_c:.1f} kN/m³ | <strong>압축강도 (f<sub>ck</sub>) :</strong> {fck:.1f} MPa</li>
                <li><strong>인양점(앵커) 개수 (N) :</strong> {anchor_qty} EA | <strong>슬링 각도 (&theta;) :</strong> {sling_angle:.1f}&deg;</li>
            </ul>
        </div>

        <h2>2. 인양 장비 및 앵커 종합 검토 결과 요약</h2>
        <div style="overflow-x: auto;">
            {html_summary_table}
        </div>

        <h2>3. 상세 구조계산 및 수식 전개 과정</h2>
        
        <h3>가. 기본하중 산정 ($P_{{basic}}$)</h3>
        <div class="math-box">
            <p>$$ W_{{air}} = V \times \gamma_c = {vol:.2f} \times {gamma_c:.1f} = {W_air:.2f} \text{{ kN}} $$</p>
            <p>$$ W_{{add}} = W_{{air}} \times {additional_load_factor*100:.0f}\% = {W_air:.2f} \times {additional_load_factor:.2f} = {W_add:.2f} \text{{ kN}} $$</p>
            <p>$$ F_{{suction}} = A \times \text{{부착력계수}} = {bottom_area:.2f} \times {suction_factor:.1f} = {F_suction:.2f} \text{{ kN}} $$</p>
            <p>$$ P_{{basic}} = W_{{air}} + W_{{add}} + F_{{suction}} = {P_basic:.2f} \text{{ kN}} $$</p>
        </div>

        <h3>나. 총 인양하중 및 앵커 설계하중 산정</h3>
        <div class="math-box">
            <p>$$ P_{{total}} = P_{{basic}} \times \text{{동적계수}}(K_d) = {P_basic:.2f} \times {dynamic_factor:.2f} = {P_total:.2f} \text{{ kN}} $$</p>
            <p>$$ T_{{req}} = \frac{{P_{{total}} \times \text{{불균등계수}}(K_u)}}{{N \times \sin(\theta)}} = \frac{{{P_total:.2f} \times {unequal_factor:.2f}}}{{{anchor_qty} \times \sin({sling_angle}^\circ)}} = {T_req:.2f} \text{{ kN/EA}} $$</p>
        </div>

        <h3>다. 케미컬 앵커 및 콘크리트 안정성 검토</h3>
        <div class="math-box">
            <p><strong>① 앵커 강재 인장강도 검토 (Grade 8.8)</strong></p>
            <p>$$ N_{{s,d}} = \phi_s \times (A_s \times f_{{uk}}) \times 10^{{-3}} = {phi_s} \times ({A_s} \times 800) \times 10^{{-3}} = {N_sd:.2f} \text{{ kN}} $$</p>
            <p>$$ S.F = \frac{{N_{{s,d}}}}{{T_{{req}}}} = \frac{{{N_sd:.2f}}}{{{T_req:.2f}}} = {sf_anchor:.2f} \ge 1.0 \text{{ ({'안전' if is_safe_anchor else 'NG'})}} $$</p>
            <hr style="border: 0; border-top: 1px dashed #CBD5E1; margin: 15px 0;">
            <p><strong>② 콘크리트 브레이크아웃 파괴강도 검토</strong></p>
            <p>$$ N_{{c,k}} = k_c \times \sqrt{{f_{{ck}}}} \times h_{{ef}}^{{1.5}} \times 10^{{-3}} = 10.0 \times \sqrt{{{fck:.1f}}} \times {h_ef}^{{1.5}} \times 10^{{-3}} = {N_ck:.2f} \text{{ kN}} $$</p>
            <p>$$ N_{{c,d}} = \phi_c \times N_{{c,k}} = {phi_c} \times {N_ck:.2f} = {N_cd:.2f} \text{{ kN}} $$</p>
            <p>$$ S.F = \frac{{N_{{c,d}}}}{{T_{{req}}}} = \frac{{{N_cd:.2f}}}{{{T_req:.2f}}} = {sf_concrete:.2f} \ge 1.0 \text{{ ({'안전' if is_safe_concrete else 'NG'})}} $$</p>
            <hr style="border: 0; border-top: 1px dashed #CBD5E1; margin: 15px 0;">
            <p><strong>③ 콘크리트 부착 파괴강도 검토</strong></p>
            <div class="caption">
                ※ 특성 부착강도는 제원표 상에는 콘크리트 강도(C20/25 등)와 건조/습윤 상태에 따라 다양한 부착강도(일반적으로 10~15MPa 이상)가 제시되어 있으나, 본 검토서는 기존 구조물의 강도가 낮고(18MPa) 수중(Water-saturated) 환경이라는 제원표 상의 악조건(강도 저감 요소)을 모두 고려하여, 가장 안전하고 보수적인 수치로 환산 적용하였음.
            </div>
            <p>$$ N_{{a,d}} = \phi_a \times (\tau_k \cdot \pi \cdot d \cdot h_{{ef}}) \times 10^{{-3}} = {phi_a} \times ({tau_k} \times \pi \times {d} \times {h_ef}) \times 10^{{-3}} = {N_ad:.2f} \text{{ kN}} $$</p>
            <p>$$ S.F = \frac{{N_{{a,d}}}}{{T_{{req}}}} = \frac{{{N_ad:.2f}}}{{{T_req:.2f}}} = {sf_bond:.2f} \ge 1.0 \text{{ ({'안전' if is_safe_bond else 'NG'})}} $$</p>
        </div>

        <h3>라. 와이어로프 및 샤클 규격 검토</h3>
        <div class="math-box">
            <p><strong>① 와이어로프 안전성</strong> (안전율 = {wire_sf_target})</p>
            <p>$$ P_{{req}} = T_{{req}} \times S.F = {T_req:.2f} \times {wire_sf_target} = {req_breaking_load:.2f} \text{{ kN}} \le P_{{nom}} ({wire_breaking_load:.2f} \text{{ kN}}) \text{{ ({'안전' if is_safe_wire else 'NG'})}} $$</p>
            <hr style="border: 0; border-top: 1px dashed #CBD5E1; margin: 15px 0;">
            <p><strong>② 샤클 안전성</strong></p>
            <p>$$ T_{{req}} ({T_req:.2f} \text{{ kN}}) \le WLL ({shackle_wll:.2f} \text{{ kN}}) \text{{ ({'안전' if is_safe_shackle else 'NG'})}} $$</p>
        </div>
    </body>
    </html>
    """
    
    mhtml_data = convert_html_to_mhtml(html_report)

col_d1, col_d2 = st.columns(2)
with col_d1:
    st.download_button(
        label="📄 구조 검토서 다운로드 (HTML웹용)", 
        data=html_report.encode('utf-8'), 
        file_name="수중블록_인양구조_검토서.html", 
        mime="text/html", 
        use_container_width=True,
        key="btn_as_html"
    )
with col_d2:
    st.download_button(
        label="📝 구조 검토서 다운로드 (MS Word용)", 
        data=mhtml_data.encode('utf-8'), 
        file_name="수중블록_인양구조_검토서.doc", 
        mime="application/msword", 
        use_container_width=True,
        key="btn_as_word"
    )
