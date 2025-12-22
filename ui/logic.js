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

// Fill params table with Grouping
function fillTable(params) {
  console.log(
    "[ZP] fillTable called with " + (params ? params.length : "null") + " items"
  );
  GLOBAL_PARAMS = params;
  var tbody = document.querySelector("#param-table tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!params || params.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align:center; color:#555; padding: 20px;">No parameters. Click "+ Add Parameter" to start.</td></tr>';
    return;
  }

  // 1. Group Data
  var groups = {};
  var groupOrder = []; // To keep stability

  params.forEach(function (p) {
    var gName = p.group || "Uncategorized";
    if (!groups[gName]) {
      groups[gName] = [];
      groupOrder.push(gName);
    }
    groups[gName].push(p);
  });

  // 2. Render Groups
  groupOrder.forEach(function (gName) {
    // Header Row
    var headerRow = document.createElement("tr");
    var td = document.createElement("td");
    td.colSpan = 5;
    td.className = "group-header";
    td.innerHTML = '<span class="group-toggle">▼</span> ' + gName;
    td.onclick = function () {
      td.classList.toggle("collapsed");
      var rows = document.querySelectorAll(
        '.group-row[data-group="' + gName + '"]'
      );
      rows.forEach(function (r) {
        if (td.classList.contains("collapsed")) {
          r.classList.add("hidden-row");
        } else {
          r.classList.remove("hidden-row");
        }
      });
    };
    headerRow.appendChild(td);
    tbody.appendChild(headerRow);

    // Param Rows
    groups[gName].forEach(function (p) {
      var tr = document.createElement("tr");
      tr.className = "group-row";
      tr.dataset.group = gName;

      if (p.isUser) {
        tr.dataset.user = "true";
        tr.innerHTML =
          '<td><input type="text" readonly class="tbl-input name" value="' +
          p.name +
          '"></td>' +
          '<td><input type="text" readonly class="tbl-input expr" value="' +
          p.expression +
          '"></td>' +
          '<td style="font-size:11px; color:#666;">' +
          (p.unit || "") +
          "</td>" +
          '<td><input type="text" readonly class="tbl-input comment" value="' +
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

// Global Shortcuts
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    sendToFusion("close_palette", {});
  }
  // Ctrl+P Global Toggle (Capture while focused)
  if (e.ctrlKey && (e.key === "p" || e.key === "P")) {
    e.preventDefault();
    sendToFusion("close_palette", {});
  }
});

var lastEnterTime = 0;
var lastEnterRow = null;

function attachEnterHandlers(context) {
  var allInputs = (context || document).querySelectorAll(".tbl-input");
  allInputs.forEach(function (inp) {
    // Auto-Sync on Change (Seamless Save) and Lock on Blur
    inp.onchange = function () {
      var changes = gatherTableData();
      sendToFusion("batch_update", { items: changes, suppress_refresh: true });
      setStatus("Synced.", "success");
    };

    inp.onblur = function () {
      inp.readOnly = true;
    };

    // Unlock on Double Click
    inp.ondblclick = function () {
      inp.readOnly = false;
      inp.select();
      inp.focus();
    };

    inp.onkeydown = function (e) {
      if (e.key === "Enter") {
        e.preventDefault();

        // If Readonly -> Unlock
        if (inp.readOnly) {
          inp.readOnly = false;
          inp.select();
          return;
        }

        // If Editable -> Save / New Row
        var tr = inp.closest("tr");
        var now = Date.now();

        // 1. Always Sync
        var changes = gatherTableData();
        sendToFusion("batch_update", {
          items: changes,
          suppress_refresh: true,
        });

        // 2. Double Enter Check
        if (lastEnterRow === tr && now - lastEnterTime < 3000) {
          addNewRow();
          lastEnterTime = 0;
          lastEnterRow = null;
        } else {
          lastEnterTime = now;
          lastEnterRow = tr;
          setStatus("Saved. Press Enter again to add new.", "info");
        }
      }
    };
  });
}

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

  var currentGroup = ""; // track context

  rows.forEach(function (row) {
    // Check if header
    if (row.querySelector(".group-header")) {
      currentGroup = row.innerText.replace("▼", "").replace("►", "").trim();
      return;
    }

    var nameInput = row.querySelector(".name");
    var exprInput = row.querySelector(".expr");
    var cmtInput = row.querySelector(".comment");

    if (nameInput && exprInput) {
      var rawCmt = cmtInput ? cmtInput.value.trim() : "";

      // Re-inject Group Tag if needed
      // Logic: If user didn't write a tag, and we are in a group, add it.
      // But if user moved it to another group by writing [NewGroup], respect that.
      var finalCmt = rawCmt;

      if (
        currentGroup &&
        currentGroup !== "Uncategorized" &&
        currentGroup !== "Model Parameters"
      ) {
        // Check if user manually overrode
        if (!rawCmt.startsWith("[")) {
          finalCmt = "[" + currentGroup + "] " + rawCmt;
        }
      }

      changes.push({
        name: nameInput.value.trim(),
        expression: exprInput.value.trim(),
        comment: finalCmt,
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

                // Update Fits
                if (parsed.content.fits) {
                  FIT_DEFAULTS = parsed.content.fits;
                }

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

  // Initialize Resizable Columns
  setTimeout(initResize, 100); // Small delay to ensure layout

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

  // Auto Sort
  var sortBtn = document.getElementById("sort-btn");
  if (sortBtn) {
    sortBtn.onclick = function () {
      setStatus("Crawling dependencies... (this may take a moment)", "info");
      sendToFusion("auto_sort", {});
    };
  }

  // --- SMART FIT LOGIC ---
  var fitBtn = document.getElementById("fit-btn");
  var fitModal = document.getElementById("fit-modal");
  var fitCreateBtn = document.getElementById("fit-create");
  var fitCancelBtn = document.getElementById("fit-cancel");
  var fitSaveDefBtn = document.getElementById("fit-save-def");

  // Inputs
  var ctxInput = document.getElementById("fit-context");
  var sizeInput = document.getElementById("fit-size");
  var tolInput = document.getElementById("fit-tol");
  var previewEl = document.getElementById("fit-preview");

  // Defaults Map (Will be overwritten by backend)
  var FIT_DEFAULTS = {
    bolt: 0.2,
    magnet: 0.15,
    bearing: 0.1,
    insert: -0.1,
    lid: 0.15,
    slider: 0.25,
  };

  function updatePreview() {
    if (!sizeInput || !tolInput) return;
    var s = parseFloat(sizeInput.value) || 0;
    var t = parseFloat(tolInput.value) || 0;
    var res = (s + t).toFixed(3);
    if (previewEl) previewEl.textContent = res + "mm";
  }

  if (fitBtn && fitModal) {
    fitBtn.onclick = function () {
      fitModal.style.display = "block";
      // Load default for current selection
      var val = ctxInput.value;
      if (FIT_DEFAULTS.hasOwnProperty(val)) {
        tolInput.value = FIT_DEFAULTS[val];
        updatePreview();
      }
      sizeInput.focus();
    };

    fitCancelBtn.onclick = function () {
      fitModal.style.display = "none";
    };

    // Auto-update Tolerance when Context changes
    if (ctxInput) {
      ctxInput.onchange = function () {
        var val = ctxInput.value;
        if (FIT_DEFAULTS.hasOwnProperty(val)) {
          tolInput.value = FIT_DEFAULTS[val];
          updatePreview();
        }
      };
    }

    // Live Preview
    if (sizeInput) sizeInput.oninput = updatePreview;
    if (tolInput) tolInput.oninput = updatePreview;

    // Save Defaults
    if (fitSaveDefBtn) {
      fitSaveDefBtn.onclick = function () {
        var ctx = ctxInput.value;
        var tol = parseFloat(tolInput.value) || 0;

        // Update Local
        FIT_DEFAULTS[ctx] = tol;

        // Send to Backend
        sendToFusion("save_fit_defaults", { fits: FIT_DEFAULTS });
        setStatus("Saving default for " + ctx + "...", "info");
      };
    }

    fitCreateBtn.onclick = function () {
      var ctx = ctxInput.value;
      var size = parseFloat(sizeInput.value) || 0;
      var tol = parseFloat(tolInput.value) || 0;
      var sign = tol >= 0 ? "+" : "-";
      var absTol = Math.abs(tol);

      // GENERATE LOGIC
      var name = "";
      var expr = size + "mm " + sign + " " + absTol + "mm";
      var comment = "[SmartFit] ";

      if (ctx === "bolt") {
        name = "Hole_M" + size;
        comment += "M" + size + " Clearance";
      } else if (ctx === "magnet") {
        name = "Mag_" + size + "mm";
        comment += "Magnet Press";
      } else if (ctx === "bearing") {
        name = "Brg_" + size + "mm";
        comment += "Bearing Press";
      } else if (ctx === "insert") {
        name = "Ins_M" + Math.floor(size);
        comment += "Heat Set Insert";
      } else if (ctx === "lid") {
        name = "Lid_Gap";
        expr = absTol + "mm"; // Lids are usually just the gap value
        comment += "Friction Fit Lid";
      } else {
        name = "Fit_Gen";
        comment += "General Clearance";
      }

      // Insert
      var tbody = document.querySelector("#param-table tbody");
      var emptyMsg = tbody.querySelector("td[colspan]");
      if (emptyMsg) emptyMsg.closest("tr").remove();

      var tr = document.createElement("tr");
      tr.dataset.user = "true";
      tr.className = "group-row";
      tr.dataset.group = "SmartFit";

      tr.innerHTML =
        '<td><input type="text" class="tbl-input name" value="' +
        name +
        '"></td>' +
        '<td><input type="text" class="tbl-input expr" value="' +
        expr +
        '"></td>' +
        '<td style="font-size:11px; color:#666;">mm</td>' +
        '<td><input type="text" class="tbl-input comment" value="' +
        comment +
        '"></td>' +
        '<td><button class="row-delete" title="Delete">×</button></td>';

      // Insert at top
      tbody.insertBefore(tr, tbody.firstChild);

      attachDeleteHandlers(tr);
      attachEnterHandlers(tr);

      // Auto-save
      var changes = gatherTableData();
      sendToFusion("batch_update", { items: changes, suppress_refresh: false });

      fitModal.style.display = "none";
      setStatus("Created Smart Fit: " + name, "success");
    };
  }

  // -------------------------------------------------------------------------
  // WATCHDOG LOOP (Smart Polling for Tab Changes)
  // -------------------------------------------------------------------------
  // --- EVENT LISTENER (PUSH FROM PYTHON) ---
  window.response = function (dataStr) {
    console.log("[ZP] Received PUSH event");
    try {
      var data = JSON.parse(dataStr);
      var type = data.type;
      var content = data.content;

      if (type === "update_table") {
        console.log("[ZP] Event: update_table");
        fillTable(content);
      } else if (type === "notification") {
        // Handle Notification {message, status}
        var msg = data.message || content; // Backwards compat
        var status = data.status || "info";
        setStatus(msg, status);
      } else if (type === "init_all") {
        console.log("[ZP] Event: init_all (Push)");
        fillPresets(content.presets || {});
        fillTable(content.params || []);
        updateCurrentPreset(content.current_preset);
        if (content.fits) FIT_DEFAULTS = content.fits;

        // Legacy Logic
        var legacyNotice = document.getElementById("legacy-notice");
        if (legacyNotice) {
          legacyNotice.style.display =
            content.legacy_params === true ? "block" : "none";
        }
      }
    } catch (e) {
      console.error("[ZP] Event Push Error:", e);
    }
  };

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

// --- RESIZE LOGIC ---
function initResize() {
  var table = document.getElementById("param-table");
  if (!table) return;
  var headers = table.querySelectorAll("th");

  headers.forEach(function (th) {
    if (th.innerHTML === "" || th.classList.contains("no-resize")) return;

    var resizer = document.createElement("div");
    resizer.className = "resizer";
    th.appendChild(resizer);

    createResizer(resizer, th);
  });
}

function createResizer(resizer, th) {
  var x, w;

  resizer.onmousedown = function (e) {
    e.preventDefault();
    x = e.clientX;

    var styles = window.getComputedStyle(th);
    w = parseInt(styles.width, 10);

    resizer.classList.add("resizing");
    document.body.style.cursor = "col-resize"; // Global cursor

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  function onMouseMove(e) {
    var dx = e.clientX - x;
    th.style.width = w + dx + "px";
  }

  function onMouseUp() {
    resizer.classList.remove("resizing");
    document.body.style.cursor = "default";
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  }
}
