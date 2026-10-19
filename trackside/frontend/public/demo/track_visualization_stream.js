/**
 * Trackside Visualizer — WebSocket Telemetry Streaming Engine.
 * Connects to simulator WebSocket broadcast, plots live track position,
 * updates sensor readouts, and records threshold alerts.
 */

window.TracksideStream = (function () {
  let ws = null;
  let reconnectTimer = null;
  let alertCount = 0;
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
    if (emptyState && emptyState.parentElement) {
      emptyState.remove();
    }

    alertCount++;
    if (alertCounter) {
      alertCounter.textContent = `${alertCount} ALERT${alertCount === 1 ? "" : "S"}`;
    }

    const item = document.createElement("div");
    item.className = "alert-item mono";

    const now = new Date();
    const timeStr =
      now.toTimeString().split(" ")[0] + "." + Math.floor(now.getMilliseconds() / 100);

    const detailsDiv = document.createElement("div");
    detailsDiv.className = "alert-details";

    const titleSpan = document.createElement("span");
    titleSpan.className = "alert-title";
    const zoneSafe =
      data && typeof data.zone === "string"
        ? data.zone
        : data && data.zone
        ? String(data.zone)
        : "Turn";
    titleSpan.textContent = `⚠ INTERVENE: ${zoneSafe} Threshold Exceeded`;

    const metaSpan = document.createElement("span");
    metaSpan.className = "alert-meta";

    const lapNum = Number(data && data.lap);
    const lapStr = Number.isFinite(lapNum) ? String(lapNum) : "1";

    const gNum = Number(data && data.g_force);
    const gStr = Number.isFinite(gNum) ? gNum.toFixed(2) : "--";

    const threshNum = Number(data && data.threshold);
    const threshStr = Number.isFinite(threshNum) ? threshNum.toFixed(2) : "1.15";

    metaSpan.textContent = `Lap ${lapStr} · Force: ${gStr}g (Limit: ${threshStr}g) · ${timeStr}`;

    detailsDiv.appendChild(titleSpan);
    detailsDiv.appendChild(metaSpan);

    const badgeSpan = document.createElement("span");
    badgeSpan.className = "alert-badge";
    badgeSpan.textContent = "RED ALERT";

    item.appendChild(detailsDiv);
    item.appendChild(badgeSpan);

    alertList.insertBefore(item, alertList.firstChild);

    while (alertList.children.length > MAX_ALERTS) {
      alertList.removeChild(alertList.lastChild);
    }
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

    if (stage === "INTERVENE") {
      recordInterveneAlert(data);
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
