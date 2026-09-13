# Investor Daily Routine Automation Tool

## Product Scope and PoC Specification

**Status:** Initial scope agreed for a presentable Proof of Concept (PoC)  
**Initial market:** United States  
**Investment approach:** Long-term fundamental selection combined with short- to medium-term entry timing

---

## 1. Product Vision

The product will support investors in their daily stock-market routine by helping them:

1. discover potentially attractive companies;
2. analyze a selected company;
3. compare it with relevant peers and its broader industry;
4. estimate fair value and expected return;
5. assess whether the current moment represents an attractive entry point;
6. monitor changes in valuation, forecasts, momentum, and catalysts;
7. receive an explainable investment recommendation.

The core principle is:

> **Fundamentals determine what may be worth buying; market and peer signals help determine when to enter.**

The eventual product workflow is:

> **Discover → Analyze → Compare → Monitor → Entry Signal → Recommendation**

For the PoC, the priority is a complete, demonstrable analysis and recommendation workflow. Full daily automation and alerts will follow after the core engine has been validated.

---

## 2. Target Investment Horizon

The tool will use a **hybrid investment horizon**:

- **Long-term perspective:** Estimate fundamental value using financial statements and forecasts.
- **Short- to medium-term perspective:** Optimize the entry point over weeks or months using momentum, peer behavior, and catalysts.

This is not intended to be a pure day-trading system or a standalone long-term valuation calculator.

---

## 3. PoC User Journey

The PoC should support the following end-to-end flow:

1. The user selects a US-listed company.
2. The system automatically proposes 5–10 comparable companies.
3. The system explains why each peer was selected.
4. The user can add, remove, or confirm proposed peers.
5. The system collects current financial statements, historical financials, market data, and available forecasts.
6. The valuation engine calculates intrinsic, relative, and historical valuation estimates.
7. The system compares the selected company with its peer group and broader industry.
8. The momentum engine evaluates whether the company, its peers, or its industry have entered upward or downward trends.
9. The scoring engine combines valuation, forecasts, momentum, peer signals, and catalysts.
10. The system returns a fair-value estimate, expected return, entry zone, peer ranking, composite score, and explainable recommendation.

---

## 4. Investment Universe

The long-term design will allow the user to define the investment universe through a combination of:

- selected markets;
- sectors and industries;
- investment themes;
- indices or exchanges;
- individual companies.

### PoC boundary

The first version will cover **US-listed companies only**.

The user may begin with:

- a specific company;
- a sector or industry;
- an investment theme, such as nuclear energy;
- a predefined list of companies.

International markets are outside the PoC scope.

---

## 5. Peer and Industry Comparison

The system will not value a company in isolation. Its analytical hierarchy will be:

> **Selected company → closest peer group → broader industry → market context**

### Hybrid peer selection

The peer-selection process will be hybrid:

- The algorithm proposes 5–10 comparable companies.
- It explains the basis for each selection.
- The user can add or remove companies before running the final comparison.

Peer similarity may consider:

- products and services;
- business model;
- revenue drivers;
- end markets and thematic exposure;
- geography;
- company size;
- growth stage and business maturity;
- profitability profile;
- capital intensity;
- regulatory exposure.

### Multiple comparison layers

The tool should distinguish between:

1. **Direct peers** — the closest operating and financial comparables.
2. **Thematic peers** — companies exposed to the same investment theme but not necessarily at the same maturity level.
3. **Broader industry** — a lower-granularity benchmark, such as electricity producers or energy infrastructure.

For example, GE Vernova, Oklo, and BWX Technologies may share nuclear-energy exposure, but they differ materially in their business models, maturity, revenue profiles, and risk. The system must display these differences rather than treating them as perfectly interchangeable.

---

## 6. Forecast Architecture

The tool will maintain three forecast scenarios separately:

1. **Management guidance** — forecasts and targets declared by the company.
2. **Analyst consensus** — expected revenue, EBITDA, EPS, free cash flow, and related measures.
3. **Internal model forecast** — projections produced from historical financials and other selected inputs.

The system should not immediately average these forecasts. It should first show their differences and use **forecast divergence** as an investment signal.

Example:

| Forecast source | Expected revenue growth |
| --- | ---: |
| Management guidance | 8% |
| Analyst consensus | 12% |
| Internal model | 18% |

A large difference may reveal conservative guidance, excessive analyst optimism, model uncertainty, or a potential market mispricing. The recommendation must explain which interpretation is most plausible and how much confidence should be assigned to it.

