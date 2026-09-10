// Keep these in sync with the category lists the models were trained on (see models.py)
const LOAN_PACKAGES = [
  { code: "PERSONAL", label: "Personal Loan", rate: 9.9, cap: 15000, blurb: "Flexible use, fastest turnaround." },
  { code: "HOMEIMPROVEMENT", label: "Home Improvement", rate: 8.5, cap: 25000, blurb: "Renovations, repairs, upgrades." },
  { code: "DEBTCONSOLIDATION", label: "Debt Consolidation", rate: 10.5, cap: 20000, blurb: "Combine balances into one payment." },
  { code: "EDUCATION", label: "Education", rate: 6.9, cap: 30000, blurb: "Tuition and course fees." },
  { code: "MEDICAL", label: "Medical", rate: 7.9, cap: 10000, blurb: "Planned or unplanned care costs." },
  { code: "VENTURE", label: "Venture / Business", rate: 11.9, cap: 40000, blurb: "Starting or growing a business." },
];
const TX_CATEGORIES = ["entertainment", "food_dining", "gas_transport", "grocery_net", "grocery_pos",
  "health_fitness", "home", "kids_pets", "misc_net", "misc_pos", "personal_care", "shopping_net",
  "shopping_pos", "travel"];

const ACCOUNT_FIELDS = [
  { key: "full_name", label: "Full name", type: "text" },
  { key: "age", label: "Age", type: "number" },
  { key: "gender", label: "Gender", type: "select", options: ["female", "male"] },
  { key: "phone", label: "Phone", type: "text" },
  { key: "email", label: "Email", type: "email" },
  { key: "state", label: "State", type: "text" },
  { key: "job", label: "Occupation", type: "text" },
  { key: "balance", label: "Account balance", type: "number" },
  { key: "income", label: "Annual income", type: "number" },
  { key: "employment_years", label: "Years employed", type: "number" },
  { key: "home_ownership", label: "Home ownership", type: "select", options: ["MORTGAGE", "OWN", "RENT", "OTHER"] },
  { key: "credit_score", label: "Credit score", type: "number" },
  { key: "credit_history_years", label: "Credit history (years)", type: "number" },
  { key: "has_prior_default", label: "Prior loan default", type: "select", options: ["No", "Yes"] },
  { key: "geography", label: "Geography (segmentation)", type: "select", options: ["France", "Germany", "Spain"] },
  { key: "tenure_years", label: "Years as a customer", type: "number" },
  { key: "num_of_products", label: "Products held", type: "number" },
];

let currentUser = null;
let editing = false;
let selectedPackage = LOAN_PACKAGES[0];
let currencyChart = null;
let lastCurrencyHistory = null;

function friendly(s) { return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }

async function refreshBalance() {
  const { user } = await api.get("/api/account");
  currentUser = user;
  document.getElementById("acc-balance").textContent = money(user.balance);
  document.getElementById("acc-number").textContent = user.account_number;
}

