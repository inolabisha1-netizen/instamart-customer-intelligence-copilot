# Instamart Customer Intelligence & Support Copilot

## Overview

This capstone implements one offline, reproducible Customer Intelligence & Support Copilot using **synthetic, fictional** Instamart-style data. Part A audits, cleans, validates and stores the data in SQLite; Part B segments customers and predicts lapse; Part C redacts identifiers and triages support tickets using the customer segments; Part D evaluates policy retrieval and a bounded refund agent using the supplied `mock_llm.py`. No real customer records, payment transactions, hosted LLM or API keys are involved.

The original assignment allocates **100 marks** across Part A (22), Part B (28), Part C (22) and Part D (28). The supplied `generate_data.py` and `mock_llm.py` must remain unmodified.

## Reproduce

Requirements: **Python 3.11+** and **SQLite 3.25+**. Run these commands **from the repository root**, in order. These are Windows PowerShell commands, matching the development environment.

```powershell
# 1. Create an isolated environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1

# 3. Install the project dependencies
python -m pip install -r requirements.txt

# 4. Regenerate the deterministic synthetic raw data and policies
python generate_data.py

# 5. Run Parts A–D in sequence, including the agent evaluation
python run_project.py
```

The generator's final line should be `generated: customers=1200 products=40 orders_raw=13084 tickets=164`. The pipeline should print `ALL CHECKPOINTS PASSED` for Part A and `RESULT: 7/7 scenarios passed` for the Part D agent evaluation. The source modules may also be run individually where supported; the single command above is the primary reproduction path.

Expected output paths after execution:

| Part | Required artifact(s) |
|---|---|
| A | `data/clean/customers.csv`, `data/clean/products.csv`, `data/clean/orders.csv`, `data/instamart.db`, `sql/queries.sql` |
| B | `outputs/customer_segments.csv`, `outputs/lapse_model.joblib`, `outputs/retention_list.csv` |
| C | `outputs/triage_results.csv`, `outputs/triage_budget_demo.csv` |
| D | `outputs/agent_runs.jsonl`, `outputs/refund_ledger.jsonl`, checkpoint files in `state/` |

**Reproducibility status:** The complete `python run_project.py` pipeline and two consecutive `python -m src.evaluate_agent` runs were reported successful in the working environment. A fresh-clone/clean-virtual-environment run has **not yet been independently verified**; verify it before submission. The seven-scenario evaluator uses isolated test state. The permanent refund ledger is persistent, so direct manual refunds may correctly return `refund already issued` on a later attempt.

## Part A 
The pipeline standardizes city/gender, treats invalid ages as missing, resolves duplicate orders by keeping the latest timestamp, imputes missing amounts from catalogue price, sets negative delivery times to missing and imputes only completed-order delivery durations by product category. The cleaned data is checked against the reference checkpoints in the capstone brief.

### Raw Data Audit
| Metric | Result |
|---|---:|
| Raw orders | 13,084 |
| Exact duplicates | 119 |
| Pending orders | 656 |
| Unique order IDs | 12,309 |
| Non-numeric amounts | 120 |
| Negative delivery times | 106 |
| Blank delivery times | 2,541 |
| Blank customer ages | 61 |
| Ages outside 10–100 | 6 |
| Raw city spellings | 24 |
| Raw gender spellings | 10 |
| Blank genders | 30 |

**Referential integrity:** No duplicate customer/product IDs or missing customer/product references.

### Data Cleaning Summary
| Cleaning operation | Records affected |
|---|---:|
| Exact duplicate orders removed | 119 |
| Older order versions removed | 656 |
| Missing order amounts imputed | 112 |
| Negative delivery times corrected | 105 |
| Completed-order delivery times imputed | 774 |
| Missing/invalid customer ages imputed | 67 |

