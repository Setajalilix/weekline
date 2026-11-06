import "../css/app.css";
import htmx from "htmx.org";
import Alpine from "alpinejs";
import {
  Calendar,
  CalendarDays,
  CalendarRange,
  ChevronDown,
  Clock3,
  History,
  LayoutDashboard,
  LogOut,
  Pencil,
  Save,
  Settings,
  Target,
  Trash2,
  X,
  createIcons,
} from "lucide";
import { initCharts } from "./charts";
import { initFlipClock } from "./flip-clock";

window.htmx = htmx;
window.Alpine = Alpine;

document.addEventListener("alpine:init", () => {
  Alpine.data("logSheet", (date) => ({
    date: date || "",
    onGoalTitle(title) {
      if (title && this.$refs.activity) this.$refs.activity.value = title;
    },
  }));

  Alpine.data("goalPicker", (selected = "") => ({
    open: false,
    value: String(selected || ""),
    label: "No goal",
    color: "",
    init() {
      this.sync();
    },
    sync() {
      const opt = this.$el.querySelector(`[data-goal-id="${this.value}"]`);
      this.label = opt?.dataset.title || "No goal";
      this.color = opt?.dataset.color || "";
    },
    pick(id, title, color) {
      this.value = id ? String(id) : "";
      this.label = title;
      this.color = color || "";
      this.open = false;
      this.$dispatch("goal-picked", { title: id ? title : "" });
      this.$nextTick(() => window.paintIcons?.());
    },
  }));

  Alpine.data("durationWheels", (hours = 1, minutes = 0) => ({
    h: Math.max(0, Number(hours) || 0),
    m: Math.min(59, Math.max(0, Number(minutes) || 0)),
    maxHours: 168,
    item: 44,
    get hoursList() {
      return Array.from({ length: Math.max(this.maxHours, this.h) + 1 }, (_, i) => i);
    },
    get minutesList() {
      return Array.from({ length: 60 }, (_, i) => i);
    },
    get label() {
      if (this.h && this.m) return `${this.h}h ${String(this.m).padStart(2, "0")}m`;
      if (this.h) return `${this.h}h`;
      return `${this.m}m`;
    },
    ready() {
      this.$nextTick(() => {
        this.$nextTick(() => {
          const sample = this.$refs.hours?.querySelector(".time-wheel-item");
          if (sample) this.item = sample.offsetHeight;
          this.jump("hours", this.h);
          this.jump("minutes", this.m);
        });
      });
    },
    jump(which, value) {
      const el = this.$refs[which];
      if (!el) return;
      el.scrollTop = value * this.item;
    },
    pick(which, value) {
      if (which === "hours") this.h = value;
      else this.m = value;
      this.jump(which, value);
    },
    sync(which) {
      const el = this.$refs[which];
      if (!el || !this.item) return;
      const value = Math.round(el.scrollTop / this.item);
      if (which === "hours") this.h = Math.max(0, Math.min(this.maxHours, value));
      else this.m = Math.max(0, Math.min(59, value));
    },
  }));

  const CIRCLE = 24 * 60;
  const STEP = 5;
  const RADIUS = 78;
  const FACE_HOURS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22];

  Alpine.data("rangeClock", (hours = 1, minutes = 0, startsAt = "") => {
    const duration = Math.max(STEP, Number(hours) * 60 + Number(minutes) || 60);
    let start = 9 * 60;
    if (startsAt && /^\d{1,2}:\d{2}/.test(startsAt)) {
      const [hh, mm] = startsAt.split(":").map(Number);
      start = ((hh % 24) * 60 + mm) % CIRCLE;
    }
    return {
      start,
      faceHours: FACE_HOURS,
      end: (start + Math.min(duration, CIRCLE)) % CIRCLE,
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
      get startsAtValue() {
        return this.format24(this.start);
      },
      get rangeLabel() {
        return `${this.format24(this.start)} – ${this.format24(this.start + this.durationMins)}`;
      },
      clockParts(mins) {
        const wrapped = ((mins % CIRCLE) + CIRCLE) % CIRCLE;
        return {
          h: String(Math.floor(wrapped / 60)).padStart(2, "0"),
          m: String(wrapped % 60).padStart(2, "0"),
        };
      },
      get startClock() {
        return this.clockParts(this.start);
      },
      get endClock() {
        return this.clockParts(this.start + this.durationMins);
      },
      get arcPath() {
        const from = this.polar(this.start);
        const to = this.polar(this.end);
        const large = this.durationMins > CIRCLE / 2 ? 1 : 0;
        return `M ${from.x} ${from.y} A ${RADIUS} ${RADIUS} 0 ${large} 1 ${to.x} ${to.y}`;
      },
      format24(mins) {
        const wrapped = ((mins % CIRCLE) + CIRCLE) % CIRCLE;
        const hour = Math.floor(wrapped / 60);
        const minute = wrapped % 60;
        return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
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
        const mins = (n % 24) * 60;
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

const lucideIcons = {
  Calendar,
  CalendarDays,
  CalendarRange,
  ChevronDown,
  Clock3,
  History,
  LayoutDashboard,
  LogOut,
  Pencil,
  Save,
  Settings,
  Target,
  Trash2,
  X,
};

window.paintIcons = function paintIcons() {
  createIcons({ icons: lucideIcons });
};

function enhance() {
  window.paintIcons();
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
