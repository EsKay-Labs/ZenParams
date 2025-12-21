// ZenParams v11 - FULL FUNCTIONAL VERSION
console.log("[ZP] Script loading...");

// Global state
var GLOBAL_PRESETS = {};
var GLOBAL_PARAMS = [];

// Simple preset filler
function fillPresets(presets) {
  GLOBAL_PRESETS = presets;
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
  setStatus("Ready.", "success");
}

// Fill params table
function fillTable(params) {
  GLOBAL_PARAMS = params;
  var tbody = document.querySelector("#param-table tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!params || params.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align:center; color:#555; padding: 20px;">No parameters. Click "+ Add Parameter" to start.</td></tr>';
    return;
  }

  params.forEach(function (p) {
    var tr = document.createElement("tr");
    if (p.isUser) {
      tr.dataset.user = "true";
      tr.innerHTML =
        '<td><input type="text" class="tbl-input name" value="' +
        p.name +
        '"></td>' +
        '<td><input type="text" class="tbl-input expr" value="' +
        p.expression +
        '"></td>' +
        '<td style="font-size:11px; color:#666;">' +
        (p.unit || "") +
        "</td>" +
        '<td><input type="text" class="tbl-input comment" value="' +
        (p.comment || "") +
        '"></td>' +
        '<td><button class="row-delete" title="Delete">×</button></td>';
    } else {
      tr.classList.add("model-param");
      tr.innerHTML =
        "<td>" +
        p.name +
        "</td>" +
        '<td style="font-family:consolas; color:#ce9178">' +
        p.expression +
        "</td>" +
        '<td style="font-size:11px; color:#666;">' +
        (p.unit || "") +
        "</td>" +
        '<td style="color:#666; font-style:italic;">' +
        (p.comment || "") +
        "</td>" +
        "<td></td>";
    }
    tbody.appendChild(tr);
  });

  // Attach delete handlers
  attachDeleteHandlers();
  attachEnterHandlers();
}

function attachDeleteHandlers(context) {
  var btns = (context || document).querySelectorAll(".row-delete");
  btns.forEach(function (btn) {
    btn.onclick = function () {
      var tr = btn.closest("tr");
      var nameInput = tr.querySelector(".name");
      var name = nameInput ? nameInput.value : "";
      var isUser = tr.dataset.user === "true";

      if (isUser && name && name !== "new_param") {
        // Attempt Fusion Deletion
        if (!confirm("Delete parameter '" + name + "' from Fusion design?"))
          return;

        setStatus("Deleting...", "info");
        sendToFusion("delete_param", { name: name }).then(function (resp) {
          try {
            var r = JSON.parse(resp);
            if (r.status === "success") {
              tr.remove();
              setStatus(r.msg, "success");
            } else {
              setStatus(r.msg, "error");
              alert(r.msg);
            }
          } catch (e) {
            setStatus("Err: " + e, "error");
          }
        });
      } else {
        // Local delete
        tr.remove();
        setStatus("Row removed.", "info");
      }
    };
  });
}

function attachEnterHandlers(context) {
  var allInputs = (context || document).querySelectorAll(".tbl-input");
  allInputs.forEach(function (inp) {
    inp.onkeydown = function (e) {
      if (e.key === "Enter") {
        e.preventDefault();

        // 1. Instant Sync (No Refresh)
        var changes = gatherTableData();
        sendToFusion("batch_update", {
          items: changes,
          suppress_refresh: true,
        });

        // 2. Continue Flow
        addNewRow();
      }
    };
  });
}

// Global Shortcuts
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    sendToFusion("close_palette", {});
  }
});

function addNewRow() {
  var tbody = document.querySelector("#param-table tbody");
  // Remove empty message if present
  var emptyMsg = tbody.querySelector("td[colspan]");
  if (emptyMsg) emptyMsg.closest("tr").remove();

  var tr = document.createElement("tr");
  tr.dataset.user = "true";
  tr.innerHTML =
    '<td><input type="text" class="tbl-input name" value="new_param"></td>' +
    '<td><input type="text" class="tbl-input expr" value="10mm"></td>' +
    '<td style="font-size:11px; color:#666;">mm</td>' +
    '<td><input type="text" class="tbl-input comment" value=""></td>' +
    '<td><button class="row-delete" title="Delete">×</button></td>';
  tbody.insertBefore(tr, tbody.firstChild);

  // Attach Handlers to this row only
  attachDeleteHandlers(tr);
  attachEnterHandlers(tr);

  tr.querySelector(".name").select();
}

