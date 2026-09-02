import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import ctypes
import os
import zipfile
import io
import pandas as pd
import numpy as np
from scipy.interpolate import griddata

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

G = 9.81

# ==============================================================================
# [순서 교정] 역산 솔버 및 유틸리티 함수 상단 전면 배치 (미정의 에러 원천 차단)
# ==============================================================================
def brentq_solver(f, xa, xb, max_iter=120, tol=1e-6):
    fa, fb = f(xa), f(xb)
    if fa * fb > 0: return xa
    for _ in range(max_iter):
        c = (xa + xb) / 2
        fc = f(c)
        if abs(fc) < tol or (xb - xa) / 2 < tol: return c
        if fa * fc < 0: xb, fb = c, fc
        else: xa, fa = c, fc
    return c

def get_L0(T):
    return (G * T**2) / (2 * math.pi)

def get_gamma_theta_sloping(theta):
    if 0 <= theta <= 10: return 1.0
    elif 10 < theta <= 50: return math.cos(math.radians(theta - 10))**2
    else: return 0.8981 - 0.0062 * theta

def get_gamma_theta_vertical(theta):
    if 0 <= theta <= 45: return 1 - 0.0062 * theta
    else: return 0.72

class OvertoppingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("항만설계기준 월파량 다각도 비교 검토 도구 v6.7 (상세계산 100% 복원판)")
        self.root.geometry("1550x900")
        
        self.ui_font = ("맑은 고딕", 10)
        self.log_korean_font = ("굴림체", 10)
        
        self.inputs = {}
        self.notebook_images = {} 
        # 파이썬 파일(.py)이 있는 현재 폴더의 절대 경로를 동적으로 가져옵니다.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.master_zip_path = os.path.join(script_dir, "source_overtop.zip")
       
        # --- [통합 데이터 로딩] source_overtop.zip 내부에서 CSV 읽기 ---
        self.config_df = None
        self.ks_points = []
        self.ks_values = []
        
        if os.path.exists(self.master_zip_path):
            try:
                with zipfile.ZipFile(self.master_zip_path, 'r') as z:
                    
                    # 1. Goda 도표 픽셀 매핑 CSV 로드
                    if "graph_config.csv" in z.namelist():
                        with z.open("graph_config.csv") as f:
                            self.config_df = pd.read_csv(f)
                    
                    # 2. Shuto 천수계수 CSV 로드
                    if "k_s_all_data.csv" in z.namelist():
                        with z.open("k_s_all_data.csv") as f:
                            df_ks = pd.read_csv(f, header=None)
                            steepness_vals = df_ks.iloc[0].dropna().values
                            points, values = [], []
                            for i in range(len(steepness_vals)):
                                steepness = float(steepness_vals[i])
                                x_data = pd.to_numeric(df_ks.iloc[2:, i * 2]).dropna().values
                                y_data = pd.to_numeric(df_ks.iloc[2:, i * 2 + 1]).dropna().values
                                for x, y in zip(x_data, y_data):
                                    points.append([steepness, x])
                                    values.append(y)
                            self.ks_points = np.array(points)
                            self.ks_values = np.array(values)
                            print(f"통합 ZIP 로딩 성공: 천수계수 {len(self.ks_points)}개 확보")
                            
            except Exception as e:
                print(f"통합 ZIP 로딩 실패: {e}")
        else:
            print(f"※ 경고: 같은 폴더에 {self.master_zip_path} 파일이 없습니다!")
        
        self.chk_kds = tk.BooleanVar(value=True)
        self.chk_cem = tk.BooleanVar(value=True)
        self.chk_euro = tk.BooleanVar(value=True)
        self.chk_goda = tk.BooleanVar(value=True)
        
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.configure(".", font=self.ui_font)
        style.configure("TLabel", font=self.ui_font)
        style.configure("TButton", font=self.ui_font)
        style.configure("TEntry", font=self.ui_font)
        
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=15, pady=15)

        # 너비를 500픽셀로 강제 지정 (원하는 숫자로 변경 가능)
        left_container = ttk.Frame(main_paned, width=700)
        # 내부에 들어가는 요소들(글자길이 등) 때문에 프레임 크기가 변하는 것을 방지(차단)
        left_container.pack_propagate(False) 
        # 오른쪽 창에만 weight=1을 주어 남는 여백을 오른쪽 창이 모두 가져가도록 설정
        main_paned.add(left_container, weight=0)

        # 1. 계산 모드 및 검토 기준 선택
        top_frame = ttk.LabelFrame(left_container, text=" [STEP 1] 계산 모드 및 검토 기준 선택 ")
        top_frame.pack(fill="x", pady=5)
        
        mode_sub = ttk.Frame(top_frame)
        mode_sub.pack(fill="x", padx=10, pady=2)
        self.mode_var = tk.StringVar(value="q")
        ttk.Radiobutton(mode_sub, text="월파량(q) 산정", variable=self.mode_var, value="q", command=self.toggle_mode).pack(side="left", padx=10)
        ttk.Radiobutton(mode_sub, text="소요 여유고(Rc) 산정", variable=self.mode_var, value="Rc", command=self.toggle_mode).pack(side="left", padx=10)
        
        ttk.Separator(top_frame, orient="horizontal").pack(fill="x", pady=5, padx=10)
        
        self.chk_sub = ttk.Frame(top_frame)
        self.chk_sub.pack(fill="x", padx=10, pady=4)
        ttk.Label(self.chk_sub, text="검토항목(중복가능):").pack(side="left", padx=5)
        ttk.Checkbutton(self.chk_sub, text="국내 연구(KDS)", variable=self.chk_kds).pack(side="left", padx=10)
        ttk.Checkbutton(self.chk_sub, text="USACE CEM (2006)", variable=self.chk_cem).pack(side="left", padx=10)
        ttk.Checkbutton(self.chk_sub, text="EurOtop (2018)", variable=self.chk_euro).pack(side="left", padx=10)
        ttk.Checkbutton(self.chk_sub, text="Goda (일본)", variable=self.chk_goda).pack(side="left", padx=10)

        # 2. 기본 제원 (DL 기준) - 고다 해저경사 3행 2열 배치 고정
        common_frame = ttk.LabelFrame(left_container, text=" [STEP 2] 기본 제원 (DL 기준) ")
        common_frame.pack(fill="x", pady=5)
        
        fields = [
            ("유의파고 H1/3 (m)", "H13", 0, 0, "2.50"),
            ("유의주기 T1/3 (s)", "T13", 0, 2, "7.50"),
            ("파랑 입사각 θ (deg)", "theta", 1, 0, "0.00"),
            ("검토 조위 (DL.m)", "DL_water", 1, 2, "1.00"),
            ("원지반고 (DL.m)", "DL_ground", 2, 0, "-7.50")
        ]
        for label, key, row, col, default in fields:
            ttk.Label(common_frame, text=label).grid(row=row, column=col, padx=12, pady=6, sticky="e")
            self.inputs[key] = ttk.Entry(common_frame, width=15)
            self.inputs[key].insert(0, default)
            self.inputs[key].grid(row=row, column=col+1, padx=8, pady=6, sticky="w")
            
        # (1) 라벨 텍스트를 약간 수정하여 직관적으로 변경
        ttk.Label(common_frame, text="해저경사 (1/N)").grid(row=2, column=2, padx=12, pady=6, sticky="e")
        
        # (2) 콤보박스의 값을 숫자(분모)로 바꾸고, 직접 입력이 가능하도록 state="normal"로 변경
        self.cbo_slope = ttk.Combobox(common_frame, values=["10", "15", "30", "50", "100"], width=13, state="normal")
        self.cbo_slope.grid(row=2, column=3, padx=8, pady=6, sticky="w")
        self.cbo_slope.set("30")  # 기본값을 30 (즉, 1/30)으로 세팅
        
        # (3) 우측(column=4)에 설계자를 위한 입력 안내 문구 추가
        ttk.Label(common_frame, text="(입력 예시: 1/30 ➔ 30)").grid(row=2, column=4, padx=8, pady=6, sticky="w")

        # 3. 목적 변수
        self.var_input_frame = ttk.LabelFrame(left_container, text=" [STEP 3] 목적변수 입력 ")
        self.var_input_frame.pack(fill="x", pady=5)
        self.lbl_var = ttk.Label(self.var_input_frame, text="구조물 마루높이(DL.m)")
        self.lbl_var.grid(row=0, column=0, padx=10, pady=8, sticky="e")
        self.ent_var = ttk.Entry(self.var_input_frame)
        self.ent_var.insert(0, "5.00")
        self.ent_var.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        # 4. 구조물 형식 결정용 메인 탭
        self.tab_control = ttk.Notebook(left_container)
        self.tab_control.pack(fill="x", pady=5)
        
        # [형식 1] 경사제(TTP) 탭
        self.tab_sloping = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_sloping, text="  경사제 (Rubble Mound)  ")
        
        kds_sl_frame = ttk.LabelFrame(self.tab_sloping, text=" 국내 기준 및 공통 제원 ")
        kds_sl_frame.pack(fill="x", padx=8, pady=5, ipadx=5, ipady=5)
        
        sl_fields = [
            ("피복층 두께 AT (m)", "AT", 0, 0, "2.70"),
            ("어깨폭 Gw (m)", "Gw", 0, 2, "3.20"),
            ("피복재 체적 V (m³)", "V", 1, 0, "2.50"),
            ("사면경사 cotα", "cot_alpha", 1, 2, "1.50")
        ]
        for label, key, row, col, default in sl_fields:
            ttk.Label(kds_sl_frame, text=label).grid(row=row, column=col, padx=12, pady=5, sticky="e")
            self.inputs[key] = ttk.Entry(kds_sl_frame, width=12)
            self.inputs[key].insert(0, default)
            self.inputs[key].grid(row=row, column=col+1, padx=8, pady=5, sticky="w")

        foreign_sl_frame = ttk.LabelFrame(self.tab_sloping, text=" 외국 기준(CEM/EurOtop) 추가 제원 ")
        foreign_sl_frame.pack(fill="x", padx=8, pady=5, ipadx=5, ipady=5)
        
        fore_sl_fields = [
            ("피복재 거칠기계수 γf", "gamma_f", 0, 0, "0.50"),
            ("소단 영향계수 γb", "gamma_b", 0, 2, "1.00"),
            ("상치벽 영향계수 γv", "gamma_v", 1, 0, "1.00")
        ]
        for label, key, row, col, default in fore_sl_fields:
            ttk.Label(foreign_sl_frame, text=label).grid(row=row, column=col, padx=12, pady=5, sticky="e")
            self.inputs[key] = ttk.Entry(foreign_sl_frame, width=12)
            self.inputs[key].insert(0, default)
            self.inputs[key].grid(row=row, column=col+1, padx=8, pady=5, sticky="w")

        # [형식 2] 무공 직립제 탭
        self.tab_vertical = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_vertical, text="  무공 직립제 (Vertical Wall)  ")
        
        kds_vt_frame = ttk.LabelFrame(self.tab_vertical, text=" 국내 기준 제원 ")
        kds_vt_frame.pack(fill="x", padx=8, pady=5, ipadx=5, ipady=5)
        
        ttk.Label(kds_vt_frame, text="형상계수 γs (KDS 전용)").grid(row=0, column=0, padx=12, pady=8, sticky="e")
        self.inputs["gamma_s"] = ttk.Entry(kds_vt_frame, width=15)
        self.inputs["gamma_s"].insert(0, "1.00")
        self.inputs["gamma_s"].grid(row=0, column=1, padx=8, pady=8, sticky="w")

        foreign_vt_frame = ttk.LabelFrame(self.tab_vertical, text=" 외국 기준(CEM/EurOtop) 추가 구조 제원 ")
        foreign_vt_frame.pack(fill="x", padx=8, pady=5, ipadx=5, ipady=5)
        
        fore_vt_fields = [
            ("저감계수 γfc(CEM)", "gamma_fc_vt", 0, 0, "1.00"),
            ("저감계수 γv(EurOtop)", "gamma_v_vt", 0, 2, "1.00")
        ]
        for label, key, row, col, default in fore_vt_fields:
            ttk.Label(foreign_vt_frame, text=label).grid(row=row, column=col, padx=12, pady=5, sticky="e")
            self.inputs[key] = ttk.Entry(foreign_vt_frame, width=12)
            self.inputs[key].insert(0, default)
            self.inputs[key].grid(row=row, column=col+1, padx=8, pady=5, sticky="w")

        # 5. 선택 형식 개념도 프레임
        self.img_frame = ttk.LabelFrame(left_container, text=" [선택 형식 개념도] ")
        self.img_frame.pack(fill="both", expand=True, pady=5)
        self.img_label = ttk.Label(self.img_frame, text="개념도를 로드 중입니다.")
        self.img_label.pack(expand=True)
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 6. 제어 버튼
        btn_frame = ttk.Frame(left_container)
        btn_frame.pack(fill="x", pady=10)
        btn_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="equal")
        
        ttk.Button(btn_frame, text="📁 불러오기", command=self.load_data).grid(row=0, column=0, padx=4, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="💾 저장하기", command=self.save_data).grid(row=0, column=1, padx=4, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="⚙️ 종합 계산 실행", command=self.execute_calculation).grid(row=0, column=2, padx=4, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="🚪 나가기", command=self.root.destroy).grid(row=0, column=3, padx=4, pady=5, sticky="ew")

        # 보고서 출력창
        right_container = ttk.LabelFrame(main_paned, text=" [계산 상세 근거 및 기준별 비교 보고서] ")
        main_paned.add(right_container, weight=2)
        self.txt_log = tk.Text(right_container, bg="#ffffff", font=self.log_korean_font, padx=20, pady=20, relief="flat", spacing1=3, spacing2=2, spacing3=3)
        self.txt_log.pack(fill="both", expand=True)

    def on_tab_changed(self, event):
        tab_id = self.tab_control.index(self.tab_control.select())
        if tab_id == 2: return
        
        # 변수명을 직관적으로 img_name으로 통일
        img_name = "경사제(월파량)_1.png" if tab_id == 0 else "직립제(월파량)_1.png" 
        
        if os.path.exists(self.master_zip_path):
            try:
                with zipfile.ZipFile(self.master_zip_path, 'r') as archive:
                    # 압축 파일 내에 해당 단면 이미지가 있는지 검색
                    matched_file = [f for f in archive.namelist() if img_name.lower() in f.lower()]
                    
                    if matched_file:
                        img_data = archive.read(matched_file[0])
                        img = Image.open(io.BytesIO(img_data)).convert("RGB")
                        # 👇 새로 추가할 부분: 최대 가로 800, 세로 300 픽셀 안에서 비율 유지하며 축소
                        try:
                            img.thumbnail((680, 270), Image.Resampling.LANCZOS)
                        except AttributeError:
                            # 구버전 라이브러리 호환성을 위한 예외 처리
                            img.thumbnail((680, 270), Image.ANTIALIAS)
                        photo = ImageTk.PhotoImage(img)
                        self.notebook_images[tab_id] = photo
                        self.img_label.config(image=photo, text="")
            except Exception: pass

    def toggle_mode(self):
        self.lbl_var.config(text="구조물 마루높이(DL.m)" if self.mode_var.get() == "q" else "허용 월파량 q_all(m³/s/m)")
        self.ent_var.delete(0, tk.END)
        if self.mode_var.get() == "q":
            self.ent_var.insert(0, "5.00")
        else:
            self.ent_var.insert(0, "0.01")

    def log_header(self, title):
        self.txt_log.insert(tk.END, "\n" + "=" * 75 + "\n")
        self.txt_log.insert(tk.END, f" ▣ {title}\n")
        self.txt_log.insert(tk.END, "=" * 75 + "\n")

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")

    def calc_linear_Ks(self, h, T):
        g = 9.81
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
        
        # 1. 초기 선형 이론값 도출
        Ks_linear, _ = self.calc_linear_Ks(h, T)
        H0_prime_linear = input_H13 / Ks_linear 
        
        current_H0_prime = H0_prime_linear
        current_Ks = Ks_linear
        
        max_iter = 100
        tolerance = 0.001
        
        # 2. 듀얼 반복 시작
        for outer_iteration in range(max_iter):
            steepness = current_H0_prime / L0
            rel_depth_L0 = h / L0
            
            # 외부 루프: 슈토 도표를 통한 Ks 업데이트 (CSV 데이터 활용)
            if hasattr(self, 'ks_points') and len(self.ks_points) > 0:
                Ks_chart = griddata(self.ks_points, self.ks_values, (steepness, rel_depth_L0), method='linear')
                if np.isnan(Ks_chart): # 보간 범위를 벗어나면 근사치 사용
                    Ks_chart = griddata(self.ks_points, self.ks_values, (steepness, rel_depth_L0), method='nearest')
                fixed_Ks = float(Ks_chart)
            else:
                fixed_Ks = Ks_linear
            
            inner_H0_prime = current_H0_prime
            inner_converged = False
            
            # 내부 루프: 고다 쇄파 공식을 통한 H0' 업데이트
            for inner_iteration in range(max_iter):
                calc_H13 = self.calc_goda_H13(inner_H0_prime, h, slope_val, L0, fixed_Ks)
                error1 = input_H13 - calc_H13
                
                if abs(error1) <= tolerance:
                    inner_converged = True
                    break
                inner_H0_prime = inner_H0_prime + (error1 * 0.5)
                
            # 새로운 Ks 재확인 (수렴 판정용)
            new_steepness = inner_H0_prime / L0
            if hasattr(self, 'ks_points') and len(self.ks_points) > 0:
                new_Ks_chart = griddata(self.ks_points, self.ks_values, (new_steepness, rel_depth_L0), method='linear')
                if np.isnan(new_Ks_chart):
                    new_Ks_chart = griddata(self.ks_points, self.ks_values, (new_steepness, rel_depth_L0), method='nearest')
                new_Ks_chart = float(new_Ks_chart)
            else:
                new_Ks_chart = fixed_Ks
            
            error2 = current_H0_prime - inner_H0_prime 
            error3 = fixed_Ks - new_Ks_chart           
            
            current_H0_prime = inner_H0_prime
            current_Ks = new_Ks_chart
            
            # 3가지 조건 모두 만족 시 종료
            if abs(error2) <= tolerance and abs(error3) <= tolerance and inner_converged:
                return current_H0_prime

        # 수렴 실패 시 안전하게 초기 선형이론값 반환
        return H0_prime_linear
    
    # ==============================================================================
    # [상단계산 100% 복원] 국내 연구기준 (KDS) - 경사제
    # ==============================================================================
    def calc_q_kds_sloping(self, H13, T13, Rc, h, AT, Gw, V, cot_alpha, theta, verbose=True):
        L0 = get_L0(T13)
        s0 = H13 / L0
        gamma_theta = get_gamma_theta_sloping(theta)
        Dn = V**(1/3)
        
        R_val = (1/gamma_theta) * (Rc/H13)**2 * (s0/(2*math.pi))**0.5 * (h/H13)**0.1 * (AT/H13) * (Gw/Dn)**0.6 * cot_alpha
        Q = 0.001 * math.exp(-7.38 * R_val)
        q = Q * G * H13 * T13
        
        if verbose:
            self.log_header("① 국내 연구기준(KDS, 2026) 실계산 과정")
            self.log(f"   - 심해파장      : L0 = (9.81 * {T13}^2) / 2π = {L0:.2f} m")
            self.log(f"   - 파형경사      : s0 = {H13} / {L0:.2f} = {s0:.4f}")
            self.log(f"   - 피복재 공칭길이: Dn = {V}^(1/3) = {Dn:.4f} m")
            self.log(f"   - 전면수심      : h  = {h:.2f} m")
            self.log(f"   \n   이제 국내 기준의 핵심 변수 R을 계산하면 다음과 같습니다.")
            self.log(f"   R = (1/{gamma_theta:.2f}) * ({Rc:.2f}/{H13})^2 * √({s0:.4f}/2π) * ({h:.2f}/{H13})^0.1 * ({AT}/{H13}) * ({Gw}/{Dn:.4f})^0.6 * {cot_alpha}")
            
            p1 = (Rc/H13)**2
            p2 = (s0/(2*math.pi))**0.5
            p3 = (h/H13)**0.1
            p4 = (AT/H13)
            p5 = (Gw/Dn)**0.6
            self.log(f"   R = {1/gamma_theta:.3f} * {p1:.3f} * {p2:.4f} * {p3:.3f} * {p4:.3f} * {p5:.3f} * {cot_alpha} ≈ {R_val:.4f}")
            self.log(f"   \n   이 R 값을 무차원 월파량 공식 Q = 0.001 * exp(-7.38 * R) 에 대입하면:")
            self.log(f"   Q = 0.001 * exp(-7.38 * {R_val:.4f}) = 0.001 * exp({-7.38*R_val:.3f}) ≈ {Q:.4e}")
            self.log(f"   \n   최종 월파량 (q_KDS):")
            self.log(f"   q = Q * g * H1/3 * T1/3 = {Q:.4e} * 9.81 * {H13} * {T13} ≈ {q:.8f} m³/s/m")
            
            self.log("\n   [KDS 공식 실험조건 범위 적합도 판정 결과]")
            self.log("   " + "-" * 60)
            v1, v2, v3, v4, v5 = Rc / H13, s0, H13 / h, Gw / Dn, AT / H13
            c1 = "O.K" if (0.77 <= v1 <= 2.0) else "⚠️ 범위초과/신뢰성낮음"
            c2 = "O.K" if (0.007 <= v2 <= 0.049) else "⚠️ 범위초과/신뢰성낮음"
            c3 = "O.K" if (0.30 <= v3 <= 0.53) else "⚠️ 범위초과/신뢰성낮음"
            c4 = "O.K" if (2.32 <= v4 <= 7.92) else "⚠️ 범위초과/신뢰성낮음"
            c5 = "O.K" if (0.60 <= v5 <= 1.52) else "⚠️ 범위초과/신뢰성낮음"
            
            self.log(f"    1) 여유고 조건   (Rc/H1/3  = {v1:.3f} / 기준: 0.77 ~ 2.0)  ➔ {c1}")
            self.log(f"    2) 파형경사 조건 (s0       = {v2:.4f} / 기준: 0.007 ~ 0.049)➔ {c2}")
            self.log(f"    3) 수심대비 파고 (H1/3/h   = {v3:.3f} / 기준: 0.30 ~ 0.53)  ➔ {c3}")
            self.log(f"    4) 어깨폭 비율   (Gw/Dn    = {v4:.3f} / 기준: 2.32 ~ 7.92)  ➔ {c4}")
            self.log(f"    5) 피복두께 비율 (AT/H1/3  = {v5:.3f} / 기준: 0.60 ~ 1.52)  ➔ {c5}")
            
            if "⚠️ 범위초과/신뢰성낮음" in [c1, c2, c3, c4, c5]:
                self.log("\n   ※ 판정의견: 현재 단면은 KDS 수리실험 유효 범위를 이탈하였습니다.")
                self.log("                공식 산정 오차가 크므로 외국기준(EurOtop) 병행 검토 혹은")
                self.log("                단면 치수 재조정 및 단면 수리모형실험 수행을 강력히 권장합니다.")
            else:
                self.log("\n   ※ 판정의견: 입력 조건이 KDS 실험조건을 완전히 만족하여 신뢰도가 높습니다.")
            self.log("   " + "-" * 60)
        return q

    # ==============================================================================
    # [상단계산 100% 복원] 국내 연구기준 (KDS) - 무공 직립제
    # ==============================================================================
    def calc_q_kds_vertical(self, H13, T13, Rc, h, gamma_s, theta, verbose=True):
        L13 = get_L0(T13)
        s = H13 / L13
        h_star = (h**2) / (H13 * L13)
        sqrt_gH3 = math.sqrt(G * H13**3)
        
        if h_star > 0.23:
            gamma_theta = get_gamma_theta_vertical(theta)
            q_norm = 0.0215 * (H13 / (h * s))**0.5 * math.exp(-3.11 * Rc / (H13 * gamma_s * gamma_theta))
            cond = f"비충격파 (h* = {h_star:.4f} > 0.23)"
            formula_str = f"0.0215 * √({H13}/({h}*{s:.4f})) * exp(-3.11 * {Rc}/({H13} * {gamma_s} * {gamma_theta:.2f}))"
            
            v_rc, v_h, v_s = Rc / H13, H13 / h, s
            r_c1 = "O.K" if (0.6 <= v_rc <= 1.5) else "⚠️ 범위초과/신뢰성낮음"
            r_c2 = "O.K" if (0.08 <= v_h <= 0.47) else "⚠️ 범위초과/신뢰성낮음"
            r_c3 = "O.K" if (0.008 <= v_s <= 0.054) else "⚠️ 범위초과/신뢰성낮음"
            range_info = [("여유고 비(Rc/H1/3)", v_rc, "0.6 ~ 1.5", r_c1), 
                          ("수심대비파고(H1/3/h)", v_h, "0.08 ~ 0.47", r_c2), 
                          ("파형경사(s)", v_s, "0.008 ~ 0.054", r_c3)]
        else:
            gamma_theta = 1.0
            Rc_ratio = Rc / H13
            cond = f"충격파 (h* = {h_star:.4f} <= 0.23)"
            if Rc_ratio < 1.35:
                q_norm = 0.017 * (H13 / (h * s))**0.5 * math.exp(-2.47 * Rc_ratio)
                formula_str = f"0.017 * √({H13}/({h}*{s:.4f})) * exp(-2.47 * {Rc_ratio:.3f})"
            else:
                q_norm = 0.0016 * (H13 / (h * s))**0.5 * (Rc_ratio)**(-3.1)
                formula_str = f"0.0016 * √({H13}/({h}*{s:.4f})) * ({Rc_ratio:.3f})^-3.1"
            
            v_rc, v_h, v_s = Rc_ratio, H13 / h, s
            r_c1 = "O.K" if (0.6 <= v_rc <= 1.5) else "⚠️ 범위초과/신뢰성낮음"
            r_c2 = "O.K" if (0.20 <= v_h <= 0.63) else "⚠️ 범위초과/신뢰성낮음"
            r_c3 = "O.K" if (0.015 <= v_s <= 0.057) else "⚠️ 범위초과/신뢰성낮음"
            range_info = [("여유고 비(Rc/H1/3)", v_rc, "0.6 ~ 1.5", r_c1), 
                          ("수심대비파고(H1/3/h)", v_h, "0.20 ~ 0.63", r_c2), 
                          ("파형경사(s)", v_s, "0.015 ~ 0.057", r_c3)]
                
        q = q_norm * sqrt_gH3
        if verbose:
            self.log_header("① 국내 연구기준(KDS, 2026) 실계산 과정")
            self.log(f"   - 심해파장(L13) : {L13:.2f} m  |  파형경사(s) : {s:.4f}")
            self.log(f"   - 충격지수(h*)  : h^2 / (H1/3 * L1/3) = {h_star:.4f} ➔ {cond}")
            self.log(f"   \n   KDS 직립벽 공식에 대입하면:")
            self.log(f"   무차원 q = {formula_str} ≈ {q_norm:.4e}")
            self.log(f"   \n   최종 월파량 (q_KDS):")
            self.log(f"   q = 무차원 q * √(g * H1/3^3) = {q_norm:.4e} * {sqrt_gH3:.4f} ≈ {q:.8f} m³/s/m")
            
            self.log("\n   [KDS 공식 직립벽 실험조건 범위 적합도 판정 결과]")
            self.log("   " + "-" * 60)
            has_error = False
            for title, val, b_range, chk in range_info:
                self.log(f"    - {title:<20}: 현재값 = {val:.4f} (적정범위: {b_range}) ➔ {chk}")
                if "⚠️" in chk: has_error = True
                
            if has_error:
                self.log("\n   ※ 판정의견: 현재 직립제 제원이 KDS 실험범위를 이탈하였습니다.")
                self.log("                충격파/비충격파 파압 연계 특성상 오차가 심화될 수 있으므로")
                self.log("                EurOtop(2018) 기준과의 교차 비교를 기반으로 검토하십시오.")
            else:
                self.log("\n   ※ 판정의견: 직립벽 적용 실험 범위 내에 정상 포함되어 있습니다.")
            self.log("   " + "-" * 60)
        return q

    # ==============================================================================
    # [상단계산 100% 복원] USACE CEM (2006) - 경사제 / 직립제
    # ==============================================================================
    def calc_q_cem_sloping(self, H13, T13, Rc, h, cot_alpha, theta, gamma_f, verbose=True):
        L0 = get_L0(T13)
        alpha = math.atan(1.0 / cot_alpha)
        xi0 = math.tan(alpha) / math.sqrt(H13 / L0)
        gamma_beta = get_gamma_theta_sloping(theta)
        sqrt_gH3 = math.sqrt(G * H13**3)
        
        if xi0 < 2.0:
            q_norm = (0.06 / math.sqrt(math.tan(alpha))) * xi0 * math.exp(-5.2 * Rc / (H13 * xi0 * gamma_f * gamma_beta))
            cond = f"쇄파형 파랑 (xi0 = {xi0:.3f} < 2.0)"
            f_str = f"(0.06 / √{math.tan(alpha):.3f}) * {xi0:.3f} * exp(-5.2 * {Rc} / ({H13} * {xi0:.3f} * {gamma_f} * {gamma_beta:.2f}))"
        else:
            q_norm = 0.2 * math.exp(-2.6 * Rc / (H13 * gamma_f * gamma_beta))
            cond = f"비쇄파형 파랑 (xi0 = {xi0:.3f} >= 2.0)"
            f_str = f"0.2 * exp(-2.6 * {Rc} / ({H13} * {gamma_f} * {gamma_beta:.2f}))"
            
        q = q_norm * sqrt_gH3
        if verbose:
            self.log_header("② 해외 기준(USACE CEM, 2006) 기준 실계산 과정")
            self.log(f"   - 심해파장      : L0 = {L0:.2f} m")
            self.log(f"   - 쇄파매개변수  : xi0 = tan(α) / √(H1/3/L0) = {xi0:.4f} ➔ {cond}")
            self.log(f"   \n   CEM 경사제 공식에 대입하면:")
            self.log(f"   무차원 Q = {f_str} ≈ {q_norm:.4e}")
            self.log(f"   \n   최종 월파량 (q_CEM):")
            self.log(f"   q = 무차원 Q * √(g * H1/3^3) = {q_norm:.4e} * {sqrt_gH3:.4f} ≈ {q:.8f} m³/s/m")
        return q

    def calc_q_cem_vertical(self, H13, T13, Rc, h, theta, gamma_fc, verbose=True):
        gamma_beta = get_gamma_theta_vertical(theta)
        q_norm = 0.04 * gamma_fc * math.exp(-2.6 * Rc / (H13 * gamma_beta))
        sqrt_gH3 = math.sqrt(G * H13**3)
        q = q_norm * sqrt_gH3
        if verbose:
            self.log_header("② 해외 기준(USACE CEM, 2006) 기준 실계산 과정")
            self.log(f"   - 파향 보정계수 : γβ = {gamma_beta:.3f} (Franco 식 중복파 모델 적용)")
            self.log(f"   - 형상 저감계수 : γfc = {gamma_fc} (유수실 구조 및 블록 피복 감쇄율)")
            self.log(f"   \n   CEM 직립벽 공식에 대입하면:")
            self.log(f"   무차원 Q = 0.04 * {gamma_fc} * exp(-2.6 * {Rc} / ({H13} * {gamma_beta:.3f})) ≈ {q_norm:.4e}")
            self.log(f"   \n   최종 월파량 (q_CEM):")
            self.log(f"   q = 무차원 Q * √(g * H1/3^3) = {q_norm:.4e} * {sqrt_gH3:.4f} ≈ {q:.8f} m³/s/m")
        return q

    # ==============================================================================
    # [상단계산 100% 복원] EurOtop (2018) - 경사제 / 직립제
    # ==============================================================================
    def calc_q_euro_sloping(self, H13, T13, Rc, h, cot_alpha, theta, gamma_f, gamma_b, gamma_v, verbose=True):
        Tm_10 = T13 / 1.1
        L_10 = (G * Tm_10**2) / (2 * math.pi)
        alpha = math.atan(1.0 / cot_alpha)
        xi_10 = math.tan(alpha) / math.sqrt(H13 / L_10)
        gamma_beta = get_gamma_theta_sloping(theta)
        sqrt_gH3 = math.sqrt(G * H13**3)
        
        v_breaking = 1.5 * Rc / (H13 * gamma_f * gamma_beta * gamma_b * gamma_v)
        v_nonbreaking = 1.5 * Rc / (H13 * gamma_f * gamma_beta)
        
        q_wave_breaking = (0.09 / math.sqrt(math.tan(alpha))) * xi_10 * math.exp(- (v_breaking)**1.3)
        q_non_breaking = 0.09 * math.exp(- (v_nonbreaking)**1.3)
        
        q_norm = min(q_wave_breaking, q_non_breaking)
        q = q_norm * sqrt_gH3
        
        if verbose:
            self.log_header("③ 해외 기준(EurOtop, 2018) 실계산 과정")
            self.log(f"   EurOtop 공식은 환산 주기 Tm-1,0 = {T13} / 1.1 ≈ {Tm_10:.2f} s를 기준으로 쇄파매개변수를 구합니다.")
            self.log(f"   - 환산 심해파장: L_m-1,0 = {L_10:.2f} m")
            self.log(f"   - 쇄파매개변수  : ξ_m-1,0 = (1/{cot_alpha}) / √({H13}/{L_10:.2f}) ≈ {xi_10:.3f}")
            self.log(f"   \n   EurOtop의 1.3승 한계 공식(쇄파형 및 비쇄파형 중 최소치 선택)에 대입하면:")
            self.log(f"   - 쇄파형 검토 무차원 공식조합 무차원 변수 : {v_breaking:.3f} ➔ 1.3승 결과: {v_breaking**1.3:.3f}")
            self.log(f"   - 비쇄파형 검토 공식조합 무차원 변수   : {v_nonbreaking:.3f} ➔ 1.3승 결과: {v_nonbreaking**1.3:.3f}")
            self.log(f"   - 최종 결정 무차원 월파량 q_norm ≈ {q_norm:.4e}")
            self.log(f"   \n   최종 월파량 (q_Euro):")
            self.log(f"   q = q_norm * √(g * H1/3^3) = {q_norm:.4e} * {sqrt_gH3:.4f} ≈ {q:.8f} m³/s/m")
        return q

    def calc_q_euro_vertical(self, H13, T13, Rc, h, theta, gamma_v_vt, verbose=True):
        Tm_10 = T13 / 1.1
        L_10 = (G * Tm_10**2) / (2 * math.pi)
        h_star = (h / H13) * (h / L_10)
        gamma_beta = get_gamma_theta_vertical(theta)
        sqrt_gH3 = math.sqrt(G * H13**3)
        
        if h_star > 0.23:
            q_norm = 0.047 * math.exp(- 2.35 * Rc / (H13 * gamma_beta * gamma_v_vt))
            cond = f"비충격파 (h* = {h_star:.4f} > 0.23)"
            f_str = f"0.047 * exp(-2.35 * {Rc} / ({H13} * {gamma_beta:.2f} * {gamma_v_vt}))"
        else:
            cond = f"충격파 발생 (h* = {h_star:.4f} <= 0.23)"
            if Rc > 0:
                q_norm = 0.011 * (h_star**-0.75) * ((Rc / H13)**-3.0)
                f_str = f"0.011 * ({h_star:.4f}^-0.75) * ({Rc}/{H13})^-3.0"
            else:
                q_norm = 0.011 * (h_star**-0.75)
                f_str = f"0.011 * ({h_star:.4f}^-0.75)"
                
        q = q_norm * sqrt_gH3
        if verbose:
            self.log_header("③ 해외 기준(EurOtop, 2018) 실계산 과정")
            self.log(f"   EurOtop 공식은 환산 주기 Tm-1,0 = {T13} / 1.1 ≈ {Tm_10:.2f} s를 기준으로 수심 매개변수를 구합니다.")
            self.log(f"   - EurOtop 전용 수심지수: h* = (h/H1/3) * (h/L_m-1,0) = {h_star:.4f} ➔ {cond}")
            self.log(f"   - 상치벽/파라펫 저감지수: γv = {gamma_v_vt}")
            self.log(f"   \n   EurOtop 직립벽 공식에 대입하면:")
            self.log(f"   무차원 q_norm = {f_str} ≈ {q_norm:.4e}")
            self.log(f"   \n   최종 월파량 (q_Euro):")
            self.log(f"   q = q_norm * √(g * H1/3^3) = {q_norm:.4e} * {sqrt_gH3:.4f} ≈ {q:.8f} m³/s/m")
        return q

    def dispatch_calculation(self, std_name, tab_id, H13, T13, Rc, h, theta, verbose=True):
        if tab_id == 0:
            AT = float(self.inputs["AT"].get())
            Gw = float(self.inputs["Gw"].get())
            V = float(self.inputs["V"].get())
            ca = float(self.inputs["cot_alpha"].get())
            gf = float(self.inputs["gamma_f"].get() if self.inputs["gamma_f"].get() else 0.5)
            gb = float(self.inputs["gamma_b"].get() if self.inputs["gamma_b"].get() else 1.0)
            gv = float(self.inputs["gamma_v"].get() if self.inputs["gamma_v"].get() else 1.0)
            if std_name == "KDS": return self.calc_q_kds_sloping(H13, T13, Rc, h, AT, Gw, V, ca, theta, verbose)
            elif std_name == "CEM": return self.calc_q_cem_sloping(H13, T13, Rc, h, ca, theta, gf, verbose)
            elif std_name == "EURO": return self.calc_q_euro_sloping(H13, T13, Rc, h, ca, theta, gf, gb, gv, verbose)
        else:
            gs = float(self.inputs["gamma_s"].get())
            g_fc_vt = float(self.inputs["gamma_fc_vt"].get() if self.inputs["gamma_fc_vt"].get() else 1.0)
            g_v_vt = float(self.inputs["gamma_v_vt"].get() if self.inputs["gamma_v_vt"].get() else 1.0)
            if std_name == "KDS": return self.calc_q_kds_vertical(H13, T13, Rc, h, gs, theta, verbose)
            elif std_name == "CEM": return self.calc_q_cem_vertical(H13, T13, Rc, h, theta, g_fc_vt, verbose)
            elif std_name == "EURO": return self.calc_q_euro_vertical(H13, T13, Rc, h, theta, g_v_vt, verbose)
        return 0.0

    def execute_calculation(self):
        try:
            H13, T13 = float(self.inputs["H13"].get()), float(self.inputs["T13"].get())
            theta = float(self.inputs["theta"].get())
            WL, GL = float(self.inputs["DL_water"].get()), float(self.inputs["DL_ground"].get())
            h = WL - GL
            
            tab_id = self.tab_control.index(self.tab_control.select())
            struct_type_str = "경사제 (Rubble Mound)" if tab_id == 0 else "무공 직립제 (Vertical Wall)"

            active_standards = []
            if self.chk_kds.get(): active_standards.append(("KDS", "국내 연구기준"))
            if self.chk_cem.get(): active_standards.append(("CEM", "USACE CEM (2006)"))
            if self.chk_euro.get(): active_standards.append(("EURO", "EurOtop (2018)"))
            if self.chk_goda.get(): active_standards.append(("GODA", "Goda (일본항만기준)"))
            
            if not active_standards:
                messagebox.showwarning("기준 미선택", "최소 하나 이상의 검토 기준 체크박스를 선택하십시오.")
                return

            self.txt_log.delete(1.0, tk.END)
            self.log("======================================================================")
            self.log("                  [공통 파랑 및 구조물 입력 제원]")
            self.log("======================================================================")
            self.log(f" ● 검토 구조물 형식 : {struct_type_str}")
            self.log(f" ● 유의파고(H1/3) = {H13} m   |   유의주기(T1/3) = {T13} s   |   입사각 = {theta}°")
            self.log(f" ● 검토조위 = DL +{WL:.2f} m  |   원지반고 = DL +{GL:.2f} m  |   설계수심 = {h:.2f} m")
            
            results_summary = {}

            if self.mode_var.get() == "q":
                Crest = float(self.ent_var.get())
                Rc_input = Crest - WL
                self.log(f" ● 적용 마루높이 = DL +{Crest:.2f} m  ➔  산정 여유고(Rc) = {Rc_input:.3f} m")
                
                for std_code, std_name in active_standards:
                    if std_code == "GODA":
                        slope_str = self.cbo_slope.get().replace("1/", "")
                        slope_num = float(slope_str) if slope_str.isdigit() else 30.0
    
                        H0_prime_calc = self.get_converged_H0_prime(H13, T13, h, slope_num)
    
                        # 로그 출력은 Goda 모듈 내부로 위임하고, H13 원본 파고를 인자로 추가 전달합니다.
                        q_res = goda_plug.execute_goda_calc(H13, H0_prime_calc, T13, h, Rc_input, struct_type_str, verbose=True)
                        results_summary[std_name] = (f"{Rc_input:.3f} m", f"{q_res:.6f} m³/s/m")
                    else:
                        q_res = self.dispatch_calculation(std_code, tab_id, H13, T13, Rc_input, h, theta, verbose=True)
                        results_summary[std_name] = (f"{Rc_input:.3f} m", f"{q_res:.8f} m³/s/m")
            else:
                q_target = float(self.ent_var.get())
                self.log(f" ● 목표 허용 월파량(q_all) = {q_target} m³/s/m")
                
                for std_code, std_name in active_standards:
                    if std_code == "GODA":
                        self.log(f"\n ▷ {std_name} 기준에 따른 수치 역산 수렴 진행중...")
                        
                        # 1. Goda 역산에 필수적인 H0' 먼저 계산
                        slope_str = self.cbo_slope.get().replace("1/", "")
                        slope_num = float(slope_str) if slope_str.isdigit() else 30.0
                        H0_prime_calc = self.get_converged_H0_prime(H13, T13, h, slope_num)
                        
                        # 2. 방금 수정한 calculate_Rc_by_goda를 호출하여 최종 Rc 확보
                        res_Rc = goda_plug.calculate_Rc_by_goda(q_target, H13, H0_prime_calc, T13, h, struct_type_str)
                        
                        # 3. 최종 산정된 Rc를 바탕으로 상세 계산 근거 로그 출력
                        goda_plug.execute_goda_calc(H13, H0_prime_calc, T13, h, res_Rc, struct_type_str, verbose=True)
                        results_summary[std_name] = (f"{res_Rc:.3f} m", f"DL +{res_Rc + WL:.3f} m")
                    else:
                        self.log(f"\n ▷ {std_name} 기준에 따른 수치 역산 수렴 진행중...")
                        f = lambda x: self.dispatch_calculation(std_code, tab_id, H13, T13, x, h, theta, verbose=False) - q_target
                        res_Rc = brentq_solver(f, 0.01, 25.0)
                        self.dispatch_calculation(std_code, tab_id, H13, T13, res_Rc, h, theta, verbose=True)
                        results_summary[std_name] = (f"{res_Rc:.3f} m", f"DL +{res_Rc + WL:.3f} m")

            def pad_string(s, target_width):
                current_width = sum(2 if ord(char) > 127 else 1 for char in s)
                if current_width >= target_width: return s
                return s + " " * (target_width - current_width)

            col1_w, col2_w, col3_w = 26, 20, 25
            self.log_header(f"최종 설계 기준별 검토 결과 종합 비교표 ({struct_type_str})")
            
            if self.mode_var.get() == "q":
                header_str = f" {pad_string('검토 적용 설계 기준', col1_w)} | {pad_string('입력 여유고 (Rc)', col2_w)} | {pad_string('산정 월파량 (q)', col3_w)}"
                self.log(header_str)
                self.log("-" * (col1_w + col2_w + col3_w + 7))
                for name, data in results_summary.items():
                    row_str = f" {pad_string(name, col1_w)} | {pad_string(data[0], col2_w)} | {pad_string(data[1], col3_w)}"
                    self.log(row_str)
            else:
                header_str = f" {pad_string('검토 적용 설계 기준', col1_w)} | {pad_string('소요 여유고 (Rc)', col2_w)} | {pad_string('설계 마루높이 (DL)', col3_w)}"
                self.log(header_str)
                self.log("-" * (col1_w + col2_w + col3_w + 7))
                for name, data in results_summary.items():
                    row_str = f" {pad_string(name, col1_w)} | {pad_string(data[0], col2_w)} | {pad_string(data[1], col3_w)}"
                    self.log(row_str)
            self.log("=" * (col1_w + col2_w + col3_w + 7))

        except Exception as e: 
            messagebox.showerror("입력 오류", f"수치 제원 및 입력형식을 재확인하세요.\n{e}")

    def save_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".otp", filetypes=[("월파량 데이터 파일", "*.otp")])
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"MODE:{self.mode_var.get()}\nVAR:{self.ent_var.get()}\n")
                    f.write(f"CHKS:{self.chk_kds.get()},{self.chk_cem.get()},{self.chk_euro.get()},{self.chk_goda.get()}\n")
                    for key, entry in self.inputs.items(): f.write(f"{key}:{entry.get()}\n")
                messagebox.showinfo("저장 완료", "모든 검토 데이터가 안전하게 저장되었습니다.")
            except Exception as e: messagebox.showerror("저장 실패", f"{e}")

    def load_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("월파량 데이터 파일", "*.otp")])
        if file_path:
            try:
                has_sloping_data = False
                has_vertical_data = False
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if ":" in line:
                            key, val = line.strip().split(":", 1)
                            if key == "MODE": 
                                self.mode_var.set(val)
                                self.toggle_mode()
                            elif key == "VAR": 
                                self.ent_var.delete(0, tk.END)
                                self.ent_var.insert(0, val)
                            elif key == "CHKS":
                                tokens = val.split(",")
                                self.chk_kds.set(tokens[0] == "True")
                                self.chk_cem.set(tokens[1] == "True")
                                self.chk_euro.set(tokens[2] == "True")
                                if len(tokens) > 3:
                                    self.chk_goda.set(tokens[3] == "True")
                            elif key in self.inputs:
                                self.inputs[key].delete(0, tk.END)
                                self.inputs[key].insert(0, val)
                                if key in ["AT", "Gw", "V", "cot_alpha"]:
                                    if val.strip() != "": has_sloping_data = True
                                if key in ["gamma_s", "gamma_fc_vt", "gamma_v_vt"]:
                                    if val.strip() != "": has_vertical_data = True
                if has_vertical_data and not has_sloping_data:
                    self.tab_control.select(1)
                elif has_sloping_data:
                    self.tab_control.select(0)
                messagebox.showinfo("로드 완료", "이전 검토 데이터를 정상적으로 매핑하고 해당 제원 탭으로 이동했습니다.")
            except Exception as e: 
                messagebox.showerror("불러오기 실패", f"파일을 읽는 중 오류가 발생했습니다.\n{e}")

