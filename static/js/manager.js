const MANAGER_ACCOUNT_FIELDS = [
  { key: "full_name", label: "Full name", type: "text" },
  { key: "age", label: "Age", type: "number" },
  { key: "gender", label: "Gender", type: "select", options: ["female", "male"] },
  { key: "phone", label: "Phone", type: "text" },
  { key: "email", label: "Email", type: "email" },
];

let currentUser = null;
let editing = false;
let currencyChart = null, segmentChart = null, loansChart = null, signupsChart = null;
let lastCurrencyHistory = null, lastDashboardData = null;

function friendly(s) { return (s || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }

function statusChip(status) {
  const map = {
    pending: ["chip-warning", "Pending"], approved: ["chip-success", "Approved"], rejected: ["chip-danger", "Declined"],
    pending_review: ["chip-warning", "Under review"], manager_approved: ["chip-success", "Cleared"],
    manager_rejected: ["chip-danger", "Blocked"],
  };
  const [cls, text] = map[status] || ["chip-neutral", status];
  return `<span class="chip ${cls}">${text}</span>`;
}

// ---------------- ACCOUNT ----------------
function renderAccountFields(user, editMode) {
  const wrap = document.getElementById("account-fields");
  wrap.innerHTML = "";
  MANAGER_ACCOUNT_FIELDS.forEach(f => {
    const box = document.createElement("div");
    box.className = "field";
    const label = document.createElement("label");
    label.textContent = f.label;
    box.appendChild(label);
    if (!editMode) {
      const val = document.createElement("div");
      val.style.padding = "11px 0"; val.style.fontWeight = "600";
      val.textContent = user[f.key] ?? "—";
      box.appendChild(val);
    } else if (f.type === "select") {
      const sel = document.createElement("select");
      sel.dataset.key = f.key;
      f.options.forEach(o => {
        const opt = document.createElement("option");
        opt.value = o; opt.textContent = friendly(o);
        if (user[f.key] === o) opt.selected = true;
        sel.appendChild(opt);
      });
      box.appendChild(sel);
    } else {
      const inp = document.createElement("input");
      inp.type = f.type; inp.dataset.key = f.key; inp.value = user[f.key] ?? "";
      box.appendChild(inp);
    }
    wrap.appendChild(box);
  });
}

async function loadAccount() {
  const { user } = await api.get("/api/account");
  currentUser = user;
  renderAccountFields(user, editing);
}

document.getElementById("edit-toggle").addEventListener("click", () => {
  editing = !editing;
  document.getElementById("edit-toggle").textContent = editing ? "Cancel" : "Edit";
  document.getElementById("account-save-row").style.display = editing ? "block" : "none";
  renderAccountFields(currentUser, editing);
});

document.getElementById("save-account").addEventListener("click", async () => {
  const payload = {};
  document.querySelectorAll("#account-fields [data-key]").forEach(el => { payload[el.dataset.key] = el.value; });
  const { user } = await api.put("/api/account", payload);
  currentUser = user; editing = false;
  document.getElementById("edit-toggle").textContent = "Edit";
  document.getElementById("account-save-row").style.display = "none";
  renderAccountFields(user, false);
  showToast("Profile updated.");
});

async function loadClientDirectory() {
  const { clients } = await api.get("/api/manager/clients");
  const wrap = document.getElementById("client-directory");
  wrap.innerHTML = clients.map(c => `
    <div class="list-row">
      <div>
        <div><strong>${c.full_name}</strong></div>
        <div class="meta">${c.account_number} · ${c.job || "—"}, ${c.state || "—"}</div>
      </div>
      <div class="row">
        <span class="amount">${money(c.balance)}</span>
        <span class="chip ${c.segment === "Premium Relationship" ? "chip-success" : "chip-neutral"}">${c.segment}</span>
      </div>
    </div>`).join("");
}

// ---------------- LOANS ----------------
async function loadManagerLoans() {
  const { loans } = await api.get("/api/manager/loans?status=pending");
  const wrap = document.getElementById("manager-loans");
  if (!loans.length) {
    wrap.innerHTML = `<div class="empty-state card"><div class="display">All caught up</div>No loan requests waiting on a decision.</div>`;
    return;
  }
  wrap.innerHTML = loans.map(l => `
    <div class="card" style="margin-bottom:14px;">
      <div class="spread" style="margin-bottom:10px;">
        <div>
          <strong>${l.full_name}</strong>
          <div class="meta muted" style="font-size:12.5px;">${l.account_number} · ${friendly(l.intent)} · requested ${money(l.amount)}</div>
        </div>
        <span class="chip ${l.model_recommend ? "chip-success" : "chip-danger"}">${l.model_recommend ? "Model: approve" : "Model: decline"}</span>
      </div>
      <div class="progress-track" style="margin-bottom:6px;"><div class="progress-fill" style="width:${l.model_probability}%;"></div></div>
      <div class="muted" style="font-size:12.5px; margin-bottom:10px;">${l.model_probability}% approval probability · credit score ${l.credit_score ?? "—"}</div>
      <ul class="reason-list" style="margin-bottom:14px;">${l.model_reasons.split("; ").map(r => `<li>${r}</li>`).join("")}</ul>
      <div class="row">
        <button class="btn btn-success btn-sm" data-approve="${l.id}">Approve</button>
        <button class="btn btn-danger btn-sm" data-reject="${l.id}">Decline</button>
      </div>
    </div>`).join("");

  wrap.querySelectorAll("[data-approve]").forEach(b => b.addEventListener("click", () => decideLoan(b.dataset.approve, true)));
  wrap.querySelectorAll("[data-reject]").forEach(b => b.addEventListener("click", () => decideLoan(b.dataset.reject, false)));
}

async function decideLoan(id, approve) {
  await api.post(`/api/manager/loans/${id}/decide`, { approve });
  showToast(approve ? "Loan approved and funded." : "Loan declined.");
  loadManagerLoans();
  refreshNotificationBadges();
}

// ---------------- FRAUD ----------------
async function loadManagerFraud() {
  const { transactions } = await api.get("/api/manager/fraud?status=pending_review");
  const wrap = document.getElementById("manager-fraud");
  if (!transactions.length) {
    wrap.innerHTML = `<div class="empty-state card"><div class="display">Nothing flagged</div>No suspicious transactions waiting on review.</div>`;
    return;
  }
  wrap.innerHTML = transactions.map(t => `
    <div class="card" style="margin-bottom:14px;">
      <div class="spread" style="margin-bottom:10px;">
        <div>
          <strong>${t.full_name}</strong>
          <div class="meta muted" style="font-size:12.5px;">${t.account_number} → ${t.receiver_account} · ${friendly(t.category)}</div>
        </div>
        <span class="chip chip-danger">${t.fraud_probability}% fraud probability</span>
      </div>
      <div class="amount" style="margin-bottom:8px;">${money(t.amount)}</div>
      <ul class="reason-list" style="margin-bottom:14px;">${t.fraud_reasons.split("; ").map(r => `<li>${r}</li>`).join("")}</ul>
      <div class="row">
        <button class="btn btn-success btn-sm" data-accept="${t.id}">Approve transaction</button>
        <button class="btn btn-danger btn-sm" data-block="${t.id}">Block</button>
      </div>
    </div>`).join("");

  wrap.querySelectorAll("[data-accept]").forEach(b => b.addEventListener("click", () => decideFraud(b.dataset.accept, true)));
  wrap.querySelectorAll("[data-block]").forEach(b => b.addEventListener("click", () => decideFraud(b.dataset.block, false)));
}

async function decideFraud(id, accept) {
  await api.post(`/api/manager/fraud/${id}/decide`, { accept });
  showToast(accept ? "Transaction approved." : "Transaction blocked.");
  loadManagerFraud();
  refreshNotificationBadges();
}

// ---------------- CURRENCY ----------------
function renderCurrencyStats(data) {
  document.getElementById("cur-last").textContent = data.prediction.last_close;
  document.getElementById("cur-pred").textContent = data.prediction.predicted_next;
  const pct = data.prediction.pct_change;
  const changeEl = document.getElementById("cur-change");
  changeEl.textContent = `${pct > 0 ? "+" : ""}${pct}%`;
  changeEl.style.color = pct >= 0 ? "var(--success)" : "var(--danger)";
  document.getElementById("cur-direction").textContent = `Model expects EUR/USD to move ${data.prediction.direction}`;
}
function renderCurrencyChart(history) {
  lastCurrencyHistory = history;
  const ctx = document.getElementById("cur-chart");
  const colors = chartColors();
  const cfg = {
    type: "line",
    data: { labels: history.map((_, i) => `D-${history.length - i}`), datasets: [{
      data: history, borderColor: colors.line, backgroundColor: colors.fill,
      fill: true, tension: 0.35, pointRadius: 0, borderWidth: 2.5,
    }] },
    options: {
      responsive: true, plugins: { legend: { display: false } },
      scales: { x: { display: false }, y: { grid: { color: colors.grid }, ticks: { color: colors.text } } },
    },
  };
  if (currencyChart) { currencyChart.destroy(); }
  currencyChart = new Chart(ctx, cfg);
}
async function loadCurrency() {
  const data = await api.get("/api/currency");
  renderCurrencyStats(data); renderCurrencyChart(data.history);
}
document.getElementById("cur-advance").addEventListener("click", async () => {
  const data = await api.post("/api/currency/advance");
  renderCurrencyStats(data); renderCurrencyChart(data.history);
  showToast("Advanced one trading day.");
});

// ---------------- DASHBOARD ----------------
async function loadDashboard() {
  const d = await api.get("/api/manager/dashboard");
  lastDashboardData = d;
  const colors = chartColors();

  document.getElementById("dash-stats").innerHTML = `
    <div class="card stat-card"><div class="label">Total registered users</div><div class="value">${d.total_users}</div><div class="sub">${d.total_clients} clients</div></div>
    <div class="card stat-card"><div class="label">Total balances held</div><div class="value">${money(d.total_balance)}</div></div>
    <div class="card stat-card"><div class="label">Loan approval rate</div><div class="value">${d.approval_rate !== null ? d.approval_rate + "%" : "—"}</div><div class="sub">Of decided requests</div></div>
    <div class="card stat-card"><div class="label">Transactions flagged</div><div class="value">${(d.tx_counts.pending_review||0)+(d.tx_counts.manager_approved||0)+(d.tx_counts.manager_rejected||0)}</div><div class="sub">of ${Object.values(d.tx_counts).reduce((a,b)=>a+b,0)} total</div></div>`;

  const segLabels = Object.keys(d.segments);
  const segData = Object.values(d.segments);
  const segCtx = document.getElementById("segment-chart");
  const segCfg = { type: "doughnut", data: { labels: segLabels, datasets: [{ data: segData, backgroundColor: [colors.segmentA, colors.segmentB], borderWidth: 0 }] },
    options: { plugins: { legend: { position: "bottom", labels: { boxWidth: 12, color: colors.text, font: { family: "Inter" } } } } } };
  if (segmentChart) segmentChart.destroy();
  segmentChart = new Chart(segCtx, segCfg);

  const loanLabels = ["Approved", "Pending", "Declined"];
  const loanData = [d.loan_counts.approved || 0, d.loan_counts.pending || 0, d.loan_counts.rejected || 0];
  const loanCtx = document.getElementById("loans-chart");
  const loanCfg = { type: "bar", data: { labels: loanLabels, datasets: [{ data: loanData, backgroundColor: ["#3F8F6B", "#B9862F", "#B4494A"], borderRadius: 8 }] },
    options: { plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: colors.text }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, color: colors.text }, grid: { color: colors.grid } },
      } } };
  if (loansChart) loansChart.destroy();
  loansChart = new Chart(loanCtx, loanCfg);

  const signupCtx = document.getElementById("signups-chart");
  const signupCfg = { type: "bar", data: {
      labels: d.signups.map(s => s.day.slice(5)), // MM-DD
      datasets: [{ data: d.signups.map(s => s.count), backgroundColor: colors.line, borderRadius: 6, maxBarThickness: 28 }],
    }, options: { plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: colors.text }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, color: colors.text }, grid: { color: colors.grid } },
      } } };
  if (signupsChart) signupsChart.destroy();
  signupsChart = new Chart(signupCtx, signupCfg);

  const order = ["loan", "fraud", "currency", "segmentation"];
  document.getElementById("model-metric-cards").innerHTML = order.map(key => {
    const m = d.model_metrics[key];
    const live = d.live_stats[key];
    const bars = m.metrics.map(metric => {
      const label = metric.label.toLowerCase();
      let pct, displayVal;
      if (label === "mae" || label === "rmse") {
        pct = Math.max(6, Math.min(100, 100 - metric.value * 2000));
        displayVal = metric.value.toFixed(4);
      } else if (label === "clusters (k)") {
        pct = 100;
        displayVal = metric.value;
      } else {
        pct = Math.min(100, metric.value);
        displayVal = `${metric.value}%`;
      }
      return `<div class="metric-bar-row">
        <div class="metric-bar-head"><span class="name">${metric.label}</span><span class="val">${displayVal}</span></div>
        <div class="metric-bar-track"><div class="metric-bar-fill" style="width:${pct}%;"></div></div>
      </div>`;
    }).join("");
    return `<div class="card model-card">
      <div class="spread">
        <div>
          <div class="tag">${m.type.toUpperCase()}</div>
          <h3 class="display">${m.name}</h3>
        </div>
        <div style="text-align:right;">
          <div class="muted" style="font-size:11.5px;">${m.headline.label}</div>
          <div class="display" style="font-size:22px;">${m.headline.value}</div>
        </div>
      </div>
      ${bars}
      <p style="margin-top:10px;">${m.note}</p>
      <div class="live-stat-pill"><span class="name">${live.label}</span><span class="val">${live.value}</span></div>
    </div>`;
  }).join("");
}

// ---------------- boot ----------------
shell.onSection("account", () => { loadAccount(); loadClientDirectory(); });
shell.onSection("loans", loadManagerLoans);
shell.onSection("fraud", loadManagerFraud);
shell.onSection("currency", loadCurrency);
shell.onSection("dashboard", loadDashboard);
shell.init("account");

async function refreshNotificationBadges() {
  try {
    const n = await api.get("/api/manager/notifications");
    shell.setBadge("loans", n.pending_loans);
    shell.setBadge("fraud", n.pending_fraud);
  } catch (e) { /* not logged in yet, ignore */ }
}
refreshNotificationBadges();
setInterval(refreshNotificationBadges, 20000);

window.addEventListener("verdict-theme-change", () => {
  if (lastCurrencyHistory) renderCurrencyChart(lastCurrencyHistory);
  if (lastDashboardData && shell.activeSection === "dashboard") loadDashboard();
});
