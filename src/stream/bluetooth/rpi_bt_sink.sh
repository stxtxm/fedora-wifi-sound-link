#!/bin/bash
# RPi Bluetooth A2DP Sink setup - rend le Pi visible et route vers AudioBox
set -e
ACTION="${1:-setup}" # setup, discoverable, status, route

# Bluetooth audio belongs to the graphical PipeWire session on the Pi.  Do
# not assume that the SSH user owns that session; locate the runtime that has
# the AudioBox sink and execute PulseAudio-compatible commands there.
# Prefer the session that owns the Bluetooth card.  A secondary user session
# may still expose the USB sink while being unable to acquire BlueZ.
AUDIO_UID=
for REQUIRE_BLUETOOTH in yes no; do
  for RUNTIME_DIR in /run/user/*; do
    [ -d "$RUNTIME_DIR" ] || continue
    CANDIDATE_UID=${RUNTIME_DIR##*/}
    AUDIO_INFO=$(sudo -n -u "#$CANDIDATE_UID" env XDG_RUNTIME_DIR="$RUNTIME_DIR" \
      pactl list short cards 2>/dev/null || true)
    if printf '%s\n' "$AUDIO_INFO" | grep -q bluez_card &&
       [ "$REQUIRE_BLUETOOTH" = yes ]; then
      AUDIO_UID=$CANDIDATE_UID
      break 2
    fi
    if [ "$REQUIRE_BLUETOOTH" = no ] &&
       sudo -n -u "#$CANDIDATE_UID" env XDG_RUNTIME_DIR="$RUNTIME_DIR" \
       pactl list short sinks 2>/dev/null | grep -q AudioBox; then
      AUDIO_UID=$CANDIDATE_UID
      break 2
    fi
  done
done
if [ -z "$AUDIO_UID" ]; then
  echo "Erreur: aucune session PipeWire avec AudioBox détectée" >&2
  exit 1
fi
AUDIO_RUNTIME_DIR="/run/user/$AUDIO_UID"
audio_pactl() {
  sudo -n -u "#$AUDIO_UID" env XDG_RUNTIME_DIR="$AUDIO_RUNTIME_DIR" pactl "$@"
}
audio_wpctl() {
  sudo -n -u "#$AUDIO_UID" env XDG_RUNTIME_DIR="$AUDIO_RUNTIME_DIR" wpctl "$@"
}

