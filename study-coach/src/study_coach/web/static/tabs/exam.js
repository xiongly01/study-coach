/* study-coach — Exam tab: question bank and self-testing */

const Exam = {
  testQuestions: [],
  testIndex: 0,
  testSubject: "",

  async load() {
    this.loadQuestions();
    this.loadResults();
  },

  // ---- Question Bank ----

  async loadQuestions() {
    const subject = document.getElementById("exam-subject-filter").value;
    const data = await api(`/api/questions${subject ? "?subject=" + encodeURIComponent(subject) : ""}`);
    const list = document.getElementById("exam-question-list");
    list.innerHTML = "";
    if (!data.questions || data.questions.length === 0) {
      list.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:1.5rem">暂无题目，点击"添加题目"开始</div>';
      return;
    }
    data.questions.forEach(q => {
      const item = document.createElement("div");
      item.className = "question-item";
      item.innerHTML = `
        <div class="q-header">
          <span class="task-subject">${q.subject}</span>
          <span style="font-size:0.75rem;color:var(--text-dim)">难度 ${"★".repeat(q.difficulty)}${"☆".repeat(5-q.difficulty)}</span>
        </div>
        <div class="q-text">${q.question_text}</div>
        <div class="q-meta">${q.topic ? q.topic + " · " : ""}ID: ${q.id}</div>
      `;
      list.appendChild(item);
    });
  },

  showAddForm() { document.getElementById("exam-add-form").style.display = "flex"; },
  hideAddForm() { document.getElementById("exam-add-form").style.display = "none"; },

  async submitQuestion() {
    const body = {
      subject: document.getElementById("qf-subject").value,
      topic: document.getElementById("qf-topic").value,
      question_text: document.getElementById("qf-text").value,
      answer: document.getElementById("qf-answer").value,
      difficulty: parseInt(document.getElementById("qf-difficulty").value),
    };
    if (!body.question_text) { showToast("请输入题目内容"); return; }
    await api("/api/questions", "POST", body);
    showToast("题目已添加");
    this.hideAddForm();
    document.getElementById("qf-topic").value = "";
    document.getElementById("qf-text").value = "";
    document.getElementById("qf-answer").value = "";
    this.loadQuestions();
  },

  // ---- Self-Test ----

  async startTest() {
    const subject = document.getElementById("exam-subject-filter").value;
    if (!subject) { showToast("请先选择一个科目"); return; }
    this.testSubject = subject;
    const data = await api("/api/test/start", "POST", { subject, count: 5 });
    if (!data.questions || data.questions.length === 0) {
      showToast("该科目暂无题目");
      return;
    }
    this.testQuestions = data.questions;
    this.testIndex = 0;
    document.getElementById("exam-test-session").style.display = "flex";
    this.renderTestQuestion();
  },

  renderTestQuestion() {
    const q = this.testQuestions[this.testIndex];
    const total = this.testQuestions.length;
    document.getElementById("test-progress").textContent = `(${this.testIndex + 1}/${total})`;
    const card = document.getElementById("test-question-card");
    card.innerHTML = `
      <div class="test-card">
        <div class="test-q">${q.question_text}</div>
        <button class="reveal-btn" onclick="this.nextElementSibling.classList.toggle('visible')">显示答案</button>
        <div class="answer-reveal">${q.answer || "暂无解析"}</div>
        <div style="margin-top:0.8rem;font-size:0.85rem;color:var(--text-dim)">
          主题：${q.topic || "—"} · 难度：${q.difficulty}
        </div>
      </div>
    `;
    document.getElementById("test-next-btn").style.display =
      this.testIndex < total - 1 ? "inline-block" : "none";
    document.getElementById("test-finish-btn").style.display =
      this.testIndex === total - 1 ? "inline-block" : "none";
  },

  nextTestQuestion() {
    this.testIndex++;
    if (this.testIndex < this.testQuestions.length) this.renderTestQuestion();
  },

  async finishTest() {
    // Simple: count questions where user toggled "reveal" as self-assessed
    const total = this.testQuestions.length;
    const score = prompt(`自测结束，共${total}题。你答对了多少题？(0-${total})`);
    const correct = Math.min(Math.max(parseInt(score) || 0, 0), total);
    await api("/api/test/submit", "POST", {
      subject: this.testSubject,
      total_questions: total,
      correct: correct,
    });
    document.getElementById("exam-test-session").style.display = "none";
    showToast(`自测完成：${correct}/${total} (${Math.round(correct/total*100)}%)`);
    this.loadResults();
  },

  // ---- Results ----

  async loadResults() {
    const data = await api("/api/test/results");
    const container = document.getElementById("exam-results");
    container.innerHTML = "";
    if (!data.results || data.results.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;text-align:center;padding:1.5rem">暂无测试记录</div>';
      return;
    }
    data.results.reverse().slice(0, 20).forEach(r => {
      const pct = r.total_questions > 0 ? Math.round(r.correct / r.total_questions * 100) : 0;
      const cls = pct >= 80 ? "high" : "low";
      const item = document.createElement("div");
      item.className = "result-item";
      item.innerHTML = `
        <div>
          <span class="task-subject">${r.subject}</span>
          <span style="font-size:0.8rem;color:var(--text-dim);margin-left:0.5rem">${r.date}</span>
          <span style="font-size:0.8rem;color:var(--text-dim);margin-left:0.5rem">${r.correct}/${r.total_questions}</span>
        </div>
        <span class="result-score ${cls}">${pct}%</span>
      `;
      container.appendChild(item);
    });
  },
};
