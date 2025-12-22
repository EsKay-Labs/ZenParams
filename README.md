# 🧘 ZenParams Pro

### The "Right Way" to Parameterize in Fusion 360.

![ZenParams Hero](img/hero.png)

> **"If you're hardcoding dimensions in your sketches, you're doing it wrong."** > _— Every Senior CAD Engineer ever._

---

## 🛑 Stop The Madness.

You know the drill. You design a beautiful enclosure. It's perfect. Then you buy the bolts and realize they're M3, not M2.5.
Now you have to hunt down **27 different sketches**, deep dive into **14 timeline features**, and manually change `2.5mm` to `3.0mm`.

**That is the path of pain.**

**ZenParams** is the path of enlightenment. It forces you to adopt the single most important habit in professional CAD: **Parametric Design.**

---

## 🔥 Why ZenParams?

### 1. 🧙‍♂️ Smart Fit Wizard (The "Killer" Feature)

Stop guessing tolerances.
"Is a loose fit 0.1mm or 0.2mm?"
"How much clearance does a 3D printed M3 hole need?"

**ZenParams knows.**

Select a context (Bolt, Magnet, Bearing, Insert), pick your nominal size, and **BOOM**. It calculates the perfect offset based on industry standards (and your own "User Presets").

![Smart Wizard](img/wizard.png)

### 2. ⚡ Live Synchronization

Fusion 360's native parameter window is... a modal dialog from 1995. It blocks your view. It blocks your clicks.

ZenParams lives in a **non-blocking palette**.

- Change a value? **Instant update.**
- Add a parameter? **Live sync.**
- No more clicking "OK" just to see if your design broke.

### 3. 💾 Project Templates (Presets)

Do you make enclosures? You probably use the same wall thickness (`2mm`), the same standoffs (`6mm`), and the same tolerance (`0.2mm`) every time.

Save your setup as a **Template**.
Start a new project -> Load "3D Print Box" -> **Done.**

![Presets Loading](img/presets.png)

### 4. 🧠 Auto-Categorization (The "Zen Mind")

**"But I have 500 parameters in my old design!"**

Don't panic. ZenParams features a **Reverse Dependency Crawler**.
It scans your entire design history to figure out _what_ your parameters are actually controlling.

- Used in the Lid? -> **Group: Lid**
- Used in the Mounting Holes? -> **Group: Mounts**
- Unused? -> **Group: Unused (Clean them up!)**

It works on **existing designs** instantly. No manual tagging required.

### 5. 🛡️ Dependency Protection

ZenParams is your safety net.
It **won't let you delete a parameter** that is currently holding your assembly together.

- Try to delete a used parameter? **Blocked.**
- Try to break your model? **Denied.**

### 6. 🎹 Excel-Style "Rapid Entry"

We built this for speed demons.

- **Narrow Mode**: Compact by default to save screen real estate.
- **Keyboard First**: Type `Name` -> `Tab` -> `Value` -> `Tab` -> `Comment`.
- **Enter (Once)**: Saves and locks the row.
- **Enter (Twice)**: Adds a new row instantly.

---

## 🚀 Features at a Glance

| Feature          | The Old Way                      | The Zen Way                          |
| :--------------- | :------------------------------- | :----------------------------------- |
| **Workflow**     | sketch -> `d` -> `3.2mm`         | click "M3 Bolt" -> Parameters Update |
| **Updates**      | Open menu -> Edit -> Enter -> OK | Edit value in panel -> Watch it move |
| **Organization** | "d1", "d2", "d3"... what is d2?  | Named groups. Clean comments.        |
| **Sanity**       | 10%                              | 100%                                 |

![Table View](img/table.png)

---

## 🛠️ Installation

1.  **Download** the code (Clone this repo).
2.  **Move** the `ZenParams` folder to your Fusion 360 Scripts folder:
    - **Windows**: `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts\`
    - **Mac**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
3.  **Open Fusion 360**.
4.  Go to **Utilities** -> **Scripts and Add-Ins**.
5.  Find `ZenParams` under "My Scripts".
6.  Click **Run**. (Pro tip: Check "Run on Startup").
7.  **Right-click** "ZenParams" and set a **Keyboard Shortcut** (e.g., `Shift+P`) for instant access.

### ⌨️ Pro Tips (Keyboard First)

- **Instant Hide**: Press `ESC` to vanish the palette instantly.
- **Quick Edit**: Double-click any cell to edit. It behaves just like Excel.
- **Rapid Add**: press `Enter` twice to keep adding parameters without touching the mouse.

---

## 🧘 The Zen Philosophy

**ZenParams** isn't just a tool; it's a mentorship in a box. It gently nudges you away from "Direct Modeling Chaos" and towards "Parametric Bliss."

When you use ZenParams, you aren't just drawing lines. You are defining **Design Intent**.

> _Code is Poetry. CAD is Logic. Parameters are Truth._

---

## 📜 License

MIT. Go forth and parameterize.
