#!/usr/bin/env python3
# Fedora Wifi Sound Link - Ultra Modern Compact GUI v2
# Design: Glassmorphism, central dial, compact, real icon, responsive
import customtkinter as ctk
import tkinter as tk
from pathlib import Path
import subprocess, threading, re, time, shlex, sys, math
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
        self.title("KRK Link")
        self.geometry("460x720")
        self.minsize(380, 620)
        self.maxsize(520, 900)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        try:
            if ICON.exists():
                img = Image.open(ICON)
                self.icon_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28,28))
                self.icon_large = ctk.CTkImage(light_image=img, dark_image=img, size=(56,56))
            else:
                self.icon_img = None
                self.icon_large = None
        except:
            self.icon_img = None
            self.icon_large = None
            
        try:
            if (ASSETS/"icon.png").exists():
                pil = Image.open(ASSETS/"icon.png")
                self.tk_icon = tk.PhotoImage(file=str(ASSETS/"icon.png"))
                self.iconphoto(True, self.tk_icon)
        except: pass

        self.bg = "#0a0c10"
        self.card_bg = "#14171f"
        self.card_border = "#232733"
        self.accent = "#7c5cff"
        self.accent2 = "#00d9ff"
        self.accent_hover = "#6b4feb"
        self.configure(fg_color=self.bg)

        # Main scrollable
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color="#1e2230", scrollbar_button_hover_color="#252a3a", corner_radius=0)
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # Header - ultra compact with real icon and status
        header = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=16, border_width=1, border_color=self.card_border)
        header.pack(fill="x", padx=12, pady=(12,8))
        header.grid_columnconfigure(1, weight=1)
        
        if self.icon_img:
            ctk.CTkLabel(header, image=self.icon_img, text="").grid(row=0, column=0, rowspan=2, padx=(14,10), pady=10)
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w", pady=(10,0))
        ctk.CTkLabel(title_box, text="KRK LINK", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(title_box, text="STUDIO", font=ctk.CTkFont(size=9), text_color=self.accent, corner_radius=4, fg_color="#1e1a33").pack(side="left", padx=6)
        
        ctk.CTkLabel(header, text=f"{self.pc_ip} → KRK", font=ctk.CTkFont(size=10), text_color="#6b7280").grid(row=1, column=1, sticky="w", pady=(0,10))
        
        self.status_dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=20), text_color="#ff3b30")
        self.status_dot.grid(row=0, column=2, rowspan=2, padx=14, pady=10)
        self.status_txt = ctk.CTkLabel(header, text="OFF", font=ctk.CTkFont(size=9, weight="bold"), text_color="#6b7280")
        self.status_txt.grid(row=0, column=3, rowspan=2, padx=(0,14), pady=10)

        # Central Dial Card - innovative circular volume
        dial_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=16, border_width=1, border_color=self.card_border)
        dial_card.pack(fill="x", padx=12, pady=6)
        dial_card.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(dial_card, text="VOLUME", font=ctk.CTkFont(size=9, weight="bold"), text_color="#6b7280").pack(pady=(12,4))
        
        # Canvas for circular dial
        self.dial_canvas = tk.Canvas(dial_card, width=160, height=160, bg=self.card_bg, highlightthickness=0, bd=0)
        self.dial_canvas.pack(pady=4)
        self.dial_value = 40
        self.dial_dragging = False
        self.dial_canvas.bind("<Button-1>", self.dial_click)
        self.dial_canvas.bind("<B1-Motion>", self.dial_drag)
        self.dial_canvas.bind("<ButtonRelease-1>", self.dial_release)
        self.draw_dial(40)
        
        self.vol_label = ctk.CTkLabel(dial_card, text="40%", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
        self.vol_label.pack()
        ctk.CTkLabel(dial_card, text="AudioBox USB 96", font=ctk.CTkFont(size=9), text_color="#6b7280").pack(pady=(0,12))

        # Transport Switch - WiFi / Bluetooth as pill toggle
        transport_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=16, border_width=1, border_color=self.card_border)
        transport_card.pack(fill="x", padx=12, pady=6)
        
        ctk.CTkLabel(transport_card, text="TRANSPORT", font=ctk.CTkFont(size=9, weight="bold"), text_color="#6b7280").pack(anchor="w", padx=14, pady=(10,6))
        
        btn_row = ctk.CTkFrame(transport_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0,6))
        btn_row.grid_columnconfigure((0,1), weight=1)
        
        self.transport_var = ctk.StringVar(value="wifi")
        self.wifi_btn = ctk.CTkButton(btn_row, text="󰖩  WiFi", height=36, corner_radius=10, fg_color=self.accent, hover_color=self.accent_hover, font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self.set_transport("wifi"))
        self.wifi_btn.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.bt_btn = ctk.CTkButton(btn_row, text="󰂯  Bluetooth", height=36, corner_radius=10, fg_color="#1e2230", border_width=1, border_color=self.card_border, hover_color="#252a3a", font=ctk.CTkFont(size=12), command=lambda: self.set_transport("bt"))
        self.bt_btn.grid(row=0, column=1, sticky="ew", padx=(4,0))
        
        # Dynamic content for WiFi vs BT
        self.wifi_frame = ctk.CTkFrame(transport_card, fg_color="transparent")
        self.bt_frame = ctk.CTkFrame(transport_card, fg_color="transparent")
        
        # WiFi content
        self.pi_ip_var = ctk.StringVar(value=DEFAULT_PI_IP)
        self.user_var = ctk.StringVar(value=DEFAULT_USER)
        self.pass_var = ctk.StringVar(value=DEFAULT_PASS)
        
        wifi_row = ctk.CTkFrame(self.wifi_frame, fg_color="#0f1115", corner_radius=10, border_width=1, border_color=self.card_border)
        wifi_row.pack(fill="x", padx=14, pady=6)
        wifi_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(wifi_row, placeholder_text="192.168.1.101", textvariable=self.pi_ip_var, corner_radius=8, border_width=0, fg_color="transparent", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(wifi_row, text="Scan", width=60, height=28, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.scan_network, font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=6, pady=6)
        
        self.scan_list_frame = ctk.CTkScrollableFrame(self.wifi_frame, height=60, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
        self.scan_list_frame.pack(fill="x", padx=14, pady=(0,6))
        ctk.CTkLabel(self.scan_list_frame, text="Scan pour AudioBox", font=ctk.CTkFont(size=10), text_color="#5a5e73").pack(pady=10)
        
        # BT content
        self.bt_mac_var = ctk.StringVar(value=DEFAULT_PI_MAC)
        bt_row = ctk.CTkFrame(self.bt_frame, fg_color="#0f1115", corner_radius=10, border_width=1, border_color=self.card_border)
        bt_row.pack(fill="x", padx=14, pady=6)
        bt_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(bt_row, textvariable=self.bt_mac_var, placeholder_text="2C:CF:67:00:AC:EE", corner_radius=8, border_width=0, fg_color="transparent", font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(bt_row, text="Scan", width=60, height=28, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.scan_bluetooth, font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=6, pady=6)
        
        bt_btn_row = ctk.CTkFrame(self.bt_frame, fg_color="transparent")
        bt_btn_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkButton(bt_btn_row, text="Power ON", height=28, corner_radius=8, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.bt_power, font=ctk.CTkFont(size=11)).pack(side="left", fill="x", expand=True, padx=(0,4))
        self.bt_status = ctk.CTkLabel(bt_btn_row, text="BT ?", font=ctk.CTkFont(size=10), text_color="#6b7280")
        self.bt_status.pack(side="left", padx=8)
        
        self.bt_list_frame = ctk.CTkScrollableFrame(self.bt_frame, height=60, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
        self.bt_list_frame.pack(fill="x", padx=14, pady=(0,6))
        ctk.CTkLabel(self.bt_list_frame, text="Scan BT pour raspberrypi", font=ctk.CTkFont(size=10), text_color="#5a5e73").pack(pady=10)
        
        self.wifi_frame.pack(fill="x", pady=(0,6))
        self.current_transport = "wifi"

        # Mode selector - compact pill
        mode_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=16, border_width=1, border_color=self.card_border)
        mode_card.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(mode_card, text="QUALITÉ", font=ctk.CTkFont(size=9, weight="bold"), text_color="#6b7280").pack(anchor="w", padx=14, pady=(10,6))
        self.preset_var = ctk.StringVar(value="pcm_stable")
        presets = [
            ("PCM Stable", "pcm_stable", "#00d9ff"),
            ("Opus", "opus_stable", "#7c5cff"),
            ("Fast", "pcm_fast", "#6b7280"),
        ]
        preset_row = ctk.CTkFrame(mode_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=14, pady=(0,10))
        preset_row.grid_columnconfigure((0,1,2), weight=1)
        self.preset_btns = {}
        for i, (title, val, color) in enumerate(presets):
            btn = ctk.CTkButton(preset_row, text=title, height=28, corner_radius=20, fg_color=self.accent if val=="pcm_stable" else "#1e2230", border_width=1, border_color=color, hover_color="#252a3a", font=ctk.CTkFont(size=10, weight="bold"), command=lambda v=val: self.select_preset(v))
            btn.grid(row=0, column=i, sticky="ew", padx=3)
            self.preset_btns[val] = btn

        # Main Connect - large, gradient, central
        self.connect_btn = ctk.CTkButton(self.scroll, text="▶  CONNECTER", height=52, corner_radius=14, fg_color=self.accent, hover_color=self.accent_hover, font=ctk.CTkFont(size=14, weight="bold"), command=self.connect)
        self.connect_btn.pack(fill="x", padx=12, pady=8)
        
        ctrl_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=12, pady=(0,8))
        ctrl_row.grid_columnconfigure((0,1), weight=1)
        self.stop_btn = ctk.CTkButton(ctrl_row, text="■ Stop", height=36, corner_radius=10, fg_color="#1e2230", border_width=1, border_color=self.card_border, hover_color="#252a3a", font=ctk.CTkFont(size=12), command=self.disconnect)
        self.stop_btn.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.tone_btn = ctk.CTkButton(ctrl_row, text="♪ Test", height=36, corner_radius=10, fg_color="#1e2230", border_width=1, border_color=self.card_border, hover_color="#252a3a", font=ctk.CTkFont(size=12), command=self.test_tone)
        self.tone_btn.grid(row=0, column=1, sticky="ew", padx=(4,0))

        # Logs - collapsible, minimal by default
        self.log_card = ctk.CTkFrame(self.scroll, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        self.log_card.pack(fill="x", padx=12, pady=6)
        log_head = ctk.CTkFrame(self.log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(log_head, text="LOGS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#6b7280").pack(side="left")
        self.log_collapsed = True
        self.log_toggle = ctk.CTkButton(log_head, text="▼", width=30, height=22, corner_radius=6, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.toggle_logs, font=ctk.CTkFont(size=10))
        self.log_toggle.pack(side="right")
        self.log = ctk.CTkTextbox(self.log_card, height=80, font=ctk.CTkFont(family="Monospace", size=10), fg_color="#0f1115", border_width=0, text_color="#a8adc3")
        # hidden by default
        self.log_visible = False

        ctk.CTkLabel(self.scroll, text="github.com/stxtxm/fedora-wifi-sound-link  •  WiFi + BT  •  v1.1", font=ctk.CTkFont(size=8), text_color="#3a3e4d").pack(pady=(4,12))

        self.after(800, self.fetch_volume)
        self.after(1500, self.auto_status)
        self.after(1000, self.update_bt_info)
        self.log_msg(f"Prêt {self.pc_ip} → KRK")

    def set_transport(self, mode):
        self.current_transport = mode
        if mode == "wifi":
            self.wifi_btn.configure(fg_color=self.accent, border_width=0)
            self.bt_btn.configure(fg_color="#1e2230", border_width=1)
            self.bt_frame.pack_forget()
            self.wifi_frame.pack(fill="x", pady=(0,6))
            self.connect_btn.configure(text="▶  CONNECTER WIFI")
        else:
            self.bt_btn.configure(fg_color=self.accent2, text_color="#0a0c10", border_width=0)
            self.wifi_btn.configure(fg_color="#1e2230", border_width=1, text_color="white")
            self.wifi_frame.pack_forget()
            self.bt_frame.pack(fill="x", pady=(0,6))
            self.connect_btn.configure(text="▶  CONNECTER BT")
        self.update()

    def draw_dial(self, value):
        self.dial_canvas.delete("all")
        # Background circle
        self.dial_canvas.create_oval(10,10,150,150, outline="#1e2230", width=8)
        # Progress arc
        angle = (value / 100) * 270 - 135  # -135 to 135
        # Draw arc as thick line
        for i in range(int((value/100)*270)):
            a = -135 + i
            rad = math.radians(a)
            x1 = 80 + 60 * math.cos(rad)
            y1 = 80 + 60 * math.sin(rad)
            x2 = 80 + 68 * math.cos(rad)
            y2 = 80 + 68 * math.sin(rad)
            self.dial_canvas.create_line(x1,y1,x2,y2, fill=self.accent, width=4, capstyle=tk.ROUND)
        # Center
        self.dial_canvas.create_oval(55,55,105,105, fill="#1e2230", outline=self.card_border, width=1)
        # Knob
        rad = math.radians(angle)
        kx = 80 + 60 * math.cos(rad)
        ky = 80 + 60 * math.sin(rad)
        self.dial_canvas.create_oval(kx-8,ky-8,kx+8,ky+8, fill="white", outline=self.accent, width=2)
        self.dial_value = value

    def dial_click(self, e):
        self.dial_drag(e)
    def dial_drag(self, e):
        # Calculate angle from center
        dx = e.x - 80
        dy = e.y - 80
        angle = math.degrees(math.atan2(dy, dx))
        # Normalize -135 to 135 -> 0-100
        # atan2 gives -180 to 180, we want -135 to 135
        if angle < -135: angle = -135
        if angle > 135: 
            if angle > 135 and angle < 180:
                angle = 135 if angle < 150 else -135
            else:
                angle = 135
        # Convert -135..135 to 0..100
        value = int(((angle + 135) / 270) * 100)
        value = max(0, min(100, value))
        self.dial_value = value
        self.vol_label.configure(text=f"{value}%")
        self.draw_dial(value)
        # Update slider var too
        try:
            self.vol_var.set(value)
        except: pass
    def dial_release(self, e):
        # Apply volume on release
        self.apply_volume()

    def toggle_logs(self):
        if self.log_visible:
            self.log.pack_forget()
            self.log_toggle.configure(text="▼")
            self.log_visible = False
        else:
            self.log.pack(fill="x", padx=8, pady=(0,8))
            self.log_visible = True

    def select_preset(self, val):
        self.preset_var.set(val)
        for k, btn in self.preset_btns.items():
            if k == val:
                btn.configure(fg_color=self.accent, border_width=0)
            else:
                btn.configure(fg_color="#1e2230", border_width=1, border_color=self.card_border)

    def get_preset(self):
        p=self.preset_var.get()
        if p=="opus_stable": return ("opus","stable")
        if p=="pcm_stable": return ("pcm","stable")
        return ("pcm","fast")

    def log_msg(self, m):
        try:
            if self.log_visible:
                self.log.insert("end", m+"\n")
                self.log.see("end")
        except: pass
        print(m)

    # ... keep all existing methods: scan_network, test_ssh, fetch_volume, on_vol_drag, apply_volume, update_bt_info, bt_power, scan_bluetooth, bt_connect, bt_disconnect, connect, disconnect, test_tone, refresh_logs, auto_status
    # For brevity, we keep them as before but ensure they use new BT_RPI/BT_PC paths
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
                        b=ctk.CTkButton(self.scan_list_frame, text=f"{ip}  •  AudioBox ✓", height=28, corner_radius=8, fg_color="#1a1d24", border_width=1, border_color=self.accent, hover_color="#252836", command=lambda ip=ip: (self.pi_ip_var.set(ip), self.log_msg(f"IP {ip}")))
                        b.pack(fill="x", pady=2, padx=4)
                    self.after(0, make_btn)
            if not found:
                self.after(0, lambda: ctk.CTkLabel(self.scan_list_frame, text="Aucun Pi — vérifie USB", text_color="#ff3b30").pack())
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="Scan"))
        threading.Thread(target=do, daemon=True).start()
    def test_ssh(self):
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg(f"Test {user}@{ip} ...")
        def do():
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 {user}@{ip} \"hostname; pactl info 2>&1 | head -3; aplay -l 2>&1 | grep AudioBox; wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1\" 2>&1", timeout=5)
            self.log_msg(out)
        threading.Thread(target=do, daemon=True).start()
    def fetch_volume(self):
        def do():
            try:
                out,_=run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1\" 2>&1", timeout=3)
                import re
                m=re.search(r"Volume:\s*([\d\.]+)", out)
                if m:
                    v=int(float(m.group(1))*100)
                    self.after(0, lambda: (self.vol_var.set(v) if hasattr(self, 'vol_var') else None, self.vol_label.configure(text=f"{v}%"), self.draw_dial(v)))
            except: pass
        threading.Thread(target=do, daemon=True).start()
    def on_vol_drag(self, v): pass
    def apply_volume(self):
        v=self.dial_value
        frac=v/100.0
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg(f"Volume {v}%")
        def do():
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"wpctl set-volume @DEFAULT_AUDIO_SINK@ {frac:.2f}; wpctl get-volume @DEFAULT_AUDIO_SINK@\" 2>&1", timeout=3)
            self.log_msg(out.strip())
        threading.Thread(target=do, daemon=True).start()
    def update_bt_info(self):
        def do():
            out,_=run_cmd("bluetoothctl show 2>&1 | grep -E 'Powered|Name' | head -5", timeout=2)
            out2,_=run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"bluetoothctl show 2>&1 | grep -E 'Powered|Discoverable|Pairable' | head -5\" 2>&1", timeout=3)
            try:
                self.after(0, lambda: self.bt_info.configure(text=f"PC:{'ON' if 'Powered: yes' in out else 'OFF'} • Pi:{'visible' if 'Discoverable: yes' in out2 else 'off'}"))
            except: pass
        threading.Thread(target=do, daemon=True).start()
        self.after(5000, self.update_bt_info)
    def bt_power(self):
        self.log_msg("BT Power ON + Pi visible")
        def do():
            out,_=run_cmd("rfkill unblock bluetooth; bluetoothctl power on 2>&1 | head -5; bluetoothctl show 2>&1 | grep Powered", timeout=4)
            self.log_msg(out)
            ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} discoverable 2>&1 | head -10\" 2>&1", timeout=5)
            self.log_msg(out2)
        threading.Thread(target=do, daemon=True).start()
    def scan_bluetooth(self):
        self.bt_scan_btn.configure(state="disabled", text="...")
        for w in self.bt_list_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.bt_list_frame, text="Scan BT 8s...", text_color="#8b8fa3").pack(pady=10)
        def do():
            out,_=run_cmd("timeout 9 bash -c 'bluetoothctl scan on 2>&1 & pid=$!; sleep 8; bluetoothctl scan off 2>&1 | head -5; wait $pid 2>/dev/null; bluetoothctl devices 2>&1' 2>&1", timeout=12)
            self.log_msg(out[:800])
            found=False
            for line in out.splitlines():
                m=re.search(r"Device\s+([0-9A-F:]{17})\s+(.+)", line, re.I)
                if m:
                    mac=m.group(1); name=m.group(2)
                    found=True
                    is_pi = "raspberry" in name.lower() or mac.upper()==self.bt_mac_var.get().upper()
                    txt=f"{mac}  •  {name} {'✓ Pi' if is_pi else ''}"
                    col=self.accent if is_pi else self.card_border
                    def make(mac=mac, txt=txt, col=col):
                        b=ctk.CTkButton(self.bt_list_frame, text=txt, height=28, corner_radius=8, fg_color="#1a1d24", border_width=1, border_color=col, hover_color="#252836", command=lambda mac=mac: (self.bt_mac_var.set(mac), self.log_msg(f"MAC {mac}")))
                        b.pack(fill="x", pady=2, padx=4)
                    self.after(0, make)
            if not found:
                self.log_msg("Aucun BT trouvé")
                self.after(0, lambda: ctk.CTkLabel(self.bt_list_frame, text="Pi non trouvé — discoverable ON ?", text_color="#ff3b30").pack())
            self.after(0, lambda: self.bt_scan_btn.configure(state="normal", text="Scan BT"))
        threading.Thread(target=do, daemon=True).start()
    def bt_connect(self):
        mac=self.bt_mac_var.get().strip()
        if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac, re.I):
            self.log_msg(f"MAC invalide: {mac}"); return
        self.log_msg(f"BT Pair+Connect {mac}...")
        self.bt_connect_btn.configure(state="disabled", text="...")
        def do():
            ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} setup 2>&1 | tail -10\" 2>&1", timeout=6)
            self.log_msg(out)
            for step in [f"bluetoothctl pair {mac} 2>&1 | tail -10", f"bluetoothctl trust {mac} 2>&1 | tail -5", f"bluetoothctl connect {mac} 2>&1 | tail -20"]:
                out,_=run_cmd(step, timeout=10)
                self.log_msg(out); time.sleep(1)
            out,_=run_cmd("pactl list short sinks 2>&1 | grep bluez | head -5; pactl info 2>&1 | grep 'Default Sink'", timeout=3)
            self.log_msg(out)
            if "bluez" in out.lower():
                m=re.search(r"(bluez_output\.[^\s]+)", out)
                if m:
                    sink=m.group(1)
                    run_cmd(f"pactl set-default-sink {shlex.quote(sink)} 2>&1", timeout=2)
                    self.log_msg(f"Default sink -> {sink}")
                    self.after(0, lambda: (self.status_dot.configure(text_color="#00d68f"), self.status_txt.configure(text="BT connecté ✓")))
                else:
                    self.after(0, lambda: self.bt_status.configure(text="● partiel", text_color="#ff9f0a"))
            else:
                self.after(0, lambda: self.bt_status.configure(text="● échec", text_color="#ff3b30"))
                self.log_msg("Pas de sink bluez")
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"{shlex.quote(str(BT_RPI))} route 2>&1 | tail -10\" 2>&1", timeout=5)
            self.log_msg(out2)
            self.after(0, lambda: self.bt_connect_btn.configure(state="normal", text="Pair + Connect"))
        threading.Thread(target=do, daemon=True).start()
    def bt_disconnect(self):
        mac=self.bt_mac_var.get().strip()
        self.log_msg(f"BT Disconnect {mac}")
        def do():
            out,_=run_cmd(f"bluetoothctl disconnect {mac} 2>&1 | tail -10", timeout=5)
            self.log_msg(out)
            self.after(0, lambda: (self.status_dot.configure(text_color="#ff3b30"), self.status_txt.configure(text="déconnecté")))
        threading.Thread(target=do, daemon=True).start()
    def connect(self):
        codec, mode = self.get_preset()
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get(); pc_ip=self.pc_ip
        current = self.tabview.get() if hasattr(self, 'tabview') else "WiFi"
        if current == "Bluetooth":
            self.bt_connect(); return
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
                self.log_msg(f"ERR {PC_STREAM}"); self.connect_btn.configure(state="normal", text="▶  CONNECTER"); return
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
                self.after(0, lambda: (self.status_dot.configure(text_color="#00d68f"), self.status_txt.configure(text="connecté ✓")))
                self.log_msg("✓ Streaming actif")
            else:
                self.after(0, lambda: (self.status_dot.configure(text_color="#ff9f0a"), self.status_txt.configure(text="erreur")))
                self.log_msg("Erreur voir logs")
            self.connect_btn.configure(state="normal", text="▶  CONNECTER")
        threading.Thread(target=do, daemon=True).start()
    def disconnect(self):
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg("STOP (WiFi + BT)")
        def do():
            run_cmd("pkill -9 ffmpeg; pkill -9 roc-send; echo pc stop", timeout=3)
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; pkill -9 roc-recv; echo rpi stop\" 2>&1", timeout=4)
            self.log_msg(out)
            mac=self.bt_mac_var.get().strip()
            run_cmd(f"bluetoothctl disconnect {mac} 2>&1 | tail -5", timeout=3)
            self.after(0, lambda: (self.status_dot.configure(text_color="#ff3b30"), self.status_txt.configure(text="déconnecté")))
        threading.Thread(target=do, daemon=True).start()
    def test_tone(self):
        current = self.tabview.get() if hasattr(self, 'tabview') else "WiFi"
        self.log_msg(f"Tone 440Hz 3s via {current}...")
        def do():
            run_cmd("timeout 4 ffmpeg -hide_banner -loglevel error -f lavfi -i \"sine=frequency=440:duration=3,volume=0.5\" -f pulse default 2>&1", timeout=5)
            self.log_msg("Tone envoyé")
        threading.Thread(target=do, daemon=True).start()
    def refresh_logs(self):
        def do():
            out,_=run_cmd("cat /tmp/pc_stream.log 2>&1 | tail -50", timeout=2)
            out2,_=run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"cat /tmp/rpi_recv.log 2>&1 | tail -50\" 2>&1", timeout=3)
            try:
                self.log.insert("end", f"\n--- PC ---\n{out}\n--- RPi ---\n{out2}\n")
                self.log.see("end")
            except: pass
        threading.Thread(target=do, daemon=True).start()
    def auto_status(self):
        def do():
            out,_=run_cmd("ps aux | grep -E 'ffmpeg.*udp|roc-send' | grep -v grep", timeout=2)
            pc = bool(out.strip())
            ip=self.pi_ip_var.get(); user=self.user_var.get(); pwd=self.pass_var.get()
            out2,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"ps aux | grep -E 'ffmpeg|roc-recv' | grep -v grep\" 2>&1", timeout=3)
            rpi=bool(out2.strip())
            out3,_=run_cmd("bluetoothctl info 2C:CF:67:00:AC:EE 2>&1 | grep Connected | head -1", timeout=2)
            bt = "Connected: yes" in out3
            if pc and rpi:
                self.after(0, lambda: (self.status_dot.configure(text_color="#00d68f"), self.status_txt.configure(text="WiFi ✓")))
            elif bt:
                self.after(0, lambda: (self.status_dot.configure(text_color="#00d9ff"), self.status_txt.configure(text="BT ✓")))
            elif pc or rpi:
                self.after(0, lambda: (self.status_dot.configure(text_color="#ff9f0a"), self.status_txt.configure(text="partiel")))
            else:
                if not bt:
                    self.after(0, lambda: (self.status_dot.configure(text_color="#ff3b30"), self.status_txt.configure(text="OFF")))
        threading.Thread(target=do, daemon=True).start()
        self.after(4000, self.auto_status)

if __name__ == "__main__":
    if not PC_STREAM.exists():
        print(f"ERR {PC_STREAM}")
        sys.exit(1)
    app = ModernApp()
    app.mainloop()
