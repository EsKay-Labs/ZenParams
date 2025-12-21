# ZenParams ⚡

**The Logic-First Parameter Manager for Autodesk Fusion 360**

> Stop clicking "Okay". Start designing.

ZenParams is a professional-grade Add-In that replaces the clunky, modal "Change Parameters" dialog with a fast, dockable, modeless palette. It is designed for power users who rely on logic, equations, and rapid iteration.

![ZenParams UI](resources/ui_preview.png)

## 🚀 Why ZenParams?

### The Problem with Native Parameters

1.  **Modal Blocking:** You open the dialog -> You can't touch the model. You close it -> You lose your place.
2.  **Slow Entry:** Clicking "+" for every single parameter is tedious.
3.  **No Templates:** Every design starts from scratch. Reuse is painful.

### The ZenParams Solution

1.  **Modeless & Dockable:** Keep the palette open while you work. Tweak a value, see the model update instantly.
2.  **Rapid Entry:** Type `Name` -> `Tab` -> `Value` -> `Enter`. Rinse and repeat. No mouse needed.
3.  **Powerful Presets:** Save your standard configurations (fasteners, material thicknesses, tolerance classes) as Templates and switch between them instantly.

---

## 🌟 Key Features

### 1. ⚡ Rapid Data Entry (New!)

Forget the mouse.

- **Enter Key:** Press `Enter` in any field to instantly spawn a new row.
- **Tab Navigation:** Tab through Name, Expression, and Comments naturally.

### 2. 📂 Smart Presets & Templates

Save your parameter sets.

- **Create Template:** Setup your variables once (e.g., `Thickness`, `Play`, `Bends`). Save as "Sheet Metal 3mm".
- **Load & Switch:** Select "Sheet Metal 5mm" from the dropdown to instantly update all values.
- **Auto-Activation:** Saving a preset automatically activates it for the current design.

### 3. 🛡️ Professional "True Delete"

- **Safety First:** ZenParams checks for dependencies before deletion.
- **Clean:** Reliably deletes parameters from the Fusion design (not just the list), keeping your file clean.

### 4. 🔄 Legacy Import

Opening an old file?

- ZenParams detects existing parameters.
- Click **"⬇️ Import"** to capture them into the UI and save them as a new Preset immediately.

### 5. 🧠 Intelligent context

- **Tab Switching:** The palette automatically follows you. Switch tabs, and ZenParams refreshes to show the active design's data.

---

## 📦 Installation

1.  Download the repository.
2.  Copy the folder to your Fusion 360 Scripts directory:
    - **Windows:** `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\`
    - **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
3.  Restart Fusion 360.
4.  Go to **Utilities > Scripts and Add-Ins**, select `ZenParams`, and check "Run on Startup".

## 🛠️ Usage

1.  **Open:** The palette appears automatically (or via `Modify` panel).
2.  **Add:** Type your first parameter. Press `Enter` to add more.
3.  **Apply:** Click **Load** to commit changes to Fusion (if not auto-updating).
4.  **Save Preset:** Click **Save Template** to store your current setup for future use.

---

**License:** MIT  
**Version:** 11.0 (Pro Edition)