case "$ACTION" in
  setup)
    WATCHER_PID_FILE=/tmp/krk-bt-watcher.pid
    BT_WATCHDOG_PID_FILE=/tmp/krk-bt-watchdog.pid
    echo "=== RPi BT Sink setup ==="
    systemctl --user is-active pipewire 2>&1 | head -3
    systemctl --user is-active wireplumber 2>&1 | head -3
    # Active bluetooth + reste visible
    rfkill unblock bluetooth 2>/dev/null || true
    bluetoothctl power on 2>&1 | head -3
    sleep 1
    bluetoothctl discoverable on 2>&1 | head -3
    bluetoothctl pairable on 2>&1 | head -3
    bluetoothctl discoverable-timeout 0 2>&1 | head -3
    # Agent NoInputNoOutput en daemon (accepte tout sans écran)
    pkill -f "bluetoothctl --agent" 2>/dev/null || true
    nohup bluetoothctl --agent NoInputNoOutput > /tmp/bt_agent.log 2>&1 &
    sleep 1
    bluetoothctl default-agent 2>&1 | head -3 || echo "agent déjà par défaut"
    bluetoothctl system-alias raspberrypi 2>/dev/null || true
    for DEVICE_MAC in $(bluetoothctl devices 2>/dev/null | awk '{print $2}'); do
      if bluetoothctl info "$DEVICE_MAC" 2>/dev/null | grep -q "Paired: yes"; then
        bluetoothctl trust "$DEVICE_MAC" >/dev/null 2>&1 || true
      fi
    done
    echo "Discoverable: $(bluetoothctl show 2>&1 | grep Discoverable)"
    echo "Pairable: $(bluetoothctl show 2>&1 | grep Pairable)"
    SINK=$(audio_pactl get-default-sink 2>&1)
    echo "Sink AudioBox: $SINK"
    audio_wpctl status 2>&1 | grep -A5 "Sinks:" | head -15
    echo "En attente de connexion Bluetooth depuis PC..."
    echo "WirePlumber route auto Bluetooth A2DP -> AudioBox, sinon lance: $0 route"
    # Replace an older watcher; duplicate loopbacks can destabilize the Bluetooth source.
    while read -r OLD_PID; do
      [ "$OLD_PID" = "$$" ] || kill "$OLD_PID" 2>/dev/null || true
    done < <(pgrep -f '[b]t_watcher.log' || true)
    if [ -f "$WATCHER_PID_FILE" ]; then
      OLD_PID=$(cat "$WATCHER_PID_FILE")
      if kill -0 "$OLD_PID" 2>/dev/null; then kill "$OLD_PID" 2>/dev/null || true; fi
    fi
    # Lance un watcher en arrière-plan pour auto-route
    nohup bash -c 'AUDIO_UID='"$AUDIO_UID"'
    AUDIO_RUNTIME_DIR=/run/user/$AUDIO_UID
    audio_pactl() {
      sudo -n -u "#$AUDIO_UID" env XDG_RUNTIME_DIR="$AUDIO_RUNTIME_DIR" pactl "$@"
    }
    LOOPBACK_ID=
    LOOPBACK_SOURCE=
    LOOPBACK_SINK=
    while true; do
      BT_CARD=$(audio_pactl list short cards 2>/dev/null | awk "\$2 ~ /^bluez_card/ {print \$2; exit}")
      # Do not force a profile here.  PipeWire must negotiate A2DP with the
      # phone; repeatedly changing profiles can reset the Bluetooth transport.
      BT_SRC=$(audio_pactl list short sources 2>/dev/null | awk "\$2 ~ /^bluez_(input|source)/ {print \$2; exit}")
      SINK=$(audio_pactl list short sinks 2>/dev/null | awk "\$2 ~ /AudioBox/ {print \$2; exit}")
      if [ -z "$SINK" ]; then
        SINK=$(audio_pactl get-default-sink 2>/dev/null | tr -d " ")
      fi
      if [ -n "$LOOPBACK_ID" ] &&
         { [ "$BT_SRC" != "$LOOPBACK_SOURCE" ] || [ "$SINK" != "$LOOPBACK_SINK" ]; }; then
        audio_pactl unload-module "$LOOPBACK_ID" >/dev/null 2>&1 || true
        LOOPBACK_ID=
        LOOPBACK_SOURCE=
        LOOPBACK_SINK=
      fi
      if [ -z "$BT_SRC" ] || [ -z "$SINK" ]; then
        if [ -n "$LOOPBACK_ID" ]; then
          audio_pactl unload-module "$LOOPBACK_ID" >/dev/null 2>&1 || true
          LOOPBACK_ID=
          LOOPBACK_SOURCE=
          LOOPBACK_SINK=
        fi
      elif [ -z "$LOOPBACK_ID" ]; then
        echo "[watcher] Routing $BT_SRC -> $SINK"
        LOOPBACK_ID=$(audio_pactl load-module module-loopback source="$BT_SRC" sink="$SINK" latency_msec=100 adjust_time=1 2>/dev/null || true)
        LOOPBACK_SOURCE=$BT_SRC
        LOOPBACK_SINK=$SINK
      fi
      sleep 2
    done' > /tmp/bt_watcher.log 2>&1 &
    echo "$!" > "$WATCHER_PID_FILE"
    echo "Watcher Bluetooth -> KRK lancé (PID $!)"
    if [ -f "$BT_WATCHDOG_PID_FILE" ]; then
      OLD_PID=$(cat "$BT_WATCHDOG_PID_FILE")
      if kill -0 "$OLD_PID" 2>/dev/null; then kill "$OLD_PID" 2>/dev/null || true; fi
    fi
    nohup bash -c '
      while true; do
        bluetoothctl power on >/dev/null 2>&1 || true
        for DEVICE_MAC in $(bluetoothctl devices 2>/dev/null | awk "{print \$2}"); do
          DEVICE_INFO=$(bluetoothctl info "$DEVICE_MAC" 2>/dev/null || true)
          if printf "%s\n" "$DEVICE_INFO" | grep -q "Paired: yes" &&
             ! printf "%s\n" "$DEVICE_INFO" | grep -q "Connected: yes"; then
            bluetoothctl connect "$DEVICE_MAC" >>/tmp/bt_watchdog.log 2>&1 || true
          fi
        done
        sleep 15
      done
    ' >> /tmp/bt_watchdog.log 2>&1 &
    echo "$!" > "$BT_WATCHDOG_PID_FILE"
    echo "Watchdog Bluetooth actif (PID $!)"
    ;;
  discoverable)
    bluetoothctl discoverable on
    bluetoothctl pairable on
    echo "Pi discoverable ON"
    ;;
  off)
    bluetoothctl discoverable off
    bluetoothctl pairable off
    echo "Pi discoverable OFF"
    ;;
  status)
    bluetoothctl show 2>&1 | grep -E "Powered|Discoverable|Pairable|Name"
    bluetoothctl devices 2>&1 | head -10
    bluetoothctl devices 2>&1 | head -10
    audio_pactl list short sinks 2>&1 | head -10
    audio_pactl list short sources 2>&1 | head -10
    audio_wpctl status 2>&1 | head -40
    echo "Watchers:"
    for PID_FILE in /tmp/krk-bt-watcher.pid /tmp/krk-bt-watchdog.pid; do
      if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "  $PID_FILE: actif ($(cat "$PID_FILE"))"
      else
        echo "  $PID_FILE: arrêté"
      fi
    done
    echo "Derniers événements watchdog:"
    tail -10 /tmp/bt_watchdog.log 2>/dev/null || true
    ;;
  route)
    # Force route BT source -> AudioBox sink si WirePlumber ne le fait pas
    BT_SOURCE=$(audio_pactl list short sources 2>&1 | awk '$2 ~ /^bluez_(input|source)/ {print $2; exit}')
    SINK=$(audio_pactl list short sinks 2>&1 | grep AudioBox | head -1 | awk '{print $2}')
    if [ -z "$SINK" ]; then SINK=$(audio_pactl get-default-sink 2>&1); fi
    if [ -n "$BT_SOURCE" ] && [ -n "$SINK" ]; then
      echo "Routing $BT_SOURCE -> $SINK"
      audio_pactl load-module module-loopback source="$BT_SOURCE" sink="$SINK" latency_msec=50 2>&1 | head
    else
      echo "Pas de source BT active ou sink AudioBox manquant"
      echo "BT_SOURCE=$BT_SOURCE SINK=$SINK"
    fi
    ;;
  *)
    echo "Usage: $0 {setup|discoverable|off|status|route}"
    ;;
esac
