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
    bluetoothctl connect "$RPI_MAC" 2>&1 | tail -30
    sleep 2
    pactl list short sinks 2>&1 | grep bluez | head -5
    BT_SINK=$(pactl list short sinks 2>&1 | grep bluez | grep -i "$RPI_MAC" | head -1 | awk '{print $2}')
    if [ -z "$BT_SINK" ]; then BT_SINK=$(pactl list short sinks 2>&1 | grep bluez | head -1 | awk '{print $2}'); fi
    if [ -n "$BT_SINK" ]; then
      echo "BT Sink: $BT_SINK"
      pactl set-default-sink "$BT_SINK" 2>&1 | head
      pactl info 2>&1 | grep "Default Sink"
      echo "Audio PC maintenant vers Pi via Bluetooth"
    else
      echo "Pas de sink BT trouvé, vérifie appariement"
      pactl list short sinks 2>&1 | head -10
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
