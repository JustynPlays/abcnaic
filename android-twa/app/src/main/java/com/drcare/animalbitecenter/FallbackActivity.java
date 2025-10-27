package com.drcare.animalbitecenter;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import androidx.browser.customtabs.CustomTabsIntent;

/**
 * Fallback activity for when TWA is not available
 * Opens the PWA in a custom tab instead
 */
public class FallbackActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Build custom tabs intent
        CustomTabsIntent.Builder builder = new CustomTabsIntent.Builder();
        builder.setToolbarColor(0xA52A2A); // Maroon color
        builder.setShowTitle(true);

        CustomTabsIntent customTabsIntent = builder.build();

        // Launch the PWA URL
        String url = "https://yourdomain.com";
        customTabsIntent.launchUrl(this, Uri.parse(url));

        // Finish this activity
        finish();
    }
}