function gatherTableData() {
  var changes = [];
  var rows = document.querySelectorAll("#param-table tbody tr");
  rows.forEach(function (row) {
    var nameInput = row.querySelector(".name");
    var exprInput = row.querySelector(".expr");
    var cmtInput = row.querySelector(".comment");
    if (nameInput && exprInput) {
      changes.push({
        name: nameInput.value.trim(),
        expression: exprInput.value.trim(),
        comment: cmtInput ? cmtInput.value.trim() : "",
        isUser: row.dataset.user === "true",
      });
    }
  });
  return changes;
}

function sendToFusion(action, data) {
  try {
    return adsk.fusionSendData(
      "send",
      JSON.stringify({ action: action, data: data })
    );
  } catch (e) {
    console.log("[ZP] Send failed:", e);
    return Promise.reject(e);
  }
}

function setStatus(msg, type) {
  var el = document.getElementById("status-bar");
  if (el) {
    el.textContent = msg;
    el.className = "status-bar " + (type || "");
  }
}

function updateCurrentPreset(name) {
  var el = document.getElementById("current-preset-name");
  if (el) {
    el.textContent = name || "New Design";
  }
}

// Request data from Python
function requestData() {
  console.log("[ZP] Requesting initial data...");
  setStatus("Loading...", "info");
  try {
    var promise = adsk.fusionSendData(
      "send",
      JSON.stringify({ action: "get_initial_data", data: {} })
    );

    if (promise && promise.then) {
      promise
        .then(function (response) {
          if (response) {
            try {
              var parsed = JSON.parse(response);
              if (parsed.type === "init_all" && parsed.content) {
                fillPresets(parsed.content.presets || {});
                fillTable(parsed.content.params || []);
                updateCurrentPreset(parsed.content.current_preset);

                // SYNC DROPDOWN
                if (
                  parsed.content.current_preset &&
                  document.getElementById("preset-select")
                ) {
                  document.getElementById("preset-select").value =
                    parsed.content.current_preset;
                }

                // LEGACY IMPORT NOTICE
                var legacyNotice = document.getElementById("legacy-notice");
                if (legacyNotice) {
                  if (parsed.content.legacy_params === true) {
                    legacyNotice.style.display = "block";
                  } else {
                    legacyNotice.style.display = "none";
                  }
                }
              }
            } catch (parseErr) {
              setStatus("Parse error", "error");
            }
          } else {
            setStatus("Empty response - retrying...", "info");
            setTimeout(requestData, 1000);
          }
        })
        .catch(function (err) {
          setStatus("Error", "error");
        });
    }
  } catch (e) {
    setStatus("Request failed", "error");
  }
}

