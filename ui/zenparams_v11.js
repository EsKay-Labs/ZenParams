// ZenParams v11 - SYNC RESPONSE VERSION
console.log("[ZP] Script loading...");

// Simple preset filler
function fillPresets(presets) {
  var select = document.getElementById("preset-select");
  if (!select) return;
  select.innerHTML =
    '<option value="" disabled selected>Load Preset...</option>';
  for (var name in presets) {
    var opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }
  console.log("[ZP] Presets filled!");
  var statusEl = document.getElementById("status-bar");
  if (statusEl) statusEl.textContent = "Presets loaded!";
}

// Request data from Python - SYNC VERSION
function requestData() {
  console.log("[ZP] Requesting initial data (SYNC)...");
  var statusEl = document.getElementById("status-bar");
  try {
    // fusionSendData returns the response synchronously via args.returnData
    var response = adsk.fusionSendData(
      "send",
      JSON.stringify({ action: "get_initial_data", data: {} })
    );
    console.log("[ZP] Got SYNC response:", response);

    if (response) {
      // Response should be a JSON string
      var parsed = JSON.parse(response);
      console.log("[ZP] Parsed response:", parsed);

      if (
        parsed.type === "init_all" &&
        parsed.content &&
        parsed.content.presets
      ) {
        fillPresets(parsed.content.presets);
        if (statusEl) statusEl.textContent = "Presets loaded!";
      } else {
        if (statusEl) statusEl.textContent = "Invalid response format";
      }
    } else {
      console.log("[ZP] No response from fusionSendData");
      if (statusEl) statusEl.textContent = "No response - retrying...";
      setTimeout(requestData, 1000);
    }
  } catch (e) {
    console.log("[ZP] fusionSendData failed:", e);
    if (statusEl) statusEl.textContent = "Error: " + e.message;
  }
}

// On DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("[ZP] DOM ready");
  var statusEl = document.getElementById("status-bar");
  if (statusEl) statusEl.textContent = "JS Loaded - Requesting...";

  // Request data after short delay
  setTimeout(requestData, 500);
});

console.log("[ZP] Script fully loaded");
