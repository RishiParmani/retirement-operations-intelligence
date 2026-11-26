# Business Insights

Format: **Observation -> Evidence -> Business impact -> Recommended action**. Every number is computed by `scripts/run_eda.py` (see `reports/insights/headline.json` and the CSVs beside it); figures are in `reports/figures/`.

> **Read this first.** The data is synthetic. `src/roip/data_generation.py` builds in specific relationships (missing information raises exception probability, exceptions raise processing time, workload and priority scale duration, `Pending` is assigned at random). The analysis below correctly *recovers* those relationships, which shows the method works and gives a realistic reporting story. It does **not** show that real retirement operations behave this way. Findings are associations; none is proven causal.

## 1. Missing intake information is the strongest single warning sign
- **Observation:** Operations received with missing information breach SLA far more often.
- **Evidence:** 66.2% breach rate vs 24.5% when information is complete (10,270 completed operations with missing info). Missing information also lifts the exception rate to 50.1% vs 8.0%. Effect size (Cramér's V) 0.21, "strong".
- **Business impact:** Priority-adjusted, about 4,287 breaches (8.5% of all breaches) are in excess of what the same priorities would produce with complete information.
- **Action:** Validate completeness at intake (mandatory-field checks, document checklist) and route incomplete items to a "chase information" queue *before* they consume processing time.

## 2. Exceptions roughly triple breach risk and double processing time
- **Observation:** Operations with an exception breach SLA 61.4% of the time vs 22.8% without; mean processing time 66.5 h vs 34.0 h.
- **Evidence:** Cramér's V 0.26 (strongest of all dimensions). Exceptions also drive rework: 33.9% of exception cases are reworked vs 3.5% otherwise (rework itself: V 0.20, moderate).
- **Business impact:** Priority-adjusted, about 7,464 breaches (14.7% of all) are in excess of the no-exception rate. Overlap with missing information means shares are **not additive**.
- **Action:** Treat exception handling as the main improvement lever: dedicated exception owners, a time-box before escalation, and first-time-right checks to cut rework.

## 3. Lower priority work breaches most - priority tiers may not be protecting the right work
- **Observation:** Breach rate runs Critical 10.5%, High 18.3%, Medium 29.6%, Low 37.9%; Medium alone is 53.3% of all breaches (Low + Medium: 78.9%).
- **Evidence:** Average hours Critical 25.6 h, High 31.7 h, Medium 39.3 h, Low 45.0 h.
- **Business impact:** Priority is doing its job at the top, but the bulk of breaches sit in the large Medium tier, which is 48% of intake.
- **Action:** Add an ageing rule that lifts Medium/Low items nearing their SLA, and review whether the Medium SLA targets are realistic.

## 4. High workload is associated with more breaches
- **Evidence:** Breach rate by team workload band: 35-54: 19.1%, 55-74: 23.9%, 75-94: 27.8%, 95+: 32.9%. The 95+ band holds 33.4% of completed work but 41.0% of breaches. Effect size 0.12 (moderate).
- **Business impact:** Overloaded periods convert directly into breaches.
- **Action:** Set a workload cap (for example rebalance when a team passes 95) and monitor the band share weekly.

## 5. Team, region, channel, operation type, weekday: no practical effect
- **Evidence:** Cramér's V below 0.025 for every one of these (teams' SLA compliance differs by well under a point). `reports/figures/04_effect_sizes.png`.
- **Business impact:** Targeting a "worst team" or "worst region" would be chasing noise here.
- **Action:** Focus on process drivers (1-4), not on who or where. This is also why the dashboard ranks by rate with sample sizes visible.

## 6. Open backlog is dominated by old Pending items
- **Evidence:** Open backlog 7,274 (Pending 7,008 + Escalated 266). Of Pending, 5,238 (74.7%) are older than 90 days as of the latest received date (31 Dec 2025).
- **Caveat:** In this dataset `Pending` is assigned at random across the year, so the ageing is a property of the generator. In a real operation the same chart would be an operational alarm.
- **Action:** Weekly review of items older than 90 days with a named owner; decide close, escalate or chase.

## 7. Highest-risk segment
- Low priority + information missing + exception raised: 83.1% breach rate on 895 completed operations (avg 100.2 h). Small (1.5% of breaches), so useful for triage rules, not for volume reduction. Table: `reports/insights/segments.csv`.

## 8. Long tail in processing time
- Median 26.8 h, P90 77.4 h, P99 172.8 h, max 767.0 h. The mean (37.3 h) sits well above the median, so report both. 3,486 rows are flagged F07 (extreme processing time) and kept, not removed.

## 9. January 2026 is not a data error
- No operations were received after 31 Dec 2025, but 796 operations that arrived in December completed in January. Counting completions by completion month therefore shows a small January bar next to zero receipts. The dashboard keeps it, annotates it, and the underlying data is unchanged.
