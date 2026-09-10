"""
models.py
---------
Loads the four trained model artifacts once at startup and exposes small,
well-documented predict functions for the rest of the app to call.

Every assumption made about a model's inputs/outputs (because the .pkl file
does not carry that context with it) is written down here, next to the code
that depends on it, so it's easy to correct later if you know better.
"""
import warnings
import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore", category=UserWarning)

MODELS_DIR = "models"

# ---------------------------------------------------------------------------
# Load artifacts once
# ---------------------------------------------------------------------------
_loan_pipeline = joblib.load(f"{MODELS_DIR}/loan_model.pkl")

_fraud_bundle = joblib.load(f"{MODELS_DIR}/final_fraud_pipeline.pkl")
_fraud_pipeline = _fraud_bundle["pipeline"]
_fraud_threshold = _fraud_bundle["threshold"]
_fraud_feature_columns = _fraud_bundle["feature_columns"]

_currency_bundle = joblib.load(f"{MODELS_DIR}/currency_final_pipeline.pkl")
_currency_model = _currency_bundle["model"]
_currency_features = _currency_bundle["features"]          # ['lag_1','lag_7','ma_7','ma_30']
_currency_pair = _currency_bundle["currency_pair"]          # 'EUR/USD'

_cluster_model = joblib.load(f"{MODELS_DIR}/clustering_model.pkl")


# ---------------------------------------------------------------------------
# LOAN MODEL  (XGBoost pipeline: OneHotEncoder + RobustScaler -> XGBClassifier)
# ---------------------------------------------------------------------------
# Categories learned during training (read straight off the fitted encoder):
LOAN_CATEGORIES = {
    "person_gender": ["female", "male"],
    "person_education": ["Associate", "Bachelor", "Doctorate", "High School", "Master"],
    "person_home_ownership": ["MORTGAGE", "OTHER", "OWN", "RENT"],
    "loan_intent": ["DEBTCONSOLIDATION", "EDUCATION", "HOMEIMPROVEMENT", "MEDICAL", "PERSONAL", "VENTURE"],
    "previous_loan_defaults_on_file": ["No", "Yes"],
}
# Typical numeric ranges (median / IQR taken from the fitted RobustScaler) -
# used only to build sane default values and slider bounds in the UI.
# Recomputed directly from loan_data.csv (45,000 rows) for exactness.
LOAN_NUMERIC_STATS = {
    "person_age": {"median": 26.0, "min": 18, "max": 80},
    "person_income": {"median": 67048.0, "min": 8000, "max": 500000},
    "person_emp_exp": {"median": 4.0, "min": 0, "max": 40},
    "loan_amnt": {"median": 8000.0, "min": 500, "max": 40000},
    "loan_int_rate": {"median": 11.01, "min": 4.0, "max": 25.0},
    "loan_percent_income": {"median": 0.12, "min": 0.0, "max": 0.8},
    "cb_person_cred_hist_length": {"median": 4.0, "min": 0, "max": 30},
    "credit_score": {"median": 640.0, "min": 300, "max": 850},
}
# Exact column order the fitted pipeline was trained with (from feature_names_in_).
LOAN_FEATURE_ORDER = [
    "person_age", "person_gender", "person_education", "person_income", "person_emp_exp",
    "person_home_ownership", "loan_amnt", "loan_intent", "loan_int_rate", "loan_percent_income",
    "cb_person_cred_hist_length", "credit_score", "previous_loan_defaults_on_file",
]

# CONFIRMED against loan.ipynb cell 21: loan_status labels are
#   0 = Rejected, 1 = Approved
# (~22% approved). Class index 1 from predict_proba is therefore P(approved).
# Do NOT invert this — class 1 = Approved.
LOAN_POSITIVE_CLASS_MEANS_APPROVED = True


