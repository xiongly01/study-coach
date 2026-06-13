# Learning Methodology Reference

This document is the methodology reference for the plan-generation engine. When generating or adjusting daily, weekly, or yearly plans, the system must follow the principles and rules defined here.

---

## 1. Knowledge Cognition Foundation — DIKW Model

Before building any knowledge system, understand what "knowledge" means at each cognitive level. The DIKW model defines four layers:

| Layer | Definition | Key question | Example (Calculus) |
|-------|-----------|--------------|---------------------|
| **Data** | Raw, unprocessed symbols and observations | "What are the facts?" | The formula `∫x²dx = x³/3 + C` |
| **Information** | Data organized into structured, meaningful patterns | "What does it mean?" | "This formula computes the area under the curve y=x²" |
| **Knowledge** | Actionable information — procedures, techniques, connections | "How do I use it?" | "To find area under a polynomial, integrate term by term; check boundaries at endpoints" |
| **Wisdom** | Meta-ability to select and combine knowledge for decision-making | "When and why?" | "This integral is a area problem → but the integrand is negative on [a,b], so I must split the interval and take absolute values" |

**Implication for plan generation**: each study session must specify which DIKW layer it targets. A session stuck at Data/Information level (reading, recognizing) will not produce exam-solving ability. Plan must push knowledge nodes toward Knowledge and Wisdom levels through deliberate practice.

---

## 2. Subject Taxonomy

Subjects are classified into four types. Each type has a distinct knowledge structure and learning strategy.

| Type | Structure | Example | Core verb |
|------|-----------|---------|-----------|
| Mathematical | Axiomatic tree — definitions, theorems, proof chains, techniques | Calculus, Linear Algebra | Derive |
| Language | Layered network — vocabulary, grammar patterns, discourse structures | English, Chinese | Use |
| Factual | Hierarchical taxonomy — concepts, categories, relationships, exceptions | Political theory, Law | Classify & recall |
| Engineering | Layered architecture — components, interfaces, protocols, trade-offs | Data Structures, OS, Networks | Decompose & compose |

For any new subject, first identify its type. If it spans multiple types, decompose it by chapter or unit and classify each part independently.

---

## 3. Knowledge System Construction

### 3.1 Core Principle: Bottom-Up Emergence over Top-Down Classification

The Zettelkasten method's central insight: **do not start with a preset topic hierarchy**. Instead, let the knowledge structure emerge organically from the content itself and the connections between individual knowledge units.

Why: a top-down hierarchy forces each concept into a single category, blurring its edges and hiding cross-cutting relationships. A bottom-up network allows the same concept to participate in multiple emergent groupings simultaneously — which is exactly how exams test knowledge (a single problem may combine concepts from different chapters).

**Practical implication**: when a student begins a new subject, do not give them a pre-built outline to "fill in". Instead, have them create individual knowledge units (one concept each) and let them discover the structure by forming links. The outline crystallizes later, as a summary of what emerged — not as a template imposed in advance.

### 3.2 Knowledge Units: Atomic and Self-Contained

Each knowledge unit follows the atomic principle:

- **One concept per unit**: a unit contains exactly one idea, definition, theorem, or technique. If you cannot state it in one sentence, it is too broad — split it.
- **Self-contained**: reading the unit alone (without context) should be sufficient to understand the concept. Write in your own words — never copy-paste. The act of rewriting forces understanding.
- **Linkable**: each unit has explicit connections to other units. These links are the primary value — not the units themselves.

Unit types:
| Type | Content | Example |
|------|---------|---------|
| Concept | A definition or idea with its boundaries | "Continuous function: f(x₀) = lim f(x) as x→x₀" |
| Procedure | A step-by-step technique | "Integration by parts: choose u and dv, apply ∫udv = uv - ∫vdu" |
| Evidence | A proof, derivation, or justification | "Proof of the Fundamental Theorem of Calculus" |
| Example | A canonical problem that illustrates a concept or procedure | "Find the area between y=x² and y=2x" |
| Pattern | A recurring structure observed across multiple units | "The 'split the interval' pattern: when the function changes sign" |

### 3.3 Three-Phase Construction Process

**Phase A — Capture: Collect raw knowledge units.**

