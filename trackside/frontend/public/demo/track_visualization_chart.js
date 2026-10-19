/**
 * Trackside Visualizer — Chart & Glove LED Signal Strip Engine.
 * Renders the rolling lateral-g waveform canvas and updates the 5-segment glove LED strip.
 */

window.TracksideChart = (function () {
  const MAX_CHART_POINTS = 60;
  const gHistory = [];

  for (let i = 0; i < MAX_CHART_POINTS; i++) {
    gHistory.push(0.2);
  }

  function drawChart(canvas, ctx, activeThreshold) {
    if (!canvas || !ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = "#161D26";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h * 0.33);
    ctx.lineTo(w, h * 0.33);
    ctx.moveTo(0, h * 0.66);
    ctx.lineTo(w, h * 0.66);
    ctx.stroke();

    // Threshold dashed line
    if (activeThreshold) {
      const maxG = 2.0;
      const threshY = h - (activeThreshold / maxG) * (h - 10) - 5;
      ctx.strokeStyle = "rgba(229, 71, 60, 0.4)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, threshY);
      ctx.lineTo(w, threshY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw waveform line
    ctx.beginPath();
    const step = w / (MAX_CHART_POINTS - 1);
    for (let i = 0; i < gHistory.length; i++) {
      const val = Math.min(2.0, gHistory[i]);
      const x = i * step;
      const y = h - (val / 2.0) * (h - 12) - 6;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }

    const latestG = gHistory[gHistory.length - 1] || 0;
    let strokeColor = "#33D17E";
    if (activeThreshold && latestG >= activeThreshold) {
      strokeColor = "#E5473C";
    } else if (activeThreshold && latestG >= activeThreshold * 0.82) {
      strokeColor = "#F2A93B";
    }

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }

  function updateSignalStrip(segments, stageBadge, stage) {
    const stageUpper = (stage || "NOMINAL").toUpperCase();

    segments.forEach((seg) => {
      if (seg) seg.className = "signal-segment";
    });

    if (stageUpper === "INTERVENE") {
      segments[0] && (segments[0].className = "signal-segment lit-green");
      segments[1] && (segments[1].className = "signal-segment lit-green");
      segments[2] && (segments[2].className = "signal-segment lit-amber");
      segments[3] && (segments[3].className = "signal-segment lit-amber");
      segments[4] && (segments[4].className = "signal-segment lit-red");

      if (stageBadge) {
        stageBadge.textContent = "INTERVENE";
        stageBadge.className = "stage-pill intervene mono";
      }
    } else if (stageUpper === "MONITORING") {
      segments[0] && (segments[0].className = "signal-segment lit-green");
      segments[1] && (segments[1].className = "signal-segment lit-green");
      segments[2] && (segments[2].className = "signal-segment lit-amber");
      segments[3] && (segments[3].className = "signal-segment lit-amber");

      if (stageBadge) {
        stageBadge.textContent = "MONITORING";
        stageBadge.className = "stage-pill monitoring mono";
      }
    } else {
      segments[0] && (segments[0].className = "signal-segment lit-green");
      segments[1] && (segments[1].className = "signal-segment lit-green");

      if (stageBadge) {
        stageBadge.textContent = "NOMINAL";
        stageBadge.className = "stage-pill nominal mono";
      }
    }
  }

  function updateZonePill(zonePills, zoneName) {
    const zn = (zoneName || "").toLowerCase();
    Object.keys(zonePills).forEach((k) => {
      if (zonePills[k]) zonePills[k].classList.remove("active");
    });

    if (zn.includes("hairpin")) {
      zonePills.hairpin && zonePills.hairpin.classList.add("active");
    } else if (zn.includes("sweeper")) {
      zonePills.sweeper && zonePills.sweeper.classList.add("active");
    } else if (zn.includes("chicane")) {
      zonePills.chicane && zonePills.chicane.classList.add("active");
    } else {
      zonePills.straight1 && zonePills.straight1.classList.add("active");
    }
  }

  return {
    gHistory,
    drawChart,
    updateSignalStrip,
    updateZonePill,
  };
})();
