/* study-coach — Overview tab: weekly stats, reports, compliance */

const Overview = {
  async load() {
    this.loadWeekChart();
    this.loadReports();
    this.loadCompliance();
  },

  async loadWeekChart() {
    const data = await api("/api/stats/week");
    const chart = document.getElementById("week-chart");
    chart.innerHTML = "";
    if (!data.days || data.days.length === 0) {
      chart.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:1.5rem">暂无数据</div>';
      return;
    }
    const maxMin = Math.max(...data.days.map(d => Math.max(d.planned_minutes, d.actual_minutes)), 1);
    data.days.forEach(d => {
      const plannedPct = (d.planned_minutes / maxMin * 100).toFixed(1);
      const actualPct = (d.actual_minutes / maxMin * 100).toFixed(1);
      const dt = new Date(d.date);
      const weekday = ["日", "一", "二", "三", "四", "五", "六"][dt.getDay()];
      const row = document.createElement("div");
      row.className = "week-bar-row";
      row.innerHTML = `
        <span class="week-bar-date">${d.date.slice(5)} 周${weekday}</span>
        <div class="week-bar-track">
          <div class="week-bar-fill planned" style="width:${plannedPct}%"></div>
          <div class="week-bar-fill actual" style="width:${actualPct}%"></div>
        </div>
        <span class="week-bar-value">${fmtMin(d.actual_minutes)}</span>
      `;
      chart.appendChild(row);
    });
  },

  async loadReports() {
    const data = await api("/api/reports");
    const container = document.getElementById("overview-reports");
    container.innerHTML = "";
    if (!data.reports || data.reports.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:1.5rem">暂无报告，点击"生成周报"创建</div>';
      return;
    }
    data.reports.forEach(r => {
      const item = document.createElement("div");
      item.className = "report-item";
      item.innerHTML = `
        <a href="#" onclick="Overview.viewReport('${r.filename}'); return false;">${r.filename}</a>
        <span style="font-size:0.75rem;color:var(--text-dim)">${(r.size / 1024).toFixed(1)}KB</span>
      `;
      container.appendChild(item);
    });
  },

  async viewReport(filename) {
    const data = await api(`/api/reports/${encodeURIComponent(filename)}`);
    if (data.error) { showToast("加载失败"); return; }
    let overlay = document.getElementById("report-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "report-overlay";
      overlay.className = "modal-overlay";
      document.body.appendChild(overlay);
    }
    overlay.style.display = "flex";
    // Simple markdown to HTML
    const html = data.content
      .replace(/^### (.+)$/gm, "<h4>$1</h4>")
      .replace(/^## (.+)$/gm, "<h3>$1</h3>")
      .replace(/^# (.+)$/gm, "<h2>$1</h2>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/\n\n/g, "<br><br>")
      .replace(/\|(.+)\|/g, (match) => {
        const cells = match.split("|").filter(c => c.trim());
        return "<tr>" + cells.map(c => `<td style="padding:2px 8px;border:1px solid var(--border)">${c.trim()}</td>`).join("") + "</tr>";
      });
    overlay.innerHTML = `
      <div class="modal modal-large">
        <h3>${filename}</h3>
        <div style="font-size:0.85rem;line-height:1.6;max-height:60vh;overflow-y:auto">${html}</div>
        <div class="modal-actions" style="margin-top:1rem">
          <button class="btn btn-ghost" onclick="document.getElementById('report-overlay').style.display='none'">关闭</button>
        </div>
      </div>
    `;
  },

  async generateReport() {
    const res = await api("/api/report/generate", "POST");
    if (res.ok) {
      showToast(`周报已生成：${res.filename}`);
      this.loadReports();
    } else {
      showToast("生成失败");
    }
  },

  async loadCompliance() {
    const data = await api("/api/stats/compliance");
    const container = document.getElementById("overview-compliance");
    container.innerHTML = "";
    if (!data.days_checked) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:1.5rem">暂无数据</div>';
      return;
    }
    const adherencePct = Math.round((data.adherence_rate || 0) * 100);
    const grid = document.createElement("div");
    grid.className = "compliance-grid";
    const cards = [
      { label: "检查天数", value: data.days_checked },
      { label: "有计划天数", value: data.days_with_plan },
      { label: "全部完成天数", value: data.days_completed },
      { label: "执行率", value: `${adherencePct}%` },
      { label: "计划总时长", value: fmtMin(data.total_planned_minutes) },
      { label: "实际总时长", value: fmtMin(data.total_actual_minutes) },
      { label: "未完成任务", value: data.overdue_tasks },
      { label: "涉及科目不足", value: Object.keys(data.subject_deficit || {}).length },
    ];
    cards.forEach(c => {
      const card = document.createElement("div");
      card.className = "compliance-card";
      card.innerHTML = `<div class="cc-value">${c.value}</div><div class="cc-label">${c.label}</div>`;
      grid.appendChild(card);
    });
    container.appendChild(grid);
  },
};
