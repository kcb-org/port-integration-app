import streamlit as st
import math
import pandas as pd
import numpy as np
import os
import urllib.request
import io
import base64
import re
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy.interpolate import griddata 
from matplotlib.ticker import MultipleLocator, LogLocator, NullFormatter

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보, 유현상, 이종태, 나제민]")
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
# ★ 보고서 생성기
# =====================================================================
class ReportBuilder:
    def __init__(self, title_text="피복재 및 소파블록 통합 검토 보고서"):
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
            .warning-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; color: #856404; }}
        </style>
        </head><body class="tex2jax_process">
        <h1 style='text-align:center;'>🌊 {title_text}</h1><hr>
        """

    def _fmt(self, text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', str(text))
        return text.replace('\n', '<br>')

    def title(self, text, level=2):
        st.markdown(f"{'#' * level} {text}")
        self.html += f"<h{level}>{text}</h{level}>"

    def custom_html(self, html_str, show_in_ui=True):
        if show_in_ui:
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

    def warning(self, text):
        st.warning(text)
        self.html += f"<div class='warning-box'>{self._fmt(text)}</div>"

    def latex(self, eq):
        st.latex(eq)
        self.html += f"<div class='eq'>$$ {eq} $$</div>"
        
    def table(self, dataframe):
        st.table(dataframe)
        self.html += dataframe.to_html(index=False, justify='center', escape=False)

    def df(self, dataframe):
        st.dataframe(dataframe, use_container_width=True)
        self.html += dataframe.to_html(index=False, justify='center', escape=False)

    def get_html(self):
        return self.html + "</body></html>"

# =====================================================================
# 2. SPM 도표 시각화 함수 추가
# =====================================================================
@st.cache_data
def load_spm_data():
    """SPM 쇄파고(외부 파일 자동 탐색) 및 쇄파수심 차트 데이터 로더"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. '7-3'이 포함된 CSV 또는 엑셀 파일을 모두 찾습니다.
    target_file = None
    try:
        for f in os.listdir(current_dir):
            if "7-3" in f and (f.lower().endswith(".csv") or f.lower().endswith(".xlsx")):
                target_file = f
                break
    except Exception:
        pass

    df_7_3 = None
    
    if target_file:
        file_path = os.path.join(current_dir, target_file)
        try:
            # 엑셀 파일(.xlsx)인 경우
            if target_file.lower().endswith(".xlsx"):
                df = pd.read_excel(file_path, skiprows=2)
            # CSV 파일(.csv)인 경우
            else:
                encodings = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
                for enc in encodings:
                    try:
                        df = pd.read_csv(file_path, skiprows=2, encoding=enc)
                        break
                    except:
                        continue
            
            # 데이터 프레임 구성
            df_7_3 = pd.DataFrame()
            df_7_3["Ho'/gT2"] = df.iloc[:, 0].astype(float)
            df_7_3["m_0.02"] = df.iloc[:, 1].astype(float)
            df_7_3["m_0.033"] = df.iloc[:, 2].astype(float)
            df_7_3["m_0.05"] = df.iloc[:, 3].astype(float)
            df_7_3["m_0.1"] = df.iloc[:, 4].astype(float)
            df_7_3 = df_7_3.dropna(subset=["Ho'/gT2"])
            
            st.success(f"✅ 외부 데이터를 완벽하게 불러왔습니다! (인식된 파일: {target_file})")
            
        except Exception as e:
            st.error(f"⚠️ 엑셀/CSV 파일을 읽는 중 문제가 발생했습니다.\n(엑셀 파일인 경우 터미널에서 'pip install openpyxl' 설치가 필요할 수 있습니다.)")

    # 2. 파일을 못 찾았거나 읽기 실패한 경우, 당초 코드처럼 '내장 데이터'로 무조건 정상 실행
    if df_7_3 is None:
        st.warning("⚠️ 첨부 데이터를 찾지 못해, 당초 코드에 있던 원본(내장) 데이터로 그래프를 그립니다.")
        backup_csv_7_3 = """Ho'/gT2,m_0.02,m_0.033,m_0.05,m_0.1
0.00024,2.21557,2.42684,2.58118,2.70658
0.00028,2.17599,2.38274,2.53267,2.65567
0.00032,2.14499,2.34570,2.49205,2.61446
0.00036,2.11644,2.31079,2.45362,2.57477
0.00040,2.09046,2.27982,2.41940,2.53990
0.00060,1.86839,2.02400,2.13929,2.27196
0.00100,1.61443,1.74785,1.84181,1.96419
0.00200,1.33604,1.43558,1.53726,1.62019
0.00400,1.14181,1.22569,1.29364,1.36718
0.01000,0.96908,1.02685,1.05865,1.10950
0.02000,0.94761,0.95000,0.97933,1.00104"""
        df_7_3 = pd.read_csv(io.StringIO(backup_csv_7_3))

    # 3. SPM Fig 7-2 데이터 (기존 안정 내장본 유지)
    csv_7_2 = """Hb/gT2,alpha,m_0.2,m_0.1,m_0.07,m_0.05,m_0.03,m_0.02,m_0.01,m_0.0
0.0004,1.47308,0.67535,0.73493,0.81362,0.88961,0.99938,1.07146,1.16542,1.28473
0.0012,1.48458,0.69692,0.75962,0.83063,0.90862,1.01838,1.09466,1.17942,1.28473
0.0020,1.49451,0.71502,0.77911,0.84746,0.92499,1.03495,1.11101,1.19060,1.28473
0.0040,1.51790,0.75328,0.82488,0.88532,0.96410,1.07198,1.14300,1.20784,1.28473
0.0060,1.53702,0.79816,0.86762,0.94329,1.02127,1.11457,1.17491,1.22500,1.28473
0.0080,1.55356,0.86502,0.92827,1.00888,1.08526,1.16592,1.21200,1.25114,1.28473
0.0100,1.57375,0.93647,1.00333,1.08183,1.15458,1.22264,1.25313,1.27739,1.28627
0.0120,1.60055,1.01322,1.09081,1.16753,1.23072,1.28258,1.29988,1.30767,1.31415
0.0140,1.63972,1.10081,1.18826,1.26718,1.31878,1.34500,1.35000,1.35798,1.38392
0.0160,1.69466,1.21416,1.30400,1.38188,1.41691,1.41500,1.42000,1.42922,1.45118
0.0188,1.82000,1.45000,1.49863,1.57147,1.56000,1.55000,1.56000,1.59240,1.60000"""
    df_7_2 = pd.read_csv(io.StringIO(csv_7_2))
    
    return df_7_3, df_7_2

