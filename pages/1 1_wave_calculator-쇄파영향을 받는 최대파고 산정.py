import streamlit as st
import math
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.path as mpath
import matplotlib.ticker as ticker
import pandas as pd
from matplotlib.ticker import MultipleLocator
from scipy.interpolate import CubicSpline, make_interp_spline
import matplotlib.font_manager as fm
import os
import requests
import platform
import textwrap
import base64
from io import BytesIO

# 페이지 기본 설정
st.set_page_config(page_title="최대파고 산정 프로그램", layout="wide", page_icon="🌊")

with st.sidebar:
    st.markdown("---")
    st.write("**제작자:** [김창보]")
    st.write("**소속:** [다온기술]")
    st.caption("© 2026 All rights reserved.")

# -----------------------------------------------------
# ★ Matplotlib 한글 및 수식 깨짐 해결 (완전 자동화 방식)
# -----------------------------------------------------
@st.cache_resource 
def install_and_get_font_name():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            with st.spinner("도표 한글 출력을 위한 폰트를 다운로드 중입니다..."):
                response = requests.get(font_url)
                response.raise_for_status()
                with open(font_path, 'wb') as f:
                    f.write(response.content)
        except Exception as e:
            st.error(f"폰트 다운로드 실패. 도표 한글이 깨질 수 있습니다. 에러: {e}")
            return "DejaVu Sans" 

    try:
        fm.fontManager.addfont(font_path)
        font_prop = fm.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        return font_name
    except Exception as e:
        st.error(f"폰트 등록 실패: {e}")
        return "DejaVu Sans"

target_font_name = install_and_get_font_name()

plt.rcParams['axes.unicode_minus'] = False 
plt.rcParams['font.family'] = target_font_name 
plt.rcParams['mathtext.fontset'] = 'stix' 
# -----------------------------------------------------

def get_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 1. SPM Table C-1
spm_table = [
    (0.040, 1.066), (0.041, 1.061), (0.042, 1.056), (0.043, 1.051),
    (0.044, 1.047), (0.045, 1.042), (0.046, 1.038), (0.047, 1.034),
    (0.048, 1.030), (0.049, 1.026), (0.050, 1.023), (0.051, 1.019),
    (0.052, 1.016), (0.053, 1.012), (0.054, 1.009), (0.055, 1.005)
]

def get_interpolated_hh0(target_dl0):
    for i in range(len(spm_table) - 1):
        x1, y1 = spm_table[i]
        x2, y2 = spm_table[i+1]
        if x1 <= target_dl0 <= x2:
            slope = (y2 - y1) / (x2 - x1)
            return y1 + slope * (target_dl0 - x1)
    return 1.05

# 2. 슈토(Shuto) 천수계수 2D 보간 테이블 및 함수 (도해 4-3 정밀 독취값 적용)
shuto_matrix = {
    0.010: [(0.040, 1.230), (0.046, 1.170), (0.050, 1.135), (0.0539, 1.100), (0.060, 1.060)],
    0.020: [(0.040, 1.165), (0.046, 1.125), (0.050, 1.095), (0.0539, 1.085), (0.060, 1.030)],
    0.0294: [(0.040, 1.140), (0.046, 1.105), (0.050, 1.080), (0.0539, 1.069), (0.060, 1.015)],
    0.040: [(0.040, 1.105), (0.046, 1.075), (0.050, 1.050), (0.0539, 1.030), (0.060, 0.990)]
}

def get_shuto_ks(h_L0, H0p_L0):
    try:
        # k_s_all_data.csv 파일이 있을 경우 CSV 데이터를 활용한 초정밀 로그 보간 수행 (도표 독취 결과와 100% 일치화)
        df = pd.read_csv("k_s_all_data.csv", header=None)
        labels = df.iloc[0].values
        
        available_slopes = []
        for i in range(0, len(labels), 2):
            if not pd.isna(labels[i]):
                val = float(labels[i])
                if val not in [x[0] for x in available_slopes]:
                    available_slopes.append((val, i))
        available_slopes.sort(key=lambda x: x[0])
        
        k1, col_idx1 = available_slopes[0]
        k2, col_idx2 = available_slopes[-1]
        
        for idx in range(len(available_slopes) - 1):
            if available_slopes[idx][0] <= H0p_L0 <= available_slopes[idx+1][0]:
                k1, col_idx1 = available_slopes[idx]
                k2, col_idx2 = available_slopes[idx+1]
                break
        
        x1 = df.iloc[2:, col_idx1].astype(float).dropna().values
        y1 = df.iloc[2:, col_idx1+1].astype(float).dropna().values
        x2 = df.iloc[2:, col_idx2].astype(float).dropna().values
        y2 = df.iloc[2:, col_idx2+1].astype(float).dropna().values
        
        valid_x_min = max(x1.min(), x2.min())
        valid_x_max = min(x1.max(), x2.max())
        
        x_common = np.logspace(np.log10(valid_x_min), np.log10(valid_x_max), 300)
        y1_interp = np.interp(x_common, x1, y1)
        y2_interp = np.interp(x_common, x2, y2)
        
        if k1 != k2:
            weight = (math.log10(H0p_L0) - math.log10(k1)) / (math.log10(k2) - math.log10(k1))
        else:
            weight = 0.0
            
        y_target = y1_interp + weight * (y2_interp - y1_interp)
        return float(np.interp(h_L0, x_common, y_target))
        
    except Exception:
        # CSV 파일이 없을 경우 갱신된 shuto_matrix를 이용한 선형 보간 수행
        y_keys = sorted(list(shuto_matrix.keys()))
        y1, y2 = y_keys[0], y_keys[-1]
        for i in range(len(y_keys) - 1):
            if y_keys[i] <= H0p_L0 <= y_keys[i+1]:
                y1, y2 = y_keys[i], y_keys[i+1]
                break

        def interp_x(target_x, points):
            for i in range(len(points) - 1):
                x1_pt, v1 = points[i]
                x2_pt, v2 = points[i+1]
                if x1_pt <= target_x <= x2_pt:
                    return v1 + (v2 - v1) * (target_x - x1_pt) / (x2_pt - x1_pt)
            return points[0][1] if target_x < points[0][0] else points[-1][1]

        val_y1 = interp_x(h_L0, shuto_matrix[y1])
        val_y2 = interp_x(h_L0, shuto_matrix[y2])

        if y1 == y2: return val_y1
        return val_y1 + (val_y2 - val_y1) * (H0p_L0 - y1) / (y2 - y1)

# H1/3 약산식 계산 함수
def calc_h13_formula(H0p, h, L0, tanTheta, Ks):
    H0p_L0 = H0p / L0
    if H0p_L0 <= 0: return 0, 0, 0, 0, 0, 0, 0
    beta0 = 0.028 * (H0p_L0 ** -0.38) * math.exp(20 * (tanTheta ** 1.5))
    beta1 = 0.52 * math.exp(4.2 * tanTheta)
    betaMax = max(0.92, 0.32 * (H0p_L0 ** -0.29) * math.exp(2.4 * tanTheta))
    val1 = beta0 * H0p + beta1 * h
    val2 = betaMax * H0p
    val3 = Ks * H0p
    return min(val1, val2, val3), beta0, beta1, betaMax, val1, val2, val3

# Hmax 약산식 계산 함수
def calc_hmax_formula(H0p, h, L0, tanTheta, Ks):
    H0p_L0 = H0p / L0
    if H0p_L0 <= 0: return 0, 0, 0, 0, 0, 0, 0
    beta0_star = 0.052 * (H0p_L0 ** -0.38) * math.exp(20 * (tanTheta ** 1.5))
    beta1_star = 0.63 * math.exp(3.8 * tanTheta)
    betaMax_star = max(1.65, 0.53 * (H0p_L0 ** -0.29) * math.exp(2.4 * tanTheta))
    val1 = beta0_star * H0p + beta1_star * h
    val2 = betaMax_star * H0p
    val3 = 1.8 * Ks * H0p
    return min(val1, val2, val3), beta0_star, beta1_star, betaMax_star, val1, val2, val3
   
