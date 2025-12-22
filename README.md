# ⚡ ZenParams PRO ⚡

### _THE "GOD MODE" PARAMETER MANAGER FOR FUSION 360_

> 🛑 **WARNING:** This plugin may cause sudden bursts of extreme productivity, uncontrollable smiling during the design phase, and a complete intolerance for manual data entry.

---

## 😤 THE PROBLEM (The Irony)

**Fusion 360 is a paradox.** It’s a futuristic, cloud-powered, AI-ready CAD beast... that handles parameters like a **Windows 95 spreadsheet**.

You’re designing rockets and race cars, yet you’re forced to:

1.  Open a slow modal window.
2.  Click a tiny "+" button.
3.  Type `wall_thick`... tab... `1.2mm`... tab... `Enclosure Wall`.
4.  Repeat 50 times.
5.  Realize you can’t sort them or group them meaningfully.

It’s 2025. **Why are we doing data entry like it’s 1995?**

## 🚀 THE SOLUTION (The Savior)

**ZenParams PRO** isn't just a plugin; it's a rebellion against bad UX. It turns the soul-crushing chore of parameter management into a fluid, high-speed workflow that actually feels _modern_.

It is the **Life Savior** for anyone who uses more than 5 parameters in a design.

---

## 🔬 ANALYTICAL FEATURE BREAKDOWN

We didn't just skin the API; we re-engineered how parameters work.

### 1. 📉 Smart Compact Layout (The "No-Pixel-Left-Behind" Engine)

We engineered a custom table layout algorithm to maximize information density:

- **Shrink-Wrap Columns**: The Name, Value, and Unit columns explicitly set their width to `1px` (a CSS trick), forcing the browser to shrink them to the _exact_ width of their text content.
- **Smart Inputs**: Input fields dynamically calculate their own width based on character count (`ch` units). A value of `0.1` takes up 10px; `125.05` takes up 50px.
- **Greedy Comment Column**: The Comment column is programmed to consume **100% of the remaining screen space**, pushing all data columns tight to the left.
- **Result**: You can see 3x more parameters on screen than the native dialog.

### 2. 🧭 Auto-Categorization (The "Zen Crawler")

Fusion 360 doesn't know which parameter drives which body. **We do.**

- **Reverse Indexing**: The script crawls the entire Design Timeline, analyzing every Feature, Sketch, and Dimension.
- **Dependency Tracing**: It maps `UserParam -> ModelParam -> SketchDimension -> Sketch -> Feature -> Body`.
- **Automatic Grouping**:
  - **[Body Name]**: Parameters used by exactly one body are automatically grouped into a folder named after that body.
  - **[Shared]**: Parameters used by multiple bodies are tagged as Shared.
  - **[Unused]**: Parameters driving nothing are grayed out, so you know what to clean up.

### 3. ⚡ High-Velocity Data Entry

- **Ctrl + Enter (Global)**: Instantly adds a new row from _anywhere_. No mouse needed.
- **Single Enter**: Saves the value and **Locks** the field (Excel-style). This prevents accidental edits while keeping you in the flow.
- **Auto-Focus**: New rows immediately focus the Name field.

### 4. 🛡️ Safe Deletion (Dependency Guard)

Native Fusion lets you delete a parameter that drives geometry, causing the timeline to explode in red errors.

- **Pre-Validation**: ZenParams checks `dependentParameters` and `parentFeatures` BEFORE you delete.
- **Usage Report**: If a parameter is in use, it denies the deletion and tells you exactly _what_ is using it.

### 5. 🔄 Version-Based Live Sync

Native palettes often desync from the actual design state.

- We implemented a **Polling System** where Python increments a `_data_version` counter on any change.
- The UI polls this version every 1 second.
- Updates are instant and atomic. If you change a generic dimension in the canvas, ZenParams reflects it immediately.

### 6. 🪄 The Smart Fit Wizard

Generates tolerance-compensated parameters automatically for 3D printing or machining.

- **Workflow**: Select "Heat Set Insert" -> "M3".
- **Result**: Creates params like `M3_Hole = 3.8mm` (includes empirically tested tolerances).

### 7. 🧬 Preset Cloning

Save your entire parameter list (materials, tolerances, standard dimensions) as a JSON preset.

- **One-Click Setup**: Load "ABS Printing Standards" and populate 20 parameters instantly.

---

## 📦 INSTALLATION

1.  **Download** this repo.
2.  **Move** the folder to your Fusion 360 Scripts folder:
    - _Windows_: `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\`
    - _Mac_: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
3.  **Open Fusion 360** -> **Utilities** -> **Scripts and Add-Ins**.
4.  Find **ZenParams** and click **RUN**.

---

## ⌨️ KEYBOARD SHORTCUTS

| Shortcut              | Action                     |
| :-------------------- | :------------------------- |
| **Ctrl + Enter**      | Add new parameter row      |
| **Enter (Edit Mode)** | Save & Lock field          |
| **Esc**               | Cancel edit / Close window |
| **Double Click**      | Edit a locked field        |

---

### 💬 FEEDBACK & LICENSE

Built for **Builders**. **MIT License**. Free forever.
