// ZenParams v11 JS

// Handler that Fusion recognizes - MUST BE GLOBAL AND IMMEDIATE
window.response = function (dataWrapper) {
  try {
    const statusEl = document.getElementById("status-bar");

    // DEBUG: Log what we receive
    console.log(
      "[ZenParams JS] response called with:",
      typeof dataWrapper,
      dataWrapper
    );
    if (statusEl) statusEl.textContent = "Data received...";

    // Fusion wraps data in {data: "..."} or passes it directly
    let jsonStr = dataWrapper;
    if (dataWrapper && typeof dataWrapper === "object" && dataWrapper.data) {
      jsonStr = dataWrapper.data;
    }

    console.log("[ZenParams JS] jsonStr:", jsonStr);
    const res = JSON.parse(jsonStr);
    console.log("[ZenParams JS] Parsed:", res.type, res);

    if (res.type === "init_all") {
      console.log("[ZenParams JS] Got init_all, presets:", res.content.presets);
      if (window.populatePresets) {
        window.populatePresets(res.content.presets);
        console.log("[ZenParams JS] populatePresets called");
      } else {
        console.log("[ZenParams JS] ERROR: populatePresets not defined!");
        if (statusEl) statusEl.textContent = "Error: UI not ready";
      }
      if (window.updateTable) window.updateTable(res.content.params);
      if (window.restoreState) window.restoreState(res.content.current_preset);
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
    console.log("[ZenParams JS] ERROR:", e);
    const statusEl = document.getElementById("status-bar");
    if (statusEl) {
      statusEl.textContent = "JS Error: " + e.message;
      statusEl.className = "status-bar error";
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("status-bar");

  // IMMEDIATE LOAD PROOF
  status.textContent = "v11 Active";

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
  const savePresetBtn = document.getElementById("save-preset-btn");
  const createNewBtn = document.getElementById("create-new-btn");

  let GLOBAL_PRESETS = {};
  let GLOBAL_PARAMS = [];
  let LAST_SAVED_PRESET = null; // Track last saved preset to auto-select
  let CURRENT_PRESET = null; // Track currently loaded preset
  let CREATING_PRESET_NAME = null; // Track if we're in creation mode

  // SYSTEM PRESETS (Hardcoded Names to Protect)
  const SYSTEM_PRESETS = [
    "3D Print (Tight Fit)",
    "3D Print (Balanced)",
    "3D Print (Loose Fit)",
  ];

  // CREATE NEW PRESET WIZARD
  createNewBtn.addEventListener("click", () => {
    const name = prompt("Enter a name for your new preset:", "my_preset");
    if (!name) return; // Cancelled

    // Check if name conflicts with system presets
    if (SYSTEM_PRESETS.includes(name)) {
      setStatus("Cannot use system preset names.", "error");
      return;
    }

    // Enter creation mode
    CREATING_PRESET_NAME = name;
    renderTable([]); // Clear the table
    addNewRow(); // Add one starter row
    updateCurrentPreset("Creating: " + name);
    setStatus("Add your parameters, then click Save Template.", "info");
  });

  // Add Row Method
  addRowBtn.addEventListener("click", () => {
    addNewRow();
    if (!CREATING_PRESET_NAME) {
      updateCurrentPreset(null); // Clear current preset on manual add (unless creating)
    }
  });

  // Save Template Method
  savePresetBtn.addEventListener("click", () => {
    // 1. Gather Data - ONLY USER PARAMS (not model params)
    const allData = gatherTableData();
    const userParams = allData.filter((item) => item.isUser === true);

    if (userParams.length === 0) {
      setStatus("No user parameters to save. Add some first.", "error");
      return;
    }

    // 2. Get Name (use CREATING_PRESET_NAME if set, otherwise prompt)
    let name = CREATING_PRESET_NAME;
    if (!name) {
      name = prompt("Name your Custom Preset:", "new_preset_name");
    }
    if (!name) return; // Cancelled

    // Protection: Don't allow system preset names (silent)
    if (SYSTEM_PRESETS.includes(name)) {
      setStatus(
        "Cannot use system preset names. Choose a different name.",
        "error"
      );
      return;
    }

    // 3. Convert List to Dict for Storage (USER PARAMS ONLY)
    const paramsDict = {};
    userParams.forEach((item) => {
      paramsDict[item.name] = item.expression;
    });

    // 4. Send to Backend
    LAST_SAVED_PRESET = name; // Store for auto-selection after backend confirms
    CREATING_PRESET_NAME = null; // Clear creation mode
    sendToFusion("save_preset", {
      name: name,
      params: paramsDict,
    });

    // 5. Immediately update UI to reflect new preset
    updateCurrentPreset(name);
    setStatus(`Saved '${name}'! Refreshing...`, "success");
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

    // Reset to New Preset state
    updateCurrentPreset(null);
    presetSelect.value = "New Preset";
    renderTable([]); // Clear the table
    setStatus("Preset deleted. Select a new preset to load.", "success");
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

  // TAB KEY NAVIGATION - Create new row when tabbing from comment field
  document.getElementById("param-table").addEventListener("keydown", (e) => {
    if (e.key === "Tab" && !e.shiftKey) {
      const target = e.target;
      // Check if we're in the comment field (last editable field in row)
      if (target.classList.contains("comment")) {
        const row = target.closest("tr");
        const allRows = Array.from(
          document.querySelectorAll("#param-table tbody tr")
        );
        const isLastRow = allRows.indexOf(row) === allRows.length - 1;

        // If this is the last row, create a new one
        if (isLastRow) {
          e.preventDefault();
          addNewRow();
          // Focus on the name field of the new row
          const newRow = document.querySelector(
            "#param-table tbody tr:first-child"
          );
          if (newRow) {
            const nameInput = newRow.querySelector(".name");
            if (nameInput) nameInput.focus();
          }
        }
      }
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
  };

  function renderTable(params) {
    const tbody = document.querySelector("#param-table tbody");
    tbody.innerHTML = "";

    if (params.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" style="text-align:center; color:#555; padding: 20px;">No parameters. Click "+ Add Parameter" to start.</td></tr>';
      return;
    }

    params.forEach((p) => {
      const tr = document.createElement("tr");
      if (p.isUser) {
        tr.dataset.user = "true";
        tr.innerHTML = `
             <td><input type="text" class="tbl-input name" value="${
               p.name
             }"></td>
             <td><input type="text" class="tbl-input expr" value="${
               p.expression
             }"></td>
             <td style="font-size:11px; color:#666;">${p.unit || ""}</td>
             <td><input type="text" class="tbl-input comment" value="${
               p.comment
             }"></td>
             <td><button class="row-delete" title="Delete row">×</button></td>
        `;
      } else {
        tr.classList.add("model-param");
        tr.innerHTML = `
            <td>${p.name}</td>
            <td style="font-family:consolas; color:#ce9178">${p.expression}</td>
            <td style="font-size:11px; color:#666;">${p.unit || ""}</td>
            <td style="color:#666; font-style:italic;">${p.comment}</td>
            <td></td>
        `;
      }
      tbody.appendChild(tr);
    });

    // Attach delete handlers
    tbody.querySelectorAll(".row-delete").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.target.closest("tr").remove();
        setStatus("Row removed.", "info");
      });
    });
  }

  function addNewRow() {
    const tbody = document.querySelector("#param-table tbody");
    // Remove "no params" message if present
    const emptyMsg = tbody.querySelector("td[colspan]");
    if (emptyMsg) emptyMsg.closest("tr").remove();

    const tr = document.createElement("tr");
    tr.classList.add("new-row");
    tr.dataset.user = "true";
    tr.innerHTML = `
        <td><input type="text" class="tbl-input name" value="new_param"></td>
        <td><input type="text" class="tbl-input expr" value="10mm"></td>
        <td style="font-size:11px; color:#666;">mm</td>
        <td><input type="text" class="tbl-input comment" value=""></td>
        <td><button class="row-delete" title="Delete row">×</button></td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);
    tr.querySelector(".name").select();

    // Attach delete handler
    tr.querySelector(".row-delete").addEventListener("click", (e) => {
      e.target.closest("tr").remove();
      setStatus("Row removed.", "info");
    });
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
          isUser: row.dataset.user === "true", // Include user flag for filtering
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
