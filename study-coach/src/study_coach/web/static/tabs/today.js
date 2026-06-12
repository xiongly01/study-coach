/* study-coach — Today tab: timer, tasks, reflection */

const Today = {
  timerRunning: false,
  timerStart: null,
  timerInterval: null,
  timerSeconds: 0,
  wsSessionId: null,
  ws: null,

  async load() {
    this.loadPlan();
    this.connectWS();
  },

  // ---- Timer ----

  toggleTimer() {
    if (this.timerRunning) this.stopTimer();
    else this.startTimer();
  },

  startTimer() {
    this.timerRunning = true;
    this.timerStart = new Date();
    this.timerSeconds = 0;
    const btn = document.getElementById("btn-start");
    btn.textContent = "⏸ 暂停";
    btn.classList.add("running");
    document.getElementById("timer-label").textContent = "专注学习中...";
    this.timerInterval = setInterval(() => {
      this.timerSeconds++;
      this.updateTimerDisplay();
    }, 1000);
    // Notify server
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const sel = document.getElementById("task-select");
      const opt = sel.options[sel.selectedIndex];
      this.ws.send(JSON.stringify({
        type: "start",
        task_id: sel.value,
        subject: opt ? opt.textContent.split(" — ")[0] : "",
      }));
    }
  },

  stopTimer() {
    this.timerRunning = false;
    clearInterval(this.timerInterval);
    const btn = document.getElementById("btn-start");
    btn.textContent = "▶ 开始";
    btn.classList.remove("running");
    document.getElementById("timer-label").textContent = "点击开始学习";
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.wsSessionId) {
      this.ws.send(JSON.stringify({ type: "stop", session_id: this.wsSessionId }));
      this.wsSessionId = null;
    }
    setTimeout(() => { this.loadPlan(); App.loadStatus(); }, 500);
  },

  resetTimer() {
    this.stopTimer();
    this.timerSeconds = 0;
    this.timerStart = null;
    this.updateTimerDisplay();
  },

  updateTimerDisplay() {
    const h = Math.floor(this.timerSeconds / 3600);
    const m = Math.floor((this.timerSeconds % 3600) / 60);
    const s = this.timerSeconds % 60;
    document.getElementById("timer-time").textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
    const circ = 2 * Math.PI * 90;
    const progress = Math.min(this.timerSeconds / (25 * 60), 1);
    document.getElementById("timer-progress").style.strokeDashoffset = circ * (1 - progress);
  },

  connectWS() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    this.ws = new WebSocket(`${proto}//${location.host}/ws/timer`);
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "started") this.wsSessionId = msg.session_id;
      else if (msg.type === "stopped") { this.loadPlan(); App.loadStatus(); }
    };
    this.ws.onclose = () => { setTimeout(() => this.connectWS(), 3000); };
  },

  // ---- Plan ----

  async loadPlan() {
    const data = await api("/api/today");
    const list = document.getElementById("task-list");
    const select = document.getElementById("task-select");
    list.innerHTML = "";
    select.innerHTML = '<option value="">自由学习</option>';

    if (!data.tasks || data.tasks.length === 0) {
      list.innerHTML = '<div class="task-empty">暂无计划，点击"生成计划"或手动添加</div>';
    } else {
      data.tasks.forEach(t => {
        const item = document.createElement("div");
        item.className = "task-item" + (t.done ? " done" : "");
        item.innerHTML = `
          <div class="task-checkbox ${t.done ? "checked" : ""}" onclick="Today.toggleTask('${t.id}', ${!t.done})"></div>
          <span class="task-subject">${t.subject}</span>
          <span class="task-content">${t.content}</span>
          <span class="task-time">${fmtMin(t.actual_minutes)}/${fmtMin(t.planned_minutes)}</span>
        `;
        list.appendChild(item);
        if (!t.done) {
          const opt = document.createElement("option");
          opt.value = t.id;
          opt.textContent = `${t.subject} — ${t.content}`;
          select.appendChild(opt);
        }
      });
    }

    const actual = data.total_actual || 0;
    document.getElementById("stat-today-time").textContent =
      `${Math.floor(actual / 60)}h${String(actual % 60).padStart(2, "0")}m`;
    document.getElementById("stat-pomodoros").textContent = data.pomodoros ? data.pomodoros.length : 0;
    if (data.reflection) document.getElementById("reflection-text").value = data.reflection;
  },

  async toggleTask(taskId, markDone) {
    const url = markDone ? `/api/tasks/${taskId}/done` : `/api/tasks/${taskId}/undone`;
    await api(url, "POST");
    this.loadPlan();
  },

  async generatePlan() {
    const res = await api("/api/plan/generate", "POST");
    if (res.ok) {
      showToast(`已生成计划（${res.task_count}个任务）`);
      this.loadPlan();
    }
  },

  async addTask() {
    const subject = document.getElementById("new-task-subject").value;
    const content = document.getElementById("new-task-content").value.trim();
    const minutes = parseInt(document.getElementById("new-task-minutes").value) || 60;
    if (!content) { showToast("请输入任务内容"); return; }
    await api("/api/tasks", "POST", { subject, content, planned_minutes: minutes });
    document.getElementById("new-task-content").value = "";
    this.loadPlan();
  },

  async saveReflection() {
    const text = document.getElementById("reflection-text").value.trim();
    if (!text) return;
    await api("/api/checkin", "POST", { reflection: text });
    showToast("反思已保存");
    App.loadStatus();
  },
};