**Cleaning rules:** Cities were standardized to six names, genders mapped to male/female/unknown, and ages imputed using city-wise medians. Duplicate orders were resolved using the latest timestamp. Missing amounts were calculated from product price, quantity, and discount. Delivery times were imputed using completed-order category medians; cancelled orders retained missing delivery times.

**Final dataset:** 1,200 customers, 40 products, and 12,309 unique orders (11,110 completed; 1,199 cancelled).

### SQL Analysis Results
| Query | Verified result |
|---|---|
| Q1 — WHERE + HAVING | 30 customers |
| Q2 — Three-table JOIN | 30 rows; ₹29,98,668.80; highest: Bengaluru/Electronics (₹2,33,909.45) |
| Q3 — Scalar subquery | 11 products |
| Q4 — LEFT JOIN | 25 customers |
| Q5 — CTE | 550 customers; average spend ₹2,552.06 |
| Q6 — Window functions | 8 ranking differences |
| Q7 — Running total | 183 days; final ₹29,98,668.80 |

**Q6 ranking:** `RANK()` assigns equal ranks to ties and skips subsequent positions, while `ROW_NUMBER()` assigns a unique position to each row.

**Q6 — Top-spending customers by city**

| City | Customer ID | Total spend (₹) |
|---|---|---:|
| Bengaluru | C0082 | 12,856.20 |
| Chennai | C0930 | 10,151.40 |
| Delhi | C0291 | 13,742.60 |
| Hyderabad | C0743 | 12,730.05 |
| Mumbai | C0693 | 14,766.55 |
| Pune | C0426 | 10,377.10 |

### Raw Data — Complete Column Audit

Blank strings are counted as missing for the raw audit (`keep_default_na=False`); nonnumeric amounts and invalid ages are separately reported as quality issues. The data types below are the raw `pandas.read_csv` types, before cleaning.

| Raw table | Shape | Column | pandas dtype | Blank/missing | Missing % |
|---|---|---|---|---:|---:|
| customers.csv | 1,200 × 5 | `customer_id` | `object` | 0 | 0.00% |
| customers.csv | 1,200 × 5 | `city` | `object` | 0 | 0.00% |
| customers.csv | 1,200 × 5 | `signup_date` | `object` | 0 | 0.00% |
| customers.csv | 1,200 × 5 | `age` | `object` | 61 | 5.08% |
| customers.csv | 1,200 × 5 | `gender` | `object` | 30 | 2.50% |
| products.csv | 40 × 4 | `product_id` | `object` | 0 | 0.00% |
| products.csv | 40 × 4 | `product_name` | `object` | 0 | 0.00% |
| products.csv | 40 × 4 | `category` | `object` | 0 | 0.00% |
| products.csv | 40 × 4 | `price_inr` | `int64` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `order_id` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `customer_id` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `product_id` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `quantity` | `int64` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `order_ts` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `status` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `discount_pct` | `int64` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `order_amount` | `object` | 0 | 0.00% |
| orders.csv | 13,084 × 9 | `delivery_minutes` | `object` | 2,541 | 19.42% |

### Cleaning Checkpoints and Reconciliation

The order cleaning sequence is: parse `order_ts`; remove 119 exact duplicates; retain the latest timestamp for each `order_id` (656 additional versions removed); convert and repair invalid `order_amount` using `round(price_inr * quantity * (1 - discount_pct / 100), 2)`; convert negative delivery durations to missing; impute completed-order delivery times from completed-order category medians; leave cancelled-order delivery times missing. Customer cleaning strips/title-cases city names, maps gender variants to `male`, `female`, or `unknown`, replaces invalid ages using city medians, and parses signup dates. Products retain the supplied catalogue fields.

The raw audit counts **120** nonnumeric order amounts and **106** negative delivery durations. The cleaning log reports **112** repaired amounts and **105** negative delivery durations corrected in retained rows. These counts refer to different stages: raw rows versus rows remaining after duplicate/version removal. They should not be interpreted as unexplained uncorrected values; the final validation checks that every retained amount is numeric and every completed delivery duration is present.

