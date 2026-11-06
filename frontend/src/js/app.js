import "../css/app.css";
import htmx from "htmx.org";
import Alpine from "alpinejs";
import {
  Calendar,
  CalendarDays,
  CalendarRange,
  Clock3,
  History,
  LayoutDashboard,
  Settings,
  Target,
  createIcons,
} from "lucide";
import { initCharts } from "./charts";
import { initFlipClock } from "./flip-clock";

window.htmx = htmx;
window.Alpine = Alpine;

document.addEventListener("alpine:init", () => {
  const CIRCLE = 12 * 60;
  const STEP = 5;
  const RADIUS = 78;

  Alpine.data("rangeClock", (hours = 1, minutes = 0, startsAt = "") => {
    const duration = Math.max(STEP, Number(hours) * 60 + Number(minutes) || 60);
    let start = 9 * 60;
    let period = "am";
    if (startsAt && /^\d{1,2}:\d{2}/.test(startsAt)) {
      const [hh, mm] = startsAt.split(":").map(Number);
      period = hh >= 12 ? "pm" : "am";
      start = (hh % 12) * 60 + mm;
    }
    return {
      start,
      period,
      end: (start + duration) % CIRCLE,
      drag: null,
      get durationMins() {
        let diff = this.end - this.start;
        if (diff <= 0) diff += CIRCLE;
        return diff;
      },
      get h() {
        return Math.floor(this.durationMins / 60);
      },
      get m() {
        return this.durationMins % 60;
      },
      get durationLabel() {
        if (this.h && this.m) return `${this.h}h ${String(this.m).padStart(2, "0")}m`;
        if (this.h) return `${this.h}h`;
        return `${this.m}m`;
      },
      get startMins24() {
        const hour12 = Math.floor(this.start / 60) % 12;
        const minute = this.start % 60;
        const hour = this.period === "pm" ? (hour12 === 0 ? 12 : hour12 + 12) : hour12;
        return hour * 60 + minute;
      },
      get startsAtValue() {
        const hour = Math.floor(this.startMins24 / 60);
        const minute = this.startMins24 % 60;
        return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
      },
      get rangeLabel() {
        return `${this.format24(this.startMins24)} – ${this.format24(this.startMins24 + this.durationMins)}`;
      },
      get arcPath() {
        const from = this.polar(this.start);
        const to = this.polar(this.end);
        const large = this.durationMins > CIRCLE / 2 ? 1 : 0;
        return `M ${from.x} ${from.y} A ${RADIUS} ${RADIUS} 0 ${large} 1 ${to.x} ${to.y}`;
      },
      format24(mins) {
        const wrapped = ((mins % (24 * 60)) + 24 * 60) % (24 * 60);
        const hour24 = Math.floor(wrapped / 60);
        const minute = wrapped % 60;
        const hour = hour24 % 12 || 12;
        const suffix = hour24 >= 12 ? "PM" : "AM";
        return `${hour}:${String(minute).padStart(2, "0")} ${suffix}`;
      },
      polar(mins) {
        const deg = (mins / CIRCLE) * 360;
        const rad = ((deg - 90) * Math.PI) / 180;
        return { x: 100 + RADIUS * Math.cos(rad), y: 100 + RADIUS * Math.sin(rad) };
      },
      handleStyle(mins) {
        const { x, y } = this.polar(mins);
        return { left: `${x / 2}%`, top: `${y / 2}%` };
      },
      numStyle(n) {
        const mins = (n % 12) * 60;
        const deg = (mins / CIRCLE) * 360;
        const rad = ((deg - 90) * Math.PI) / 180;
        const r = 52;
        const x = 50 + (r / 2) * Math.cos(rad);
        const y = 50 + (r / 2) * Math.sin(rad);
        return { left: `${x}%`, top: `${y}%` };
      },
      grab(which, event) {
        event.preventDefault();
        this.drag = which;
        event.currentTarget.setPointerCapture(event.pointerId);
        const onMove = (moveEvent) => this.point(moveEvent);
        const onUp = () => {
          this.drag = null;
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        this.point(event);
      },
      point(event) {
        if (!this.drag || !this.$refs.face) return;
        const rect = this.$refs.face.getBoundingClientRect();
        const dx = event.clientX - (rect.left + rect.width / 2);
        const dy = event.clientY - (rect.top + rect.height / 2);
        let deg = (Math.atan2(dx, -dy) * 180) / Math.PI;
        if (deg < 0) deg += 360;
        const mins = (Math.round((deg / 360) * CIRCLE / STEP) * STEP) % CIRCLE;
        if (this.drag === "start") this.start = mins;
        else this.end = mins;
      },
    };
  });
});

Alpine.start();

function enhance() {
  createIcons({
    icons: {
      Calendar,
      CalendarDays,
      CalendarRange,
      Clock3,
      History,
      LayoutDashboard,
      Settings,
      Target,
    },
  });
  initCharts();
  initFlipClock();
}

document.addEventListener("DOMContentLoaded", enhance);
document.body.addEventListener("htmx:afterSwap", enhance);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && document.querySelector("[data-timer-state]")) {
    initFlipClock(true);
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("#fullscreen-timer");
  if (!button) return;
  const stage = document.getElementById("timer-stage");
  if (!stage) return;
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    stage.requestFullscreen();
  }
});
