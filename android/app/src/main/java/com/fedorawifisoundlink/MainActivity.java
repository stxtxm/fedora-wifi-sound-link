package com.fedorawifisoundlink;
import android.Manifest;
import android.bluetooth.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.provider.Settings;
import android.media.AudioManager;
import android.widget.*;
import android.view.Gravity;
import android.graphics.Color;
import android.util.TypedValue;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import java.util.Set;

public class MainActivity extends AppCompatActivity {
    private static final String PI_MAC = "2C:CF:67:00:AC:EE";
    private static final String PI_NAME = "raspberrypi";
    private BluetoothAdapter btAdapter;
    private BluetoothA2dp a2dpProxy;
    private TextView statusText;
    private Button toggleBtn;
    private boolean isOn = false;
    private BluetoothDevice piDevice;
    private boolean waitingForSystemConnection;
    private AudioManager audioManager;

    private boolean hasBluetoothPermissions() {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.S) {
            return ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        }
        return ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                == PackageManager.PERMISSION_GRANTED
            && ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
                == PackageManager.PERMISSION_GRANTED;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        audioManager = (AudioManager) getSystemService(AUDIO_SERVICE);

        // Permissions Android 12+
        String[] perms = android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S
            ? new String[] { Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN }
            : new String[] { Manifest.permission.ACCESS_FINE_LOCATION };
        for (String p : perms) {
            if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, perms, 1);
                break;
            }
        }

        // UI programmatically - responsive, dark, compact
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.parseColor("#0f1115"));
        root.setPadding(32, 48, 32, 32);

        TextView title = new TextView(this);
        title.setText("KRK LINK");
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 26);
        title.setTextColor(Color.parseColor("#7c5cff"));
        title.setGravity(Gravity.CENTER);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Téléphone → RPi → AudioBox → KRK");
        subtitle.setTextSize(12);
        subtitle.setTextColor(Color.parseColor("#8b8fa3"));
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, 8, 0, 24);
        root.addView(subtitle);

        // Icon placeholder
        TextView icon = new TextView(this);
        icon.setText("♪");
        icon.setTextSize(48);
        icon.setTextColor(Color.parseColor("#00d9ff"));
        icon.setGravity(Gravity.CENTER);
        icon.setPadding(0, 16, 0, 16);
        root.addView(icon);

        statusText = new TextView(this);
        statusText.setText("Prêt — Appuie sur ACTIVER");
        statusText.setTextSize(13);
        statusText.setTextColor(Color.parseColor("#a8adc3"));
        statusText.setGravity(Gravity.CENTER);
        statusText.setPadding(0, 16, 0, 24);
        root.addView(statusText);

        toggleBtn = new Button(this);
        toggleBtn.setText("▶  ACTIVER SORTIE KRK");
        toggleBtn.setTextSize(16);
        toggleBtn.setTextColor(Color.WHITE);
        toggleBtn.setBackgroundColor(Color.parseColor("#7c5cff"));
        toggleBtn.setPadding(32, 24, 32, 24);
        // Rounded via background drawable
        toggleBtn.setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#7c5cff")));
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 140);
        btnParams.setMargins(0, 0, 0, 16);
        toggleBtn.setLayoutParams(btnParams);
        toggleBtn.setAllCaps(false);
        toggleBtn.setOnClickListener(v -> toggle());
        root.addView(toggleBtn);

        TextView volumeLabel = new TextView(this);
        volumeLabel.setText("VOLUME TÉLÉPHONE / BLUETOOTH");
        volumeLabel.setTextSize(11);
        volumeLabel.setTextColor(Color.parseColor("#8b8fa3"));
        volumeLabel.setPadding(0, 8, 0, 0);
        root.addView(volumeLabel);

        SeekBar volumeSlider = new SeekBar(this);
        volumeSlider.setMax(100);
        volumeSlider.setProgress(getMediaVolumePercent());
        volumeSlider.setContentDescription("Volume Bluetooth");
        volumeSlider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                if (fromUser) setMediaVolumePercent(progress);
            }
            public void onStartTrackingTouch(SeekBar seekBar) {}
            public void onStopTrackingTouch(SeekBar seekBar) {}
        });
        root.addView(volumeSlider, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView hint = new TextView(this);
        hint.setText("Le son du téléphone sortira sur les KRK via le Pi en Bluetooth.\nPas besoin de WiFi. Le Pi doit être allumé.");
        hint.setTextSize(11);
        hint.setTextColor(Color.parseColor("#5a5e73"));
        hint.setGravity(Gravity.CENTER);
        hint.setPadding(0, 8, 0, 0);
        root.addView(hint);

        TextView footer = new TextView(this);
        footer.setText("Pi: " + PI_NAME + " • " + PI_MAC + "\nAppuie = ON/OFF");
        footer.setTextSize(10);
        footer.setTextColor(Color.parseColor("#3a3e4d"));
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, 24, 0, 0);
        root.addView(footer);

        setContentView(root);

        initializeBluetooth();
        updateStatus();
    }

    private int getMediaVolumePercent() {
        if (audioManager == null) return 50;
        int max = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        if (max == 0) return 0;
        return Math.round(audioManager.getStreamVolume(AudioManager.STREAM_MUSIC) * 100f / max);
    }

    private void setMediaVolumePercent(int percent) {
        if (audioManager == null) return;
        int max = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        audioManager.setStreamVolume(AudioManager.STREAM_MUSIC,
            Math.round(Math.max(0, Math.min(100, percent)) * max / 100f), 0);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (statusText != null) {
            statusText.postDelayed(() -> {
                waitingForSystemConnection = false;
                updateStatus();
            }, 500);
        }
    }

    private void initializeBluetooth() {
        if (!hasBluetoothPermissions()) return;

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        btAdapter = bm != null ? bm.getAdapter() : BluetoothAdapter.getDefaultAdapter();
        if (btAdapter == null) return;

        btAdapter.getProfileProxy(this, new BluetoothProfile.ServiceListener() {
            public void onServiceConnected(int profile, BluetoothProfile proxy) {
                if (profile == BluetoothProfile.A2DP) {
                    a2dpProxy = (BluetoothA2dp) proxy;
                    updateStatus();
                }
            }
            public void onServiceDisconnected(int profile) { a2dpProxy = null; }
        }, BluetoothProfile.A2DP);

        IntentFilter filter = new IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED);
        filter.addAction(BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED);
        filter.addAction(BluetoothDevice.ACTION_ACL_CONNECTED);
        filter.addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED);
        ContextCompat.registerReceiver(this, btReceiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED);
    }

    private final BroadcastReceiver btReceiver = new BroadcastReceiver() {
        public void onReceive(Context c, Intent i) {
            String a = i.getAction();
            if (BluetoothDevice.ACTION_BOND_STATE_CHANGED.equals(a) ||
                BluetoothDevice.ACTION_ACL_CONNECTED.equals(a) ||
                BluetoothDevice.ACTION_ACL_DISCONNECTED.equals(a)) {
                updateStatus();
            }
        }
    };

    private void updateStatus() {
        if (!hasBluetoothPermissions()) {
            statusText.setText("Autorisation Bluetooth requise");
            toggleBtn.setText("Autoriser Bluetooth");
            return;
        }
        if (btAdapter == null || !btAdapter.isEnabled()) {
            statusText.setText("Bluetooth désactivé sur le téléphone");
            toggleBtn.setText("Activer Bluetooth");
            isOn = false;
            return;
        }
        Set<BluetoothDevice> paired = btAdapter.getBondedDevices();
        boolean pairedFound = false;
        boolean connected = false;
        for (BluetoothDevice d : paired) {
            if (d.getAddress().equalsIgnoreCase(PI_MAC) || PI_NAME.equalsIgnoreCase(d.getName())) {
                pairedFound = true;
                piDevice = d;
                connected = isA2dpConnected(d);
                break;
            }
        }
        if (connected) {
            statusText.setText("● Connecté à raspberrypi → son sur KRK ✓");
            statusText.setTextColor(Color.parseColor("#00d68f"));
            toggleBtn.setText("■  DÉSACTIVER");
            toggleBtn.setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#ff3b30")));
            isOn = true;
        } else if (pairedFound) {
            statusText.setText("Appairé à raspberrypi — appuie pour connecter");
            statusText.setTextColor(Color.parseColor("#ff9f0a"));
            toggleBtn.setText("▶  ACTIVER SORTIE KRK");
            toggleBtn.setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#7c5cff")));
            isOn = false;
        } else {
            statusText.setText("Non appairé — appuie pour scanner + appairer");
            statusText.setTextColor(Color.parseColor("#8b8fa3"));
            toggleBtn.setText("▶  ACTIVER SORTIE KRK");
            toggleBtn.setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#7c5cff")));
            isOn = false;
        }
    }

    private boolean isA2dpConnected(BluetoothDevice device) {
        if (a2dpProxy == null || device == null) return false;
        try {
            return a2dpProxy.getConnectedDevices().contains(device);
        } catch (SecurityException e) {
            return false;
        }
    }

    private void toggle() {
        if (isOn) {
            disconnect();
        } else {
            connect();
        }
    }

    private void connect() {
        if (!hasBluetoothPermissions()) {
            ActivityCompat.requestPermissions(this,
                android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S
                    ? new String[] { Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN }
                    : new String[] { Manifest.permission.ACCESS_FINE_LOCATION }, 1);
            return;
        }
        if (btAdapter == null) return;
        if (!btAdapter.isEnabled()) {
            btAdapter.enable();
            statusText.setText("Activation Bluetooth...");
            // wait a bit then retry
            statusText.postDelayed(() -> connect(), 1500);
            return;
        }
        // Find Pi
        Set<BluetoothDevice> paired = btAdapter.getBondedDevices();
        BluetoothDevice target = null;
        for (BluetoothDevice d : paired) {
            if (d.getAddress().equalsIgnoreCase(PI_MAC) || PI_NAME.equalsIgnoreCase(d.getName())) {
                target = d; break;
            }
        }
        if (target != null) {
            piDevice = target;
            waitingForSystemConnection = true;
            statusText.setText("Ouvre les réglages et sélectionne raspberrypi");
            startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS));
            return;
        }
        // Not paired -> start discovery
        statusText.setText("Recherche raspberrypi 8s... rends Pi visible");
        // Make sure Pi is discoverable via network if possible (fire and forget)
        // Scan
        if (btAdapter.isDiscovering()) btAdapter.cancelDiscovery();
        btAdapter.startDiscovery();
        // Wait 8s and check
        statusText.postDelayed(() -> {
            btAdapter.cancelDiscovery();
            Set<BluetoothDevice> bonded = btAdapter.getBondedDevices();
            // Also check discovered devices via getBonded + scan results are not directly accessible, so we need BroadcastReceiver
            // For simplicity, try to find Pi among bonded or show manual instruction
            boolean found = false;
            for (BluetoothDevice d : bonded) {
                if (PI_NAME.equalsIgnoreCase(d.getName())) { found = true; break; }
            }
            if (!found) {
                // Need to get discovered devices via receiver - we didn't collect, so show instruction
                statusText.setText("Pi non trouvé. Vérifie que Pi est allumé et visible.\nSur Pi: bluetoothctl discoverable on");
                // Try direct createBond by MAC (even if not discovered, it may work if Pi is discoverable)
                try {
                    BluetoothDevice dev = btAdapter.getRemoteDevice(PI_MAC);
                    dev.createBond();
                    statusText.setText("Tentative appairage direct " + PI_MAC + "... Confirme sur les deux appareils. Code: 0000");
                } catch (Exception e) {
                    statusText.setText("Échec scan. Entre MAC manuellement: " + PI_MAC);
                }
            }
            updateStatus();
        }, 8500);

        // Register discovery receiver
        IntentFilter filter = new IntentFilter(BluetoothDevice.ACTION_FOUND);
        BroadcastReceiver disc = new BroadcastReceiver() {
            public void onReceive(Context c, Intent intent) {
                BluetoothDevice dev = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
                if (dev != null && (PI_MAC.equalsIgnoreCase(dev.getAddress()) || PI_NAME.equalsIgnoreCase(dev.getName()))) {
                    statusText.setText("Trouvé: " + dev.getName() + " " + dev.getAddress() + " → appairage...");
                    btAdapter.cancelDiscovery();
                    try { dev.createBond(); } catch (Exception e) {}
                    try { unregisterReceiver(this); } catch (Exception e) {}
                }
            }
        };
        ContextCompat.registerReceiver(this, disc,
            new IntentFilter(BluetoothDevice.ACTION_FOUND), ContextCompat.RECEIVER_NOT_EXPORTED);
    }

    private void disconnect() {
        if (piDevice != null && a2dpProxy != null) {
            statusText.setText("Déconnecte raspberrypi dans les réglages Bluetooth");
            startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS));
        } else {
            statusText.setText("Déconnecté");
        }
        isOn = false;
        statusText.postDelayed(() -> updateStatus(), 1000);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        // Relance l'init après autorisation
        try {
            initializeBluetooth();
        } catch (SecurityException ignored) {}
        updateStatus();
    }

    @Override
    protected void onDestroy() {
        try { unregisterReceiver(btReceiver); } catch (Exception e) {}
        try { if (a2dpProxy != null && btAdapter != null) btAdapter.closeProfileProxy(BluetoothProfile.A2DP, a2dpProxy); } catch (Exception e) {}
        super.onDestroy();
    }
}