// On DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("[ZP] DOM ready");
  setStatus("Loading...", "info");

  // Get elements
  var presetSelect = document.getElementById("preset-select");
  var loadBtn = document.getElementById("load-preset-btn");
  var createBtn = document.getElementById("create-new-btn");
  var saveBtn = document.getElementById("save-preset-btn");
  var deleteBtn = document.getElementById("delete-preset-btn");
  var addRowBtn = document.getElementById("add-row-btn");

  // Help Modal Logic
  var helpBtn = document.getElementById("help-btn");
  var helpModal = document.getElementById("help-modal");
  var closeSpan = helpModal ? helpModal.querySelector(".close") : null;

  if (helpBtn && helpModal) {
    helpBtn.onclick = function () {
      helpModal.style.display = "block";
    };
  }
  if (closeSpan) {
    closeSpan.onclick = function () {
      helpModal.style.display = "none";
    };
  }
  window.onclick = function (event) {
    if (event.target == helpModal) {
      helpModal.style.display = "none";
    }
  };

  // Add Row
  if (addRowBtn) {
    addRowBtn.onclick = function () {
      addNewRow();
    };
  }

  // -------------------------------------------------------------------------
  // WATCHDOG LOOP (Smart Polling for Tab Changes)
  // -------------------------------------------------------------------------
  var lastDocId = "";

  setInterval(function () {
    try {
      var promise = adsk.fusionSendData(
        "send",
        JSON.stringify({ action: "get_active_doc_info", data: {} })
      );
      if (promise && promise.then) {
        promise.then(function (resp) {
          if (resp) {
            try {
              var info = JSON.parse(resp);
              if (info && info.id) {
                // If doc ID changed from last known, Refresh everything!
                if (lastDocId && lastDocId !== info.id) {
                  console.log("[ZP] Tab Change Detected! Refreshing...");
                  setStatus("Syncing...", "info");
                  requestData();
                }
                lastDocId = info.id;
              }
            } catch (e) {}
          }
        });
      }
    } catch (e) {}
  }, 2500); // Check every 2.5s (Less aggressive)

  // Preset Selection

  // LIVE PREVIEW - When preset selection changes, show preview in table
  if (presetSelect) {
    presetSelect.onchange = function () {
      var selected = presetSelect.value;
      if (!selected || !GLOBAL_PRESETS[selected]) return;

      var presetData = GLOBAL_PRESETS[selected];
      if (Object.keys(presetData).length === 0) {
        fillTable([]);
        return;
      }

      // Clear existing rows and show preset as preview
      var tbody = document.querySelector("#param-table tbody");
      tbody.innerHTML = "";

      for (var key in presetData) {
        var tr = document.createElement("tr");
        tr.dataset.user = "true";
        tr.innerHTML =
          '<td><input type="text" class="tbl-input name" value="' +
          key +
          '"></td>' +
          '<td><input type="text" class="tbl-input expr modified" value="' +
          presetData[key] +
          '"></td>' +
          '<td style="font-size:11px; color:#666;">mm</td>' +
          '<td><input type="text" class="tbl-input comment" value=""></td>' +
          '<td><button class="row-delete">×</button></td>';
        tbody.appendChild(tr);
      }
      attachDeleteHandlers();
      setStatus("Preview: " + selected + " (click Apply to load)", "info");
    };
  }

  // Create New Preset
  if (createBtn) {
    createBtn.onclick = function () {
      var name = prompt("Enter preset name:", "my_preset");
      if (!name) return;
      fillTable([]);
      addNewRow();
      updateCurrentPreset("Creating: " + name);
      setStatus("Add parameters then click Save Template", "info");
    };
  }

  // Apply/Load Preset
  if (loadBtn) {
    loadBtn.onclick = function () {
      var selected = presetSelect.value;
      if (!selected) {
        setStatus("Select a preset first", "error");
        return;
      }

      var presetData = GLOBAL_PRESETS[selected];
      if (!presetData) return;

      // Stage the preset (add to table)
      var tbody = document.querySelector("#param-table tbody");
      for (var key in presetData) {
        var tr = document.createElement("tr");
        tr.dataset.user = "true";
        tr.innerHTML =
          '<td><input type="text" class="tbl-input name" value="' +
          key +
          '"></td>' +
          '<td><input type="text" class="tbl-input expr modified" value="' +
          presetData[key] +
          '"></td>' +
          '<td style="font-size:11px; color:#666;">mm</td>' +
          '<td><input type="text" class="tbl-input comment" value=""></td>' +
          '<td><button class="row-delete">×</button></td>';
        tbody.insertBefore(tr, tbody.firstChild);
      }
      attachDeleteHandlers();

      // Apply to Fusion
      var changes = gatherTableData();
      sendToFusion("batch_update", changes);
      sendToFusion("set_current_preset", { name: selected });
      updateCurrentPreset(selected);
      setStatus("Applied: " + selected, "success");
    };
  }

  // Save Template
  if (saveBtn) {
    saveBtn.onclick = function () {
      var allData = gatherTableData();
      var userParams = allData.filter(function (item) {
        return item.isUser === true;
      });

      if (userParams.length === 0) {
        setStatus("No parameters to save", "error");
        return;
      }

      var name = prompt("Name your preset:", "my_preset");
      if (!name) return;

      var paramsDict = {};
      userParams.forEach(function (item) {
        paramsDict[item.name] = item.expression;
      });

      sendToFusion("save_preset", { name: name, params: paramsDict });
      updateCurrentPreset(name);
      setStatus("Saved: " + name, "success");

      // Refresh to get updated list
      setTimeout(requestData, 500);
    };
  }

  // Delete Preset
  if (deleteBtn) {
    deleteBtn.onclick = function () {
      var selected = presetSelect.value;
      if (!selected) {
        setStatus("Select a preset first", "error");
        return;
      }
      if (!confirm("Delete preset: " + selected + "?")) return;

      sendToFusion("delete_preset", { name: selected });
      fillTable([]);
      updateCurrentPreset(null);
      setStatus("Deleted: " + selected, "success");
      setTimeout(requestData, 500);
    };
  }

  // Legacy Import Button
  var importLegacyBtn = document.getElementById("import-legacy-btn");
  if (importLegacyBtn && saveBtn) {
    importLegacyBtn.onclick = function () {
      saveBtn.click();
    };
  }

  // Request data after short delay
  setTimeout(requestData, 500);
});

console.log("[ZP] Script fully loaded");