During first exposure (reading, lecture), create one unit per new concept encountered. Do not organize or classify yet. Focus on:
- Accurate definition or statement (in own words).
- Source reference (textbook page, lecture timestamp).
- Initial links to any previously captured unit that comes to mind.

The output is a flat collection of units — no hierarchy, no folders, no tags beyond the subject name.

**Phase B — Elaborate: Deepen each unit and discover links.**

After the initial capture pass, revisit each unit:
- Add: one canonical example, common edge case, or application.
- Identify: prerequisite links ("must know X before Y") and cross-reference links ("X is analogous to Z").
- If a unit feels incomplete, do targeted study to fill the gap — do not leave it vague.

The key question at this stage is not "where does this unit belong?" but **"in which context would I want to encounter this unit again?"** This shifts thinking from filing to retrieval, and produces links that match how memory actually works.

**Phase C — Crystallize: Let structure emerge from the network.**

After sufficient units exist (typically after completing a chapter or topic area):
- Look for clusters of densely connected units — these are natural topic boundaries.
- Create **structure notes**: summary notes that link to all units in a cluster and describe the relationship between them. Structure notes are emergent outlines — they are built from the bottom up, discovered rather than designed.
- Reassess depth markers based on what the network reveals about which concepts are central (highly connected) vs. peripheral (sparsely connected).

### 3.4 Depth Markers

Not all units deserve the same depth. Use this classification to allocate effort:

| Marker | Meaning | Study behavior |
|--------|---------|----------------|
| Core | High-frequency, high-weight on exam | Full capture + elaborate + crystallize + drill |
| Supporting | Appears often but low individual weight | Capture + elaborate + one-direction links |
| Peripheral | Rare or low weight | Capture only; elaborate on demand |

Assign markers during the crystallize phase. Re-assess after each mock exam or self-test based on actual frequency and error rate.

---

## 4. Six-Step Knowledge Management Workflow

The complete knowledge management process operates in six sequential steps. Each step has a clear input, output, and quality gate. When generating plans, ensure every study activity maps to one of these steps.

### Step 1 — Define Target

**Input**: exam syllabus, past papers, personal baseline.
**Output**: a prioritized list of knowledge areas with target mastery levels.

- Identify the exam's high-frequency topics and their DIKW depth requirements.
- Assess current mastery baseline for each area (see Section 6).
- Set concrete, measurable targets: "reach level 4 (Proficient) on integration techniques by [date]."
- Target setting is the prerequisite for all subsequent steps — without it, study becomes directionless consumption.

### Step 2 — Input

**Input**: textbooks, lectures, practice problems, reference materials.
**Output**: raw knowledge units (capture phase).

- One session, one source, one topic area. Avoid mixing sources within a session.
- Create atomic units during or immediately after input — not "later."
- Rate input quality: was this source clear? Did it create more questions than answers? Flag gaps for targeted re-input.

### Step 3 — Internalize

**Input**: raw knowledge units from Step 2.
**Output**: elaborated units with links (elaborate phase).

- Active recall: close the source material and reproduce the unit from memory.
- Self-explanation: explain the concept aloud as if teaching someone. If you stumble, the unit is not yet internalized.
- Form links: for each unit, identify at least one connection to a previously internalized unit.
- Practice: solve 3-5 basic problems that use this unit without reference.

### Step 4 — Output

**Input**: internalized knowledge.
**Output**: produced work — problem solutions, written explanations, structure notes.

- Output is the proof of internalization. If you cannot produce, you have not internalized.
- Output forms: solving problem sets, writing summary notes, creating structure notes, teaching a peer.
- Every study session should end with at least one output artifact.

### Step 5 — Apply

**Input**: output artifacts and practice results.
**Output**: exam-relevant performance data (scores, error patterns, timing).

- Apply knowledge under exam conditions: timed, no references, full problem sets.
- Application reveals gaps that practice alone does not — the difference between "I understand" and "I can solve under pressure."
- Record all results: scores, time per problem, error classifications.

### Step 6 — Review & Iterate

**Input**: performance data from Step 5.
**Output**: updated mastery levels, revised targets, adjusted plans.

- Compare actual performance against targets from Step 1.
- Classify every error (see Section 7).
- Update mastery levels for affected knowledge units.
- Identify systemic patterns (not just isolated mistakes).
- Feed results back into Step 1: revise targets, re-prioritize areas, adjust the plan.

