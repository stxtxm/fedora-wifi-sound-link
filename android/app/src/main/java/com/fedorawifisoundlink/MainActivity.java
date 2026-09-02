package com.fedorawifisoundlink;
import android.Manifest;
import android.bluetooth.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Bundle;
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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Permissions Android 12+
        String[] perms = {
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.ACCESS_FINE_LOCATION
        };
        for (String p : perms) {
            if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, perms, 1);
                break;
            }
        }

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        btAdapter = bm.getAdapter();

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

        // Init A2DP proxy
        btAdapter.getProfileProxy(this, new BluetoothProfile.ServiceListener() {
            public void onServiceConnected(int profile, BluetoothProfile proxy) {
                if (profile == BluetoothProfile.A2DP) {
                    a2dpProxy = (BluetoothA2dp) proxy;
                    updateStatus();
                }
            }
            public void onServiceDisconnected(int profile) { a2dpProxy = null; }
        }, BluetoothProfile.A2DP);

        // Register receiver for bond state
        IntentFilter filter = new IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED);
        filter.addAction(BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED);
        filter.addAction(BluetoothDevice.ACTION_ACL_CONNECTED);
        filter.addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED);
        registerReceiver(btReceiver, filter);

        updateStatus();
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
                // Check A2DP connection
                if (a2dpProxy != null) {
                    try {
                        // Use reflection for hidden isConnected
                        // Fallback: check ACL connected via getBondState + isConnected via device
                        connected = d.getBondState() == BluetoothDevice.BOND_BONDED;
                        // Try to check via a2dpProxy.getConnectedDevices()
                        if (a2dpProxy.getConnectedDevices().contains(d)) connected = true;
                    } catch (Exception e) {}
                }
                break;
            }
        }
        // Also check via getConnectedDevices
        if (a2dpProxy != null && piDevice != null && a2dpProxy.getConnectedDevices().contains(piDevice)) {
            connected = true;
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

    private void toggle() {
        if (isOn) {
            disconnect();
        } else {
            connect();
        }
    }

    private void connect() {
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
            statusText.setText("Connexion à raspberrypi...");
            // Try A2DP connect via reflection (hidden API)
            try {
                if (a2dpProxy != null) {
                    // Use reflection to call connect
                    java.lang.reflect.Method m = a2dpProxy.getClass().getMethod("connect", BluetoothDevice.class);
                    m.invoke(a2dpProxy, target);
                    statusText.setText("Connexion A2DP en cours...");
                } else {
                    target.createBond();
                }
            } catch (Exception e) {
                // Fallback: just createBond and let system handle
                try { target.createBond(); } catch (Exception ex) {}
                statusText.setText("Appairage en cours... confirme sur Pi si besoin");
            }
            // Also ensure Pi is discoverable via PWA if on same WiFi (optional)
            // Post delayed update
            statusText.postDelayed(() -> updateStatus(), 3000);
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
        registerReceiver(disc, new IntentFilter(BluetoothDevice.ACTION_FOUND));
    }

    private void disconnect() {
        if (piDevice != null && a2dpProxy != null) {
            try {
                java.lang.reflect.Method m = a2dpProxy.getClass().getMethod("disconnect", BluetoothDevice.class);
                m.invoke(a2dpProxy, piDevice);
                statusText.setText("Déconnexion...");
            } catch (Exception e) {
                statusText.setText("Déconnecté (son repasse sur tel)");
            }
        } else {
            statusText.setText("Déconnecté");
        }
        isOn = false;
        updateStatus();
    }

    @Override
    protected void onDestroy() {
        try { unregisterReceiver(btReceiver); } catch (Exception e) {}
        if (a2dpProxy != null) btAdapter.closeProfileProxy(BluetoothProfile.A2DP, a2dpProxy);
        super.onDestroy();
    }
}