# ==============================================================================
# Goda 확장 플러그인 구역 (디지타이징 데이터 기반 정밀 보간 및 보고서 출력 모듈)
# ==============================================================================
class GodaExtensionModule:
    def __init__(self, app_instance):
        self.app = app_instance
        self.config_df = None
        self.goda_interp_data = {} # 디지타이징 데이터 저장소
        
        self.load_graph_config()
        self.load_goda_digitized_data() # 압축파일에서 CSV 자동 로드

    def load_graph_config(self):
        if os.path.exists(self.app.master_zip_path):
            try:
                with zipfile.ZipFile(self.app.master_zip_path, 'r') as z:
                    if "graph_config.csv" in z.namelist():
                        with z.open("graph_config.csv") as f:
                            self.config_df = pd.read_csv(f)
                            self.config_df['file_name'] = self.config_df['file_name'].str.strip().str.lower()
            except: pass

    def load_goda_digitized_data(self):
        """ source_overtop.zip 내부의 s_*, v_* CSV 데이터를 읽어 보간 함수로 준비합니다. """
        if not os.path.exists(self.app.master_zip_path): return
        try:
            from scipy.interpolate import interp1d
            with zipfile.ZipFile(self.app.master_zip_path, 'r') as z:
                csv_files = [f for f in z.namelist() if f.endswith('.csv') and (f.startswith('s_') or f.startswith('v_'))]
                for csv_file in csv_files:
                    file_key = csv_file.replace('.csv', '').lower()
                    with z.open(csv_file) as f:
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
                        self.goda_interp_data[file_key] = curve_dict
            print(f"디지타이징 CSV 로딩 완료: 총 {len(self.goda_interp_data)}개 도표 데이터 구축")
        except Exception as e:
            print(f"디지타이징 CSV 로딩 실패: {e}")

    def get_Y_from_chart(self, file_key, h_H0, Rc_H0):
        if file_key not in self.goda_interp_data: return None
        curves = self.goda_interp_data[file_key]
        available_Rc = sorted(curves.keys())
        if not available_Rc: return None
        
        if Rc_H0 <= available_Rc[0]:
            return float(curves[available_Rc[0]](h_H0))
        elif Rc_H0 >= available_Rc[-1]:
            return float(curves[available_Rc[-1]](h_H0))
        
        for i in range(len(available_Rc)-1):
            if available_Rc[i] <= Rc_H0 <= available_Rc[i+1]:
                Rc_lo, Rc_hi = available_Rc[i], available_Rc[i+1]
                Y_lo = float(curves[Rc_lo](h_H0))
                Y_hi = float(curves[Rc_hi](h_H0))
                if Y_lo <= 0 or Y_hi <= 0: return 0.0
                
                log_Y_lo = math.log10(Y_lo)
                log_Y_hi = math.log10(Y_hi)
                factor = (Rc_H0 - Rc_lo) / (Rc_hi - Rc_lo)
                log_Y = log_Y_lo + factor * (log_Y_hi - log_Y_lo)
                return 10 ** log_Y
        return None
    
    def calculate_Rc_by_goda(self, target_q, H13, H0_prime, T, h, struct_type):
        """
        1. 초기값: Takayama 근사식을 역산하여 초기 여유고(Rc) 산정
        2. 도표 범위 내라면: 도표 보간으로 정밀 수렴
        3. 도표 범위 밖이라면: "도표 산정 불가" 경고 후 근사식 최종값 제시
        """
        # 1. Takayama 근사식 기반 역산으로 초기 여유고(Rc) 탐색
        f_approx = lambda x: self.calculate_takayama_formula(h, x, H0_prime) - target_q
        initial_rc = brentq_solver(f_approx, 0.01, 30.0)
        
        # 도표의 물리적 한계 Rc/H0' 값 (0.5 ~ 2.0)
        min_rc = 0.5 * H0_prime
        max_rc = 2.0 * H0_prime
        
        # 2. 도표 범위 검증
        if initial_rc < min_rc or initial_rc > max_rc:
            self.app.log(f"\n   [⚠️ 정보] 목표 월파량을 만족하는 여유고(Rc = {initial_rc:.3f} m)가")
            self.app.log(f"             고다 도표 유효 범위(0.5 ~ 2.0 H0')를 벗어났습니다.")
            self.app.log(f"   ➔ 도표를 이용한 정밀 산정이 불가하여 'Takayama 근사식' 역산 결과로 대체합니다.")
            return initial_rc # 근사식 역산값 그대로 반환

        # 3. 도표 범위 내일 경우: 도표 보간 함수를 이용해 정밀 수렴
        self.app.log(f"\n   [💡 정보] 근사식 여유고(Rc = {initial_rc:.3f} m)가 도표 범위 내에 있습니다.")
        self.app.log(f"   ➔ 고다 도표 다중 보간을 통한 정밀 역산 수렴을 시작합니다.")
        
        # 탐색 범위를 도표 유효 범위(min_rc ~ max_rc)로 제한하여 역산 수행
        f_chart = lambda x: self.execute_goda_calc(H13, H0_prime, T, h, x, struct_type, verbose=False) - target_q
        
        try:
            final_rc = brentq_solver(f_chart, min_rc, max_rc)
            return final_rc
        except Exception as e:
            # 수렴 실패 시 안전장치
            self.app.log(f"\n   [⚠️ 오류] 도표 보간 역산 중 수렴에 실패하였습니다. 근사식 결과로 대체합니다.")
            return initial_rc

    def calculate_takayama_formula(self, h, hc, H0_prime):
        g = 9.81
        rel_h = max(h / H0_prime, 0.5)
        rel_hc = hc / H0_prime
        alpha = -0.12 * (rel_h ** 0.5)
        beta = -1.15 * (1.0 + 0.1 * rel_h)
        gamma = -1.82 + 0.15 * rel_h
        log_q_coef = alpha * (rel_hc ** 2) + beta * rel_hc + gamma
        Y_val = 10 ** log_q_coef
        return Y_val * math.sqrt(2 * g * (H0_prime ** 3))

    def val_to_x_px(self, row, x_val):
        if x_val <= row['x2_val']:
            ratio = (x_val - row['x1_val']) / (row['x2_val'] - row['x1_val'])
            return int(row['x1_px'] + ratio * (row['x2_px'] - row['x1_px']))
        else:
            log_min = math.log10(row['x3_val'])
            log_max = math.log10(row['x4_val'])
            if x_val <= 0: x_val = row['x3_val'] 
            ratio = (math.log10(x_val) - log_min) / (log_max - log_min)
            return int(row['x3_px'] + ratio * (row['x4_px'] - row['x3_px']))

    def val_to_y_px(self, row, y_val):
        y_min, y_max = row['y1_val'], row['y2_val']
        if y_val < y_min: y_val = y_min
        if y_val > y_max: y_val = y_max
        log_min, log_max = math.log10(y_min), math.log10(y_max)
        ratio = (math.log10(y_val) - log_min) / (log_max - log_min)
        return int(row['y1_py'] + ratio * (row['y2_py'] - row['y1_py']))

    def val_to_q_px(self, row, q_val):
        q_min = min(row['x5_val'], row['x6_val'])
        q_max = max(row['x5_val'], row['x6_val'])
        px_min = row['x6_px'] if q_min == row['x6_val'] else row['x5_px']
        px_max = row['x5_px'] if q_max == row['x5_val'] else row['x6_px']
        if q_val < q_min: q_val = q_min
        if q_val > q_max: q_val = q_max
        log_min, log_max = math.log10(q_min), math.log10(q_max)
        ratio = (math.log10(q_val) - log_min) / (log_max - log_min)
        return int(px_min + ratio * (px_max - px_min))

    def draw_goda_validation_chart(self, row, h_H0, q_calc, H0_prime, background_file):
        """ 💡 [요청 사항 반영] 이미지 내부 글자 및 텍스트 박스 전면 삭제 """
        if not os.path.exists(self.app.master_zip_path): return None
        try:
            with zipfile.ZipFile(self.app.master_zip_path, 'r') as archive:
                matched_files = [f for f in archive.namelist() if background_file.lower() in f.lower()]
                if not matched_files: return None
                img_bytes = archive.read(matched_files[0])
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception: return None

        draw = ImageDraw.Draw(img)
        g = 9.81
        Y_val = q_calc / math.sqrt(2 * g * (H0_prime ** 3))

        x_px = self.val_to_x_px(row, h_H0)
        y_px = self.val_to_y_px(row, Y_val)
        q_px = self.val_to_q_px(row, q_calc)
        axis_y_common = int(row['x1-4_py'])

        line_color = (255, 0, 0)
        target_color = (0, 0, 255)

        # 오직 십자선과 교차점(파란 점)만 도식
        draw.line([(x_px, y_px), (x_px, axis_y_common)], fill=line_color, width=3)
        draw.line([(x_px, y_px), (q_px, y_px)], fill=line_color, width=3)
        draw.line([(q_px, y_px), (q_px, axis_y_common)], fill=line_color, width=3)

        r = 6
        draw.ellipse([(x_px - r, y_px - r), (x_px + r, y_px + r)], fill=target_color)
        draw.ellipse([(q_px - r, y_px - r), (q_px + r, y_px + r)], fill=target_color)

        out_path = f"temp_{background_file.replace('.bmp', '.png')}"
        img.save(out_path)
        return out_path

    def popup_goda_window(self, q_calc, h_H0, hc_H0, H0_prime, wave_slope, bottom_slope, calc_method, chart_data_list):
        """ 💡 [요청 사항 반영] 상단 입력 조건 줄에 보간조건, 파형경사, 해저경사 정보 추가 표시 """
        if not chart_data_list: return
        pop = tk.Toplevel(self.app.root)
        pop.title("Goda 도표 월파량 산정 근거 삽도 (다중 보간 결과)")
        
        n_charts = len(chart_data_list)
        if n_charts == 1:
            pop.geometry("1000x750")
        elif n_charts == 2:
            pop.geometry("1300x750")
        else: 
            pop.geometry("1300x950")
            
        info_panel = ttk.Frame(pop, padding=10)
        info_panel.pack(fill=tk.X)
        
        # 💡 보간조건(산정방식명), 파형경사, 해저경사 분모를 포맷에 맞추어 한 문장으로 결합
        main_guide = (
            f"■ [최종 결과] 도표의 다중 Log보간을 통해 산정한 월파량(q) : {q_calc:.6f} m³/m·s\n"
            f"  - 입력 조건 : 수심비 h/H₀': {h_H0:.3f} | 여유고비 R_c/H₀': {hc_H0:.3f} | 환산심해파고 H₀': {H0_prime:.3f} m\n"
            f"  - 보간 조건 : 파형경사 H₀'/L₀: {wave_slope:.4f} | 해저경사: 1/{bottom_slope:.1f}"
        )
        ttk.Label(info_panel, text=main_guide, font=("맑은 고딕", 10, "bold"), foreground="blue", justify=tk.LEFT).pack(side=tk.LEFT)
        
        main_frame = ttk.Frame(pop)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        cols = 2 if n_charts > 1 else 1
        rows = 2 if n_charts > 2 else 1
        
        for i in range(cols): main_frame.columnconfigure(i, weight=1, uniform="col")
        for i in range(rows): main_frame.rowconfigure(i, weight=1, uniform="row")
            
        for i, data in enumerate(chart_data_list):
            r = i // cols
            c = i % cols
            
            sub_frame = ttk.Frame(main_frame, borderwidth=2, relief="groove", padding=5)
            sub_frame.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            
            b_val = data['bottom']
            w_val = data['wave']
            q_val = data['q_val']
            w_b = data['weight_b'] * 100
            w_w = data['weight_w'] * 100
            
            data_spec_text = (
                f"▶ [산정 근거] : 1. 도표({i+1}) 해저경사 1/{b_val} , 파형경사 {w_val:.3f}\n"
                f"                   2. 도표 단독 산출 월파량 : {q_val:.6f} m³/m·s\n"
                f"                   3. 반영 비중 : 해저경사({w_b:.1f}%) × 파형경사({w_w:.1f}%)"
            )
            spec_lbl = ttk.Label(sub_frame, text=data_spec_text, font=("맑은 고딕", 10, "bold"), justify=tk.LEFT, padding=5)
            spec_lbl.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
            
            opened = Image.open(data['path'])
            lbl = tk.Label(sub_frame)
            lbl.pack(fill=tk.BOTH, expand=True)
            
            def make_resizer(img_obj, target_lbl):
                def on_resize(event):
                    w, h = event.width, event.height
                    h_bound = max(h - 40, 10) 
                    if w > 10 and h_bound > 10:
                        resized = img_obj.copy()
                        try: resized.thumbnail((w, h_bound), Image.Resampling.LANCZOS)
                        except AttributeError: resized.thumbnail((w, h_bound), Image.ANTIALIAS)
                        tk_img = ImageTk.PhotoImage(resized)
                        target_lbl.config(image=tk_img)
                        target_lbl.image = tk_img
                return on_resize
                
            sub_frame.bind("<Configure>", make_resizer(opened, lbl))

    def execute_goda_calc(self, H13, H0_prime, T, h, Rc, struct_type, verbose=True):
        g = 9.81
        L0 = (g * (T ** 2)) / (2 * math.pi)
        wave_slope_calc = H0_prime / L0
        rel_h = h / H0_prime
        rel_hc = Rc / H0_prime
        
        q_takayama = self.calculate_takayama_formula(h, Rc, H0_prime)
        struct_code = 'v' if "직립" in struct_type else 's'
        
        try:
            bottom_slope_val = float(self.app.cbo_slope.get().strip().replace("1/", ""))
        except Exception:
            bottom_slope_val = 30.0

        standard_bottoms = [10, 30]
        if bottom_slope_val <= standard_bottoms[0]:
            bottom_lo = bottom_hi = standard_bottoms[0]
            factor_bottom = 0.0
        elif bottom_slope_val >= standard_bottoms[-1]:
            bottom_lo = bottom_hi = standard_bottoms[-1]
            factor_bottom = 1.0
        else:
            bottom_lo = standard_bottoms[0]
            bottom_hi = standard_bottoms[-1]
            factor_bottom = (bottom_slope_val - bottom_lo) / (bottom_hi - bottom_lo)

        standard_waves = [0.012, 0.017, 0.036]
        if wave_slope_calc <= standard_waves[0]:
            wave_lo = wave_hi = standard_waves[0]
            factor_wave = 0.0
        elif wave_slope_calc >= standard_waves[-1]:
            wave_lo = wave_hi = standard_waves[-1]
            factor_wave = 1.0
        else:
            for i in range(len(standard_waves)-1):
                if standard_waves[i] <= wave_slope_calc <= standard_waves[i+1]:
                    wave_lo = standard_waves[i]
                    wave_hi = standard_waves[i+1]
                    factor_wave = (wave_slope_calc - wave_lo) / (wave_hi - wave_lo)
                    break

        def get_chart_Y(b_val, w_val):
            w_str = f"{w_val:.3f}".replace(".", "")
            f_key = f"{struct_code}_1_{int(b_val)}_{w_str}".lower()
            return self.get_Y_from_chart(f_key, rel_h, rel_hc), f_key

        Y_b10_wLo, f_b10_wLo = get_chart_Y(10, wave_lo)
        Y_b10_wHi, f_b10_wHi = get_chart_Y(10, wave_hi)
        Y_b30_wLo, f_b30_wLo = get_chart_Y(30, wave_lo)
        Y_b30_wHi, f_b30_wHi = get_chart_Y(30, wave_hi)

        q_goda_final = 0.0
        calc_method = ""
        chart_data_list = [] 
        
        if all(y is not None for y in [Y_b10_wLo, Y_b10_wHi, Y_b30_wLo, Y_b30_wHi]):
            Y_10_final = 0.0
            if Y_b10_wLo > 0 and Y_b10_wHi > 0:
                lY_10 = math.log10(Y_b10_wLo) + factor_wave * (math.log10(Y_b10_wHi) - math.log10(Y_b10_wLo))
                Y_10_final = 10 ** lY_10

            Y_30_final = 0.0
            if Y_b30_wLo > 0 and Y_b30_wHi > 0:
                lY_30 = math.log10(Y_b30_wLo) + factor_wave * (math.log10(Y_b30_wHi) - math.log10(Y_b30_wLo))
                Y_30_final = 10 ** lY_30

            Y_final = 0.0
            if Y_10_final > 0 and Y_30_final > 0:
                lY_final = math.log10(Y_10_final) + factor_bottom * (math.log10(Y_30_final) - math.log10(Y_10_final))
                Y_final = 10 ** lY_final
            elif Y_10_final > 0: Y_final = Y_10_final
            elif Y_30_final > 0: Y_final = Y_30_final

            q_goda_final = Y_final * math.sqrt(2 * g * (H0_prime ** 3))
            calc_method = "데이터 도표 기반 다차원 보간"

            if self.app.config_df is not None:
                inc_b10 = (factor_bottom < 1.0)
                inc_b30 = (factor_bottom > 0.0)
                inc_wLo = (factor_wave < 1.0)
                inc_wHi = (factor_wave > 0.0)

                def add_chart(b_val, w_val, f_key, y_val, w_b, w_w):
                    rows = self.app.config_df[self.app.config_df['file_name'] == f"{f_key}.bmp"]
                    if not rows.empty and y_val > 0:
                        q_val = y_val * math.sqrt(2 * g * (H0_prime ** 3))
                        p = self.draw_goda_validation_chart(rows.iloc[0], rel_h, q_val, H0_prime, f"{f_key}.bmp")
                        if p:
                            chart_data_list.append({
                                'path': p, 'bottom': b_val, 'wave': w_val, 
                                'q_val': q_val, 'weight_b': w_b, 'weight_w': w_w
                            })

                if inc_b10 and inc_wLo: add_chart(10, wave_lo, f_b10_wLo, Y_b10_wLo, 1-factor_bottom, 1-factor_wave)
                if inc_b10 and inc_wHi: add_chart(10, wave_hi, f_b10_wHi, Y_b10_wHi, 1-factor_bottom, factor_wave)
                if inc_b30 and inc_wLo: add_chart(30, wave_lo, f_b30_wLo, Y_b30_wLo, factor_bottom, 1-factor_wave)
                if inc_b30 and inc_wHi: add_chart(30, wave_hi, f_b30_wHi, Y_b30_wHi, factor_bottom, factor_wave)
        else:
            q_goda_final = q_takayama
            calc_method = "Takayama(1992) 근사식 적용"

        if verbose:
            self.app.log_header("④ 일본 항만 설계 기준(Goda 식) 실계산 과정")
            self.app.log(f"   ● [쇄파변형 고려 역산] 입력 유의파고(H1/3): {H13} m ➔ 환산심해파고(H0'): {H0_prime:.3f} m")
            self.app.log(f"   - 외해 심해 파장 (L₀)   : {L0:.2f} m")
            self.app.log(f"   - 계산된 실 파형경사    : {wave_slope_calc:.4f}")
            self.app.log(f"   - 설계 해저경사         : 1 / {bottom_slope_val:.1f}")
            self.app.log(f"   - 수심비 (h/H0')        : {rel_h:.3f}")
            self.app.log(f"   - 여유고비 (Rc/H0')     : {rel_hc:.3f}")
            
            self.app.log(f"   \n   ● [최종 산정] 기준서 원본 도표 다중 보간 결과")
            self.app.log(f"   - 산정 방식: {calc_method}")
            
            if chart_data_list:
                for idx, c_data in enumerate(chart_data_list):
                    self.app.log(f"   - [도표 {idx+1}] 해저 1/{c_data['bottom']}, 파형 {c_data['wave']:.3f} ➔ 산출치: {c_data['q_val']:.6f}")
                    
                # 💡 [수정 포인트] 확장된 변수(wave_slope_calc, bottom_slope_val, calc_method)들을 팝업창 인자로 함께 넘겨줍니다.
                self.popup_goda_window(q_goda_final, rel_h, rel_hc, H0_prime, wave_slope_calc, bottom_slope_val, calc_method, chart_data_list)
                            
            self.app.log(f"   ➔ 단위 폭당 평균 월파 유량(q) = {q_goda_final:.6f} m³/m·s")
            
        return q_goda_final

if __name__ == "__main__":
    root = tk.Tk()
    app = OvertoppingApp(root)
    goda_plug = GodaExtensionModule(app)
    root.mainloop()