This six-step cycle operates at multiple granularities:
- **Within a session**: the 3-part structure (review → new → consolidate) is a micro-cycle of input → internalize → output.
- **Within a week**: weekly review runs the full cycle at topic level.
- **Within a milestone**: the milestone transition check runs the full cycle at subject level.

---

## 5. Phase-Based Learning Strategy

### 5.1 Phase Definitions

| Phase | Goal | Knowledge focus | Primary workflow steps | Output standard |
|-------|------|-----------------|----------------------|-----------------|
| Foundation | Build the knowledge unit collection | Every topic touched once | Step 1 → Step 2 → Step 3 (capture + elaborate) | Can reproduce the network structure; can solve basic problems for each unit |
| Reinforcement | Deepen units + crystallize structure + identify weak spots | Focus on Core units; crystallize all clusters | Step 3 → Step 4 → Step 5 (elaborate + output + apply) | Can solve medium-difficulty problems without hints; weak topics identified |
| Sprint | Maximize exam score under time pressure | Core only; patch remaining weak spots | Step 5 → Step 6 (apply + review) | Can complete a full mock exam within time limit at target accuracy |

### 5.2 Per-Phase Subject Behavior

**Foundation phase:**

- Mathematical: read theory → work through textbook examples → do 10-15 exercises per section. Do not skip proofs; understanding the proof is how you learn the technique.
- Language: learn vocabulary in context (not isolated lists) → study one grammar pattern per session → read one passage and analyze structure.
- Factual: read source material → capture knowledge units → add one mnemonic or example per concept.
- Engineering: understand the layer architecture → trace one complete request/operation through all layers → summarize each component's responsibility and interface.

**Reinforcement phase:**

- Mathematical: topic-based problem sets (not chapter-based) → collect techniques that appear across chapters → crystallize structure notes for each technique cluster.
- Language: timed reading practice → writing with targeted feedback → error pattern analysis on past practice.
- Factual: active recall from the network (not re-reading source) → fill gaps revealed by self-testing → connect concepts across clusters.
- Engineering: comparative analysis ("how does concept A differ from B?") → trace cross-layer interactions → practice "explain in your own words" for every Core unit.

**Sprint phase:**

- All types: full mock exams under real conditions → analyze every wrong answer → targeted drill on recurring weak patterns. No new material unless a gap is critical and small.

### 5.3 Phase Transition Criteria

Do not transition to the next phase by calendar alone. Verify:

| Transition | Must achieve |
|------------|-------------|
| Foundation → Reinforcement | ≥ 80% of syllabus topics have captured units; basic-problem accuracy ≥ 70% |
| Reinforcement → Sprint | Medium-problem accuracy ≥ 65%; weak-topic list is ≤ 20% of total units |
| Sprint → Exam | Mock exam score at or above target for 2 consecutive mocks |

If criteria are not met by the planned transition date, re-plan: compress the current phase for non-core topics, or adjust the milestone deadline.

---

## 6. Mastery Assessment

### 6.1 Mastery Levels

For every knowledge unit, track a mastery level aligned with the DIKW layers:

| Level | Name | DIKW layer | Behavior | How to verify |
|-------|------|-----------|----------|---------------|
| 0 | Unseen | — | No exposure | N/A |
| 1 | Exposed | Data | Has encountered the raw fact or formula | Can recognize it in a multiple-choice question |
| 2 | Informed | Information | Can explain what it means in own words | Can write a correct definition from memory |
| 3 | Knowledgeable | Knowledge | Can apply it to solve standard problems | Can solve a basic exercise without reference |
| 4 | Proficient | Knowledge+ | Can solve variations and combined problems | Can adapt technique to unfamiliar problem |
| 5 | Wise | Wisdom | Can select, combine, and teach; can spot the technique embedded in complex problems | Can explain to someone else; can solve under time pressure; can choose the right approach when multiple are available |

### 6.2 Level Promotion Rules

- Level 0 → 1: one exposure (read or lecture) — captures a raw data point.
- Level 1 → 2: rewrite in own words + self-explanation within 24 hours — transforms data into information.
- Level 2 → 3: 5-10 practice problems without reference — builds actionable knowledge.
- Level 3 → 4: exposure to variations; at least one problem that combines this concept with another — deepens knowledge.
- Level 4 → 5: successful application under timed mock conditions + teaching or explaining to someone — achieves wisdom-level judgment.