def predict_loan(payload: dict) -> dict:
    """payload keys must match LOAN_FEATURE_ORDER. Class 1 = approved (not default risk)."""
    row = {k: payload[k] for k in LOAN_FEATURE_ORDER}
    X = pd.DataFrame([row], columns=LOAN_FEATURE_ORDER)
    proba = _loan_pipeline.predict_proba(X)[0]
    p_approved = float(proba[1])  # class 1 = Approved per training notebook
    approved = p_approved >= 0.5

    reasons = []
    if row["previous_loan_defaults_on_file"] == "Yes":
        reasons.append("previous default on file — historically almost never approved in training data")
    if row["loan_percent_income"] > 0.40:
        reasons.append("loan is a very large share of stated income")
    elif row["loan_percent_income"] < 0.05 and row["loan_amnt"] < 3000:
        reasons.append("very small loan relative to income — model saw few such approvals in training")
    if row["credit_score"] < 580:
        reasons.append("credit score is below typical approval range")
    if row["loan_int_rate"] > 18:
        reasons.append("interest rate reflects higher assessed risk")
    if row["cb_person_cred_hist_length"] < 2:
        reasons.append("short credit history")
    if row["person_income"] and row["person_income"] < 25000:
        reasons.append("stated income is on the low side for the requested amount")
    if not reasons:
        reasons.append("profile is broadly in line with historically approved applicants")

    return {
        "approved": bool(approved),
        "probability": round(p_approved * 100, 1),
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# FRAUD MODEL  (CountEncoder + OneHotEncoder -> XGBClassifier)
# ---------------------------------------------------------------------------
FRAUD_CATEGORIES = {
    "gender": ["F", "M"],
    "category": ["entertainment", "food_dining", "gas_transport", "grocery_net", "grocery_pos",
                 "health_fitness", "home", "kids_pets", "misc_net", "misc_pos",
                 "personal_care", "shopping_net", "shopping_pos", "travel"],
}
US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA",
             "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM",
             "NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA",
             "WV","WI","WY"]
# CONFIRMED from fraud_fixed_notebook.ipynb's own category-level EDA (Q4):
# shopping_net, misc_net, and grocery_pos run 3-10x the baseline fraud rate;
# "_net" (online) categories generally skew riskier than "_pos" (in-person) ones.
_RISKIER_CATEGORIES = {"shopping_net", "misc_net", "grocery_pos"}
# CONFIRMED from the same notebook's hour-of-day EDA (Q3): fraud rate is flat
# (~0.1%) during the day but spikes at 22:00-23:00 and 00:00-03:00 (~25x baseline).
_RISKY_HOURS = {22, 23, 0, 1, 2, 3}
FRAUD_THRESHOLD = _fraud_threshold  # 0.85, taken from the bundle as trained (best-F1 cutoff)


def predict_fraud(payload: dict, sender_avg_amt: float | None = None) -> dict:
    """payload keys: merchant, category, amt, gender, state, job,
    trans_hour, trans_dayofweek, trans_day, trans_month, age."""
    row = {k: payload[k] for k in _fraud_feature_columns}
    X = pd.DataFrame([row])
    
    # 1. Machine Learning Prediction
    proba = float(_fraud_pipeline.predict_proba(X)[0][1])
    is_model_flagged = proba >= FRAUD_THRESHOLD

    reasons = []
    is_rule_flagged = False

    # 2. Hardcoded Business Rules (Overrides ML if triggered)
    if sender_avg_amt and row["amt"] > 3 * max(sender_avg_amt, 1):
        is_rule_flagged = True
        reasons.append(f"Amount (${row['amt']:.2f}) is >3x this client's usual transaction size.")
    elif row["amt"] > 800:
        is_rule_flagged = True
        reasons.append(f"Relatively large transaction amount (${row['amt']:.2f}) requires manual review.")
        
    # --- NEW RULE: Overnight Spikes ---
    if row["trans_hour"] in _RISKY_HOURS and row["category"] in _RISKIER_CATEGORIES:
        is_rule_flagged = True
        reasons.append(f"High-risk category ('{row['category'].replace('_', ' ')}') used during the overnight window.")

    # 3. Add context if the ML model flagged it
    if is_model_flagged:
        if row["trans_hour"] in _RISKY_HOURS and not any("overnight" in r for r in reasons):
            reasons.append("Transaction occurred during the overnight window (historically high fraud rate).")
        if row["category"] in _RISKIER_CATEGORIES and not any("category" in r for r in reasons):
            reasons.append(f"'{row['category'].replace('_', ' ')}' carries a higher baseline fraud risk.")
        if not reasons:
            reasons.append("Combination of factors deviates from typical baseline patterns.")

    # 4. Final Decision: Flag if ML caught it OR a Business Rule caught it
    final_flagged = is_model_flagged or is_rule_flagged
    
    if not final_flagged and not reasons:
        reasons.append("Transaction is consistent with normal patterns.")

    return {
        "flagged": bool(final_flagged), 
        "probability": round(proba * 100, 1), 
        "reasons": reasons
    }


