/* study-coach — main app logic, routing, shared utils */

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function api(url, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body && !(body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (body instanceof FormData) {
    opts.body = body;
  }
  const res = await fetch(url, opts);
  return res.json();
}

function fmtMin(minutes) {
  if (!minutes) return "0m";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h${String(m).padStart(2, "0")}m` : `${m}m`;
}

function pad(n) { return String(n).padStart(2, "0"); }

function showToast(msg, duration = 2000) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.display = "block";
  setTimeout(() => { t.style.display = "none"; }, duration);
}

// ---------------------------------------------------------------------------
// App controller
// ---------------------------------------------------------------------------

const App = {
  currentTab: "today",
  initialized: false,

  init() {
    this.updateDate();
    this.checkInit();
  },

  updateDate() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("zh-CN", {
      year: "numeric", month: "long", day: "numeric", weekday: "long",
    });
    document.getElementById("today-date").textContent = dateStr;
  },

  async checkInit() {
    const data = await api("/api/config");
    if (!data.initialized) {
      this.showSetup();
      return;
    }
    this.initialized = true;
    this.loadStatus();
    this.switchTab("today");
  },

  showSetup() {
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    document.getElementById("tab-setup").classList.add("active");
    document.getElementById("tab-bar").style.display = "none";
  },

  async saveSetup() {
    const config = {
      exam_date: document.getElementById("setup-exam-date").value,
      daily_study_hours: parseInt(document.getElementById("setup-hours").value),
      target_school: document.getElementById("setup-school").value,
      target_major: document.getElementById("setup-major").value,
    };
    await api("/api/config", "POST", config);
    showToast("设置已保存");
    document.getElementById("tab-bar").style.display = "flex";
    this.initialized = true;
    this.loadStatus();
    this.switchTab("today");
  },

  switchTab(name) {
    this.currentTab = name;
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    document.getElementById(`tab-${name}`).classList.add("active");
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelector(`.tab-btn[data-tab="${name}"]`).classList.add("active");

    // Load tab data
    const loaders = {
      today: () => Today.load(),
      plan: () => Plan.load(),
      exam: () => Exam.load(),
      wrongbook: () => WrongBook.load(),
      overview: () => Overview.load(),
    };
    if (loaders[name]) loaders[name]();
  },

  async loadStatus() {
    const data = await api("/api/status");
    if (!data.initialized) return;
    const badgeExam = document.getElementById("badge-exam");
    const badgeStreak = document.getElementById("badge-streak");
    if (data.days_to_exam >= 0) {
      badgeExam.innerHTML = `距考研 <strong>${data.days_to_exam}</strong> 天`;
    }
    badgeStreak.innerHTML = `连续打卡 <strong>${data.streak}</strong> 天`;
    document.getElementById("stat-pomodoros").textContent = data.pomodoros || 0;
    const actual = data.actual_minutes || 0;
    document.getElementById("stat-today-time").textContent =
      `${Math.floor(actual / 60)}h${String(actual % 60).padStart(2, "0")}m`;
  },
};

// ---------------------------------------------------------------------------
// Init on DOM ready
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => App.init());
