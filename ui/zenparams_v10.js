// ZenParams v10.1 JS - Dark Mode & Smart Logic

// Handler that Fusion recognizes - MUST BE GLOBAL AND IMMEDIATE
window.response = function (dataWrapper) {
  try {
    const statusEl = document.getElementById("status-bar");

    // Fusion wraps data in {data: "..."} or passes it directly
    const jsonStr =
      dataWrapper && dataWrapper.data ? dataWrapper.data : dataWrapper;
    const res = JSON.parse(jsonStr);

    if (res.type === "init_all") {
      if (window.populatePresets) window.populatePresets(res.content.presets);
      if (window.updateTable) window.updateTable(res.content.params);

      // Restore current preset name (or set to New Design)
      window.restoreState(res.content.current_preset);

      // Legacy Detection Prompt
      if (res.content.legacy_params && !res.content.current_preset) {
        // Small delay to ensure UI renders first
        setTimeout(() => {
          if (
            confirm(
              "⚠️ Existing parameters detected!\n\nThis design has parameters but no ZenParams preset.\n\nDo you want to save them as a new Preset now?"
            )
          ) {
            document.getElementById("save-preset-btn").click();
          }
        }, 500);
      }
    } else if (res.type === "init_presets") {
      if (window.populatePresets) window.populatePresets(res.content.presets);
    } else if (res.type === "update_table") {
      if (window.updateTable) window.updateTable(res.content);
      if (statusEl) {
        statusEl.textContent = "Synced.";
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
  status.textContent = "v10.1 Active";

  // REQUEST INITIAL DATA FROM PYTHON
  // Using adsk.fusionSendData to ask Python for data
  function requestInitialData() {
    try {
      adsk.fusionSendData(
        "get_initial_data",
        JSON.stringify({ action: "get_initial_data" })
      );
      status.textContent = "Requesting data...";
    } catch (e) {
      status.textContent = "Fusion API not ready, retrying...";
      setTimeout(requestInitialData, 500);
    }
  }
  // Request data after short delay to ensure Fusion API is ready
  setTimeout(requestInitialData, 300);

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

    // 2. Prompt Name
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

    // 5. Poll for backend response (force immediate check)
    // The Watchdog will catch it anyway, but this is for instant feedback feel
    setTimeout(() => {
      // Force watchdog check soon
    }, 500);
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
      setStatus(`System presets are protected.`, "error");
      return;
    }
    // Protection: Check if it's a user preset (not just "current")
    // User presets have data in GLOBAL_PRESETS that's not from system
    const isUserPreset =
      GLOBAL_PRESETS[selectedName] &&
      !SYSTEM_PRESETS.includes(selectedName) &&
      selectedName !== "New Preset";
    if (!isUserPreset) {
      setStatus("Only saved custom presets can be deleted.", "error");
      return;
    }

    // Use simple confirm without special characters
    if (!confirm("Delete preset: " + selectedName + "?")) return;

    sendToFusion("delete_preset", { name: selectedName });

    // Clear current preset if it was deleted
    if (CURRENT_PRESET === selectedName) {
      updateCurrentPreset(null);
    }
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
    checked.forEach((cb) => cb.closest("tr").remove());
    setStatus(`Removed ${checked.length} rows.`, "info");
  });

  // Select All
  selectAllCb.addEventListener("change", (e) => {
    const cbs = document.querySelectorAll(".row-cb");
    cbs.forEach((cb) => (cb.checked = e.target.checked));
  });

  // -------------------------------------------------------------------------
  // WATCHDOG LOOP (Auto-Refresh Logic)
  // -------------------------------------------------------------------------

  let lastTimestamp = 0;

  const watchdog = setInterval(() => {
    // 1. Keep Alive (Optional, mostly to ensure Fusion doesn't sleep the script)
    // Removed to prevent UI lag. Passive polling only.
    /*
    try {
      adsk.fusionSendData(
        "send",
        JSON.stringify({ action: "check", data: "" })
      );
    } catch (e) {}
    */

    // 2. Poll the bridge file
    fetch("data_bridge.json?t=" + Date.now())
      .then((r) => r.json())
      .then((data) => {
        // Only update if timestamp is newer
        if (data.timestamp && data.timestamp > lastTimestamp) {
          lastTimestamp = data.timestamp;

          // Handle Payload
          if (data.type === "init_all") {
            window.populatePresets(data.content.presets);
            window.updateTable(data.content.params);
            window.restoreState(data.content.current_preset);
            setStatus("Refreshed", "success");
          } else if (data.type === "init_presets") {
            window.populatePresets(data.content.presets);
          } else if (data.type === "update_table") {
            window.updateTable(data.content.params);
          } else if (data.type === "notification") {
            setStatus(data.message, data.status);
          }
        }
      })
      .catch((e) => {
        // Silent fail (offline)
      });
  }, 1000); // 1 Second Interval

  // Console Input
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
      sendToFusion("create_param", input.value.trim());
      input.value = "";
    }
  });

  // Preset Selection
  presetSelect.addEventListener("change", () => {
    const selectedName = presetSelect.value;
    if (selectedName && GLOBAL_PRESETS[selectedName]) {
      const data = GLOBAL_PRESETS[selectedName];
      if (Object.keys(data).length === 0) {
        renderTable([]); // Clear for new
        return;
      }
      stagePreset(data, selectedName);
    }
  });

  // LOAD BUTTON
  loadPresetBtn.addEventListener("click", () => {
    const changes = gatherTableData();
    if (changes.length === 0) return;

    sendToFusion("batch_update", changes);
    const presetName = presetSelect.value || "Manual Changes";

    if (presetSelect.value) {
      sendToFusion("set_current_preset", { name: presetName });
    }
    updateCurrentPreset(presetName);
    setStatus(`Applied!`, "success");
  });

  // TABLE EDIT FEEDBACK
  document.getElementById("param-table").addEventListener("change", (e) => {
    if (e.target.classList.contains("tbl-input")) {
      e.target.classList.add("modified");
      updateCurrentPreset(null); // New Design state
    }
  });

  // -------------------------------------------------------------------------
  // HELPER: Restore State (Smart Logic)
  // -------------------------------------------------------------------------

  window.restoreState = function (currentPreset) {
    if (!currentPreset) {
      // v10: Show "New Design" instead of None
      updateCurrentPreset(null);
      return;
    }

    // 1. Force Text Update
    updateCurrentPreset(currentPreset);

    // 2. Try to sync dropdown (Delayed)
    setTimeout(() => {
      const dropdown = document.getElementById("preset-select");
      if (dropdown) {
        let found = false;
        for (let i = 0; i < dropdown.options.length; i++) {
          if (dropdown.options[i].value === currentPreset) {
            found = true;
            break;
          }
        }
        // If not found (e.g. deleted), Add it temporarily
        if (!found) {
          const opt = document.createElement("option");
          opt.value = currentPreset;
          opt.textContent = currentPreset;
          dropdown.appendChild(opt);
        }
        dropdown.value = currentPreset;
      }
    }, 100);
  };

  // -------------------------------------------------------------------------
  // HELPER: Update Current Preset Display (v10 Redesign)
  // -------------------------------------------------------------------------

  function updateCurrentPreset(presetName) {
    CURRENT_PRESET = presetName;
    const displayEl = document.getElementById("current-preset-name");
    if (displayEl) {
      if (presetName) {
        displayEl.textContent = presetName;
        displayEl.style.color = "#4ec9b0"; // Value is Green (Requested)
      } else {
        displayEl.textContent = "New Design";
        displayEl.style.color = "#4ec9b0";
      }
    }
  }

  // -------------------------------------------------------------------------
  // UI GENERATORS
  // -------------------------------------------------------------------------

  window.populatePresets = function (presetsDict) {
    GLOBAL_PRESETS = presetsDict;
    // v10: Clean Dropdown Text
    presetSelect.innerHTML =
      '<option value="" disabled selected>Load Preset...</option>';

    Object.keys(presetsDict).forEach((k) => {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = k;
      presetSelect.appendChild(opt);
    });

    if (LAST_SAVED_PRESET && presetsDict[LAST_SAVED_PRESET]) {
      presetSelect.value = LAST_SAVED_PRESET;
      LAST_SAVED_PRESET = null;
    }
  };

  window.updateTable = function (params) {
    GLOBAL_PARAMS = params;
    renderTable(params);
    updateSuggestions(params);
  };

  function updateSuggestions(params) {
    const datalist = document.getElementById("param-suggestions");
    datalist.innerHTML = "";
    params.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name + " = ";
      datalist.appendChild(opt);
    });
  }

  function renderTable(params) {
    const tbody = document.querySelector("#param-table tbody");
    tbody.innerHTML = "";

    if (params.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" style="text-align:center; color:#555; padding: 20px;">No parameters found in this design.</td></tr>';
      updateCurrentPreset(null); // Ensure status reflects empty state
      return;
    }

    params.forEach((p) => {
      const tr = document.createElement("tr");
      if (p.isUser) {
        tr.innerHTML = `
            <td style="text-align:center;"><input type="checkbox" class="row-cb"></td>
             <td><input type="text" class="tbl-input name" value="${
               p.name
             }"></td>
             <td><input type="text" class="tbl-input expr" value="${
               p.expression
             }"></td>
             <td style="font-size:11px; color:#666; padding-left:8px;">${
               p.unit || ""
             }</td>
             <td><input type="text" class="tbl-input comment" value="${
               p.comment
             }"></td>
        `;
      } else {
        tr.style.opacity = "0.7";
        tr.innerHTML = `
            <td></td>
            <td>${p.name}</td>
            <td style="font-family:consolas; color:#ce9178">${p.expression}</td>
            <td style="font-size:11px; color:#666;">${p.unit || ""}</td>
            <td style="color:#666; font-style:italic;">${p.comment}</td>
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
        <td style="font-size:11px; color:#666;">mm</td>
        <td><input type="text" class="tbl-input comment" value=""></td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);
    tr.querySelector(".name").select();
  }

  function stagePreset(presetData, presetName) {
    const tbody = document.querySelector("#param-table tbody");
    Object.keys(presetData).forEach((key) => {
      const targetVal = presetData[key];
      const inputs = Array.from(tbody.querySelectorAll("input.name"));
      const existingRowInput = inputs.find((i) => i.value === key);

      if (existingRowInput) {
        const row = existingRowInput.closest("tr");
        const exprInput = row.querySelector(".expr");
        if (exprInput) {
          exprInput.value = targetVal;
          exprInput.classList.add("modified");
        }
      } else {
        const tr = document.createElement("tr");
        tr.innerHTML = `
             <td style="text-align:center;"><input type="checkbox" class="row-cb"></td>
             <td><input type="text" class="tbl-input name" value="${key}"></td>
             <td><input type="text" class="tbl-input expr" value="${targetVal}"></td>
             <td style="font-size:11px; color:#666;">mm</td>
             <td><input type="text" class="tbl-input comment" value="Preview"></td>
        `;
        tbody.insertBefore(tr, tbody.firstChild);
      }
    });
  }

  function gatherTableData() {
    const changes = [];
    const rows = document.querySelectorAll("#param-table tbody tr");
    rows.forEach((row) => {
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

// Register
if (window.adsk && adsk.eventHandlers) {
  adsk.eventHandlers["response"] = window.response;
}