Final checks include 12,309 unique orders, no pending orders, 11,110 completed and 1,199 cancelled orders, no missing completed delivery times, and cancelled delivery times left missing. The cleaned tables are written to `data/clean/` and to `data/instamart.db` (`customers`, `products`, `orders`). The validation run prints `ALL CHECKPOINTS PASSED`.

### Pandas Cross-Check and Exploratory Analysis

A `pd.pivot_table(..., margins=True)` of completed-order revenue by city and product category agrees with SQL Q2: **INR 2,998,668.80**. Grouped city revenue, mean amount and completed-order count include Bengaluru (INR 523,643.40; mean INR 276.47; 1,894 orders) and Mumbai (INR 479,058.50; mean INR 297.00; 1,613 orders), matching the brief's checkpoints.

For completed `order_amount`: mean INR 269.91, median INR 135.00, skewness approximately 4.61, Q1 INR 64.80, Q3 INR 297.00, IQR INR 232.20, lower fence INR -283.50 and upper fence INR 645.30. There are **897** values above the upper fence and **zero** below the lower fence.

**Four EDA questions (under 200 words total):**

1. **What is the data about?** Synthetic customer purchases, products, cities, order amounts, discounts, quantities and delivery durations across the six cities.
2. **What do the distributions and statistics look like?** Completed-order amounts are strongly right-skewed: the mean (INR 269.91) is well above the median (INR 135.00).
3. **Are there outliers or anomalies?** The 1.5×IQR rule identifies 897 high-value completed orders. Raw exports also contain duplicates, invalid amounts and delivery durations, which are handled by the documented cleaning pipeline.
4. **What relationships exist between variables?** Among `order_amount`, `discount_pct`, `quantity` and `delivery_minutes`, the strongest reported absolute correlation is between amount and discount (approximately −0.095); amount and quantity is approximately +0.087. These are weak associations and do not establish causation.

## Part B 
RFM uses completed orders and a fixed snapshot date. K-means diagnostics compare K=2..8; K=4 was selected based on the silhouette diagnostics. Lapse features use orders strictly before 2025-09-01, while the label uses September outcomes. The pipeline uses a preprocessing Pipeline fitted on training rows, GridSearchCV and a saved joblib model. The Premium retention list is illustrative only because the Premium label uses the whole RFM window and is post-hoc; it is not a leakage-free evaluation.

### K-Means Cluster Selection
K-Means clustering was evaluated for K=2 through K=8 using StandardScaler, `n_init=10`, and `random_state=42`.

**K=4 was selected** because it achieved the highest silhouette score (0.526), while inertia decreased substantially from 1,268.23 at K=3 to 743.07 at K=4. It also produced four actionable customer segments: Premium, Frequent, Regular, and At Risk.

K=8 has lower inertia than K=2 because increasing the number of clusters reduces or maintains the distance between observations and their assigned centroids. However, inertia alone is insufficient for selecting K because too many clusters can fragment customers into groups that are less meaningful for business campaigns.

### Customer Segment Profiles and Recommended Actions
The K-Means model identified four customer segments using Recency, Frequency, and Monetary (RFM) values.

| Segment ID | Segment Name | Customers | Mean Recency (Days) | Mean Frequency | Mean Monetary (₹) |
|---|---|---:|---:|---:|---:|
| 0 | Regular | 436 | 28.86 | 3.77 | 1,057.62 |
| 1 | Premium | 138 | 24.12 | 6.77 | 7,129.70 |
| 2 | Frequent | 419 | 8.77 | 19.40 | 3,410.02 |
| 3 | At Risk | 182 | 109.04 | 2.20 | 685.99 |

**Recommended business actions:**

- **Regular:** Encourage repeat purchases through personalised product recommendations.

- **Premium:** Offer VIP benefits and personalised retention campaigns.

