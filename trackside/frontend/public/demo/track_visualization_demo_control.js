/**
 * Trackside Visualizer — Demo Process Control Engine.
 * Manages simulator process start/stop, status polling, and CSRF token handling.
 */

(function () {
  const inputLaps = document.getElementById("input-laps");
  const chkContinuous = document.getElementById("chk-continuous");
  const btnStartDemo = document.getElementById("btn-start-demo");
  const btnStopDemo = document.getElementById("btn-stop-demo");
  const demoStatusText = document.getElementById("demo-status-text");
  const demoOutputLines = document.getElementById("demo-output-lines");
  const demoActionButtons = document.getElementById("demo-action-buttons");

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
    if (window.TracksideLimits) {
      window.TracksideLimits.applyRanges(data);
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
      if (window.TracksideLimits) {
        for (const corner of ["Hairpin", "Sweeper", "Chicane"]) {
          if (!window.TracksideLimits.validateCorner(corner)) {
            allValid = false;
          }
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

      const cachedRanges = window.TracksideLimits ? window.TracksideLimits.getCachedRanges() : null;
      const cornerInputs = window.TracksideLimits ? window.TracksideLimits.cornerInputs : null;

      if (cachedRanges && cornerInputs) {
        const limitsObj = {};
        let hasDiff = false;
        for (const corner of ["Hairpin", "Sweeper", "Chicane"]) {
          const val = parseFloat(cornerInputs[corner] ? cornerInputs[corner].value : "0");
          const def = cachedRanges[corner].default;
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
