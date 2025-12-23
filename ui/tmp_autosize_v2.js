// --- AUTO-SIZE COLUMNS LOGIC (ADAPTIVE) ---
function autoSizeColumns(params) {
  if (!params || params.length === 0) return;

  // 1. Calculate Max Lengths (across ALL params, including hidden)
  var maxNameLen = 10;
  var maxExprLen = 10;

  params.forEach(function (p) {
    if (p.name && p.name.length > maxNameLen) maxNameLen = p.name.length;
    if (p.expression && String(p.expression).length > maxExprLen)
      maxExprLen = String(p.expression).length;
  });

  // Cap max length to prevent insanity (e.g. 100 chars)
  if (maxNameLen > 80) maxNameLen = 80;
  if (maxExprLen > 80) maxExprLen = 80; // Allow wider values

  // 2. Convert to Pixels (Approx 8px per char + liberal padding)
  var namePx = maxNameLen * 8 + 40;
  var exprPx = maxExprLen * 8 + 40;

  // 3. Get Headers
  var table = document.getElementById("param-table");
  if (!table) return;
  var ths = table.querySelectorAll("th");
  if (ths.length < 5) return;

  // Scale Name Column (Index 0)
  if (namePx < 120) namePx = 120; // Absolute Min

  // Scale Value Column (Index 1)
  if (exprPx < 120) exprPx = 120; // Absolute Min

  // Apply
  ths[0].style.width = namePx + "px";
  ths[1].style.width = exprPx + "px";

  // Fixed Columns
  ths[2].style.width = "50px"; // Unit
  ths[4].style.width = "34px"; // Actions

  // Comment (Index 3) - Auto rest
  // If table width exceeds container, overflow-x handles it.

  console.log("[ZP] Auto-Sized: Name=" + namePx + "px, Value=" + exprPx + "px");
}