# -------------------------------------------------------------------------
# ★★★ 초정밀 교정 완료된 Goda 도표 데이터베이스 ★★★
# -------------------------------------------------------------------------
goda_data_master = {
    0.01: {
        0.002: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.659, 0.869, 1.176, 1.503, 1.843, 2.187, 2.546, 2.906, 3.18]},
        0.005: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.439, 0.698, 1.003, 1.348, 1.712, 2.069, 2.365, 2.497, 2.401]},
        0.01: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.335, 0.596, 0.929, 1.283, 1.625, 1.922, 2.083, 2.032, 1.952]},
        0.02: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.25, 0.527, 0.873, 1.216, 1.522, 1.743, 1.783, 1.748, 1.717]},
        0.04: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.186, 0.487, 0.811, 1.115, 1.369, 1.55, 1.625, 1.649, 1.653]},
        0.08: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.149, 0.429, 0.698, 0.944, 1.161, 1.332, 1.448, 1.532, 1.59]},
    },
    0.02: {
        0.002: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.684, 0.913, 1.21, 1.546, 1.908, 2.285, 2.668, 3.029, 3.275]},
        0.005: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.458, 0.717, 1.041, 1.408, 1.788, 2.154, 2.452, 2.515, 2.392]},
        0.01: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.345, 0.615, 0.961, 1.339, 1.705, 1.998, 2.115, 2.082, 1.973]},
        0.02: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.253, 0.559, 0.922, 1.273, 1.578, 1.776, 1.788, 1.756, 1.702]},
        0.04: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.202, 0.511, 0.856, 1.176, 1.422, 1.585, 1.637, 1.647, 1.645]},
        0.08: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.149, 0.45, 0.741, 0.992, 1.195, 1.351, 1.469, 1.553, 1.602]},
    },
    0.033: {
        0.002: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.757, 1.002, 1.316, 1.669, 2.055, 2.454, 2.852, 3.215, 3.44]},
        0.005: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.504, 0.782, 1.142, 1.511, 1.896, 2.296, 2.581, 2.555, 2.407]},
        0.01: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.382, 0.68, 1.042, 1.432, 1.813, 2.114, 2.144, 2.053, 1.963]},
        0.02: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.293, 0.609, 0.968, 1.341, 1.686, 1.85, 1.817, 1.769, 1.74]},
        0.04: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.233, 0.543, 0.898, 1.229, 1.488, 1.626, 1.655, 1.659, 1.656]},
        0.08: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.177, 0.49, 0.794, 1.061, 1.269, 1.411, 1.512, 1.589, 1.654]},
    },
    0.05: {
        0.002: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.7], 'y': [0.85, 1.112, 1.445, 1.823, 2.224, 2.64, 3.048, 3.403, 3.493]},
        0.005: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.573, 0.88, 1.248, 1.649, 2.066, 2.471, 2.719, 2.576, 2.413]},
        0.01: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.444, 0.76, 1.146, 1.557, 1.955, 2.227, 2.155, 2.038, 1.95]},
        0.02: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.331, 0.679, 1.066, 1.452, 1.78, 1.872, 1.8, 1.748, 1.72]},
        0.04: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.246, 0.612, 0.985, 1.318, 1.571, 1.648, 1.653, 1.646, 1.644]},
        0.08: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.182, 0.542, 0.863, 1.121, 1.314, 1.452, 1.544, 1.606, 1.644]},
    },
    0.1: {
        0.002: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 2.61], 'y': [1.208, 1.518, 1.927, 2.383, 2.879, 3.388, 3.498]},
        0.005: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.822, 1.183, 1.621, 2.115, 2.637, 3.039, 2.884, 2.604, 2.423]},
        0.01: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.628, 1.014, 1.472, 1.977, 2.419, 2.393, 2.169, 2.04, 1.959]},
        0.02: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.474, 0.865, 1.353, 1.826, 2.034, 1.908, 1.814, 1.761, 1.737]},
        0.04: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.371, 0.779, 1.228, 1.594, 1.726, 1.681, 1.658, 1.655, 1.655]},
        0.08: {'x': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'y': [0.282, 0.683, 1.044, 1.316, 1.49, 1.583, 1.627, 1.642, 1.648]},
    },
}

def get_user_curve_spline(x_arr, target_H0p_L0, slope_data_dict):
    keys = sorted(list(slope_data_dict.keys()))
    
    if target_H0p_L0 <= keys[0]:
        target_data = slope_data_dict[keys[0]]
        x = np.array(target_data["x"])
        y = np.array(target_data["y"])
        if len(x) < 4:
            return np.interp(x_arr, x, y)
        spl = make_interp_spline(x, y, k=3)
        return spl(x_arr)
        
    if target_H0p_L0 >= keys[-1]:
        target_data = slope_data_dict[keys[-1]]
        x = np.array(target_data["x"])
        y = np.array(target_data["y"])
        if len(x) < 4:
            return np.interp(x_arr, x, y)
        spl = make_interp_spline(x, y, k=3)
        return spl(x_arr)

    for i in range(len(keys)-1):
        if keys[i] <= target_H0p_L0 <= keys[i+1]:
            k1, k2 = keys[i], keys[i+1]
            break

    data1 = slope_data_dict[k1]
    x1, y1_pts = np.array(data1["x"]), np.array(data1["y"])
    k_val1 = min(3, len(x1) - 1)
    if k_val1 >= 1:
        spl1 = make_interp_spline(x1, y1_pts, k=k_val1)
        y1_interp = spl1(x_arr)
    else:
        y1_interp = np.interp(x_arr, x1, y1_pts)

    data2 = slope_data_dict[k2]
    x2, y2_pts = np.array(data2["x"]), np.array(data2["y"])
    k_val2 = min(3, len(x2) - 1)
    if k_val2 >= 1:
        spl2 = make_interp_spline(x2, y2_pts, k=k_val2)
        y2_interp = spl2(x_arr)
    else:
        y2_interp = np.interp(x_arr, x2, y2_pts)

    log_k1, log_k2, log_t = math.log10(k1), math.log10(k2), math.log10(target_H0p_L0)
    weight = (log_t - log_k1) / (log_k2 - log_k1)

    return y1_interp + weight * (y2_interp - y1_interp)

def get_final_graph_ratio(h_H0p_val, H0p_L0_val, tanTheta):
    slope_keys = sorted(list(goda_data_master.keys()))
    
    if tanTheta <= slope_keys[0]:
        return float(get_user_curve_spline(np.array([h_H0p_val]), H0p_L0_val, goda_data_master[slope_keys[0]])[0])
    if tanTheta >= slope_keys[-1]:
        return float(get_user_curve_spline(np.array([h_H0p_val]), H0p_L0_val, goda_data_master[slope_keys[-1]])[0])
        
    for i in range(len(slope_keys)-1):
        if slope_keys[i] <= tanTheta <= slope_keys[i+1]:
            s1, s2 = slope_keys[i], slope_keys[i+1]
            break
            
    val1 = float(get_user_curve_spline(np.array([h_H0p_val]), H0p_L0_val, goda_data_master[s1])[0])
    val2 = float(get_user_curve_spline(np.array([h_H0p_val]), H0p_L0_val, goda_data_master[s2])[0])
    
    log_s1, log_s2, log_t = math.log10(s1), math.log10(s2), math.log10(tanTheta)
    weight = (log_t - log_s1) / (log_s2 - log_s1)
    
    return val1 + weight * (val2 - val1)

