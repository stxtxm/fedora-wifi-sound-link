# Fedora Wifi Sound Link

**PC → Raspberry Pi → KRK** — Streaming audio haute-fidélité sur wifi, même pourri.

> Fedora (PipeWire) → Raspberry Pi (AudioBox USB 96) → KRK Rokit. Latence maîtrisée, qualité studio, anti-saccades.

![icon](assets/icon-256.png)

### Pourquoi ce projet ?

Envoyer le son du PC vers un Pi branché à une interface audio + enceintes KRK sans câble, sur un wifi moyen, sans craquement ni coupure, sans perte de qualité. Les solutions classiques (Soundwire, PulseAudio tunnel, ffmpeg brut) saccadent dès que le wifi est chargé. Ici on utilise **Roc Toolkit** (FEC + jitter buffer adaptatif) avec fallback **ffmpeg** optimisé.

### Features

- 🚀 **1-clic GUI** compacte ultra-moderne (CustomTkinter, dark, VU-meter)
- 🔍 **Auto-détection Pi** sur le réseau (scan 192.168.1.0/24 + test AudioBox)
- 🎛️ **Modes**: `ROC Stable` (recommandé), `Opus Stable 192k`, `PCM Stable/Fast`
- 🔊 **Volume KRK** direct (`wpctl`) + VU temps réel
- 🛜 **Anti-saccades**: buffer adaptatif, `aresample` haute qualité, FEC Roc, 8x moins de bande en Opus
- 🧪 **CI + tests auto**

### Architecture

```
PC (Fedora, PipeWire) --pulse monitor--> [pc_sender.sh] --udp/roc--> [rpi_receiver.sh] --pulse--> AudioBox USB 96 --> KRK
```

- `src/stream/pc_sender.sh` : capture `pactl get-default-sink).monitor` → encode (Roc/Opus/PCM) → UDP
- `src/stream/rpi_receiver.sh` : écoute `udp://0.0.0.0:4711` → `aresample` (drift) → `pulse default` (AudioBox)
- `src/gui/modern_app.py` : GUI CustomTkinter

### Installation

#### PC (Fedora 44)
```bash
sudo dnf install -y ffmpeg roc-toolkit-utils pipewire-pulse pulseaudio-utils gstreamer1
pip install customtkinter pillow
git clone https://github.com/timo/fedora-wifi-sound-link.git
cd fedora-wifi-sound-link
```

#### Raspberry Pi (Debian/Raspberry Pi OS)
```bash
sudo apt update && sudo apt install -y ffmpeg roc-toolkit-tools pipewire pipewire-pulse wireplumber pulseaudio-utils alsa-utils
# Vérifier AudioBox
aplay -l | grep AudioBox
wpctl status
```

### Usage

#### GUI (recommandé)
```bash
python3 src/gui/modern_app.py
# ou
python3 -m src.gui.modern_app
```
1. **Scan** → sélectionne le Pi avec AudioBox
2. Choisis **ROC Stable** (wifi pourri) ou **PCM Stable**
3. **CONNECTER** → joue ta musique sur le PC

#### CLI
```bash
# Sur RPi (ou via GUI)
./src/stream/rpi_receiver.sh 192.168.1.108 roc stable 4711
# Sur PC
./src/stream/pc_sender.sh 192.168.1.101 roc stable 4711
# Test tone
ffmpeg -f lavfi -i "sine=frequency=440:duration=3" -f pulse default
# Volume
ssh timo@192.168.1.101 "wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.6"
```

### Modes détaillés

| Mode | Codec | Bande | Latence | Qualité | Wifi |
|---|---|---|---|---|---|
| **ROC Stable** | Roc (FEC rs8m) | ~400k | 300ms | Studio | ★★★★★ |
| Opus Stable | Opus 192k VBR | 192k | 300ms | Transparent | ★★★★ |
| PCM Stable | PCM S32LE | 3072k | 600ms | Lossless | ★★★ |
| PCM Fast | PCM S16LE | 1536k | 60ms | Lossless | ★★ |

