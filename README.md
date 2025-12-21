# ⚡ ZenParams PRO ⚡

### _THE "GOD MODE" PARAMETER MANAGER FOR FUSION 360_

> 🛑 **WARNING:** This plugin may cause sudden bursts of extreme productivity, uncontrollable smiling during the design phase, and a complete intolerance for manual data entry.

---

## 😤 THE PROBLEM

Let's be real. Managing parameters in Fusion 360 is **boring**.
You start a new design. You type `tol_snug = 0.15mm`. You type `wall_thick = 1.2mm`. You do this **EVERY. SINGLE. TIME.**
You are a creative engineer, not a data entry clerk. Stop acting like one.

## 🚀 THE SOLUTION

**ZenParams PRO** is the high-octane injection your workflow has been screaming for. It takes the tedious, soul-crushing task of parameter management and automates it into a **single click**.

We didn't just build a plugin. We built a **Time Machine** that gives you back hours of your life.

---

## 🔥 KILLER FEATURES

### 1. 🧬 PRESET CLONING (The "Magic Button")

Save your _entire_ parameter list as a Preset.

- Working on a PLA project? **CLICK.** Boom, all your PLA tolerances are loaded.
- Switching to CNC Aluminum? **CLICK.** Boom, your machining allowances are set.
- **It’s like Copy-Paste for your entire brain.**

### 2. 🖨️ 3D PRINTING "GOD MODE" (Built-In)

We included the **Holy Grail** of 3D printing tolerances right out of the box. Stop guessing.

- `Tol_Press` (0.10mm): For bearings that never move.
- `Tol_Snug` (0.15mm): For satisfying "click" fits.
- `Tol_Slide` (0.25mm): For buttery smooth hinges.
- `Tol_Loose` (0.40mm): For when you just don't care.

### 3. ⚡ BATCH BLASTING

Need to update 50 parameters? Change names? Delete the old ones?
Do it in **bulk**. Our UI handles the heavy lifting while you sip coffee.

### 4. 🧠 DEPENDENCY CHECKS

ZenParams is smart. It won't let you delete a parameter that's currently holding your entire assembly together. It’s the safety net you didn't know you needed.

---

## 📦 INSTALLATION (30 Seconds)

1.  **Download** this repo.
2.  **Move** the folder to your Fusion 360 Scripts folder:
    - _Windows_: `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\`
    - _Mac_: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
3.  **Open Fusion 360** -> **Utilities** -> **Scripts and Add-Ins**.
4.  Find **ZenParams** and click **RUN**.
5.  _Optional_: Check "Run on Startup" so you never have to live without it again.

---

## 🎮 HOW TO USE

1.  **Open the Palette**: You'll find the **ZenParams Pro** icon in your **Modify** panel (Design > Solid > Modify). It's also in the **Modify** dropdown menu.
2.  **Load a Preset**: Click "3DP Tolerances (Global)" to load the built-in magic.
3.  **Customize**: Edit values in the table.
4.  **Save Your Own**: Click "Save Preset", name it (e.g., "PETG Master"), and feel the power.
5.  **Apply**: Just select a preset and your current design is instantly populated.

---

## ⌨️ PRO TIPS (Keyboard First)

- **ENABLE SHORTCUTS**: Fusion 360 requires you to set user shortcuts manually (security rules).

  1.  Go to **Modify Panel** (Solid Tab).
  2.  Hover over the **ZenParams Pro** icon.
  3.  Click the **3 Dots** -> **Change Keyboard Shortcut**.
  4.  Press **`Ctrl+P`** (or `Command+P`).
  5.  Now `Ctrl+P` will **Toggle** the script (Open AND Hide).

- **RAPID ENTRY**: Type `Name` -> `Tab` -> `Value` -> `Tab` -> `Comment`.
  - **`Enter` (Once)**: Saves the value instantly. Stays on the row so you can edit more.
  - **`Enter` (Twice)**: Adds a new row and jumps to it.
- **INSTANT HIDE**: Press **`Esc`** at any time to instantly hide the palette. Simply press your shortcut (`Ctrl+P`) to bring it back instantly.

---

## 🏆 CREDITS

Built for the **Builders**, the **Makers**, and the **Engineers** who value their time.

- **Core Logic**: Python 3.x
- **UI**: HTML5/JS (Chrome Engine)
- **Vibe**: Unstoppable

---

### 💬 FEEDBACK

Found a bug? Want to request a feature?
**Don't keep it to yourself.** Open an issue. We eat bugs for breakfast.

### 📄 LICENSE

**MIT**. Open Source. Free forever. Go build something awesome.