def get_plot_html(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f'<img src="data:image/png;base64,{img_b64}" style="max-width:100%; height:auto; border:1px solid #ccc; margin: 10px 0;">'

def plot_spm_charts(H0_prime, T, m, Hb, X_h0, Hb_ratio, X_hb, alpha_val, beta_val):
    import matplotlib.ticker as ticker 
    
    df_7_3, df_7_2 = load_spm_data()
    
    # ==========================================
    # 1) Fig 7-3 (쇄파고) 
    # ==========================================
    fig_7_3, ax1 = plt.subplots(figsize=(10, 7))
    slopes_7_3 = [0.02, 0.033, 0.05, 0.1]
    for i, s in enumerate(slopes_7_3):
        ax1.plot(df_7_3.iloc[:, 0], df_7_3.iloc[:, i+1], label=f'm={s}', alpha=0.8, linewidth=1.5)
    
    # m이 0.02 미만일 경우 0.02 곡선(파란선) 적용
    plot_m_7_3 = m if m >= 0.02 else 0.02
    
    # 독취점 (파란선 곡선과 정확히 만나는 지점에 마킹)
    ax1.vlines(x=X_h0, ymin=0.5, ymax=Hb_ratio, color='r', linestyle='--', alpha=0.8)
    ax1.hlines(y=Hb_ratio, xmin=0.0001, xmax=X_h0, color='r', linestyle='--', alpha=0.8)
    ax1.plot(X_h0, Hb_ratio, 'r*', markersize=14, label=f'독취값(m={plot_m_7_3} 곡선 적용): {Hb_ratio:.3f}')
    
    # X축 로그 스케일 설정
    ax1.set_xscale('log')
    ax1.set_xlim(0.0002, 0.03)
    
    # 로그 스케일의 10등분 보조 눈금선 복구
    ax1.xaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=np.arange(2, 10)))
    ax1.xaxis.set_minor_formatter(ticker.NullFormatter())
    
    # 지정해주신 주 눈금선 표시
    custom_xticks = [0.0002, 0.0004, 0.0006, 0.001, 0.002, 0.004, 0.006, 0.01, 0.02, 0.03]
    ax1.set_xticks(custom_xticks)
    ax1.set_xticklabels([f"{x:g}" for x in custom_xticks])
    
    # Y축 선형 스케일
    ax1.set_ylim(0.5, 3.0)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(0.05))
    
    ax1.set_xlabel(r"$H_0' / gT^2$", fontsize=12)
    ax1.set_ylabel(r"$H_b / H_0'$", fontsize=12)
    ax1.set_title("SPM Fig 7-3: Breaking Wave Height", pad=15, fontsize=14)
    
    ax1.grid(True, which="major", ls="-", color='black', alpha=0.4)
    ax1.grid(True, which="minor", ls=":", color='gray', alpha=0.5)
    ax1.legend(fontsize=10)
    
    html_7_3 = get_plot_html(fig_7_3)
    
    # ==========================================
    # 2) Fig 7-2 (쇄파수심)
    # ==========================================
    fig_7_2, ax2 = plt.subplots(figsize=(10, 7))
    
    # α 곡선
    ax2.plot(df_7_2['Hb/gT2'], df_7_2['alpha'], 'b-', linewidth=2.5, label='α 선')
    
    # β 해저경사 곡선들
    colors = {0.01: 'black', 0.02: 'purple', 0.03: 'brown', 0.05: 'red', 0.07: 'orange', 0.1: 'green', 0.2: 'cyan'}
    slopes_7_2 = [0.2, 0.1, 0.07, 0.05, 0.03, 0.02, 0.01]
    for s in slopes_7_2:
        ax2.plot(df_7_2['Hb/gT2'], df_7_2[f'm_{s}'], label=f'm={s}', color=colors.get(s, 'gray'), linewidth=1.5)
    
    # 지시선 화살표
    ax2.annotate('α 선', xy=(0.012, np.interp(0.012, df_7_2['Hb/gT2'], df_7_2['alpha'])), 
                 xytext=(0.009, 1.65),
                 arrowprops=dict(facecolor='blue', arrowstyle='->', lw=1.5), fontsize=13, fontweight='bold', color='blue')
                 
    ax2.annotate('β 선', xy=(0.012, np.interp(0.012, df_7_2['Hb/gT2'], df_7_2['m_0.01'])), 
                 xytext=(0.014, 1.10),
                 arrowprops=dict(facecolor='red', arrowstyle='->', lw=1.5), fontsize=13, fontweight='bold', color='red')

    # 독취점
    ax2.vlines(x=X_hb, ymin=0, ymax=alpha_val, color='blue', linestyle='--', alpha=0.8)
    ax2.hlines(y=alpha_val, xmin=0, xmax=X_hb, color='blue', linestyle='--', alpha=0.8)
    ax2.plot(X_hb, alpha_val, 'bo', markersize=8, label=f'α 독취값: {alpha_val:.3f}')
    
    ax2.vlines(x=X_hb, ymin=0, ymax=beta_val, color='red', linestyle='--', alpha=0.8)
    ax2.hlines(y=beta_val, xmin=0, xmax=X_hb, color='red', linestyle='--', alpha=0.8)
    ax2.plot(X_hb, beta_val, 'ro', markersize=8, label=f'β 독취값(m={m}): {beta_val:.3f}')
    
    ax2.set_xscale('linear')
    ax2.set_xlim(0, 0.020)
    ax2.xaxis.set_major_locator(ticker.MultipleLocator(0.002))
    ax2.xaxis.set_minor_locator(ticker.MultipleLocator(0.0002)) 
    
    ax2.set_ylim(0, 1.75)
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(0.25))
    ax2.yaxis.set_minor_locator(ticker.MultipleLocator(0.025)) 
    
    ax2_top = ax2.twiny()
    ax2_top.set_xlim(0, 0.65)
    ax2_top.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.65])
    ax2_top.set_xlabel(r"$H_b / T^2$", fontsize=12)
    
    ax2.set_xlabel(r"$H_b / gT^2$", fontsize=12)
    ax2.set_ylabel(r"$d_b / H_b$", fontsize=12)
    ax2.set_title("SPM Fig 7-2: Breaker Depth", pad=20, fontsize=14)
    
    ax2.grid(True, which="major", ls="-", color='black', alpha=0.3)
    ax2.grid(True, which="minor", ls=":", color='gray', alpha=0.5)
    ax2.legend(ncol=2, fontsize=10, loc='lower right')
    
    html_7_2 = get_plot_html(fig_7_2)
    return html_7_3, html_7_2

# =====================================================================
# 3. KDS 도참 4-20b 시각화 함수 추가
# =====================================================================
@st.cache_data
def load_kds_data():
    """KDS 도참 4-20b 차트 데이터 로더 (외부 CSV/Excel 자동 탐색)"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_file = None
    try:
        for f in os.listdir(current_dir):
            if "4-20b" in f and (f.lower().endswith(".csv") or f.lower().endswith(".xlsx")):
                target_file = f
                break
    except Exception:
        pass

    df_kds = None
    if target_file:
        file_path = os.path.join(current_dir, target_file)
        try:
            if target_file.lower().endswith(".xlsx"):
                df = pd.read_excel(file_path, skiprows=2)
            else:
                encodings = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
                for enc in encodings:
                    try:
                        df = pd.read_csv(file_path, skiprows=2, encoding=enc)
                        break
                    except:
                        continue
            
            df_kds = pd.DataFrame()
            df_kds["Ho'/Lo"] = df.iloc[:, 0].astype(float)
            df_kds["m_1/10"] = df.iloc[:, 1].astype(float)
            df_kds["m_1/20"] = df.iloc[:, 2].astype(float)
            df_kds["m_1/30"] = df.iloc[:, 3].astype(float)
            df_kds["m_1/100"] = df.iloc[:, 4].astype(float)
            df_kds = df_kds.dropna(subset=["Ho'/Lo"])
        except Exception:
            pass
            
    # 파일을 찾지 못했거나 에러가 난 경우 예비 데이터 가동
    if df_kds is None:
        st.warning("⚠️ KDS 4-20b 첨부 데이터를 찾지 못해 내장 데이터로 그래프를 그립니다.")
        backup_kds = """Ho'/Lo,m_1/10,m_1/20,m_1/30,m_1/100
