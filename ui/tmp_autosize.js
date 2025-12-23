// --- AUTO-SIZE COLUMNS LOGIC ---
function autoSizeColumns(params) {
  if (!params || params.length === 0) return;

  // 1. Calculate Max Lengths (approx chars)
  var maxNameLen = 10; // Min
  params.forEach(function (p) {
    if (p.name && p.name.length > maxNameLen) maxNameLen = p.name.length;
  });

  // Cap max name length to prevent layout breakage (e.g. 40 chars)
  if (maxNameLen > 40) maxNameLen = 40;

  // 2. Convert to Pixels (Approx 8px per char + padding)
  var namePx = maxNameLen * 8 + 20;

  // 3. Get Headers
  var table = document.getElementById("param-table");
  if (!table) return;
  var ths = table.querySelectorAll("th");

  // Scale Name Column (Index 0)
  // Ensure it doesn't take up entire screen
  var maxWidth = window.innerWidth * 0.4;
  if (namePx > maxWidth) namePx = maxWidth;
  if (namePx < 100) namePx = 100;

  ths[0].style.width = namePx + "px";

  // Reset others to reasonable defaults if they were squashed
  // Value (Index 1)
  if (!ths[1].style.width || parseInt(ths[1].style.width) < 80)
    ths[1].style.width = "120px";
  // Unit (Index 2)
  ths[2].style.width = "50px";
  // Comment (Index 3) - auto rest
  ths[3].style.width = "auto";
  // Actions (Index 4)
  ths[4].style.width = "32px";

  console.log("[ZP] Auto-Sized Name Column to: " + namePx + "px");
}
