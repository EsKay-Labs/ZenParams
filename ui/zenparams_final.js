// Phase 4: Editable Table & Batch Sync

// Handler that Fusion recognizes - MUST BE GLOBAL AND IMMEDIATE
window.response = function (dataWrapper) {
  try {
    const statusEl = document.getElementById("status-bar");
    if (statusEl) statusEl.textContent = "Received data from Python!";

    // Fusion wraps data in {data: "..."} or passes it directly
    const jsonStr =
      dataWrapper && dataWrapper.data ? dataWrapper.data : dataWrapper;
    const res = JSON.parse(jsonStr);

    if (res.type === "init_all") {
      if (window.populatePresets) window.populatePresets(res.content.presets);
      if (window.updateTable) window.updateTable(res.content.params);
      if (statusEl) {
        statusEl.textContent = "System Loaded (Atomic).";
        statusEl.className = "status-bar success";
      }
    } else if (res.type === "init_presets") {
      if (window.populatePresets) window.populatePresets(res.content.presets);
    } else if (res.type === "update_table") {
      if (window.updateTable) window.updateTable(res.content);
      if (statusEl) {
        statusEl.textContent = "Table synced from Fusion.";
        statusEl.className = "status-bar success";
      }
    } else if (res.type === "notification") {
      if (statusEl) {
        statusEl.textContent = res.message;
        statusEl.className = `status-bar ${res.status}`;
      }
    }
  } catch (e) {
    const statusEl = document.getElementById("status-bar");
    if (statusEl) {
      statusEl.textContent = "JS Error: " + e.message;
      statusEl.className = "status-bar error";
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("console-input");
  const status = document.getElementById("status-bar");

  // IMMEDIATE LOAD PROOF
  status.textContent = "JS FILE LOADED v6.0";

  const presetSelect = document.getElementById("preset-select");
  const loadPresetBtn = document.getElementById("load-preset-btn");
  const deletePresetBtn = document.getElementById("delete-preset-btn");
  const addRowBtn = document.getElementById("add-row-btn");
  const delRowBtn = document.getElementById("del-row-btn");
  const savePresetBtn = document.getElementById("save-preset-btn");
  const selectAllCb = document.getElementById("select-all");

  let GLOBAL_PRESETS = {};
  let GLOBAL_PARAMS = [];
  let LAST_SAVED_PRESET = null; // Track last saved preset to auto-select
  let CURRENT_PRESET = null; // Track currently loaded preset

  // SYSTEM PRESETS (Hardcoded Names to Protect)
  const SYSTEM_PRESETS = [
    "3D Print (Tight Fit)",
    "3D Print (Balanced)",
    "3D Print (Loose Fit)",
  ];

  // Add Row Method
  addRowBtn.addEventListener("click", () => {
    addNewRow();
    updateCurrentPreset(null); // Clear current preset on manual add
  });

  // Save Template Method
  savePresetBtn.addEventListener("click", () => {
    // 1. Gather Data
    const data = gatherTableData();
    if (data.length === 0) {
      setStatus("Table is empty.", "error");
      return;
    }

    // 2. Prompt Name - straight to it, no alerts
    const name = prompt("Name your Custom Preset:", "new_preset_name");
    if (!name) return; // Cancelled

    // Protection: Don't allow system preset names (silent)
    if (SYSTEM_PRESETS.includes(name)) {
      setStatus(
        "Cannot use system preset names. Choose a different name.",
        "error"
      );
      return;
    }

    // 3. Convert List to Dict for Storage
    const paramsDict = {};
    data.forEach((item) => {
      paramsDict[item.name] = item.expression;
    });

    // 4. Send to Backend
    LAST_SAVED_PRESET = name; // Store for auto-selection after backend confirms
    sendToFusion("save_preset", {
      name: name,
      params: paramsDict,
    });

    // 5. Poll for backend response (refresh preset list)
    pollBridgeFile(5); // Poll up to 5 times
  });

  // Delete Preset Method (Protected)
  deletePresetBtn.addEventListener("click", () => {
    const selectedName = presetSelect.value;

    if (!selectedName) {
      setStatus("No preset selected.", "error");
      return;
    }

    // Protection: Cannot delete system presets
    if (SYSTEM_PRESETS.includes(selectedName)) {
      setStatus(`Cannot delete system preset "${selectedName}"!`, "error");
      return;
    }

    // Confirmation
    if (
      !confirm(`Delete preset "${selectedName}"?\n\nThis cannot be undone.`)
    ) {
      return;
    }

    // Send to backend
    sendToFusion("delete_preset", { name: selectedName });

    // Clear current preset if it was deleted
    if (CURRENT_PRESET === selectedName) {
      updateCurrentPreset(null);
    }

    // Poll for refreshed list
    pollBridgeFile(5);
  });

  // Help Modal
  const helpBtn = document.getElementById("help-btn");
  const modal = document.getElementById("help-modal");
  const closeBtn = modal ? modal.querySelector(".close") : null;

  if (helpBtn && modal && closeBtn) {
    helpBtn.addEventListener("click", () => {
      modal.style.display = "block";
    });

    closeBtn.addEventListener("click", () => {
      modal.style.display = "none";
    });

    window.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.style.display = "none";
      }
    });
  }

  // Delete Selected Method
  delRowBtn.addEventListener("click", () => {
    const checked = document.querySelectorAll(".row-cb:checked");
    if (checked.length === 0) return;

    checked.forEach((cb) => {
      const row = cb.closest("tr");
      row.remove();
    });
    setStatus(`Removed ${checked.length} rows.`, "info");
  });

  // Select All
  selectAllCb.addEventListener("change", (e) => {
    const cbs = document.querySelectorAll(".row-cb");
    cbs.forEach((cb) => (cb.checked = e.target.checked));
  });

  // Startup: File-based polling (sendInfoToHTML is broken)
  let pollCount = 0;
  const pollInterval = setInterval(() => {
    pollCount++;

    // Request data from Python
    try {
      adsk.fusionSendData(
        "send",
        JSON.stringify({ action: "get_initial_data", data: "" })
      );
    } catch (e) {}

    // Poll the bridge file
    fetch("data_bridge.json?t=" + Date.now())
      .then((r) => r.json())
      .then((data) => {
        clearInterval(pollInterval);
        if (data.type === "init_all") {
          window.populatePresets(data.content.presets);
          window.updateTable(data.content.params);
          setStatus("Presets Loaded (File Bridge)!", "success");
        }
      })
      .catch((e) => {
        if (pollCount > 10) {
          clearInterval(pollInterval);
          setStatus("Failed to load presets.", "error");
        }
      });
  }, 500);

  // Console Input (Still creates individually)
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
      sendToFusion("create_param", input.value.trim());
      input.value = "";
    }
  });

  // Preset Selection: No Auto-Staging
  // LIVE PREVIEW: Selecting preset stages values in table for review
  presetSelect.addEventListener("change", () => {
    const selectedName = presetSelect.value;
    if (selectedName && GLOBAL_PRESETS[selectedName]) {
      const data = GLOBAL_PRESETS[selectedName];

      // Special Case: New Preset (Empty) -> CLEAR TABLE
      if (Object.keys(data).length === 0) {
        renderTable([]); // Clear
        setStatus("Table cleared. Ready for new input.", "info");
        return;
      }

      // Stage preset for preview (NO Fusion changes yet)
      stagePreset(data, selectedName);
      setStatus(`Preview: "${selectedName}" - Click Load to apply`, "info");
    }
  });

  // LOAD BUTTON: Apply staged changes to Fusion
  loadPresetBtn.addEventListener("click", () => {
    // Gather current table data (already staged from preview)
    const changes = gatherTableData();

    if (changes.length === 0) {
      setStatus("No parameters to load.", "error");
      return;
    }

    // Apply to Fusion
    sendToFusion("batch_update", changes);
    const presetName = presetSelect.value || "Manual Changes";

    // Save preset name to Fusion parameter for persistence
    if (presetSelect.value) {
      sendToFusion("set_current_preset", { name: presetName });
    }

    // Update current preset tracking
    updateCurrentPreset(presetName);

    setStatus(`Applied "${presetName}" to Fusion!`, "success");
  });

  // TABLE EDIT FEEDBACK (No auto-sync during preview mode)
  document.getElementById("param-table").addEventListener("change", (e) => {
    if (e.target.classList.contains("tbl-input")) {
      e.target.classList.add("modified"); // Visual feedback only
      updateCurrentPreset(null); // Clear current preset on manual edit
      setStatus("Modified - Click Load to apply changes", "info");
    }
  });

  // Refresh button removed - redundant with auto-sync

  // -------------------------------------------------------------------------
  // HELPER: Update Current Preset Display
  // -------------------------------------------------------------------------

  function updateCurrentPreset(presetName) {
    CURRENT_PRESET = presetName;
    const displayEl = document.getElementById("current-preset-name");
    if (displayEl) {
      displayEl.textContent = presetName || "None";
    }
  }

  // -------------------------------------------------------------------------
  // HELPER: Poll Bridge File
  // -------------------------------------------------------------------------

  function pollBridgeFile(maxAttempts = 10) {
    let attempts = 0;
    const pollInterval = setInterval(() => {
      attempts++;

      fetch("data_bridge.json?t=" + Date.now())
        .then((r) => r.json())
        .then((data) => {
          clearInterval(pollInterval);

          if (data.type === "init_all") {
            window.populatePresets(data.content.presets);
            window.updateTable(data.content.params);
            setStatus("Preset list refreshed!", "success");
          } else if (data.type === "notification") {
            setStatus(data.message, data.status);
          }
        })
        .catch((e) => {
          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            setStatus("Failed to refresh presets.", "error");
          }
        });
    }, 300); // Poll every 300ms
  }

  // -------------------------------------------------------------------------
  // HELPERS
  // -------------------------------------------------------------------------

  window.populatePresets = function (presetsDict) {
    GLOBAL_PRESETS = presetsDict;
    const count = Object.keys(presetsDict).length;

    presetSelect.innerHTML =
      '<option value="" disabled selected>Select a Preset... (' +
      count +
      ")</option>";

    Object.keys(presetsDict).forEach((k) => {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = k;
      presetSelect.appendChild(opt);
    });

    // Auto-select newly saved preset if exists
    if (LAST_SAVED_PRESET && presetsDict[LAST_SAVED_PRESET]) {
      presetSelect.value = LAST_SAVED_PRESET;
      LAST_SAVED_PRESET = null; // Clear after selection
    }

    setStatus(`Presets Loaded: ${count}`, "success");
  };

  window.updateTable = function (params) {
    GLOBAL_PARAMS = params; // Sync source of truth
    renderTable(params);
    updateSuggestions(params);
  };

  function updateSuggestions(params) {
    const datalist = document.getElementById("param-suggestions");
    datalist.innerHTML = "";
    params.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name + " = "; // Easy start for editing
      datalist.appendChild(opt);
    });
  }

  function renderTable(params) {
    const tbody = document.querySelector("#param-table tbody");
    tbody.innerHTML = "";

    if (params.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" style="text-align:center; color:#666;">No parameters found</td></tr>';
      return;
    }

    params.forEach((p) => {
      const tr = document.createElement("tr");

      // Editable Inputs for User Params
      if (p.isUser) {
        tr.innerHTML = `
            <td style="text-align:center;"><input type="checkbox" class="row-cb"></td>
                    <td><input type="text" class="tbl-input name" value="${
                      p.name
                    }" ${p.isUser ? "" : "disabled"}></td>
                    <td><input type="text" class="tbl-input expr" value="${
                      p.expression
                    }"></td>
                    <td style="font-size:11px; color:#aaa; padding-left:8px;">${
                      p.unit || ""
                    }</td>
                    <td><input type="text" class="tbl-input comment" value="${
                      p.comment
                    }"></td>
                `;
      } else {
        // Read-only for Model Params
        tr.style.opacity = "0.6";
        tr.innerHTML = `
            <td></td>
                    <td>${p.name}</td>
                    <td style="font-family:consolas">${p.expression}</td>
                    <td style="font-size:11px; color:#aaa;">${p.unit || ""}</td>
                    <td style="color:#888; font-style:italic;">${p.comment}</td>
                `;
      }
      tbody.appendChild(tr);
    });
  }

  function addNewRow() {
    const tbody = document.querySelector("#param-table tbody");
    const tr = document.createElement("tr");
    tr.classList.add("new-row");
    tr.innerHTML = `
        <td style="text-align:center;"><input type="checkbox" class="row-cb"></td>
        <td><input type="text" class="tbl-input name" value="new_param"></td>
        <td><input type="text" class="tbl-input expr" value="10mm"></td>
        <td style="font-size:11px; color:#aaa;">mm</td>
        <td><input type="text" class="tbl-input comment" value=""></td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);
    tr.querySelector(".name").select();
  }

  function stagePreset(presetData, presetName) {
    // Logic:
    // 1. Check if param exists in table -> Update input value
    // 2. If not -> Append new row at top

    const tbody = document.querySelector("#param-table tbody");

    Object.keys(presetData).forEach((key) => {
      const targetVal = presetData[key];

      // Find row by name input
      const inputs = Array.from(tbody.querySelectorAll("input.name"));
      const existingRowInput = inputs.find((i) => i.value === key);

      if (existingRowInput) {
        // Update Existing Row
        const row = existingRowInput.closest("tr");
        const exprInput = row.querySelector(".expr");
        if (exprInput) {
          exprInput.value = targetVal;
          highlightRow(row);
        }
      } else {
        // Create New Row (Staged)
        const tr = document.createElement("tr");
        tr.classList.add("new-row");
        tr.innerHTML = `
                    <td style="text-align:center;"><input type="checkbox" class="row-cb"></td>
                    <td><input type="text" class="tbl-input name" value="${key}"></td>
                    <td><input type="text" class="tbl-input expr" value="${targetVal}"></td>
                    <td style="font-size:11px; color:#aaa;">mm</td>
                    <td><input type="text" class="tbl-input comment" value="Preset: ${presetName}"></td>
                `;
        // Insert at top
        tbody.insertBefore(tr, tbody.firstChild);
        highlightRow(tr);
      }
    });
  }

  function highlightRow(row) {
    row.style.backgroundColor = "#383838";
    setTimeout(() => (row.style.backgroundColor = ""), 1000);
  }

  function gatherTableData() {
    const changes = [];
    const rows = document.querySelectorAll("#param-table tbody tr");

    rows.forEach((row) => {
      // Only gather rows with inputs (User Params)
      const nameInput = row.querySelector(".name");
      const exprInput = row.querySelector(".expr");
      const cmtInput = row.querySelector(".comment");

      if (nameInput && exprInput) {
        changes.push({
          name: nameInput.value.trim(),
          expression: exprInput.value.trim(),
          comment: cmtInput ? cmtInput.value.trim() : "",
        });
      }
    });
    return changes;
  }
});

// Bridge
function sendToFusion(action, data) {
  try {
    adsk.fusionSendData("send", JSON.stringify({ action, data }));
  } catch (e) {
    console.log("Fusion offline");
    setStatus("Send Error: Fusion Offline", "error"); // DEBUG
  }
}

function setStatus(msg, type = "info") {
  const el = document.getElementById("status-bar");
  el.textContent = msg;
  el.className = `status-bar ${type}`;
  if (type === "success") {
    setTimeout(() => {
      el.textContent = "Ready.";
      el.className = "status-bar";
    }, 3000);
  }
}

// Handler that Fusion recognizes
window.response = function (data) {
  // setStatus("JS: Signal Received!", "info"); // TRACE 1
  try {
    const statusEl = document.getElementById("status-bar");
    if (statusEl) statusEl.textContent = "Received data from Python!";

    // data comes in as a JSON string from Python
    const res = JSON.parse(data);
    // setStatus(`JS: Payload ${res.type}`, "info"); // TRACE 2

    if (res.type === "init_all") {
      // ATOMIC RELOAD
      window.populatePresets(res.content.presets);
      window.updateTable(res.content.params);

      // Restore current preset name
      const currentPreset = res.content.current_preset;

      if (currentPreset) {
        // 1. Force Text Update and Global Variable IMMEDIATELY
        const displayEl = document.getElementById("current-preset-name");
        if (displayEl) displayEl.textContent = currentPreset;
        if (window.CURRENT_PRESET !== undefined)
          window.CURRENT_PRESET = currentPreset;

        // 2. Try to sync dropdown (Delayed)
        setTimeout(() => {
          const dropdown = document.getElementById("preset-select");
          if (dropdown) {
            // Check if option exists
            let found = false;
            for (let i = 0; i < dropdown.options.length; i++) {
              if (dropdown.options[i].value === currentPreset) {
                found = true;
                break;
              }
            }

            // If not found, ADD IT so it can be selected
            if (!found) {
              const opt = document.createElement("option");
              opt.value = currentPreset;
              opt.textContent = currentPreset;
              dropdown.appendChild(opt);
            }

            dropdown.value = currentPreset;
          }
          setStatus(`Restored: "${currentPreset}"`, "success");
        }, 150);
      } else {
        setStatus("System Loaded (Atomic).", "success");
      }
    } else if (res.type === "init_presets") {
      window.populatePresets(res.content.presets);
    } else if (res.type === "update_table") {
      window.updateTable(res.content);
      setStatus("Table synced from Fusion.", "success");
    } else if (res.type === "notification") {
      setStatus(res.message, res.status);
    } else if (res.message) {
      setStatus(res.message, res.status || "info");
    }
  } catch (e) {
    setStatus("JS Error: " + e.message, "error");
  }
};

// Register the handler explicitly with Fusion
if (window.adsk && adsk.eventHandlers) {
  adsk.eventHandlers["response"] = window.response;
}

// Removed old handlers

// Improve "Live Sync" feel: Sync on Enter Key in inputs
document.getElementById("param-table").addEventListener("keydown", (e) => {
  if (e.target.classList.contains("tbl-input") && e.key === "Enter") {
    e.target.blur(); // Trigger 'change' event -> Syncs
  }
});