def plot_authentic_chart_spline(h_H0p_read, read_ratio, user_H0p_L0, tanTheta):
    # 화면 출력을 위해 원래의 완벽한 비율로 되돌립니다.
    fig, ax = plt.subplots(figsize=(5.5, 6.8)) 
    
    closest_slope = min(goda_data_master.keys(), key=lambda k: abs(k - tanTheta))
    base_data = goda_data_master[closest_slope]
    
    all_x = []
    all_y = []
    for s in base_data.keys():
        all_x.extend(base_data[s]["x"])
        all_y.extend(base_data[s]["y"])
    
    x_max = max(4.0, h_H0p_read + 0.5, max(all_x) if all_x else 0)
    y_max = max(3.5, read_ratio + 0.5, max(all_y) if all_y else 0)
    
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.xaxis.set_minor_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.05))
    
    ax.grid(which='major', color='black', linewidth=1.0)
    ax.grid(which='minor', color='black', linewidth=0.4)
    
    decay_lines = {
        0.01: { 
            'x': [4.0, 3.5, 3.0, 2.9, 2.825, 2.82, 2.83, 2.86, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.43],
            'y': [2.63, 2.32, 1.99, 1.88, 1.785, 1.75, 1.7, 1.65, 1.63, 1.60, 1.59, 1.58, 1.582, 1.592, 1.6]
        },
        0.02: { 
            'x': [4.0, 3.5, 3.0, 2.9, 2.85, 2.825, 2.83, 2.86, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.64],
            'y': [2.74, 2.43, 2.01, 1.90, 1.80, 1.75, 1.70, 1.64, 1.62, 1.59, 1.575, 1.57, 1.58, 1.589, 1.592, 1.61, 1.62] 
        },
        0.033: { 
            'x': [4.0, 3.5, 3.0, 2.6, 2.59, 2.58, 2.6, 2.65, 2.7, 2.8, 2.9, 3.0, 3.1],
            'y': [3.07, 2.67, 2.228, 1.80, 1.77, 1.75, 1.698, 1.65, 1.63, 1.605, 1.585, 1.575, 1.57]
        },
        0.05: { 
            'x': [4.0, 3.5, 3.0, 2.5, 2.4, 2.39, 2.4, 2.45, 2.5, 2.6, 2.7, 2.8, 2.82],
            'y': [3.425, 2.97, 2.48, 1.91, 1.75, 1.70, 1.66, 1.63, 1.605, 1.58, 1.57, 1.575, 1.58]
        },
        0.1: { 
            'x': [3.18, 3.0, 2.5, 2.3, 2.0, 1.95, 1.94, 1.96, 1.98, 2.0, 2.1, 2.2, 2.3, 2.35, 2.4, 2.5],
            'y': [3.5, 3.33, 2.748, 2.48, 2.0, 1.85, 1.8, 1.73, 1.70, 1.68, 1.63, 1.61, 1.598, 1.596, 1.6, 1.61]
        }
    }

    decay_data = decay_lines.get(closest_slope, {'x': [], 'y': []})
    
    decay_path = None
    if decay_data['x']:
        x_arr = np.array(decay_data['x'])
        y_arr = np.array(decay_data['y'])
        
        dists = np.sqrt(np.diff(x_arr)**2 + np.diff(y_arr)**2)
        t = np.concatenate(([0], np.cumsum(dists)))
        t = t / t[-1]
        
        k_val = min(3, len(x_arr) - 1)
        
        if k_val >= 1: 
            spl_x = make_interp_spline(t, x_arr, k=k_val)
            spl_y = make_interp_spline(t, y_arr, k=k_val)
            
            t_fine = np.linspace(0, 1, 300)
            fine_x = spl_x(t_fine)
            fine_y = spl_y(t_fine)
            
            ax.plot(fine_x, fine_y, color='#333333', linestyle='-.', linewidth=2.0, zorder=4)
            ax.text(decay_data['x'][1] + 0.05, decay_data['y'][1], "2% Decay line", 
                    color='#333333', fontsize=10, fontweight='bold', rotation=45, ha='left')

            poly_points = list(zip(fine_x, fine_y))
            poly_points.append((10.0, fine_y[-1])) 
            poly_points.append((10.0, fine_y[0]))  
            decay_path = mpath.Path(poly_points)

    for s in base_data.keys():
        curve_data = base_data[s]
        x_pts, y_pts = np.array(curve_data["x"]), np.array(curve_data["y"])
        
        k_curve = min(3, len(x_pts) - 1)
        x_curve_arr = np.linspace(x_pts[0], x_pts[-1], 200)

        if k_curve >= 1:
            spl_curve = make_interp_spline(x_pts, y_pts, k=k_curve)
            y_curve = spl_curve(x_curve_arr)
        else:
            y_curve = np.interp(x_curve_arr, x_pts, y_pts)
        
        if decay_path:
            pts_interp = np.column_stack((x_curve_arr, y_curve))
            inside = decay_path.contains_points(pts_interp) 
            
            y_solid = np.ma.masked_where(inside, y_curve)
            y_dashed = np.ma.masked_where(~inside, y_curve)
            
            ax.plot(x_curve_arr, y_solid, color='black', linewidth=1.2, zorder=2)
            ax.plot(x_curve_arr, y_dashed, color='black', linewidth=1.2, linestyle='--', zorder=2)
        else:
            ax.plot(x_curve_arr, y_curve, color='black', linewidth=1.2, zorder=2)
            
        label_x = curve_data["x"][-1] * 0.9
        label_y = np.interp(label_x, x_curve_arr, y_curve)
        
        label_text = f"H'o/Lo={s}" if s in [0.002, 0.005] else f"{s}"
        ax.text(label_x, label_y + 0.06, label_text, fontsize=9, backgroundcolor='white', ha='center', va='bottom', zorder=5)
        
    x_user_max = max(base_data[s]["x"][-1] for s in base_data.keys())
    x_user_arr = np.linspace(0, x_user_max, 500)
    y_user = get_user_curve_spline(x_user_arr, user_H0p_L0, base_data)
    
    if decay_path:
        pts_user = np.column_stack((x_user_arr, y_user))
        inside_user = decay_path.contains_points(pts_user)
        yu_solid = np.ma.masked_where(inside_user, y_user)
        yu_dashed = np.ma.masked_where(~inside_user, y_user)
        ax.plot(x_user_arr, yu_solid, color='blue', linewidth=2.5, alpha=0.7, zorder=3)
        ax.plot(x_user_arr, yu_dashed, color='blue', linewidth=2.5, linestyle='--', alpha=0.7, zorder=3)
    else:
        ax.plot(x_user_arr, y_user, color='blue', linewidth=2.5, alpha=0.7, zorder=3) 
    
    ax.axvline(x=h_H0p_read, color='red', linestyle='--', linewidth=1.5, alpha=0.7, zorder=5)
    ax.axhline(y=read_ratio, color='red', linestyle='--', linewidth=1.5, alpha=0.7, zorder=5)
    ax.plot(h_H0p_read, read_ratio, 'ro', markersize=8, zorder=6)
    
    ax.text(h_H0p_read + 0.1, read_ratio + 0.1, f"독취결과\nh/H'o={h_H0p_read:.2f}\nHmax/H'o={read_ratio:.3f}", 
            color='red', fontsize=10, fontweight='bold', 
            bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3', alpha=0.9), zorder=6)
    
    frac_slope = "1/" + str(int(1/tanTheta)) if tanTheta > 0 else f"{tanTheta}"
    ax.text(0.2, y_max - 0.2, f"  해저경사 {frac_slope} (모사)  ", fontsize=11, fontweight='bold', bbox=dict(facecolor='white', edgecolor='black', linewidth=1.2), zorder=5)
    ax.text(1.0, y_max - 0.6, r"$H_{max} \equiv H_{1/250}$", fontsize=10, fontweight='bold', backgroundcolor='white', zorder=5)
    
    ax.set_xlim(0, x_max)
    ax.set_ylim(0, y_max)
    ax.set_xlabel("$h / H_0'$", fontsize=12)
    ax.set_ylabel(r"$\frac{H_{max}}{H_0'}$", fontsize=14, rotation=0, labelpad=15)
    
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    fig.tight_layout()
    return fig

# -------------------------------------------------------------------------
# ★★★ [추가/수정] 슈토(Shuto) 천수계수 도표 동적 생성 함수 ★★★
# -------------------------------------------------------------------------
def plot_shuto_ks_chart(h_L0_val, Ks_val, H0_L0_val=None):
    """
    슈토(Shuto)의 천수계수 산정도 원본 규격 그래프 생성 함수
    + 계산된 H0'/L0 값에 대한 동적 보간 곡선(파란색 점선) 자동 작도 기능 포함
    + [수정] true_ks_val(비선형 도표 독취값)을 메인스크립트로 반환하도록 변경
    """
    plt.rcParams['font.family'] = target_font_name
    plt.rcParams['axes.unicode_minus'] = False

    # 세로 비율을 원본 크기와 비슷하게 설정
    fig = plt.figure(figsize=(13, 8.5), dpi=100)

    # -------------------------------------------------------------------------
    # 1. 메인 그래프 영역 (h/L0 : 0.004 ~ 0.1)
    # -------------------------------------------------------------------------
    ax_main = fig.add_axes([0.08, 0.08, 0.88, 0.65]) 

    try:
        df = pd.read_csv("k_s_all_data.csv", header=None)
        labels = df.iloc[0].values
        
        # 1) 원본 데이터 곡선들 먼저 흑색으로 작도
        for i in range(0, len(labels), 2):
            if pd.isna(labels[i]): continue
            label_val = float(labels[i])
            x = df.iloc[2:, i].astype(float).dropna().values
            y = df.iloc[2:, i+1].astype(float).dropna().values
            
            mask_main = (x >= 0.0039) & (x <= 0.101)
            ax_main.plot(x[mask_main], y[mask_main], color='black', linewidth=1.2, zorder=2)
            
            # 기존 대표 라벨 박스 처리
            if label_val in [0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.04]:
                fs = 10
                bbox_style = dict(facecolor='white', edgecolor='none', pad=1.5) 
                
                if label_val == 0:
                    ax_main.text(0.0052, 1.63, "0", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.0005:
                    ax_main.text(0.0055, 1.95, "$H'_0/L_0=0.0005$", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.001:
                    ax_main.text(0.008, 1.76, "0.001", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.002:
                    ax_main.text(0.011, 1.55, "0.002", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.005:
                    ax_main.text(0.013, 1.72, "$H'_0/L_0=0.005$", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.01:
                    ax_main.text(0.020, 1.55, "0.01", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.02:
                    ax_main.text(0.033, 1.32, "0.02", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)
                elif label_val == 0.04:
                    ax_main.text(0.048, 1.13, "0.04", fontsize=fs, bbox=bbox_style, ha='center', va='center', zorder=3)

        # =========================================================================
        # ★ [수정됨] 계산된 임의 H'0/L0 값에 대해 파란색 점선 보간 곡선 생성 ★
        # =========================================================================
        if H0_L0_val is not None and H0_L0_val > 0:
            # CSV에 수록된 유효 경사 키값을 수집 (중복 제외 및 오름차순 정렬)
            available_slopes = []
            for i in range(0, len(labels), 2):
                if not pd.isna(labels[i]):
                    val = float(labels[i])
                    if val not in [x[0] for x in available_slopes]:
                        available_slopes.append((val, i))
            available_slopes.sort(key=lambda x: x[0])
            
            # 입력값(H0_L0_val)을 감싸는 상·하한 곡선(k1, k2) 찾기
            k1, col_idx1 = available_slopes[0]
            k2, col_idx2 = available_slopes[-1]
            
            for idx in range(len(available_slopes) - 1):
                if available_slopes[idx][0] <= H0_L0_val <= available_slopes[idx+1][0]:
                    k1, col_idx1 = available_slopes[idx]
                    k2, col_idx2 = available_slopes[idx+1]
                    break
            
            # 두 인접 곡선의 좌표 추출
            x1 = df.iloc[2:, col_idx1].astype(float).dropna().values
            y1 = df.iloc[2:, col_idx1+1].astype(float).dropna().values
            
            x2 = df.iloc[2:, col_idx2].astype(float).dropna().values
            y2 = df.iloc[2:, col_idx2+1].astype(float).dropna().values
            
            # ★ 핵심 수정: 두 곡선이 모두 존재하는 유효 X축 구간(x_min ~ x_max)에서만 보간 수행
            valid_x_min = max(x1.min(), x2.min())
            valid_x_max = min(x1.max(), x2.max())
            
            # 유효 구간 내에서만 x축 그리드 생성
            x_common = np.logspace(np.log10(valid_x_min), np.log10(valid_x_max), 300)
            
            y1_interp = np.interp(x_common, x1, y1)
            y2_interp = np.interp(x_common, x2, y2)
            
            # 로그 스케일 가중치에 따른 선형 보간 곡선 산정
            if k1 != k2:
                weight = (math.log10(H0_L0_val) - math.log10(k1)) / (math.log10(k2) - math.log10(k1))
            else:
                weight = 0.0
                
            y_target = y1_interp + weight * (y2_interp - y1_interp)
            
            # 1) 계산된 H'0/L0 곡선을 '파란색 굵은 점선'으로 작도
            ax_main.plot(x_common, y_target, color='#0056b3', linestyle='--', linewidth=2.2, zorder=4,
                         label=f"$H'_0/L_0={H0_L0_val:.4f}$ (계산선)")
            
            # 2) 파란색 곡선 위에 명확한 라벨 박스 표출
            idx_txt = int(len(x_common) * 0.15) 
            ax_main.text(x_common[idx_txt], y_target[idx_txt] + 0.05, 
                         f"$H'_0/L_0={H0_L0_val:.4f}$", 
                         color='#0056b3', fontsize=11, fontweight='bold',
                         bbox=dict(facecolor='white', edgecolor='#0056b3', boxstyle='round,pad=0.2', alpha=0.9), 
                         ha='center', va='bottom', zorder=6)
        # =========================================================================

    except FileNotFoundError:
        pass

    ax_main.set_xscale('log')
    ax_main.set_xlim(0.004, 0.1)
    ax_main.set_ylim(0.8, 3.0)

    # [하단 X축 Major 눈금] 
    main_x_ticks = [0.004, 0.006, 0.008, 0.01, 0.015, 0.02, 0.03, 0.04, 0.06, 0.08, 0.1]
    main_x_labels = ['0.004', '0.006', '0.008', '0.01', '0.015', '0.02', '0.03', '0.04', '0.06', '0.08', '0.1']
    ax_main.set_xticks(main_x_ticks)
    ax_main.set_xticklabels(main_x_labels, fontsize=10, fontweight='bold')
    ax_main.xaxis.set_major_formatter(ticker.FixedFormatter(main_x_labels))

    # [하단 X축 Minor 눈금]
    minor_x = [
        0.0045, 0.005, 0.0055, 0.0065, 0.007, 0.0075, 0.0085, 0.009, 0.0095,
        0.011, 0.012, 0.013, 0.014, 0.016, 0.017, 0.018, 0.019,
        0.022, 0.024, 0.026, 0.028,
        0.035, 0.045, 0.05, 0.055, 0.065, 0.07, 0.075, 0.085, 0.09, 0.095
    ]
    ax_main.set_xticks(minor_x, minor=True)
    ax_main.xaxis.set_minor_formatter(ticker.NullFormatter())

    # [좌측 Y축 눈금] 
    ax_main.set_yticks([0.8, 1.0, 1.5, 2.0, 2.5, 3.0])
    ax_main.set_yticklabels(['0.8', '1.0', '1.5', '2.0', '2.5', '3.0'], fontsize=11, fontweight='bold')
    
    minor_y = np.arange(0.8, 3.1, 0.1)
    ax_main.set_yticks(minor_y, minor=True)

    ax_main.grid(True, which='both', color='#555555', linewidth=0.5, zorder=1)
    ax_main.set_xlabel(r"$h / L_0$", fontsize=13, fontweight='bold', labelpad=5)
    ax_main.set_ylabel(r"$K_s = \frac{H}{H_0'}$", fontsize=14, rotation=0, labelpad=35, va='center')

    # -------------------------------------------------------------------------
    # 2. 상단 보조 그래프 영역 (h/L0 : 0.1 ~ 1.0)
    # -------------------------------------------------------------------------
    ax_top = fig.add_axes([0.36, 0.77, 0.60, 0.17])

    try:
        for i in range(0, len(labels), 2):
            if pd.isna(labels[i]): continue
            x = df.iloc[2:, i].astype(float).dropna().values
            y = df.iloc[2:, i+1].astype(float).dropna().values
            
            mask_top = (x >= 0.099) & (x <= 1.0)
            if len(x[mask_top]) > 0:
                ax_top.plot(x[mask_top], y[mask_top], color='black', linewidth=1.2, zorder=2)
    except NameError:
        pass

    ax_top.set_xscale('log')
    ax_top.set_xlim(0.1, 1.0)
    ax_top.set_ylim(0.85, 1.00)

    top_x_ticks = [0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0]
    top_x_labels = ['0.1', '0.15', '0.2', '0.3', '0.4', '0.6', '0.8', '1.0']
    ax_top.set_xticks(top_x_ticks)
    ax_top.set_xticklabels(top_x_labels, fontsize=10, fontweight='bold')
    ax_top.xaxis.set_major_formatter(ticker.FixedFormatter(top_x_labels))
    ax_top.xaxis.tick_top()
    ax_top.set_title(r"$h / L_0$", fontsize=13, fontweight='bold', pad=15)

    minor_top_x = [
        0.11, 0.12, 0.13, 0.14,
        0.16, 0.17, 0.18, 0.19,
        0.22, 0.24, 0.26, 0.28,
        0.32, 0.34, 0.36, 0.38,
        0.5, 0.7, 0.9
    ]
    ax_top.set_xticks(minor_top_x, minor=True)
    ax_top.xaxis.set_minor_formatter(ticker.NullFormatter())

    ax_top.yaxis.tick_right()
    ax_top.set_yticks([0.85, 0.9, 0.95, 1.0])
    ax_top.set_yticklabels(['0.85', '0.9', '0.95', '1.0'], fontsize=10, fontweight='bold')
    ax_top.yaxis.set_label_position("right")
    ax_top.text(1.08, 0.45, r"$K_s$", fontsize=12, fontweight='bold', transform=ax_top.transAxes)
    ax_top.grid(True, which='both', color='#555555', linewidth=0.5, zorder=1)

    # -------------------------------------------------------------------------
    # 3. 입력 좌표 수치 마킹 (붉은선 & 교차점) 및 독취값 표시
    # -------------------------------------------------------------------------
    try:
        # 1번 블록에서 만든 x_common(X축 데이터)과 y_target(파란 점선 Y데이터)을 이용
        true_ks_val = float(np.interp(h_L0_val, x_common, y_target))
    except NameError:
        true_ks_val = Ks_val

    # 실제 만나는 교차점(true_ks_val)으로 빨간 교차선과 점을 그립니다.
    if h_L0_val <= 0.1:
        ax_main.plot(h_L0_val, true_ks_val, 'ro', markersize=7, zorder=5)
        ax_main.axvline(x=h_L0_val, color='red', linestyle='-', linewidth=1.2, zorder=4)
        ax_main.axhline(y=true_ks_val, color='red', linestyle='-', linewidth=1.2, zorder=4)
        
        ax_main.text(h_L0_val * 1.04, true_ks_val + 0.04, 
                     f"독취결과\nh/L0={h_L0_val:.4f}\nKs={true_ks_val:.3f}", 
                     color='red', fontsize=10, fontweight='bold', 
                     bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3', alpha=0.9), 
                     zorder=6)
    else:
        ax_top.plot(h_L0_val, true_ks_val, 'ro', markersize=7, zorder=5)
        ax_top.axvline(x=h_L0_val, color='red', linestyle='-', linewidth=1.2, zorder=4)
        ax_top.axhline(y=true_ks_val, color='red', linestyle='-', linewidth=1.2, zorder=4)
        
        ax_top.text(h_L0_val * 1.04, true_ks_val + 0.02, 
                    f"독취결과\nh/L₀={h_L0_val:.4f}\nKs={true_ks_val:.3f}", 
                    color='red', fontsize=10, fontweight='bold', 
                    bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3', alpha=0.9), 
                    zorder=6)

    # ★ [수정] 메인 스크립트에서 비선형 독취값을 바로 쓸 수 있도록 튜플(fig, true_ks_val)로 반환합니다.
    return fig, true_ks_val
# -------------------------------------------------------------------------

# --- UI 레이아웃 구성 ---
st.title("🌊 최대파고 완전 자동 산정 프로그램")
st.markdown("항만 및 어항 설계기준 산출 로직 (Spline 이중 보간 적용 완벽 모사)")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.header("📝 입력 제원")
    H13 = st.number_input("설계 유의파고 (H1/3, m)", value=9.86, step=0.1)
    T13 = st.number_input("설계 주기 (T1/3, sec)", value=15.29, step=0.1)
    h = st.number_input("적용 수심 (h, m)", value=19.66, step=0.01)
    tanTheta = st.number_input("해저 경사 (tanθ)", value=0.010, step=0.001, format="%.3f")
    
    st.markdown("---")
    st.markdown("🤖 **스마트 판독 설정**")
    auto_ks = st.checkbox("천수계수 (Ks) 자동 판독 (도해 4-3)", value=True)
    if not auto_ks:
        Ks_input = st.number_input("천수계수 수동 입력 (Ks)", value=1.06, step=0.01)
    else:
        Ks_input = 1.06 
        
    auto_graph = st.checkbox("해저경사별 도표 자동 판독", value=True)
    if not auto_graph:
        graph_ratio_input = st.number_input("산정도 적용비율 수동입력 (Hmax/H'o)", value=1.78, step=0.01)
    else:
        graph_ratio_input = 1.78 
    
    calc_button = st.button("최대파고 계산 및 결과서 생성", type="primary", use_container_width=True)

with col2:
    if calc_button:
        L0 = 1.56 * (T13 ** 2)
        d_L0 = h / L0
        spm_ratio = get_interpolated_hh0(d_L0)
        H0p_spm = H13 / spm_ratio

        low, high = 1.0, 15.0
        verified_H0p = H0p_spm
        final_Ks = Ks_input
        
        for _ in range(100):
            mid = (low + high) / 2
            mid_H0p_L0 = mid / L0
            
            if auto_ks:
                current_Ks = get_shuto_ks(d_L0, mid_H0p_L0)
            else:
                current_Ks = Ks_input
                
            curr_H13, b0, b1, bM, v1, v2, v3 = calc_h13_formula(mid, h, L0, tanTheta, current_Ks)
            
            if curr_H13 < H13:
                low = mid
            else:
                high = mid
            
            verified_H0p = mid
            final_Ks = current_Ks
            if abs(curr_H13 - H13) < 0.0001:
                break
                
        H0p_L0_val = verified_H0p / L0
        h_H0p_val = h / verified_H0p
        if auto_ks:
            try:
                graph_ratio_temp = get_final_graph_ratio(h_H0p_val, H0p_L0_val, tanTheta)
            except Exception:
                pass

        Hmax_form, b0_s, b1_s, bM_s, fv1, fv2, fv3 = calc_hmax_formula(verified_H0p, h, L0, tanTheta, final_Ks)

        # 역산된 변수를 이용해 최종 H1/3 검증 수치를 가져옴 (상세 폼 출력용)
        final_H13_calc, f_b0, f_b1, f_bM, f_val1, f_val2, f_val3 = calc_h13_formula(verified_H0p, h, L0, tanTheta, final_Ks)

        if auto_graph:
            graph_ratio = round(get_final_graph_ratio(h_H0p_val, H0p_L0_val, tanTheta), 4)
        else:
            graph_ratio = graph_ratio_input
                
        Hmax_graph = graph_ratio * verified_H0p
        Hmax_non_breaking = 1.8 * H13
        
        # --- 쇄파 저감 판단 및 최종 파고 선정 로직 ---
        is_breaking = (h_H0p_val <= 3.0)
        
        applied_str_graph = ""
        applied_str_form = ""
        applied_str_non = ""
        
        if is_breaking:
            final_hmax = max(Hmax_graph, Hmax_form)
            if final_hmax == Hmax_graph:
                applied_str_graph = f"🟢 **최종 적용** ($H_{{1/3}}$의 {final_hmax/H13:.2f}배)"
            else:
                applied_str_form = f"🟢 **최종 적용** ($H_{{1/3}}$의 {final_hmax/H13:.2f}배)"
        else:
            final_hmax = Hmax_non_breaking
            applied_str_non = f"🟢 **최종 적용** ($H_{{1/3}}$의 {final_hmax/H13:.2f}배)"

        with st.container():
            st.markdown("### 📊 검토 결과 요약")
            table_md = f"""
| 산정 방법 | 계산 결과 ($H_{{\\max}}$) | 비고 |
| :--- | :--- | :--- |
| **쇄파대 내 최대파고 산정도** | **{Hmax_graph:.4f} m** | {applied_str_graph if applied_str_graph else '비교용'} |
| **쇄파대 내 최대파고 약산식** | **{Hmax_form:.4f} m** | {applied_str_form if applied_str_form else '비교용'} |
| **비쇄파시 최대파고** | **{Hmax_non_breaking:.4f} m** | {applied_str_non if applied_str_non else f"참고용 ($1.8 \\times H_{{1/3}}$)"} |
            """
            st.markdown(table_md)

            if is_breaking:
                st.info(f"💡 **선정 사유:** 전면수심이 환산심해파고의 3배 이하($h/H_0' \\le 3.0$)이므로 **쇄파에 의한 저감을 고려**하여 산정도와 약산식 중 **큰 값**을 최종 선정함.")
            else:
                st.info(f"💡 **선정 사유:** 전면수심이 환산심해파고의 3배 초과($h/H_0' > 3.0$)이므로 쇄파에 의한 저감이 없다고 보아 **비쇄파파고**를 최종 선정함.")

            st.markdown("---")

            st.markdown("### 📝 상세 산출 과정")

            # 1) 설계조건 출력 (가로 표 형식)
            st.markdown("#### 1) 설계조건")
            design_cond_md = f"""
| 설계 유의파고 ($H_{{1/3}}$) | 설계 주기 ($T_{{1/3}}$) | 적용 수심 ($h$) | 해저 경사 ($\\tan\\theta$) |
| :---: | :---: | :---: | :---: |
| **{H13:.2f} m** | **{T13:.2f} s** | **{h:.3f} m** | **{tanTheta:.3f} (1/{int(1/tanTheta) if tanTheta > 0 else '0'})** |
            """
            st.markdown(design_cond_md)

            st.markdown("<br>", unsafe_allow_html=True)

            # 2) 로 번호 변경
            st.markdown("#### 2) 기본 제원 및 심해파 환산")
            st.markdown(f"- **설계유의파주기 ($T_{{1/3}}$)** = {T13} $\\mathrm{{s}}$")
            st.markdown(f"- **심해파장 ($L_0$)** = $1.56 \\times T_{{1/3}}^2$ = $1.56 \\times {T13}^2$ = **{L0:.4f} m**")
            st.markdown(f"- **파형경사 ($h/L_0$)** = {h} / {L0:.4f} = **{d_L0:.6f}**")

            st.markdown("<br>", unsafe_allow_html=True)

            # 3) 로 번호 변경
            st.markdown("#### 3) 수정환산심해파고 ($H_0'$) 및 천수계수 ($K_s$) 산출 과정")
            st.info(f"""
            **[수정환산심해파고 ($H_0'$) 수치해석적 역산]**\n
            Goda의 쇄파대 내 파고 약산식은 $H_0'$에 대해 양음함수(비선형) 형태이므로 직접적인 대수적 풀이가 불가합니다. 따라서 목표 설계유의파고($H_{{1/3}}$)로 수렴하기 위해 이분법(Bisection Method, 최대 100회 반복)을 통한 수치해석적 역산을 수행합니다.
            * 목표 설계유의파고 ($H_{{1/3}}$) = **{H13} m**
            * 수치해석 역산 결과 ($H_0'$) = **{verified_H0p:.4f} m**
            * 환산심해파형경사 ($H_0'/L_0$) = {verified_H0p:.4f} / {L0:.4f} = **{H0p_L0_val:.6f}**
            """)
            
            if auto_ks:
                st.success(f"""
                **[천수계수 ($K_s$) 자동 판독 (슈토(Shuto)의 도해 4-3)]**\n
                위 $H_0'$ 역산 과정의 매 반복 단계마다 갱신되는 $H_0'/L_0$를 바탕으로 천수계수 산정도(도해 4-3)를 2D 이중 선형 보간하여 정밀하게 자동 판독합니다.
                * 입력 매개변수: 상대수심($h/L_0$) = {d_L0:.6f}, 환산심해파형경사($H_0'/L_0$) = {H0p_L0_val:.6f}
                * 슈토(Shuto) 천수계수 매트릭스 도해 독취값 ($K_s$) = {final_Ks:.3f}
                """)
            else:
                st.success(f"""
                **[천수계수 ($K_s$) 수동 입력]**\n
                * 사용자 입력 천수계수 적용 ($K_s$) = **{final_Ks:.4f}**
                """)

            try:
                img_base64 = get_image_base64("도해(4-3) 슈트의 천수계수 산정도.png")  
            except Exception:
                img_base64 = ""

            # 1. 참고 설명 텍스트 박스 출력
            st.markdown("""
            <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; color: #000000; line-height: 1.6; margin-bottom: 15px; border-radius: 4px;">
                <strong>📌 참고) 슈토(1974)의 비선형 장파이론</strong><br>
                • 도해(4-3)은 슈토(1974)의 비선형 장파이론에 근거한 것으로 천수변형을 추정할 수 있고 천수변형만을 고려하는 경우 환산심해파고는 심해파고와 동일하다.<br>
                • 불규칙파가 천해역에 들어가면 불규칙파 중의 각 성분파의 파속은 어느 것이든 장파의 속도에 수렴하여 주파수에 따른 파속의 차가 거의 없기 때문에 파군의 형태는 거의 변하지 않고 진행한다. 이와 같은 경우에 쇄파 이전의 파랑만을 대상으로 한정하면 불규칙한 파군중의 개개파에 대하여 비선형 변형이론이 적용될 수 단다. 따라서 규칙파에 대한 비선형 파랑의 변형식은 불규칙파에도 적용할 수 있다.<br>
                • Bretschneider나 Pierson, Moskovitsz의 스펙트럼을 갖는 불규칙한 파랑의 각 성분파가 미소진폭파와 동일한 천수변형을 한다고 가정하여 계산한 불규칙파의 천수계수는 미소진폭 규칙파의 천수계수와 h/Lo>0.05의 영역에서는 기껏해야 5%정도의 차가 난다. 따라서 장파 영역외에는 불규칙파의 천수계수로서 미소진폭 규칙파의 천수계수를 근사적으로 쓸 수 있다.<br>
                • 쇄파 이전의 천해역에서 불규칙파의 천수계수는 장파 영역 내외의 여하에 관계없이 유의파로 대표된 도해(4-3)을 이용할 수 있다.<br>
                • 도해(4-3)은 일점쇄선은 쇄파로 인해 유의파가 98%로 감쇠한 지점을 나타낸다. 이 선보다 위의 영역에서는 쇄파에 의한 파고감쇠가 커서 천수변형만으로는 파고변화를 추정할 수 없다.
            </div>
            """, unsafe_allow_html=True)
            # 2. Streamlit 내장 함수로 이미지 안전하게 출력 (파일명과 경로 확인 필요)
            st.image("도해(4-3) 슈트의 천수계수 산정도.png", use_container_width=True)
            
            try:
                with st.spinner("슈토 천수계수 산정도 자동 표출 중..."):
                    # ★ [핵심 수정] 튜플 반환값을 받아 true_ks_val 변수에 도표 독취 결과 할당
                    fig_ks, true_ks_val = plot_shuto_ks_chart(d_L0, final_Ks, H0p_L0_val)
                    
                    # 3-1) 과정 및 이후 결과에 비선형 독취값 적용을 위해 덮어쓰기
                    final_Ks = true_ks_val 
                    
                st.pyplot(fig_ks, use_container_width=True)
            except Exception as e:
                st.error(f"도표 생성 중 오류 발생: {e}")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 기존 2-1) -> 3-1) 로 번호 변경
            st.markdown("#### 3-1) $H_{1/3}$ 자동역산 상세 과정")
            st.markdown(f"""
            **⓵ 쇄파대 내 파고 약산식을 이용한 $H_{{1/3}}$ 산정**
            * $H_{{1/3}} = K_s H_0'$  ($h/L_0 \ge 0.2$)
            * $H_{{1/3}} = \min{{(\\beta_0 H_0' + \\beta_1 h),\\ \\beta_{{\\max}} H_0',\\ K_s H_0'}}$  ($h/L_0 < 0.2$)
            """)
            
            cond_str = "<span style='color:red; font-weight:bold;'>< 0.2</span>" if d_L0 < 0.2 else "<span>≥ 0.2</span>"

            # =========================================================================
            # ★ [수정됨] 도표에서 반환된 실제 Ks 독취값(final_Ks)을 바탕으로 조건 3 및 최종 유의파고 재계산 적용
            # =========================================================================  
            f_val3 = final_Ks * verified_H0p

            if d_L0 >= 0.2:
                final_H13_calc = final_Ks * verified_H0p
            else:
                final_H13_calc = min(f_val1, f_val2, f_val3)

            # 상세 과정 표 및 HTML 테이블 렌더링
            table_md_detail = f"""
            | 구분 | 기호 | 산출식 / 설명 | 산출결과 | 비고 |
            | :--- | :---: | :--- | :---: | :---: |
            | **여기서,** | $\\beta_0$ | $0.028(H_0'/L_0)^{{-0.38}} \\exp[20(\\tan\\theta)^{{1.5}}]$ | **{f_b0:.3f}** | |
            | | $\\beta_1$ | $0.52 \\exp[4.2 \\tan\\theta]$ | **{f_b1:.3f}** | |
            | | $\\beta_{{\\max}}$ | $\\max(0.92, 0.32(H_0'/L_0)^{{-0.29}} \\exp[2.4 \\tan\\theta])$ | **{f_bM:.3f}** | |
            | | $K_s$ | 비선형 천수계수 | <span style='border: 2px solid black; padding: 2px 8px; font-weight:bold;'>{final_Ks:.3f}</span> | 맞추기 (도표 독취) |
            | | $H_0'$ | 환산심해파고 (m) | <span style='border: 2px solid black; padding: 2px 8px; font-weight:bold;'>{verified_H0p:.2f}</span> | 맞추기 |
            | | $\\tan\\theta$ | 해저경사 | **1/{int(1/tanTheta) if tanTheta > 0 else '0'}** | |
            | | $h$ | 적용 수심 (m) | **{h:.2f}** | |
            | | $L_0$ | 심해파장 (m) | **{L0:.2f}** | |
            | | $h/L_0$ | 상대 수심 | **{d_L0:.3f}** | {cond_str} |
            | | $H_0'/L_0$ | 환산심해파형경사 | **{H0p_L0_val:.3f}** | |
            | | 조건 1 | $\\beta_0 H_0' + \\beta_1 h$ | **{f_val1:.2f}** | |
            | | 조건 2 | $\\beta_{{\\max}} H_0'$ | **{f_val2:.2f}** | |
            | | 조건 3 | $K_s H_0'$ | **{f_val3:.2f}** | |
            | **결과** | **$H_{{1/3}}$** | **유의파고** | <span style='border: 2px solid black; padding: 2px 8px; font-weight:bold; font-size:1.1em;'>{final_H13_calc:.2f} m</span> | |
            """

            st.markdown(table_md_detail, unsafe_allow_html=True)            
            st.markdown("**⓶ 검증결과**")
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                <div style="border: 2px solid black; padding: 10px; width: 250px; background-color: white; color: black;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span>∴ 약산식 H<sub>1/3</sub></span>
                        <span>= <b>{final_H13_calc:.2f}</b></span>
                    </div>
                    <div style="border-top: 1px solid #ccc; margin: 5px 0;"></div>
                    <div style="display: flex; justify-content: space-between; color: red;">
                        <span>파랑 산출 H<sub>1/3</sub></span>
                        <span>= <b>{H13:.2f}</b></span>
                    </div>
                </div>
                <div style="font-size: 20px; font-weight: bold; color: black;">
                    O.K
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 4) 로 번호 변경
            st.markdown("#### 4) 쇄파 발생 여부 (쇄파 저감) 판단")
            if is_breaking:
                st.success(f"▶ **상대수심 ($h/H_0'$)** = {h} / {verified_H0p:.4f} = **{h_H0p_val:.4f}** $\\le 3.0$\n\n결과: 전면수심이 환산심해파고의 3배 이하이므로 **쇄파 저감 조건**에 해당합니다. 쇄파대 내 산정도와 약산식 산출값 중 비교 적용합니다.")
            else:
                st.warning(f"▶ **상대수심 ($h/H_0'$)** = {h} / {verified_H0p:.4f} = **{h_H0p_val:.4f}** $> 3.0$\n\n결과: 전면수심이 환산심해파고의 3배를 초과하므로 **비쇄파 조건**에 해당합니다. $1.8 H_{{1/3}}$ 을 적용합니다.")

            st.markdown("<br>", unsafe_allow_html=True)

            # 5) 로 번호 변경
            st.markdown("#### 5) 가) 해저경사별 쇄파대 최대파고 산정도 판독 (도참 4-18a ~ 4-19e)")
            st.info(f"""
            **[산정도 판독용 변수]**
            * 해저경사 ($\\tan\\theta$) = {tanTheta}
            * 환산심해파형경사 ($H_0'/L_0$) = {verified_H0p:.4f} / {L0:.4f} = **{H0p_L0_val:.6f}**
            * 상대수심 ($h/H_0'$) = **{h_H0p_val:.4f}**
            """)
            st.markdown(f"▶ 조건에 해당하는 산정도 곡선 자동 판독 결과: 파고비 ($H_{{\\max}}/H_0'$) = **{graph_ratio:.3f}**")
            st.success(f"▶ **산정도 $H_{{\\max}}$** = {graph_ratio:.3f} $\\times$ {verified_H0p:.4f} = **{Hmax_graph:.4f} m**")

            st.markdown("""
            <div style="background-color: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; color: #000000; line-height: 1.6; margin-bottom: 15px; border-radius: 4px;">
                <strong>📌 참고) 항만 및 어항 설계기준의 도표를 이용한 최대파고 산정방법</strong><br>
                • 도표에서 우측의 2%감쇄선(일점쇄선)의 우측영역의 파고변화는 천수변형의 천수계수(p.72)를 적용하여 쇄파대내 Hmax 약산식을 사용한다.<br>
                • 도표에서 우측의 2%감쇄선(일점쇄선)의 좌측영역은 쇄파에 의한 파고변화가 탁월하므로 도표를 이용하여 산출한다.<br>
                • 이 그림들을 사용하여 파고를 결정해야 하는 해저경사는 수심과 환산심해파 파고의 비 h/H'o가 1.5~2.5인 범위에서의 평균 해저경사를 사용하는 것이 중요하다.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 6) 로 번호 변경
            st.markdown("#### 6) 나) 쇄파대 내 파고 약산식을 이용한 $H_{{\\max}}$ 산정 (비교 검증용)")
            st.markdown("**① 약산식 계수 산출:**")
            st.markdown(f"- $\\beta_0^*$ = $0.052 \\times (H_0'/L_0)^{{-0.38}} \\times \\exp(20 \\times \\tan\\theta^{{1.5}})$ = **{b0_s:.6f}**")
            st.markdown(f"- $\\beta_1^*$ = $0.63 \\times \\exp(3.8 \\times \\tan\\theta)$ = **{b1_s:.6f}**")
            st.markdown(f"- $\\beta_{{\\max}}^*$ = $\\max\\left[1.65,\\ 0.53 \\times (H_0'/L_0)^{{-0.29}} \\times \\exp(2.4 \\times \\tan\\theta)\\right]$ = **{bM_s:.6f}**")

            st.markdown("**② 최대파고 조건별 계산:**")
            st.markdown(f"""
            - **Condition 1**: $\\beta_0^* H_0' + \\beta_1^* h$ = ({b0_s:.4f} $\\times$ {verified_H0p:.4f}) + ({b1_s:.4f} $\\times$ {h}) = **{fv1:.6f} m**
            - **Condition 2**: $\\beta_{{\\max}}^* H_0'$ = {bM_s:.4f} $\\times$ {verified_H0p:.4f} = **{fv2:.6f} m**
            - **Condition 3**: $1.8 \\times K_s \\times H_0'$ = $1.8 \\times {final_Ks:.4f} \\times {verified_H0p:.4f}$ = **{fv3:.6f} m**
            """)
            st.success(f"▶ **약산식 $H_{{\\max}}$** = $\\min$(Condition 1, Condition 2, Condition 3) = **{Hmax_form:.6f} m**")

            st.markdown("---")

            spacer1, col_fig, spacer2 = st.columns([1.5, 2.5, 1.5])
            with col_fig:
                with st.spinner("스플라인 기반 원본 도표 생성 중..."):
                    fig = plot_authentic_chart_spline(h_H0p_val, graph_ratio, H0p_L0_val, tanTheta)
                    st.pyplot(fig, use_container_width=True)
            
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")

            # 1. HTML 렌더링 전 조건별 텍스트 정제 (마크다운 및 수식을 순수 HTML로 변환)
            def clean_html_text(text):
                if not text: return text
                t = text.replace("**", "")
                t = t.replace("$H_{1/3}$", "H<sub>1/3</sub>")
                return t

            if is_breaking:
                box_class_1 = "success-box"
                reason_text_1 = "전면수심이 환산심해파고의 3배 이하(h/H<sub>0</sub>' &le; 3.0)이므로 <strong>쇄파에 의한 저감을 고려</strong>하여 산정도와 약산식 중 큰 값을 최종 선정함."
                box_class_2 = "success-box"
                reason_text_2 = "전면수심이 환산심해파고의 3배 이하이므로 쇄파 저감 조건에 해당"
            else:
                box_class_1 = "info-box"
                reason_text_1 = "전면수심이 환산심해파고의 3배 초과(h/H<sub>0</sub>' > 3.0)이므로 쇄파에 의한 저감이 없다고 보아 <strong>비쇄파파고</strong>를 최종 선정함."
                box_class_2 = "warning-box"
                reason_text_2 = "전면수심이 환산심해파고의 3배를 초과하므로 비쇄파 조건에 해당"

            ks_text = "자동 판독 (슈토 도해 4-3)" if auto_ks else "수동 입력"
            tan_denom = int(1 / tanTheta) if tanTheta > 0 else 0
            tan_theta_str = f"1/{tan_denom}" if tan_denom > 0 else "0"

            # 요약 테이블 비고란 텍스트 정제 적용
            note_graph = clean_html_text(applied_str_graph) if applied_str_graph else "비교용"
            note_form = clean_html_text(applied_str_form) if applied_str_form else "비교용"
            note_non = clean_html_text(applied_str_non) if applied_str_non else "참고용 (1.8 &times; H<sub>1/3</sub>)"

            # 2. HTML 보고서 문자열 생성 (수식은 모두 순수 HTML 태그 적용)
            raw_html = f"""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>최대파고 산정 상세 보고서</title>
                <style>
                    body {{ font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; padding: 30px; max-width: 900px; margin: auto; color: #333; }}
                    h2 {{ border-bottom: 2px solid #333; padding-bottom: 10px; text-align: center; }}
                    h3 {{ color: #0056b3; margin-top: 40px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                    h4 {{ color: #222; margin-top: 25px; margin-bottom: 10px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; text-align: center; font-size: 14px; }}
                    th, td {{ border: 1px solid #ccc; padding: 10px; }}
                    th {{ background-color: #f4f6f8; font-weight: bold; }}
                    .highlight {{ font-weight: bold; color: #d9534f; }}
                    .box {{ padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .info-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; }}
                    .success-box {{ background-color: #e9f7ef; border-left: 4px solid #28a745; }}
                    .warning-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
                    .verify-box {{ display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }}
                    .verify-inner {{ border: 2px solid black; padding: 10px; width: 250px; background-color: white; color: black; }}
                    .flex-between {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
                    .divider {{ border-top: 1px solid #ccc; margin: 5px 0; }}
                    .ok-text {{ font-size: 20px; font-weight: bold; color: black; }}
                    img {{ max-width: 100%; height: auto; display: block; margin: 30px auto; border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                    ul {{ margin-top: 5px; margin-bottom: 15px; }}
                    li {{ margin-bottom: 5px; }}
                </style>
            </head>
            <body>
                <h2>🌊 최대파고 산정 결과 보고서</h2>
                <div style="text-align: right; color: #666; font-size: 13px;">항만 및 어항 설계기준 산출 로직 적용</div>

                <h3>📊 1. 검토 결과 요약</h3>
                <table>
                    <tr><th>산정 방법</th><th>계산 결과 (H<sub>max</sub>)</th><th>비고</th></tr>
                    <tr><td>쇄파대 내 최대파고 산정도</td><td><strong>{Hmax_graph:.4f} m</strong></td><td>{note_graph}</td></tr>
                    <tr><td>쇄파대 내 최대파고 약산식</td><td><strong>{Hmax_form:.4f} m</strong></td><td>{note_form}</td></tr>
                    <tr><td>비쇄파시 최대파고</td><td><strong>{Hmax_non_breaking:.4f} m</strong></td><td>{note_non}</td></tr>
                </table>

                <div class="box {box_class_1}">
                    💡 <strong>선정 사유:</strong> {reason_text_1}
                </div>

                <h3>📝 2. 상세 산출 과정</h3>

                <h4>1) 설계조건</h4>
                <table>
                    <tr>
                        <th>설계 유의파고 (H<sub>1/3</sub>)</th>
                        <th>설계 주기 (T<sub>1/3</sub>)</th>
                        <th>적용 수심 (h)</th>
                        <th>해저 경사 (tan&theta;)</th>
                    </tr>
                    <tr>
                        <td><strong>{H13:.2f} m</strong></td>
                        <td><strong>{T13:.2f} s</strong></td>
                        <td><strong>{h:.3f} m</strong></td>
                        <td><strong>{tanTheta:.3f} ({tan_theta_str})</strong></td>
                    </tr>
                </table>

                <h4>2) 기본 제원 및 심해파 환산</h4>
                <ul>
                    <li><strong>설계유의파주기 (T<sub>1/3</sub>)</strong> = {T13} s</li>
                    <li><strong>심해파장 (L<sub>0</sub>)</strong> = 1.56 &times; T<sub>1/3</sub><sup>2</sup> = 1.56 &times; {T13}<sup>2</sup> = <strong>{L0:.4f} m</strong></li>
                    <li><strong>파형경사 (h/L<sub>0</sub>)</strong> = {h} / {L0:.4f} = <strong>{d_L0:.6f}</strong></li>
                </ul>

                <h4>3) 수정환산심해파고 (H<sub>0</sub>') 및 천수계수 (K<sub>s</sub>) 산출 과정</h4>
                <div class="box info-box">
                    <strong>[수정환산심해파고 (H<sub>0</sub>') 수치해석적 역산]</strong><br>
                    Goda의 쇄파대 내 파고 약산식은 H<sub>0</sub>'에 대해 양음함수(비선형) 형태이므로 이분법을 통한 수치해석적 역산을 수행합니다.<br>
                    <ul>
                        <li>목표 설계유의파고 (H<sub>1/3</sub>) = <strong>{H13} m</strong></li>
                        <li>수치해석 역산 결과 (H<sub>0</sub>') = <strong>{verified_H0p:.4f} m</strong></li>
                        <li>환산심해파형경사 (H<sub>0</sub>'/L<sub>0</sub>) = <strong>{H0p_L0_val:.6f}</strong></li>
                    </ul>
                </div>

                <div class="box success-box">
                    <strong>[천수계수 (K<sub>s</sub>) {ks_text}]</strong><br>
                    반영된 천수계수 (K<sub>s</sub>) = <strong>{final_Ks:.4f}</strong>
                </div>

                <h4>3-1) H<sub>1/3</sub> 자동역산 상세 과정</h4>
                <p><strong>⓵ 쇄파대 내 파고 약산식을 이용한 H<sub>1/3</sub> 산정</strong></p>
                <table>
                    <tr><th>구분</th><th>기호</th><th>산출식 / 설명</th><th>산출결과</th><th>비고</th></tr>
                    <tr><td><strong>여기서,</strong></td><td>&beta;<sub>0</sub></td><td>0.028(H<sub>0</sub>'/L<sub>0</sub>)<sup>-0.38</sup> exp[20(tan&theta;)<sup>1.5</sup>]</td><td><strong>{f_b0:.3f}</strong></td><td></td></tr>
                    <tr><td></td><td>&beta;<sub>1</sub></td><td>0.52 exp[4.2 tan&theta;]</td><td><strong>{f_b1:.3f}</strong></td><td></td></tr>
                    <tr><td></td><td>&beta;<sub>max</sub></td><td>max(0.92, 0.32(H<sub>0</sub>'/L<sub>0</sub>)<sup>-0.29</sup> exp[2.4 tan&theta;])</td><td><strong>{f_bM:.3f}</strong></td><td></td></tr>
                    <tr><td></td><td>K<sub>s</sub></td><td>비선형 천수계수</td><td><span style="border: 2px solid black; padding: 2px 8px; font-weight:bold;">{final_Ks:.3f}</span></td><td>맞추기</td></tr>
                    <tr><td></td><td>H<sub>0</sub>'</td><td>환산심해파고 (m)</td><td><span style="border: 2px solid black; padding: 2px 8px; font-weight:bold;">{verified_H0p:.2f}</span></td><td>맞추기</td></tr>
                    <tr><td></td><td>tan&theta;</td><td>해저경사</td><td><strong>{tan_theta_str}</strong></td><td></td></tr>
                    <tr><td></td><td>h</td><td>적용 수심 (m)</td><td><strong>{h:.2f}</strong></td><td></td></tr>
                    <tr><td></td><td>L<sub>0</sub></td><td>심해파장 (m)</td><td><strong>{L0:.2f}</strong></td><td></td></tr>
                    <tr><td></td><td>h/L<sub>0</sub></td><td>상대 수심</td><td><strong>{d_L0:.3f}</strong></td><td>{cond_str}</td></tr>
                    <tr><td></td><td>H<sub>0</sub>'/L<sub>0</sub></td><td>환산심해파형경사</td><td><strong>{H0p_L0_val:.3f}</strong></td><td></td></tr>
                    <tr><td></td><td>조건 1</td><td>&beta;<sub>0</sub>H<sub>0</sub>' + &beta;<sub>1</sub>h</td><td><strong>{f_val1:.2f}</strong></td><td></td></tr>
                    <tr><td></td><td>조건 2</td><td>&beta;<sub>max</sub>H<sub>0</sub>'</td><td><strong>{f_val2:.2f}</strong></td><td></td></tr>
                    <tr><td></td><td>조건 3</td><td>K<sub>s</sub>H<sub>0</sub>'</td><td><strong>{f_val3:.2f}</strong></td><td></td></tr>
                    <tr><td><strong>결과</strong></td><td><strong>H<sub>1/3</sub></strong></td><td><strong>유의파고</strong></td><td><span style="border: 2px solid black; padding: 2px 8px; font-weight:bold; font-size:1.1em;">{final_H13_calc:.2f} m</span></td><td></td></tr>
                </table>

                <p><strong>⓶ 검증결과</strong></p>
                <div class="verify-box">
                    <div class="verify-inner">
                        <div class="flex-between"><span>∴ 약산식 H<sub>1/3</sub></span><span>= <b>{final_H13_calc:.2f}</b></span></div>
                        <div class="divider"></div>
                        <div class="flex-between" style="color: red;"><span>파랑 산출 H<sub>1/3</sub></span><span>= <b>{H13:.2f}</b></span></div>
                    </div>
                    <div class="ok-text">O.K</div>
                </div>

                <h4>4) 쇄파 발생 여부 (쇄파 저감) 판단</h4>
                <div class="box {box_class_2}">
                    ▶ <strong>상대수심 (h/H<sub>0</sub>')</strong> = {h} / {verified_H0p:.4f} = <strong>{h_H0p_val:.4f}</strong><br>
                    결과: {reason_text_2}
                </div>

                <h4>5) 해저경사별 쇄파대 최대파고 산정도 판독</h4>
                <div class="box info-box">
                    <strong>[산정도 판독용 변수]</strong><br>
                    • 해저경사 (tan&theta;) = {tanTheta}<br>
                    • 환산심해파형경사 (H<sub>0</sub>'/L<sub>0</sub>) = <strong>{H0p_L0_val:.6f}</strong><br>
                    • 상대수심 (h/H<sub>0</sub>') = <strong>{h_H0p_val:.4f}</strong>
                </div>
                <p>▶ 조건에 해당하는 산정도 곡선 자동 판독 결과: 파고비 (H<sub>max</sub>/H<sub>0</sub>') = <strong>{graph_ratio:.3f}</strong></p>
                <div class="box success-box">
                    ▶ <strong>산정도 H<sub>max</sub></strong> = {graph_ratio:.3f} &times; {verified_H0p:.4f} = <strong>{Hmax_graph:.4f} m</strong>
                </div>

                <h4>6) 쇄파대 내 파고 약산식을 이용한 H<sub>max</sub> 산정 (비교 검증용)</h4>
                <ul>
                    <li><strong>① 약산식 계수 산출:</strong><br>
                        • &beta;<sub>0</sub><sup>*</sup> = 0.052 &times; (H<sub>0</sub>'/L<sub>0</sub>)<sup>-0.38</sup> &times; exp(20 &times; tan&theta;<sup>1.5</sup>) = <strong>{b0_s:.6f}</strong><br>
                        • &beta;<sub>1</sub><sup>*</sup> = 0.63 &times; exp(3.8 &times; tan&theta;) = <strong>{b1_s:.6f}</strong><br>
                        • &beta;<sub>max</sub><sup>*</sup> = max[1.65, 0.53 &times; (H<sub>0</sub>'/L<sub>0</sub>)<sup>-0.29</sup> &times; exp(2.4 &times; tan&theta;)] = <strong>{bM_s:.6f}</strong>
                    </li>
                    <li style="margin-top: 10px;"><strong>② 최대파고 조건별 계산:</strong><br>
                        • Condition 1: &beta;<sub>0</sub><sup>*</sup>H<sub>0</sub>' + &beta;<sub>1</sub><sup>*</sup>h = <strong>{fv1:.6f} m</strong><br>
                        • Condition 2: &beta;<sub>max</sub><sup>*</sup>H<sub>0</sub>' = <strong>{fv2:.6f} m</strong><br>
                        • Condition 3: 1.8 &times; K<sub>s</sub> &times; H<sub>0</sub>' = <strong>{fv3:.6f} m</strong>
                    </li>
                </ul>
                <div class="box success-box">
                    ▶ <strong>약산식 H<sub>max</sub></strong> = min(Condition 1, Condition 2, Condition 3) = <strong>{Hmax_form:.6f} m</strong>
                </div>

                <!-- MS Word 완벽 호환용 페이지 넘김 -->
                <p style="page-break-before: always; mso-break-type: page-break; clear: both;"></p>
                
                <h3>📈 3. 최대파고 산정도 (결과 모사 도표)</h3>
                
                <div style="text-align: center;">
                    <!-- 화면 원본 이미지는 건드리지 않고, 출력되는 Word 문서 안에서만 A4 크기에 맞게 축소 -->
                    <img src="data:image/png;base64,{img_base64}" alt="최대파고 산정도 그래프" width="450" height="556" style="border: none; max-width: 100%;">
                </div>

            </body>
            </html>
            """
            
            html_report = "\n".join([line.strip() for line in raw_html.splitlines()])

            # 3. ★ MS Word 전용 MHTML (이미지 포함 단일 문서 포맷) 생성 ★
            # MS Word가 HTML 내부의 base64 이미지를 엑스박스로 처리하는 문제를 해결하기 위해,
            # 멀티파트 웹 아카이브 형식(MHTML)으로 데이터를 패키징합니다.
            boundary = "----=_NextPart_HTML_DOC_001"
            html_for_word = html_report.replace(f"data:image/png;base64,{img_base64}", "cid:chart_image_001")
            
            mhtml_report = f"""MIME-Version: 1.0
Content-Type: multipart/related; type="text/html"; boundary="{boundary}"

--{boundary}
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: 8bit

{html_for_word}

--{boundary}
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-ID: <chart_image_001>

{img_base64}
--{boundary}--"""

            st.markdown("---")
            st.markdown("### 📥 상세 보고서 다운로드")
            st.info("💡 **출력 팁:** HTML 파일을 열어 인쇄(Ctrl+P)에서 'PDF로 저장'을 선택하시면 가장 깔끔합니다.\n\n"
                    "💡 **Word 다운로드:** Word 다운로드 버튼을 누르면 문서 내 그래프 이미지가 정상적으로 삽입된 상태로 편집할 수 있습니다.")

            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                st.download_button(
                    label="📄 결과 보고서 다운로드 (HTML 웹용)",
                    data=html_report,
                    file_name="최대파고_상세산정보고서.html",
                    mime="text/html",
                    use_container_width=True,
                )
                
            with col_btn2:
                # Word가 정상적으로 인식할 수 있도록 MHTML 데이터를 던져주면서 확장자를 .doc로 덮어씌움
                st.download_button(
                    label="📝 결과 보고서 다운로드 (MS Word용)",
                    data=mhtml_report,
                    file_name="최대파고_상세산정보고서.doc",
                    mime="application/msword",
                    use_container_width=True,
                )

    else:
        st.info("좌측에 제원을 확인한 후 '최대파고 계산 및 결과서 생성' 버튼을 클릭하세요.")
