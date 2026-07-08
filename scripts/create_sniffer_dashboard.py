#!/usr/bin/env python3
"""Create Sniffer token audit overview dashboard.

Thin declarative spec on top of rewatch.assistant.dashboard_builder — all
validation, creation, refresh, layout, and publishing happens in
build_dashboard_from_spec.
"""

from __future__ import annotations

from dashboard_script_utils import build_and_report

DS = 14


def q(name: str, description: str, sql: str, viz: list[dict]) -> dict:
    return {
        "name": name,
        "description": description,
        "data_source_id": DS,
        "query": sql.strip(),
        "visualizations": viz,
    }


def counter(name: str, column: str, label: str = "") -> dict:
    return {"type": "COUNTER", "name": name, "counter_column": column, "counter_label": label}


def chart(name: str, chart_type: str, mapping: dict) -> dict:
    return {"type": "CHART", "name": name, "chart_type": chart_type, "column_mapping": mapping}


QUERIES = [
    q(
        "Sniffer - Summary",
        "Overall scan totals and average scores.",
        """
SELECT
  COUNT(*)::int AS total_reports,
  COUNT(*) FILTER (WHERE verdict = 'honeypot')::int AS honeypots,
  COUNT(*) FILTER (WHERE verdict = 'promising')::int AS promising,
  COUNT(*) FILTER (WHERE verdict = 'neutral')::int AS neutral,
  ROUND(AVG(risk_score)::numeric, 1) AS avg_risk_score,
  ROUND(AVG(potential_score)::numeric, 1) AS avg_potential_score,
  ROUND(100.0 * SUM(CASE WHEN source_verified = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS verified_pct,
  (SELECT value::bigint FROM state WHERE key = 'last_processed_block') AS last_block
FROM reports
""",
        [
            counter("Total Reports", "total_reports"),
            counter("Honeypots", "honeypots"),
            counter("Promising", "promising"),
            counter("Neutral", "neutral"),
            counter("Avg Risk Score", "avg_risk_score"),
            counter("Avg Potential", "avg_potential_score"),
            counter("Verified %", "verified_pct"),
            counter("Last Block", "last_block"),
        ],
    ),
    q(
        "Sniffer - Reports per Day",
        "Daily token audit scan volume.",
        "SELECT created_at::date AS day, COUNT(*)::int AS reports\nFROM reports\nGROUP BY 1\nORDER BY 1",
        [chart("Reports per Day", "area", {"day": "x", "reports": "y"})],
    ),
    q(
        "Sniffer - Verdict Breakdown",
        "Share of audit verdicts across all scans.",
        "SELECT verdict, COUNT(*)::int AS count\nFROM reports\nGROUP BY 1\nORDER BY 2 DESC",
        [chart("Verdict Mix", "pie", {"verdict": "x", "count": "y"})],
    ),
    q(
        "Sniffer - Verdict per Day",
        "Daily verdict counts over time.",
        "SELECT created_at::date AS day, verdict, COUNT(*)::int AS count\nFROM reports\nGROUP BY 1, 2\nORDER BY 1",
        [chart("Verdicts per Day", "line", {"day": "x", "count": "y", "verdict": "series"})],
    ),
    q(
        "Sniffer - Honeypots per Day",
        "Daily honeypot detections.",
        "SELECT created_at::date AS day, COUNT(*)::int AS honeypots\nFROM reports\nWHERE verdict = 'honeypot'\nGROUP BY 1\nORDER BY 1",
        [chart("Honeypots per Day", "column", {"day": "x", "honeypots": "y"})],
    ),
    q(
        "Sniffer - Reports by DEX",
        "Scan volume by decentralized exchange.",
        "SELECT dex, COUNT(*)::int AS reports\nFROM reports\nGROUP BY 1\nORDER BY 2 DESC",
        [chart("Reports by DEX", "column", {"dex": "x", "reports": "y"})],
    ),
    q(
        "Sniffer - Risk Tier Breakdown",
        "Tokens grouped by risk score tier.",
        """
SELECT CASE
    WHEN risk_score < 40 THEN 'low'
    WHEN risk_score < 70 THEN 'medium'
    ELSE 'high'
  END AS risk_tier,
  COUNT(*)::int AS count
FROM reports
GROUP BY 1
ORDER BY 2 DESC
""",
        [chart("Risk Tiers", "pie", {"risk_tier": "x", "count": "y"})],
    ),
    q(
        "Sniffer - Avg Scores by Verdict",
        "Average potential and risk scores per verdict.",
        """
SELECT verdict,
  ROUND(AVG(potential_score)::numeric, 1) AS avg_potential,
  ROUND(AVG(risk_score)::numeric, 1) AS avg_risk
FROM reports
GROUP BY 1
ORDER BY 1
""",
        [chart("Scores by Verdict", "column", {"verdict": "x", "avg_potential": "y", "avg_risk": "y"})],
    ),
    q(
        "Sniffer - Avg Liquidity by Verdict",
        "Average pool liquidity by audit verdict.",
        """
SELECT verdict,
  ROUND(AVG(liquidity_usd)::numeric, 0) AS avg_liquidity_usd,
  COUNT(*)::int AS reports
FROM reports
WHERE liquidity_usd IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
""",
        [chart("Liquidity by Verdict", "column", {"verdict": "x", "avg_liquidity_usd": "y"})],
    ),
    q(
        "Sniffer - Potential Score Distribution",
        "Histogram of potential scores across all tokens.",
        """
SELECT ROUND(potential_score::numeric, 0) AS score, COUNT(*)::int AS count
FROM reports
WHERE potential_score IS NOT NULL
GROUP BY 1
ORDER BY 1
""",
        [chart("Potential Distribution", "column", {"score": "x", "count": "y"})],
    ),
    q(
        "Sniffer - Verified Rate by DEX",
        "Percentage of source-verified contracts per DEX.",
        """
SELECT dex,
  ROUND(100.0 * SUM(CASE WHEN source_verified = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS verified_pct,
  COUNT(*)::int AS total
FROM reports
GROUP BY 1
ORDER BY 3 DESC
""",
        [chart("Verified by DEX", "column", {"dex": "x", "verified_pct": "y"})],
    ),
    q(
        "Sniffer - Promising Tokens",
        "Tokens flagged as promising by the auditor.",
        """
SELECT name, symbol, dex, potential_score, risk_score,
  ROUND(liquidity_usd::numeric, 0) AS liquidity_usd,
  source_verified, created_at::timestamp AS scanned_at
FROM reports
WHERE verdict = 'promising'
ORDER BY potential_score DESC, created_at DESC
""",
        [{"type": "TABLE", "name": "Promising Tokens"}],
    ),
    q(
        "Sniffer - Recent Honeypots",
        "Most recently detected honeypot tokens.",
        """
SELECT name, symbol, dex, potential_score, risk_score,
  ROUND(liquidity_usd::numeric, 0) AS liquidity_usd,
  source_verified, created_at::timestamp AS scanned_at
FROM reports
WHERE verdict = 'honeypot'
ORDER BY created_at DESC
LIMIT 50
""",
        [{"type": "TABLE", "name": "Recent Honeypots"}],
    ),
    q(
        "Sniffer - Recent Reports",
        "Latest token audit results.",
        """
SELECT name, symbol, dex, verdict, potential_score, risk_score,
  ROUND(liquidity_usd::numeric, 0) AS liquidity_usd,
  source_verified, created_at::timestamp AS scanned_at
FROM reports
ORDER BY created_at DESC
LIMIT 100
""",
        [{"type": "TABLE", "name": "Recent Reports"}],
    ),
    q(
        "Sniffer - Highest Risk Tokens",
        "Tokens with the highest risk scores.",
        """
SELECT name, symbol, dex, verdict, potential_score, risk_score,
  ROUND(liquidity_usd::numeric, 0) AS liquidity_usd,
  created_at::date AS scanned
FROM reports
ORDER BY risk_score DESC, created_at DESC
LIMIT 50
""",
        [{"type": "TABLE", "name": "Highest Risk"}],
    ),
    q(
        "Sniffer - Neutral Tokens",
        "Tokens with neutral audit verdicts.",
        """
SELECT name, symbol, dex, potential_score, risk_score,
  ROUND(liquidity_usd::numeric, 0) AS liquidity_usd,
  created_at::date AS scanned
FROM reports
WHERE verdict = 'neutral'
ORDER BY potential_score DESC
""",
        [{"type": "TABLE", "name": "Neutral Tokens"}],
    ),
]


