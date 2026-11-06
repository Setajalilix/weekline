let clockTimer = null;

function elapsedFromState(state) {
  if (!state || state.status === "idle") return 0;
  if (state.status !== "running" || !state.segment_started_at) {
    return state.elapsed_seconds || state.accumulated_seconds || 0;
  }
  const started = Date.parse(state.segment_started_at);
  return Math.max(0, (state.accumulated_seconds || 0) + Math.floor((Date.now() - started) / 1000));
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function renderClock(root, totalSeconds) {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const parts = {
    hours: pad(Math.floor(safe / 3600)),
    minutes: pad(Math.floor((safe % 3600) / 60)),
    seconds: pad(safe % 60),
  };
  root.querySelectorAll("[data-flap]").forEach((card) => {
    const next = parts[card.dataset.flap];
    if (card.textContent !== next) card.textContent = next;
  });
}

export function initFlipClock(resync = false) {
  const stage = document.getElementById("timer-stage");
  if (!stage) return;
  const root = stage.querySelector(".flap-clock");
  if (!root) return;

  let state = {};
  try {
    state = JSON.parse(stage.dataset.timerState || "{}");
  } catch {
    state = {};
  }

  renderClock(root, elapsedFromState(state));

  if (clockTimer) window.clearInterval(clockTimer);
  if (state.status === "running") {
    clockTimer = window.setInterval(() => {
      renderClock(root, elapsedFromState(state));
    }, 250);
  }

  if (resync) {
    fetch("/timer/state/", { headers: { "HX-Request": "true" } })
      .then((res) => res.text())
      .then((html) => {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        const next = wrapper.querySelector("[data-timer-state]");
        if (!next) return;
        stage.dataset.timerState = next.dataset.timerState;
        initFlipClock(false);
      })
      .catch(() => {});
  }
}
