#!/usr/bin/env python3
# Fedora Wifi Sound Link - Modern Responsive GUI + Bluetooth
# Compact, dark, icon réelle, tabs WiFi/Bluetooth, responsive
import customtkinter as ctk
import tkinter as tk
from pathlib import Path
import subprocess, threading, re, time, shlex, sys
import concurrent.futures
from PIL import Image

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_STREAM = PROJECT_DIR / "src" / "stream"
PC_STREAM = SRC_STREAM / "pc_sender.sh"
RPI_RECEIVE = SRC_STREAM / "rpi_receiver.sh"
BT_RPI = SRC_STREAM / "bluetooth" / "rpi_bt_sink.sh"
BT_PC = SRC_STREAM / "bluetooth" / "pc_bt_connect.sh"
ASSETS = PROJECT_DIR / "assets"
ICON = ASSETS / "icon-256.png"

DEFAULT_PI_IP = "192.168.1.101"
DEFAULT_PI_MAC = "2C:CF:67:00:AC:EE"
DEFAULT_USER = "timo"
DEFAULT_PASS = "1010"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def get_pc_ip():
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True)
        return out.strip().split()[0]
    except:
        return "192.168.1.108"

def run_cmd(cmd, timeout=5):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.stdout + res.stderr, res.returncode
    except subprocess.TimeoutExpired:
        return "timeout", 1
    except Exception as e:
        return str(e), 1

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.pc_ip = get_pc_ip()
        self.title("Fedora Wifi Sound Link")
        # Responsive: petite taille initiale mais resizable, minsize compact
        self.geometry("540x780")
        self.minsize(380, 600)
        # Allow resizing - responsive
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # icon
        try:
            if ICON.exists():
                img = Image.open(ICON)
                self.icon_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28,28))
                self.icon_img_small = ctk.CTkImage(light_image=img, dark_image=img, size=(20,20))
            else:
                self.icon_img = None
        except:
            self.icon_img = None
        try:
            if (ASSETS/"icon.png").exists():
                pil = Image.open(ASSETS/"icon.png")
                self.tk_icon = tk.PhotoImage(file=str(ASSETS/"icon.png"))
                self.iconphoto(True, self.tk_icon)
        except: pass

        self.bg = "#0f1115"
        self.card_bg = "#1a1d24"
        self.card_border = "#2a2e39"
        self.accent = "#7c5cff"
        self.accent2 = "#00d9ff"
        self.configure(fg_color=self.bg)

        # Main container with grid for responsiveness
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        # Header fixed
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12,6))
        header.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        if self.icon_img:
            ctk.CTkLabel(left, image=self.icon_img, text="").pack(side="left", padx=(0,10))
        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="FEDORA WIFI SOUND LINK", font=ctk.CTkFont(size=12, weight="bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"PC {self.pc_ip} → KRK", font=ctk.CTkFont(size=10), text_color="#8b8fa3").pack(anchor="w")
        self.status_dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=16), text_color="#ff3b30")
        self.status_dot.grid(row=0, column=1, padx=4, sticky="e")
        self.status_txt = ctk.CTkLabel(header, text="déconnecté", font=ctk.CTkFont(size=11), text_color="#8b8fa3")
        self.status_txt.grid(row=0, column=2, padx=2, sticky="e")

        # Scrollable content for responsiveness
        self.scroll = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", scrollbar_button_color="#252836", scrollbar_button_hover_color="#2a2e39")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Transport Tabs - WiFi / Bluetooth
        self.tabview = ctk.CTkTabview(self.scroll, width=500, height=320, fg_color=self.card_bg, segmented_button_fg_color="#0f1115", segmented_button_selected_color=self.accent, segmented_button_unselected_color="#252836", segmented_button_selected_hover_color="#6b4feb", text_color="white", corner_radius=14, border_width=1, border_color=self.card_border)
        self.tabview.pack(fill="x", padx=16, pady=6, expand=False)
        self.tabview.add("WiFi")
        self.tabview.add("Bluetooth")
        # Set WiFi as default, but allow Bluetooth
        self.tabview.set("WiFi")

        # --- WiFi Tab ---
        wifi = self.tabview.tab("WiFi")
        wifi.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(wifi, text="WIFI  •  RTP/UDP  •  ROC/FEC", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=8, pady=(6,2))
        # Pi IP row responsive with grid
        row1 = ctk.CTkFrame(wifi, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=4)
        row1.grid_columnconfigure(0, weight=1)
        self.pi_ip_var = ctk.StringVar(value=DEFAULT_PI_IP)
        self.pi_entry = ctk.CTkEntry(row1, placeholder_text="192.168.1.101", textvariable=self.pi_ip_var, corner_radius=8, border_color=self.card_border, fg_color="#0f1115")
        self.pi_entry.grid(row=0, column=0, sticky="ew", padx=2)
        self.user_var = ctk.StringVar(value=DEFAULT_USER)
        e2 = ctk.CTkEntry(row1, width=70, placeholder_text="user", textvariable=self.user_var, corner_radius=8, border_color=self.card_border, fg_color="#0f1115")
        e2.grid(row=0, column=1, padx=2)
        self.pass_var = ctk.StringVar(value=DEFAULT_PASS)
        e3 = ctk.CTkEntry(row1, width=80, placeholder_text="pass", textvariable=self.pass_var, show="*", corner_radius=8, border_color=self.card_border, fg_color="#0f1115")
        e3.grid(row=0, column=2, padx=2)
        self.scan_btn = ctk.CTkButton(row1, text="Scan", width=60, height=28, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.scan_network, font=ctk.CTkFont(size=11))
        self.scan_btn.grid(row=0, column=3, padx=2)

        row2 = ctk.CTkFrame(wifi, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=2)
        self.test_btn = ctk.CTkButton(row2, text="Tester SSH", width=90, height=26, corner_radius=8, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.test_ssh, font=ctk.CTkFont(size=11))
        self.test_btn.pack(side="left", padx=2)
        self.pi_state = ctk.CTkLabel(row2, text="non testé", font=ctk.CTkFont(size=11), text_color="#8b8fa3")
        self.pi_state.pack(side="left", padx=8)
        self.scan_list_frame = ctk.CTkScrollableFrame(wifi, height=70, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
        self.scan_list_frame.pack(fill="x", padx=8, pady=(4,6))
        ctk.CTkLabel(self.scan_list_frame, text="Scan pour détecter le Pi AudioBox", font=ctk.CTkFont(size=11), text_color="#5a5e73").pack(pady=12)

        # --- Bluetooth Tab ---
        bt = self.tabview.tab("Bluetooth")
        bt.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bt, text="BLUETOOTH  •  A2DP  •  Pi comme enceinte", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=8, pady=(6,2))
        ctk.CTkLabel(bt, text="Le Pi devient une enceinte Bluetooth. Le son du PC sortira sur les KRK via BT.", font=ctk.CTkFont(size=9), text_color="#5a5e73", wraplength=460).pack(anchor="w", padx=8)
        b_row1 = ctk.CTkFrame(bt, fg_color="transparent")
        b_row1.pack(fill="x", padx=8, pady=6)
        b_row1.grid_columnconfigure(0, weight=1)
        self.bt_mac_var = ctk.StringVar(value=DEFAULT_PI_MAC)
        ctk.CTkLabel(b_row1, text="MAC Pi:").grid(row=0, column=0, padx=2)
        self.bt_mac_entry = ctk.CTkEntry(b_row1, textvariable=self.bt_mac_var, width=140, corner_radius=8, border_color=self.card_border, fg_color="#0f1115", placeholder_text="2C:CF:67:00:AC:EE")
        self.bt_mac_entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.bt_scan_btn = ctk.CTkButton(b_row1, text="Scan BT", width=80, height=28, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.scan_bluetooth, font=ctk.CTkFont(size=11))
        self.bt_scan_btn.grid(row=0, column=2, padx=4)
        self.bt_power_btn = ctk.CTkButton(b_row1, text="Power ON", width=80, height=28, corner_radius=8, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.bt_power, font=ctk.CTkFont(size=11))
        self.bt_power_btn.grid(row=0, column=3, padx=2)

        b_row2 = ctk.CTkFrame(bt, fg_color="transparent")
        b_row2.pack(fill="x", padx=8, pady=4)
        self.bt_connect_btn = ctk.CTkButton(b_row2, text="Pair + Connect", height=28, corner_radius=8, fg_color=self.accent2, text_color="#0f1115", hover_color="#00c4e6", command=self.bt_connect, font=ctk.CTkFont(size=11, weight="bold"))
        self.bt_connect_btn.pack(side="left", padx=2, fill="x", expand=True)
        self.bt_disconnect_btn = ctk.CTkButton(b_row2, text="Disconnect", width=90, height=28, corner_radius=8, fg_color="#1a1d24", border_width=1, border_color=self.card_border, command=self.bt_disconnect, font=ctk.CTkFont(size=11))
        self.bt_disconnect_btn.pack(side="left", padx=4)
        self.bt_status = ctk.CTkLabel(b_row2, text="BT non testé", font=ctk.CTkFont(size=11), text_color="#8b8fa3")
        self.bt_status.pack(side="left", padx=6)

        self.bt_list_frame = ctk.CTkScrollableFrame(bt, height=80, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
        self.bt_list_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(self.bt_list_frame, text="Scan BT pour trouver raspberrypi", font=ctk.CTkFont(size=11), text_color="#5a5e73").pack(pady=12)
        # BT status line
        self.bt_info = ctk.CTkLabel(bt, text="Pi: discoverable ? • PC: powered ?", font=ctk.CTkFont(size=9), text_color="#5a5e73")
        self.bt_info.pack(anchor="w", padx=8, pady=2)

        # Mode card responsive
        mode_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        mode_card.pack(fill="x", padx=16, pady=6)
        mode_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mode_card, text="MODE STREAMING", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=14, pady=(10,4))
        self.preset_var = ctk.StringVar(value="pcm_stable")
        presets = [
            ("PCM Stable — RECOMMANDÉ", "pcm_stable", "Lossless • 600ms • stable wifi pourri", "#00d9ff"),
            ("Opus Stable", "opus_stable", "Opus 192k • 8x moins de bande • transparent", "#7c5cff"),
            ("PCM Fast", "pcm_fast", "Low latency 60ms • saccades si wifi pourri", "#5a5e73"),
            ("ROC Stable (beta)", "roc_stable", "Roc + FEC • 300ms • expérimental", "#ff3b30"),
        ]
        self.preset_frames = {}
        for title, val, desc, color in presets:
            f = ctk.CTkFrame(mode_card, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
            f.pack(fill="x", padx=12, pady=3)
            f.bind("<Button-1>", lambda e, v=val: self.select_preset(v))
            rb = ctk.CTkRadioButton(f, text="", variable=self.preset_var, value=val, radiobutton_width=16, radiobutton_height=16, border_width_checked=5, fg_color=self.accent, hover_color="#5a4bd1", command=lambda: self.update_preset_ui())
            rb.pack(side="left", padx=10, pady=10)
            txt = ctk.CTkFrame(f, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, pady=6)
            txt.bind("<Button-1>", lambda e, v=val: self.select_preset(v))
            ctk.CTkLabel(txt, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="white").pack(anchor="w")
            ctk.CTkLabel(txt, text=desc, font=ctk.CTkFont(size=9), text_color="#8b8fa3").pack(anchor="w")
            dot = ctk.CTkLabel(f, text="●", font=ctk.CTkFont(size=10), text_color=color)
            dot.pack(side="right", padx=10)
            self.preset_frames[val] = f
        self.update_preset_ui()

        # Control card responsive
        ctrl = ctk.CTkFrame(self.scroll, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=8)
        ctrl.grid_columnconfigure(0, weight=1)
        self.connect_btn = ctk.CTkButton(ctrl, text="▶  CONNECTER WIFI", height=42, corner_radius=10, fg_color=self.accent, hover_color="#6b4feb", font=ctk.CTkFont(size=13, weight="bold"), command=self.connect)
        self.connect_btn.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.stop_btn = ctk.CTkButton(ctrl, text="■", width=48, height=42, corner_radius=10, fg_color="#1a1d24", border_width=1, border_color=self.card_border, hover_color="#252836", font=ctk.CTkFont(size=16), command=self.disconnect)
        self.stop_btn.grid(row=0, column=1, padx=2)
        self.tone_btn = ctk.CTkButton(ctrl, text="♪", width=48, height=42, corner_radius=10, fg_color="#1a1d24", border_width=1, border_color=self.card_border, hover_color="#252836", font=ctk.CTkFont(size=16), command=self.test_tone)
        self.tone_btn.grid(row=0, column=2, padx=(4,0))

        # Volume card responsive
        vol_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        vol_card.pack(fill="x", padx=16, pady=4)
        vol_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(vol_card, text="VOLUME KRK", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=14, pady=(8,2))
        vol_row = ctk.CTkFrame(vol_card, fg_color="transparent")
        vol_row.pack(fill="x", padx=12, pady=(2,4))
        vol_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(vol_row, text="◂", text_color="#5a5e73").grid(row=0, column=0)
        self.vol_var = tk.IntVar(value=40)
        self.vol_slider = ctk.CTkSlider(vol_row, from_=0, to=100, variable=self.vol_var, height=16, button_color=self.accent, button_hover_color="#6b4feb", progress_color=self.accent, fg_color="#2a2e39", command=self.on_vol_drag)
        self.vol_slider.grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkLabel(vol_row, text="▸", text_color="#5a5e73").grid(row=0, column=2)
        self.vol_label = ctk.CTkLabel(vol_row, text="40%", font=ctk.CTkFont(size=12, weight="bold"), text_color="white", width=45)
        self.vol_label.grid(row=0, column=3, padx=4)
        self.vol_apply = ctk.CTkButton(vol_row, text="OK", width=40, height=26, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.apply_volume, font=ctk.CTkFont(size=11))
        self.vol_apply.grid(row=0, column=4, padx=2)
        self.vu_canvas = tk.Canvas(vol_card, height=18, bg="#0f1115", highlightthickness=0)
        self.vu_canvas.pack(fill="x", padx=14, pady=(0,8))
        self.draw_vu(0)
        # Make VU responsive on resize
        self.bind("<Configure>", lambda e: self.draw_vu(0.02))

        # Logs responsive expand
        log_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        log_card.pack(fill="both", expand=True, padx=16, pady=(4,10))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)
        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.grid(row=0, column=0, sticky="ew", padx=12, pady=6)
        log_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_head, text="LOGS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").grid(row=0, column=0, sticky="w")
        self.log_btn = ctk.CTkButton(log_head, text="↻", width=30, height=22, corner_radius=6, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.refresh_logs, font=ctk.CTkFont(size=12))
        self.log_btn.grid(row=0, column=2, padx=2)
        ctk.CTkButton(log_head, text="clear", width=45, height=22, corner_radius=6, fg_color="transparent", border_width=1, border_color=self.card_border, command=lambda: self.log.delete("1.0","end"), font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=2)
        self.log = ctk.CTkTextbox(log_card, height=120, font=ctk.CTkFont(family="Monospace", size=11), fg_color="#0f1115", border_width=0, text_color="#a8adc3")
        self.log.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

        # footer inside scroll for responsiveness
        footer = ctk.CTkLabel(self.scroll, text="Fedora Wifi Sound Link  •  github.com/stxtxm/fedora-wifi-sound-link  •  WiFi + Bluetooth", font=ctk.CTkFont(size=9), text_color="#5a5e73")
        footer.pack(pady=(4,10))

        self.after(800, self.fetch_volume)
        self.after(1500, self.auto_status)
        self.after(100, self.vu_animate)
        self.after(1000, self.update_bt_info)
        self.log_msg(f"Prêt. PC {self.pc_ip} — Responsive • WiFi + Bluetooth")
        self.log_msg("WiFi: PCM Stable recommandé • Bluetooth: appaire le Pi comme enceinte")

    def select_preset(self, val):
        self.preset_var.set(val)
        self.update_preset_ui()
    def update_preset_ui(self):
        sel = self.preset_var.get()
        for k, f in self.preset_frames.items():
            f.configure(border_color=self.accent if k==sel else self.card_border, border_width=2 if k==sel else 1)

    def draw_vu(self, level):
        try:
            self.vu_canvas.delete("all")
            w = self.vu_canvas.winfo_width() or self.vu_canvas.winfo_reqwidth() or 480
            if w < 10: w = 480
            self.vu_canvas.create_rectangle(0,4,w,14, fill="#2a2e39", outline="", width=0)
            lv = int(w * min(max(level,0),1))
            if lv>0:
                self.vu_canvas.create_rectangle(0,4,lv,14, fill=self.accent, outline="")
                if level>0.85:
                    self.vu_canvas.create_rectangle(lv-3,2,lv,16, fill="#ff3b30", outline="")
            for i in range(5):
                x = int(w * i/4)
                self.vu_canvas.create_line(x,4,x,14, fill="#0f1115", width=1)
        except: pass

    def vu_animate(self):
        import random, math
        try:
            if "connecté" in self.status_txt.cget("text"):
                lvl = 0.15 + 0.3*abs(math.sin(time.time()*3)) + random.random()*0.15
                self.draw_vu(lvl)
            else:
                self.draw_vu(0.02 + 0.02*math.sin(time.time()*1.5))
        except: pass
        self.after(80, self.vu_animate)

    def log_msg(self, m):
        self.log.insert("end", m+"\n")
        self.log.see("end")
        print(m)

    def get_preset(self):
        p=self.preset_var.get()
        if p=="roc_stable": return ("roc","stable")
        if p=="opus_stable": return ("opus","stable")
        if p=="pcm_stable": return ("pcm","stable")
        return ("pcm","fast")

    # WiFi methods (same as before, compact)
    def scan_network(self):
        self.scan_btn.configure(state="disabled", text="...")
        for w in self.scan_list_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.scan_list_frame, text="Scan 192.168.1.0/24 ...", text_color="#8b8fa3").pack(pady=10)
        def do():
            base="192.168.1."
            def ping(ip):
                try:
                    subprocess.run(["ping","-c","1","-W","1",ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
                    return ip
                except: return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
                futs={ex.submit(ping, f"{base}{i}"):i for i in range(1,255)}
                reachable=[]
                for f in concurrent.futures.as_completed(futs):
                    r=f.result()
                    if r: reachable.append(r)
            self.log_msg(f"{len(reachable)} hôtes")
            found=False
            for ip in sorted(reachable, key=lambda x: int(x.split('.')[-1])):
                user=self.user_var.get().strip(); pwd=self.pass_var.get()
                out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 {user}@{ip} \"hostname; aplay -l 2>&1 | grep -i AudioBox; wpctl status 2>&1 | grep -i AudioBox\" 2>&1", timeout=4)
                if "AudioBox" in out:
                    found=True
                    self.log_msg(f"✓ {ip} AudioBox")
                    def make_btn(ip=ip):
                        b=ctk.CTkButton(self.scan_list_frame, text=f"{ip}  •  AudioBox KRK  ✓", height=28, corner_radius=8, fg_color="#1a1d24", border_width=1, border_color=self.accent, hover_color="#252836", command=lambda ip=ip: (self.pi_ip_var.set(ip), self.log_msg(f"IP {ip} sélectionnée")))
                        b.pack(fill="x", pady=2, padx=4)
                    self.after(0, make_btn)
                elif "raspberry" in out.lower():
                    self.log_msg(f"· {ip} raspberry sans AudioBox")
            if not found:
                self.after(0, lambda: ctk.CTkLabel(self.scan_list_frame, text="Aucun Pi AudioBox — vérifie USB", text_color="#ff3b30").pack())
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="Scan"))
            try:
                for w in list(self.scan_list_frame.winfo_children()):
                    if isinstance(w, ctk.CTkLabel) and "Scan 192" in w.cget("text"):
                        w.destroy()
            except: pass
        threading.Thread(target=do, daemon=True).start()

    def test_ssh(self):
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg(f"Test {user}@{ip} ...")
        def do():
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 {user}@{ip} \"hostname; whoami; pactl info 2>&1 | head -3; aplay -l 2>&1 | grep AudioBox; wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1\" 2>&1", timeout=5)
            self.log_msg(out)
            if "AudioBox" in out or "PulseAudio" in out:
                self.pi_state.configure(text="● connecté", text_color="#00d68f")
                m=re.search(r"Volume:\s*([\d\.]+)", out)
                if m:
                    try:
                        v=float(m.group(1))*100
                        self.vol_var.set(int(v)); self.vol_label.configure(text=f"{int(v)}%")
                    except: pass
            else:
                self.pi_state.configure(text="● échec", text_color="#ff3b30")
        threading.Thread(target=do, daemon=True).start()

    def fetch_volume(self):
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        def do():
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1\" 2>&1", timeout=3)
            m=re.search(r"Volume:\s*([\d\.]+)", out)
            if m:
                try:
                    v=float(m.group(1))*100
                    self.after(0, lambda: (self.vol_var.set(int(v)), self.vol_label.configure(text=f"{int(v)}%")))
                except: pass
        threading.Thread(target=do, daemon=True).start()

    def on_vol_drag(self, v):
        self.vol_label.configure(text=f"{int(float(v))}%")
    def apply_volume(self):
        v=self.vol_var.get(); frac=v/100.0
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg(f"Volume {v}%")
        def do():
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"wpctl set-volume @DEFAULT_AUDIO_SINK@ {frac:.2f}; wpctl get-volume @DEFAULT_AUDIO_SINK@\" 2>&1", timeout=3)
            self.log_msg(out.strip())
        threading.Thread(target=do, daemon=True).start()

    # Bluetooth methods
    def update_bt_info(self):
        def do():
            out,_=run_cmd("bluetoothctl show 2>&1 | grep -E 'Powered|Name' | head -5", timeout=2)
            out2,_=run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"bluetoothctl show 2>&1 | grep -E 'Powered|Discoverable|Pairable' | head -5\" 2>&1", timeout=3)
            self.after(0, lambda: self.bt_info.configure(text=f"PC: {'ON' if 'Powered: yes' in out else 'OFF'} • Pi: {'discoverable' if 'Discoverable: yes' in out2 else 'off'} | {self.bt_mac_var.get()}"))
        threading.Thread(target=do, daemon=True).start()
        self.after(5000, self.update_bt_info)

    def bt_power(self):
        self.log_msg("Bluetooth power ON + Pi discoverable ON")
        def do():
            out,_=run_cmd("rfkill unblock bluetooth; bluetoothctl power on 2>&1 | head -5; bluetoothctl show 2>&1 | grep Powered", timeout=4)
            self.log_msg(out)
            ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} discoverable 2>&1 | head -10; {shlex.quote(str(BT_RPI))} status 2>&1 | head -20\" 2>&1", timeout=5)
            self.log_msg(out2)
            self.after(0, self.update_bt_info)
        threading.Thread(target=do, daemon=True).start()

    def scan_bluetooth(self):
        self.bt_scan_btn.configure(state="disabled", text="...")
        for w in self.bt_list_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.bt_list_frame, text="Scan Bluetooth 8s...", text_color="#8b8fa3").pack(pady=10)
        def do():
            self.log_msg("Scan BT 8s...")
            # Use bluetoothctl scan
            out,_=run_cmd("timeout 9 bash -c 'bluetoothctl scan on 2>&1 & pid=$!; sleep 8; bluetoothctl scan off 2>&1 | head -5; wait $pid 2>/dev/null; bluetoothctl devices 2>&1' 2>&1", timeout=12)
            self.log_msg(out[:800])
            # Parse devices
            found=False
            for line in out.splitlines():
                m=re.search(r"Device\s+([0-9A-F:]{17})\s+(.+)", line, re.I)
                if m:
                    mac=m.group(1); name=m.group(2)
                    found=True
                    is_pi = "raspberry" in name.lower() or mac.upper()==self.bt_mac_var.get().upper()
                    txt=f"{mac}  •  {name} {'✓ Pi' if is_pi else ''}"
                    col=self.accent if is_pi else self.card_border
                    def make(mac=mac):
                        b=ctk.CTkButton(self.bt_list_frame, text=txt, height=28, corner_radius=8, fg_color="#1a1d24", border_width=1, border_color=col, hover_color="#252836", command=lambda mac=mac: (self.bt_mac_var.set(mac), self.log_msg(f"MAC {mac} sélectionnée")))
                        b.pack(fill="x", pady=2, padx=4)
                    self.after(0, make)
            # Also try direct RPi MAC
            if not found:
                self.log_msg("Aucun device BT trouvé, vérifie Pi discoverable")
                self.after(0, lambda: ctk.CTkLabel(self.bt_list_frame, text="Aucun device — Pi discoverable ON ?", text_color="#ff3b30").pack())
            # Clear scanning label
            try:
                for w in list(self.bt_list_frame.winfo_children()):
                    if isinstance(w, ctk.CTkLabel) and "Scan Bluetooth" in w.cget("text"):
                        w.destroy()
            except: pass
            self.after(0, lambda: self.bt_scan_btn.configure(state="normal", text="Scan BT"))
        threading.Thread(target=do, daemon=True).start()

    def bt_connect(self):
        mac=self.bt_mac_var.get().strip()
        if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac, re.I):
            self.log_msg(f"MAC invalide: {mac}")
            return
        self.log_msg(f"BT Pair+Connect {mac} (A2DP Sink)...")
        self.bt_connect_btn.configure(state="disabled", text="...")
        def do():
            # Ensure Pi discoverable
            ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} setup 2>&1 | tail -10\" 2>&1", timeout=6)
            self.log_msg(out)
            # PC side: pair, trust, connect
            for step in [
                f"bluetoothctl pair {mac} 2>&1 | tail -10",
                f"bluetoothctl trust {mac} 2>&1 | tail -5",
                f"bluetoothctl connect {mac} 2>&1 | tail -20",
            ]:
                out,_=run_cmd(step, timeout=10)
                self.log_msg(out)
                time.sleep(1)
            # Check sink
            out,_=run_cmd("pactl list short sinks 2>&1 | grep bluez | head -5; pactl info 2>&1 | grep 'Default Sink'", timeout=3)
            self.log_msg(out)
            if "bluez" in out.lower():
                # Set default sink to BT
                m=re.search(r"(bluez_output\.[^\s]+)", out)
                if m:
                    sink=m.group(1)
                    run_cmd(f"pactl set-default-sink {shlex.quote(sink)} 2>&1", timeout=2)
                    self.log_msg(f"Default sink -> {sink} (PC audio vers Pi)")
                    self.bt_status.configure(text="● BT connecté", text_color="#00d68f")
                    self.status_dot.configure(text_color="#00d68f"); self.status_txt.configure(text="BT connecté ✓")
                else:
                    self.bt_status.configure(text="● connect partiel", text_color="#ff9f0a")
            else:
                self.bt_status.configure(text="● BT échec", text_color="#ff3b30")
                self.log_msg("Pas de sink bluez, vérifie appairage Pi")
            # Route on Pi side if needed
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} route 2>&1 | tail -10; {shlex.quote(str(BT_RPI))} status 2>&1 | head -20\" 2>&1", timeout=5)
            self.log_msg(out2)
            self.after(0, lambda: self.bt_connect_btn.configure(state="normal", text="Pair + Connect"))
        threading.Thread(target=do, daemon=True).start()

    def bt_disconnect(self):
        mac=self.bt_mac_var.get().strip()
        self.log_msg(f"BT Disconnect {mac}")
        def do():
            out,_=run_cmd(f"bluetoothctl disconnect {mac} 2>&1 | tail -10", timeout=5)
            self.log_msg(out)
            self.bt_status.configure(text="● BT déconnecté", text_color="#8b8fa3")
            self.status_dot.configure(text_color="#ff3b30"); self.status_txt.configure(text="déconnecté")
        threading.Thread(target=do, daemon=True).start()

    def connect(self):
        codec, mode = self.get_preset()
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get(); pc_ip=self.pc_ip
        # If Bluetooth tab active, do BT connect instead?
        current = self.tabview.get()
        if current == "Bluetooth":
            self.bt_connect()
            return
        self.log_msg(f"CONNECT {codec}/{mode} {pc_ip} -> {ip}:4711")
        self.connect_btn.configure(state="disabled", text="Connexion...")
        def do():
            run_cmd("pkill -9 ffmpeg; pkill -9 roc-send 2>/dev/null; echo ok", timeout=3)
            run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; pkill -9 roc-recv; sleep 0.5; echo ok\" 2>&1", timeout=4)
            self.log_msg("Copie receiver...")
            out,_=run_cmd(f"sshpass -p '{pwd}' scp -o StrictHostKeyChecking=no {shlex.quote(str(RPI_RECEIVE))} {user}@{ip}:/tmp/rpi_receiver.sh 2>&1", timeout=5)
            self.log_msg(out)
            run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"chmod +x /tmp/rpi_receiver.sh\" 2>&1", timeout=3)
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"nohup /tmp/rpi_receiver.sh {pc_ip} {codec} {mode} 4711 > /tmp/rpi_recv.log 2>&1 & sleep 1; cat /tmp/rpi_recv.log | head -25; ps aux | grep -E 'ffmpeg|roc-recv' | grep -v grep\" 2>&1", timeout=6)
            self.log_msg(out)
            if not PC_STREAM.exists():
                self.log_msg(f"ERR {PC_STREAM}"); self.connect_btn.configure(state="normal", text="▶  CONNECTER WIFI"); return
            cmd=f"nohup {shlex.quote(str(PC_STREAM))} {ip} {codec} {mode} 4711 > /tmp/pc_stream.log 2>&1 & echo $!"
            out,_=run_cmd(cmd, timeout=4)
            self.log_msg(f"PC PID {out.strip()}")
            time.sleep(2)
            out2,_=run_cmd("cat /tmp/pc_stream.log | tail -25; ps aux | grep -E 'ffmpeg|roc-send' | grep -v grep", timeout=3)
            self.log_msg(out2)
            out3,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"cat /tmp/rpi_recv.log | tail -25; wpctl status 2>&1 | grep -A2 Streams | head -10\" 2>&1", timeout=4)
            self.log_msg("— RPi —\n"+out3)
            pc_ok = ("ffmpeg" in out2 or "roc-send" in out2)
            rpi_ok = ("ffmpeg" in out3 or "roc-recv" in out3)
            if pc_ok and rpi_ok:
                self.status_dot.configure(text_color="#00d68f"); self.status_txt.configure(text="connecté ✓", text_color="#00d68f")
                self.after(0, lambda: self.log_msg("✓ Streaming actif — joue ta musique !"))
            else:
                self.status_dot.configure(text_color="#ff9f0a"); self.status_txt.configure(text="erreur")
                self.log_msg("Erreur voir logs")
            self.connect_btn.configure(state="normal", text="▶  CONNECTER WIFI")
        threading.Thread(target=do, daemon=True).start()

    def disconnect(self):
        # Disconnect both WiFi and BT
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg("STOP (WiFi + BT)")
        def do():
            run_cmd("pkill -9 ffmpeg; pkill -9 roc-send; echo pc stop", timeout=3)
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; pkill -9 roc-recv; echo rpi stop; ps aux | grep -E 'ffmpeg|roc' | grep -v grep || echo clean\" 2>&1", timeout=4)
            self.log_msg(out)
            # BT disconnect also
            mac=self.bt_mac_var.get().strip()
            run_cmd(f"bluetoothctl disconnect {mac} 2>&1 | tail -5", timeout=3)
            self.status_dot.configure(text_color="#ff3b30"); self.status_txt.configure(text="déconnecté")
            self.bt_status.configure(text="● BT déconnecté", text_color="#8b8fa3")
        threading.Thread(target=do, daemon=True).start()

    def test_tone(self):
        # If BT tab active, test via BT sink, else WiFi
        current = self.tabview.get()
        self.log_msg(f"Tone 440Hz 3s via {current}...")
        def do():
            # For BT, ensure default sink is BT when BT tab
            if current=="Bluetooth":
                mac=self.bt_mac_var.get().strip()
                # check sink
                out,_=run_cmd("pactl list short sinks 2>&1 | grep bluez | head -1", timeout=2)
                if "bluez" not in out:
                    self.log_msg("Pas de sink BT, tone sur default")
            run_cmd("timeout 4 ffmpeg -hide_banner -loglevel error -f lavfi -i \"sine=frequency=440:duration=3,volume=0.5\" -f pulse default 2>&1", timeout=5)
            self.log_msg("Tone envoyé")
        threading.Thread(target=do, daemon=True).start()

    def refresh_logs(self):
        def do():
            out,_=run_cmd("cat /tmp/pc_stream.log 2>&1 | tail -50", timeout=2)
            out2,_=run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"cat /tmp/rpi_recv.log 2>&1 | tail -50\" 2>&1", timeout=3)
            self.log.insert("end", f"\n--- PC ---\n{out}\n--- RPi ---\n{out2}\n")
            self.log.see("end")
        threading.Thread(target=do, daemon=True).start()

    def auto_status(self):
        def do():
            out,_=run_cmd("ps aux | grep -E 'ffmpeg.*udp|roc-send' | grep -v grep", timeout=2)
            pc = bool(out.strip())
            ip=self.pi_ip_var.get(); user=self.user_var.get(); pwd=self.pass_var.get()
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"ps aux | grep -E 'ffmpeg|roc-recv' | grep -v grep\" 2>&1", timeout=3)
            rpi=bool(out2.strip())
            # BT status
            out3,_=run_cmd("bluetoothctl info 2C:CF:67:00:AC:EE 2>&1 | grep Connected | head -1", timeout=2)
            bt = "Connected: yes" in out3
            if pc and rpi:
                self.after(0, lambda: (self.status_dot.configure(text_color="#00d68f"), self.status_txt.configure(text="WiFi connecté ✓")))
            elif bt:
                self.after(0, lambda: (self.status_dot.configure(text_color="#00d9ff"), self.status_txt.configure(text="BT connecté ✓")))
            elif pc or rpi:
                self.after(0, lambda: (self.status_dot.configure(text_color="#ff9f0a"), self.status_txt.configure(text="partiel")))
            else:
                if not bt:
                    self.after(0, lambda: (self.status_dot.configure(text_color="#ff3b30"), self.status_txt.configure(text="déconnecté")))
        threading.Thread(target=do, daemon=True).start()
        self.after(4000, self.auto_status)

if __name__ == "__main__":
    if not PC_STREAM.exists():
        print(f"ERR {PC_STREAM}")
        sys.exit(1)
    app = ModernApp()
    app.mainloop()
