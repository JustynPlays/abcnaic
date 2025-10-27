# Add project specific ProGuard rules here
-keep class com.google.androidbrowserhelper.** { *; }
-keep class androidx.browser.** { *; }
-dontwarn com.google.androidbrowserhelper.**
-dontwarn androidx.browser.**

# Keep all classes in the main package
-keep class com.drcare.animalbitecenter.** { *; }

# Keep all native methods
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep all public and protected methods
-keepclassmembers class * {
    public protected <methods>;
}