# ---------------------------------------------------------------------------
# CURRENCY MODEL  (Linear Regression on lag/moving-average features)
# ---------------------------------------------------------------------------
def predict_currency(history: list[float]) -> dict:
    """history: chronological list of past closing prices (oldest -> newest),
    needs at least 30 points. Builds lag_1, lag_7, ma_7, ma_30 exactly as the
    model expects and returns tomorrow's predicted value."""
    s = pd.Series(history)
    feats = {
        "lag_1": s.iloc[-1],
        "lag_7": s.iloc[-7],
        "ma_7": s.iloc[-7:].mean(),
        "ma_30": s.iloc[-30:].mean(),
    }
    X = pd.DataFrame([feats])[_currency_features]
    pred = float(_currency_model.predict(X)[0])
    last = float(s.iloc[-1])
    pct_change = ((pred - last) / last) * 100
    return {
        "pair": _currency_pair,
        "last_close": round(last, 5),
        "predicted_next": round(pred, 5),
        "pct_change": round(pct_change, 3),
        "direction": "up" if pred > last else ("down" if pred < last else "flat"),
    }


# ---------------------------------------------------------------------------
# CLUSTERING MODEL (KMeans, k=2, trained on a bank-churn customer table)
# ---------------------------------------------------------------------------
# The shipped pickle is bare (`KMeans` only) with no feature names attached,
# and the fitted preprocessor (`preprocessing_transformer.pkl`) wasn't part of
# the handoff. Reconstructed from Copy_of_Customer_Segmentation.ipynb instead:
#
#   ColumnTransformer([
#       ('num', StandardScaler(), ['CreditScore','Age','Tenure','Balance',
#                                    'EstimatedSalary','NumOfProducts']),
#       ('cat', OneHotEncoder(),  ['Geography','Gender']),
#   ])
#
# giving the 11 columns in this exact order: CreditScore, Age, Tenure, Balance,
# EstimatedSalary, NumOfProducts, Geography_France, Geography_Germany,
# Geography_Spain, Gender_Female, Gender_Male.
#
# The fitted scaler itself wasn't in the handoff either, but the notebook's
# own output cell printed each cluster's *unscaled* feature means. Combined
# with the shipped model's *scaled* cluster_centers_, that's two points per
# feature on a known-linear map — enough to solve for the exact StandardScaler
# mean_/scale_ algebraically. Where that solve was well-conditioned (features
# with real separation between the two clusters) it landed within ~0.1% of the
# well-documented statistics for this dataset (a 10,000-row bank-churn table),
# which is what's hardcoded below.
SEGMENT_NUMERIC_ORDER = ["CreditScore", "Age", "Tenure", "Balance", "EstimatedSalary", "NumOfProducts"]
SEGMENT_SCALER = {
    "CreditScore":     {"mean": 650.5288, "std": 96.6533},
    "Age":             {"mean": 38.9218,  "std": 10.4878},
    "Tenure":          {"mean": 5.0128,   "std": 2.8922},
    "Balance":         {"mean": 76485.8893, "std": 62397.4052},
    "EstimatedSalary": {"mean": 100090.2399, "std": 57510.4928},
    "NumOfProducts":   {"mean": 1.5302,   "std": 0.5817},
}
SEGMENT_GEOGRAPHIES = ["France", "Germany", "Spain"]  # OneHotEncoder 'auto' sorts alphabetically
SEGMENT_GENDERS = ["Female", "Male"]

SEGMENT_LABELS = {0: "Everyday Banking", 1: "Premium Relationship"}


def _segment_vector(credit_score, age, tenure, balance, salary, num_products, geography, gender):
    numeric_raw = {
        "CreditScore": credit_score, "Age": age, "Tenure": tenure, "Balance": balance,
        "EstimatedSalary": salary, "NumOfProducts": num_products,
    }
    scaled = [
        (numeric_raw[f] - SEGMENT_SCALER[f]["mean"]) / SEGMENT_SCALER[f]["std"]
        for f in SEGMENT_NUMERIC_ORDER
    ]
    geo_ohe = [1.0 if geography == g else 0.0 for g in SEGMENT_GEOGRAPHIES]
    gender_ohe = [1.0 if gender == g else 0.0 for g in SEGMENT_GENDERS]
    return np.array(scaled + geo_ohe + gender_ohe).reshape(1, -1)


