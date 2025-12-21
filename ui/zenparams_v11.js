// ZenParams v11 - PROMISE-BASED VERSION
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

// Request data from Python - PROMISE VERSION
function requestData() {
  console.log("[ZP] Requesting initial data...");
  var statusEl = document.getElementById("status-bar");
  try {
    // fusionSendData returns a Promise
    var promise = adsk.fusionSendData(
      "send",
      JSON.stringify({ action: "get_initial_data", data: {} })
    );

    if (promise && promise.then) {
      promise
        .then(function (response) {
          console.log("[ZP] Promise resolved:", response);

          if (response) {
            try {
              var parsed = JSON.parse(response);
              console.log("[ZP] Parsed response:", parsed);

              if (
                parsed.type === "init_all" &&
                parsed.content &&
                parsed.content.presets
              ) {
                fillPresets(parsed.content.presets);
              } else {
                if (statusEl) statusEl.textContent = "Invalid format";
              }
            } catch (parseErr) {
              console.log("[ZP] Parse error:", parseErr);
              if (statusEl)
                statusEl.textContent = "Parse error: " + parseErr.message;
            }
          } else {
            console.log("[ZP] Empty response");
            if (statusEl) statusEl.textContent = "Empty response - retrying...";
            setTimeout(requestData, 1000);
          }
        })
        .catch(function (err) {
          console.log("[ZP] Promise error:", err);
          if (statusEl) statusEl.textContent = "Promise error";
        });
    } else {
      // Not a promise, try direct
      console.log("[ZP] Not a promise, raw:", promise);
      if (statusEl) statusEl.textContent = "Direct response: " + typeof promise;
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