// ---------------- ACCOUNT ----------------
function renderAccountFields(user, editMode) {
  const wrap = document.getElementById("account-fields");
  wrap.innerHTML = "";
  ACCOUNT_FIELDS.forEach(f => {
    const box = document.createElement("div");
    box.className = "field";
    const label = document.createElement("label");
    label.textContent = f.label;
    box.appendChild(label);
    if (!editMode) {
      const val = document.createElement("div");
      val.style.padding = "11px 0";
      val.style.fontWeight = "600";
      val.textContent = ((f.key === "income" || f.key === "balance") && user[f.key] != null) ? money(user[f.key]) : (user[f.key] ?? "—");
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
  document.getElementById("acc-balance").textContent = money(user.balance);
  document.getElementById("acc-number").textContent = user.account_number;
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
  try {
    const { user } = await api.put("/api/account", payload);
    currentUser = user;
    editing = false;
    document.getElementById("edit-toggle").textContent = "Edit";
    document.getElementById("account-save-row").style.display = "none";
    renderAccountFields(user, false);
    document.getElementById("acc-balance").textContent = money(user.balance);
    document.getElementById("acc-number").textContent = user.account_number;
    showToast("Profile updated.");
  } catch (err) { showToast(err.message, true); }
});

// ---------------- LOANS ----------------
function renderLoanPackages() {
  const wrap = document.getElementById("loan-packages");
  wrap.innerHTML = "";
  LOAN_PACKAGES.forEach(p => {
    const card = document.createElement("div");
    card.className = "card";
    card.style.cursor = "pointer";
    card.style.borderColor = p.code === selectedPackage.code ? "var(--navy)" : "";
    card.style.borderWidth = p.code === selectedPackage.code ? "2px" : "1px";
    card.innerHTML = `<h3 class="display" style="font-size:16.5px; margin-bottom:6px;">${p.label}</h3>
      <p class="muted" style="font-size:13px; margin:0 0 10px;">${p.blurb}</p>
      <div class="row" style="justify-content:space-between;">
        <span class="chip chip-neutral">from ${p.rate}% APR</span>
        <span class="muted" style="font-size:12.5px;">up to ${money(p.cap)}</span>
      </div>`;
    card.addEventListener("click", () => {
      selectedPackage = p;
      document.getElementById("loan-amount").max = p.cap;
      renderLoanPackages();
      updateLoanIntentSelect();
    });
    wrap.appendChild(card);
  });
}

function updateLoanIntentSelect() {
  const sel = document.getElementById("loan-intent");
  sel.innerHTML = "";
  LOAN_PACKAGES.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.code; opt.textContent = p.label;
    if (p.code === selectedPackage.code) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.onchange = () => {
    selectedPackage = LOAN_PACKAGES.find(p => p.code === sel.value);
    document.getElementById("loan-amount").max = selectedPackage.cap;
    renderLoanPackages();
  };
}

document.getElementById("loan-amount").addEventListener("input", (e) => {
  document.getElementById("loan-amount-label").textContent = money(e.target.value);
});

document.getElementById("loan-submit").addEventListener("click", async () => {
  const amount = Number(document.getElementById("loan-amount").value);
  const gender = document.getElementById("loan-gender").value;
  const education = document.getElementById("loan-education").value;
  const home_ownership = document.getElementById("loan-home").value;
  const prior_default = document.getElementById("loan-default").value;
  const btn = document.getElementById("loan-submit");
  btn.disabled = true;
  try {
    const res = await api.post("/api/loans", {
      amount, intent: selectedPackage.code, interest_rate: selectedPackage.rate,
      gender, education, home_ownership, prior_default,
    });
    const a = res.preliminary_assessment;
    const resultBox = document.getElementById("loan-result");
    resultBox.innerHTML = `
      <div class="card" style="background: var(--bg-soft); border:none;">
        <div class="spread" style="margin-bottom:10px;">
          <strong>Automated preliminary read</strong>
          <span class="chip ${a.approved ? "chip-success" : "chip-danger"}">${a.approved ? "Likely approvable" : "Likely declined"}</span>
        </div>
        <div class="progress-track" style="margin-bottom:6px;"><div class="progress-fill" style="width:${a.probability}%;"></div></div>
        <div class="muted" style="font-size:12.5px;">${a.probability}% modeled approval probability (class 1 = approved)</div>
        <ul class="reason-list">${a.reasons.map(r => `<li>${r}</li>`).join("")}</ul>
        <p class="muted" style="font-size:12.5px; margin-top:10px; margin-bottom:0;">Submitted — a manager will confirm the final decision.</p>
      </div>`;
    loadLoanHistory();
  } catch (err) { showToast(err.message, true); }
  btn.disabled = false;
});

function statusChip(status) {
  const map = {
    pending: ["chip-warning", "Pending review"],
    approved: ["chip-success", "Approved"],
    rejected: ["chip-danger", "Declined"],
    cleared: ["chip-success", "Cleared"],
    pending_review: ["chip-warning", "Under review"],
    manager_approved: ["chip-success", "Cleared"],
    manager_rejected: ["chip-danger", "Blocked"],
    blocked: ["chip-danger", "Blocked"],
  };
  const [cls, text] = map[status] || ["chip-neutral", status];
  return `<span class="chip ${cls}">${text}</span>`;
}

async function loadLoanHistory() {
  const { loans } = await api.get("/api/loans");
  const wrap = document.getElementById("loan-history");
  if (!loans.length) {
    wrap.innerHTML = `<div class="empty-state card"><div class="display">No requests yet</div>Submit one above to see how the model responds.</div>`;
    return;
  }
  wrap.innerHTML = loans.map(l => {
    const pkg = LOAN_PACKAGES.find(p => p.code === l.intent);
    return `<div class="list-row">
      <div>
        <div><strong>${pkg ? pkg.label : l.intent}</strong></div>
        <div class="meta">${fmtDate(l.created_at)} · ${l.model_probability}% approval probability</div>
      </div>
      <div class="row">
        <span class="amount">${money(l.amount)}</span>
        ${statusChip(l.status)}
      </div>
    </div>`;
  }).join("");
}

// ---------------- TRANSACTIONS ----------------
function populateCategorySelect() {
  const sel = document.getElementById("tx-category");
  sel.innerHTML = TX_CATEGORIES.map(c => `<option value="${c}">${friendly(c)}</option>`).join("");
}

document.getElementById("tx-submit").addEventListener("click", async () => {
  const receiver_account = document.getElementById("tx-receiver").value.trim();
  const amount = Number(document.getElementById("tx-amount").value);
  const merchant = document.getElementById("tx-merchant").value.trim();
  const category = document.getElementById("tx-category").value;
  const gender = document.getElementById("tx-gender").value;
  const state = document.getElementById("tx-state").value.trim();
  const job = document.getElementById("tx-job").value.trim();
  const hourEl = document.getElementById("tx-hour");
  const dayEl = document.getElementById("tx-day");
  const monthEl = document.getElementById("tx-month");
  const trans_hour = hourEl && hourEl.value !== "" ? Number(hourEl.value) : null;
  const trans_day = dayEl && dayEl.value !== "" ? Number(dayEl.value) : null;
  const trans_month = monthEl && monthEl.value !== "" ? Number(monthEl.value) : null;
  if (!receiver_account || !amount) { showToast("Enter a recipient and amount.", true); return; }
  const btn = document.getElementById("tx-submit");
  btn.disabled = true;
  try {
    const res = await api.post("/api/transactions", {
      receiver_account, amount, merchant, category, gender, state, job,
      trans_hour, trans_day, trans_month,
    });
    document.getElementById("tx-result").innerHTML = `
      <div class="card" style="background: ${res.status === "cleared" ? "var(--success-bg)" : "var(--warning-bg)"}; border:none;">
        <strong style="color: ${res.status === "cleared" ? "var(--success)" : "var(--warning)"};">${res.status === "cleared" ? "Sent" : "Under review"}</strong>
        <p style="margin:6px 0 0; font-size:13.5px;">${res.message}</p>
      </div>`;
    document.getElementById("tx-amount").value = "";
    document.getElementById("tx-merchant").value = "";
    loadTxHistory();
    refreshBalance();
  } catch (err) { showToast(err.message, true); }
  btn.disabled = false;
});

async function loadTxHistory() {
  const { transactions } = await api.get("/api/transactions");
  const wrap = document.getElementById("tx-history");
  if (!transactions.length) {
    wrap.innerHTML = `<div class="empty-state card"><div class="display">No activity yet</div>Send your first transfer above.</div>`;
    return;
  }
  wrap.innerHTML = transactions.map(t => `
    <div class="list-row">
      <div>
        <div><strong>${t.receiver_name || t.receiver_account}</strong></div>
        <div class="meta">${friendly(t.category || "")} · ${fmtDate(t.created_at)}</div>
      </div>
      <div class="row">
        <span class="amount">${money(t.amount)}</span>
        ${statusChip(t.status)}
      </div>
    </div>`).join("");
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
    data: {
      labels: history.map((_, i) => `D-${history.length - i}`),
      datasets: [{
        data: history, borderColor: colors.line,
        backgroundColor: colors.fill, fill: true, tension: 0.35, pointRadius: 0, borderWidth: 2.5,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { grid: { color: colors.grid }, ticks: { color: colors.text } },
      },
    },
  };
  if (currencyChart) { currencyChart.destroy(); }
  currencyChart = new Chart(ctx, cfg);
}

function renderSuggestions(suggestions) {
  document.getElementById("cur-suggestions").innerHTML = suggestions.map(s => `
    <div class="card">
      <h3 class="display" style="font-size:16.5px; margin-bottom:8px;">${s.title}</h3>
      <p class="muted" style="font-size:13.5px; margin:0;">${s.detail}</p>
    </div>`).join("");
}

async function loadCurrency() {
  const data = await api.get("/api/currency");
  renderCurrencyStats(data);
  renderCurrencyChart(data.history);
  renderSuggestions(data.suggestions);
}

document.getElementById("cur-advance").addEventListener("click", async () => {
  const data = await api.post("/api/currency/advance");
  renderCurrencyStats(data);
  renderCurrencyChart(data.history);
  showToast("Advanced one trading day.");
});

// ---------------- boot ----------------
renderLoanPackages();
updateLoanIntentSelect();
populateCategorySelect();

async function ensureCurrentUser() {
  if (!currentUser) {
    const { user } = await api.get("/api/account");
    currentUser = user;
  }
  return currentUser;
}

function prefillLoanFields(user) {
  if (user.gender) document.getElementById("loan-gender").value = user.gender;
  if (user.home_ownership) document.getElementById("loan-home").value = user.home_ownership;
  if (user.has_prior_default) document.getElementById("loan-default").value = user.has_prior_default;
}

function prefillTxFields(user) {
  document.getElementById("tx-gender").value = (user.gender || "").toLowerCase().startsWith("m") ? "M" : "F";
  if (user.state) document.getElementById("tx-state").value = user.state;
  if (user.job) document.getElementById("tx-job").value = user.job;
}

shell.onSection("account", loadAccount);
shell.onSection("loans", async () => { prefillLoanFields(await ensureCurrentUser()); loadLoanHistory(); });
shell.onSection("transactions", async () => { prefillTxFields(await ensureCurrentUser()); loadTxHistory(); });
shell.onSection("currency", loadCurrency);
shell.init("account");

window.addEventListener("verdict-theme-change", () => {
  if (lastCurrencyHistory) renderCurrencyChart(lastCurrencyHistory);
});
