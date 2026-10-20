/**
 * Trackside Visualizer — WebSocket Telemetry Streaming Engine.
 * Connects to simulator WebSocket broadcast, plots live track position,
 * updates sensor readouts, and records threshold alerts.
 */

window.TracksideStream = (function () {
  let ws = null;
  let reconnectTimer = null;
  let alertCount = 0;
  let lastReading = null;
  const MAX_ALERTS = 40;

  const trackPath = document.getElementById("track-path");
  const kartDot = document.getElementById("kart-dot");
  const kartPulse = document.getElementById("kart-pulse");
  const pathLength = trackPath ? trackPath.getTotalLength() : 0;

  const statusIndicator = document.getElementById("status-indicator");
  const statusText = document.getElementById("status-text");
  const wsUrlInput = document.getElementById("ws-url-input");
  const btnReconnect = document.getElementById("btn-reconnect");
  const btnClearLog = document.getElementById("btn-clear-log");

  const gValueEl = document.getElementById("g-value");
  const speedValueEl = document.getElementById("speed-value");
  const lapValueEl = document.getElementById("lap-value");
  const lapPillEl = document.getElementById("lap-pill");
  const zoneNameDisplay = document.getElementById("zone-name-display");
  const zoneSubEl = document.getElementById("zone-sub");
  const thresholdSubEl = document.getElementById("threshold-sub");
  const progressTextEl = document.getElementById("progress-text");
  const stageBadge = document.getElementById("stage-badge");
  const alertList = document.getElementById("alert-list");
  const emptyState = document.getElementById("empty-state");
  const alertCounter = document.getElementById("alert-counter");

  const segments = [
    document.getElementById("seg-0"),
    document.getElementById("seg-1"),
    document.getElementById("seg-2"),
    document.getElementById("seg-3"),
    document.getElementById("seg-4"),
  ];

  const zonePills = {
    hairpin: document.getElementById("zone-pill-hairpin"),
    straight1: document.getElementById("zone-pill-straight1"),
    sweeper: document.getElementById("zone-pill-sweeper"),
    straight2: document.getElementById("zone-pill-straight2"),
    chicane: document.getElementById("zone-pill-chicane"),
  };

  const canvas = document.getElementById("g-chart");
  const ctx = canvas ? canvas.getContext("2d") : null;

  function recordInterveneAlert(data) {
    if (!alertList) return;
    if (emptyState && emptyState.parentElement) emptyState.remove();

    alertCount++;
    if (alertCounter) alertCounter.textContent = `${alertCount} ALERT${alertCount === 1 ? "" : "S"}`;

    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0] + "." + Math.floor(now.getMilliseconds() / 100);
    const zoneSafe = data && data.zone ? String(data.zone) : "Turn";
    const lapStr = Number.isFinite(Number(data && data.lap)) ? String(data.lap) : "1";
    const gStr = Number.isFinite(Number(data && data.g_force)) ? Number(data.g_force).toFixed(2) : "--";
    const threshStr = Number.isFinite(Number(data && data.threshold)) ? Number(data.threshold).toFixed(2) : "1.15";

    const item = document.createElement("div");
    item.className = "alert-item mono";
    item.innerHTML = `
      <div class="alert-details">
        <span class="alert-title">⚠ INTERVENE: ${zoneSafe} Threshold Exceeded</span>
        <span class="alert-meta">Lap ${lapStr} · Force: ${gStr}g (Limit: ${threshStr}g) · ${timeStr}</span>
      </div>
      <span class="alert-badge">RED ALERT</span>
    `;

    alertList.insertBefore(item, alertList.firstChild);
    while (alertList.children.length > MAX_ALERTS) alertList.removeChild(alertList.lastChild);
  }

  function applyReading(data) {
    const g = typeof data.g_force === "number" ? data.g_force : 0.0;
    const speed = typeof data.speed_kmh === "number" ? data.speed_kmh : 0.0;
    const lap = data.lap || 1;
    const zone = data.zone || "Straight";
    const stage = (data.stage || "NOMINAL").toUpperCase();
    const progress = Math.max(
      0.0,
      Math.min(1.0, typeof data.track_progress === "number" ? data.track_progress : 0.0),
    );
    const threshold = data.threshold || 1.15;

    if (trackPath && kartDot && kartPulse && pathLength > 0) {
      const dist = progress * pathLength;
      const pt = trackPath.getPointAtLength(dist);

      kartDot.setAttribute("cx", pt.x);
      kartDot.setAttribute("cy", pt.y);
      kartPulse.setAttribute("cx", pt.x);
      kartPulse.setAttribute("cy", pt.y);

      let dotColor = "#33D17E";
      if (stage === "INTERVENE") dotColor = "#E5473C";
      else if (stage === "MONITORING") dotColor = "#F2A93B";

      kartDot.setAttribute("fill", dotColor);
      kartPulse.setAttribute("fill", dotColor);
    }

    if (gValueEl) gValueEl.textContent = g.toFixed(2);
    if (speedValueEl) speedValueEl.textContent = speed.toFixed(1);
    if (lapValueEl) lapValueEl.textContent = lap;
    if (lapPillEl) lapPillEl.textContent = `LAP ${lap.toString().padStart(2, "0")}`;
    if (zoneNameDisplay) zoneNameDisplay.textContent = zone;
    if (zoneSubEl) zoneSubEl.textContent = `Sector: ${zone}`;
    if (thresholdSubEl) thresholdSubEl.textContent = `Threshold: ${threshold.toFixed(2)} g`;
    if (progressTextEl) progressTextEl.textContent = `PROGRESS ${(progress * 100).toFixed(1)}%`;

    if (window.TracksideChart) {
      window.TracksideChart.updateSignalStrip(segments, stageBadge, stage);
      window.TracksideChart.updateZonePill(zonePills, zone);
      window.TracksideChart.gHistory.shift();
      window.TracksideChart.gHistory.push(g);
      window.TracksideChart.drawChart(canvas, ctx, threshold);
    }

    const shouldAlert = typeof shouldRecordAlert === "function"
      ? shouldRecordAlert(lastReading, data)
      : (stage === "INTERVENE");

    if (shouldAlert) {
      recordInterveneAlert(data);
    }
    lastReading = data;
  }

  function handleRunStart(eventData) {
    if (alertList) {
      alertList.innerHTML = '<div id="empty-state" class="empty-alerts mono">No Intervene Alerts Recorded Yet</div>';
    }
    alertCount = 0;
    if (alertCounter) alertCounter.textContent = "0 ALERTS";
    lastReading = null;

    if (lapValueEl) lapValueEl.textContent = "1";
    if (lapPillEl) lapPillEl.textContent = "LAP 01";

    const lapTotalEl = document.getElementById("lap-total");
    if (lapTotalEl) {
      if (eventData && eventData.mode === "continuous") {
        lapTotalEl.textContent = "";
      } else if (eventData && eventData.total_laps) {
        lapTotalEl.textContent = ` / ${eventData.total_laps}`;
      } else {
        lapTotalEl.textContent = "";
      }
    }

    if (progressTextEl) progressTextEl.textContent = "PROGRESS 0.0%";
    const modeEl = document.getElementById("session-mode-sub");
    if (modeEl) modeEl.textContent = "Session Mode: Active";
  }

  function handleRunEnd() {
    if (progressTextEl) progressTextEl.textContent = "PROGRESS 100.0%";
    const modeEl = document.getElementById("session-mode-sub");
    if (modeEl) modeEl.textContent = "Session Mode: Finished";
    if (statusText) statusText.textContent = "RUN FINISHED · SIMULATION COMPLETE";

    if (trackPath && kartDot && kartPulse && pathLength > 0) {
      const pt = trackPath.getPointAtLength(pathLength);
      kartDot.setAttribute("cx", pt.x);
      kartDot.setAttribute("cy", pt.y);
      kartPulse.setAttribute("cx", pt.x);
      kartPulse.setAttribute("cy", pt.y);
    }
  }

  function connectWebSocket() {
    const url = (wsUrlInput && wsUrlInput.value.trim()) || "ws://127.0.0.1:8765";

    if (ws) {
      try {
        ws.close();
      } catch (e) {}
    }

    if (statusIndicator) statusIndicator.className = "status-dot connecting";
    if (statusText) statusText.textContent = `CONNECTING TO ${url}...`;

    try {
      ws = new WebSocket(url);
    } catch (err) {
      scheduleReconnect();
      return;
    }

    ws.onopen = function () {
      if (statusIndicator) statusIndicator.className = "status-dot connected";
      if (statusText) {
        statusText.textContent = `LIVE TELEMETRY STREAM ACTIVE (${url.replace("ws://", "")})`;
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    ws.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "connection_ack") {
          console.log("[Trackside WS Handshake]", data.message);
          return;
        }
        if (data.type === "run_start") {
          handleRunStart(data);
          return;
        }
        if (data.type === "run_end") {
          handleRunEnd();
          return;
        }
        applyReading(data);
      } catch (e) {
        console.error("[Trackside WS Parse Error]", e);
      }
    };

    ws.onclose = function () {
      if (statusIndicator) statusIndicator.className = "status-dot";
      if (statusText) statusText.textContent = "DISCONNECTED · RECONNECTING IN 2s...";
      scheduleReconnect();
    };

    ws.onerror = function () {
      if (statusIndicator) statusIndicator.className = "status-dot";
      if (statusText) statusText.textContent = "STREAM OFFLINE · CHECK SIMULATOR SCRIPT";
    };
  }

  function scheduleReconnect() {
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(function () {
        reconnectTimer = null;
        connectWebSocket();
      }, 2000);
    }
  }

  if (btnReconnect) {
    btnReconnect.addEventListener("click", function () {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      connectWebSocket();
    });
  }

  if (btnClearLog) {
    btnClearLog.addEventListener("click", function () {
      if (alertList) {
        alertList.innerHTML =
          '<div id="empty-state" class="empty-alerts mono">No Intervene Alerts Recorded Yet</div>';
      }
      alertCount = 0;
      lastReading = null;
      if (alertCounter) alertCounter.textContent = "0 ALERTS";
    });
  }

  return {
    connectWebSocket,
    zonePills,
    canvas,
    ctx,
  };
})();
