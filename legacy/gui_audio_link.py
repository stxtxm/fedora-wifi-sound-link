#!/usr/bin/env python3
# gui_audio_link.py - GUI pour PC -> RPi -> KRK
# Détection Pi, lancement 1-clic, anti-saccades
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess, threading, os, re, time, sys, json, shlex
from pathlib import Path
import concurrent.futures

PROJECT_DIR = Path(__file__).parent
PC_STREAM = PROJECT_DIR / "pc_stream_v2.sh"
RPI_RECEIVE = PROJECT_DIR / "rpi_receive_v2.sh"

DEFAULT_PI_IP = "192.168.1.101"
DEFAULT_USER = "timo"
DEFAULT_PASS = "1010"
DEFAULT_PORT = "4711"

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

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC → KRK Link - AudioBox")
        self.geometry("780x680")
        self.resizable(False, False)
        self.pc_ip = get_pc_ip()
        self.scan_results = []

        # Style
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except: pass

        # Header
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="PC → RPi → KRK", font=("Arial", 16, "bold")).pack(side="left")
        ttk.Label(header, text=f"PC: {self.pc_ip}", foreground="#2b7").pack(side="right")

        # Pi config frame
        cfg = ttk.LabelFrame(self, text="Raspberry Pi", padding=10)
        cfg.pack(fill="x", padx=10, pady=5)

        row1 = ttk.Frame(cfg)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="IP RPi:").pack(side="left")
        self.pi_ip_var = tk.StringVar(value=DEFAULT_PI_IP)
        self.pi_ip_entry = ttk.Entry(row1, textvariable=self.pi_ip_var, width=16)
        self.pi_ip_entry.pack(side="left", padx=5)
        ttk.Label(row1, text="User:").pack(side="left", padx=(10,0))
        self.user_var = tk.StringVar(value=DEFAULT_USER)
        ttk.Entry(row1, textvariable=self.user_var, width=8).pack(side="left", padx=5)
        ttk.Label(row1, text="Pass:").pack(side="left", padx=(10,0))
        self.pass_var = tk.StringVar(value=DEFAULT_PASS)
        self.pass_entry = ttk.Entry(row1, textvariable=self.pass_var, width=10, show="*")
        self.pass_entry.pack(side="left", padx=5)

        row2 = ttk.Frame(cfg)
        row2.pack(fill="x", pady=5)
        self.scan_btn = ttk.Button(row2, text="🔍 Scanner réseau", command=self.scan_network)
        self.scan_btn.pack(side="left")
        self.test_ssh_btn = ttk.Button(row2, text="Tester connexion", command=self.test_ssh)
        self.test_ssh_btn.pack(side="left", padx=5)
        self.pi_status = ttk.Label(row2, text="● non testé", foreground="gray")
        self.pi_status.pack(side="left", padx=10)

        self.scan_list = tk.Listbox(cfg, height=4)
        self.scan_list.pack(fill="x", pady=5)
        self.scan_list.bind("<<ListboxSelect>>", self.on_scan_select)
        ttk.Label(cfg, text="Double-clic ou sélection pour utiliser l'IP", font=("Arial", 7)).pack()

        # Mode frame
        mode = ttk.LabelFrame(self, text="Mode streaming (anti-saccades)", padding=10)
        mode.pack(fill="x", padx=10, pady=5)
        self.codec_var = tk.StringVar(value="opus")
        self.mode_var = tk.StringVar(value="stable")
        # Combined selector
        self.preset_var = tk.StringVar(value="opus_stable")
        presets = [
            ("Opus Stable 192k — RECOMMANDÉ wifi pourri (8x moins de bande, qualité transparente)", "opus_stable"),
            ("PCM Stable — lossless, latence ~600ms (qualité max, stable)", "pcm_stable"),
            ("PCM Fast Low-Latency — ~60ms (saccades si wifi pourri)", "pcm_fast"),
        ]
        for txt, val in presets:
            ttk.Radiobutton(mode, text=txt, variable=self.preset_var, value=val).pack(anchor="w", pady=1)
        ttk.Label(mode, text="Opus 192k = transparent pour l'oreille, 8x moins de données => beaucoup moins de saccades", font=("Arial", 7), foreground="#555").pack(anchor="w")

        # Control frame
        ctrl = ttk.Frame(self, padding=10)
        ctrl.pack(fill="x", padx=10)
        self.connect_btn = ttk.Button(ctrl, text="▶ CONNECTER", command=self.connect, style="Accent.TButton")
        self.connect_btn.pack(side="left", padx=5, ipadx=10, ipady=5)
        self.disconnect_btn = ttk.Button(ctrl, text="■ STOP", command=self.disconnect)
        self.disconnect_btn.pack(side="left", padx=5, ipadx=10)
        self.test_tone_btn = ttk.Button(ctrl, text="♪ Test son 3s", command=self.test_tone)
        self.test_tone_btn.pack(side="left", padx=5)
        self.status_lbl = ttk.Label(ctrl, text="● déconnecté", foreground="red", font=("Arial", 10, "bold"))
        self.status_lbl.pack(side="right")

        # Volume frame
        vol = ttk.LabelFrame(self, text="Volume KRK (AudioBox)", padding=10)
        vol.pack(fill="x", padx=10, pady=5)
        rowv = ttk.Frame(vol)
        rowv.pack(fill="x")
        ttk.Label(rowv, text="Volume:").pack(side="left")
        self.vol_var = tk.IntVar(value=40)
        self.vol_scale = ttk.Scale(rowv, from_=0, to=100, variable=self.vol_var, orient="horizontal", length=400, command=self.on_vol_change)
        self.vol_scale.pack(side="left", padx=10, fill="x", expand=True)
        self.vol_lbl = ttk.Label(rowv, text="40%")
        self.vol_lbl.pack(side="left")
        ttk.Button(rowv, text="Appliquer", command=self.apply_volume).pack(side="left", padx=5)
        ttk.Button(vol, text="🔄 Récupérer volume actuel", command=self.fetch_volume).pack(anchor="w", pady=2)

        # Log frame
        logf = ttk.LabelFrame(self, text="Logs", padding=5)
        logf.pack(fill="both", expand=True, padx=10, pady=5)
        self.log = scrolledtext.ScrolledText(logf, height=12, font=("Monospace", 7))
        self.log.pack(fill="both", expand=True)
        btnlog = ttk.Frame(logf)
        btnlog.pack(fill="x")
        ttk.Button(btnlog, text="Rafraîchir logs", command=self.refresh_logs).pack(side="left")
        ttk.Button(btnlog, text="Effacer", command=lambda: self.log.delete(1.0, tk.END)).pack(side="left", padx=5)
        ttk.Button(btnlog, text="Status détaillé", command=self.detailed_status).pack(side="left", padx=5)

        # Init volume fetch
        self.after(1000, self.fetch_volume)
        self.after(2000, self.auto_status_check)
        self.log_msg(f"GUI prêt. PC IP: {self.pc_ip}\nScripts: {PC_STREAM.name}, {RPI_RECEIVE.name}\nSélectionne Opus Stable pour wifi pourri (recommandé).\n")

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        print(msg)

    def get_preset(self):
        p = self.preset_var.get()
        if p == "opus_stable":
            return ("opus", "stable")
        elif p == "pcm_stable":
            return ("pcm", "stable")
        else:
            return ("pcm", "fast")

    def scan_network(self):
        self.scan_btn.config(state="disabled", text="Scan en cours...")
        self.scan_results.clear()
        self.scan_list.delete(0, tk.END)
        self.log_msg("Scan 192.168.1.0/24 en cours (ping + ssh)...")
        def do_scan():
            base = "192.168.1."
            candidates = []
            # ping sweep rapide avec threads
            def ping(ip):
                out, code = run_cmd(f"ping -c 1 -W 0.5 {ip} > /dev/null 2>&1; echo $?", timeout=2)
                # fallback: check via bash return code direct
                try:
                    subprocess.run(["ping","-c","1","-W","1",ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
                    return ip
                except:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
                futures = {ex.submit(ping, f"{base}{i}"): i for i in range(1,255)}
                reachable = []
                for fut in concurrent.futures.as_completed(futures):
                    r = fut.result()
                    if r:
                        reachable.append(r)
            self.log_msg(f"{len(reachable)} hôtes joignables: {', '.join(sorted(reachable)[:10])}{'...' if len(reachable)>10 else ''}")
            # Pour chaque joignable, test ssh AudioBox
            for ip in sorted(reachable, key=lambda x: int(x.split('.')[-1])):
                # test ssh avec user/pass saisis, check AudioBox
                user = self.user_var.get().strip()
                pwd = self.pass_var.get()
                out, code = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 {user}@{ip} \"hostname; aplay -l 2>&1 | grep -i AudioBox; wpctl status 2>&1 | grep -i AudioBox\" 2>&1", timeout=4)
                if "AudioBox" in out:
                    candidates.append((ip, out.strip().splitlines()[0] if out else ip))
                    self.log_msg(f"✓ Pi candidat trouvé: {ip} -> {out[:80]}")
                    # update UI thread safe
                    self.after(0, lambda ip=ip: self.scan_list.insert(tk.END, f"{ip} - AudioBox KRK"))
                elif "raspberry" in out.lower() or "timo" in out.lower():
                    self.log_msg(f"· {ip} répond ssh mais pas AudioBox")
            if not candidates:
                self.log_msg("Aucun Pi avec AudioBox trouvé. Vérifie user/pass ou branchement USB.")
                self.after(0, lambda: self.scan_list.insert(tk.END, "— aucun Pi AudioBox trouvé —"))
            self.after(0, lambda: self.scan_btn.config(state="normal", text="🔍 Scanner réseau"))
            self.scan_results = candidates
        threading.Thread(target=do_scan, daemon=True).start()

    def on_scan_select(self, evt):
        sel = self.scan_list.curselection()
        if not sel: return
        txt = self.scan_list.get(sel[0])
        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", txt)
        if m:
            self.pi_ip_var.set(m.group(1))
            self.log_msg(f"IP sélectionnée: {m.group(1)}")

    def test_ssh(self):
        ip = self.pi_ip_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        self.log_msg(f"Test SSH {user}@{ip} ...")
        def do_test():
            out, code = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 {user}@{ip} \"hostname; whoami; pactl info 2>&1 | head -5; aplay -l 2>&1 | grep AudioBox; wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1\" 2>&1", timeout=5)
            self.log_msg(out)
            if "AudioBox" in out or "PulseAudio" in out:
                self.pi_status.config(text="● connecté", foreground="green")
                # fetch volume
                m = re.search(r"Volume:\s*([\d\.]+)", out)
                if m:
                    try:
                        v = float(m.group(1))*100
                        self.vol_var.set(int(v))
                        self.vol_lbl.config(text=f"{int(v)}%")
                    except: pass
            else:
                self.pi_status.config(text="● échec", foreground="red")
        threading.Thread(target=do_test, daemon=True).start()

    def fetch_volume(self):
        ip = self.pi_ip_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        def do_fetch():
            out, _ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>&1; pactl get-sink-volume @DEFAULT_SINK@ 2>&1\" 2>&1", timeout=3)
            # wpctl output: Volume: 0.40
            m = re.search(r"Volume:\s*([\d\.]+)", out)
            if m:
                try:
                    v = float(m.group(1))*100
                    self.after(0, lambda: (self.vol_var.set(int(v)), self.vol_lbl.config(text=f"{int(v)}%")))
                except: pass
            else:
                # try pactl 45%
                m2 = re.search(r"(\d+)%", out)
                if m2:
                    try:
                        v=int(m2.group(1))
                        self.after(0, lambda: (self.vol_var.set(v), self.vol_lbl.config(text=f"{v}%")))
                    except: pass
            self.after(0, lambda: self.log_msg(f"Volume actuel: {out.strip()}"))
        threading.Thread(target=do_fetch, daemon=True).start()

    def on_vol_change(self, val):
        v = int(float(val))
        self.vol_lbl.config(text=f"{v}%")
        # on ne applique pas auto, doit cliquer Appliquer pour éviter spam ssh

    def apply_volume(self):
        v = self.vol_var.get()
        frac = v/100.0
        ip = self.pi_ip_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        self.log_msg(f"Volume -> {v}% ({frac:.2f})")
        def do_apply():
            out, _ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"wpctl set-volume @DEFAULT_AUDIO_SINK@ {frac:.2f} 2>&1; wpctl get-volume @DEFAULT_AUDIO_SINK@\" 2>&1", timeout=3)
            self.log_msg(out.strip())
        threading.Thread(target=do_apply, daemon=True).start()

    def connect(self):
        codec, mode = self.get_preset()
        ip = self.pi_ip_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        pc_ip = self.pc_ip
        self.log_msg(f"=== CONNECT {codec}/{mode} : PC {pc_ip} -> RPi {ip}:4711 ===")
        self.connect_btn.config(state="disabled")
        def do_connect():
            # Stop anciens
            self.log_msg("Stop anciens flux...")
            run_cmd("pkill -9 ffmpeg 2>/dev/null; echo ok", timeout=3)
            run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; sleep 0.5; echo ok\" 2>&1", timeout=4)
            # Copie receiver
            self.log_msg("Copie rpi_receive_v2.sh sur Pi...")
            out, code = run_cmd(f"sshpass -p '{pwd}' scp -o StrictHostKeyChecking=no {shlex.quote(str(RPI_RECEIVE))} {user}@{ip}:/tmp/rpi_receive_v2.sh 2>&1", timeout=5)
            self.log_msg(out)
            run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"chmod +x /tmp/rpi_receive_v2.sh\" 2>&1", timeout=3)
            # Lance receiver sur Pi
            self.log_msg(f"Lancement receiver sur Pi: {codec} {mode}")
            out, _ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"nohup /tmp/rpi_receive_v2.sh {pc_ip} {codec} {mode} 4711 > /tmp/rpi_recv.log 2>&1 & echo \\$!; sleep 1; cat /tmp/rpi_recv.log | head -20; ps aux | grep ffmpeg | grep -v grep\" 2>&1", timeout=6)
            self.log_msg(out)
            if "ffmpeg" not in out and "Lavf" not in out:
                # peut etre encore en démarrage
                pass
            # Lance sender sur PC
            self.log_msg(f"Lancement sender sur PC: {codec} {mode} -> {ip}")
            # vérifie PC stream existe
            if not PC_STREAM.exists():
                self.log_msg(f"ERREUR: {PC_STREAM} introuvable!")
                self.after(0, lambda: self.connect_btn.config(state="normal"))
                return
            # nohup local
            cmd = f"nohup {shlex.quote(str(PC_STREAM))} {ip} {codec} {mode} 4711 > /tmp/pc_stream.log 2>&1 & echo $!"
            out, _ = run_cmd(cmd, timeout=4)
            self.log_msg(f"PC sender PID:{out.strip()}")
            time.sleep(2)
            out2, _ = run_cmd("cat /tmp/pc_stream.log | tail -20; ps aux | grep \"ffmpeg.*udp://\" | grep -v grep", timeout=3)
            self.log_msg(out2)
            out3, _ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"cat /tmp/rpi_recv.log | tail -20; wpctl status 2>&1 | grep -A2 Streams | head -10\" 2>&1", timeout=4)
            self.log_msg("— RPi log —\n" + out3)
            # check both running
            pc_run = "ffmpeg" in out2
            rpi_run = "ffmpeg" in out3
            if pc_run and rpi_run:
                self.after(0, lambda: self.status_lbl.config(text="● connecté ✓", foreground="green"))
                self.after(0, lambda: messagebox.showinfo("Connecté", f"Streaming actif !\n{codec} / {mode}\nPC -> {ip}:4711 -> KRK\nJoue de la musique sur le PC."))
            else:
                self.after(0, lambda: self.status_lbl.config(text="● erreur", foreground="orange"))
                self.log_msg("Erreur: un des flux n'a pas démarré, vérifie logs.")
            self.after(0, lambda: self.connect_btn.config(state="normal"))
        threading.Thread(target=do_connect, daemon=True).start()

    def disconnect(self):
        ip = self.pi_ip_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        self.log_msg("=== STOP ===")
        def do_disc():
            out,_ = run_cmd("pkill -9 ffmpeg; echo pc stopped", timeout=3)
            self.log_msg(out)
            out2,_ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"pkill -9 ffmpeg; echo rpi stopped; ps aux | grep ffmpeg | grep -v grep || echo clean\" 2>&1", timeout=4)
            self.log_msg(out2)
            self.after(0, lambda: self.status_lbl.config(text="● déconnecté", foreground="red"))
        threading.Thread(target=do_disc, daemon=True).start()

    def test_tone(self):
        self.log_msg("Test tone 440Hz 3s sur PC (doit sortir KRK)...")
        def do_tone():
            out,_ = run_cmd("timeout 4 ffmpeg -hide_banner -loglevel error -f lavfi -i \"sine=frequency=440:duration=3,volume=0.5\" -f pulse default 2>&1 & sleep 1; echo tone-playing", timeout=5)
            self.log_msg(out)
            self.log_msg("Tone envoyé - écoute KRK !")
        threading.Thread(target=do_tone, daemon=True).start()

    def refresh_logs(self):
        def do_logs():
            out,_ = run_cmd("cat /tmp/pc_stream.log 2>&1 | tail -40", timeout=2)
            out2,_ = run_cmd(f"sshpass -p '{self.pass_var.get()}' ssh -o StrictHostKeyChecking=no {self.user_var.get()}@{self.pi_ip_var.get()} \"cat /tmp/rpi_recv.log 2>&1 | tail -40\" 2>&1", timeout=3)
            self.after(0, lambda: self.log.insert(tk.END, f"\n--- PC log ---\n{out}\n--- RPi log ---\n{out2}\n"))
            self.after(0, lambda: self.log.see(tk.END))
        threading.Thread(target=do_logs, daemon=True).start()

    def detailed_status(self):
        def do_stat():
            out,_ = run_cmd("ps aux | grep ffmpeg | grep -v grep; echo '---'; cat /tmp/pc_stream.log 2>&1 | tail -10", timeout=3)
            ip=self.pi_ip_var.get(); user=self.user_var.get(); pwd=self.pass_var.get()
            out2,_ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"ps aux | grep ffmpeg | grep -v grep; echo '---'; cat /tmp/rpi_recv.log | tail -10; echo '---'; wpctl status 2>&1 | grep -A5 Sinks\" 2>&1", timeout=4)
            self.after(0, lambda: messagebox.showinfo("Status détaillé", f"PC:\n{out}\n\nRPi:\n{out2}"))
        threading.Thread(target=do_stat, daemon=True).start()

    def auto_status_check(self):
        # check si ffmpeg tourne des deux côtés
        def do_check():
            out,_ = run_cmd("ps aux | grep \"ffmpeg.*udp\" | grep -v grep", timeout=2)
            pc = "ffmpeg" in out
            ip=self.pi_ip_var.get(); user=self.user_var.get(); pwd=self.pass_var.get()
            out2,_ = run_cmd(f"sshpass -p '{pwd}' ssh -o StrictHostKeyChecking=no {user}@{ip} \"ps aux | grep ffmpeg | grep -v grep\" 2>&1", timeout=3)
            rpi = "ffmpeg" in out2
            if pc and rpi:
                self.after(0, lambda: self.status_lbl.config(text="● connecté ✓", foreground="green"))
            elif pc or rpi:
                self.after(0, lambda: self.status_lbl.config(text="● partiel", foreground="orange"))
            else:
                self.after(0, lambda: self.status_lbl.config(text="● déconnecté", foreground="red"))
        threading.Thread(target=do_check, daemon=True).start()
        self.after(5000, self.auto_status_check)

if __name__ == "__main__":
    # verif dépendances
    if not PC_STREAM.exists():
        print(f"ERREUR: {PC_STREAM} introuvable. Lance depuis {PROJECT_DIR}")
        sys.exit(1)
    app = App()
    app.mainloop()
