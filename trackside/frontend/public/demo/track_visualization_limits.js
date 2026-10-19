/**
 * Trackside Visualizer — Corner Limits & Presets Engine.
 * Manages per-corner lateral-g limit validation, error rendering, and preset switching.
 */

window.TracksideLimits = (function () {
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

  function applyRanges(data) {
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
  }

  return {
    cornerInputs,
    validateCorner,
    applyRanges,
    getCachedRanges: () => cachedLimitRanges,
  };
})();
