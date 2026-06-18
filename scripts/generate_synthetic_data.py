#!/usr/bin/env python3
"""
Deterministic synthetic-data generator for the Acme Data Platform AI agent.

ONE in-memory MODEL -> projects EVERY data file so all 16 tools return rich,
internally-consistent results. Everything fictional (company "Acme"). No real
production data. Fully deterministic: no random / no datetime.now().

Run from repo root:  python3 scripts/generate_synthetic_data.py
Lives in scripts/ (never under src/, never imported at runtime) so it can never
scrub/overwrite itself.
"""
import json, hashlib, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
DP = ROOT / "src" / "data_platform"
CACHE = DP / "cache"
HIST = DP / "history"

BASE = datetime(2026, 6, 1, 2, 30, tzinfo=timezone.utc)   # fixed anchor
NOWISH = datetime(2026, 6, 17, 14, 0, tzinfo=timezone.utc)  # "recent" anchor (~1d before 2026-06-18)

def ts(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
def sha(seed): return hashlib.sha1(seed.encode()).hexdigest()[:8]

def urn(name): return f"urn:li:dataset:(urn:li:dataPlatform:hdfs,{name},PROD)"
def flow_urn(project): return f"urn:li:dataFlow:(airflow,{project},PROD)"
def cref_urn(slug): return f"urn:li:dataset:(urn:li:dataPlatform:confluence_ref,{slug},PROD)"

# ───────────────────────────── TEAMS ──────────────────────────────
TEAMS = {
    "core":      {"id": "team:data-platform-core", "name": "Data Platform Core", "slack": "#data-eng-oncall", "lead": "Tâm Nguyễn"},
    "lending":   {"id": "team:lending-data",       "name": "Lending Data",       "slack": "#credit-oncall",   "lead": "Bình Trần"},
    "payments":  {"id": "team:payments-data",      "name": "Payments Data",      "slack": "#payments-data",   "lead": "Hùng Lê"},
    "identity":  {"id": "team:identity-platform",  "name": "Identity Platform",  "slack": "#identity-oncall", "lead": "Mai Phạm"},
    "risk":      {"id": "team:risk-engineering",   "name": "Risk Engineering",   "slack": "#risk-oncall",     "lead": "Sơn Đỗ"},
    "fraud":     {"id": "team:fraud-detection",    "name": "Fraud Detection",    "slack": "#fraud-oncall",    "lead": "Linh Vũ"},
    "marketing": {"id": "team:marketing-analytics","name": "Marketing Analytics","slack": "#marketing-data",  "lead": "Quân Hoàng"},
    "finance":   {"id": "team:finance-analytics",  "name": "Finance Analytics",  "slack": "#finance-data",    "lead": "Hà Đặng"},
}
# pure cross-team CONSUMERS (own consumer datasets only, no producer project)
CONSUMERS = {
    "col": {"name": "Collections", "space": "COL"},
    "cs":  {"name": "Customer Support Analytics", "space": "CSA"},
}

# ─────────────────────────── PROJECTS (6) ──────────────────────────
# name kept fictional; "credit-curated-etl" preserved (monitor _CRITICAL_PIPELINES).
PROJECTS = {
    "lending-ingest-etl":      {"team": "lending",   "domain": "lending",   "flow": "batch",     "desc": "Ingest raw installment-loan core tables from the lending service into HDFS (batch T-1)."},
    "credit-curated-etl":      {"team": "core",      "domain": "lending",   "flow": "batch",     "desc": "Build the curated credit zone (staging + facts + daily risk mart) from the loan core tables."},
    "qrpay-streaming-svc":     {"team": "payments",  "domain": "payment",   "flow": "streaming", "desc": "Spark Structured Streaming jobs that ingest and enrich QR-pay transaction events in near real-time."},
    "merchant-mart-etl":       {"team": "payments",  "domain": "merchant",  "flow": "batch",     "desc": "Daily merchant dimension + revenue marts joining merchant profile with QR-pay settlement."},
    "identity-resolution-etl": {"team": "identity",  "domain": "identity",  "flow": "batch",     "desc": "Resolve device/identity graph and publish the identity mart + bank-code reference (batch T-1)."},
    "platform-etl-lib":        {"team": "core",      "domain": "infra",     "flow": "batch",     "desc": "Shared reference/lookup tables and the data-quality result tables produced by the platform DQ framework."},
    "risk-scorecard-etl":      {"team": "risk",      "domain": "risk",      "flow": "batch",     "desc": "Credit-risk scorecards, PD/LGD model features and the daily NPL/exposure marts consumed by Risk."},
    "fraud-signal-streaming":  {"team": "fraud",     "domain": "fraud",     "flow": "streaming", "desc": "Near-real-time fraud signals and rule hits computed from the QR-pay enriched stream."},
    "marketing-segment-etl":   {"team": "marketing", "domain": "marketing", "flow": "batch",     "desc": "Customer segments, campaign audiences and engagement marts built from identity + payment data."},
    "finance-reporting-etl":   {"team": "finance",   "domain": "finance",   "flow": "batch",     "desc": "GL postings, revenue recognition and P&L reporting marts feeding Finance dashboards (batch T-1)."},
}

# ─────────────────────────── TABLES (30) ───────────────────────────
# (short_leaf, dotted_name, project, tier, flow, domain, [upstream_leaves], col_archetype, pii)
# upstream_leaves reference other table leaves OR "ext:<source>" for external; pipeline link added automatically.
ST, BT = "streaming", "batch"
TABLES = [
    # P1 lending-ingest-etl (raw, batch T-1)
    ("loan_core_account",  "acme.secure.lending_svc.installment.loan_core_account",  "lending-ingest-etl", "Tier1", BT, "lending", ["ext:lending-svc"], "loan_account", True),
    ("loan_core_order",    "acme.secure.lending_svc.installment.loan_core_order",    "lending-ingest-etl", "Tier1", BT, "lending", ["ext:lending-svc"], "loan_order", True),
    ("loan_core_bill",     "acme.secure.lending_svc.installment.loan_core_bill",     "lending-ingest-etl", "Tier1", BT, "lending", ["ext:lending-svc"], "loan_bill", True),
    ("loan_core_statement","acme.secure.lending_svc.installment.loan_core_statement","lending-ingest-etl", "Tier1", BT, "lending", ["ext:lending-svc"], "loan_statement", True),
    ("loan_core_user",     "acme.secure.lending_svc.installment.loan_core_user",     "lending-ingest-etl", "Tier1", BT, "lending", ["ext:lending-svc"], "loan_user", True),
    # P2 credit-curated-etl (staging + curated, batch T-1)
    ("stg_loan_statement",   "acme.analytics.staging.credit.stg_loan_statement",   "credit-curated-etl", "Tier2", BT, "credit", ["loan_core_statement", "loan_core_bill"], "loan_statement", True),
    ("loan_statement_fact",  "acme.analytics.curated.credit.loan_statement_fact",  "credit-curated-etl", "Tier1", BT, "credit", ["stg_loan_statement"], "loan_statement_fact", False),
    ("loan_account_dim",     "acme.analytics.curated.credit.loan_account_dim",     "credit-curated-etl", "Tier1", BT, "credit", ["loan_core_account", "loan_core_user"], "loan_account_dim", True),
    ("loan_payment_fact",    "acme.analytics.curated.credit.loan_payment_fact",    "credit-curated-etl", "Tier2", BT, "credit", ["stg_loan_statement"], "loan_payment_fact", False),
    ("credit_risk_daily_mart","acme.analytics.curated.credit.credit_risk_daily_mart","credit-curated-etl","Tier1", BT, "credit", ["loan_statement_fact", "loan_account_dim"], "risk_mart", False),
    # P3 qrpay-streaming-svc (streaming + near-rt)
    ("qrpay_txn_stream",        "acme.payment.qrpay.raw.qrpay_txn_stream",        "qrpay-streaming-svc", "Tier1", ST, "payment", ["ext:qrpay-gateway"], "qrpay_txn", False),
    ("qrpay_txn_enriched",      "acme.payment.qrpay.rt.qrpay_txn_enriched",       "qrpay-streaming-svc", "Tier1", ST, "payment", ["qrpay_txn_stream", "bank_code_mapping"], "qrpay_txn", False),
    ("qrpay_refund_stream",     "acme.payment.qrpay.raw.qrpay_refund_stream",     "qrpay-streaming-svc", "Tier2", ST, "payment", ["ext:qrpay-gateway"], "qrpay_refund", False),
    ("qrpay_merchant_settlement","acme.payment.qrpay.curated.qrpay_merchant_settlement","qrpay-streaming-svc","Tier2", BT, "payment", ["qrpay_txn_enriched"], "settlement", False),
    ("qrpay_daily_volume_mart", "acme.payment.qrpay.curated.qrpay_daily_volume_mart","qrpay-streaming-svc","Tier2", BT, "payment", ["qrpay_txn_enriched"], "volume_mart", False),
    # P4 merchant-mart-etl (batch daily)
    ("stg_merchant_profile",      "acme.merchant.staging.stg_merchant_profile",      "merchant-mart-etl", "Tier3", BT, "merchant", ["ext:merchant-svc"], "merchant", False),
    ("stg_merchant_kyc_status",   "acme.merchant.staging.stg_merchant_kyc_status",   "merchant-mart-etl", "Tier2", BT, "merchant", ["ext:merchant-svc"], "merchant_kyc", True),
    ("merchant_dim",              "acme.merchant.curated.merchant_dim",              "merchant-mart-etl", "Tier2", BT, "merchant", ["stg_merchant_profile", "bank_code_mapping"], "merchant", False),
    ("merchant_revenue_mart",     "acme.merchant.curated.merchant_revenue_mart",     "merchant-mart-etl", "Tier2", BT, "merchant", ["merchant_dim", "qrpay_merchant_settlement"], "revenue_mart", False),
    ("merchant_active_daily_mart","acme.merchant.curated.merchant_active_daily_mart","merchant-mart-etl", "Tier3", BT, "merchant", ["merchant_dim"], "active_mart", False),
    # P5 identity-resolution-etl (batch T-1)
    ("stg_identity_events",  "acme.identity.staging.stg_identity_events",  "identity-resolution-etl", "Tier3", BT, "identity", ["ext:identity-svc"], "identity_event", True),
    ("identity_graph",       "acme.identity.curated.identity_graph",       "identity-resolution-etl", "Tier2", BT, "identity", ["stg_identity_events"], "identity_graph", True),
    ("identity_mart",        "acme.analytics.warehouse.identity_mart",     "identity-resolution-etl", "Tier1", BT, "identity", ["identity_graph"], "identity_mart", True),
    ("bank_code_mapping",    "acme.analytics.warehouse.bank_code_mapping", "identity-resolution-etl", "Tier1", BT, "reference", ["ext:napas-ref"], "bank_code", False),
    ("identity_device_dim",  "acme.identity.curated.identity_device_dim",  "identity-resolution-etl", "Tier3", BT, "identity", ["stg_identity_events"], "device_dim", False),
    # P6 platform-etl-lib (reference + DQ, batch daily)
    ("currency_dim",         "acme.reference.lookup.currency_dim",         "platform-etl-lib", "Tier3", BT, "reference", ["ext:ops-config"], "currency", False),
    ("calendar_dim",         "acme.reference.lookup.calendar_dim",         "platform-etl-lib", "Tier3", BT, "reference", ["ext:ops-config"], "calendar", False),
    ("product_catalog_dim",  "acme.reference.lookup.product_catalog_dim",  "platform-etl-lib", "Tier3", BT, "reference", ["ext:ops-config"], "product", False),
    ("dq_check_results",     "acme.dataquality.result.dq_check_results",   "platform-etl-lib", "Tier2", BT, "dataquality", ["ext:dq-framework"], "dq_result", False),
    ("dq_freshness_log",     "acme.dataquality.result.dq_freshness_log",   "platform-etl-lib", "Tier2", BT, "dataquality", ["ext:dq-framework"], "dq_fresh", False),
    # P7 risk-scorecard-etl (Risk Engineering, batch) — consumes lending+identity → organic cross-team
    ("risk_feature_store",      "acme.risk.curated.risk_feature_store",       "risk-scorecard-etl", "Tier1", BT, "risk", ["loan_account_dim", "loan_statement_fact", "identity_mart"], "risk_feature", True),
    ("credit_risk_scorecard",   "acme.risk.curated.credit_risk_scorecard",    "risk-scorecard-etl", "Tier1", BT, "risk", ["risk_feature_store"], "scorecard", True),
    ("pd_model_scores",         "acme.risk.curated.pd_model_scores",          "risk-scorecard-etl", "Tier2", BT, "risk", ["risk_feature_store"], "model_score", False),
    ("lgd_model_scores",        "acme.risk.curated.lgd_model_scores",         "risk-scorecard-etl", "Tier2", BT, "risk", ["risk_feature_store"], "model_score", False),
    ("npl_exposure_daily_mart", "acme.risk.curated.npl_exposure_daily_mart",  "risk-scorecard-etl", "Tier1", BT, "risk", ["credit_risk_scorecard", "loan_statement_fact"], "npl_mart", False),
    ("risk_limit_dim",          "acme.risk.curated.risk_limit_dim",           "risk-scorecard-etl", "Tier3", BT, "risk", ["ext:risk-config"], "risk_limit", False),
    ("collection_priority_mart","acme.risk.curated.collection_priority_mart", "risk-scorecard-etl", "Tier2", BT, "risk", ["npl_exposure_daily_mart"], "collection_mart", True),
    # P8 fraud-signal-streaming (Fraud Detection, streaming) — consumes qrpay enriched
    ("fraud_txn_signal",   "acme.fraud.rt.fraud_txn_signal",    "fraud-signal-streaming", "Tier1", ST, "fraud", ["qrpay_txn_enriched"], "fraud_signal", False),
    ("fraud_rule_hits",    "acme.fraud.rt.fraud_rule_hits",     "fraud-signal-streaming", "Tier1", ST, "fraud", ["fraud_txn_signal"], "fraud_rule", False),
    ("device_risk_score",  "acme.fraud.rt.device_risk_score",   "fraud-signal-streaming", "Tier2", ST, "fraud", ["qrpay_txn_enriched", "identity_device_dim"], "device_risk", False),
    ("fraud_case_mart",    "acme.fraud.curated.fraud_case_mart","fraud-signal-streaming", "Tier2", BT, "fraud", ["fraud_rule_hits"], "fraud_case", True),
    ("blocklist_dim",      "acme.fraud.curated.blocklist_dim",  "fraud-signal-streaming", "Tier3", BT, "fraud", ["ext:fraud-config"], "blocklist", True),
    # P9 marketing-segment-etl (Marketing Analytics, batch) — consumes identity+payment
    ("customer_segment_dim",      "acme.marketing.curated.customer_segment_dim",      "marketing-segment-etl", "Tier2", BT, "marketing", ["identity_mart", "loan_account_dim"], "segment_dim", True),
    ("campaign_dim",              "acme.marketing.curated.campaign_dim",              "marketing-segment-etl", "Tier3", BT, "marketing", ["ext:campaign-config"], "campaign_dim", False),
    ("campaign_audience_mart",    "acme.marketing.curated.campaign_audience_mart",    "marketing-segment-etl", "Tier2", BT, "marketing", ["customer_segment_dim", "campaign_dim"], "audience_mart", True),
    ("engagement_event_log",      "acme.marketing.raw.engagement_event_log",          "marketing-segment-etl", "Tier3", BT, "marketing", ["ext:attribution-sdk"], "engagement_log", False),
    ("marketing_attribution_mart","acme.marketing.curated.marketing_attribution_mart","marketing-segment-etl", "Tier2", BT, "marketing", ["engagement_event_log", "qrpay_daily_volume_mart"], "attribution_mart", False),
    ("ltv_prediction_mart",       "acme.marketing.curated.ltv_prediction_mart",       "marketing-segment-etl", "Tier2", BT, "marketing", ["customer_segment_dim", "loan_statement_fact"], "ltv_mart", False),
    # P10 finance-reporting-etl (Finance Analytics, batch) — consumes payment+lending+merchant
    ("gl_posting_fact",          "acme.finance.curated.gl_posting_fact",          "finance-reporting-etl", "Tier1", BT, "finance", ["qrpay_merchant_settlement", "loan_payment_fact"], "gl_fact", False),
    ("revenue_recognition_fact", "acme.finance.curated.revenue_recognition_fact", "finance-reporting-etl", "Tier1", BT, "finance", ["gl_posting_fact"], "revenue_fact", False),
    ("pnl_daily_mart",           "acme.finance.curated.pnl_daily_mart",           "finance-reporting-etl", "Tier1", BT, "finance", ["revenue_recognition_fact", "merchant_revenue_mart"], "pnl_mart", False),
    ("fee_income_mart",          "acme.finance.curated.fee_income_mart",          "finance-reporting-etl", "Tier2", BT, "finance", ["qrpay_merchant_settlement"], "fee_mart", False),
    ("chart_of_accounts_dim",    "acme.finance.curated.chart_of_accounts_dim",    "finance-reporting-etl", "Tier3", BT, "finance", ["ext:finance-config"], "coa_dim", False),
    ("finance_close_log",        "acme.finance.curated.finance_close_log",        "finance-reporting-etl", "Tier2", BT, "finance", ["gl_posting_fact"], "close_log", False),
]

# ───────────────────── column archetypes ─────────────────────
def c(n, t): return {"name": n, "type": t}
AUDIT = [c("etl_load_ts", "timestamp"), c("etl_batch_id", "string"), c("source_system", "string"), c("dt", "string")]
PII = [c("user_id", "string"), c("national_id_hash", "string"), c("phone_hash", "string")]
ARCHETYPES = {
    "loan_account":  [c("account_id","string"), c("credit_limit","decimal(18,2)"), c("account_status","string"), c("open_date","date")],
    "loan_order":    [c("order_id","string"), c("account_id","string"), c("merchant_id","string"), c("order_amount","decimal(18,2)"), c("installment_plan","string"), c("status","string")],
    "loan_bill":     [c("bill_id","string"), c("account_id","string"), c("billing_cycle","string"), c("due_date","date"), c("amount_due","decimal(18,2)"), c("paid_amount","decimal(18,2)")],
    "loan_statement":[c("statement_id","string"), c("account_id","string"), c("statement_period","string"), c("statement_date","date"), c("min_pay_amount","decimal(18,2)"), c("outstanding_amount","decimal(18,2)"), c("status","string")],
    "loan_user":     [c("user_id","string"), c("kyc_tier","string"), c("credit_score","int"), c("enroll_date","date")],
    "loan_statement_fact":[c("statement_sk","bigint"), c("account_id","string"), c("statement_date","date"), c("outstanding_amount","decimal(18,2)"), c("min_pay_amount","decimal(18,2)"), c("dpd_bucket","string")],
    "loan_account_dim":   [c("account_sk","bigint"), c("account_id","string"), c("user_id","string"), c("credit_limit","decimal(18,2)"), c("account_status","string")],
    "loan_payment_fact":  [c("payment_sk","bigint"), c("account_id","string"), c("paid_amount","decimal(18,2)"), c("paid_date","date"), c("channel","string")],
    "risk_mart":     [c("report_date","date"), c("segment","string"), c("total_outstanding","decimal(20,2)"), c("npl_ratio","double"), c("active_accounts","bigint")],
    "qrpay_txn":     [c("txn_id","string"), c("merchant_id","string"), c("amount","decimal(18,2)"), c("currency","string"), c("qr_code_id","string"), c("event_ts","timestamp"), c("status","string"), c("partition_hour","string")],
    "qrpay_refund":  [c("refund_id","string"), c("txn_id","string"), c("amount","decimal(18,2)"), c("event_ts","timestamp"), c("reason","string")],
    "settlement":    [c("settlement_date","date"), c("merchant_id","string"), c("gross_amount","decimal(20,2)"), c("fee_amount","decimal(18,2)"), c("net_amount","decimal(20,2)")],
    "volume_mart":   [c("txn_date","date"), c("merchant_id","string"), c("txn_count","bigint"), c("total_amount","decimal(20,2)")],
    "merchant":      [c("merchant_id","string"), c("merchant_name","string"), c("mcc","string"), c("onboard_date","date"), c("status","string")],
    "merchant_kyc":  [c("merchant_id","string"), c("kyc_status","string"), c("doc_type","string"), c("verified_at","timestamp")],
    "revenue_mart":  [c("report_date","date"), c("merchant_id","string"), c("revenue","decimal(20,2)"), c("txn_count","bigint"), c("avg_ticket","decimal(18,2)")],
    "active_mart":   [c("report_date","date"), c("active_merchant_count","bigint"), c("new_merchant_count","bigint")],
    "identity_event":[c("event_id","string"), c("user_id","string"), c("device_id","string"), c("event_type","string"), c("event_ts","timestamp")],
    "identity_graph":[c("identity_id","string"), c("user_id","string"), c("device_id","string"), c("match_score","double"), c("linked_user_ids","array<string>")],
    "identity_mart": [c("identity_id","string"), c("user_id","string"), c("primary_device","string"), c("risk_flag","string"), c("last_seen","date")],
    "bank_code":     [c("bank_code","string"), c("bank_name","string"), c("napas_code","string"), c("active","boolean")],
    "device_dim":    [c("device_sk","bigint"), c("device_id","string"), c("os","string"), c("first_seen","date")],
    "currency":      [c("currency_code","string"), c("currency_name","string"), c("decimals","int")],
    "calendar":      [c("date_key","date"), c("year","int"), c("month","int"), c("is_holiday","boolean")],
    "product":       [c("product_code","string"), c("product_name","string"), c("category","string"), c("effective_date","date")],
    "dq_result":     [c("check_id","string"), c("dataset_urn","string"), c("rule","string"), c("result","string"), c("row_count","bigint"), c("checked_at","timestamp")],
    "dq_fresh":      [c("dataset_urn","string"), c("expected_by","timestamp"), c("actual_ts","timestamp"), c("is_late","boolean")],
    # risk
    "risk_feature":  [c("user_id","string"), c("account_id","string"), c("dpd_max_6m","int"), c("utilization_ratio","double"), c("num_active_loans","int"), c("avg_outstanding_3m","decimal(18,2)"), c("identity_risk_flag","string")],
    "scorecard":     [c("account_id","string"), c("user_id","string"), c("score","int"), c("grade","string"), c("pd_12m","double"), c("score_date","date"), c("model_version","string")],
    "model_score":   [c("account_id","string"), c("score","double"), c("model_version","string"), c("scored_at","timestamp")],
    "npl_mart":      [c("report_date","date"), c("segment","string"), c("total_exposure","decimal(20,2)"), c("npl_amount","decimal(20,2)"), c("npl_ratio","double"), c("provision_amount","decimal(20,2)")],
    "risk_limit":    [c("segment","string"), c("max_limit","decimal(18,2)"), c("policy_version","string"), c("effective_date","date")],
    "collection_mart":[c("account_id","string"), c("user_id","string"), c("dpd","int"), c("outstanding_amount","decimal(18,2)"), c("priority","string"), c("assigned_agent","string")],
    # fraud
    "fraud_signal":  [c("txn_id","string"), c("merchant_id","string"), c("user_id","string"), c("risk_score","double"), c("signal_type","string"), c("event_ts","timestamp")],
    "fraud_rule":    [c("txn_id","string"), c("rule_id","string"), c("rule_name","string"), c("severity","string"), c("action","string"), c("event_ts","timestamp")],
    "device_risk":   [c("device_id","string"), c("user_id","string"), c("risk_score","double"), c("velocity_1h","int"), c("event_ts","timestamp")],
    "fraud_case":    [c("case_id","string"), c("txn_id","string"), c("user_id","string"), c("status","string"), c("loss_amount","decimal(18,2)"), c("opened_at","timestamp")],
    "blocklist":     [c("entity_type","string"), c("entity_value_hash","string"), c("reason","string"), c("added_at","timestamp")],
    # marketing
    "segment_dim":   [c("user_id","string"), c("segment_code","string"), c("segment_name","string"), c("rfm_score","int"), c("refreshed_date","date")],
    "campaign_dim":  [c("campaign_id","string"), c("campaign_name","string"), c("channel","string"), c("start_date","date"), c("end_date","date")],
    "audience_mart": [c("campaign_id","string"), c("user_id","string"), c("segment_code","string"), c("eligible","boolean"), c("snapshot_date","date")],
    "engagement_log":[c("event_id","string"), c("user_id","string"), c("campaign_id","string"), c("event_type","string"), c("event_ts","timestamp")],
    "attribution_mart":[c("report_date","date"), c("channel","string"), c("campaign_id","string"), c("conversions","bigint"), c("attributed_gmv","decimal(20,2)")],
    "ltv_mart":      [c("user_id","string"), c("predicted_ltv","decimal(18,2)"), c("horizon_months","int"), c("model_version","string"), c("scored_date","date")],
    # finance
    "gl_fact":       [c("posting_id","string"), c("account_code","string"), c("amount","decimal(20,2)"), c("currency","string"), c("posting_date","date"), c("source_txn_id","string")],
    "revenue_fact":  [c("report_date","date"), c("revenue_type","string"), c("recognized_amount","decimal(20,2)"), c("currency","string")],
    "pnl_mart":      [c("report_date","date"), c("line_item","string"), c("amount","decimal(20,2)"), c("currency","string")],
    "fee_mart":      [c("report_date","date"), c("merchant_id","string"), c("fee_type","string"), c("fee_amount","decimal(18,2)")],
    "coa_dim":       [c("account_code","string"), c("account_name","string"), c("account_type","string"), c("is_active","boolean")],
    "close_log":     [c("close_period","string"), c("step","string"), c("status","string"), c("completed_at","timestamp")],
}

LEAF2NAME = {t[0]: t[1] for t in TABLES}
LEAF2META = {t[0]: t for t in TABLES}

def schedule_for(flow, tier_idx):
    if flow == "streaming":
        return {"type": "streaming", "frequency": "continuous", "trigger_time": None, "sla_minutes": 5}
    return {"type": "batch", "frequency": "daily", "trigger_time": "02:30 ICT", "lag": "T-1"}

def schema_for(archetype, pii):
    cols = list(ARCHETYPES[archetype])
    if pii:
        cols = PII + cols
    return cols + AUDIT

def desc_for(leaf, project, flow, domain):
    p = PROJECTS[project]
    team = TEAMS[p["team"]]["name"]
    if flow == "streaming":
        cadence = "Cập nhật **streaming** (near real-time, SLA ~5 phút) qua Spark Structured Streaming."
    else:
        cadence = "Chạy **batch daily T-1**, 02:30 ICT qua Airflow DAG `%s`." % project
    return (f"Bảng `{leaf}` thuộc domain **{domain}**, do team **{team}** sở hữu, sinh ra bởi pipeline "
            f"`{project}`. {cadence}")

# ───────────────────── build datasets + pipelines ─────────────────────
def build_datasets():
    out = []
    for i, (leaf, name, project, tier, flow, domain, ups, arch, pii) in enumerate(TABLES):
        p = PROJECTS[project]; team = TEAMS[p["team"]]
        upstream = []
        for u in ups:
            if u.startswith("ext:"):
                continue
            upstream.append(urn(LEAF2NAME[u]))
        # produced tables list the pipeline as an upstream producer
        upstream.append(flow_urn(project))
        tags = [domain, tier.lower()]
        tags += ["streaming", "real-time"] if flow == "streaming" else ["batch", "t-1", "daily"]
        if pii:
            tags.append("pii")
        cols = schema_for(arch, pii)
        # deterministic, realistic stats
        tier_mult = {"Tier1": 50, "Tier2": 12, "Tier3": 3}[tier]
        row_count = (tier_mult * 1_000_000) + (i * 137_000)
        if flow == "streaming":
            last_dt = NOWISH - timedelta(minutes=2 + (i % 5))   # near real-time
        else:
            last_dt = NOWISH.replace(hour=2, minute=30) - timedelta(days=1) + timedelta(minutes=(i % 30))
        last_ms = int(last_dt.timestamp() * 1000)
        out.append({
            "id": urn(name), "name": name, "entityType": "dataset",
            "owner": {"type": "team", "name": team["name"], "slack": team["slack"]},
            "domain": domain, "tier": tier, "status": "active",
            "tags": tags,
            "description": desc_for(leaf, project, flow, domain),
            "schema": cols,
            "lineage": {"upstream": upstream, "downstream": []},
            "metadata": {"schedule": schedule_for(flow, 0),
                         "hierarchy": ["hdfs"] + name.split("."),
                         "stats": {"row_count": row_count, "column_count": len(cols),
                                   "last_modified_ms": last_ms,
                                   "size_gb": round(row_count / 2_500_000, 1),
                                   "partition_key": "dt" if flow == "batch" else "partition_hour"}},
        })
    # wire downstream from upstream (dataset->dataset)
    by_urn = {d["id"]: d for d in out}
    for d in out:
        for u in d["lineage"]["upstream"]:
            if u in by_urn:
                by_urn[u]["lineage"]["downstream"].append(d["id"])
    return out, by_urn

def build_pipelines(by_urn):
    out = []
    for project, p in PROJECTS.items():
        team = TEAMS[p["team"]]
        produced = [urn(LEAF2NAME[t[0]]) for t in TABLES if t[2] == project]
        inputs = []
        for t in TABLES:
            if t[2] != project:
                continue
            for u in t[6]:
                if not u.startswith("ext:"):
                    src = urn(LEAF2NAME[u])
                    if src not in produced and src not in inputs:
                        inputs.append(src)
        flow = p["flow"]
        ds = ("Spark Structured Streaming service." if flow == "streaming"
              else "Airflow batch pipeline (daily T-1).")
        out.append({
            "id": flow_urn(project), "name": project, "entityType": "pipeline",
            "owner": {"type": "team", "name": team["name"], "slack": team["slack"]},
            "domain": f"acme.analytics.{p['domain']}", "tier": "Tier1" if project == "credit-curated-etl" else "Tier2",
            "description": f"{p['desc']} {ds}",
            "files": [f"dags/{project.replace('-', '_')}.py", "README.md", "sql/transform.sql", "config/job.yaml"],
            "lineage": {"upstream": inputs, "downstream": produced},
            "directory_structure": {
                "dags": {f"{project.replace('-', '_')}.py": "file"},
                "sql": {"transform.sql": "file", "schema_checks.sql": "file"},
                "config": {"job.yaml": "file"},
                "tests": {"test_transform.py": "file"},
                "README.md": "file", ".gitlab-ci.yml": "file",
            },
            "metadata": {"branch_tracked": "main", "schedule": schedule_for(flow, 0)},
        })
    return out

# ───────────────────── domains + teams ─────────────────────
DOMAINS = [
    ("domain:lending",  "Lending (Credit / Consumer Loan)",  "Tier1", "core",     "lending",  ["credit","lending","pii","tier1"]),
    ("domain:payment",  "Payment (QR-Pay / Acme Core)",      "Tier1", "payments", "payment",  ["payment","qrpay","streaming","tier1"]),
    ("domain:merchant", "Merchant Ecosystem",                "Tier2", "payments", "merchant", ["merchant","tier2"]),
    ("domain:identity", "Identity (Customer Verification)",  "Tier1", "identity", "identity", ["identity","pii","tier1"]),
    ("domain:data-platform-infra", "Data Platform Infrastructure", "Tier2", "core", "infra", ["infra","data-quality","reference"]),
    ("domain:risk",      "Risk (Credit Risk / Scorecards)", "Tier1", "risk",      "risk",      ["risk","scorecard","pii","tier1"]),
    ("domain:fraud",     "Fraud Detection",                 "Tier1", "fraud",     "fraud",     ["fraud","real-time","tier1"]),
    ("domain:marketing", "Marketing & Growth Analytics",    "Tier2", "marketing", "marketing", ["marketing","segments","tier2"]),
    ("domain:finance",   "Finance & Reporting",             "Tier1", "finance",   "finance",   ["finance","gl","reporting","tier1"]),
]
# a domain "area" may cover several dataset domain labels
AREA_SET = {
    "lending": {"lending", "credit"}, "payment": {"payment"}, "merchant": {"merchant"},
    "identity": {"identity"}, "infra": {"reference", "dataquality", "infra"},
    "risk": {"risk"}, "fraud": {"fraud"}, "marketing": {"marketing"}, "finance": {"finance"},
}
def area_leaves(area):
    members = AREA_SET.get(area, {area})
    return [t[0] for t in TABLES if t[5] in members]

PAGE = {}  # title -> page_id
_pid = [30000000]
def page_id(title):
    if title not in PAGE:
        _pid[0] += 1; PAGE[title] = str(_pid[0])
    return PAGE[title]

def build_domains():
    out = []
    for did, dname, tier, teamk, area, tags in DOMAINS:
        key_ds = [urn(LEAF2NAME[l]) for l in area_leaves(area)][:6]
        key_pl = [flow_urn(pn) for pn, pp in PROJECTS.items() if pp["domain"] == area]
        doc = f"{dname} — Overview"
        out.append({
            "id": did, "name": dname, "entityType": "domain", "tier": tier,
            "description": f"Domain {dname} trên Acme Data Platform.",
            "owner": {"type": "team", "name": TEAMS[teamk]["name"], "slack": TEAMS[teamk]["slack"]},
            "tags": tags, "teams": [TEAMS[teamk]["id"]],
            "metadata": {"key_datasets": key_ds, "key_pipelines": key_pl,
                         "key_docs": [{"title": doc, "page_id": page_id(doc)}]},
        })
    return out

def build_teams():
    out = []
    for k, t in TEAMS.items():
        projs = [pn for pn, pp in PROJECTS.items() if pp["team"] == k]
        doms = sorted({f"domain:{PROJECTS[pn]['domain']}".replace("infra", "data-platform-infra") for pn in projs})
        doc = f"{t['name']} — Onboarding"
        out.append({
            "id": t["id"], "name": t["name"], "entityType": "team",
            "description": f"Team {t['name']} thuộc Acme Data Platform. Sở hữu: {', '.join(projs)}.",
            "owner": {"type": "team", "name": t["name"], "slack": t["slack"], "tech_lead": t["lead"]},
            "tags": ["data-engineering", "owner"], "domains": doms, "projects": projs,
            "metadata": {"onboarding_docs": [{"title": doc, "page_id": page_id(doc)}]},
        })
    return out

# ───────────────────── cross_team ─────────────────────
# consumer team -> [(producer_leaf, domain_label)]
# pure cross-team consumers (extra Confluence-evidence flavor on top of the organic
# cross-team lineage that already exists via risk/fraud/finance owning-team tables).
CONSUMES = {
    "col": [("npl_exposure_daily_mart", "risk"), ("collection_priority_mart", "risk")],
    "cs":  [("fraud_case_mart", "fraud"), ("loan_statement_fact", "lending")],
}
def build_cross_team():
    consumers, edges = [], []
    for ck, items in CONSUMES.items():
        cons = CONSUMERS[ck]
        for leaf, dom in items:
            slug = f"acme.cross_team.{cons['name'].lower().replace(' ', '_')}.{dom}_consumer"
            cid = cref_urn(slug)
            # dedupe consumer entity per (team,domain)
            if not any(c["id"] == cid for c in consumers):
                consumers.append({
                    "id": cid, "name": f"{cons['name']} · {dom} consumer", "entityType": "dataset",
                    "description": (f"Team **{cons['name']}** (Confluence space {cons['space']}) tiêu thụ dữ liệu "
                                    f"{dom} của Data Platform → phụ thuộc downstream."),
                    "tier": "Tier2",
                    "owner": {"type": "team", "name": cons["name"], "space": cons["space"]},
                    "domain": f"domain:{dom}".replace("lending", "lending"),
                    "tags": ["cross-team", "confluence-evidence", dom],
                    "lineage": {"upstream": [urn(LEAF2NAME[leaf])], "downstream": []},
                })
            edges.append({"from": urn(LEAF2NAME[leaf]), "to": cid})
    return {"_comment": "Fully fictional cross-team consumers (synthetic). No real org/PII.",
            "consumer_datasets": consumers, "edges": edges}

# ───────────────────── confluence (knowledge + index + md + tree) ─────────────────────
def safe(t): return "".join(ch if ch.isalnum() else "_" for ch in t)[:60]

def build_confluence():
    # one doc per domain + one per project = good coverage; bodies name table leaves
    knowledge, index, md_files, trees = [], [], {}, {}
    def add(title, domain, team, body_sections, tags):
        pid = page_id(title)
        # knowledge_article entry
        knowledge.append({
            "id": f"urn:li:knowledge:(confluence,{pid},PROD)", "page_id": pid, "name": title,
            "entityType": "knowledge_article", "owner": {"type": "team", "name": team},
            "domain": domain, "tier": "Tier2", "tags": tags,
            "description": body_sections[0][1][:240],
            "relations": {"references": [], "dependsOn": []},
            "content_chunks": [{"chunk_id": f"c{i}", "heading": h, "content": b}
                               for i, (h, b) in enumerate(body_sections)],
        })
        # index entry (mirrors live updater format)
        fname = f"{pid}_{safe(title)}.md"
        index.append({"id": f"urn:li:dataset:(urn:li:dataPlatform:confluence,{pid},PROD)",
                      "page_id": pid, "title": title, "space": "ADP", "file_name": fname, "version": 3})
        # markdown cache
        body = f"# {title}\n**Space:** ADP | **Page ID:** {pid} | **Version:** 3\n\n"
        body += "\n\n".join(f"## {h}\n{b}" for h, b in body_sections)
        md_files[fname] = body
        # tree cache (sections drive DOCUMENTED_BY)
        trees[f"{safe(title)}_{pid}.json"] = {
            "page_id": pid, "title": title, "level": 1,
            "metadata": {"space": "ADP", "version": 3},
            "content_structure": {
                "sections": [{"heading": h, "body": b} for h, b in body_sections],
                "extracted_entities": {"links_and_references": [], "tables": [], "images": []},
            },
            "child_pages": [],
        }
    # domain docs
    for did, dname, tier, teamk, area, tags in DOMAINS:
        leaves = area_leaves(area)
        secs = [
            ("Overview", f"Tài liệu domain {dname}. Các bảng chính: {', '.join(leaves)}."),
            ("Tables", "Chi tiết: " + "; ".join(f"`{l}` ({LEAF2META[l][4]})" for l in leaves) + "."),
            ("Ownership", f"Owner: team {TEAMS[teamk]['name']} ({TEAMS[teamk]['slack']})."),
        ]
        add(f"{dname} — Overview", dname, TEAMS[teamk]["name"], secs, ["domain"] + tags)
    # project docs
    for project, p in PROJECTS.items():
        leaves = [t[0] for t in TABLES if t[2] == project]
        secs = [
            ("Pipeline", f"Pipeline `{project}`: {p['desc']}"),
            ("Outputs", "Sinh ra các bảng: " + ", ".join(f"`{l}`" for l in leaves) + "."),
            ("Runbook", f"On-call: {TEAMS[p['team']]['slack']}. DAG chạy {'streaming' if p['flow']=='streaming' else 'batch daily T-1'}."),
        ]
        add(f"Pipeline {project} — Runbook", p["domain"], TEAMS[p["team"]]["name"], secs, ["runbook", "pipeline"])
    # team onboarding docs (referenced by teams.json key_docs)
    for k, t in TEAMS.items():
        projs = [pn for pn, pp in PROJECTS.items() if pp["team"] == k]
        team_leaves = [x[0] for x in TABLES if x[2] in projs]
        tier1 = [x[0] for x in TABLES if x[2] in projs and x[3] == "Tier1"]
        key_line = ("Tier1 cần nắm: " + ", ".join(f"`{l}`" for l in tier1) + ". ") if tier1 else ""
        secs = [("Welcome", f"Onboarding cho team {t['name']}. Bạn sở hữu: {', '.join(projs)}."),
                ("Key tables", key_line + "Các bảng team quản lý: " + ", ".join(f"`{l}`" for l in team_leaves) + ".")]
        add(f"{t['name']} — Onboarding", "Data Platform", t["name"], secs, ["onboarding"])
    return knowledge, index, md_files, trees

# ───────────────────── jira (epics + tickets) ─────────────────────
GITLAB_BASE = "https://gitlab.acme.example"
def mr_url(project, n): return f"{GITLAB_BASE}/dataeng/datainfra/{project}/-/merge_requests/{n}"

def build_jira():
    epics = {}
    pkey = "ADP"
    n = 100
    for pi, (project, p) in enumerate(PROJECTS.items()):
        leaves = [t[0] for t in TABLES if t[2] == project]
        ekey = f"{pkey}-{100 + pi}"
        tickets = []
        for ti, leaf in enumerate(leaves):
            tkey = f"{pkey}-{200 + pi*10 + ti}"
            tickets.append({
                "ticket_key": tkey, "issuetype": ("Story" if ti % 2 == 0 else "Task"),
                "summary": f"Build/maintain `{leaf}` in {project}",
                "description": (f"Implement transform for `{leaf}` (domain {LEAF2META[leaf][5]}). "
                                f"Owner team {TEAMS[p['team']]['name']}. "
                                f"Merge request: {mr_url(project, 40 + ti)} . "
                                f"Upstream: {', '.join(u for u in LEAF2META[leaf][6])}."),
                "status": ["Done", "In Progress", "In Review"][ti % 3],
                "assignee": {"name": TEAMS[p["team"]]["lead"]},
                "created_at": ts(BASE + timedelta(days=pi, hours=ti)),
                "labels": [LEAF2META[leaf][5], p["flow"]],
            })
        epics[ekey] = {
            "epic_key": ekey, "project": pkey,
            "summary": f"{project}: data platform epic",
            "description": (f"Epic tracking pipeline `{project}` — {p['desc']} "
                            f"Tables: {', '.join(leaves)}. Repo: {mr_url(project, 1)}"),
            "status": "In Progress",
            "created_at": ts(BASE + timedelta(days=pi)),
            "tickets": tickets,
        }
    # incident epic (drives RCA / open_incident narrative) — mentions loan_statement_fact
    epics[f"{pkey}-900"] = {
        "epic_key": f"{pkey}-900", "project": pkey,
        "summary": "INC: loan_statement_fact delayed after credit-curated-etl change",
        "description": (f"Incident: `loan_statement_fact` chậm cập nhật sau commit gần nhất của "
                        f"`credit-curated-etl`. Nghi ngờ đổi schema upstream `stg_loan_statement`. "
                        f"MR liên quan: {mr_url('credit-curated-etl', 51)}"),
        "status": "In Progress", "created_at": ts(NOWISH - timedelta(hours=10)),
        "tickets": [{
            "ticket_key": f"{pkey}-901", "issuetype": "Bug",
            "summary": "loan_statement_fact freshness SLA breach",
            "description": (f"`loan_statement_fact` trễ > 6h. Điều tra `credit-curated-etl`. "
                            f"Diff: {mr_url('credit-curated-etl', 51)}"),
            "status": "In Progress", "assignee": {"name": TEAMS["core"]["lead"]},
            "created_at": ts(NOWISH - timedelta(hours=9)), "labels": ["incident", "p0", "credit"],
        }],
    }
    other = {"epic_key": "OTHER", "project": "MIXED",
             "summary": "Tickets without an Epic", "status": "Open",
             "created_at": ts(BASE), "tickets": [{
                 "ticket_key": f"{pkey}-950", "issuetype": "Task",
                 "summary": "Ad-hoc: backfill currency_dim", "description": "Backfill `currency_dim`.",
                 "status": "Done", "assignee": {"name": TEAMS["core"]["lead"]},
                 "created_at": ts(BASE), "labels": ["adhoc"]}]}
    return epics, other

# ───────────────────── gitlab cache (files + commits + mrs + diffs) ─────────────────────
def build_gitlab():
    files, commits, mrs, diffs = {}, {}, {}, {}
    for pi, (project, p) in enumerate(PROJECTS.items()):
        modname = project.replace("-", "_")
        leaves = [t[0] for t in TABLES if t[2] == project]
        # representative source files
        dag = (f'"""Airflow DAG / Spark job for {project}."""\n'
               f'# Owner: {TEAMS[p["team"]]["name"]} ({TEAMS[p["team"]]["slack"]})\n'
               f'# Outputs: {", ".join(leaves)}\n'
               f'SCHEDULE = "{"@continuous" if p["flow"]=="streaming" else "30 2 * * *"}"\n'
               f'def build():\n    for t in {leaves!r}:\n        transform(t)\n')
        files[f"{project}/dags/{modname}.py"] = dag
        files[f"{project}/README.md"] = f"# {project}\n\n{p['desc']}\n\nOutputs: {', '.join(leaves)}\n"
        files[f"{project}/sql/transform.sql"] = (
            "-- transform for " + project + "\n" +
            "\n".join(f"INSERT INTO {LEAF2NAME[l]} SELECT * FROM staging_{l};" for l in leaves) + "\n")
        files[f"{project}/config/job.yaml"] = f"project: {project}\nschedule: {p['flow']}\nowner: {TEAMS[p['team']]['name']}\n"
        # commit history (newest first). credit-curated-etl gets a recent 'smoking gun'.
        clist = []
        is_credit = project == "credit-curated-etl"
        for ci in range(6):
            if is_credit and ci == 0:
                cd = NOWISH - timedelta(hours=12)
                msg = "feat(credit): add dpd_bucket column to loan_statement_fact + change join key"
            else:
                cd = NOWISH - timedelta(days=ci + 1, hours=pi)
                msg = [f"fix({p['domain']}): handle null in {leaves[ci % len(leaves)]}",
                       f"chore: bump etl-lib for {project}",
                       f"feat: add data-quality check for {leaves[(ci+1) % len(leaves)]}",
                       f"refactor: simplify {modname} transform",
                       f"docs: update runbook for {project}",
                       f"perf: partition prune {leaves[ci % len(leaves)]}"][ci % 6]
            sid = sha(f"{project}:{ci}")
            clist.append({"short_id": sid, "title": msg,
                          "author_name": TEAMS[p["team"]]["lead"], "committed_date": ts(cd)})
        commits[project] = clist
        # smoking-gun diff for the newest credit commit
        if is_credit:
            sg = clist[0]["short_id"]
            diffs[f"{project}/{sg}"] = [{
                "new_path": f"dags/{modname}.py", "old_path": f"dags/{modname}.py",
                "new_file": False, "deleted_file": False, "renamed_file": False,
                "diff": ("@@ -18,6 +18,8 @@ def build_statement_fact(df):\n"
                         "     df = df.withColumn('outstanding_amount', col('amt'))\n"
                         "+    df = df.withColumn('dpd_bucket', bucketize(col('dpd')))\n"
                         "+    # NOTE: join key changed account_id -> account_sk\n"
                         "     return df\n")}]
        # open MR
        mrs[project] = [{
            "iid": 51 if is_credit else 40 + pi, "title": f"WIP: improve {project}",
            "author": {"name": TEAMS[p["team"]]["lead"]}, "state": "opened",
            "created_at": ts(NOWISH - timedelta(days=2, hours=pi)),
            "source_branch": f"feat/{modname}-improve"}]
    return files, commits, mrs, diffs

# ───────────────────── observations.jsonl ─────────────────────
def build_observations():
    recs = []
    monitored = ["loan_core_statement", "loan_statement_fact", "identity_mart", "bank_code_mapping"]
    for d, leaf in enumerate(monitored):
        recs.append({"entity_id": urn(LEAF2NAME[leaf]), "kind": "freshness",
                     "value": {"last_modified_ms": int((NOWISH - timedelta(hours=d*6)).timestamp()*1000),
                               "row_count": 1000000 + d*250000},
                     "observed_at": ts(NOWISH - timedelta(hours=d*6))})
    recs.append({"entity_id": urn(LEAF2NAME["loan_statement_fact"]), "kind": "schema",
                 "value": {"columns": [col["name"] for col in schema_for("loan_statement_fact", False)]},
                 "observed_at": ts(NOWISH - timedelta(hours=11))})
    return recs

# ───────────────────── emit + verify ─────────────────────
def writej(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    # clear stale cache subdirs only (never touch scripts/)
    for sub in ["gitlab", "confluence", "confluence_tree", "jira"]:
        d = CACHE / sub
        if d.exists():
            shutil.rmtree(d)
    datasets, by_urn = build_datasets()
    pipelines = build_pipelines(by_urn)
    domains = build_domains()        # allocates domain/team doc page_ids
    teams = build_teams()
    knowledge, cindex, md_files, trees = build_confluence()
    cross = build_cross_team()
    epics, other = build_jira()
    gl_files, gl_commits, gl_mrs, gl_diffs = build_gitlab()
    obs = build_observations()

    # core JSON
    writej(DP / "datasets.json", datasets)
    writej(DP / "pipelines.json", pipelines)
    writej(DP / "domains.json", domains)
    writej(DP / "teams.json", teams)
    writej(DP / "confluence_knowledge.json", knowledge)
    writej(DP / "cross_team.json", cross)
    writej(DP / "confluence_index.json", cindex)
    # gitlab cache
    for rel, content in gl_files.items():
        p = CACHE / "gitlab" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    for project, clist in gl_commits.items():
        writej(CACHE / "gitlab" / project / "_commits.json", clist)
    for project, mlist in gl_mrs.items():
        writej(CACHE / "gitlab" / project / "_mrs.json", mlist)
    for key, dlist in gl_diffs.items():
        project, sid = key.split("/")
        writej(CACHE / "gitlab" / project / "_diffs" / f"{sid}.json", dlist)
    # confluence cache
    for fname, body in md_files.items():
        p = CACHE / "confluence" / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    for fname, tree in trees.items():
        writej(CACHE / "confluence_tree" / fname, tree)
    # jira cache
    for ekey, epic in epics.items():
        writej(CACHE / "jira" / f"{ekey}.json", epic)
    writej(CACHE / "jira" / "other_epic.json", other)
    # observations
    HIST.mkdir(parents=True, exist_ok=True)
    (HIST / "observations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in obs) + "\n", encoding="utf-8")

    verify(datasets, pipelines, epics, trees)
    print(f"OK generated: {len(datasets)} datasets, {len(pipelines)} pipelines, "
          f"{len(domains)} domains, {len(teams)} teams, {len(knowledge)} confluence, "
          f"{len(cross['consumer_datasets'])} consumers/{len(cross['edges'])} edges, "
          f"{len(epics)+1} jira files, {sum(len(v) for v in gl_commits.values())} commits.")

MONITORED = [
    "acme.analytics.warehouse.bank_code_mapping", "acme.analytics.warehouse.identity_mart",
    "acme.secure.lending_svc.installment.loan_core_account", "acme.secure.lending_svc.installment.loan_core_bill",
    "acme.secure.lending_svc.installment.loan_core_order", "acme.secure.lending_svc.installment.loan_core_statement",
    "acme.secure.lending_svc.installment.loan_core_user",
]
def verify(datasets, pipelines, epics, trees):
    names = {d["name"] for d in datasets}
    ids = {d["id"] for d in datasets}
    assert len(datasets) == len(TABLES), f"expected {len(TABLES)} datasets, got {len(datasets)}"
    assert len(ids) == len(TABLES), "duplicate dataset urns"
    for m in MONITORED:
        assert m in names, f"monitored URN missing: {m}"
    # lineage resolves
    for d in datasets:
        for u in d["lineage"]["upstream"] + d["lineage"]["downstream"]:
            if u.startswith("urn:li:dataset"):
                assert u in ids, f"dangling dataset urn {u} in {d['name']}"
    # pipelines produce real datasets
    for p in pipelines:
        for u in p["lineage"]["downstream"]:
            assert u in ids, f"pipeline {p['name']} outputs unknown {u}"
    # jira tickets mention a table leaf + an MR url
    leaves = [t[0] for t in TABLES]
    for ekey, epic in epics.items():
        txt = epic["description"] + " ".join(t["description"] for t in epic["tickets"])
        assert "/-/merge_requests/" in txt, f"epic {ekey} has no MR url"
        assert any(l in txt for l in leaves), f"epic {ekey} names no table"
    # confluence trees name table leaves
    for fn, tree in trees.items():
        body = " ".join(s["body"] for s in tree["content_structure"]["sections"])
        assert any(l in body for l in leaves), f"tree {fn} names no table"
    print(f"verify_self: OK ({len(datasets)} datasets, 7 monitored present, lineage resolves, jira+confluence wired)")

if __name__ == "__main__":
    main()
