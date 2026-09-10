# Verdict

A working bank web app built around your four trained models: loan approval,
fraud detection, currency forecasting, and client segmentation. Flask +
SQLite backend, no build step on the frontend.

## What's inside

- **Welcome page** — animated "Welcome," then login/signup with a client-or-manager
  switch.
- **Client dashboard** — Account (view/edit profile), Loans (pick a package, get an
  instant automated read, track status), Transactions (send money, screened by the
  fraud model in real time), Currency (EUR/USD forecast + term-deposit/campaign
  suggestions).
- **Manager console** — Account + client directory, Loans queue (approve/decline with
  the model's score and reasons in front of you), Fraud detection queue (same, for
  flagged transactions), Currency, and a Model & Performance dashboard with charts.
- Color palette, typography, and the slide-out drawer nav follow your brief.

## 1. Install

Requires Python 3.10+.

```bash
git clone [https://github.com/youssef-shawky26/SmartBank-Ai--NTI_Final_Project.git](https://github.com/youssef-shawky26/SmartBank-Ai--NTI_Final_Project.git)
cd SmartBank-Ai--NTI_Final_Project
python -m venv venv
source venv/bin/activate        # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Run

```bash
python3 app.py
```

Open **http://127.0.0.1:5000** in your browser.

The first run creates `data/aurion_bank.db` and seeds demo accounts:

| Role    | Username | Password    |
|---------|----------|-------------|
| Client  | jmartin  | client123   |
| Client  | sfields  | client123   |
| Client  | rkline   | client123   |
| Manager | manager  | manager123  |

Sign up your own accounts from the welcome page — clients need no code, managers
need the staff access code `VERDICT-STAFF-2026` (change this in `app.py`,
`MANAGER_ACCESS_CODE`, before showing this to anyone else).

To start over with a clean database, stop the server and delete the `data/` folder.

## 3. A few things worth trying

- **Loans** (as a client): apply for a **$25,000 Venture / Business loan**
  with `jmartin` — the model reads back a solid repayment likelihood (mid-60s%).
  Then log in as `manager` and approve it from the Loans queue; the funds land
  in the client's balance. (Small loan amounts relative to income score lower
  for this model — see the loan model note below.)
- **Fraud detection**: log in as `rkline` (balance is intentionally low) and send
  **$500** to any account number, category **Grocery (in-person)**. The model
  reliably flags this combination — you'll see it land in the manager's Fraud
  detection queue with its reasons, and approving it actually moves the money.
- **Currency**: hit "Simulate next trading day" a few times on the Currency page
  to watch the forecast update as new (synthetic) history comes in.
- **Model & Performance**: switch to the manager console's last tab for the
  live dashboard — approval rate, flagged-transaction count, segment split, and
  the currency model's current call, all computed from what's actually in the
  database.

## Model notes — updated after reviewing your training notebooks

You sent over `loan.ipynb`, `fraud_fixed_notebook.ipynb`, `Currency.ipynb`, and
`Copy_of_Customer_Segmentation.ipynb`. I went through all four and corrected
the app against what they actually show, including one real bug:

1. **Loan model — I had the target backwards, now fixed.** I originally
   inferred (from my own synthetic test profiles) that class 1 meant "high
   default risk." Your notebook shows `loan_status` is actually **1 =
   Approved, 0 = Rejected** (~22% approved). I replayed 5 real labeled rows
   from your training data through the shipped pipeline and `predict()`
   matched the true label 5/5 times, and the notebook's own test-set numbers
   (93.7% accuracy, 80% recall on the approved class) confirm it. The app now
   reads the model correctly.

   One real, verified characteristic worth knowing: `previous_loan_defaults_on_file`
   dominates this model's decisions overwhelmingly (its gain score is ~16x the
   next most important feature) — a prior default drives approval odds to
   roughly 0% almost regardless of anything else. Below that, `loan_percent_income`
   has a secondary, non-monotonic effect for applicants *without* a prior
   default: very small loan requests relative to income (under ~20-25% of
   income) can score lower than moderate-to-large ones (25-50%) for otherwise
   identical, strong applicants. That's a genuine property of the trained
   model (verified by isolating the feature directly), not an artifact of the
   app's integration, so I left it as-is rather than second-guessing the model.

2. **Fraud model reasons — now grounded in your own EDA.** The "why flagged"
   explanations now use the exact risk factors your notebook identified:
   `shopping_net`, `misc_net`, and `grocery_pos` (Q4), and the overnight window
   22:00-03:00 where fraud rates run ~25x the daytime baseline (Q3), rather
   than a guessed list.

3. **Clustering model — reconstructed from your notebook, no longer a
   placeholder.** `Copy_of_Customer_Segmentation.ipynb` showed the real
   pipeline: `StandardScaler` on `CreditScore, Age, Tenure, Balance,
   EstimatedSalary, NumOfProducts` plus one-hot-encoded `Geography` (France/
   Germany/Spain) and `Gender` — the same 11-column shape as the shipped
   `KMeans`. The scaler itself wasn't included in the handoff, but the
   notebook printed each cluster's raw (unscaled) feature means, and the
   shipped model's `cluster_centers_` gave the same means in scaled space —
   two known points per feature is enough to solve for the exact
   `StandardScaler` `mean_`/`scale_` algebraically. I validated the result by
   feeding the notebook's own two cluster-mean profiles back through it: they
   land in cluster 0 and cluster 1 exactly as expected.

   Practically, this means client profiles now include three more fields —
   **Geography, years as a customer (tenure), and number of products held** —
   editable from the Account tab, and segmentation on the Manager dashboard
   uses the real feature set instead of a single-dimension stand-in.

4. **Currency model** — double-checked against the notebook's own
   `latest_features` cell; the app's `lag_1/lag_7/ma_7/ma_30` construction
   already matched it exactly, no change needed.

Also worth knowing: the fraud model is somewhat sensitive to the transaction's
real calendar month, which shifts how easily a transaction gets flagged
depending on what day you're running the app. The "$500 grocery-store,
low-balance account" scenario below was tested to work regardless of hour or
month, so it's a safe way to demonstrate the flow.

## Project structure

```text
SmartBank-Ai/
├── app.py                  # Flask app: routes, auth, hybrid business logic
├── models.py               # Loads the 4 .pkl pipelines, exposes predict_* functions
├── db.py                   # SQLite schema + connection helper
├── seed.py                 # Generates DB and demo data on first run
├── requirements.txt        # Python dependencies
├── Notebooks/              # Original Jupyter notebooks for EDA and Model Training
├── models/                 # Exported Joblib pipelines (.pkl)
├── data/                   # aurion_bank.db (created dynamically on first run)
├── templates/              # HTML files (welcome, client, manager, base)
└── static/
    ├── css/style.css       # Custom design system and color palette
    └── js/                 # Vanilla JS for API calls and DOM manipulation
```

## Production note

`app.py` runs Flask's built-in development server, which is fine for local use
and demos. If you ever deploy this somewhere reachable by others, put it behind
a real WSGI server (gunicorn/uwsgi) and change `app.secret_key` in `app.py` to
a private, random value.