---

## 7. Valuation Engine

The PoC will use three complementary valuation perspectives.

### 7.1 Intrinsic valuation

A focused **Discounted Cash Flow (DCF)** model will estimate intrinsic value using assumptions such as:

- revenue growth;
- operating margins;
- taxes;
- reinvestment and capital expenditure;
- working capital;
- free cash flow;
- discount rate;
- terminal growth.

The model should expose its assumptions and support at least a basic sensitivity analysis.

### 7.2 Peer-relative valuation

The system will compare the selected company with its confirmed peer group using a focused set of relevant multiples, potentially including:

- EV/EBITDA;
- P/E;
- EV/Sales;
- free-cash-flow yield.

The exact multiples should depend on the company's maturity and business model. For example, EV/Sales may be more useful than P/E for an early-stage company without positive earnings.

### 7.3 Historical valuation

Historical valuation is included in the PoC with a deliberately limited scope:

- approximately **3–5 years** of history;
- approximately **three core valuation multiples**;
- current value versus historical median;
- current historical percentile;
- optional comparison with historical valuation bands.

Example output:

| Measure | Result |
| --- | ---: |
| Current EV/EBITDA | 14.2× |
| Five-year median | 17.1× |
| Current historical percentile | 23rd |
| Current peer median | 18.4× |

This creates three independent valuation lenses:

> **Intrinsic value (DCF) + Relative value (peers) + Historical value (company versus itself)**

Historical valuation is expected to add approximately **20–30%** to the implementation effort of the valuation module if kept within this limited scope.

---

## 8. Momentum and Peer-Leadership Analysis

The momentum component should answer two different questions:

1. Has the selected company's own price trend improved or deteriorated?
2. Have comparable companies or the broader industry already begun moving in a direction that the selected company may follow?

The tool should identify potential patterns such as:

> Peers have started repricing upward, while the selected company has not. Its fundamentals and valuation indicate possible catch-up potential.

The PoC should treat this as a **probabilistic signal**, not proof that the selected company will follow its peers.

Candidate momentum inputs include:

- returns over several time windows;
- moving-average relationships;
- relative strength versus peers, industry, and market;
- volume confirmation;
- volatility;
- breadth of positive or negative movement across the peer group;
- lead-lag relationships between companies.

The exact initial indicators and windows remain to be finalized.

---

## 9. Composite Entry Score

The entry recommendation will be based on a configurable composite score rather than one standalone signal.

Candidate components are:

- valuation gap;
- management-versus-analyst-versus-model forecast divergence;
- selected-company momentum;
- peer and industry momentum;
- peer-leader or laggard signal;
- catalysts and events;
- financial quality;
- risk.

### User-controlled configuration

Users will be able to define:

- the weight of each component;
- the hierarchy or importance of components;
- hard decision rules that can override the weighted score.

Example balanced configuration:

| Component | Illustrative weight |
| --- | ---: |
| Valuation | 35% |
| Forecast divergence | 25% |
| Peer momentum | 20% |
| Company momentum | 15% |
| Catalysts | 5% |

These weights are an initial example, not a finalized PoC calibration.

### Recommended defaults

When the user is uncertain, the product should recommend suitable weights and explain its reasoning. Future presets may include:

- Balanced;
- Value;
- Growth;
- Momentum;
- Quality.

### Hard decision rules

Weights and hard rules must remain separate. A user might define a rule such as:

> Never issue an ENTRY recommendation when the market price is more than 20% above estimated fair value, regardless of momentum.

This prevents a high score in one area from hiding a critical constraint in another.

---

## 10. Required Output

For each analyzed company, the PoC should provide:

- **Fair value** — a point estimate or range.
- **Valuation gap** — difference between fair value and current price.
- **Expected return** — for a defined time horizon.
- **Entry zone** — attractive and very attractive price levels.
- **Recommendation** — using a clear rating scale.
- **Composite score** — with component-level contributions.
- **Peer ranking** — the selected company relative to confirmed peers.
- **Forecast comparison** — management, consensus, and model estimates.
- **Momentum assessment** — company, peers, and broader industry.
- **Key catalysts and risks**.
- **Confidence or uncertainty indicator**.
- **Plain-language explanation** of why the recommendation was produced.

The result should never be a black box. A user must be able to inspect the inputs, assumptions, weights, rules, and main drivers of the recommendation.

---

## 11. Recommended PoC Interface