Relegation: if a wrong answer on a topic at level 4+ is due to a conceptual gap (not a careless error), drop one level and re-do the promotion requirements.

### 6.3 Using Mastery in Plan Generation

When generating daily tasks:
- Units at level 0-1: schedule as "new content" blocks (Step 2: Input).
- Units at level 2: schedule as "internalize" blocks (Step 3: Internalize).
- Units at level 3: schedule as "output" blocks or include in mixed problem sets (Step 4: Output).
- Units at level 4-5: only include in spaced-repetition review; no dedicated block needed.

When a subject has > 60% of units at level 3+, that subject is ready to enter Reinforcement phase for new content, even if other subjects are still in Foundation.

---

## 7. Error Analysis Method

When a wrong answer is recorded:

### 7.1 Error Classification

| Type | Root cause | DIKW gap |
|------|-----------|----------|
| Knowledge gap | The concept was not known or misunderstood | Data/Information level not reached |
| Technique gap | The concept was known but the solution method was wrong or incomplete | Knowledge level not reached |
| Strategic gap | The correct approach was available but not selected | Wisdom level not reached |
| Careless error | Correct knowledge and approach, but execution failed | Not a knowledge gap — process failure |

### 7.2 Action per Classification

- **Knowledge gap** → re-learn the unit from source material; set mastery to level 1; schedule the full promotion path (1 → 2 → 3).
- **Technique gap** → add 3-5 targeted exercises of the same type; schedule within 3 days.
- **Strategic gap** → practice approach selection: given 5 problems, choose the method without solving; compare with optimal. This builds Wisdom-level judgment.
- **Careless error** → flag for attention; if same type of carelessness appears 3+ times, create a checklist rule (e.g., "always check units before submitting").

### 7.3 Pattern Detection

After every 20 wrong answers, check for recurring patterns:
- Same topic cluster → the underlying unit needs re-learning, not just practice.
- Same error type across topics → systemic issue (e.g., poor time management, skipping steps).
- Same difficulty range failing → the difficulty jump may be too steep; insert intermediate problems.

---

## 8. Plan Generation Rules

### 8.1 Time Allocation Principles

**Across subjects — the 40-30-20-10 rule as starting point:**

| Category | Default weight | Rationale |
|----------|---------------|-----------|
| Heaviest subject (largest syllabus, deepest DIKW requirement) | 40% | Needs the most units and the deepest elaboration |
| Second heaviest | 30% | Large syllabus, moderate depth |
| Third | 20% | Moderate syllabus, or high-efficiency methods available |
| Fourth | 10% | Memorization-heavy, benefits from shorter but consistent sessions |

Adjust weights based on:
- Current mastery gap (distance between current level and target level across all units).
- Time efficiency per subject (some subjects yield more mastery-level promotions per hour).
- Proximity to exam (shift toward weaker subjects and mock practice in later phases).

**Within a subject session — the 3-part structure (micro workflow cycle):**

1. **Review** (15-20% of session time): recall units from previous session on this subject. Active recall, not re-reading. Check spaced-repetition items due today.
2. **New content** (50-60%): learn or practice the day's scheduled topic. Map to workflow Step 2 (input) or Step 3 (internalize) depending on phase.
3. **Consolidation** (20-30%): summarize, create links, or do practice problems. This is Step 4 (output). End with a one-sentence note on what to focus on next time.

### 8.2 Daily Plan Structure

Each daily plan must contain:

1. **Carry-over review** (first 30 minutes): review yesterday's notes, check spaced-repetition items due today. This is Step 6 (review) feeding into today's Step 1 (targets).
2. **Subject blocks**: 2-3 subjects per day. Each subject gets one contiguous block (avoid context-switching within a block). Block length: 90-150 minutes.
3. **Flexible buffer** (10% of total time): for unexpected overflows or spontaneous weak-topic drills.
4. **End-of-day reflection** (5-10 minutes): answer three questions:
   - What did I complete vs. plan?
   - Which knowledge unit felt hardest and why?
   - What should tomorrow prioritize?

Subject block ordering rules:
- Put the hardest or most important subject in the first block (when mental energy is highest).
- Separate two blocks of the same type (e.g., two mathematical blocks) with a different-type block.
- In Sprint phase, alternate between full-mock sessions (Step 5: Apply) and targeted-review sessions (Step 6: Review).

