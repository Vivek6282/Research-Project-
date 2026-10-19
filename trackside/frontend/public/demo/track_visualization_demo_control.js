/**
 * Trackside Visualizer — Demo Process Control Engine.
 * Manages simulator process start/stop, status polling, and corner threshold limits.
 */

(function () {
  const inputLaps = document.getElementById("input-laps");
  const chkContinuous = document.getElementById("chk-continuous");
  const btnStartDemo = document.getElementById("btn-start-demo");
  const btnStopDemo = document.getElementById("btn-stop-demo");
  const demoStatusText = document.getElementById("demo-status-text");
  const demoOutputLines = document.getElementById("demo-output-lines");
  const demoActionButtons = document.getElementById("demo-action-buttons");

  const selectPreset = document.getElementById("select-preset");
  const btnResetLimits = document.getElementById("btn-reset-limits");
  const limitsInForceContainer = document.getElementById("limits-in-force-container");
  const limitsInForceText = document.getElementById("limits-in-force-text");
  const limitsSyncedNote = document.getElementById("limits-synced-note");

  const cornerInputs = {
    Hairpin: document.getElementById("input-limit-hairpin"),
    Sweeper: document.getElementById("input-limit-sweeper"),
    Chicane: document.getElementById("input-limit-chicane"),
  };

  const cornerRanges = {
    Hairpin: document.getElementById("range-limit-hairpin"),
    Sweeper: document.getElementById("range-limit-sweeper"),
    Chicane: document.getElementById("range-limit-chicane"),
  };

  const cornerErrors = {
    Hairpin: document.getElementById("err-limit-hairpin"),
    Sweeper: document.getElementById("err-limit-sweeper"),
    Chicane: document.getElementById("err-limit-chicane"),
  };

  let cachedLimitRanges = null;
  let limitsInitialized = false;

  function clearCornerError(corner) {
    const errEl = cornerErrors[corner];
    const inputEl = cornerInputs[corner];
    if (errEl) {
      errEl.textContent = "";
      errEl.style.display = "none";
    }
    if (inputEl) {
      inputEl.style.borderColor = "var(--line)";
    }
  }

  function validateCorner(corner) {
    if (!cachedLimitRanges || !cachedLimitRanges[corner]) return true;
    const r = cachedLimitRanges[corner];
    const inputEl = cornerInputs[corner];
    const errEl = cornerErrors[corner];
    if (!inputEl) return true;
    const rawVal = inputEl.value.trim();

    if (!rawVal || isNaN(rawVal)) {
      if (errEl) {
        errEl.textContent = "Must be a valid number";
        errEl.style.display = "block";
      }
      inputEl.style.borderColor = "var(--stage-intervene)";
      return false;
    }

    const val = parseFloat(rawVal);
    const parts = rawVal.split(".");
    if (parts.length > 1 && parts[1].length > 2) {
      if (errEl) {
        errEl.textContent = "At most 2 decimals allowed";
        errEl.style.display = "block";
      }
      inputEl.style.borderColor = "var(--stage-intervene)";
      return false;
    }

    if (val < r.min || val > r.max) {
      if (errEl) {
        errEl.textContent = `Allowed: ${r.min.toFixed(2)} – ${r.max.toFixed(2)} g`;
        errEl.style.display = "block";
      }
      inputEl.style.borderColor = "var(--stage-intervene)";
      return false;
    }

    clearCornerError(corner);
    return true;
  }

  ["Hairpin", "Sweeper", "Chicane"].forEach((corner) => {
    if (cornerInputs[corner]) {
      cornerInputs[corner].addEventListener("input", () => validateCorner(corner));
    }
  });

  if (selectPreset) {
    selectPreset.addEventListener("change", function () {
      if (!cachedLimitRanges) return;
      const mode = selectPreset.value;
      if (mode === "defaults") {
        for (const [corner, r] of Object.entries(cachedLimitRanges)) {
          if (cornerInputs[corner]) {
            cornerInputs[corner].value = r.default.toFixed(2);
            validateCorner(corner);
          }
        }
      } else if (mode === "cautious") {
        for (const [corner, r] of Object.entries(cachedLimitRanges)) {
          const cautiousVal = Math.max(1.0, Number((r.default * 0.85).toFixed(2)));
          if (cornerInputs[corner]) {
            cornerInputs[corner].value = cautiousVal.toFixed(2);
            validateCorner(corner);
          }
        }
      }
    });
  }

  if (btnResetLimits) {
    btnResetLimits.addEventListener("click", function () {
      if (!cachedLimitRanges) return;
      if (selectPreset) selectPreset.value = "";
      for (const [corner, r] of Object.entries(cachedLimitRanges)) {
        if (cornerInputs[corner]) {
          cornerInputs[corner].value = r.default.toFixed(2);
          clearCornerError(corner);
        }
      }
    });
  }

  let csrfTokenCached = null;

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  async function ensureCsrfToken() {
    if (!csrfTokenCached) {
      try {
        await fetch("/api/auth/csrf/", { credentials: "include" });
      } catch (e) {
        console.warn("[Demo Control] Could not fetch CSRF token:", e);
      }
      csrfTokenCached = getCookie("csrftoken");
    }
    return csrfTokenCached || getCookie("csrftoken") || "";
  }

  function updateDemoStatusUI(data) {
    if (data.limit_ranges) {
      cachedLimitRanges = data.limit_ranges;
      for (const [corner, r] of Object.entries(cachedLimitRanges)) {
        if (cornerRanges[corner]) {
          cornerRanges[corner].textContent = `${r.min.toFixed(2)} – ${r.max.toFixed(2)} g`;
        }
        if (cornerInputs[corner]) {
          cornerInputs[corner].min = r.min;
          cornerInputs[corner].max = r.max;
          if (!limitsInitialized) {
            cornerInputs[corner].value = r.default.toFixed(2);
          }
        }
      }
      limitsInitialized = true;
    }

    const isRunning = !!data.running;
    for (const corner of ["Hairpin", "Sweeper", "Chicane"]) {
      if (cornerInputs[corner]) cornerInputs[corner].disabled = isRunning;
    }
    if (selectPreset) selectPreset.disabled = isRunning;
    if (btnResetLimits) btnResetLimits.disabled = isRunning;

    if (data.limits && limitsInForceContainer && limitsInForceText) {
      limitsInForceContainer.style.display = "flex";
      const h = data.limits.Hairpin !== undefined ? data.limits.Hairpin.toFixed(2) : "--";
      const s = data.limits.Sweeper !== undefined ? data.limits.Sweeper.toFixed(2) : "--";
      const c = data.limits.Chicane !== undefined ? data.limits.Chicane.toFixed(2) : "--";
      limitsInForceText.textContent = `Limits in force: Hairpin ${h} / Sweeper ${s} / Chicane ${c}`;

      if (limitsSyncedNote) {
        if (data.limits_synced === true) {
          limitsSyncedNote.textContent = "Dashboards use the same limits.";
          limitsSyncedNote.style.color = "var(--stage-nominal)";
          limitsSyncedNote.style.display = "block";
        } else if (data.limits_synced === false && data.limits_note) {
          limitsSyncedNote.textContent = data.limits_note;
          limitsSyncedNote.style.color = "var(--stage-monitoring)";
          limitsSyncedNote.style.display = "block";
        } else {
          limitsSyncedNote.textContent = "";
          limitsSyncedNote.style.display = "none";
        }
      }

      const zp = window.TracksideStream ? window.TracksideStream.zonePills : null;
      if (zp) {
        if (zp.hairpin) zp.hairpin.textContent = `HAIRPIN (${h}g)`;
        if (zp.sweeper) zp.sweeper.textContent = `SWEEPER (${s}g)`;
        if (zp.chicane) zp.chicane.textContent = `CHICANE (${c}g)`;
      }
    }

    if (data.running) {
      if (btnStartDemo) btnStartDemo.disabled = true;
      if (btnStopDemo) btnStopDemo.disabled = false;

      if (demoStatusText) {
        if (data.bridge_connected === true) {
          demoStatusText.textContent = data.port_hint
            ? `Running, bridge connected (${data.port_hint})`
            : "Running, bridge connected";
          demoStatusText.style.color = "var(--stage-nominal)";
        } else if (data.bridge_connected === false) {
          demoStatusText.textContent =
            "Running, but the bridge is NOT connected: close the Arduino Serial Monitor and check SERIAL_PORT in trackside/demo/.env";
          demoStatusText.style.color = "var(--stage-monitoring)";
        } else {
          demoStatusText.textContent = "Running, bridge connected";
          demoStatusText.style.color = "var(--stage-nominal)";
        }
      }
    } else {
      if (btnStartDemo) btnStartDemo.disabled = false;
      if (btnStopDemo) btnStopDemo.disabled = true;

      if (demoStatusText) {
        if (data.error) {
          demoStatusText.textContent = data.error;
          demoStatusText.style.color = "var(--stage-intervene)";
        } else if (data.exit_code === 0 && data.mode === "laps" && data.laps) {
          demoStatusText.textContent = `Finished ${data.laps} laps`;
          demoStatusText.style.color = "var(--accent-blue)";
        } else {
          demoStatusText.textContent = "Stopped";
          demoStatusText.style.color = "var(--text-muted)";
        }
      }
    }

    if (demoOutputLines) {
      if (data.last_lines && Array.isArray(data.last_lines) && data.last_lines.length > 0) {
        demoOutputLines.textContent = data.last_lines.slice(-6).join("\n");
      } else {
        demoOutputLines.textContent = "(No process output yet)";
      }
    }
  }

  async function pollDemoStatus() {
    try {
      const res = await fetch("/api/demo/simulator/status/", { credentials: "include" });

      if (res.status === 200) {
        if (demoActionButtons) demoActionButtons.style.display = "flex";
        const data = await res.json();
        updateDemoStatusUI(data);
      } else if (res.status === 404) {
        if (demoActionButtons) demoActionButtons.style.display = "none";
        if (demoStatusText) {
          demoStatusText.textContent =
            "Demo control is switched off on this server (DEMO_TOOLS_ENABLED).";
          demoStatusText.style.color = "var(--text-muted)";
        }
      } else if (res.status === 401 || res.status === 403) {
        if (demoActionButtons) demoActionButtons.style.display = "none";
        if (demoStatusText) {
          demoStatusText.textContent = "Log in as a Coach in this browser, then reload.";
          demoStatusText.style.color = "var(--stage-monitoring)";
        }
      } else {
        if (demoStatusText) {
          demoStatusText.textContent = `Server error (${res.status})`;
          demoStatusText.style.color = "var(--stage-intervene)";
        }
      }
    } catch (err) {
      if (demoActionButtons) demoActionButtons.style.display = "none";
      if (demoStatusText) {
        demoStatusText.textContent =
          "Open this page from Coach Settings (http://localhost:5173/demo/track_visualization.html) to use Start/Stop.";
        demoStatusText.style.color = "var(--stage-monitoring)";
      }
    }
  }

  if (chkContinuous && inputLaps) {
    chkContinuous.addEventListener("change", function () {
      inputLaps.disabled = chkContinuous.checked;
    });
  }

  if (btnStartDemo) {
    btnStartDemo.addEventListener("click", async function () {
      btnStartDemo.disabled = true;

      let allValid = true;
      for (const corner of ["Hairpin", "Sweeper", "Chicane"]) {
        if (!validateCorner(corner)) {
          allValid = false;
        }
      }
      if (!allValid) {
        btnStartDemo.disabled = false;
        return;
      }

      const isContinuous = chkContinuous ? chkContinuous.checked : false;
      let payload = {};

      if (isContinuous) {
        payload = { mode: "continuous" };
      } else {
        const lapsVal = parseInt(inputLaps ? inputLaps.value : "3", 10);
        if (isNaN(lapsVal) || lapsVal < 1 || lapsVal > 20) {
          alert("Laps must be an integer between 1 and 20.");
          btnStartDemo.disabled = false;
          return;
        }
        payload = { mode: "laps", laps: lapsVal };
      }

      if (cachedLimitRanges) {
        const limitsObj = {};
        let hasDiff = false;
        for (const corner of ["Hairpin", "Sweeper", "Chicane"]) {
          const val = parseFloat(cornerInputs[corner] ? cornerInputs[corner].value : "0");
          const def = cachedLimitRanges[corner].default;
          if (Math.abs(val - def) > 0.001) {
            hasDiff = true;
          }
          limitsObj[corner] = Number(val.toFixed(2));
        }
        if (hasDiff) {
          payload.limits = limitsObj;
        }
      }

      try {
        const token = await ensureCsrfToken();
        const res = await fetch("/api/demo/simulator/start/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
          },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 200) {
          const resData = await res.json().catch(() => ({}));
          if (demoStatusText) {
            demoStatusText.textContent = "Starting simulator...";
            demoStatusText.style.color = "var(--accent-blue)";
          }
          if (resData.limits) {
            updateDemoStatusUI({
              running: true,
              limits: resData.limits,
              limits_synced: resData.limits_synced,
              limits_note: resData.limits_note,
            });
          }
          setTimeout(pollDemoStatus, 400);
        } else {
          const errData = await res.json().catch(() => ({}));
          if (demoStatusText) {
            demoStatusText.textContent =
              errData.error || `Error starting simulator (${res.status})`;
            demoStatusText.style.color = "var(--stage-intervene)";
          }
          pollDemoStatus();
        }
      } catch (err) {
        if (demoStatusText) {
          demoStatusText.textContent = `Network error starting simulator: ${err.message}`;
          demoStatusText.style.color = "var(--stage-intervene)";
        }
        pollDemoStatus();
      }
    });
  }

  if (btnStopDemo) {
    btnStopDemo.addEventListener("click", async function () {
      btnStopDemo.disabled = true;

      try {
        const token = await ensureCsrfToken();
        const res = await fetch("/api/demo/simulator/stop/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
          },
          credentials: "include",
        });

        if (res.status === 200) {
          if (demoStatusText) {
            demoStatusText.textContent = "Stopping simulator...";
            demoStatusText.style.color = "var(--text-muted)";
          }
          setTimeout(pollDemoStatus, 400);
        } else {
          pollDemoStatus();
        }
      } catch (err) {
        if (demoStatusText) {
          demoStatusText.textContent = `Network error stopping simulator: ${err.message}`;
          demoStatusText.style.color = "var(--stage-intervene)";
        }
        pollDemoStatus();
      }
    });
  }

  // Initializations
  if (window.TracksideChart && window.TracksideStream) {
    window.TracksideChart.drawChart(
      window.TracksideStream.canvas,
      window.TracksideStream.ctx,
      1.15,
    );
    window.TracksideStream.connectWebSocket();
  }

  pollDemoStatus();
  setInterval(pollDemoStatus, 2000);
})();