- **Frequent:** Reward consistent purchasing behaviour and introduce cross-category bundles.

- **At Risk:** Launch reactivation campaigns with targeted offers.

The Premium segment is identified by the highest mean monetary value (₹7,129.70), not by its cluster number. Cluster IDs are arbitrary labels and do not indicate customer value or ranking.

**PCA results:** The first two principal components explain 63.43% and 21.80% of the variance, respectively, giving a combined explained variance of **85.23%**.

### Customer Lapse Prediction
**Problem definition and data leakage prevention**

The prediction cutoff was September 1, 2025. Customers with at least one completed order before this date were included in the cohort. A customer was labelled `lapsed = 1` if they placed no completed orders during September 2025; otherwise, `lapsed = 0`.

The dataset contained **1,156 customers**, including **443 lapsed customers (38.32%)**. A stratified 80:20 split produced 924 training customers and 232 test customers.

All predictive features were constructed from orders strictly before September 1, 2025, and the cleaned customer table. The whole-window customer segment labels were excluded from the model features. Missing-value imputation, numeric standardisation, and one-hot encoding with `drop="first"` were performed inside scikit-learn pipelines, ensuring that preprocessing parameters were learned only from training data. No encoder, scaler, or resampler was fitted on test rows.

**Baseline and model performance**

Always predicting "not lapsed" produced a test accuracy of **61.64%**, but precision, recall, and F1 for the lapsed class were all zero.

Both Logistic Regression and Random Forest were tuned using five-fold cross-validation with F1 scoring.

| Metric | Logistic Regression | Random Forest |
|---|---:|---:|
| Best parameters | C = 100 | max_depth = 8, min_samples_leaf = 10 |
| Cross-validation F1 | 0.651 | 0.687 |
| Test precision | 0.644 | 0.633 |
| Test recall | 0.652 | 0.640 |
| Test F1 | 0.648 | 0.637 |

**Test confusion matrices** (rows: actual class 0 and 1; columns: predicted class 0 and 1):

- Logistic Regression: `[[111, 32], [31, 58]]`

- Random Forest: `[[110, 33], [32, 57]]`

**Model selection**

Random Forest was selected because it achieved the higher five-fold cross-validation F1 score (0.687 compared with 0.651), providing a training-only basis for selection without using the test set to choose the model. Its test F1 of 0.637 exceeded the required minimum of 0.55. Missing a genuinely lapsing customer means losing an opportunity to intervene before disengagement, whereas incorrectly targeting a loyal customer may waste promotional resources. Both errors matter, so F1 provides a useful balance between recall and precision, although a retention team prioritising recall might choose a different operating threshold.

**Test Accuracy Comparison**

Accuracy was calculated from the previously recorded test confusion matrices, without retraining or modifying either model.

| Model | Correct Predictions | Test Accuracy |
|---|---:|---:|
| Logistic Regression | 169 / 232 | 72.84% |
| Random Forest | 167 / 232 | 71.98% |

Logistic Regression achieved slightly higher test accuracy and F1 score. However, Random Forest was selected based on its higher training cross-validation F1 score (0.687 versus 0.651), avoiding model selection based solely on test-set performance.

Accuracy is reported as an additional metric; precision, recall, and F1 remain important for evaluating customer lapse prediction.

**Scaler verification**

The training-fitted scaler learned a mean frequency of **8.1147**, while the full-cohort mean was **8.0285**. These differ because the scaler was fitted only on training rows, while the full-cohort calculation also includes test customers.

### Class-Balance Experiment
The lapsed class was the minority in the training dataset. To address this imbalance, random oversampling was applied **only to the training set**, using `random_state=42`. Minority-class training rows were duplicated with replacement until both classes contained 570 observations. The original test set remained unchanged.

The best Logistic Regression hyperparameter (`C=100`) was used for the comparison.