def predict_segment(credit_score=None, age=None, tenure=None, balance=0, salary=None,
                     num_products=None, geography="France", gender="Female"):
    vec = _segment_vector(
        credit_score if credit_score is not None else 650,
        age if age is not None else 39,
        tenure if tenure is not None else 5,
        balance or 0,
        salary if salary is not None else 100000,
        num_products if num_products is not None else 1,
        geography or "France",
        "Male" if (gender or "").lower().startswith("m") else "Female",
    )
    label = int(_cluster_model.predict(vec)[0])
    return {"segment_id": label, "segment_label": SEGMENT_LABELS.get(label, f"Segment {label}")}


def cluster_distribution(clients: list[dict]) -> dict:
    """clients: list of dicts with keys credit_score, age, tenure, balance,
    salary, num_products, geography, gender."""
    counts = {"Everyday Banking": 0, "Premium Relationship": 0}
    for c in clients:
        counts[predict_segment(**c)["segment_label"]] += 1
    return counts


# ---------------------------------------------------------------------------
# TRAINING-TIME METRICS, read directly from your notebooks (not recomputed
# live — these describe how each model performed on its own held-out test
# set at training time). Sources:
#   loan.ipynb        cell 66 (final pipeline, test set, threshold 0.5)
#   fraud_fixed_notebook.ipynb  cell 57 (test PR-AUC/ROC-AUC, threshold-independent)
#   Currency.ipynb    cell 11 (Linear Regression, held-out test split)
#   Copy_of_Customer_Segmentation.ipynb + silhouette recomputed directly
#   against clustering_model.pkl on the real churn.csv (this repo), since the
#   notebook only saved the number to a JSON file that wasn't part of the handoff.
# ---------------------------------------------------------------------------
MODEL_METRICS = {
    "loan": {
        "name": "Loan Approval Model", "type": "XGBoost Classifier",
        "headline": {"label": "Test accuracy", "value": "93.7%"},
        "metrics": [
            {"label": "Accuracy", "value": 93.73},
            {"label": "Precision", "value": 89.83},
            {"label": "Recall", "value": 80.03},
            {"label": "F1-score", "value": 84.65},
        ],
        "note": "Evaluated on a held-out test split at the shipped decision threshold (0.5). "
                "~22% of applications are approved in the training data, so precision/recall "
                "matter more here than accuracy alone.",
    },
    "fraud": {
        "name": "Fraud Detection Model", "type": "XGBoost Classifier",
        "headline": {"label": "Test ROC-AUC", "value": "0.998"},
        "metrics": [
            {"label": "ROC-AUC", "value": 99.81},
            {"label": "PR-AUC", "value": 92.11},
        ],
        "note": "Fraud makes up only ~0.58% of transactions, so accuracy is a meaningless "
                "metric here (predicting 'never fraud' would already score ~99.4%) — ROC-AUC "
                "and PR-AUC (threshold-independent) are what the notebook uses to judge it. "
                f"The shipped decision threshold is {FRAUD_THRESHOLD:.2f}, tuned for high precision.",
    },
    "currency": {
        "name": "Currency Forecast Model", "type": "Linear Regression",
        "headline": {"label": "Test MAE", "value": "0.0030"},
        "metrics": [
            {"label": "MAE", "value": 0.003019},
            {"label": "RMSE", "value": 0.004181},
        ],
        "note": "MAE of 0.003 on EUR/USD means next-day predictions are typically off by about "
                "3/10 of a cent. Linear Regression outperformed both Random Forest (MAE 0.0050) "
                "and XGBoost (MAE 0.0046) in testing — the simplest model won.",
    },
    "segmentation": {
        "name": "Client Segmentation Model", "type": "KMeans Clustering (k=2)",
        "headline": {"label": "Silhouette score", "value": "0.15"},
        "metrics": [
            {"label": "Silhouette score", "value": 15.45},
            {"label": "Clusters (k)", "value": 2},
        ],
        "note": "k=2 was chosen by sweeping silhouette scores across candidate k values. "
                "A silhouette of 0.15 is modest but expected here — mixing continuous features "
                "(balance, salary) with one-hot categoricals (geography, gender) tends to pull "
                "scores down even when the clusters are meaningfully different in practice.",
    },
}
