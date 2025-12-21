// ZenParams v11 - MINIMAL DEBUG VERSION
console.log("[ZP] Script loading...");

// Global response handler - MUST be defined before DOMContentLoaded
window.response = function (incoming) {
  console.log("[ZP] response() called!", incoming);
  try {
    var statusEl = document.getElementById("status-bar");
    if (statusEl) statusEl.textContent = "GOT DATA!";

    // Parse the data
    var data = incoming;
    if (incoming && incoming.data) {
      data = incoming.data;
    }

    console.log("[ZP] Raw data:", data);
    var parsed = JSON.parse(data);
    console.log("[ZP] Parsed:", parsed);

    if (
      parsed.type === "init_all" &&
      parsed.content &&
      parsed.content.presets
    ) {
      console.log("[ZP] Got presets:", parsed.content.presets);
      fillPresets(parsed.content.presets);
    }
  } catch (err) {
    console.log("[ZP] Error in response:", err);
    var statusEl = document.getElementById("status-bar");
    if (statusEl) statusEl.textContent = "Error: " + err.message;
  }
};

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

// Request data from Python
function requestData() {
  console.log("[ZP] Requesting initial data...");
  try {
    adsk.fusionSendData(
      "send",
      JSON.stringify({ action: "get_initial_data", data: {} })
    );
  } catch (e) {
    console.log("[ZP] fusionSendData failed:", e);
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

// Also try registering handler with eventHandlers
if (typeof adsk !== "undefined" && adsk.eventHandlers) {
  adsk.eventHandlers["response"] = window.response;
  console.log("[ZP] Registered with eventHandlers");
}

console.log("[ZP] Script fully loaded");