| Metric | Original Training | Oversampled Training |
|---|---:|---:|
| Precision | 0.6444 | 0.5891 |
| Recall | 0.6517 | 0.8539 |
| F1 | 0.6480 | 0.6972 |

**Interpretation:** Recall showed the largest change, increasing by approximately 20.22 percentage points, while precision decreased by 5.53 percentage points. The oversampled model identified more genuinely lapsing customers, reducing missed retention opportunities, but also incorrectly flagged more loyal customers. This trade-off may be acceptable when the cost of losing a customer exceeds the cost of sending an unnecessary retention offer.

Oversampling was performed after the train/test split, and no test observations were used to create the balanced training dataset.

### Model Interpretability and Persistence
**Random Forest — Top Five Important Features**

| Feature | Importance | Business Interpretation |
|---|---:|---|
| Monetary | 0.2804 | Total historical spending is an important predictor of customer lapse. |
| Frequency | 0.2779 | Historical purchasing frequency contributes strongly to identifying disengagement risk. |
| Recency | 0.1091 | The time since a customer's last completed order helps distinguish lapse behaviour. |
| Average Delivery Time | 0.0597 | Historical delivery experience contributes to the model's predictions. |
| Cancellation Rate | 0.0518 | Past cancellation behaviour provides additional information about lapse risk. |

Feature importance indicates predictive contribution, not whether a feature increases or decreases lapse probability, and does not establish causation.

**Logistic Regression — Coefficient Interpretation**

| Feature | Coefficient | Interpretation |
|---|---:|---|
| Recency | +0.0392 | Higher recency is associated with higher predicted lapse odds, holding other features constant. |
| Frequency | −1.6973 | More frequent historical purchasing is associated with lower predicted lapse odds, holding other features constant. |
| Monetary | +0.2834 | Higher historical spending is associated with higher predicted lapse odds after accounting for other model features. |

These coefficients apply to standardised numerical features. Their signs describe model associations, not causal effects.

**Model Persistence**

The selected Random Forest pipeline was saved to `outputs/lapse_model.joblib` using `joblib.dump`. After reloading it using `joblib.load`, an exact comparison confirmed that its predictions on the untouched test set were identical to those produced before saving.

**Premium Customer Retention List**

The top 10 Premium test-set customers were ranked by predicted lapse probability and saved to `outputs/retention_list.csv`, containing `customer_id`, `lapse_probability`, and `actually_lapsed`.

Of the 10 selected customers, **1 actually lapsed**.

**Important limitation:** The Premium flag comes from whole-window RFM segmentation, which includes September 2025—the same period used to define the lapse label. Therefore, this retention list is a post-hoc illustration and **must not be treated as a leakage-free evaluation**. Premium segment labels were never used as predictive model features.

## Part C 
Empty and overlong tickets are skipped before model calls. Email, phone and order ID patterns are redacted before prompting. Retries handle simulated transient errors. JSON category values are allow-listed; malformed outputs are accepted only when exactly one allowed category is detectable using `re.findall`. Human review receives guardrail/invalid/budget cases, fraud goes to security, premium customers go to the premium desk, and the rest go to the support queue.


The support-ticket triage pipeline processes 164 tickets in their original order using the supplied mock LLM. It applies input guardrails, privacy redaction, retry handling, strict output validation, token budgeting, and customer-segment-aware routing.

**Input Safety and Privacy**

- Four empty tickets were skipped, and four overlong tickets were flagged before any model call.

- Redaction followed the required order: email → phone → order ID.

- The privacy audit recorded 55 email, 91 phone, and 132 order-ID substitutions (278 total).

- Assertions verified that none of the three specified identifier patterns remained in the redacted text.

- The model received only the redacted ticket text as its user-message content.

**Resilience and Output Validation**

- Each full run recovered all 19 simulated transient errors using exponential backoff with jitter.

- Of the 156 eligible tickets, 135 were accepted as valid JSON classifications, 12 through the single-keyword fallback, and 9 were flagged for human review.

