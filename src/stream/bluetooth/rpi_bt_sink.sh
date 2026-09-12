#!/bin/bash
# RPi Bluetooth A2DP Sink setup - rend le Pi visible et route vers AudioBox
set -e
ACTION="${1:-setup}" # setup, discoverable, status, route
case "$ACTION" in
  setup)
    WATCHER_PID_FILE=/tmp/krk-bt-watcher.pid
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
    echo "Discoverable: $(bluetoothctl show 2>&1 | grep Discoverable)"
    echo "Pairable: $(bluetoothctl show 2>&1 | grep Pairable)"
    SINK=$(pactl get-default-sink 2>&1)
    echo "Sink AudioBox: $SINK"
    wpctl status 2>&1 | grep -A5 "Sinks:" | head -15
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
    nohup bash -c 'while true; do
      BT_CARD=$(pactl list short cards 2>/dev/null | awk "\$2 ~ /^bluez_card/ {print \$2; exit}")
      if [ -n "$BT_CARD" ]; then
        # Changing the profile repeatedly renegotiates A2DP and disconnects some phones.
        BT_PROFILE=$(pactl get-card-profile "$BT_CARD" 2>/dev/null || true)
        if [ "$BT_PROFILE" != "a2dp-sink" ]; then
          pactl set-card-profile "$BT_CARD" a2dp-sink >/dev/null 2>&1 || true
          sleep 1
          continue
        fi
      fi
      BT_SRC=$(pactl list short sources 2>/dev/null | awk "\$2 ~ /^bluez_(input|source)/ {print \$2; exit}")
      SINK=$(pactl list short sinks 2>/dev/null | awk "\$2 ~ /AudioBox/ {print \$2; exit}")
      if [ -z "$SINK" ]; then
        SINK=$(pactl get-default-sink 2>/dev/null | tr -d " ")
      fi
      if [ -n "$BT_SRC" ] && [ -n "$SINK" ] &&
         ! pactl list short modules 2>/dev/null | grep -q "source=$BT_SRC.*sink=$SINK"; then
        echo "[watcher] Routing $BT_SRC -> $SINK"
        pactl load-module module-loopback source="$BT_SRC" sink="$SINK" latency_msec=100 adjust_time=1 >/dev/null 2>&1 || true
      fi
      sleep 2
    done' > /tmp/bt_watcher.log 2>&1 &
    echo "$!" > "$WATCHER_PID_FILE"
    echo "Watcher Bluetooth -> KRK lancé (PID $!)"
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
    bluetoothctl paired-devices 2>&1 | head -10 || bluetoothctl devices Paired 2>&1 | head -10
    pactl list short sinks 2>&1 | head -10
    pactl list short sources 2>&1 | head -10
    wpctl status 2>&1 | head -40
    ;;
  route)
    # Force route BT source -> AudioBox sink si WirePlumber ne le fait pas
    BT_SOURCE=$(pactl list short sources 2>&1 | awk '$2 ~ /^bluez_(input|source)/ {print $2; exit}')
    SINK=$(pactl list short sinks 2>&1 | grep AudioBox | head -1 | awk '{print $2}')
    if [ -z "$SINK" ]; then SINK=$(pactl get-default-sink 2>&1); fi
    if [ -n "$BT_SOURCE" ] && [ -n "$SINK" ]; then
      echo "Routing $BT_SOURCE -> $SINK"
      pactl load-module module-loopback source="$BT_SOURCE" sink="$SINK" latency_msec=50 2>&1 | head
    else
      echo "Pas de source BT active ou sink AudioBox manquant"
      echo "BT_SOURCE=$BT_SOURCE SINK=$SINK"
    fi
    ;;
  *)
    echo "Usage: $0 {setup|discoverable|off|status|route}"
    ;;
esac