*ROC = Real-time streaming avec Reed-Solomon FEC + jitter buffer adaptatif + resampler haute qualité. Tolère 10-15% packet loss.*

### Dépannage craquements/saccades

Même en Opus tu avais des craquements -> source: **drift d'horloge** + **buffer trop petit** + **resampler basse qualité**.

Fix v3:
- `aresample=async=1:filter_size=32:cutoff=0.95:linear_interp=0` (au lieu de 16)
- `thread_queue_size 2048` + `buffer_size 262144` + `fifo_size 8192`
- `Roc` avec `--resampler-profile high` + FEC `rs8m` + target latency 300ms
- Envoi `S32LE` natif AudioBox (évite double conversion S16→S32)

Logs temps réel:
```bash
cat /tmp/pc_stream.log | tail -f
ssh timo@192.168.1.101 "cat /tmp/rpi_recv.log | tail -f"
wpctl status | grep Streams
pw-top
```

### Structure

```
.
├── src/
│   ├── stream/pc_sender.sh
│   ├── stream/rpi_receiver.sh
│   └── gui/modern_app.py
├── assets/icon*.png/svg
├── tests/
├── .github/workflows/ci.yml
└── docs/
```

### Tests & CI

```bash
pytest tests/ -v
bash tests/diagnose_flux.sh
```

CI GitHub Actions: lint, shellcheck, pytest, build. `master` protégé: merge uniquement si CI passe + approbation.

### Licence

MIT — Timo

### Crédits

Roc Toolkit, PipeWire, FFmpeg, CustomTkinter.

> **Live testé**: ROC Stable 300ms FEC = zéro craquement sur wifi pourri (testé 192.168.1.108 → 192.168.1.101 AudioBox → KRK)

## AppImage

Télécharge la dernière release:

**https://github.com/stxtxm/fedora-wifi-sound-link/releases/latest**

```bash
chmod +x Fedora_Wifi_Sound_Link-x86_64.AppImage
./Fedora_Wifi_Sound_Link-x86_64.AppImage
```

L'AppImage embarque Python + customtkinter + pillow, aucune install nécessaire (sauf ffmpeg/roc sur le système).

Build local:
```bash
make appimage  # nécessite appimagetool + mksquashfs
```

## 📱 Téléphone → Pi → KRK (Bluetooth)

Le Pi est aussi une enceinte Bluetooth pour ton tel.

### PWA (recommandé, sans install)
1. Sur le Pi, le serveur PWA tourne déjà (port 8080) via `krk-pwa.service`
2. Sur ton tel (même WiFi), ouvre `http://192.168.1.101:8080` ou `http://raspberrypi.local:8080`
3. **Installer** → Ajouter à l'écran d'accueil → PWA
4. Dans la PWA: **Rendre visible** → sur ton tel: Bluetooth → appaire `raspberrypi` → joue de la musique → son sur KRK

API PWA:
- `GET /api/status` → état BT + volume
- `POST /api/bt/discoverable` → rend Pi visible
- `POST /api/bt/scan` → scan BT
- `POST /api/volume` → `{"volume": 60}`

### APK Android
APK WebView qui encapsule la PWA + permissions Bluetooth.

- Source: `android/` (gradle)
- Build: `cd android && ./gradlew assembleDebug` (nécessite Android SDK)
- CI build l'APK automatiquement (GitHub Actions)
- Release: `KRKLink.apk` dans https://github.com/stxtxm/fedora-wifi-sound-link/releases

```bash
adb install KRKLink.apk
# Ouvre l'app → elle charge http://192.168.1.101:8080
```

### Mode Bluetooth dans la GUI PC
Onglet **Bluetooth** dans la GUI moderne:
- `Scan BT` → détecte `raspberrypi` (MAC `2C:CF:67:00:AC:EE`)
- `Pair + Connect` → `bluetoothctl pair/trust/connect` + `pactl set-default-sink bluez_output...` + route `module-loopback` vers AudioBox
- `Power ON` → `rfkill unblock` + `bluetoothctl discoverable on` sur Pi

> Responsive: GUI s'adapte à toutes les tailles (min 380px), scrollable, VU réactif.