- Invalid categories and ambiguous outputs were never assigned guessed classifications.

**Zero-Shot vs Few-Shot Comparison**

| Metric | Zero-shot | Few-shot |
|---|---:|---:|
| Classified tickets | 147 | 147 |
| Correct classifications | 126 | 147 |
| Accuracy | 85.71% | 100.00% |
| Total tokens | 8,464 | 13,768 |
| Tokens per classified ticket | 57.58 | 93.66 |

The zero-shot confusion table showed 21 errors: 11 fraud tickets and 10 technical tickets were classified as billing. Few-shot prompting eliminated these errors in the mock experiment. Although few-shot used 5,304 additional tokens (approximately 62.7% more), the improvement may justify the cost when accurate fraud and technical routing is important.

**Token Budget and Routing**

A zero-shot run with a 6,000-token budget produced 45 `budget_exhausted` tickets, which were routed to human review. The recorded token total was 6,027 because the budget is checked before each call rather than limiting an individual call's usage.

The final few-shot run routed 102 tickets to `support_queue`, 34 to `security_team`, 11 to `premium_desk`, and 17 to `human_review`. Fraud tickets took precedence over Premium routing. Customers without a segment record were treated as non-Premium.

**Generated Outputs**

- `outputs/triage_results.csv` — final few-shot results for all 164 tickets.

- `outputs/triage_budget_demo.csv` — zero-shot budget demonstration with 45 exhausted tickets.

These results describe a deterministic mock-LLM experiment, not measured performance of a production language model.

**Part B–Part C Integration Verification**

The final Part C output was independently validated against `outputs/customer_segments.csv` using `tests/test_part_b_c_integration.py`. All 164 tickets passed the segment-name, routing, and priority assertions. The integration identified 138 Premium customers in Part B and verified that 11 tickets were routed to `premium_desk`, 34 to `security_team`, and 17 to `human_review`. Fraud routing takes precedence over Premium status, while missing customer segments are treated as non-Premium.

## Part D 
Policy documents are chunked with overlap, represented with `TfidfVectorizer`, and ranked using cosine similarity. The offline mock returns context-derived sentences. Refund rules are implemented in Python tools backed by SQLite: completed orders delivered in over 45 minutes qualify for a full refund; orders over INR 1000 escalate instead of auto-issuing. This is a simulation, not a payment integration.

### RAG Evaluation — Chunk Overlap Comparison
| Evaluation metric | 40-word chunks, 10-word overlap | 40-word chunks, zero overlap |
|---|---:|---:|
| Expected policy document in top-3 retrieval | 12/12 | 12/12 |
| Generated answer contains expected fact | 12/12 | 10/12 |
| Correct fallback for unanswerable questions | 2/2 | 2/2 |

**Findings:** With 10-word overlap, all 12 answerable questions returned the expected factual information. Removing overlap reduced factual accuracy to 10/12, although document retrieval remained perfect.

Two questions failed the exact-fact check without overlap:

- Full refund eligibility based on delivery time.

- Refund timing for a failed payment that was deducted.

Chunk overlap reduces the risk of separating related information at chunk boundaries. The results demonstrate that retrieving the correct document does not necessarily guarantee a complete factual answer.

### Refund Agent — Seven-Scenario Evaluation
The refund agent uses the supplied offline `mock_llm.py` and five Python tools: `get_order`, `search_policy`, `calculate_refund`, `issue_refund`, and `escalate_to_human`. The agent reads order details from SQLite and reuses the policy retrieval component. Refunds are simulated using a local JSONL ledger; no real payment is processed.

The seven supplied scenarios were evaluated using `python -m src.evaluate_agent`.

