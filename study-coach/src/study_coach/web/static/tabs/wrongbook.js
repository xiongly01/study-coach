/* study-coach — Wrong Book tab: upload, list, review, stats */

const WrongBook = {
  selectedFile: null,
  selectedPdf: null,
  currentPage: 1,
  aiAvailable: false,

  async load() {
    this.checkAI();
    this.loadReviewBadge();
    this.loadList();
  },

  async checkAI() {
    const data = await api("/api/ai/status");
    this.aiAvailable = data.available;
    const btn = document.getElementById("wb-analyze-btn");
    if (!this.aiAvailable) {
      btn.textContent = "AI 未配置（需设置 API Key）";
    }
  },

  // ---- Sub-view switching ----

  showSubView(name) {
    document.querySelectorAll(".wb-subview").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".wb-subnav-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`wb-${name}`).classList.add("active");
    // Highlight the clicked button
    const btns = document.querySelectorAll(".wb-subnav-btn");
    const map = { upload: 0, list: 1, review: 2, stats: 3 };
    if (map[name] !== undefined) btns[map[name]].classList.add("active");

    const loaders = {
      list: () => this.loadList(),
      review: () => this.loadReview(),
      stats: () => this.loadStats(),
    };
    if (loaders[name]) loaders[name]();
  },

  // ---- Image Upload ----

  handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    this.selectedFile = file;
    const preview = document.getElementById("upload-preview");
    const placeholder = document.getElementById("upload-placeholder");
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.style.display = "block";
      placeholder.style.display = "none";
    };
    reader.readAsDataURL(file);
    document.getElementById("wb-analyze-btn").disabled = false;
  },

  async analyzeImage() {
    if (!this.selectedFile) { showToast("请先选择图片"); return; }
    if (!this.aiAvailable) { showToast("AI 服务未配置，请设置 ANTHROPIC_API_KEY"); return; }

    const btn = document.getElementById("wb-analyze-btn");
    btn.textContent = "分析中...";
    btn.disabled = true;

    const formData = new FormData();
    formData.append("file", this.selectedFile);
    formData.append("subject", document.getElementById("wb-subject").value);
    formData.append("source", document.getElementById("wb-source").value);

    try {
      const res = await fetch("/api/wrong-book/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) {
        showToast(data.error);
        return;
      }
      // Show AI result
      const q = data.question;
      const resultDiv = document.getElementById("wb-ai-result");
      resultDiv.style.display = "block";
      resultDiv.innerHTML = `
        <h4>✅ AI 分析完成</h4>
        <p><strong>科目：</strong>${q.subject || "未识别"} · <strong>主题：</strong>${q.topic || "—"}</p>
        <p><strong>难度：</strong>${q.difficulty}/5</p>
        <pre><strong>题目：</strong>\n${q.question_text}\n\n<strong>解析：</strong>\n${q.answer}</pre>
        <div style="margin-top:0.5rem">
          ${q.knowledge_points.map(kp => `<span class="kp-tag">${kp}</span>`).join(" ")}
        </div>
      `;
      showToast("错题已添加");
      this.resetUpload();
      this.loadReviewBadge();
    } catch (e) {
      showToast("分析失败：" + e.message);
    } finally {
      btn.textContent = "AI 分析并添加";
      btn.disabled = false;
    }
  },

  resetUpload() {
    this.selectedFile = null;
    document.getElementById("wb-image-input").value = "";
    document.getElementById("upload-preview").style.display = "none";
    document.getElementById("upload-placeholder").style.display = "block";
    document.getElementById("wb-analyze-btn").disabled = true;
    document.getElementById("wb-source").value = "";
  },

  // ---- PDF Upload ----

  handlePdfSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    this.selectedPdf = file;
    document.getElementById("wb-pdf-btn").disabled = false;
  },

  async analyzePdf() {
    if (!this.selectedPdf) { showToast("请先选择 PDF 文件"); return; }
    if (!this.aiAvailable) { showToast("AI 服务未配置，请设置 ANTHROPIC_API_KEY"); return; }

    const btn = document.getElementById("wb-pdf-btn");
    const progress = document.getElementById("wb-pdf-progress");
    btn.textContent = "处理中...";
    btn.disabled = true;
    progress.style.display = "block";
    progress.textContent = "正在转换 PDF 并分析各页，请稍候...";

    const formData = new FormData();
    formData.append("file", this.selectedPdf);
    formData.append("subject", document.getElementById("wb-subject").value);
    formData.append("source", document.getElementById("wb-source").value || this.selectedPdf.name);

    try {
      const res = await fetch("/api/wrong-book/upload-pdf", { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) {
        progress.textContent = "❌ " + data.error;
        showToast(data.error);
        return;
      }
      progress.textContent = `✅ 已添加 ${data.total_pages} 页错题`;
      showToast(`PDF 已处理完成，共 ${data.total_pages} 页`);
      this.resetPdfUpload();
      this.loadReviewBadge();
    } catch (e) {
      progress.textContent = "❌ 处理失败：" + e.message;
      showToast("处理失败：" + e.message);
    } finally {
      btn.textContent = "分析 PDF";
      btn.disabled = true;
    }
  },

  resetPdfUpload() {
    this.selectedPdf = null;
    document.getElementById("wb-pdf-input").value = "";
    document.getElementById("wb-pdf-btn").disabled = true;
  },

  async manualAdd() {
    const kpStr = document.getElementById("wb-manual-kp").value.trim();
    const body = {
      subject: document.getElementById("wb-manual-subject").value,
      topic: document.getElementById("wb-manual-topic").value,
      question_text: document.getElementById("wb-manual-text").value,
      answer: document.getElementById("wb-manual-answer").value,
      knowledge_points: kpStr ? kpStr.split(/[,，]/).map(s => s.trim()).filter(Boolean) : [],
    };
    if (!body.question_text) { showToast("请输入题目内容"); return; }
    await api("/api/wrong-book", "POST", body);
    showToast("已添加");
    document.getElementById("wb-manual-topic").value = "";
    document.getElementById("wb-manual-text").value = "";
    document.getElementById("wb-manual-answer").value = "";
    document.getElementById("wb-manual-kp").value = "";
    this.loadReviewBadge();
  },

  // ---- List ----

  async loadList(page) {
    if (page) this.currentPage = page;
    const subject = document.getElementById("wb-filter-subject").value;
    let url = `/api/wrong-book?page=${this.currentPage}&page_size=10`;
    if (subject) url += `&subject=${encodeURIComponent(subject)}`;

    const data = await api(url);
    const container = document.getElementById("wb-question-list");
    container.innerHTML = "";

    if (!data.questions || data.questions.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:2rem">暂无错题</div>';
      document.getElementById("wb-pagination").innerHTML = "";
      return;
    }

    data.questions.forEach(q => {
      const masteryPct = Math.round(q.mastery_level / 5 * 100);
      const masteryCls = q.mastery_level <= 1 ? "low" : q.mastery_level <= 3 ? "mid" : "high";
      const text = q.question_text.length > 80 ? q.question_text.slice(0, 80) + "..." : q.question_text;
      const item = document.createElement("div");
      item.className = "wb-item";
      item.onclick = () => this.showDetail(q.id);
      item.innerHTML = `
        <div class="wb-header">
          <span class="task-subject">${q.subject || "—"}</span>
          <span style="font-size:0.75rem;color:var(--text-dim)">${q.topic || ""}</span>
        </div>
        <div class="wb-text">${text}</div>
        <div class="wb-footer">
          ${q.knowledge_points.slice(0, 3).map(kp => `<span class="kp-tag">${kp}</span>`).join("")}
          <span style="margin-left:auto;font-size:0.75rem;color:var(--text-dim)">
            掌握度 <div class="mastery-bar"><div class="mastery-bar-fill ${masteryCls}" style="width:${masteryPct}%"></div></div> ${q.mastery_level}/5
          </span>
        </div>
      `;
      container.appendChild(item);
    });

    // Pagination
    const totalPages = Math.ceil(data.total / data.page_size);
    const pagDiv = document.getElementById("wb-pagination");
    pagDiv.innerHTML = "";
    for (let i = 1; i <= totalPages && i <= 10; i++) {
      const btn = document.createElement("button");
      btn.textContent = i;
      btn.className = i === this.currentPage ? "active" : "";
      btn.onclick = () => this.loadList(i);
      pagDiv.appendChild(btn);
    }
  },

  async showDetail(id) {
    const data = await api(`/api/wrong-book/${id}`);
    if (data.error) { showToast("加载失败"); return; }
    const q = data.question;
    const masteryPct = Math.round(q.mastery_level / 5 * 100);
    const masteryCls = q.mastery_level <= 1 ? "low" : q.mastery_level <= 3 ? "mid" : "high";

    // Use a simple overlay for detail view
    let overlay = document.getElementById("wb-detail-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "wb-detail-overlay";
      overlay.className = "modal-overlay";
      document.body.appendChild(overlay);
    }
    overlay.style.display = "flex";
    overlay.innerHTML = `
      <div class="modal modal-large">
        <h3>${q.subject} · ${q.topic || "—"}</h3>
        <div style="margin:1rem 0;font-size:0.9rem;line-height:1.8">${q.question_text}</div>
        <div style="margin:0.8rem 0;padding:0.8rem;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent);font-size:0.85rem;line-height:1.6">${q.answer || "暂无解析"}</div>
        <div style="margin:0.5rem 0">
          ${q.knowledge_points.map(kp => `<span class="kp-tag">${kp}</span>`).join(" ")}
        </div>
        <div style="margin:0.5rem 0;font-size:0.85rem;color:var(--text-dim)">
          难度：${q.difficulty}/5 · 来源：${q.source || "—"} · 复习${q.review_count}次 · 掌握度 ${q.mastery_level}/5
          <div class="mastery-bar" style="width:80px"><div class="mastery-bar-fill ${masteryCls}" style="width:${masteryPct}%"></div></div>
        </div>
        ${q.next_review_date ? `<div style="font-size:0.8rem;color:var(--text-dim)">下次复习：${q.next_review_date}</div>` : ""}
        <div class="modal-actions" style="margin-top:1rem">
          <button class="btn btn-ghost" onclick="document.getElementById('wb-detail-overlay').style.display='none'">关闭</button>
          <button class="btn btn-ghost" style="color:var(--red)" onclick="WrongBook.deleteQuestion('${q.id}')">删除</button>
        </div>
      </div>
    `;
  },

  async deleteQuestion(id) {
    if (!confirm("确定删除此错题？")) return;
    await api(`/api/wrong-book/${id}`, "DELETE");
    showToast("已删除");
    document.getElementById("wb-detail-overlay").style.display = "none";
    this.loadList();
  },

  // ---- Review ----

  async loadReviewBadge() {
    const data = await api("/api/wrong-book/review/today");
    const badge = document.getElementById("wb-review-badge");
    badge.textContent = data.count || 0;
    badge.style.display = data.count > 0 ? "inline" : "none";
  },

  async loadReview(useAgent) {
    const budgetEl = document.getElementById("wb-review-budget");
    const budget = parseInt((budgetEl && budgetEl.value) || "40", 10);
    let data;
    if (useAgent) {
      data = await api("/api/wrong-book/review/agent-pick", "POST", { budget });
    } else {
      data = await api(`/api/wrong-book/review/pick?budget=${budget}`);
    }
    const container = document.getElementById("wb-review-cards");
    container.innerHTML = "";

    const items = data.items || [];
    if (items.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:2rem;font-size:0.9rem">🎉 暂无可复查的错题</div>';
      return;
    }

    // Show curation source/rationale when the agent path was used.
    if (data.source) {
      const note = document.createElement("div");
      note.style.cssText = "font-size:0.8rem;color:var(--text-dim);margin-bottom:0.6rem";
      note.textContent = `来源：${data.source}${data.rationale ? " · " + data.rationale : ""}`;
      container.appendChild(note);
    }

    items.forEach(it => {
      const q = it.question;
      const card = document.createElement("div");
      card.className = "review-card";
      card.id = `rc-${q.id}`;
      const kps = (q.knowledge_points || []).map(kp => `<span class="kp-tag">${kp}</span>`).join(" ");
      const kpPct = Math.round((it.kp_mastery ?? 0) * 100);
      const meta = [
        `掌握度 ${kpPct}%`,
        it.due ? "到期" : "未到期",
        `紧急度 ${(it.score ?? 0).toFixed(2)}`,
      ].join(" · ");
      card.innerHTML = `
        <div class="rc-text">${q.question_text}</div>
        <div style="font-size:0.75rem;color:var(--text-dim);margin:0.3rem 0">${meta}</div>
        <button class="reveal-btn" onclick="this.nextElementSibling.classList.toggle('visible')">显示解析</button>
        <div class="rc-answer">${q.answer || "暂无解析"}</div>
        <div style="margin:0.5rem 0">
          ${kps}
        </div>
        <div class="rc-actions">
          <button class="review-btn mastered" onclick="WrongBook.submitReview('${q.id}','mastered')">✓ 掌握了</button>
          <button class="review-btn familiar" onclick="WrongBook.submitReview('${q.id}','familiar')">有点熟</button>
          <button class="review-btn unfamiliar" onclick="WrongBook.submitReview('${q.id}','unfamiliar')">不熟悉</button>
          <button class="review-btn forgot" onclick="WrongBook.submitReview('${q.id}','forgot')">忘记了</button>
        </div>
      `;
      container.appendChild(card);
    });
  },

  async submitReview(qid, result) {
    await api(`/api/wrong-book/${qid}/review`, "POST", { result });
    const card = document.getElementById(`rc-${qid}`);
    if (card) {
      card.style.opacity = "0.3";
      card.style.pointerEvents = "none";
    }
    this.loadReviewBadge();
    showToast("已记录复习结果");
  },

  // ---- Stats ----

  async loadStats() {
    const data = await api("/api/wrong-book/stats");
    const container = document.getElementById("wb-stats-content");
    container.innerHTML = "";

    if (data.total === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:2rem;font-size:0.9rem">暂无统计数据</div>';
      return;
    }

    // Level distribution
    const labels = ["未复习", "初识", "了解", "熟悉", "掌握", "精通"];
    const levels = data.level_distribution || [0,0,0,0,0,0];
    const distDiv = document.createElement("div");
    distDiv.innerHTML = `<h3 style="font-size:0.9rem;margin-bottom:0.5rem">掌握度分布（共${data.total}题）</h3>`;
    levels.forEach((count, i) => {
      if (count === 0) return;
      const pct = Math.round(count / data.total * 100);
      const row = document.createElement("div");
      row.className = "stat-row";
      row.innerHTML = `
        <span class="sr-label">${labels[i]}</span>
        <div class="sr-bar"><div style="width:${pct}%;height:100%;background:var(--accent);border-radius:4px"></div></div>
        <span class="sr-value">${count}题 (${pct}%)</span>
      `;
      distDiv.appendChild(row);
    });
    container.appendChild(distDiv);

    // Knowledge point stats
    const kpStats = data.knowledge_points || {};
    const kpEntries = Object.entries(kpStats).sort((a, b) => a[1].avg_mastery - b[1].avg_mastery);
    if (kpEntries.length > 0) {
      const kpDiv = document.createElement("div");
      kpDiv.innerHTML = `<h3 style="font-size:0.9rem;margin:1rem 0 0.5rem">知识点薄弱度排行</h3>`;
      kpEntries.slice(0, 15).forEach(([kp, info]) => {
        const pct = Math.round(info.avg_mastery / 5 * 100);
        const cls = info.avg_mastery <= 1 ? "var(--red)" : info.avg_mastery <= 3 ? "var(--yellow)" : "var(--green)";
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `
          <span class="sr-label">${kp} (${info.count}题)</span>
          <div class="sr-bar"><div style="width:${pct}%;height:100%;background:${cls};border-radius:4px"></div></div>
          <span class="sr-value">${info.avg_mastery}/5</span>
        `;
        kpDiv.appendChild(row);
      });
      container.appendChild(kpDiv);
    }

    // Subject breakdown
    const subjects = data.subjects || {};
    if (Object.keys(subjects).length > 0) {
      const subDiv = document.createElement("div");
      subDiv.innerHTML = `<h3 style="font-size:0.9rem;margin:1rem 0 0.5rem">科目分布</h3>`;
      Object.entries(subjects).forEach(([sub, info]) => {
        const pct = info.total > 0 ? Math.round(info.mastered / info.total * 100) : 0;
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `
          <span class="sr-label">${sub}</span>
          <div class="sr-bar"><div style="width:${pct}%;height:100%;background:var(--green);border-radius:4px"></div></div>
          <span class="sr-value">${info.mastered}/${info.total}</span>
        `;
        subDiv.appendChild(row);
      });
      container.appendChild(subDiv);
    }
  },
};