def pos(col: int, row: int, size_x: int, size_y: int) -> dict:
    return {"col": col, "row": row, "sizeX": size_x, "sizeY": size_y}


WIDGETS = [
    {
        "text": "# Sniffer Overview\n\nAutomated Ethereum token audit scanner — LLM-powered risk analysis of new Uniswap pools.",
        "position": pos(0, 0, 12, 3),
    },
    {"text": "## Scan Overview", "position": pos(0, 3, 12, 2)},
    {"visualization": "Total Reports", "position": pos(0, 5, 3, 8)},
    {"visualization": "Honeypots", "position": pos(3, 5, 3, 8)},
    {"visualization": "Promising", "position": pos(6, 5, 3, 8)},
    {"visualization": "Neutral", "position": pos(9, 5, 3, 8)},
    {"visualization": "Avg Risk Score", "position": pos(0, 13, 3, 8)},
    {"visualization": "Avg Potential", "position": pos(3, 13, 3, 8)},
    {"visualization": "Verified %", "position": pos(6, 13, 3, 8)},
    {"visualization": "Last Block", "position": pos(9, 13, 3, 8)},
    {"text": "## Scan Activity", "position": pos(0, 21, 12, 2)},
    {"visualization": "Reports per Day", "position": pos(0, 23, 8, 8)},
    {"visualization": "Verdict Mix", "position": pos(8, 23, 4, 8)},
    {"visualization": "Verdicts per Day", "position": pos(0, 31, 12, 8)},
    {"visualization": "Honeypots per Day", "position": pos(0, 39, 6, 8)},
    {"visualization": "Risk Tiers", "position": pos(6, 39, 6, 8)},
    {"text": "## DEX & Risk Analysis", "position": pos(0, 47, 12, 2)},
    {"visualization": "Reports by DEX", "position": pos(0, 49, 6, 8)},
    {"visualization": "Liquidity by Verdict", "position": pos(6, 49, 6, 8)},
    {"visualization": "Scores by Verdict", "position": pos(0, 57, 6, 8)},
    {"visualization": "Potential Distribution", "position": pos(6, 57, 6, 8)},
    {"visualization": "Verified by DEX", "position": pos(0, 65, 12, 6)},
    {"text": "## Token Reports", "position": pos(0, 71, 12, 2)},
    {"visualization": "Promising Tokens", "position": pos(0, 73, 6, 8)},
    {"visualization": "Recent Honeypots", "position": pos(6, 73, 6, 8)},
    {"visualization": "Recent Reports", "position": pos(0, 81, 12, 8)},
    {"visualization": "Highest Risk", "position": pos(0, 89, 6, 8)},
    {"visualization": "Neutral Tokens", "position": pos(6, 89, 6, 8)},
]


if __name__ == "__main__":
    build_and_report(name="Sniffer Overview", queries=QUERIES, widgets=WIDGETS)
