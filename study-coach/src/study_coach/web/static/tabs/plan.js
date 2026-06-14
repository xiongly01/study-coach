/* study-coach — Plan tab: yearly/monthly cascade, milestones, and plan history */

const Plan = {
  async load() {
    this.loadYearly();
    this.loadMonthly();
    this.loadDrift();
    this.loadMilestones();
    this.loadHistory();
  },

  // ---- Yearly cascade ----

  async loadYearly() {
    const data = await api("/api/yearly");
    const container = document.getElementById("plan-yearly");
    container.innerHTML = "";
    const plan = data.plan;
    if (!plan || !plan.phases || plan.phases.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem">暂无年度计划</div>';
      return;
    }
    plan.phases.forEach(p => {
      const wstr = Object.entries(p.weight_overrides || {})
        .map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(" · ");
      const item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML = `
        <div class="hi-date">${p.name}</div>
        <div class="hi-summary">${p.start} ~ ${p.end}<br>${wstr || "—"}</div>
      `;
      container.appendChild(item);
    });
  },

  async regenerateYearly() {
    await api("/api/yearly/regenerate", "POST");
    showToast("已按考试日期重建年度阶段");
    this.loadYearly();
  },

  // ---- Monthly plan ----

  async loadMonthly() {
    const data = await api("/api/monthly");
    const container = document.getElementById("plan-monthly");
    if (!data.plan) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem">本月暂无月度计划，点击"生成月度"</div>';
      return;
    }
    const p = data.plan;
    const wstr = Object.entries(p.subject_weights || {})
      .map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(" · ");
    let html = `<div class="history-item"><div class="hi-date">${p.month} · ${p.phase || "—"}</div>`;
    html += `<div class="hi-summary">${wstr}</div></div>`;
    if (p.goals && p.goals.length) {
      html += p.goals.map(g =>
        `<div class="history-item"><div class="hi-summary">🎯 [${g.subject}] ${g.goal}</div></div>`
      ).join("");
    }
    const src = p.generated_from || {};
    if (src.source || src.rationale) {
      html += `<div class="hi-summary" style="color:var(--text-dim)">来源：${src.source || "—"}${src.rationale ? " · " + src.rationale : ""}</div>`;
    }
    container.innerHTML = html;
  },

  async generateMonthly() {
    const data = await api("/api/monthly/generate", "POST");
    if (data.ok) {
      showToast("月度计划已生成");
      this.loadMonthly();
    } else {
      showToast(data.error || "生成失败");
    }
  },

  // ---- Drift signals ----

  async loadDrift() {
    const data = await api("/api/drift");
    const panel = document.getElementById("plan-drift-panel");
    const container = document.getElementById("plan-drift");
    if (!data.signals || data.signals.length === 0) {
      panel.style.display = "none";
      return;
    }
    panel.style.display = "block";
    const icon = { high: "🔴", medium: "🟡", low: "🟢" };
    let html = data.signals.map(s =>
      `<div class="history-item">
        <div class="hi-date">${icon[s.severity] || "⚪"} ${s.type}</div>
        <div class="hi-summary">${s.detail}</div>
       </div>`
    ).join("");
    // Drift describes past deviation; regenerating refreshes the month's weights
    // for the days ahead. Signals persist until execution catches up.
    if (data.trigger_replan) {
      html += `<button class="btn btn-small" style="margin-top:0.6rem;width:100%" onclick="Plan.generateMonthly()">根据漂移重新生成月度</button>`;
    }
    container.innerHTML = html;
  },

  // ---- Milestones ----

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