A presentable first dashboard could contain:

1. **Company selector**
2. **Automatically proposed peer group** with add/remove controls and similarity explanations
3. **Headline recommendation card**
4. **Fair-value and entry-zone summary**
5. **DCF assumptions and sensitivity view**
6. **Peer valuation table and ranking**
7. **Historical valuation view**
8. **Management vs analysts vs model forecast comparison**
9. **Company and peer momentum view**
10. **Composite-score breakdown and editable weights**
11. **Catalysts, risks, and recommendation explanation**

The demonstration should follow one coherent case study from company selection to final recommendation.

---

## 12. PoC Scope: Included

The first presentable product will include:

- US-listed companies;
- analysis initiated by a selected company;
- automatically proposed and user-editable peer groups;
- direct-peer and broader-industry comparisons;
- management, analyst, and model forecasts shown separately;
- DCF valuation;
- peer-multiple valuation;
- limited 3–5 year historical valuation;
- company and peer momentum analysis;
- configurable composite scoring;
- recommended default weights when the user is uncertain;
- hard decision rules;
- fair value, expected return, entry zone, ranking, and recommendation;
- an explainable dashboard suitable for a PoC presentation.

---

## 13. Outside the Initial PoC

The following capabilities are part of the broader vision but should be postponed until the analytical core is working:

- full global-market coverage;
- automated daily watchlist recalculation;
- email, mobile, or in-app alerts;
- portfolio management and optimization;
- broker integration and trade execution;
- highly sophisticated machine-learning forecasting;
- natural-language news and filings analysis at production scale;
- personalized models trained on each user's behavior;
- tax optimization;
- social or collaborative investing features.

Deferring these features keeps the PoC focused on proving the quality, explainability, and usefulness of the recommendation engine.

---

## 14. Validation and Backtesting

Backtesting is essential before the recommendation engine can be treated as reliable. In particular, it should test whether claims such as **“peer leaders move first and a laggard follows”** contain predictive information.

Recommended validation questions include:

- Did high composite scores lead to positive forward returns?
- Did recommendations outperform a relevant benchmark after risk adjustment?
- Did peer-leadership signals improve timing beyond company momentum alone?
- Did DCF, peer-relative, or historical valuation contribute most to performance?
- Were results stable across sectors and market regimes?
- How sensitive were results to weights, thresholds, and lookback windows?
- Would conclusions remain valid after avoiding look-ahead and survivorship bias?

Backtesting may be implemented after the first interactive PoC, but its data requirements should influence the architecture from the beginning.

---

## 15. Remaining Decisions

The following questions should be resolved during implementation planning:

1. Which US exchanges, indices, and sectors should be supported in the demo?
2. Which company should be used as the main PoC case study?
3. Which data providers can supply financial statements, management guidance, analyst estimates, prices, corporate actions, and classifications?
4. Are paid data APIs acceptable, or must the first version use only free/public sources?
5. Which financial metrics should dominate the internal forecast model?
6. What should the initial forecast horizons be: 1 year, 3 years, 5 years, or several simultaneously?
7. Which three historical multiples should be used by default, and how should they vary by business maturity?
8. Which momentum indicators, windows, and peer lead-lag tests should be included?
9. What recommendation scale should be used—for example, Strong Buy, Buy, Watch, Hold, Reduce, and Avoid?
10. How should company, sector, and market risk adjust fair value and the composite score?
11. Which default weight preset should power the first demo?
12. What confidence methodology should be used when forecasts or peer comparability are weak?
13. What minimum backtest should be completed before presenting predictive claims?

---

## 16. Recommended Next Step

Freeze a single PoC demonstration scenario and translate this product scope into a technical specification.

A strong candidate is:

> **Analyze GE Vernova in a user-confirmed nuclear/energy-technology peer context, compare management, analyst, and internal forecasts, calculate DCF plus peer and historical valuation, evaluate company and peer momentum, and produce an explainable entry recommendation.**

The next specification should define:

- exact data sources;
- required database tables;
- calculation formulas;
- API endpoints;
- scoring configuration;
- dashboard screens;
- implementation milestones;
- acceptance criteria for the PoC demonstration.

---

## 17. Product Disclaimer

The product should be presented as a **decision-support and research tool**, not as personalized financial advice or a guarantee of future performance. Forecasts, valuation outputs, peer relationships, and momentum signals are uncertain. Recommendations should always show their assumptions, data freshness, risks, and confidence level.
