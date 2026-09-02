#!/bin/bash
# PC Bluetooth connect to RPi
set -e
RPI_MAC="${1:-2C:CF:67:00:AC:EE}"
ACTION="${2:-connect}" # scan, pair, connect, disconnect, status

PC_BT_CTL="bluetoothctl"

case "$ACTION" in
  scan)
    echo "Scan Bluetooth 8s..."
    timeout 8 bluetoothctl --timeout 8 scan on 2>&1 | head -40 || timeout 8 bash -c 'bluetoothctl scan on 2>&1 & sleep 8; bluetoothctl devices 2>&1 | head -20; bluetoothctl scan off 2>&1 | head' 2>&1 | head -40
    bluetoothctl devices 2>&1 | grep -i raspberry -A2 -B2 | head -20
    bluetoothctl devices 2>&1 | head -20
    ;;
  pair)
    echo "Pair $RPI_MAC"
    bluetoothctl pair "$RPI_MAC" 2>&1 | tail -20
    bluetoothctl trust "$RPI_MAC" 2>&1 | tail -5
    ;;
  connect)
    echo "Connect $RPI_MAC"
    # Ensure adapter powered and discoverable
    rfkill unblock bluetooth 2>/dev/null || true
    bluetoothctl power on 2>&1 | head -3
    sleep 1
    # Pair if not already
    if ! bluetoothctl info "$RPI_MAC" 2>&1 | grep -q "Paired: yes"; then
      echo "Pairing..."
      bluetoothctl pair "$RPI_MAC" 2>&1 | tail -20
      bluetoothctl trust "$RPI_MAC" 2>&1 | tail -5
      sleep 1
    fi
    bluetoothctl connect "$RPI_MAC" 2>&1 | tail -30
    echo "Attente profil A2DP..."
    sleep 3
    # Force A2DP sink profile (au lieu de HSP/HFP)
    BLUEZ_CARD=$(pactl list cards 2>&1 | grep -B5 "bluez" | grep "Name: bluez_card" | head -1 | awk '{print $2}')
    if [ -z "$BLUEZ_CARD" ]; then
      BLUEZ_CARD=$(pactl list short cards 2>&1 | grep bluez | head -1 | awk '{print $2}')
    fi
    if [ -n "$BLUEZ_CARD" ]; then
      echo "Carte BT: $BLUEZ_CARD -> a2dp-sink"
      pactl set-card-profile "$BLUEZ_CARD" a2dp-sink 2>&1 | head -5
      # PipeWire alternative
      wpctl set-profile "$BLUEZ_CARD" a2dp-sink 2>&1 | head -5 || true
      sleep 1
    fi
    pactl list cards 2>&1 | grep -A2 "bluez" | head -20
    pactl list short sinks 2>&1 | grep bluez | head -10
    wpctl status 2>&1 | grep -A3 "Sinks:" | head -20
    BT_SINK=$(pactl list short sinks 2>&1 | grep bluez | grep a2dp | head -1 | awk '{print $2}')
    if [ -z "$BT_SINK" ]; then BT_SINK=$(pactl list short sinks 2>&1 | grep bluez | head -1 | awk '{print $2}'); fi
    # PipeWire wpctl fallback
    if [ -z "$BT_SINK" ]; then
      BT_SINK=$(wpctl status 2>&1 | grep -A20 "Sinks:" | grep bluez | head -1 | awk '{print $4}')
    fi
    if [ -n "$BT_SINK" ]; then
      echo "BT Sink: $BT_SINK"
      pactl set-default-sink "$BT_SINK" 2>&1 | head
      wpctl set-default "$BT_SINK" 2>&1 | head || true
      pactl info 2>&1 | grep "Default Sink"
      wpctl status 2>&1 | grep -A2 "Sinks:" | head -10
      echo "Audio PC maintenant vers Pi via Bluetooth (A2DP)"
    else
      echo "Pas de sink BT trouvé, vérifie appariement/profil"
      pactl list short sinks 2>&1 | head -10
      pactl list cards 2>&1 | head -40
      wpctl status 2>&1 | head -60
    fi
    ;;
  disconnect)
    bluetoothctl disconnect "$RPI_MAC" 2>&1 | tail -10
    ;;
  status)
    bluetoothctl info "$RPI_MAC" 2>&1 | head -40
    pactl list short sinks 2>&1 | grep bluez | head -10
    pactl info 2>&1 | grep "Default Sink"
    bluetoothctl show 2>&1 | grep -E "Powered|Discoverable"
    ;;
  poweron)
    rfkill unblock bluetooth 2>&1 | head
    bluetoothctl power on 2>&1 | head
    ;;
  *)
    echo "Usage: $0 <RPI_MAC> {scan|pair|connect|disconnect|status|poweron}"
    ;;
esac
