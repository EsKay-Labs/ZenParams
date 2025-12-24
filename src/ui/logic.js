// ZenParams v11 - FULL FUNCTIONAL VERSION
console.log("[ZP] Script loading...");

// Global state
var GLOBAL_PRESETS = {};
var GLOBAL_PARAMS = [];
var FIT_DATA = { standards: [], customs: [] };
var FIT_LOOKUP = {}; // ID -> Tol

// --- GLOBAL EVENT LISTENER (PUSH FROM PYTHON) ---
// Defined at top-level to be immediately available when Fusion calls
window.response = function (dataStr) {
  console.log("[ZP] Received PUSH event");
  console.log("[ZP] Raw Data:", dataStr ? dataStr.substring(0, 200) : "null");
  try {
    var data = JSON.parse(dataStr);
    var type = data.type;
    var content = data.content;

    if (type === "update_table") {
      console.log(
        "[ZP] Event: update_table -> fillTable with " +
          (content ? content.length : "null") +
          " items"
      );
      fillTable(content);
    } else if (type === "notification") {
      var msg = data.message || content;
      var status = data.status || "info";
      setStatus(msg, status);
    } else if (type === "init_all") {
      console.log("[ZP] Event: init_all (Push)");
      fillPresets(content.presets || {});
      fillTable(content.params || []);
      updateCurrentPreset(content.current_preset);
      // 1. Fresh Structure (Backwards Compatible check)
      if (content.fits && content.fits.standards) {
        FIT_DATA = content.fits;
      } else {
        // 2. Fallback: Backend sent old flat dict OR nothing
        var rawFits = content.fits || {};
        console.log("[ZP] Converting legacy/missing fit data locally...");
        var legacyStandards = [];
        var legacyCustoms = [];

        // Known Map (must match desired defaults)
        var MAP = {
          bolt: { l: "Bolt Clearance", g: "3D Printing" },
          magnet: { l: "Magnet Press", g: "3D Printing" },
          bearing: { l: "Bearing Press", g: "3D Printing" },
          insert: { l: "Heat Set Insert", g: "3D Printing" },
          lid: { l: "Lid (Snug)", g: "3D Printing" },
          slider: { l: "Slider / Moving", g: "3D Printing" },
          iso_h7: { l: "ISO H7 (Sliding)", g: "Mechanical" },
          iso_p7: { l: "ISO P7 (Press)", g: "Mechanical" },
          cnc_clr: { l: "CNC Clearance", g: "Mechanical" },
        };

        // A. Process what we received
        for (var key in rawFits) {
          var val = rawFits[key];
          if (MAP[key]) {
            legacyStandards.push({
              id: key,
              label: MAP[key].l,
              group: MAP[key].g,
              tol: val,
            });
          } else {
            legacyCustoms.push({
              id: key,
              label: key,
              group: "Custom",
              tol: val,
            });
          }
        }

        // B. Inject missing defaults (If backend is REALLY old/empty)
        for (var k in MAP) {
          if (!rawFits.hasOwnProperty(k)) {
            // Guess default
            var dVal = 0.1;
            if (k === "bolt") dVal = 0.2;
            else if (k === "insert") dVal = -0.1;
            else if (k === "slider") dVal = 0.25;

            legacyStandards.push({
              id: k,
              label: MAP[k].l,
              group: MAP[k].g,
              tol: dVal,
            });
          }
        }

        FIT_DATA = { standards: legacyStandards, customs: legacyCustoms };
      }

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
    td.className = "group-header-cell"; // New class for cell
    td.style.padding = "0";
    td.style.border = "none";

    var div = document.createElement("div");
    div.className = "group-header collapsed"; // Style applied to div
    div.setAttribute("data-category", gName); // Style hook

    // Count of params in this group
    var count = groups[gName].length;
    div.innerHTML =
      '<span class="group-toggle">►</span> ' +
      gName +
      ' <span class="group-count">(' +
      count +
      ")</span>";

    // Click handler
    div.onclick = function () {
      console.log("[ZP] Group Clicked: " + gName);
      div.classList.toggle("collapsed");
      var isClosed = div.classList.contains("collapsed");

      // Toggle Icon
      var toggle = div.querySelector(".group-toggle");
      if (toggle) toggle.innerText = isClosed ? "►" : "▼";

      var allRows = tbody.querySelectorAll("tr.group-row");
      var count = 0;
      allRows.forEach(function (r) {
        if (r.dataset.group === gName) {
          count++;
          if (isClosed) {
            r.classList.add("hidden-row");
          } else {
            r.classList.remove("hidden-row");
          }
        }
      });
      console.log("[ZP] Toggled " + count + " rows for group: " + gName);
    };

    td.appendChild(div);
    headerRow.appendChild(td);
    tbody.appendChild(headerRow);

    // Param Rows
    groups[gName].forEach(function (p) {
      var tr = document.createElement("tr");
      tr.className = "group-row hidden-row"; // Default Hidden
      tr.dataset.group = gName;

      if (p.isUser) {
        tr.dataset.user = "true";
        tr.innerHTML =
          '<td><input type="text" readonly class="tbl-input name" style="width:100%" value="' +
          p.name +
          '"></td>' +
          '<td><input type="text" readonly class="tbl-input expr" style="width:100%" value="' +
          p.expression +
          '"></td>' +
          '<td style="font-size:11px; color:#666;">' +
          (p.unit || "") +
          "</td>" +
          '<td><input type="text" readonly class="tbl-input comment" style="width:100%" value="' +
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

  // Trigger Auto-Size
  if (params.length > 0) {
    setTimeout(function () {
      autoSizeColumns(params);
    }, 50);
  }
}

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

  // Cap max length to prevent insanity
  if (maxNameLen > 80) maxNameLen = 80;
  if (maxExprLen > 80) maxExprLen = 80;

  // 2. Convert to Pixels (Liberal padding)
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

  // Apply and Log
  ths[0].style.width = namePx + "px";
  ths[1].style.width = exprPx + "px";

  // Fixed Columns
  ths[2].style.width = "50px";
  ths[4].style.width = "34px";

  // Comment (Index 3) - Auto rest

  console.log("[ZP] Auto-Sized: Name=" + namePx + "px, Value=" + exprPx + "px");
}

// Real-time search filter
function filterTable(query) {
  var q = query.toLowerCase().trim();
  var tbody = document.querySelector("#param-table tbody");
  if (!tbody) return;

  // Get all rows
  var allRows = tbody.querySelectorAll("tr");
  var groupVisibility = {}; // Track if group has visible items

  allRows.forEach(function (row) {
    // Check if this is a group header (has .group-header in its td)
    var headerTd = row.querySelector(".group-header");
    if (headerTd) {
      // Skip headers on first pass
      return;
    }

    // Data rows (have .group-row class)
    if (!row.classList.contains("group-row")) return;

    var nameInput = row.querySelector(".name");
    var exprInput = row.querySelector(".expr");
    var commentInput = row.querySelector(".comment");

    var name = nameInput ? nameInput.value.toLowerCase() : "";
    var expr = exprInput ? exprInput.value.toLowerCase() : "";
    var comment = commentInput ? commentInput.value.toLowerCase() : "";
    var group = row.dataset.group || "";

    var match =
      q === "" || name.includes(q) || expr.includes(q) || comment.includes(q);

    // Don't hide with display:none, toggle the hidden-row class instead
    if (match) {
      row.classList.remove("hidden-row");
      groupVisibility[group] = true;
    } else {
      row.classList.add("hidden-row");
    }
  });

  // Now toggle group headers based on visibility
  allRows.forEach(function (row) {
    var headerTd = row.querySelector(".group-header");
    if (headerTd) {
      var gName = "";
      // Extract group name from data-group of child rows
      var nextRow = row.nextElementSibling;
      if (nextRow && nextRow.dataset.group) {
        gName = nextRow.dataset.group;
      }
      var hasVisible = groupVisibility[gName] || false;
      row.style.display = q === "" || hasVisible ? "" : "none";
    }
  });
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
          console.log("[ZP] Delete Response:", resp);
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
            console.error("[ZP] Delete Parse Err:", e);
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

  // Ctrl+Enter: Add new parameter anywhere
  if (e.ctrlKey && e.key === "Enter") {
    e.preventDefault();
    addNewRow();
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

        // If Editable -> Save and exit edit mode
        // (Double-Enter is handled globally)
        var changes = gatherTableData();
        sendToFusion("batch_update", {
          items: changes,
          suppress_refresh: true,
        });

        // Exit edit mode
        inp.readOnly = true;
        inp.blur();
        setStatus("Saved.", "success");
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

  // Search Filter
  var searchInput = document.getElementById("param-search");
  if (searchInput) {
    searchInput.oninput = function () {
      filterTable(searchInput.value);
    };
  }

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
  var fitAddCustomBtn = document.getElementById("fit-add-custom-btn");

  // Inputs
  var ctxSelect = document.getElementById("fit-context");
  var nameInput = document.getElementById("fit-name");
  var sizeInput = document.getElementById("fit-size");
  var tolInput = document.getElementById("fit-tol");
  var previewEl = document.getElementById("fit-preview");

  // Data Store
  // MOVED TO GLOBAL SCOPE

  function refreshFitLookup() {
    FIT_LOOKUP = {};
    if (FIT_DATA.standards) {
      FIT_DATA.standards.forEach(function (f) {
        FIT_LOOKUP[f.id] = f.tol;
      });
    }
    if (FIT_DATA.customs) {
      FIT_DATA.customs.forEach(function (f) {
        FIT_LOOKUP[f.id] = f.tol;
      });
    }
  }

  function initFitUI() {
    if (!ctxSelect) return;

    // FAILSAFE: If no data loaded (frontend restart without backend push), use defaults
    if (!FIT_DATA.standards || FIT_DATA.standards.length === 0) {
      console.warn("[ZP] FIT_DATA empty in UI Init - injecting defaults");
      var legacyStandards = [
        { id: "bolt", label: "Bolt Clearance", group: "3D Printing", tol: 0.2 },
        {
          id: "magnet",
          label: "Magnet Press",
          group: "3D Printing",
          tol: 0.15,
        },
        {
          id: "bearing",
          label: "Bearing Press",
          group: "3D Printing",
          tol: 0.1,
        },
        {
          id: "insert",
          label: "Heat Set Insert",
          group: "3D Printing",
          tol: -0.1,
        },
        { id: "lid", label: "Lid (Snug)", group: "3D Printing", tol: 0.15 },
        {
          id: "slider",
          label: "Slider / Moving",
          group: "3D Printing",
          tol: 0.25,
        },
        {
          id: "iso_h7",
          label: "ISO H7 (Sliding)",
          group: "Mechanical",
          tol: 0.012,
        },
        {
          id: "iso_p7",
          label: "ISO P7 (Press)",
          group: "Mechanical",
          tol: -0.015,
        },
        {
          id: "cnc_clr",
          label: "CNC Clearance",
          group: "Mechanical",
          tol: 0.1,
        },
      ];
      FIT_DATA.standards = legacyStandards;
    }

    refreshFitLookup();
    ctxSelect.innerHTML = "";

    // Helper to add OptGroup
    function addGroup(label, items) {
      if (!items || items.length === 0) return;
      var grp = document.createElement("optgroup");
      grp.label = label;
      items.forEach(function (item) {
        var opt = document.createElement("option");
        opt.value = item.id;
        opt.textContent =
          item.label + (item.tol > 0 ? " (+" : " (") + item.tol + ")";
        grp.appendChild(opt);
      });
      ctxSelect.appendChild(grp);
    }

    // 1. Group Standards
    var groups = {};
    FIT_DATA.standards.forEach(function (f) {
      var g = f.group || "General";
      if (!groups[g]) groups[g] = [];
      groups[g].push(f);
    });

    for (var gName in groups) {
      addGroup(gName, groups[gName]);
    }

    // 2. Customs
    if (FIT_DATA.customs && FIT_DATA.customs.length > 0) {
      addGroup("User Custom", FIT_DATA.customs);
    }

    // Trigger update
    updateFitContext();
  }

  function updateFitContext() {
    var val = ctxSelect.value;
    if (FIT_LOOKUP.hasOwnProperty(val)) {
      tolInput.value = FIT_LOOKUP[val];
      updatePreview();
      autoGenerateName();
    }
  }

  function autoGenerateName() {
    // Only auto-gen if user hasn't typed a custom one?
    // Or just overwrite? Let's overwrite for now, user can edit after.
    // Better: check if it matches a pattern.
    var ctx = ctxSelect.value;
    var size = parseFloat(sizeInput.value) || 0;
    var base = "";

    // Simple heuristic for defaults
    if (ctx.includes("bolt") || ctx.includes("hole")) base = "Hole_M" + size;
    else if (ctx.includes("magnet")) base = "Mag_" + size + "mm";
    else if (ctx.includes("bearing")) base = "Brg_" + size + "mm";
    else if (ctx.includes("insert")) base = "Ins_M" + Math.floor(size);
    else if (ctx.includes("lid")) base = "Lid_Gap";
    else if (ctx.includes("slider")) base = "Slide_Gap";
    else base = "Fit_" + size + "mm";

    // If existing value is empty or looks like an auto-gen, update it
    // Simple verification: Update always for wizard-like feel
    if (nameInput) nameInput.value = base;
  }

  function updatePreview() {
    if (!sizeInput || !tolInput) return;
    var s = parseFloat(sizeInput.value) || 0;
    var t = parseFloat(tolInput.value) || 0;
    var res = (s + t).toFixed(3);
    if (previewEl) previewEl.textContent = res + "mm";
  }

  // --- Handlers ---

  if (fitBtn && fitModal) {
    fitBtn.onclick = function () {
      fitModal.style.display = "block";
      initFitUI();
      sizeInput.focus();
    };

    fitCancelBtn.onclick = function () {
      fitModal.style.display = "none";
    };

    if (ctxSelect) ctxSelect.onchange = updateFitContext;
    if (sizeInput) {
      sizeInput.oninput = function () {
        updatePreview();
        autoGenerateName();
      };
    }
    if (tolInput) tolInput.oninput = updatePreview;

    // SAVE DEFAULTS
    if (fitSaveDefBtn) {
      fitSaveDefBtn.onclick = function () {
        var ctxId = ctxSelect.value;
        var tol = parseFloat(tolInput.value) || 0;

        // Is it Standard or Custom?
        var isCustom = false;
        var customIdx = -1;

        if (FIT_DATA.customs) {
          customIdx = FIT_DATA.customs.findIndex(function (c) {
            return c.id === ctxId;
          });
          if (customIdx >= 0) isCustom = true;
        }

        if (isCustom) {
          // Update Custom
          FIT_DATA.customs[customIdx].tol = tol;
        } else {
          // Update Standard (in memory)
          var std = FIT_DATA.standards.find(function (s) {
            return s.id === ctxId;
          });
          if (std) std.tol = tol;
        }

        // Refresh Lookup & UI text
        refreshFitLookup();
        initFitUI(); // Re-render to show new tolerance in dropdown
        ctxSelect.value = ctxId; // Restore selection

        // PREPARE PAYLOAD { overrides: {}, custom: [] }
        var payload = { overrides: {}, custom: FIT_DATA.customs || [] };
        FIT_DATA.standards.forEach(function (s) {
          // If it differs from HARDCODED default?
          // We don't know hardcoded here easily.
          // Simpler: Just save ALL standards as overrides?
          // Or better: The backend handles "overrides".
          // So we send { overrides: {id: tol}, ... }
          // Let's just send the current state of standards as overrides map.
          payload.overrides[s.id] = s.tol;
        });

        sendToFusion("save_fit_defaults", { fits: payload });
        setStatus("Saved default for " + ctxId, "success");
      };
    }

    // ADD CUSTOM FIT
    if (fitAddCustomBtn) {
      fitAddCustomBtn.onclick = function () {
        var label = prompt("Enter name for new Fit Type (e.g. 'Laser Kerf'):");
        if (!label) return;

        var id = "custom_" + label.toLowerCase().replace(/[^a-z0-9]/g, "_");
        var newFit = {
          id: id,
          label: label,
          group: "Custom",
          tol: 0.1,
        };

        if (!FIT_DATA.customs) FIT_DATA.customs = [];
        FIT_DATA.customs.push(newFit);

        refreshFitLookup();
        initFitUI();
        ctxSelect.value = id;
        updateFitContext();

        // Auto-save existence
        fitSaveDefBtn.click();
      };
    }

    fitCreateBtn.onclick = function () {
      var name = nameInput.value || "New_Param";
      var size = parseFloat(sizeInput.value) || 0;
      var tol = parseFloat(tolInput.value) || 0;
      var sign = tol >= 0 ? "+" : "-";
      var absTol = Math.abs(tol);

      // GENERATE
      var expr = size + "mm " + sign + " " + absTol + "mm";
      var comment =
        "[SmartFit] " +
        (ctxSelect.options[ctxSelect.selectedIndex].text || "Custom Gap");

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
      setStatus("Created: " + name, "success");
    };
  }

  // WATCHDOG LOOP removed - window.response now at global scope (top of file)

  var lastDocId = "";
  var lastDataVersion = -1; // Track Python's _data_version

  // Tab Change Detection (every 2.5s)
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
                  lastDataVersion = -1; // Reset version on tab change
                }
                lastDocId = info.id;
              }
            } catch (e) {}
          }
        });
      }
    } catch (e) {}
  }, 2500);

  // DATA VERSION POLLING (fast sync using request/response pattern)
  // Python increments _data_version when auto-sort runs. We poll for changes.
  setInterval(function () {
    try {
      var promise = adsk.fusionSendData(
        "send",
        JSON.stringify({ action: "get_data_version", data: {} })
      );
      if (promise && promise.then) {
        promise.then(function (resp) {
          if (resp) {
            try {
              var info = JSON.parse(resp);
              if (info && typeof info.version === "number") {
                // If version changed, refresh the table!
                if (lastDataVersion >= 0 && info.version !== lastDataVersion) {
                  console.log("[ZP] Data Version Changed! Refreshing...");
                  requestData();
                }
                lastDataVersion = info.version;
              }
            } catch (e) {}
          }
        });
      }
    } catch (e) {}
  }, 1000); // Check every 1s for fast sync

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
      // Note: Preset deletion only removes the template file
      // It does NOT affect actual Fusion 360 parameters
      updateCurrentPreset(null);
      setStatus("Deleted preset: " + selected, "success");
      setTimeout(requestData, 500); // Refresh to show updated preset list
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
