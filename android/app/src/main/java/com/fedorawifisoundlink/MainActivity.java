package com.fedorawifisoundlink;
import android.os.Bundle; import android.webkit.WebView; import android.webkit.WebViewClient; import android.webkit.WebSettings; import android.Manifest; import android.content.pm.PackageManager; import androidx.appcompat.app.AppCompatActivity; import androidx.core.app.ActivityCompat; import androidx.core.content.ContextCompat;
public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private static final String PI_URL = "http://192.168.1.101:8080";
    private static final String FALLBACK = "http://raspberrypi.local:8080";
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Permissions for Android 12+
        String[] perms = {Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.ACCESS_FINE_LOCATION};
        for(String p: perms) if(ContextCompat.checkSelfPermission(this,p)!=PackageManager.PERMISSION_GRANTED) ActivityCompat.requestPermissions(this, perms, 1);
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true);
        webView.setWebViewClient(new WebViewClient(){
            @Override public void onReceivedError(WebView v,int c,String d,String url){
                // fallback to local asset if Pi not reachable
                if(url.contains("192.168.1.101")) v.loadUrl(FALLBACK);
            }
        });
        setContentView(webView);
        // Try Pi IP first, fallback to mDNS
        webView.loadUrl(PI_URL);
    }
    @Override public void onBackPressed(){ if(webView.canGoBack()) webView.goBack(); else super.onBackPressed(); }
}
