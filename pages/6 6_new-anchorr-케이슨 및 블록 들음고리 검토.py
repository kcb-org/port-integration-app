import streamlit as st
import math
import os
import base64
import urllib.parse
import re

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")
# 페이지 기본 설정
st.set_page_config(page_title="들음고리 SI 자동계산기", layout="wide")

# 깃허브 Raw 이미지 기본 주소 (kimchangbo/anchor-apps/main)
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/kimchangbo/anchor-apps/main/"

# =====================================================================
# ★ 보고서 생성기 (수식 깨짐 완벽 방지 + 마크다운 렌더러 탑재)
# =====================================================================
class ReportBuilder:
    def __init__(self, title_text="들음고리 구조검토 보고서"):
        self.html = f"""
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'>
        <title>{title_text}</title>
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script>
          MathJax = {{
            tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], processEscapes: true }},
            options: {{ ignoreHtmlClass: "tex2jax_ignore", processHtmlClass: "tex2jax_process" }}
          }};
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; padding: 20px; color: #333; max-width: 1200px; margin: auto; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 14px; background: white; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #f4f6f8; font-weight: bold; color: #333;}}
            h2 {{ color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 40px;}}
            h3 {{ color: #1e3a8a; margin-top: 25px; }}
            h4 {{ color: #34495e; font-weight: bold; margin-top: 20px;}}
            .eq {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #1e3a8a; margin: 15px 0; overflow-x: auto; font-size: 1.1em;}}
            p {{ margin: 8px 0; }}
            ul {{ margin-top: 5px; margin-bottom: 15px; padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            .info-box {{ background-color: #e8f0fe; border-left: 4px solid #1e3a8a; padding: 15px; margin: 15px 0; }}
            .success-box {{ background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; color: #155724; }}
            .error-box {{ background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; color: #721c24; }}
            
            /* UI와 동일한 커스텀 클래스 매칭 */
            .basis-tag {{ background-color: #e7f5ff; color: #1971c2; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; margin-left: 10px; }}
            .status-ok {{ color: #2f9e44; font-weight: bold; font-size: 1.2em; }}
            .status-ng {{ color: #e03131; font-weight: bold; font-size: 1.2em; }}
            .section-title {{ color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 30px; font-size: 1.17em; font-weight: bold;}}
            .total-box {{ background-color: #f1f8ff; padding: 10px; border-left: 4px solid #007bff; font-weight: bold; margin-top: 10px;}}
            .block-spec-box {{ border: 2px solid black; padding: 15px; margin-top: 15px; background-color: #ffffff;}}
            .block-spec-title {{ font-weight: bold; font-size: 1.1em; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px;}}
            .block-spec-list {{ list-style-type: none; padding-left: 10px; line-height: 1.8; font-size: 1em; margin: 0; }}
        </style>
        </head><body class="tex2jax_process">
        <h1 style='text-align:center;'>🏗️ {title_text}</h1><hr>
        """

    def _fmt(self, text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', str(text))
        return text.replace('\n', '<br>')

    def title(self, text, level=2):
        st.markdown(f"{'#' * level} {text}")
        self.html += f"<h{level}>{text}</h{level}>"

    def custom_html(self, html_str):
        st.markdown(html_str, unsafe_allow_html=True)
        self.html += html_str

    def md(self, text, unsafe_allow_html=False):
        st.markdown(text, unsafe_allow_html=unsafe_allow_html)
        html_out = ""
        in_list = False
        for line in text.split('\n'):
            if not line.strip(): continue
            content = line.strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            
            if content.startswith('* ') or content.startswith('- '):
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

    def latex(self, eq):
        st.latex(eq)
        self.html += f"<div class='eq'>$$ {eq} $$</div>"

    def get_html(self):
        return self.html + "</body></html>"

# 1. 케이슨 리프팅 케이블 데이터
CABLE_SPECS = {
    "E100L/F100L": {"D_mm": 33.3, "Pu_kN": 912.33, "Pa_kN": 547.40, "Desc": "7 x Ø11.1", "img": "E100-F100L 리프팅 케이블 제원.png"},
    "E130L/F130L": {"D_mm": 38.1, "Pu_kN": 1216.44, "Pa_kN": 729.86, "Desc": "7 x Ø12.7", "img": "E130-F130L 리프팅 케이블 제원.png"},
    "E160L/F160L": {"D_mm": 45.6, "Pu_kN": 1599.03, "Pa_kN": 959.42, "Desc": "7 x Ø15.2", "img": "E160-F160L 리프팅 케이블 제원.png"}
}

# 2. 블록 와이어 로프 데이터 (6 x Fi (25) IWRC (KS 14호))
WIRE_ROPE_SPECS = {
    "6 x Fi (25) IWRC (KS 14호) - 8.0 mm": {"D_mm": 8.0, "Pu_ton": 4.30},
    "6 x Fi (25) 단선 IWRC (KS 14호) - 9.0 mm": {"D_mm": 9.0, "Pu_ton": 5.45},
    "6 x Fi (25) IWRC (KS 14호) - 10.0 mm": {"D_mm": 10.0, "Pu_ton": 6.72},
    "6 x Fi (25) IWRC (KS 14호) - 11.2 mm": {"D_mm": 11.2, "Pu_ton": 8.44},
    "6 x Fi (25) IWRC (KS 14호) - 12.0 mm": {"D_mm": 12.0, "Pu_ton": 8.68},
    "6 x Fi (25) IWRC (KS 14호) - 14.0 mm": {"D_mm": 14.0, "Pu_ton": 13.20},
    "6 x Fi (25) IWRC (KS 14호) - 16.0 mm": {"D_mm": 16.0, "Pu_ton": 17.20},
    "6 x Fi (25) IWRC (KS 14호) - 20.0 mm": {"D_mm": 20.0, "Pu_ton": 26.90}
}

# CSS 스타일 설정
st.markdown("""
    <style>
    .basis-tag { background-color: #e7f5ff; color: #1971c2; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; margin-left: 10px; }
    .status-ok { color: #2f9e44; font-weight: bold; font-size: 1.2em; }
    .status-ng { color: #e03131; font-weight: bold; font-size: 1.2em; }
    .section-title { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 30px;}
    .total-box { background-color: #f1f8ff; padding: 10px; border-left: 4px solid #007bff; font-weight: bold; margin-top: 10px;}
    .block-spec-box { border: 2px solid black; padding: 15px; margin-top: 15px; background-color: #ffffff;}
    .block-spec-title { font-weight: bold; font-size: 1.1em; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px;}
    .block-spec-list { list-style-type: none; padding-left: 10px; line-height: 1.8; font-size: 1em; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# 이미지 안전 출력 함수
def display_image_safely(file_name, caption_text="", rep=None):
    if os.path.exists(file_name):
        st.image(file_name, caption=caption_text, use_container_width=True)
        if rep is not None:
            try:
                with open(file_name, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = "jpeg" if file_name.lower().endswith("jpg") else "png"
                img_html = f'<div style="text-align: center; margin-bottom: 15px;"><img src="data:image/{ext};base64,{b64}" style="max-width: 100%; height: auto;" /><br><i><small>{caption_text}</small></i></div>'
                rep.html += img_html
            except Exception:
                pass

# 이미지 가운데 정렬 (웹 UI 전용 - Base64 유지)
def display_centered_image_safely(file_name, width_px=350, rep=None):
    if os.path.exists(file_name):
        try:
            with open(file_name, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = "jpeg" if file_name.lower().endswith("jpg") else "png"
            html_str = f'<div style="text-align: center; margin-bottom: 15px;"><img src="data:image/{ext};base64,{b64}" style="width: {width_px}px; max-width: 100%; height: auto;" /></div>'
            st.markdown(html_str, unsafe_allow_html=True)
            if rep is not None:
                rep.html += html_str
            return True
        except Exception:
            pass
    return False

# 워드 문서용 이미지 블록 (엑스박스 방지를 위해 인터넷(GitHub) 절대 경로 URL 사용)
def get_word_img_block(file_name, caption, width_px="250", height_px="200"):
    encoded_name = urllib.parse.quote(file_name)
    img_url = f"{GITHUB_RAW_BASE}{encoded_name}"
    return f'<div style="text-align: center; padding: 5px; margin-bottom: 10px;"><img src="{img_url}" width="{width_px}" height="{height_px}" /><br><i><small>{caption}</small></i></div>'

def get_imbalance_factor(n):
    """들음고리 본수에 따른 불균등 계수(K) 자동 산정"""
    if n >= 5: return 1.80
    elif n == 4: return 1.33
    else: return 1.20

def main():
    st.title("🏗️ 케이슨 및 블록 들음고리 자동계산 (SI 단위계)")
    st.markdown("---")

    col_in, col_out = st.columns([1, 2], gap="large")

    # ==========================================
    # 왼쪽: 입력난
    # ==========================================
    with col_in:
        st.header("📋 설계 데이터 입력")
        category = st.radio("검토 대상 선택", ["케이슨(Caisson)", "블록(Block)"])
        
        st.markdown("<br>", unsafe_allow_html=True)

        if category == "케이슨(Caisson)":
            st.subheader("1. 케이슨 제원")
            W_kN = st.number_input("케이슨 자중 (W, kN)", value=14000.0, step=100.0, format="%.2f")
            A_m2 = st.number_input("저판 면적 (A, m²)", value=160.0, step=1.0, format="%.2f")
            
            st.subheader("2. 작업 조건 및 장비")
            crane = st.selectbox("해상기중기 용량", ["2,000톤급(24조, N=48)", "3,000톤급(32조, N=64)", "기타 (직접입력)"])
            
            if "2,000" in crane:
                N = 48
                sets = 24
                jo_text = "24조(PC 케이블 1조당 2개)"
            elif "3,000" in crane:
                N = 64
                sets = 32
                jo_text = "32조(PC 케이블 1조당 2개)"
            else:
                N = st.number_input("케이블 개수 (N)", value=32)
                sets = N // 2
                jo_text = f"{sets}조(PC 케이블 1조당 2개)"
            
            K = get_imbalance_factor(N)
            st.info(f"**자동 산정된 불균등 계수 (K) = {K}**")
            
            # --- [자동 선택 로직] 안전한 규격 미리 계산 ---
            W_prime = 0.05 * W_kN
            F = 3.0 * A_m2 
            Total_P = ((W_kN + W_prime + F) * K) / N
            
            default_idx = 0
            for idx, (k, s) in enumerate(CABLE_SPECS.items()):
                if Total_P <= s["Pa_kN"]:
                    default_idx = idx
                    break
            # -----------------------------------------------
            
            st.subheader("3. 리프팅 케이블 규격")
            spec_key = st.selectbox("Lifting Cable 규격 선택", list(CABLE_SPECS.keys()), index=default_idx)
            spec = CABLE_SPECS[spec_key]
            
            st.subheader("4. 재료 및 보정 계수")
            fck = st.number_input("콘크리트 설계강도 (fck, MPa)", value=35.0, step=1.0)
            
            col_rad1, col_rad2 = st.columns(2)
            with col_rad1:
                pc_reduction_str = st.radio("P.C강선 저하율 (이형철근 대비)", ["적용 (0.75)", "미적용 (1.0)"], key="pc_c")
                pc_factor = 0.75 if "0.75" in pc_reduction_str else 1.0
            with col_rad2:
                short_term_str = st.radio("단기하중 할증", ["적용 (1.5)", "미적용 (1.0)"], key="st_c")
                short_term_factor = 1.5 if "1.5" in short_term_str else 1.0

        else: # 블록 입력
            st.subheader("1. 블록 제원")
            block_shape = st.radio("블록 형태 선택", ["정형 (폭, 길이, 높이 입력)", "비정형 (자중, 면적 직접입력)"])
            
            if block_shape.startswith("정형"):
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    B_m = st.number_input("폭 (B, m)", value=1.50, step=0.1, format="%.2f")
                    L_m = st.number_input("길이 (L, m)", value=2.48, step=0.1, format="%.2f")
                with col_b2:
                    H_m = st.number_input("높이 (H, m)", value=0.80, step=0.1, format="%.2f")
                    unit_W = st.number_input("단위중량 (kN/m³)", value=22.6, step=0.1, format="%.1f")
                
                W_kN_b = B_m * L_m * H_m * unit_W
                A_m2_b = B_m * L_m
                st.success(f"💡 **자동 산정:** 자중 = {W_kN_b:,.2f} kN / 저면 면적 = {A_m2_b:,.2f} m²")
            else:
                W_kN_b = st.number_input("블록 자중 (W, kN)", value=59.12, step=1.0, format="%.2f")
                A_m2_b = st.number_input("저면 면적 (A, m²)", value=3.72, step=0.1, format="%.2f")
                B_m = L_m = H_m = unit_W = 0 
            
            st.subheader("2. 작업 조건")
            N_b = st.number_input("들음고리 본수 (N)", value=4, step=1)
            theta_deg = st.number_input("로프 각도 (θ, 도)", value=60.0, step=1.0)
            
            K_b = get_imbalance_factor(N_b)
            st.info(f"**자동 산정된 불균등 계수 (K) = {K_b}**")
            
            # --- [자동 선택 로직] 안전한 규격 미리 계산 ---
            W_prime_b = 0.05 * W_kN_b
            F_b = 3.0 * A_m2_b
            Total_W_b = W_kN_b + W_prime_b + F_b
            theta_rad = math.radians(theta_deg)
            Pi_b = (Total_W_b / (N_b * math.sin(theta_rad))) * K_b
            req_Pu = (3 * Pi_b) / 2
            
            default_idx_b = 0
            for idx, (k, s) in enumerate(WIRE_ROPE_SPECS.items()):
                if s["Pu_ton"] * 9.81 >= req_Pu:
                    default_idx_b = idx
                    break
            # -----------------------------------------------
            
            st.subheader("3. 재료 및 양생")
            fck_b = st.number_input("설계강도 (fck, MPa)", value=30.0, step=1.0)
            t_weeks = st.number_input("양생 기간 (주)", value=2, step=1)
            
            st.subheader("4. 상세 설계 조건")
            wire_key = st.selectbox("와이어 로프 규격 선택", list(WIRE_ROPE_SPECS.keys()), index=default_idx_b)
            selected_wire = WIRE_ROPE_SPECS[wire_key]
            
            hook_str = st.radio("갈고리 효과", ["적용 무 (m=1.0)", "적용 유 (m=1.5)"], index=0, key="hook_b")
            m_factor = 1.5 if "1.5" in hook_str else 1.0

    # ==========================================
    # 오른쪽: 결과 및 상세 풀이 과정
    # ==========================================
    with col_out:
        rep = ReportBuilder(title_text=f"들음고리 구조검토 보고서 ({category})")
        report_html_body = ""

        if category == "케이슨(Caisson)":
            is_safe = Total_P <= spec["Pa_kN"]
            status = "<span class='status-ok'>O.K ✅</span>" if is_safe else "<span class='status-ng'>N.G ❌ (규격 상향 필요)</span>"
            status_text = "<span style='color: green; font-weight: bold;'>O.K</span>" if is_safe else "<span style='color: red; font-weight: bold;'>N.G (규격 상향 필요)</span>"
            
            tau_base = 0.202 * math.sqrt(fck) 
            tau_oa = tau_base * pc_factor * short_term_factor 
            
            L_req = (Total_P * 1000) / (math.pi * spec["D_mm"] * tau_oa)
            L_total_calc_exact = (L_req / 1000) + 0.3 + 1.0 
            L_total_calc = round(L_total_calc_exact, 1)

            rep.title("📝 케이슨 들음고리 구조검토 보고서", level=2)
            
            cont_summary = st.container()
            cont_detail_1 = st.container()
            cont_detail_2 = st.container()
            cont_detail_3 = st.container()
            cont_decision = st.container()
            
            with cont_decision:
                rep.custom_html("<h3 class='section-title'>5. 설계 반영 매입길이 결정</h3>")
                rep.info(f"💡 **설계 반영 길이 가이드:** \n\n순수 매입장({L_req/1000:.2f} m) + 상부 노출부(0.3 m) + 시공 여유(1.0 m) = **최종 권장 {L_total_calc:.1f} m 이상**")
                
                L_final_input = st.number_input("📏 1본당 도면에 반영할 최종 매입길이 확정 (m)", value=float(L_total_calc), step=0.1)
                
                rep.custom_html(f"<div class='total-box'>총 매입길이 = 최종 매입길이({L_final_input:.2f} m) × {sets}조</div>")

            with cont_summary:
                # 케이슨 인양 삽도: 웹 UI 가운데 정렬
                if not display_centered_image_safely("케이슨 인양 삽도.jpg", 350, rep):
                    display_centered_image_safely("케이슨 인양 삽도.png", 350, rep)
                
                rep.custom_html("<h3 class='section-title'>1. 검토결과 요약</h3>")
                summary_html = f"""
                <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.05em;" border="1">
                    <tr style="background-color: #f1f8ff; color: #1e3a8a;">
                        <th style="padding: 10px;">항목</th><th style="padding: 10px;">적용값</th>
                    </tr>
                    <tr><td style="padding: 8px;">1본당 설계 하중 (P)</td><td style="padding: 8px; font-weight: bold;">{Total_P:,.2f} kN</td></tr>
                    <tr><td style="padding: 8px;">적용 케이블 규격</td><td style="padding: 8px; font-weight: bold;">{spec_key}</td></tr>
                    <tr><td style="padding: 8px;">1본당 최종 매입길이</td><td style="padding: 8px; font-weight: bold; color: #d9480f;">{L_final_input:.2f} m</td></tr>
                    <tr><td style="padding: 8px;">총 매입길이</td><td style="padding: 8px; font-weight: bold;">{L_final_input:.2f} m × {sets}조</td></tr>
                </table>
                """
                rep.custom_html(summary_html)

            with cont_detail_1:
                rep.custom_html("<h3 class='section-title'>2. 설계 하중 산정</h3>")
                rep.md("**[적용 공식]**")
                rep.latex(r"P = \frac{(W + W' + F) \times K}{N}")
                rep.md(r"""
                **[기호 설명]**
                - $P$ : 케이블 1개당 작용 하중 (kN/ea)
                - $W$ : 케이슨 자중 (kN)
                - $W'$ : 부가중량 ($0.05 \times W$) <span class='basis-tag'>항만설계기준</span>
                - $F$ : 저면 부착력 ($3.0 \text{ kN/m}^2 \times A$) <span class='basis-tag'>항만설계기준</span>
                - $K$ : 불균등 계수 (다점 리프팅 보정)
                - $N$ : 적용된 들음고리 케이블 본수
                """, unsafe_allow_html=True)
                rep.md("**[상세 풀이]**")
                rep.md(f"- **들음고리 개수:** {crane} 적용 시, **{jo_text}** 적용")
                rep.latex(rf"P = \frac{{({W_kN:,.2f} + {W_prime:,.2f} + {F:,.2f}) \times {K}}}{{{N}}} = {Total_P:.2f} \text{{ kN/ea}}")

            with cont_detail_2:
                rep.custom_html("<h3 class='section-title'>3. 사용 규격 및 안전성 검토</h3>")
                col_img1, col_img2 = st.columns(2)
                with col_img1: display_image_safely("리프팅 케이블 구성 및 표준규격.png", "리프팅 케이블 구성", rep)
                with col_img2: display_image_safely(spec["img"], f"{spec_key} 제원 상세", rep)
                rep.md("**[적용 공식]**")
                rep.latex(r"P \le P_a \quad (단, P_a = 0.6 \times P_u)")
                rep.md("**[상세 풀이 및 검토 결과]**")
                rep.md(f"- **선택 규격:** {spec_key} ({spec['Desc']})")
                rep.md(rf"- **허용하중 ($P_a$):** $0.6 \times {spec['Pu_kN']:,.2f} = {spec['Pa_kN']:,.2f} \text{{ kN}}$")
                rep.md(rf"**결과 판정:** 작용하중 $P ({Total_P:.2f} \text{{ kN}}) \le$ 허용하중 $P_a ({spec['Pa_kN']:,.2f} \text{{ kN}}) \rightarrow$ {status}", unsafe_allow_html=True)

            with cont_detail_3:
                rep.custom_html("<h3 class='section-title'>4. 필요 매입길이 (Embedment Length) 산정</h3>")
                display_image_safely("리프팅 케이블 부품규격.png", "FITTING ANCHOR 및 부품 규격", rep)
                rep.md("**[적용 공식]**")
                rep.latex(r"\tau = 0.202 \times \sqrt{f_{ck}} \quad \text{,  } \quad \tau_{oa} = \tau \times \text{저하율} \times \text{할증계수}")
                rep.latex(r"L_{req} = \frac{P \times 10^3}{\pi \times D \times \tau_{oa}}")
                rep.md("**[상세 풀이]**")
                rep.md(rf"- **콘크리트 부착강도 ($\tau$):** $0.202 \times \sqrt{{{fck}}} = {tau_base:.3f} \text{{ MPa}}$")
                rep.md(r"*(참고 : 기존 톤단위식 $\tau = 0.64 \times \sqrt{f_{ck}} \text{ (kg/cm}^2\text{)}$)*")
                rep.md(rf"- **허용 부착응력 ($\tau_{{oa}}$):** ${tau_base:.3f} \times {pc_factor} \times {short_term_factor} = {tau_oa:.3f} \text{{ MPa}}$")
                rep.md(rf"- **최소 매입길이 ($L_{{req}}$):**")
                rep.latex(rf"L_{{req}} = \frac{{{Total_P:.2f} \times 10^3}}{{\pi \times {spec['D_mm']} \times {tau_oa:.3f}}} = {L_req:.1f} \text{{ mm}} \approx {L_req/1000:.2f} \text{{ m}}")

            # === 워드 문서용 HTML 구성 (케이슨 모든 화면 포함) ===
            intro_file = "케이슨 인양 삽도.png"
            encoded_intro = urllib.parse.quote(intro_file)
            img_intro_block = f'<div style="text-align: center; margin-bottom: 10px;"><img src="{GITHUB_RAW_BASE}{encoded_intro}" width="220" height="280" /></div>'
            
            img1_block = get_word_img_block("리프팅 케이블 구성 및 표준규격.png", "리프팅 케이블 구성", "280", "200")
            img2_block = get_word_img_block(spec["img"], f"{spec_key} 제원 상세", "280", "200")
            
            images_table = ""
            if img1_block or img2_block:
                images_table = f"""
                <table style="width: 100%; border: none; table-layout: fixed; margin-bottom: 10px;">
                    <tr>
                        <td style="width: 50%; border: none; vertical-align: top; text-align: center;">{img1_block}</td>
                        <td style="width: 50%; border: none; vertical-align: top; text-align: center;">{img2_block}</td>
                    </tr>
                </table>
                """
                
            img3_block = get_word_img_block("리프팅 케이블 부품규격.png", "FITTING ANCHOR 및 부품 규격", "500", "180")

            report_html_body = f"""
            {img_intro_block}
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">1. 검토결과 요약</h3>
            {summary_html}
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">2. 설계 하중 산정</h3>
            <p><b>[적용 공식]</b><br> P = (W + W' + F) × K / N</p>
            <p><b>[기호 설명]</b><br>
            - P : 케이블 1개당 작용 하중 (kN/ea)<br>
            - W : 케이슨 자중 (kN)<br>
            - W' : 부가중량 (0.05 × W) [항만설계기준]<br>
            - F : 저면 부착력 (3.0 kN/m² × A) [항만설계기준]<br>
            - K : 불균등 계수 (다점 리프팅 보정)<br>
            - N : 적용된 들음고리 케이블 본수</p>
            <p><b>[상세 풀이]</b><br>
            - <b>들음고리 개수:</b> {crane} 적용 시, <b>{jo_text}</b> 적용<br>
            P = ({W_kN:,.2f} + {W_prime:,.2f} + {F:,.2f}) × {K} / {N} = <b>{Total_P:.2f} kN/ea</b></p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">3. 사용 규격 및 안전성 검토</h3>
            {images_table}
            <p><b>[적용 공식]</b><br> P ≤ Pa (단, Pa = 0.6 × Pu)</p>
            <p><b>[상세 풀이 및 검토 결과]</b><br>
            - <b>선택 규격:</b> {spec_key} ({spec['Desc']})<br>
            - <b>허용하중 (Pa):</b> 0.6 × {spec['Pu_kN']:,.2f} = {spec['Pa_kN']:,.2f} kN<br>
            - <b>결과 판정:</b> 작용하중 P ({Total_P:.2f} kN) ≤ 허용하중 Pa ({spec['Pa_kN']:,.2f} kN) → {status_text}</p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">4. 필요 매입길이 (Embedment Length) 산정</h3>
            {img3_block}
            <p><b>[적용 공식]</b><br>
            τ = 0.202 × √fck  ,   τ_oa = τ × 저하율 × 할증계수<br>
            L_req = (P × 10³) / (π × D × τ_oa)</p>
            <p><b>[상세 풀이]</b><br>
            - <b>콘크리트 부착강도 (τ):</b> 0.202 × √{fck} = {tau_base:.3f} MPa<br>
            <i>(참고 : 기존 톤단위식 τ = 0.64 × √fck (kg/cm²))</i><br>
            - <b>허용 부착응력 (τ_oa):</b> {tau_base:.3f} × {pc_factor} × {short_term_factor} = {tau_oa:.3f} MPa<br>
            - <b>최소 매입길이 (L_req):</b><br>
            L_req = ({Total_P:.2f} × 10³) / (π × {spec['D_mm']} × {tau_oa:.3f}) = {L_req:.1f} mm ≈ {L_req/1000:.2f} m</p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">5. 설계 반영 매입길이 결정</h3>
            <p>💡 <b>설계 반영 길이 가이드:</b><br>
            순수 매입장({L_req/1000:.2f} m) + 상부 노출부(0.3 m) + 시공 여유(1.0 m) = <b>최종 권장 {L_total_calc:.1f} m 이상</b></p>
            <div style="background-color: #f1f8ff; padding: 10px; border-left: 4px solid #007bff; font-weight: bold; margin-top: 10px;">
                총 매입길이 = 최종 매입길이({L_final_input:.2f} m) × {sets}조
            </div>
            """

        else:
            # [블록 계산 로직]
            T_b = (Total_W_b / N_b) * K_b
            
            y_factor = t_weeks / (1.203 + 0.7 * t_weeks - 0.000195 * (t_weeks**2))
            fcky_b = y_factor * fck_b
            
            tau_oa_b = (0.28 * (fcky_b**(2/3)) * 0.4 * 9.81) 
            
            D_mm_b = selected_wire["D_mm"]
            Pu_kN_b = selected_wire["Pu_ton"] * 9.81
            
            L_req_b = (T_b * 1000) / (2 * math.pi * (D_mm_b * 0.1) * tau_oa_b * m_factor)
            
            L_pure_m = L_req_b / 1000
            L_total_calc_b_exact = (L_pure_m * 2) + 0.3
            L_total_calc_b = round(L_total_calc_b_exact, 1)

            rep.title("📝 블록 들음고리 구조검토 보고서", level=2)
            
            cont_summary = st.container()
            cont_detail_1 = st.container()
            cont_detail_2 = st.container()
            cont_detail_3 = st.container()
            cont_decision = st.container()
            
            with cont_decision:
                rep.custom_html("<h3 class='section-title'>5. 설계 반영 매입길이 결정</h3>")
                rep.info(f"💡 **설계 반영 길이 가이드:** \n\n순수 매입장({L_pure_m:.2f} m) $\\times$ 2 + 상부 노출부 및 시공 여유(약 0.3m) = **최종 권장 {L_total_calc_b:.1f} m 이상**")
                
                L_final_input_b = st.number_input("📏 1본당 도면에 반영할 최종 매입장 길이 확정 (m)", value=float(L_total_calc_b), step=0.1)
                total_len_b = L_final_input_b * N_b
                total_margin_b = total_len_b * 1.05
                
                if L_final_input_b >= L_total_calc_b:
                    rep.success(f"**✅ 1본당 최종 매입길이 확정:** **{L_final_input_b:.2f} m** (구조적 요구 및 시공 여유 충족)")
                    rep.custom_html(f"<div class='total-box'>총 매입길이 = 최종 매입길이({L_final_input_b:.2f} m) × {N_b}본 = {total_len_b:.2f} m (Add 5% {total_margin_b:.2f} m)</div>")
                else:
                    rep.error(f"**⚠️ 경고:** 확정하신 길이({L_final_input_b:.2f} m)가 권장되는 최종 최소 길이({L_total_calc_b:.1f} m)보다 짧습니다!")

            with cont_summary:
                rep.custom_html("<h3 class='section-title'>1. 검토결과 요약</h3>")
                summary_b_html = f"""
                <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.05em;" border="1">
                    <tr style="background-color: #f1f8ff; color: #1e3a8a;">
                        <th style="padding: 10px;">항목</th><th style="padding: 10px;">적용값</th>
                    </tr>
                    <tr><td style="padding: 8px;">총 설계 하중 (∑W)</td><td style="padding: 8px; font-weight: bold;">{Total_W_b:,.2f} kN</td></tr>
                    <tr><td style="padding: 8px;">적용 와이어 로프 규격</td><td style="padding: 8px; font-weight: bold;">{wire_key}</td></tr>
                    <tr><td style="padding: 8px;">1본당 최종 매입길이</td><td style="padding: 8px; font-weight: bold; color: #d9480f;">{L_final_input_b:.2f} m</td></tr>
                    <tr><td style="padding: 8px;">총 매입길이<br><span style="font-size: 0.8em; font-weight: normal;">({N_b}본 기준)</span></td><td style="padding: 8px; font-weight: bold;">{total_len_b:.2f} m<br><span style="font-size: 0.8em; font-weight: normal; color: gray;">(5% 할증 적용 시: {total_margin_b:.2f} m)</span></td></tr>
                </table>
                """
                rep.custom_html(summary_b_html)

                if block_shape.startswith("정형"):
                    block_title_str = f"{L_m:.2f}L × {H_m:.2f}H × {B_m:.2f}B 콘크리트블록"
                    gamma_c_str = f"{unit_W} kN/m³"
                else:
                    block_title_str = "비정형 콘크리트블록"
                    gamma_c_str = "직접 입력 (해당 없음)"

                # 블록 모식도 이미지 (웹용 Base64, 워드용 깃허브 원격 링크)
                img_file = "와이어로프 들음고리 모식도.png"
                img_html_ui = ""
                
                if os.path.exists(img_file):
                    try:
                        with open(img_file, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode()
                        img_html_ui = f'<img src="data:image/png;base64,{img_b64}" style="width: 250px; height: auto; object-fit: contain; image-rendering: crisp-edges;" />'
                    except Exception:
                        pass
                
                # 워드용은 파일이 로컬에 없더라도 깃허브 링크 강제 지정
                encoded_block_img = urllib.parse.quote(img_file)
                img_html_word = f'<img src="{GITHUB_RAW_BASE}{encoded_block_img}" width="200" height="200" />'

                block_spec_ui = f"""
                <div class="block-spec-box">
                    <div class="block-spec-title">{block_title_str}</div>
                    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 30px;">
                        <div>
                            <ul class="block-spec-list">
                                <li>ㆍ 달아올림강재의 본수(N) : {N_b} 개</li>
                                <li>ㆍ 달아올림강재의 종류 : {wire_key}</li>
                                <li>ㆍ 불균등 계수(k) : {K_b}</li>
                                <li>ㆍ 로프와 블록 상면과의 각도(θ) : {theta_deg}</li>
                                <li>ㆍ Concrete Block의 설계강도(fck) : {fck_b:.2f} MPa</li>
                                <li>ㆍ Concrete Block의 단위중량(γ_c) : {gamma_c_str}</li>
                                <li>ㆍ 갈고리 효과(유:m=1.5, 무:m=1.0) : {m_factor}</li>
                                <li>ㆍ 양생기간(주) : <span style="color:red; font-weight:bold;">{t_weeks}</span></li>
                            </ul>
                        </div>
                        <div style="text-align: left;">
                            {img_html_ui}
                        </div>
                    </div>
                </div>
                """
                rep.custom_html(block_spec_ui)
                
                block_spec_word = f"""
                <div class="block-spec-box">
                    <div class="block-spec-title">{block_title_str}</div>
                    <table style="border: none; margin: 0; padding: 0; width: 100%;">
                        <tr>
                            <td style="border: none; vertical-align: middle; width: 60%; padding-right: 10px;">
                                <ul class="block-spec-list">
                                    <li>ㆍ 달아올림강재의 본수(N) : {N_b} 개</li>
                                    <li>ㆍ 달아올림강재의 종류 : {wire_key}</li>
                                    <li>ㆍ 불균등 계수(k) : {K_b}</li>
                                    <li>ㆍ 로프와 블록 상면과의 각도(θ) : {theta_deg}</li>
                                    <li>ㆍ Concrete Block의 설계강도(fck) : {fck_b:.2f} MPa</li>
                                    <li>ㆍ Concrete Block의 단위중량(γ_c) : {gamma_c_str}</li>
                                    <li>ㆍ 갈고리 효과(유:m=1.5, 무:m=1.0) : {m_factor}</li>
                                    <li>ㆍ 양생기간(주) : <span style="color:red; font-weight:bold;">{t_weeks}</span></li>
                                </ul>
                            </td>
                            <td style="border: none; text-align: left; vertical-align: middle; width: 40%;">
                                {img_html_word}
                            </td>
                        </tr>
                    </table>
                </div>
                """

            with cont_detail_1:
                rep.custom_html("<h3 class='section-title'>2. 설계 하중 산정</h3>")
                rep.md("**[적용 공식]**")
                rep.latex(r"\sum W = W + W' + F")
                rep.md(r"""
                **[기호 설명]**
                - $W$ : 블록의 자중 (kN)
                - $W'$ : 기타 증가 하중 ($0.05 \times W$) <span class='basis-tag'>항만설계기준</span>
                - $F$ : 저면 부착력 ($3.0 \text{ kN/m}^2 \times A$) <span class='basis-tag'>항만설계기준</span>
                """, unsafe_allow_html=True)
                rep.md("**[상세 풀이]**")
                
                if block_shape.startswith("정형"):
                    rep.md(rf"- 블록 자중 ($W$): 폭 $\times$ 길이 $\times$ 높이 $\times$ 단위중량 = ${B_m} \times {L_m} \times {H_m} \times {unit_W} = {W_kN_b:,.2f} \text{{ kN}}$")
                    rep.md(rf"- 저면 면적 ($A$): 폭 $\times$ 길이 = ${B_m} \times {L_m} = {A_m2_b:,.2f} \text{{ m}}^2$")
                else:
                    rep.md(rf"- 블록 자중 ($W$): ${W_kN_b:,.2f} \text{{ kN}}$")
                    rep.md(rf"- 저면 면적 ($A$): ${A_m2_b:,.2f} \text{{ m}}^2$")
                    
                rep.md(rf"- 기타 증가 하중 ($W'$): $0.05 \times {W_kN_b:,.2f} = {W_prime_b:,.2f} \text{{ kN}}$")
                rep.md(rf"- 저면 부착력 ($F$): $3.0 \times {A_m2_b:.2f} = {F_b:,.2f} \text{{ kN}}$")
                rep.md(rf"- **총 인양 하중 ($\sum W$):** ${W_kN_b:,.2f} + {W_prime_b:,.2f} + {F_b:,.2f} = {Total_W_b:,.2f} \text{{ kN}}$")
                rep.md(rf"- **불균등 계수 ($k$):** {K_b} (본편 1-6 기준: 5점 이상 1.8, 4점 1.33, 2~3점 1.2 적용) <span class='basis-tag'>항만설계기준</span>", unsafe_allow_html=True)

            with cont_detail_2:
                rep.custom_html("<h3 class='section-title'>3. 와이어 로프 인양 응력 및 안전성 검토</h3>")
                rep.md("**[적용 공식]**")
                rep.latex(r"P_i = \frac{\sum W}{N \times \sin \theta} \times k \quad \text{(응력 산정용)}")
                rep.md(r"""
                **[기호 설명]**
                - $P_i$ : 인양 각도를 고려하여 로프 1점에 걸리는 경사 장력 (kN)
                - $T$ : 로프가 콘크리트에서 뽑히려는 힘에 저항하기 위한 연직 하중 (kN)
                - $k$ : 불균등 계수
                """)
                rep.md("**[상세 풀이]**")
                rep.latex(rf"P_i = \frac{{{Total_W_b:,.2f}}}{{{N_b} \times \sin({theta_deg}^\circ)}} \times {K_b} = {Pi_b:.2f} \text{{ kN/ea}}")
                
                is_wire_safe = Pu_kN_b >= req_Pu
                wire_status = "<span class='status-ok'>O.K ✅</span>" if is_wire_safe else "<span class='status-ng'>N.G ❌ (규격 상향 필요)</span>"
                wire_status_text = "<span style='color: green; font-weight: bold;'>O.K</span>" if is_wire_safe else "<span style='color: red; font-weight: bold;'>N.G (규격 상향 필요)</span>"
                
                rep.md("**[와이어 로프 안전성 검토]**")
                rep.md(rf"- **적용 규격:** {wire_key} (공칭 파단하중 $P_u$: {selected_wire['Pu_ton']} ton $\times 9.81 = {Pu_kN_b:.2f} \text{{ kN}}$)")
                rep.latex(r"P_u \ge \frac{3 \times P_i}{2} \quad \text{(안전율 3, U자형 매입으로 2가닥 지지 조건)}")
                rep.md(rf"**결과 판정:** 파단하중 $P_u ({Pu_kN_b:.2f} \text{{ kN}}) \ge$ 요구하중 $({req_Pu:.2f} \text{{ kN}}) \rightarrow$ {wire_status}", unsafe_allow_html=True)
            
            with cont_detail_3:
                rep.custom_html("<h3 class='section-title'>4. 필요 매입장 (Embedment Length) 산정</h3>")
                rep.md("**[적용 공식]**")
                rep.latex(rf"T = \frac{{{Total_W_b:,.2f}}}{{{N_b}}} \times {K_b} = {T_b:.2f} \text{{ kN/ea}}")
                rep.latex(r"y = \frac{t}{1.203 + 0.7t - 0.000195t^2} \quad \text{(양생 보정계수)}")
                rep.latex(r"\tau_{oa} = 0.28 \times (f_{ck} \times y)^{2/3} \times 0.4 \times 9.81")
                rep.latex(r"L_{req} = \frac{T \times 10^3}{2\pi \times (D \times 0.1) \times \tau_{oa} \times m}")

                rep.md(r"""
                **[기호 설명]**
                - $y$ : 양생 일수($t$주)에 따른 콘크리트 강도 발현율 보정 계수 (강도비)
                - $\tau_{oa}$ : 허용 부착응력 (MPa)
                - $L_{req}$ : 구조적 최소 매입 길이 (mm)
                - $D \times 0.1$ : 와이어로프 직경(mm)을 단위 맞춤을 위해 보정(cm 환산 효과) 적용
                - $m$ : 갈고리 효과 계수 (유: 1.5, 무: 1.0)
                """)

                rep.md("**[상세 풀이]**")
                rep.md(rf"- **양생 보정계수 ($y$):**")
                rep.latex(rf"y = \frac{{{t_weeks}}}{{1.203 + 0.7({t_weeks}) - 0.000195({t_weeks})^2}} = {y_factor:.3f}")
                rep.md(rf"- 보정 강도 ($f_{{ck\_y}}$): ${fck_b} \times {y_factor:.3f} = {fcky_b:.2f} \text{{ MPa}}$")
                rep.md(rf"- **허용 부착응력 ($\tau_{{oa}}$):**")
                rep.latex(rf"\tau_{{oa}} = 0.28 \times ({fcky_b:.2f})^{{2/3}} \times 0.4 \times 9.81 = {tau_oa_b:.3f} \text{{ MPa (N/mm}}^2\text{{)}}")
                rep.md(r"*(참고 : 기존 톤단위식 $\tau_{oa} = 0.28 \times f_{cky}^{2/3} \times 0.4 \times 9.8 \text{ kg/cm}^2$)*")
                rep.md(rf"- **최소 매입길이 ($L_{{req}}$):**")
                rep.latex(rf"L_{{req}} = \frac{{{T_b:.2f} \times 10^3}}{{2\pi \times ({D_mm_b} \times 0.1) \times {tau_oa_b:.3f} \times {m_factor}}} = {L_req_b:.1f} \text{{ mm}} \approx {L_pure_m:.2f} \text{{ m}}")

            # === 워드 문서용 HTML 구성 (블록 모든 화면 포함) ===
            w_detail_html = f"- 블록 자중 (W): 폭 × 길이 × 높이 × 단위중량 = {B_m} × {L_m} × {H_m} × {unit_W} = {W_kN_b:,.2f} kN<br>- 저면 면적 (A): 폭 × 길이 = {B_m} × {L_m} = {A_m2_b:,.2f} m²" if block_shape.startswith("정형") else f"- 블록 자중 (W): {W_kN_b:,.2f} kN<br>- 저면 면적 (A): {A_m2_b:,.2f} m²"
            
            report_html_body = f"""
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">1. 검토결과 요약</h3>
            {summary_b_html}
            {block_spec_word}
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">2. 설계 하중 산정</h3>
            <p><b>[적용 공식]</b><br> ∑ W = W + W' + F</p>
            <p><b>[기호 설명]</b><br>
            - W : 블록의 자중 (kN)<br>
            - W' : 기타 증가 하중 (0.05 × W) [항만설계기준]<br>
            - F : 저면 부착력 (3.0 kN/m² × A) [항만설계기준]</p>
            <p><b>[상세 풀이]</b><br>
            {w_detail_html}<br>
            - 기타 증가 하중 (W'): 0.05 × {W_kN_b:,.2f} = {W_prime_b:,.2f} kN<br>
            - 저면 부착력 (F): 3.0 × {A_m2_b:.2f} = {F_b:,.2f} kN<br>
            - <b>총 인양 하중 (∑W):</b> {W_kN_b:,.2f} + {W_prime_b:,.2f} + {F_b:,.2f} = <b>{Total_W_b:,.2f} kN</b><br>
            - <b>불균등 계수 (k):</b> {K_b} (본편 1-6 기준: 5점 이상 1.8, 4점 1.33, 2~3점 1.2 적용) [항만설계기준]</p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">3. 와이어 로프 인양 응력 및 안전성 검토</h3>
            <p><b>[적용 공식]</b><br>
            P_i = (∑ W) / (N × sin θ) × k  (응력 산정용)</p>
            <p><b>[기호 설명]</b><br>
            - P_i : 인양 각도를 고려하여 로프 1점에 걸리는 경사 장력 (kN)<br>
            - T : 로프가 콘크리트에서 뽑히려는 힘에 저항하기 위한 연직 하중 (kN)<br>
            - k : 불균등 계수</p>
            <p><b>[상세 풀이]</b><br>
            P_i = {Total_W_b:,.2f} / ({N_b} × sin({theta_deg}°)) × {K_b} = {Pi_b:.2f} kN/ea</p>
            <p><b>[와이어 로프 안전성 검토]</b><br>
            - <b>적용 규격:</b> {wire_key} (공칭 파단하중 P_u: {selected_wire['Pu_ton']} ton × 9.81 = {Pu_kN_b:.2f} kN)<br>
            - P_u ≥ (3 × P_i) / 2 (안전율 3, U자형 매입으로 2가닥 지지 조건)<br>
            - <b>결과 판정:</b> 파단하중 P_u ({Pu_kN_b:.2f} kN) ≥ 요구하중 ({req_Pu:.2f} kN) → {wire_status_text}</p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">4. 필요 매입장 (Embedment Length) 산정</h3>
            <p><b>[적용 공식]</b><br>
            T = ({Total_W_b:,.2f} / {N_b}) × {K_b} = {T_b:.2f} kN/ea<br>
            y = t / (1.203 + 0.7t - 0.000195t²) (양생 보정계수)<br>
            τ_oa = 0.28 × (f_ck × y)^(2/3) × 0.4 × 9.81<br>
            L_req = (T × 10³) / (2π × (D × 0.1) × τ_oa × m)</p>
            <p><b>[상세 풀이]</b><br>
            - <b>양생 보정계수 (y):</b> y = {t_weeks} / (1.203 + 0.7({t_weeks}) - 0.000195({t_weeks})²) = {y_factor:.3f}<br>
            - <b>보정 강도 (fck_y):</b> {fck_b} × {y_factor:.3f} = {fcky_b:.2f} MPa<br>
            - <b>허용 부착응력 (τ_oa):</b> τ_oa = 0.28 × ({fcky_b:.2f})^(2/3) × 0.4 × 9.81 = {tau_oa_b:.3f} MPa (N/mm²)<br>
            <i>(참고 : 기존 톤단위식 τ_oa = 0.28 × f_cky^(2/3) × 0.4 × 9.8 kg/cm²)</i><br>
            - <b>최소 매입길이 (L_req):</b><br>
            L_req = ({T_b:.2f} × 10³) / (2π × ({D_mm_b} × 0.1) × {tau_oa_b:.3f} × {m_factor}) = {L_req_b:.1f} mm ≈ {L_pure_m:.2f} m</p>
            
            <h3 style="color: #1e3a8a; border-bottom: 1px solid #1e3a8a;">5. 설계 반영 매입길이 결정</h3>
            <p>💡 <b>설계 반영 길이 가이드:</b><br>
            순 매입장({L_pure_m:.2f} m) × 2 + 상부 노출부 및 시공 여유(약 0.3m) = <b>최종 권장 {L_total_calc_b:.1f} m 이상</b></p>
            <div style="background-color: #f1f8ff; padding: 10px; border-left: 4px solid #007bff; font-weight: bold; margin-top: 10px;">
                총 매입길이 = 최종 매입길이({L_final_input_b:.2f} m) × {N_b}본 = {total_len_b:.2f} m (Add 5% {total_margin_b:.2f} m)
            </div>
            """

        # ==========================================
        # 하단: 한글/Word 보고서 및 통합 HTML 보고서 다운로드 기능
        # ==========================================
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.subheader("📥 산출 보고서 다운로드")
        st.caption("아래 버튼을 클릭하여 원하는 형식의 보고서를 다운로드하세요.")
        
        full_report_html = f"""
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head>
            <meta charset='utf-8'>
            <title>구조검토 보고서</title>
            <style>
                body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; font-size: 11pt; }}
                h1 {{ color: #1e3a8a; text-align: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; }}
                h3 {{ color: #1e3a8a; margin-top: 25px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f1f8ff; text-align: center; }}
                p {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>들음고리 구조검토 보고서 ({category})</h1>
            {report_html_body}
        </body>
        </html>
        """
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                label="📄 구조검토 보고서 다운로드 (.doc)",
                data=full_report_html.encode('utf-8'),
                file_name=f"들음고리_구조검토보고서_{category[:3]}.doc",
                mime="application/msword",
                use_container_width=True
            )
            
        with col_dl2:
            st.download_button(
                label="📄 통합 산정 보고서 다운로드 (.html)",
                data=rep.get_html().encode('utf-8'),
                file_name=f"들음고리_통합산정보고서_{category[:3]}.html",
                mime="text/html",
                help="클릭 시 수식이 완벽히 복원된 HTML 형태의 보고서를 다운로드합니다.",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
