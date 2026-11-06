import Tick from "@pqina/flip";
import "@pqina/flip/dist/flip.min.css";

let clockTimer = null;

function elapsedFromState(state) {
  if (!state || state.status === "idle") return 0;
  if (state.status !== "running" || !state.segment_started_at) {
    return state.elapsed_seconds || state.accumulated_seconds || 0;
  }
  const started = Date.parse(state.segment_started_at);
  return Math.max(0, (state.accumulated_seconds || 0) + Math.floor((Date.now() - started) / 1000));
}

function toHms(totalSeconds) {
  const safe = Math.max(0, Math.floor(totalSeconds));
  return {
    hours: Math.floor(safe / 3600),
    minutes: Math.floor((safe % 3600) / 60),
    seconds: safe % 60,
  };
}

function bindClock(root, seconds) {
  const existing = Tick.DOM.find(root);
  if (existing) {
    existing.value = toHms(seconds);
    return existing;
  }
  const tick = Tick.DOM.create(root, { credits: false });
  if (tick) tick.value = toHms(seconds);
  return tick;
}

export function initFlipClock(resync = false) {
  const stage = document.getElementById("timer-stage");
  if (!stage) return;
  const root = stage.querySelector(".tick");
  if (!root) return;

  let state = {};
  try {
    state = JSON.parse(stage.dataset.timerState || "{}");
  } catch {
    state = {};
  }

  bindClock(root, elapsedFromState(state));

  if (clockTimer) window.clearInterval(clockTimer);
  if (state.status === "running") {
    clockTimer = window.setInterval(() => {
      bindClock(root, elapsedFromState(state));
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
