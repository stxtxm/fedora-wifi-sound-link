#!/bin/bash
# RPi Bluetooth A2DP Sink setup - rend le Pi visible et route vers AudioBox
set -e
ACTION="${1:-setup}" # setup, discoverable, status, route
case "$ACTION" in
  setup)
    echo "=== RPi BT Sink setup ==="
    # Assure PipeWire bluetooth
    systemctl --user is-active pipewire 2>&1 | head
    # Active bluetooth
    bluetoothctl power on 2>&1 | head
    bluetoothctl discoverable on 2>&1 | head
    bluetoothctl pairable on 2>&1 | head
    bluetoothctl agent NoInputNoOutput 2>&1 | head
    bluetoothctl default-agent 2>&1 | head
    echo "Discoverable: $(bluetoothctl show 2>&1 | grep Discoverable)"
    echo "Pairable: $(bluetoothctl show 2>&1 | grep Pairable)"
    # Vérifie AudioBox sink
    SINK=$(pactl info 2>&1 | grep "Default Sink" || wpctl status 2>&1 | grep -A2 Sinks | grep AudioBox)
    echo "Sink AudioBox: $SINK"
    echo "En attente de connexion Bluetooth depuis PC..."
    # WirePlumber linkera auto le bluez_input vers AudioBox
    # On peut forcer avec pw-link si besoin
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
    BT_SOURCE=$(pactl list short sources 2>&1 | grep bluez | grep input | head -1 | awk '{print $2}')
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
