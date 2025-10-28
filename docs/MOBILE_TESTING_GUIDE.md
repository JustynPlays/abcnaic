# Quick Start Guide - Testing Mobile Responsive Design

## 🚀 Quick Start

### 1. Start the Application
```powershell
python app.py
```

### 2. Open in Browser
- Desktop: http://localhost:5000
- Mobile (same WiFi): http://YOUR_LOCAL_IP:5000

### 3. Test on Mobile Device

#### Using Browser DevTools (Easiest):
1. Open Chrome/Edge
2. Press `F12`
3. Click mobile icon (or `Ctrl+Shift+M`)
4. Select "iPhone 12 Pro" or "Samsung Galaxy S20"
5. Visit http://localhost:5000

#### Using Real Phone:
1. Find your PC's IP:
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., 192.168.1.100)

2. On your phone (must be on same WiFi):
   - Open browser
   - Visit: `http://192.168.1.100:5000`

## ✅ What Should Work

### Home Page (/)
- [x] Cards stack vertically on mobile
- [x] Icons display (64px × 64px)
- [x] Text is centered and readable
- [x] No horizontal scrolling
- [x] Hamburger menu opens sidebar with overlay

### All Pages
- [x] Header fits properly
- [x] Sidebar slides in from left
- [x] Forms are touch-friendly
- [x] Buttons are sized correctly
- [x] No overlapping content

(...trimmed...)
