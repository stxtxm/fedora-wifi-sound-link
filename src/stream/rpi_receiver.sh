#!/bin/bash
# Fedora Wifi Sound Link - RPi Receiver v3
set -e
PC_IP="${1:-192.168.1.108}"
CODEC="${2:-pcm}"
MODE="${3:-stable}"
PORT="${4:-4711}"
ROC_PORT="$PORT"; ROC_CTRL=$((PORT+1)); ROC_REPAIR=$((PORT+2))

echo "RPi Receiver $CODEC/$MODE on 0.0.0.0:$PORT -> AudioBox"
pactl info 2>&1 | grep -E "Default Sink|Server Name" || true
wpctl status 2>&1 | grep -A3 Sinks | head -10 || true

if [ "$CODEC" = "roc" ]; then
  if command -v roc-recv >/dev/null 2>&1; then
    LAT="--latency=300"
    if [ "$MODE" = "fast" ]; then LAT="--latency=80"; fi
    echo "ROC recv latency $LAT"
    exec roc-recv -v -o pulse://default --rate 48000 --format s16 --channels 2 -s rtp://0.0.0.0:$ROC_PORT -r rs8m://0.0.0.0:$ROC_REPAIR -c rtcp://0.0.0.0:$ROC_CTRL $LAT --resampler-profile high
  else
    echo "roc-recv manquant fallback PCM stable"
    CODEC="pcm"; MODE="stable"
  fi
fi

UDP_IN="udp://0.0.0.0:$PORT?buffer_size=262144&fifo_size=8192&overrun_nonfatal=1&timeout=10000000"
if [ "$CODEC" = "opus" ]; then
  exec ffmpeg -hide_banner -loglevel info -thread_queue_size 1024 -fflags nobuffer -analyzeduration 0 -probesize 32 -f ogg -i "$UDP_IN" -af aresample=async=1:min_hard_comp=0.100000:first_pts=0:osr=48000:filter_size=32:phase_shift=5:cutoff=0.9 -f pulse -buffer_size 4096 default
else
  # PCM natif: detect FMT via PCM_FMT env, sinon s16le
  FMT="s16le"
  if [ "$PCM_FMT" = "s32" ]; then FMT="s32le"; fi
  if [ "$MODE" = "stable" ]; then
    # stable: gros jitter buffer, resampler haute qualité pour drift horloge sans craquement
    exec ffmpeg -hide_banner -loglevel info -thread_queue_size 2048 -analyzeduration 0 -probesize 32 \
      -f $FMT -ar 48000 -ac 2 -i "$UDP_IN" \
      -af aresample=async=1:min_hard_comp=0.100000:first_pts=0:osr=48000:filter_size=32:phase_shift=5:cutoff=0.95:linear_interp=0 \
      -f pulse -buffer_size 4096 default
  else
    # fast: low delay, pas de resample lourd
    exec ffmpeg -hide_banner -loglevel info -fflags nobuffer -flags low_delay -probesize 32 -thread_queue_size 512 \
      -f $FMT -ar 48000 -ac 2 -i "udp://0.0.0.0:$PORT?buffer_size=65536&fifo_size=1024&overrun_nonfatal=1" \
      -f pulse -buffer_size 1024 default
  fi
fi
