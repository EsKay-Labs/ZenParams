# ZenParams 🚀

**The "Logic-First" Parameter Manager for Autodesk Fusion 360**

> Stop clicking "Okay". Start designing.

ZenParams is a professional, open-source Add-In that transforms how you handle parametric design in Fusion 360. It replaces the native, modal "Change Parameters" dialog with a fast, modeless, and logic-driven palette.

![ZenParams UI Preview](resources/ui_preview.png)

---

## 🏆 Why "Next Level"? (The Zen Philosophy)

Native Fusion parameters are powerful but slow to access. You have to open a dialog, block your view, click `+`, type, click `OK`. ZenParams removes the friction.

### 1. Modeless & Dockable

**The Native Way:** Open Dialog -> View Blocked -> Close Dialog to Rotate Model -> Re-open Dialog.
**The Zen Way:** Dock the palette to the right. Change a value like `Length` from `50mm` to `100mm` and see your model update **instantly** without closing anything.

### 2. Rapid Data Entry (Keyboard First)

**The Native Way:** Click `+`. Type Name. Click Value. Type Value. Click OK. Repeat.
**The Zen Way:**

- Type `Name` -> `Tab` -> `Value` -> `Tab` -> `Comment` -> **`Enter`**.
- **`Enter`** automatically creates a new row and focuses it.
- You can define 10 parameters in 30 seconds without touching the mouse.

### 3. "True Delete" with Dependency Guard 🛡️

**The Native Way:** Deleting used parameters throws cryptic errors or breaks features.
**The Zen Way:** Click the **`×`** button. ZenParams intelligently checks if the parameter is used by any feature (Extrude, Sketch, etc.).

- **Safe:** If used, it warns you: _"Cannot delete 'd1': Used in design."_
- **Clean:** If unused, it permanently deletes it from the Fusion file, keeping your timeline clean.

---

## ⚡ Key Features (Every Detail)

### 📂 Smart Presets (Templates)

Don't start from scratch.

- **Factory Loaded:** "3DP Tolerances (Global)" - A single master preset containing standard keys for every fit type:
  - `Tol_Press` (0.10mm), `Tol_Snug` (0.15mm), `Tol_Slide` (0.25mm), `Tol_Loose` (0.40mm).
  - `Tol_Hole` (0.20mm) and `Tol_Thread` (0.20mm).
- **Save Template:** Configure your standard variables (e.g., `Thickness`, `Kerf`, `Clearance`) once. Save as "Laser Cut Acrylic".
- **Instant Load:** Select the preset from the dropdown. ZenParams **previews** the values in the table. Click **Load** to apply them all at once.
- **Auto-Activation:** Saving a new template automatically applies it and sets it as the "Active" preset for the current design.

### 🔄 Intelligent Context Awareness

ZenParams knows where you are.

- **Multi-Doc Support:** Switch between open design tabs (`Design A` -> `Design B`). ZenParams detects the switch (via a smart 2.5s watchdog) and automatically refreshes to show `Design B`'s parameters.
- **Persistence:** The active preset name is stored _inside the Fusion file_ (in a hidden parameter `_zen_current_preset`). If you send the file to a colleague with ZenParams, they see the same preset name.

### 👁️ Live Preview & Visual Feedback

- **Preview Mode:** Selecting a preset shows values in the table with a visual "Modified" style, letting you verify data before committing to the model.
- **Read-Only Model Params:** ZenParams displays native Model Parameters (like `d1`, `d2`) in a dimmed, read-only style, so you can reference their values without accidentally breaking driven dimensions.
- **Status Bar:** Real-time feedback ("Saved", "Syncing...", "Error") keeps you informed.

### 📥 Legacy Import

Opening an old project?

- ZenParams detects if a design has parameters (`UserParameters > 0`) but no ZenParams preset.
- A blue notification bar appears: **"Found existing parameters."**
- Click **"⬇️ Import"** to instantly pull them into the UI and save them as a new Template.

---

## 🛠️ Architecture (For Developers)

ZenParams is built on a robust hybrid architecture:

- **Backend (Python):** Handles Fusion API calls, dependency checks, file I/O, and event dispatching.
- **Frontend (HTML/JS):** A responsive, dark-themed UI built with vanilla JS (no heavy frameworks).
- **Communication:** Uses a reliable message bus (`adsk.fusionSendData`).
- **Resilience:** Includes `adsk.autoTerminate(False)` to prevent garbage collection of event handlers—a common issue in complex Add-Ins.

---

## 📦 Installation

1.  **Download:** Clone or download this repository.
2.  **Locate Scripts Folder:**
    - **Windows:** `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\`
    - **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
3.  **Install:** Copy the `ZenParams` folder into the Scripts folder.
4.  **Run:** Restart Fusion 360. Go to **Utilities > Scripts and Add-Ins**. Select `ZenParams` and check **"Run on Startup"**.

---

**License:** MIT
**Version:** 11.0
**Author:** ZenParams Team