0.002,2.83941,3.29705,3.49683,3.7
0.004,2.33351,2.65152,2.81977,3.01804
0.006,2.07287,2.37803,2.53424,2.7303
0.008,1.93006,2.22458,2.37063,2.56117
0.010,1.81201,2.10277,2.25476,2.44596
0.020,1.52044,1.75841,1.89063,2.06733
0.030,1.38133,1.59762,1.71452,1.87978
0.040,1.29528,1.48866,1.59604,1.74542
0.050,1.23358,1.4057,1.50348,1.64332"""
        df_kds = pd.read_csv(io.StringIO(backup_kds))
        
    return df_kds

def plot_kds_chart(H0_prime, L0, m, S0, peak_ratio):
    import matplotlib.ticker as ticker
    df_kds = load_kds_data()
    
    # 세로 비율을 조금 줄여 안정적인 크기로 설정 (가로 8, 세로 9)
    fig_kds, ax = plt.subplots(figsize=(8, 9))
    
    # 해저경사 곡선 매핑
    labels = ['m=1/10', 'm=1/20', 'm=1/30', 'm=1/100']
    cols = ['m_1/10', 'm_1/20', 'm_1/30', 'm_1/100']
    
    for col, label in zip(cols, labels):
        ax.plot(df_kds.iloc[:, 0], df_kds[col], label=label, alpha=0.8, linewidth=1.5)
    
    # 독취점 표시 (시작점 ymin을 1.3으로 조정)
    ax.vlines(x=S0, ymin=1.3, ymax=peak_ratio, color='r', linestyle='--', alpha=0.8)
    ax.hlines(y=peak_ratio, xmin=0.002, xmax=S0, color='r', linestyle='--', alpha=0.8)
    ax.plot(S0, peak_ratio, 'r*', markersize=14, label=f'독취값(m={m}): {peak_ratio:.3f}')
    
    # ==========================================
    # X축 설정 (로그 스케일 및 지정 눈금)
    # ==========================================
    ax.set_xscale('log')
    ax.set_xlim(0.002, 0.1)
    
    # 주 눈금 지정
    custom_xticks = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
    ax.set_xticks(custom_xticks)
    ax.set_xticklabels([f"{x:g}" for x in custom_xticks])
    
    # 로그 스케일 보조 눈금선 세팅 (1~9 배수 모두 표시)
    ax.xaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=np.arange(2, 10)))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    
    # ==========================================
    # Y축 설정 (1.3 ~ 3.7 범위 및 지정 눈금)
    # ==========================================
    ax.set_ylim(1.3, 3.7)
    
    # 주 눈금 지정
    ax.set_yticks([1.5, 2.0, 2.5, 3.0, 3.5])
    
    # 보조 눈금 간격 0.1 지정
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
    
    # ==========================================
    # 라벨 및 격자선 설정
    # ==========================================
    ax.set_xlabel(r"$H_0' / L_0$", fontsize=12)
    ax.set_ylabel(r"$h_{1/3, peak} / H_0'$", fontsize=12)
    ax.set_title("항만 및 어항 설계기준 도참 4-20(b)", pad=15, fontsize=14)
    
    # 주 격자는 실선, 보조 격자는 점선
    ax.grid(True, which="major", ls="-", color='black', alpha=0.4)
    ax.grid(True, which="minor", ls=":", color='gray', alpha=0.5)
    ax.legend(fontsize=10)
    
    return get_plot_html(fig_kds)
  
class ArmorCalculator:
    def __init__(self):
        # 해수 단위중량 (kN/m³) - 10.1 적용
        self.gamma_w = 10.1  
        self.g = 9.81        

    def calc_L(self, T, d):
        """파장(L)을 반복법으로 산출"""
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

    def calc_Ks(self, T, d):
        """SPM Table과 동일한 선형 천수계수(Ks) 역산 산출"""
        L0 = (self.g * T**2) / (2 * math.pi)
        L = self.calc_L(T, d)
        kd = 2 * math.pi * d / L
        
        if 2 * kd > 50:
            n = 0.5
        else:
            n = 0.5 * (1 + (2 * kd) / math.sinh(2 * kd))
            
        Ks = math.sqrt(L0 / (2 * n * L))
        return Ks, L0, L

    def check_surf_zone_spm(self, H0_prime, T, m, depth):
        """1. SPM 방식 쇄파대 검토 (도표 독취 데이터 기반 정밀 보간법 적용)"""
        L0 = (self.g * T**2) / (2 * math.pi)
        X_h0 = H0_prime / (self.g * T**2)
        
        spm_m_keys = [0.005, 0.010, 0.020, 0.033, 0.050, 0.100]
        spm_X = [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.00346, 0.005, 0.01, 0.02, 0.05, 0.1]
        
        spm_Y = {
            0.005: [1.38, 1.30, 1.22, 1.15, 1.05, 0.99,  0.95, 0.90, 0.85, 0.80, 0.78],
            0.010: [1.70, 1.55, 1.40, 1.25, 1.15, 1.08,  1.02, 0.95, 0.90, 0.83, 0.79],
            0.020: [2.10, 1.88, 1.60, 1.40, 1.28, 1.17,  1.10, 1.00, 0.92, 0.84, 0.81],
            0.033: [2.35, 2.10, 1.78, 1.55, 1.37, 1.24,  1.17, 1.05, 0.96, 0.87, 0.82],
            0.050: [2.55, 2.30, 1.95, 1.70, 1.48, 1.34,  1.25, 1.12, 1.02, 0.90, 0.83],
            0.100: [2.73, 2.48, 2.15, 1.95, 1.65, 1.48,  1.35, 1.20, 1.08, 0.93, 0.85]
        }
        
        log_X = math.log10(X_h0) if X_h0 > 0 else -4
        log_spm_X = [math.log10(x) for x in spm_X]
        
        y_vals_for_m = []
        for m_key in spm_m_keys:
            log_Y = np.interp(log_X, log_spm_X, [math.log10(y) for y in spm_Y[m_key]])
            y_vals_for_m.append(10**log_Y)
            
        Hb_ratio = np.interp(m, spm_m_keys, y_vals_for_m)
        Hb = Hb_ratio * H0_prime
        
        X_hb = Hb / (self.g * T**2)
        alpha = 1.49 + 2.5 * X_hb
        beta = 1.19 + 2.5 * X_hb
        
        db_max = alpha * Hb
        db_min = beta * Hb
        
        if depth > db_max:
            status = "비쇄파"
            is_breaking = False
        elif depth < db_min:
            status = "쇄파"
            is_breaking = True
        else:
            status = "쇄파대"
            is_breaking = True
            
        return L0, X_h0, Hb_ratio, Hb, X_hb, alpha, beta, db_max, db_min, is_breaking, status

    def check_surf_zone_harbor(self, H0_prime, L0, m, depth):
        """2. 항만 및 어항 설계기준 방식 검토"""
        S0 = H0_prime / L0
        
        x_vals = [0.0100, 0.0150, 0.0189, 0.0217, 0.0242, 0.0245, 0.0300, 0.0400, 0.0500]
        y_vals = [2.40,   2.30,   2.22,   2.20,   2.19,   2.18,   2.15,   2.05,   1.95]
        
        peak_ratio = np.interp(S0, x_vals, y_vals)
        h_peak = peak_ratio * H0_prime
        
        if depth > h_peak:
            status = "비쇄파"
            is_breaking = False
        else:
            status = "쇄파(대)"
            is_breaking = True
            
        return S0, peak_ratio, h_peak, is_breaking, status

    def calc_hudson(self, gamma_r, H, Kd, cot_alpha):
        Sr = gamma_r / self.gamma_w
        weight = (gamma_r * (H ** 3)) / (Kd * cot_alpha * ((Sr - 1) ** 3))
        return weight, Sr

    def calc_vandermeer_rock(self, gamma_r, Hs, Tz, cot_alpha, P, S, N):
        Sr = gamma_r / self.gamma_w
        Delta = Sr - 1
        L_om = (self.g * Tz**2) / (2 * math.pi)
        s_m = Hs / L_om
        tan_alpha = 1.0 / cot_alpha
        xi_m = tan_alpha / math.sqrt(s_m) 
        
        xi_mc = (6.2 * (P**0.31) * math.sqrt(tan_alpha)) ** (1 / (P + 0.5))
        
        if xi_m < xi_mc:
            wave_type = "Plunging (붕괴파)"
            Ns = 6.2 * (P**0.18) * ((S / math.sqrt(N))**0.2) * (xi_m**(-0.5))
        else:
            wave_type = "Surging (단파)"
            Ns = 1.0 * (P**-0.13) * ((S / math.sqrt(N))**0.2) * math.sqrt(cot_alpha) * (xi_m**P)
            
        Dn50 = Hs / (Delta * Ns)
        weight = gamma_r * (Dn50 ** 3)
        return weight, wave_type, Sr, L_om, s_m, xi_m, xi_mc, Ns, Dn50

    def calc_vandermeer_ttp(self, gamma_r, Hs, Tz, Nod, N):
        Sr = gamma_r / self.gamma_w
        Delta = Sr - 1
        
        Tm = Tz / 1.2
        L_om = (self.g * Tm**2) / (2 * math.pi)
        s_m = Hs / L_om
        
        Ns = (3.75 * (Nod**0.5) / (N**0.25) + 0.85) * (s_m**-0.2)
        Dn = Hs / (Delta * Ns)
        weight = gamma_r * (Dn ** 3)
        return weight, Sr, Tm, L_om, s_m, Ns, Dn

    def calc_hudson_rel(self, gamma_r, H, Kd, cot_alpha, gR, gS, gm):
        Sr = gamma_r / self.gamma_w; Delta = Sr - 1
        Rk_req = (gm * gS * H) / gR
        Dn = Rk_req / (Delta * (Kd * cot_alpha)**(1/3))
        weight = gamma_r * (Dn ** 3)
        return weight, Sr, Rk_req, Dn
   
    def calc_vandermeer_rock_rel(self, gamma_r, Hs, Tz, cot_alpha, P, S, N, gR_p, gS_p, gm_p, gR_s, gS_s, gm_s):
        Sr = gamma_r / self.gamma_w; Delta = Sr - 1
        L_om = (self.g * Tz**2) / (2 * math.pi)
        s_om = Hs / L_om; tan_alpha = 1.0 / cot_alpha
        xi_m = tan_alpha / math.sqrt(s_om)
        xi_mc = (6.2 * (P**0.31) * math.sqrt(tan_alpha)) ** (1 / (P + 0.5))

        if xi_m <= xi_mc:
            wave_type = "Plunging (권파)"
            gR, gS, gm = gR_p, gS_p, gm_p
            Rk_req = (gm * gS * Hs) / gR
            coef = 6.2 * (S**0.2) * Delta * (cot_alpha**0.5) * (P**0.18) * (s_om**-0.25) * (N**-0.1)
        else:
            wave_type = "Surging (쐐기파)"
            gR, gS, gm = gR_s, gS_s, gm_s
            Rk_req = (gm * gS * Hs) / gR
            coef = (S**0.2) * Delta * (cot_alpha**(0.5 - P)) * (P**-0.13) * (s_om**(-0.5 * P)) * (N**-0.1)
            
        Dn = Rk_req / coef
        weight = gamma_r * (Dn ** 3)
        return weight, wave_type, Sr, L_om, s_om, xi_m, xi_mc, None, Dn, Rk_req, gR, gS, gm

    def calc_vandermeer_ttp_rel(self, gamma_r, Hs, Tz, Nod, N, gR, gS, gm):
        Sr = gamma_r / self.gamma_w; Delta = Sr - 1
        Tm = Tz / 1.2
        L_om = (self.g * Tm**2) / (2 * math.pi); s_om = Hs / L_om
        Rk_req = (gm * gS * Hs) / gR
        coef = (3.75 * (Nod**0.5) / (N**0.25) + 0.85) * Delta * (s_om**-0.2)
        Dn = Rk_req / coef
        weight = gamma_r * (Dn ** 3)
        return weight, Sr, Tm, L_om, s_om, None, Dn, Rk_req


# --- 번역 오작동 방지용 HTML 텍스트 ---
html_cot = "<span class='notranslate' translate='no'>Cot</span>"
html_tan = "<span class='notranslate' translate='no'>tan</span>"

# --- UI 레이아웃 구성 ---
st.set_page_config(page_title="피복재 통합 검토", page_icon="🌊", layout="wide")

st.title("피복재 및 소파블록 통합 검토 (SPM & 설계기준)")
st.markdown("SPM 방식과 항만 및 어항 설계기준 방식을 교차 적용한 쇄파대 판정 및 피복재 중량 자동 산출 프로그램입니다.")
st.markdown("---")

with st.sidebar:
    design_method = st.radio("✅ **설계법 선택**", ["결정론적 설계법", "신뢰성 설계법"])
    
    if design_method == "신뢰성 설계법":
        st.markdown("---")
        st.header("🔐 신뢰성 설계법 부분안전계수 (자동적용)")
        st.caption("KDS 64 10 07 해설 표 4.2-20 ~ 23 참조")
        
        with st.expander("1. 허드슨(Hudson)식 계수", expanded=False):
            st.markdown("**피복석 (목표파괴확률 28%)**")
            gR_hud_rock = st.number_input("저항계수 γR (Hudson 피복석)", value=0.91, step=0.01)
            gS_hud_rock = st.number_input("하중계수 γS (Hudson 피복석)", value=1.06, step=0.01)
            gm_hud_rock = st.number_input("조정계수 γm (Hudson 피복석)", value=1.00, step=0.01)
            st.markdown("**테트라포드 등 (목표파괴확률 41%)**")
            gR_hud_ttp = st.number_input("저항계수 γR (Hudson TTP)", value=0.96, step=0.01)
            gS_hud_ttp = st.number_input("하중계수 γS (Hudson TTP)", value=1.02, step=0.01)
            gm_hud_ttp = st.number_input("조정계수 γm (Hudson TTP)", value=1.00, step=0.01)
            
        with st.expander("2. 반데미어(VdM) 피복석 계수", expanded=False):
            st.markdown("**권파 (Plunging, 목표파괴확률 50%)**")
            gR_vdm_rock_p = st.number_input("저항계수 γR (VdM 권파)", value=1.00, step=0.01)
            gS_vdm_rock_p = st.number_input("하중계수 γS (VdM 권파)", value=1.00, step=0.01)
            gm_vdm_rock_p = st.number_input("조정계수 γm (VdM 권파)", value=1.00, step=0.01)
            st.markdown("**쐐기파 (Surging, 목표파괴확률 34%)**")
            gR_vdm_rock_s = st.number_input("저항계수 γR (VdM 쐐기파)", value=0.98, step=0.01)
            gS_vdm_rock_s = st.number_input("하중계수 γS (VdM 쐐기파)", value=1.05, step=0.01)
            gm_vdm_rock_s = st.number_input("조정계수 γm (VdM 쐐기파)", value=1.00, step=0.01)
            
        with st.expander("3. 반데미어(VdM) TTP 계수", expanded=False):
            st.markdown("**테트라포드 (목표파괴확률 37%)**")
            gR_vdm_ttp = st.number_input("저항계수 γR (VdM TTP)", value=0.97, step=0.01)
            gS_vdm_ttp = st.number_input("하중계수 γS (VdM TTP)", value=1.04, step=0.01)
            gm_vdm_ttp = st.number_input("조정계수 γm (VdM TTP)", value=1.00, step=0.01)
    st.markdown("---")
    st.header("1. 설계 파랑 및 구조 제원")
    Hs = st.number_input("유의파고 Hs (m)", value=4.6, step=0.1)
    Tz = st.number_input("유의주기 Tz (s)", value=11.77, step=0.1)
    depth = st.number_input("구조물 전면수심 h (m)", value=14.41, step=0.1)
    cot_alpha = st.number_input("사면경사 (Cot α)", value=1.5, step=0.1)
    N_waves = st.number_input("내습 파랑수 N", value=1000, step=100)
    st.markdown("---")

    st.header("2. 쇄파대 검토 제원")
    st.info("💡 **환산심해파고($H_0'$)**는 입력된 파고($H_s$), 주기($T_z$), 수심($h$)을 바탕으로 SPM Table을 통해 자동 산출됩니다.")
    m_slope = st.number_input("해저면 경사 m (예: 1/100 = 0.01)", value=0.01, step=0.01)
    st.markdown("---")

    st.header("3. 피복석 파라미터")
    gamma_rock = st.number_input("단위중량 γ (kN/m³) [피복석]", value=26.0, step=0.1)
    st.info("💡 피복석의 안정계수(KD)는 쇄파대 판정 결과에 따라 **자동 산정**됩니다. (비쇄파: 4.0, 쇄파: 2.0)")
    P_rock = st.number_input("VdM 투과계수 P (0.1~0.6)", value=0.50, step=0.01)
    S_rock = st.number_input("VdM 허용손상도 S (2~8)", value=2.0, step=0.1)
    st.markdown("---")

    st.header("4. 소파블록(TTP) 파라미터")
    gamma_ttp = st.number_input("단위중량 γ (kN/m³) [TTP]", value=22.6, step=0.1)
    st.info("💡 TTP의 안정계수(KD)는 쇄파대 판정 결과에 따라 **자동 산정**됩니다. (비쇄파: 8.0, 쇄파: 7.0)")
    Nod_ttp = st.number_input("VdM 상대피해율 Nod (0~0.5)", value=0.20, step=0.01)
    st.markdown("---")

    st.header("5. TTP 외 소파블록(기타 블록) 파라미터")
    gamma_other = st.number_input("단위중량 γ (kN/m³) [기타 블록]", value=22.6, step=0.1)
    Kd_other = st.number_input("안정계수 KD [기타 블록]", value=10.0, step=0.1)

    st.info("💡 기타 소파블록은 입력하신 KD 값을 바탕으로 **Hudson 공식**으로만 중량을 산출합니다.")
    st.markdown("---")
    
    # 1. 계산 완료 상태를 기억할 세션 변수 초기화
    if 'armor_calculated' not in st.session_state:
        st.session_state['armor_calculated'] = False
        
    run_button = st.button("🚀 검토 실행 (Calculate)", type="primary", use_container_width=True)
    
    # 2. 버튼이 눌리면 계산 완료 상태로 기록
    if run_button:
        st.session_state['armor_calculated'] = True

# 3. 버튼 클릭 여부가 아닌 계산 완료 상태를 기준으로 화면 유지
if st.session_state['armor_calculated']:
    calc = ArmorCalculator()
    rep = ReportBuilder(title_text=f"피복재 및 소파블록 통합 검토 ({design_method})")
    
    # 0. 환산심해파고(H0') 자동 산출
    Ks, L0_val, L_val = calc.calc_Ks(Tz, depth)
    H0_prime = Hs / Ks
    
    # 1. 쇄파대 검토 실행
    L0, X_h0, Hb_ratio, Hb, X_hb, alpha, beta, db_max, db_min, is_brk_spm, status_spm = calc.check_surf_zone_spm(H0_prime, Tz, m_slope, depth)
    S0, peak_ratio, h_peak, is_brk_harbor, status_harbor = calc.check_surf_zone_harbor(H0_prime, L0, m_slope, depth)
    
    # 종합 쇄파대 판정 (보수적 적용)
    final_is_breaking = (status_spm != "비쇄파" or status_harbor != "비쇄파")
    
    # 2. KD 값 산정 (피복석, TTP는 자동 / 기타블록은 사용자 입력값 사용)
    Kd_rock = 2.0 if final_is_breaking else 4.0
    Kd_ttp = 7.0 if final_is_breaking else 8.0
    
    # 3. 피복재 중량 계산
    H_design = Hs  
    
    if design_method == "결정론적 설계법":
        # 오리지널 방식 호출
        rock_h_weight, r_Sr = calc.calc_hudson(gamma_rock, H_design, Kd_rock, cot_alpha)
        rock_v_weight, r_type, _, r_Lom, r_sm, r_xim, r_ximc, r_Ns, r_Dn50 = calc.calc_vandermeer_rock(gamma_rock, Hs, Tz, cot_alpha, P_rock, S_rock, N_waves)
        
        ttp_h_weight, t_Sr = calc.calc_hudson(gamma_ttp, H_design, Kd_ttp, cot_alpha)
        ttp_v_weight, _, t_Tm, t_Lom, t_sm, t_Ns, t_Dn = calc.calc_vandermeer_ttp(gamma_ttp, Hs, Tz, Nod_ttp, N_waves)
        
        other_h_weight, o_Sr = calc.calc_hudson(gamma_other, H_design, Kd_other, cot_alpha)
    else:
        # 신뢰성 방식 호출 (피복석/TTP 분리된 계수 전달)
        rock_h_weight, r_Sr, r_Rk_req, r_h_Dn = calc.calc_hudson_rel(gamma_rock, H_design, Kd_rock, cot_alpha, gR_hud_rock, gS_hud_rock, gm_hud_rock)
        
        # 반데미어 피복석 (권파/쐐기파 계수 동시 전달 -> 내부에서 판정 후 적용)
        rock_v_weight, r_type, _, r_Lom, r_sm, r_xim, r_ximc, _, r_Dn50, r_v_Rk_req, used_gR, used_gS, used_gm = calc.calc_vandermeer_rock_rel(
            gamma_rock, Hs, Tz, cot_alpha, P_rock, S_rock, N_waves, 
            gR_vdm_rock_p, gS_vdm_rock_p, gm_vdm_rock_p, 
            gR_vdm_rock_s, gS_vdm_rock_s, gm_vdm_rock_s
        )
        
        ttp_h_weight, t_Sr, t_Rk_req, t_h_Dn = calc.calc_hudson_rel(gamma_ttp, H_design, Kd_ttp, cot_alpha, gR_hud_ttp, gS_hud_ttp, gm_hud_ttp)
        ttp_v_weight, _, t_Tm, t_Lom, t_sm, _, t_Dn, t_v_Rk_req = calc.calc_vandermeer_ttp_rel(gamma_ttp, Hs, Tz, Nod_ttp, N_waves, gR_vdm_ttp, gS_vdm_ttp, gm_vdm_ttp)
        
        other_h_weight, o_Sr, o_Rk_req, o_h_Dn = calc.calc_hudson_rel(gamma_other, H_design, Kd_other, cot_alpha, gR_hud_ttp, gS_hud_ttp, gm_hud_ttp)
        
    rock_final_kN = max(rock_h_weight, rock_v_weight)
    ttp_final_kN = max(ttp_h_weight, ttp_v_weight)
    other_final_kN = other_h_weight  # 단일 공식 적용이므로 그대로 결정중량

    # ====================================================
    # UI 출력 - 요약 (비교표 추가)
    # ====================================================
    rep.title("📊 검토 결과 요약", level=2)
    res_col1, res_col2 = st.columns([1, 1.2]) 
    
    with res_col1:
        rep.info(f"**🌊 쇄파대 판정 (수심 h = {depth:.2f} m)**\n\n"
                f"- **SPM 기준:** {status_spm} (영역: {db_min:.2f} ~ {db_max:.2f} m)\n"
                f"- **설계기준:** {status_harbor} ($h_{{1/3, peak}}$ = {h_peak:.2f} m)")
                
    with res_col2:
        rep.success(f"**🪨 피복재 소요중량 산정 결과 (비교표 - {design_method})**")
        
        # HTML 렌더링에 최적화된 결과 테이블 적용
        tbl_html = f"""
        <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 1.05em;" border="1">
            <tr style="background-color: #f1f8ff; color: #1e3a8a;">
                <th style="padding: 10px;">구분</th>
                <th style="padding: 10px;">Hudson 공식</th>
                <th style="padding: 10px;">Van der Meer 공식</th>
                <th style="padding: 10px;">결정중량(MAX)</th>
            </tr>
            <tr><td style="padding: 8px;"><b>피복석</b></td><td style="padding: 8px;">{rock_h_weight:,.1f} kN</td><td style="padding: 8px;">{rock_v_weight:,.1f} kN</td><td style="padding: 8px; color: #d9480f;"><b>{rock_final_kN:,.1f} kN</b></td></tr>
            <tr><td style="padding: 8px;"><b>소파블록(TTP)</b></td><td style="padding: 8px;">{ttp_h_weight:,.1f} kN</td><td style="padding: 8px;">{ttp_v_weight:,.1f} kN</td><td style="padding: 8px; color: #d9480f;"><b>{ttp_final_kN:,.1f} kN</b></td></tr>
            <tr><td style="padding: 8px;"><b>기타 블록</b></td><td style="padding: 8px;">{other_h_weight:,.1f} kN</td><td style="padding: 8px;">-</td><td style="padding: 8px; color: #d9480f;"><b>{other_final_kN:,.1f} kN</b></td></tr>
        </table>
        """
        rep.custom_html(tbl_html)
        rep.md(f"*(적용 $K_D$: 피복석 **{Kd_rock:.1f}**, TTP **{Kd_ttp:.1f}**, 기타블록 **{Kd_other:.1f}**)*")

    rep.custom_html("<hr>")

    # ====================================================
    # UI 출력 - 상세 풀이과정
    # ====================================================
    rep.title(f"📝 상세 검토 풀이과정 ({design_method})", level=2)
    
    # ★ 목차 순서(가, 나, 다...) 동적 할당을 위한 변수 세팅
    lbls = ["가", "나", "다", "라", "마", "바", "사", "아", "자"]
    lbl_idx = 0

    # ----------------------------------------------------
    # [추가] 신뢰성 설계법 선택 시 공식 및 기호/계수 설명 선행 출력
    # ----------------------------------------------------
    if design_method == "신뢰성 설계법":
        rep.title(f"{lbls[lbl_idx]}. 신뢰성 설계법 공식 및 적용 계수 (KDS 64 10 07)", level=3)
        lbl_idx += 1  # 신뢰성 설계법일 경우 다음 목차 기호를 하나 미룸
        
        rep.info("항만 및 어항 설계기준에 따른 신뢰성 설계법 기본 방정식 및 입력된 하중저항계수입니다.")
        
        def get_img_html(file_name):
            if os.path.exists(file_name):
                with open(file_name, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode()
                return f'<img src="data:image/png;base64,{b64_string}" style="max-width:800px; height:auto; margin: 15px 0; border: 1px solid #ddd; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);">'
            return ""

        # 1) 허드슨
        rep.title("1) 허드슨(Hudson)식", level=4)
        rep.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k")
        rep.latex(r"R_k = \Delta D_n \cdot (K_D \cot\alpha)^{1/3}, \quad S_k = H_{1/3}")
        rep.md(f"- **적용 계수 (피복석)**: 저항계수 $\\gamma_R = {gR_hud_rock}$, 하중계수 $\\gamma_S = {gS_hud_rock}$, 조정계수 $\\gamma_m = {gm_hud_rock}$")
        rep.md(f"- **적용 계수 (TTP 등)**: 저항계수 $\\gamma_R = {gR_hud_ttp}$, 하중계수 $\\gamma_S = {gS_hud_ttp}$, 조정계수 $\\gamma_m = {gm_hud_ttp}$")
        rep.md(r"- **기호 설명**: $R_k$: 저항의 특성값, $S_k$: 하중의 특성값, $\Delta$: 이형도($S_r - 1$), $D_n$: 공칭직경, $K_D$: 안정계수, $\alpha$: 사면경사")
        if os.path.exists("허드슨 피복재 하중저항계수.png"):
            st.image("허드슨 피복재 하중저항계수.png", width=800) 
            rep.custom_html(get_img_html("허드슨 피복재 하중저항계수.png"), show_in_ui=False)

        # 2) 반데미어 피복석
        rep.title("2) 반데미어(Van der Meer)식 - 피복석", level=4)
        rep.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k \quad (S_k = H_{1/3})")
        rep.md(r"- **권파 (Plunging) 조건** ($\xi_m \le \xi_{mc}$)")
        rep.latex(r"R_k = 6.2 S^{0.2} \Delta D_n \cdot \cot\alpha^{0.5} \cdot P^{0.18} \cdot s_{om}^{-0.25} \cdot N^{-0.1}")
        rep.md(r"- **쇄기파 (Surging) 조건** ($\xi_m > \xi_{mc}$)")
        rep.latex(r"R_k = S^{0.2} \Delta D_n \cdot \cot\alpha^{(0.5-P)} \cdot P^{-0.13} \cdot s_{om}^{-0.5P} \cdot N^{-0.1}")
        rep.md(f"- **적용 계수 (권파)**: 저항계수 $\\gamma_R = {gR_vdm_rock_p}$, 하중계수 $\\gamma_S = {gS_vdm_rock_p}$, 조정계수 $\\gamma_m = {gm_vdm_rock_p}$")
        rep.md(f"- **적용 계수 (쐐기파)**: 저항계수 $\\gamma_R = {gR_vdm_rock_s}$, 하중계수 $\\gamma_S = {gS_vdm_rock_s}$, 조정계수 $\\gamma_m = {gm_vdm_rock_s}$")
        rep.md(r"- **기호 설명**: $S$: 허용손상도, $P$: 투과계수, $s_{om}$: 심해파형경사, $N$: 내습파랑수, $\xi_m$: 쇄파유사도")
        if os.path.exists("반데미어 피복석 하중저항계수(권파, 쐐기파).png"):
            st.image("반데미어 피복석 하중저항계수(권파, 쐐기파).png", width=800) 
            rep.custom_html(get_img_html("반데미어 피복석 하중저항계수(권파, 쐐기파).png"), show_in_ui=False)

        # 3) 반데미어 TTP
        rep.title("3) 반데미어(Van der Meer)식 - 테트라포드(TTP)", level=4)
        rep.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k \quad (S_k = H_{1/3})")
        rep.latex(r"R_k = \left( 3.75 \frac{N_o^{0.5}}{N^{0.25}} + 0.85 \right) \Delta D_n \cdot s_{om}^{-0.2}")
        rep.md(f"- **적용 계수**: 저항계수 $\\gamma_R = {gR_vdm_ttp}$, 하중계수 $\\gamma_S = {gS_vdm_ttp}$, 조정계수 $\\gamma_m = {gm_vdm_ttp}$")
        rep.md(r"- **기호 설명**: $N_o$: 상대피해율, $N$: 내습파랑수, $s_{om}$: 심해파형경사")
        if os.path.exists("반데미어 테트라포드 하중저항계수.png"):
            st.image("반데미어 테트라포드 하중저항계수.png", width=800) 
            rep.custom_html(get_img_html("반데미어 테트라포드 하중저항계수.png"), show_in_ui=False)
            
        rep.custom_html("<hr>")

    rep.title(f"{lbls[lbl_idx]}. 설계조건 및 환산심해파고 자동 산정", level=3)
    lbl_idx += 1
    rep.md(rf"- 유의파고 $H_{{1/3}} = {Hs} \text{{ m}}$, 유의주기 $T_{{1/3}} = {Tz} \text{{ s}}$, 수심 $h = {depth} \text{{ m}}$")
    rep.md(rf"- 심해파장 $L_0 = {L0_val:.2f} \text{{ m}}$, 상대수심 $d/L_0 = {(depth/L0_val):.5f}$")
    rep.md(rf"- 천수계수 산정 $K_s = {Ks:.4f}$ (SPM Table 선형파 이론 역산 적용)")
    rep.md(rf"- **환산심해파고 $H_0' = H_{{1/3}} / K_s = {Hs} / {Ks:.4f} = {H0_prime:.3f} \text{{ m}}$**")

    rep.custom_html("<hr>")
    
    rep.title(f"{lbls[lbl_idx]}. S.P.M 방법에 의한 쇄파대 검토", level=3)
    lbl_idx += 1
    
    # =========================================================================
    # ★ 보간값 정밀 재계산
    df_7_3, df_7_2 = load_spm_data()
    plot_m_7_3 = m_slope if m_slope >= 0.02 else 0.02
    
    Hb_ratio = float(np.interp(X_h0, df_7_3.iloc[:, 0], df_7_3[f'm_{plot_m_7_3}']))
    Hb = Hb_ratio * H0_prime
    X_hb = Hb / (9.81 * Tz**2)
    
    alpha = float(np.interp(X_hb, df_7_2['Hb/gT2'], df_7_2['alpha']))
    
    points, values = [], []
    slopes_7_2 = [0.2, 0.1, 0.07, 0.05, 0.03, 0.02, 0.01]
    for idx, row in df_7_2.iterrows():
        for s in slopes_7_2:
            points.append([row['Hb/gT2'], s])
            values.append(row[f'm_{s}'])
            
    try:
        beta = float(griddata(points, values, (X_hb, m_slope), method='linear'))
        if np.isnan(beta): beta = float(griddata(points, values, (X_hb, m_slope), method='nearest'))
    except:
        beta = float(griddata(points, values, (X_hb, m_slope), method='nearest'))
        
    db_max = alpha * Hb
    db_min = beta * Hb
    status_spm = "안정 (쇄파대 외측)" if depth > db_max else "불안정 (쇄파대 내측)"
    
    # KDS 도참 4-20b 보간값 정밀 재계산 추가
    df_kds = load_kds_data()
    kds_points, kds_values = [], []
    kds_slopes = [0.1, 0.05, 1/30, 0.01]  # 1/10, 1/20, 1/30, 1/100
    kds_cols = ['m_1/10', 'm_1/20', 'm_1/30', 'm_1/100']
    
    for idx, row in df_kds.iterrows():
        for s, col in zip(kds_slopes, kds_cols):
            if not pd.isna(row[col]):
                kds_points.append([row["Ho'/Lo"], s])
                kds_values.append(row[col])
    
    try:
        peak_ratio = float(griddata(kds_points, kds_values, (S0, m_slope), method='linear'))
        if np.isnan(peak_ratio): peak_ratio = float(griddata(kds_points, kds_values, (S0, m_slope), method='nearest'))
    except:
        peak_ratio = float(griddata(kds_points, kds_values, (S0, m_slope), method='nearest'))
        
    h_peak = peak_ratio * H0_prime
    status_harbor = "안정 (쇄파대 외측)" if depth > h_peak else "불안정 (쇄파대 내측)"
    final_is_breaking = (status_spm != "안정 (쇄파대 외측)" or status_harbor != "안정 (쇄파대 외측)")
    # =========================================================================

    html_img_7_3, html_img_7_2 = plot_spm_charts(H0_prime, Tz, m_slope, Hb, X_h0, Hb_ratio, X_hb, alpha, beta)
    
    rep.md("**1) 쇄파고($H_b$) 도표 보간 산정** *(Shore Protection Manual Vol. II, Fig. 7-3 기반)*")
    rep.md(rf"- 파형경사 파라미터 $H_0' / (g \cdot T^2) = {H0_prime:.3f} / (9.81 \times {Tz}^2) = {X_h0:.5f}$")
    
    if m_slope < 0.02:
        rep.md(rf"- **(해저경사 {m_slope}에 해당하는 곡선이 없기 때문에, 보수적으로 0.02 그래프 곡선을 참조하여 독취값을 약 {Hb_ratio:.3f}으로 적용하였음)**")
        
    rep.md(rf"- 도표 독취 역산 계수 $H_b / H_0' = {Hb_ratio:.3f}$")
    rep.md(rf"- 산출된 쇄파고 $H_b = {Hb_ratio:.3f} \times {H0_prime:.3f} = {Hb:.3f} \text{{ m}}$")
    rep.custom_html(html_img_7_3)
    
    rep.custom_html("<br>")
    
    rep.md("**2) 쇄파수심($d_b$) 영역 산정** *(Shore Protection Manual Vol. II, Fig. 7-2)*")
    rep.md(rf"- 쇄파고 파라미터 $H_b / (g \cdot T^2) = {Hb:.3f} / (9.81 \times {Tz}^2) = {X_hb:.5f}$")
    rep.md(rf"- 상한계수 $\alpha = {alpha:.3f}$, 하한계수 $\beta = {beta:.3f}$")
    rep.md(rf"- $d_{{b,max}} = \alpha \times H_b = {alpha:.3f} \times {Hb:.3f} = {db_max:.3f} \text{{ m}}$")
    rep.md(rf"- $d_{{b,min}} = \beta \times H_b = {beta:.3f} \times {Hb:.3f} = {db_min:.3f} \text{{ m}}$")
    rep.custom_html(html_img_7_2)
    rep.md(rf"👉 **판정:** 수심 $h ({depth} \text{{ m}}) > d_{{b,max}} ({db_max:.3f} \text{{ m}})$ 여부 비교결과 **{status_spm}** 임.")

    rep.custom_html("<hr>")

    # ====================================================
    # 항만 및 어항 설계기준 쇄파대 검토 
    # ====================================================
    rep.title(f"{lbls[lbl_idx]}. 항만 및 어항 설계기준을 이용한 쇄파대 검토", level=3)
    lbl_idx += 1
    html_img_kds = plot_kds_chart(H0_prime, L0, m_slope, S0, peak_ratio)
    
    rep.md("**쇄파한계수심($h_{1/3, peak}$) 영역 산정** *(항만 및 어항 설계기준 해설 도참 4-20(b) 기반)*")
    rep.md(rf"- 파형경사 파라미터 $H_0' / L_0 = {H0_prime:.3f} / {L0:.2f} = {S0:.5f}$")
    rep.md(rf"- 도표 독취 역산 계수 $h_{{1/3, peak}} / H_0' = {peak_ratio:.3f}$")
    rep.md(rf"- 산출된 쇄파한계수심 $h_{{1/3, peak}} = {peak_ratio:.3f} \times {H0_prime:.3f} = {h_peak:.3f} \text{{ m}}$")
    rep.custom_html(html_img_kds)
    rep.md(rf"👉 **판정:** 수심 $h ({depth} \text{{ m}}) > h_{{1/3, peak}} ({h_peak:.3f} \text{{ m}})$ 여부 비교결과 **{status_harbor}** 임.")

    rep.custom_html("<hr>")
    
    # ====================================================
    # 쇄파대 검토결과 요약
    # ====================================================
    rep.title(f"{lbls[lbl_idx]}. 쇄파대 검토결과 요약", level=3)
    lbl_idx += 1
    summary_data = {
        "구분": [f"수심 h(m)", "S.P.M에 의한 방법", "항만 및 어항 설계기준", "최종 판정"],
        "검토값": [f"{depth:.2f}", f"{db_min:.2f} ~ {db_max:.2f}", f"{h_peak:.2f}", f"{status_spm}"],
        "결과": ["-", f"{status_spm}", f"{status_harbor}", f"{'비쇄파' if not final_is_breaking else '쇄파(대)'}"]
    }
    rep.table(pd.DataFrame(summary_data))
    
    rep.custom_html("<hr>")
    
    # ----------------------------------------------------
    # 피복석 상세 계산
    # ----------------------------------------------------
    rep.title(f"{lbls[lbl_idx]}. 피복석 소요중량 산정", level=3)
    lbl_idx += 1
    
    rep.title("1) Hudson 공식에 의한 산정", level=4)
    rep.md(rf"- **설계파고($H_{{1/3}}$)**: $H_s = {H_design:.2f} \text{{ m}}$")
    rep.md(rf"- **피복석 비중($S_r$)**: $\gamma_r / \gamma_w = {gamma_rock:.2f} / 10.1 = {r_Sr:.3f}$")
    rep.md(f"- **안정계수($K_D$)**: {Kd_rock:.1f} (판정결과 자동적용), **사면경사({html_cot} $\\alpha$)**: {cot_alpha}", unsafe_allow_html=True)
    
    if design_method == "결정론적 설계법":
        rep.latex(r"W = \frac{\gamma_r H^3}{K_D \cdot \mathrm{C}\kern0.1ex\mathrm{o}\kern0.1ex\mathrm{t}\,\alpha \cdot (S_r - 1)^3}")
        rep.latex(rf"W = \frac{{{gamma_rock:.2f} \times {H_design:.2f}^3}}{{{Kd_rock:.1f} \times {cot_alpha} \times ({r_Sr:.3f} - 1)^3}} = {rock_h_weight:,.1f} \text{{ kN}}")
    else:
        rep.md(rf"- **부분안전계수 적용**: 저항계수 $\gamma_R = {gR_hud_rock}$, 하중계수 $\gamma_S = {gS_hud_rock}$, 조정계수 $\gamma_m = {gm_hud_rock}$")
        rep.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k \quad (S_k = H_{1/3})")
        rep.latex(rf"R_{{k,req}} = \frac{{\gamma_m \cdot \gamma_S \cdot H_{{1/3}}}}{{\gamma_R}} = \frac{{{gm_hud_rock} \times {gS_hud_rock} \times {H_design:.2f}}}{{{gR_hud_rock}}} = {r_Rk_req:.3f}")
        rep.latex(r"D_n = \frac{R_{k,req}}{\Delta \cdot (K_D \cot\alpha)^{1/3}}")
        rep.latex(rf"D_n = \frac{{{r_Rk_req:.3f}}}{{({r_Sr:.3f} - 1) \cdot ({Kd_rock} \times {cot_alpha})^{{1/3}}}} = {r_h_Dn:.3f} \text{{ m}}")
        rep.latex(rf"W = \gamma_r \cdot D_n^3 = {gamma_rock:.2f} \times {r_h_Dn:.3f}^3 = {rock_h_weight:,.1f} \text{{ kN}}")

    rep.custom_html("<br>")
    
    rep.title("2) Van der Meer 공식에 의한 산정", level=4)
    if design_method == "결정론적 설계법":
        rep.md(rf"- **적용파고($H_s$)**: {Hs} $\text{{m}}$")
        rep.md(rf"- **심해파장($L_{{om}}$)**: $g T_z^2 / 2\pi = 9.81 \times {Tz}^2 / 2\pi = {r_Lom:.2f} \text{{ m}}$")
        rep.md(rf"- **파형경사($s_m$)**: $H_s / L_{{om}} = {Hs} / {r_Lom:.2f} = {r_sm:.4f}$")
        rep.md(f"- **쇄파유사도($\\xi_m$)**: {html_tan} $\\alpha / \\sqrt{{s_m}} = (1/{cot_alpha}) / \\sqrt{{{r_sm:.4f}}} = {r_xim:.3f}$", unsafe_allow_html=True)
        rep.md(f"- **임계 쇄파유사도($\\xi_{{mc}}$)**: $(6.2 \\times P^{{0.31}} \\sqrt{{\\mathrm{{t}}\\kern0.1ex\\mathrm{{a}}\\kern0.1ex\\mathrm{{n}}\\,\\alpha}})^{{1/(P+0.5)}} = {r_ximc:.3f}$ (투과계수 P={P_rock})", unsafe_allow_html=True)
        rep.md(rf"- **파랑조건 판정**: $\xi_m({r_xim:.3f})$ {'<' if r_xim < r_ximc else '>'} $\xi_{{mc}}({r_ximc:.3f})$ 이므로 **{r_type}** 공식 적용")
        rep.md(rf"- **안정계수($N_s$)**: {r_Ns:.3f} (허용손상도 S={S_rock}, 내습파랑수 N={N_waves})")
        rep.md(rf"- **공칭직경($D_{{n50}}$)**: $H_s / ((S_r - 1) N_s) = {Hs} / (({r_Sr:.3f} - 1) \times {r_Ns:.3f}) = {r_Dn50:.3f} \text{{ m}}$")
        rep.latex(r"W = \gamma_r \times D_{n50}^3")
        rep.latex(rf"W = {gamma_rock:.2f} \times {r_Dn50:.3f}^3 = {rock_v_weight:,.1f} \text{{ kN}}")
    else:
        rep.md(rf"- **적용파고($H_s$)**: {Hs} $\text{{m}}$, **파형경사($s_{{om}}$)**: $H_s / L_{{om}} = {r_sm:.4f}$")
        rep.md(rf"- **파랑조건 판정**: $\xi_m({r_xim:.3f})$ {'<' if r_xim < r_ximc else '>'} $\xi_{{mc}}({r_ximc:.3f})$ 이므로 **{r_type}** 공식 적용")
        rep.md(rf"- **부분안전계수 적용**: 저항계수 $\gamma_R = {used_gR}$, 하중계수 $\gamma_S = {used_gS}$, 조정계수 $\gamma_m = {used_gm}$")
        rep.latex(r"\gamma_R \cdot R_k \ge \gamma_m \cdot \gamma_S \cdot S_k")
        rep.latex(rf"R_{{k,req}} = \frac{{\gamma_m \cdot \gamma_S \cdot H_{{1/3}}}}{{\gamma_R}} = \frac{{{used_gm} \times {used_gS} \times {Hs}}}{{{used_gR}}} = {r_v_Rk_req:.3f}")
        
        if "Plunging" in r_type:
            rep.latex(r"R_k = 6.2 \cdot S^{0.2} \cdot \Delta \cdot D_n \cdot \cot\alpha^{0.5} \cdot P^{0.18} \cdot s_{om}^{-0.25} \cdot N^{-0.1}")
            rep.latex(rf"D_n = \frac{{{r_v_Rk_req:.3f}}}{{6.2 \times {S_rock}^{{0.2}} \times ({r_Sr:.3f}-1) \times {cot_alpha}^{{0.5}} \times {P_rock}^{{0.18}} \times {r_sm:.4f}^{{-0.25}} \times {N_waves}^{{-0.1}}}} = {r_Dn50:.3f} \text{{ m}}")
        else:
            rep.latex(r"R_k = S^{0.2} \cdot \Delta \cdot D_n \cdot \cot\alpha^{(0.5-P)} \cdot P^{-0.13} \cdot s_{om}^{-0.5P} \cdot N^{-0.1}")
            rep.latex(rf"D_n = \frac{{{r_v_Rk_req:.3f}}}{{{S_rock}^{{0.2}} \times ({r_Sr:.3f}-1) \times {cot_alpha}^{{(0.5-{P_rock})}} \times {P_rock}^{{-0.13}} \times {r_sm:.4f}^{{-0.5 \times {P_rock}}} \times {N_waves}^{{-0.1}}}} = {r_Dn50:.3f} \text{{ m}}")
            
        rep.latex(rf"W = \gamma_r \cdot D_n^3 = {gamma_rock:.2f} \times {r_Dn50:.3f}^3 = {rock_v_weight:,.1f} \text{{ kN}}")

    rep.custom_html("<hr>")
    
    # ----------------------------------------------------
    # 소파블록(TTP) 상세 계산
    # ----------------------------------------------------
    rep.title(f"{lbls[lbl_idx]}. 소파블록 (TTP) 소요중량 산정", level=3)
    lbl_idx += 1

    rep.title("1) Hudson 공식에 의한 산정", level=4)
    rep.md(rf"- **설계파고($H_{{1/3}}$)**: $H_s = {H_design:.2f} \text{{ m}}$")
    rep.md(rf"- **TTP 비중($S_r$)**: $\gamma_r / \gamma_w = {gamma_ttp:.2f} / 10.1 = {t_Sr:.3f}$")
    rep.md(f"- **안정계수($K_D$)**: {Kd_ttp:.1f} (판정결과 자동적용), **사면경사({html_cot} $\\alpha$)**: {cot_alpha}", unsafe_allow_html=True)

    if design_method == "결정론적 설계법":
        rep.latex(r"W = \frac{\gamma_r H^3}{K_D \cdot \mathrm{C}\kern0.1ex\mathrm{o}\kern0.1ex\mathrm{t}\,\alpha \cdot (S_r - 1)^3}")
        rep.latex(rf"W = \frac{{{gamma_ttp:.2f} \times {H_design:.2f}^3}}{{{Kd_ttp:.1f} \times {cot_alpha} \times ({t_Sr:.3f} - 1)^3}} = {ttp_h_weight:,.1f} \text{{ kN}}")
    else:
        rep.md(rf"- **부분안전계수 적용**: 저항계수 $\gamma_R = {gR_hud_ttp}$, 하중계수 $\gamma_S = {gS_hud_ttp}$, 조정계수 $\gamma_m = {gm_hud_ttp}$")
        rep.latex(rf"R_{{k,req}} = \frac{{{gm_hud_ttp} \times {gS_hud_ttp} \times {H_design:.2f}}}{{{gR_hud_ttp}}} = {t_Rk_req:.3f}")
        rep.latex(rf"D_n = \frac{{{t_Rk_req:.3f}}}{{({t_Sr:.3f} - 1) \cdot ({Kd_ttp} \times {cot_alpha})^{{1/3}}}} = {t_h_Dn:.3f} \text{{ m}}")
        rep.latex(rf"W = \gamma_r \cdot D_n^3 = {gamma_ttp:.2f} \times {t_h_Dn:.3f}^3 = {ttp_h_weight:,.1f} \text{{ kN}}")

    rep.custom_html("<br>")

    rep.title("2) Van der Meer 공식에 의한 산정", level=4)
    if design_method == "결정론적 설계법":
        rep.md(rf"- **적용파고($H_s$)**: {Hs} $\text{{m}}$")
        rep.md(rf"- **평균주기($T_m$)**: $T_{{1/3}} / 1.2 = {Tz} / 1.2 = {t_Tm:.2f} \text{{ s}}$")
        rep.md(rf"- **심해파장($L_{{om}}$)**: $g T_m^2 / 2\pi = 9.81 \times {t_Tm:.2f}^2 / 2\pi = {t_Lom:.2f} \text{{ m}}$")
        rep.md(rf"- **파형경사($s_m$)**: $H_s / L_{{om}} = {Hs} / {t_Lom:.2f} = {t_sm:.4f}$")
        rep.md(rf"- **안정계수($N_s$)**: $(3.75 \sqrt{{N_{{od}}}} / N^{{0.25}} + 0.85) \times s_m^{{-0.2}} = {t_Ns:.3f}$ (상대피해율 Nod={Nod_ttp})")
        rep.md(rf"- **공칭직경($D_n$)**: $H_s / ((S_r - 1) N_s) = {Hs} / (({t_Sr:.3f} - 1) \times {t_Ns:.3f}) = {t_Dn:.3f} \text{{ m}}$")
        rep.latex(r"W = \gamma_r \times D_n^3")
        rep.latex(rf"W = {gamma_ttp:.2f} \times {t_Dn:.3f}^3 = {ttp_v_weight:,.1f} \text{{ kN}}")
    else:
        rep.md(rf"- **적용파고($H_s$)**: {Hs} $\text{{m}}$")
        rep.md(rf"- **부분안전계수 적용**: 저항계수 $\gamma_R = {gR_vdm_ttp}$, 하중계수 $\gamma_S = {gS_vdm_ttp}$, 조정계수 $\gamma_m = {gm_vdm_ttp}$")
        rep.latex(rf"R_{{k,req}} = \frac{{\gamma_m \cdot \gamma_S \cdot H_{{1/3}}}}{{\gamma_R}} = \frac{{{gm_vdm_ttp} \times {gS_vdm_ttp} \times {Hs}}}{{{gR_vdm_ttp}}} = {t_v_Rk_req:.3f}")
        rep.latex(r"R_k = \left(3.75 \frac{N_o^{0.5}}{N^{0.25}} + 0.85\right) \Delta \cdot D_n \cdot s_{om}^{-0.2}")
        rep.latex(rf"D_n = \frac{{{t_v_Rk_req:.3f}}}{{\left(3.75 \frac{{{Nod_ttp}^{0.5}}}{{{N_waves}^{0.25}}} + 0.85\right) \times ({t_Sr:.3f}-1) \times {t_sm:.4f}^{{-0.2}}}} = {t_Dn:.3f} \text{{ m}}")
        rep.latex(rf"W = \gamma_r \cdot D_n^3 = {gamma_ttp:.2f} \times {t_Dn:.3f}^3 = {ttp_v_weight:,.1f} \text{{ kN}}")

    rep.custom_html("<hr>")

    # ----------------------------------------------------
    # 기타 소파블록 상세 계산
    # ----------------------------------------------------
    rep.title(f"{lbls[lbl_idx]}. 기타 소파블록 소요중량 산정", level=3)
    lbl_idx += 1

    rep.title("1) Hudson 공식에 의한 산정", level=4)
    rep.md(rf"- **설계파고($H_{{1/3}}$)**: $H_s = {H_design:.2f} \text{{ m}}$")
    rep.md(rf"- **기타 블록 비중($S_r$)**: $\gamma_r / \gamma_w = {gamma_other:.2f} / 10.1 = {o_Sr:.3f}$")
    rep.md(f"- **안정계수($K_D$)**: {Kd_other:.1f} (사용자 입력), **사면경사({html_cot} $\\alpha$)**: {cot_alpha}", unsafe_allow_html=True)
    
    if design_method == "결정론적 설계법":
        rep.latex(r"W = \frac{\gamma_r H^3}{K_D \cdot \mathrm{C}\kern0.1ex\mathrm{o}\kern0.1ex\mathrm{t}\,\alpha \cdot (S_r - 1)^3}")
        rep.latex(rf"W = \frac{{{gamma_other:.2f} \times {H_design:.2f}^3}}{{{Kd_other:.1f} \times {cot_alpha} \times ({o_Sr:.3f} - 1)^3}} = {other_h_weight:,.1f} \text{{ kN}}")
    else:
        rep.md(rf"- **부분안전계수 적용**: 저항계수 $\gamma_R = {gR_hud_ttp}$, 하중계수 $\gamma_S = {gS_hud_ttp}$, 조정계수 $\gamma_m = {gm_hud_ttp}$")
        rep.latex(rf"R_{{k,req}} = \frac{{{gm_hud_ttp} \times {gS_hud_ttp} \times {H_design:.2f}}}{{{gR_hud_ttp}}} = {o_Rk_req:.3f}")
        rep.latex(rf"D_n = \frac{{{o_Rk_req:.3f}}}{{({o_Sr:.3f} - 1) \cdot ({Kd_other} \times {cot_alpha})^{{1/3}}}} = {o_h_Dn:.3f} \text{{ m}}")
        rep.latex(rf"W = \gamma_r \cdot D_n^3 = {gamma_other:.2f} \times {o_h_Dn:.3f}^3 = {other_h_weight:,.1f} \text{{ kN}}")
        
    rep.md("*(기타 소파블록은 설정에 따라 Hudson 공식만 적용하여 산출합니다.)*")

    rep.custom_html("<hr>")

    # ====================================================
    # 다운로드 버튼 (HTML & MS Word 동시 지원 + 초고속 렌더링)
    # ====================================================
    st.divider()
    st.header("🖨️ 상세 계산 보고서 다운로드")
    st.info("💡 **HTML 출력:** 브라우저에서 '인쇄(Ctrl+P)' 기능을 통해 PDF로 저장하기 좋습니다.\n\n💡 **Word 출력:** 수식을 문서 내부에 고해상도 이미지로 직접 박제하며, 멀티스레딩(Multi-threading) 기술을 적용해 생성 속도를 비약적으로 단축했습니다.")

    # API 호출 속도 향상 및 중복 다운로드 방지용 캐싱
    @st.cache_data(show_spinner=False)
    def fetch_equation_image(api_url):
        import urllib.request
        import base64
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                return base64.b64encode(response.read()).decode('utf-8')
        except Exception:
            return None

    with st.spinner("Word 보고서를 위한 수식 및 그래프를 고속 변환 중입니다. 잠시만 기다려주세요..."):
        report_html = rep.get_html()
        
        import urllib.parse
        import urllib.request
        import concurrent.futures
        import re
        import base64
        
        word_html = report_html
        attachments = {}
        counters = {'img': 0, 'eq': 0}

        # MathJax 스크립트 삭제
        word_html = re.sub(r'<script.*?</script>', '', word_html, flags=re.DOTALL)

        # 표(Table) 테두리 강제 설정
        word_html = word_html.replace('<table', '<table style="border-collapse: collapse; width: 100%; border: 1px solid black; margin-bottom: 20px;"')
        word_html = word_html.replace('<th>', '<th style="border: 1px solid black; padding: 8px; background-color: #f2f2f2; text-align: center;">')
        word_html = word_html.replace('<td>', '<td style="border: 1px solid black; padding: 8px; text-align: center;">')

        # HTML 내 <img> 태그(base64 데이터) 추출 및 CID 치환
        def image_replacer(match):
            b64_data = match.group(1)
            counters['img'] += 1
            img_id = f"fig_img_{counters['img']}"
            attachments[img_id] = b64_data
            return f'src="cid:{img_id}" style="max-width: 100%; height: auto;"'
            
        word_html = re.sub(r'src=[\'"]data:image/png;base64,([^\'"]+)[\'"]', image_replacer, word_html)

        # --- 🚀 초고속 병렬 다운로드 준비 ---
        display_maths = re.findall(r'\$\$(.*?)\$\$', word_html, flags=re.DOTALL)
        inline_maths = re.findall(r'\$([^\$]+)\$', word_html)
        
        urls_to_fetch = set()
        
        def prepare_url(eq_text, is_display):
            eq_clean = re.sub(r'\\text\{([^}]+)\}', lambda m: "" if re.search(r'[가-힣]', m.group(1)) else m.group(0), eq_text)
            eq_clean = eq_clean.replace(r'\max', 'max').replace(r'\min', 'min').replace(r'\mathbf', '')
            dpi = "110" if is_display else "100"
            return f"https://latex.codecogs.com/png.image?\\dpi{{{dpi}}}\\bg_white&space;{urllib.parse.quote(eq_clean)}"
        
        for eq in display_maths:
            urls_to_fetch.add(prepare_url(eq.strip(), True))
            
        for eq in inline_maths:
            txt = eq.strip()
            if any(op in txt for op in ["\\", "=", "+", "-", "/", "times", "ge", "le", "<", ">"]):
                urls_to_fetch.add(prepare_url(txt, False))
                
        # 다중 스레드로 수식 이미지 일괄 다운로드
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            list(executor.map(fetch_equation_image, urls_to_fetch))

        # --- 수식 이미지 치환 ---
        def render_math_to_img(eq_text, is_display):
            korean_parts = []
            def kr_replacer(m):
                txt = m.group(1)
                if re.search(r'[가-힣]', txt):
                    korean_parts.append(txt)
                    return ""
                return m.group(0)
                
            eq_clean = re.sub(r'\\text\{([^}]+)\}', kr_replacer, eq_text)
            eq_clean = eq_clean.replace(r'\max', 'max').replace(r'\min', 'min').replace(r'\mathbf', '')
            
            eq_url = urllib.parse.quote(eq_clean)
            dpi = "110" if is_display else "100"
            api_url = f"https://latex.codecogs.com/png.image?\\dpi{{{dpi}}}\\bg_white&space;{eq_url}"
            
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
            return f'''
            <table align="center" style="border-collapse: collapse; border: none; margin: 10px auto; width: 100%;">
                <tr><td style="border: none; padding: 0; text-align: center;">{img_tag} {kr_addon}</td></tr>
            </table>
            '''
            
        word_html = re.sub(r'\$\$(.*?)\$\$', display_math_replacer, word_html, flags=re.DOTALL)

        def inline_math_replacer(match):
            eq_text = match.group(1).strip()
            if any(op in eq_text for op in ["\\", "=", "+", "-", "/", "times", "ge", "le", "<", ">"]):
                img_tag, kr_addon = render_math_to_img(eq_text, False)
                return f"{img_tag}{kr_addon}"
            else:
                return f"${eq_text}$"
                
        word_html = re.sub(r'\$([^\$]+)\$', inline_math_replacer, word_html)

        # 잔여 기호 Word 호환 HTML 첨자 변환
        word_html = word_html.replace("$H_{1/3}$", "H<sub>1/3</sub>").replace("$T_z$", "T<sub>z</sub>").replace("$h_{1/3, peak}$", "h<sub>1/3, peak</sub>")
        word_html = word_html.replace("$H_0'$", "H<sub>0</sub>'").replace("$H_s$", "H<sub>s</sub>").replace("$T_{1/3}$", "T<sub>1/3</sub>")
        word_html = word_html.replace("$\\gamma_R$", "γ<sub>R</sub>").replace("$\\gamma_S$", "γ<sub>S</sub>").replace("$\\gamma_m$", "γ<sub>m</sub>")
        word_html = word_html.replace("$\\Delta$", "Δ").replace("$\\xi_m$", "ξ<sub>m</sub>").replace("$\\xi_{mc}$", "ξ<sub>mc</sub>")
        word_html = word_html.replace("$\\alpha$", "α").replace("$S_r$", "S<sub>r</sub>").replace("$K_D$", "K<sub>D</sub>")
        word_html = word_html.replace("$L_0$", "L<sub>0</sub>").replace("$K_s$", "K<sub>s</sub>").replace("$H_b$", "H<sub>b</sub>")
        word_html = word_html.replace("$d_{b,max}$", "d<sub>b,max</sub>").replace("$d_{b,min}$", "d<sub>b,min</sub>")
        word_html = re.sub(r'\$([a-zA-Z]+)_([a-zA-Z0-9\+\-]+)\$', r'\1<sub>\2</sub>', word_html)
        word_html = word_html.replace('$', '')

        # --- MHTML 패키징 ---
        boundary = "----=_NextPart_HTML_DOC_001"
        mhtml = f'MIME-Version: 1.0\nContent-Type: multipart/related; type="text/html"; boundary="{boundary}"\n\n'
        mhtml += f'--{boundary}\nContent-Type: text/html; charset="utf-8"\nContent-Transfer-Encoding: 8bit\n\n'
        mhtml += word_html + "\n\n"
        
        for cid, b64 in attachments.items():
            mhtml += f'--{boundary}\nContent-Type: image/png\nContent-Transfer-Encoding: base64\nContent-ID: <{cid}>\n\n{b64}\n\n'
        mhtml += f"--{boundary}--\n"

    # --- 3. 버튼 레이아웃 구성 ---
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        st.download_button(
            label="📄 통합 산정 보고서 다운로드 (HTML 웹용)",
            data=report_html.encode('utf-8'),
            file_name=f"피복재_통합산정보고서({design_method}).html",
            mime="text/html",
            use_container_width=True
        )
        
    with col_btn2:
        st.download_button(
            label="📝 통합 산정 보고서 다운로드 (MS Word용)",
            data=mhtml.encode('utf-8'),
            file_name=f"피복재_통합산정보고서({design_method}).doc",
            mime="application/msword",
            use_container_width=True
        )

else:
    st.info("👈 좌측 사이드바에 제원을 입력하고 **검토 실행** 버튼을 눌러주세요.")