### 8.3 Weekly Plan Structure

A weekly plan is not seven daily plans glued together. It adds a coordination layer:

1. **Weekly goal**: 1-3 measurable outcomes, each tied to specific knowledge units and target mastery levels (e.g., "capture all units for Chapter 5", "promote integration technique units to level 3", "one full mock exam per subject").
2. **Progress checkpoints**: mid-week (Day 3 or 4) — compare actual progress vs. weekly goal. If behind, adjust Days 5-7.
3. **Weekly review session** (last session of the week):
   - Check which weekly goals were met.
   - Analyze wrong-answer patterns accumulated this week (Section 7.3).
   - Update depth markers (Section 3.4) based on new evidence from the knowledge network.
   - Adjust next week's time allocation if needed.
   - Feed results into next week's Step 1 (Define Target).

### 8.4 Yearly / Milestone Plan Structure

Long-term plans operate on milestones, not fixed schedules. Each milestone has:

- A scope (which subjects, which chapters or units).
- A deadline.
- Completion criteria (Section 5.3).

Milestone planning rules:

1. **Backward from exam date**: the Sprint milestone ends at exam minus 5 days. Allocate 4-6 weeks for Sprint. The rest is Foundation + Reinforcement.
2. **Foundation first, heavier subjects first**: start Foundation with the heaviest subject; overlap Foundation for later subjects with Reinforcement for earlier ones.
3. **Buffer weeks**: insert one buffer week between major milestones. Buffers absorb slippage; if no slippage, use buffers for concentrated crystallization (Phase C) and weak-topic review.
4. **Reassessment points**: at each milestone deadline, run a diagnostic self-test. Results determine whether to advance, compress, or extend.

### 8.5 Review Scheduling

Spaced repetition is mandatory for all factual and definitional knowledge. Use these intervals:

| Review number | Delay from last review |
|---------------|----------------------|
| 1st | 1 day |
| 2nd | 3 days |
| 3rd | 7 days |
| 4th | 14 days |
| 5th | 30 days |

After the 5th successful review, the unit is considered stable at its current mastery level. If a review fails (unit forgotten or answered wrong), reset to review #1.

Review sessions should be scheduled as part of the daily "carry-over review" block, not as separate sessions. Estimate 5-10 units per minute of review time when scheduling.

### 8.6 Plan Adjustment Triggers

The system must detect these signals and adjust the plan accordingly:

| Signal | Source | Adjustment |
|--------|--------|------------|
| Task completion rate < 60% for 3+ days | Daily tracking | Reduce daily scope; redistribute time across subjects |
| Same unit appears in wrong-answer notebook 2+ times | Wrong-answer data | Schedule a focused re-learn session (Step 2 → Step 3), not just review |
| Milestone deadline within 7 days and < 70% scope covered | Milestone tracking | Compress non-core topics; focus only on Core units |
| Weekly goal achievement < 50% for 2+ weeks | Weekly review | Re-assess time estimates; consider reducing total scope or adjusting targets |
| Mock exam score drops vs. previous | Test results | Analyze which phase-transition assumption was wrong; step back if needed |
| Knowledge network shows isolated clusters with no cross-links | Network analysis | Schedule a crystallization session (Phase C) to bridge disconnected areas |

---

## 9. Summary of Plan Generation Checklist

When the system generates or adjusts any plan, it must have considered:

- [ ] Subject classification and appropriate strategy selected.
- [ ] DIKW layer targeted by each activity is explicit.
- [ ] Phase-appropriate activities (Foundation / Reinforcement / Sprint) and construction phases (Capture / Elaborate / Crystallize) are aligned.
- [ ] Time allocation follows the weighting principle, adjusted by mastery gaps.
- [ ] Each session follows the 3-part structure (review → new → consolidate).
- [ ] Spaced-repetition units due today are scheduled in carry-over review.
- [ ] Knowledge units are atomic and self-contained; links are being formed.
- [ ] Buffer time is included.
- [ ] Adjustment triggers have been checked.
- [ ] Mastery levels are up to date based on latest practice and test results.
- [ ] Weekly and milestone plans have measurable goals and completion criteria.
- [ ] The six-step workflow (target → input → internalize → output → apply → review) is visible in the plan structure.
