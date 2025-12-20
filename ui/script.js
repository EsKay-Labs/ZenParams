// Phase 4: Editable Table & Batch Sync
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("console-input");
  const status = document.getElementById("status-bar");
  const presetSelect = document.getElementById("preset-select");
  const applyBtn = document.getElementById("apply-preset");
  const refreshBtn = document.getElementById("refresh-btn");
  const addRowBtn = document.getElementById("add-row-btn");
  const delRowBtn = document.getElementById("del-row-btn");
  const savePresetBtn = document.getElementById("save-preset-btn");
  const selectAllCb = document.getElementById("select-all");

  let GLOBAL_PRESETS = {};
  let GLOBAL_PARAMS = [];

  // Add Row Method
  addRowBtn.addEventListener("click", () => {
    addNewRow();
  });

  // Save Template Method
  savePresetBtn.addEventListener("click", () => {
    // 1. Gather Data
    const data = gatherTableData();
    if (data.length === 0) {
      setStatus("Table is empty. Add parameters first.", "error");
      return;
    }

    // 2. Prompt Name
    const name = prompt("Name your Custom Template:");
    if (!name) return; // Cancelled

    // 3. Convert List to Dict for Storage
    const paramsDict = {};
    data.forEach((item) => {
      paramsDict[item.name] = item.expression;
    });

    // 4. Send to Backend
    sendToFusion("save_preset", {
      name: name,
      params: paramsDict,
    });
  });

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

  // Startup: Robust connection attempt
  let attempts = 0;
  const initInterval = setInterval(() => {
    attempts++;
    try {
      adsk.fusionSendData(
        "send",
        JSON.stringify({ action: "check", data: "" })
      );
      clearInterval(initInterval);
      console.log("Fusion connected.");
      sendToFusion("get_initial_data", "");
    } catch (e) {
      if (attempts > 5) clearInterval(initInterval);
    }
  }, 500);

  // Console Input (Still creates individually)
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
      sendToFusion("create_param", input.value.trim());
      input.value = "";
    }
  });

  // Preset Selection: STAGE changes locally
  presetSelect.addEventListener("change", () => {
    const selectedName = presetSelect.value;
    if (selectedName && GLOBAL_PRESETS[selectedName]) {
      stagePreset(GLOBAL_PRESETS[selectedName], selectedName);
      setStatus(`Staged "${selectedName}". Review table above.`, "info");
    }
  });

  // Apply Button: COMMIT changes to Fusion
  applyBtn.addEventListener("click", () => {
    const changes = gatherTableData();
    if (changes.length > 0) {
      sendToFusion("batch_update", changes);
      setStatus("Sending to Fusion...", "info");
    } else {
      setStatus("No parameters to update.", "error");
    }
  });

  refreshBtn.addEventListener("click", () => {
    sendToFusion("refresh", "");
  });

  // -------------------------------------------------------------------------
  // HELPERS
  // -------------------------------------------------------------------------

  window.populatePresets = function (presetsDict) {
    GLOBAL_PRESETS = presetsDict;
    presetSelect.innerHTML =
      '<option value="" disabled selected>Select a Preset...</option>';
    Object.keys(presetsDict).forEach((k) => {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = k;
      presetSelect.appendChild(opt);
    });
  };

  window.updateTable = function (params) {
    GLOBAL_PARAMS = params; // Sync source of truth
    renderTable(params);
  };

  function renderTable(params) {
    const tbody = document.querySelector("#param-table tbody");
    tbody.innerHTML = "";

    if (params.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" style="text-align:center; color:#666;">No parameters found</td></tr>';
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

window.fusionJavaScriptHandler = {
  handle: function (action, data) {
    try {
      if (action === "response") {
        const res = JSON.parse(data);
        if (res.type === "init_presets")
          window.populatePresets(res.content.presets);
        else if (res.type === "update_table") window.updateTable(res.content);
        else setStatus(res.message, res.status);
      }
    } catch (e) {
      console.error(e);
    }
    return "OK";
  },
};
