#!/usr/bin/env python3
# Fedora Wifi Sound Link - Modern Compact GUI
# Design ultra moderne, dark, compact, icon réelle
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
ASSETS = PROJECT_DIR / "assets"
ICON = ASSETS / "icon-256.png"

DEFAULT_PI_IP = "192.168.1.101"
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
        self.geometry("520x720")
        self.minsize(520, 640)
        # icon
        try:
            if ICON.exists():
                img = Image.open(ICON)
                self.icon_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28,28))
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

        # colors
        self.bg = "#0f1115"
        self.card_bg = "#1a1d24"
        self.card_border = "#2a2e39"
        self.accent = "#7c5cff"
        self.accent2 = "#00d9ff"
        self.configure(fg_color=self.bg)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14,8))
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        if self.icon_img:
            ctk.CTkLabel(left, image=self.icon_img, text="").pack(side="left", padx=(0,10))
        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="FEDORA WIFI SOUND LINK", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"PC {self.pc_ip}  →  AudioBox USB 96  →  KRK", font=ctk.CTkFont(size=10), text_color="#8b8fa3").pack(anchor="w")
        self.status_dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=18), text_color="#ff3b30")
        self.status_dot.pack(side="right", padx=4)
        self.status_txt = ctk.CTkLabel(header, text="déconnecté", font=ctk.CTkFont(size=11), text_color="#8b8fa3")
        self.status_txt.pack(side="right")

        # Pi card
        pi_card = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        pi_card.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(pi_card, text="RASPBERRY PI", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=14, pady=(10,2))
        row1 = ctk.CTkFrame(pi_card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=4)
        self.pi_ip_var = ctk.StringVar(value=DEFAULT_PI_IP)
        self.pi_entry = ctk.CTkEntry(row1, width=130, placeholder_text="192.168.1.101", textvariable=self.pi_ip_var, corner_radius=8, border_color=self.card_border, fg_color="#0f1115")
        self.pi_entry.pack(side="left", padx=4)
        self.user_var = ctk.StringVar(value=DEFAULT_USER)
        ctk.CTkEntry(row1, width=70, placeholder_text="user", textvariable=self.user_var, corner_radius=8, border_color=self.card_border, fg_color="#0f1115").pack(side="left", padx=4)
        self.pass_var = ctk.StringVar(value=DEFAULT_PASS)
        self.pass_entry = ctk.CTkEntry(row1, width=80, placeholder_text="pass", textvariable=self.pass_var, show="*", corner_radius=8, border_color=self.card_border, fg_color="#0f1115")
        self.pass_entry.pack(side="left", padx=4)
        self.scan_btn = ctk.CTkButton(row1, text="Scan", width=60, height=28, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.scan_network, font=ctk.CTkFont(size=11))
        self.scan_btn.pack(side="left", padx=4)

        row2 = ctk.CTkFrame(pi_card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(2,8))
        self.test_btn = ctk.CTkButton(row2, text="Tester", width=80, height=26, corner_radius=8, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.test_ssh, font=ctk.CTkFont(size=11))
        self.test_btn.pack(side="left", padx=4)
        self.pi_state = ctk.CTkLabel(row2, text="non testé", font=ctk.CTkFont(size=11), text_color="#8b8fa3")
        self.pi_state.pack(side="left", padx=10)
        self.scan_list_frame = ctk.CTkScrollableFrame(pi_card, height=70, fg_color="#0f1115", corner_radius=8, border_width=1, border_color=self.card_border)
        self.scan_list_frame.pack(fill="x", padx=12, pady=(0,10))
        self.scan_buttons = []
        ctk.CTkLabel(self.scan_list_frame, text="Lance un scan pour détecter le Pi avec AudioBox", font=ctk.CTkFont(size=11), text_color="#5a5e73").pack(pady=20)

        # Mode card
        mode_card = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        mode_card.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(mode_card, text="MODE STREAMING", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=14, pady=(10,4))
        self.preset_var = ctk.StringVar(value="roc_stable")
        presets = [
            ("ROC Stable", "roc_stable", "Roc toolkit + FEC • latence 300ms • PARFAIT wifi pourri • qualité studio", "#00d9ff"),
            ("Opus Stable", "opus_stable", "Opus 192k VBR • 8x moins de bande • transparent", "#7c5cff"),
            ("PCM Stable", "pcm_stable", "Lossless 1536k • latence 600ms • qualité max", "#5a5e73"),
            ("PCM Fast", "pcm_fast", "Low latency 60ms • saccades si wifi pourri", "#3a3e4d"),
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

        # Control card
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=8)
        self.connect_btn = ctk.CTkButton(ctrl, text="▶  CONNECTER", height=42, corner_radius=10, fg_color=self.accent, hover_color="#6b4feb", font=ctk.CTkFont(size=13, weight="bold"), command=self.connect)
        self.connect_btn.pack(side="left", fill="x", expand=True, padx=(0,6))
        self.stop_btn = ctk.CTkButton(ctrl, text="■", width=48, height=42, corner_radius=10, fg_color="#1a1d24", border_width=1, border_color=self.card_border, hover_color="#252836", font=ctk.CTkFont(size=16), command=self.disconnect)
        self.stop_btn.pack(side="left", padx=2)
        self.tone_btn = ctk.CTkButton(ctrl, text="♪", width=48, height=42, corner_radius=10, fg_color="#1a1d24", border_width=1, border_color=self.card_border, hover_color="#252836", font=ctk.CTkFont(size=16), command=self.test_tone)
        self.tone_btn.pack(side="left", padx=(6,0))

        # Volume card
        vol_card = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        vol_card.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(vol_card, text="VOLUME KRK", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(anchor="w", padx=14, pady=(8,2))
        vol_row = ctk.CTkFrame(vol_card, fg_color="transparent")
        vol_row.pack(fill="x", padx=12, pady=(2,8))
        ctk.CTkLabel(vol_row, text="◂", text_color="#5a5e73").pack(side="left")
        self.vol_var = tk.IntVar(value=40)
        self.vol_slider = ctk.CTkSlider(vol_row, from_=0, to=100, variable=self.vol_var, width=260, height=16, button_color=self.accent, button_hover_color="#6b4feb", progress_color=self.accent, fg_color="#2a2e39", command=self.on_vol_drag)
        self.vol_slider.pack(side="left", padx=8, fill="x", expand=True)
        ctk.CTkLabel(vol_row, text="▸", text_color="#5a5e73").pack(side="left")
        self.vol_label = ctk.CTkLabel(vol_row, text="40%", font=ctk.CTkFont(size=12, weight="bold"), text_color="white", width=45)
        self.vol_label.pack(side="left", padx=6)
        self.vol_apply = ctk.CTkButton(vol_row, text="OK", width=40, height=26, corner_radius=8, fg_color="#252836", hover_color="#2a2e39", command=self.apply_volume, font=ctk.CTkFont(size=11))
        self.vol_apply.pack(side="left", padx=4)
        # VU meter canvas
        self.vu_canvas = tk.Canvas(vol_card, height=18, bg="#0f1115", highlightthickness=0)
        self.vu_canvas.pack(fill="x", padx=14, pady=(0,8))
        self.draw_vu(0)

        # Logs (collapsible)
        log_card = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=14, border_width=1, border_color=self.card_border)
        log_card.pack(fill="both", expand=True, padx=16, pady=(4,10))
        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(log_head, text="LOGS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b8fa3").pack(side="left")
        self.log_btn = ctk.CTkButton(log_head, text="↻", width=30, height=22, corner_radius=6, fg_color="transparent", border_width=1, border_color=self.card_border, command=self.refresh_logs, font=ctk.CTkFont(size=12))
        self.log_btn.pack(side="right", padx=4)
        ctk.CTkButton(log_head, text="clear", width=45, height=22, corner_radius=6, fg_color="transparent", border_width=1, border_color=self.card_border, command=lambda: self.log.delete("1.0","end"), font=ctk.CTkFont(size=11)).pack(side="right", padx=4)
        self.log = ctk.CTkTextbox(log_card, height=110, font=ctk.CTkFont(family="Monospace", size=11), fg_color="#0f1115", border_width=0, text_color="#a8adc3")
        self.log.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # footer
        footer = ctk.CTkLabel(self, text="Fedora Wifi Sound Link  •  github.com/timo/fedora-wifi-sound-link  •  Roc • Opus • PCM", font=ctk.CTkFont(size=9), text_color="#5a5e73")
        footer.pack(pady=(0,8))

        self.after(800, self.fetch_volume)
        self.after(1500, self.auto_status)
        self.after(100, self.vu_animate)
        self.log_msg(f"Prêt. PC {self.pc_ip} → Scan pour trouver le Pi AudioBox")
        self.log_msg("Recommandé: ROC Stable (FEC) pour wifi pourri, latence 300ms, qualité studio sans craquement")

    def select_preset(self, val):
        self.preset_var.set(val)
        self.update_preset_ui()
    def update_preset_ui(self):
        sel = self.preset_var.get()
        for k, f in self.preset_frames.items():
            if k == sel:
                f.configure(border_color=self.accent, border_width=2)
            else:
                f.configure(border_color=self.card_border, border_width=1)

    def draw_vu(self, level):
        self.vu_canvas.delete("all")
        w = self.vu_canvas.winfo_width() or 480
        h = 18
        # background bar
        self.vu_canvas.create_rectangle(0,4,w,14, fill="#2a2e39", outline="", width=0)
        # level bar with gradient
        lv = int(w * min(max(level,0),1))
        if lv>0:
            # gradient from accent to accent2
            self.vu_canvas.create_rectangle(0,4,lv,14, fill=self.accent, outline="")
            # peak
            if level>0.85:
                self.vu_canvas.create_rectangle(lv-3,2,lv,16, fill="#ff3b30", outline="")
        # ticks
        for i in range(5):
            x = int(w * i/4)
            self.vu_canvas.create_line(x,4,x,14, fill="#0f1115", width=1)

    def vu_animate(self):
        # animate based on audio level if connected, else idle
        import random, math
        try:
            if "connecté" in self.status_txt.cget("text"):
                # simule vu ou lit vrai niveau via pactl?
                lvl = 0.15 + 0.3*abs(math.sin(time.time()*3)) + random.random()*0.15
                # si besoin, lire vrai niveau via ssh: wpctl get-volume etc, mais simu suffit
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
            # clear initial label
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
                    self.vol_var.set(int(v)); self.vol_label.configure(text=f"{int(v)}%")
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

    def connect(self):
        codec, mode = self.get_preset()
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get(); pc_ip=self.pc_ip
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
                self.status_dot.configure(text_color="#00d68f"); self.status_txt.configure(text="connecté ✓", text_color="#00d68f")
                self.after(0, lambda: self.log_msg("✓ Streaming actif — joue ta musique !"))
            else:
                self.status_dot.configure(text_color="#ff9f0a"); self.status_txt.configure(text="erreur")
                self.log_msg("Erreur voir logs")
            self.connect_btn.configure(state="normal", text="▶  CONNECTER")
        threading.Thread(target=do, daemon=True).start()

    def disconnect(self):
        ip=self.pi_ip_var.get().strip(); user=self.user_var.get().strip(); pwd=self.pass_var.get()
        self.log_msg("STOP")
        def do():
            run_cmd("pkill -9 ffmpeg; pkill -9 roc-send; echo pc stop", timeout=3)
            out,_=run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; pkill -9 roc-recv; echo rpi stop; ps aux | grep -E 'ffmpeg|roc' | grep -v grep || echo clean\" 2>&1", timeout=4)
            self.log_msg(out)
            self.status_dot.configure(text_color="#ff3b30"); self.status_txt.configure(text="déconnecté")
        threading.Thread(target=do, daemon=True).start()

    def test_tone(self):
        self.log_msg("Tone 440Hz 3s...")
        def do():
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
            if pc and rpi:
                self.status_dot.configure(text_color="#00d68f"); self.status_txt.configure(text="connecté ✓")
            elif pc or rpi:
                self.status_dot.configure(text_color="#ff9f0a"); self.status_txt.configure(text="partiel")
            else:
                self.status_dot.configure(text_color="#ff3b30"); self.status_txt.configure(text="déconnecté")
        threading.Thread(target=do, daemon=True).start()
        self.after(4000, self.auto_status)

if __name__ == "__main__":
    if not PC_STREAM.exists():
        print(f"ERR {PC_STREAM}")
        sys.exit(1)
    app = ModernApp()
    app.mainloop()
