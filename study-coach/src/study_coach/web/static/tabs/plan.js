/* study-coach — Plan tab: milestones and plan history */

const Plan = {
  async load() {
    this.loadMilestones();
    this.loadHistory();
  },

  async loadMilestones() {
    const data = await api("/api/milestones");
    const list = document.getElementById("plan-milestones");
    list.innerHTML = "";
    if (!data.milestones || data.milestones.length === 0) {
      list.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem">暂无里程碑，请先完成初始设置</div>';
      return;
    }
    data.milestones.forEach(m => {
      const daysLeft = (() => {
        try { return Math.ceil((new Date(m.deadline) - new Date()) / 86400000); }
        catch { return ""; }
      })();
      let dotClass = "pending";
      if (m.completed) dotClass = "done";
      else if (daysLeft !== "" && daysLeft <= 14) dotClass = "active";

      const item = document.createElement("div");
      item.className = "milestone-item";
      item.innerHTML = `
        <div class="milestone-dot ${dotClass}"></div>
        <span class="milestone-name">${m.name}</span>
        <span class="milestone-deadline">${m.deadline} ${daysLeft !== "" ? "(" + daysLeft + "天)" : ""}</span>
        <button class="milestone-toggle" onclick="Plan.toggleMilestone('${m.id}', ${m.completed})">
          ${m.completed ? "↩ 撤销" : "✓ 完成"}
        </button>
      `;
      list.appendChild(item);
    });

    // Show alerts if any
    if (data.alerts && data.alerts.length > 0) {
      const alertDiv = document.createElement("div");
      alertDiv.style.cssText = "margin-top:0.8rem;padding:0.6rem;background:var(--bg);border-radius:8px;border-left:3px solid var(--yellow);font-size:0.85rem";
      alertDiv.innerHTML = data.alerts.map(a => {
        const icon = a.status === "overdue" ? "🔴" : a.status === "urgent" ? "🟡" : "🟠";
        return `${icon} ${a.milestone}：剩余${a.days}天`;
      }).join("<br>");
      list.appendChild(alertDiv);
    }
  },

  async toggleMilestone(id, currentlyCompleted) {
    await api(`/api/milestones/${id}/toggle`, "POST");
    this.loadMilestones();
  },

  async loadHistory() {
    const data = await api("/api/stats/week");
    const container = document.getElementById("plan-history");
    container.innerHTML = "";
    if (!data.days || data.days.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem">暂无历史记录</div>';
      return;
    }
    data.days.forEach(d => {
      const item = document.createElement("div");
      item.className = "history-item";
      const rate = d.tasks_total > 0 ? Math.round(d.tasks_done / d.tasks_total * 100) : 0;
      item.innerHTML = `
        <div class="hi-date">${d.date}</div>
        <div class="hi-summary">${d.tasks_done}/${d.tasks_total} 任务 (${rate}%) · ${fmtMin(d.actual_minutes)} · ${d.pomodoros} 番茄钟 ${d.checked_in ? "✅" : ""}</div>
      `;
      container.appendChild(item);
    });
  },
};
