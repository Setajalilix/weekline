import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  ArcElement,
  LinearScale,
  Tooltip,
} from "chart.js";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, DoughnutController, ArcElement, Tooltip);

const ink = "#17191F";
const paper = "#F4F1E9";
const mist = "#A5A7B1";
const accent = "#B8A0FF";
const success = "#A9C9B2";

export function initCharts() {
  const week = document.getElementById("week-chart");
  if (week && !week.dataset.ready) {
    const data = JSON.parse(week.dataset.chart);
    paintBar(week, data.labels, data.values);
    week.dataset.ready = "1";
  }
  const daily = document.getElementById("review-daily-chart");
  if (daily && !daily.dataset.ready) {
    const data = JSON.parse(daily.dataset.chart);
    paintBar(daily, data.labels, data.values);
    daily.dataset.ready = "1";
  }
  const source = document.getElementById("review-source-chart");
  if (source && !source.dataset.ready) {
    const data = JSON.parse(source.dataset.chart);
    new Chart(source, {
      type: "doughnut",
      data: {
        labels: ["Manual", "Timer"],
        datasets: [
          {
            data: [data.manual, data.timer],
            backgroundColor: [accent, success],
            borderWidth: 0,
          },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: mist } } },
      },
    });
    source.dataset.ready = "1";
  }
}

function paintBar(canvas, labels, values) {
  new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: accent,
          borderRadius: 10,
          maxBarThickness: 28,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: mist },
          grid: { display: false },
        },
        y: {
          ticks: { color: mist },
          grid: { color: "rgba(255,255,255,0.06)" },
          beginAtZero: true,
          suggestedMax: 1,
        },
      },
    },
  });
}

void ink;
void paper;