| Scenario | Status | Refund amount (INR) | Model calls | Tokens used |
|---|---|---:|---:|---:|
| S1 | REFUND | 128.25 | 5 | 897 |
| S2 | REFUND | 135.00 | 5 | 897 |
| S3 | ESCALATE | 1,999.00 | 5 | 884 |
| S4 | DENIED | 0.00 | 4 | 605 |
| S5 | DENIED | 0.00 | 3 | 337 |
| S6 | NOT_FOUND | 0.00 | 2 | 72 |
| S7 | FALLBACK_MAX_ITERATIONS | 0.00 | 6 | 3,000 |

**Evaluation result: 7/7 scenarios passed.** S3 was escalated for human approval rather than automatically refunded. S7 exhausted the maximum of six iterations without completing a refund.

### Stop-Safely Demonstrations
| Demonstration | Observed status |
|---|---|
| S1 with `token_limit=200` | FALLBACK_TOKEN_LIMIT |
| S1 with `time_limit_seconds=0` | FALLBACK_TIMEOUT |
| S7 with `max_iterations=6` and default token limit | FALLBACK_MAX_ITERATIONS |

The token-limit check prevents execution of a newly requested tool after the budget is exceeded. The timeout check occurs before the model call at the start of an iteration. Each fallback returns a human-handoff message and the execution history available at that point.

### Crash Recovery and Checkpointing
Crash recovery was demonstrated using S1, with a simulated crash immediately after the second tool execution and its checkpoint.

The complete sequence across the initial run and the resumed run was:

1. `get_order`

2. `search_policy`

3. `calculate_refund`

4. `issue_refund`

**Final resumed status:** REFUND  

**Refund amount:** INR 128.25  

**Total tool executions:** 4, with no repeated execution in this demonstration.

The agent saves its messages, token usage, step number, and executed tools to a JSON checkpoint. `resume_agent(run_id)` restores this information and continues from the saved state. This demonstrates recovery from the specified simulated crash; it does not guarantee exactly-once execution if a real process crashes during a ledger write before checkpointing.

### ReAct Versus Plan-and-Execute
The implemented agent follows a ReAct-style process, alternating model calls with tool execution and observation. S1 required five model calls and 897 tokens, S5 required three calls and 337 tokens, and S6 required two calls and 72 tokens.

A plan-and-execute design would request the complete tool sequence in an initial planning call and replan only when necessary. This could reduce model-call overhead and token consumption, although the exact savings were not measured in this project.

ReAct is more adaptive to unexpected observations. For example, an unknown order can produce NOT_FOUND without proceeding to refund calculation, while a cancelled order can be denied after its status is retrieved. A fixed plan must incorporate explicit conditions or replan to handle these cases safely.

For this refund workflow, ReAct is the implemented approach because it checks observations between actions. However, the refund eligibility and approval limits must remain enforced in Python tools rather than relying solely on the model's decisions.

## Limitations and Next Steps

- **Retention-list leakage caveat:** Premium membership comes from whole-window RFM segmentation, including the September 2025 label window. The top-10 Premium retention list is illustrative and **not a leakage-free evaluation**. The lapse model's own features use only pre-cutoff information and do not include whole-window segment labels.
- **Offline simulation:** `mock_llm.py` is a deterministic mock, not a production language model. Reported triage and policy performance applies to this synthetic evaluation only.
- **Refund idempotency and concurrency:** The JSONL ledger blocks sequential duplicate `issue_refund` requests for the same order. A temporary-ledger test confirmed one entry for two sequential requests; the seven-scenario evaluation passed twice, and the simulated crash-resume regression passed with one refund entry. The read/check/append operation is **not atomic**, so simultaneous requests may race. A production design would require transactional uniqueness and payment-provider idempotency, but neither is implemented here.
- **Crash-recovery scope:** The demonstrated checkpoint recovery follows a simulated crash after two completed tools. It does not establish exactly-once execution across arbitrary real process failures, particularly a crash between ledger writing and checkpointing.
- **Operational scope:** There is no live payment processing, live support deployment or production security/monitoring infrastructure; those are outside the capstone implementation.
