# Finance Context

> Domain-specific knowledge for finance and revenue questions.
> The agent reads this file when answering financial queries.

## Key Metrics

### Revenue

**Definition:**
Total money received from customers for products/services.

**Revenue recognition:**
- Model: [Accrual-based, cash-based?]
- Timing: [When is revenue recognized?]
- Deferred revenue: [How handled?]

**SQL Formula:**
```sql
SELECT 
  DATE_TRUNC('month', invoice_date) AS month,
  SUM(amount) AS total_revenue
FROM invoices
WHERE status = 'paid'
  AND invoice_date >= '2024-01-01'
GROUP BY 1
ORDER BY 1 DESC;
```

**Important notes:**
- Exclude: Refunds (tracked separately)
- Include: All successfully paid invoices
- Currency: [USD, EUR, multi-currency?]
- Exchange rates: [Conversion logic]

**Reporting:**
- Fiscal year: [January-December or other?]
- Reporting currency: [USD, local currencies?]

### MRR (Monthly Recurring Revenue)

**Definition:**
Normalized monthly value of all active subscriptions.

**Calculation:**
- Annual plans: Total / 12
- Monthly plans: Total
- One-time: Excluded from MRR

**SQL Formula:**
```sql
SELECT 
  DATE_TRUNC('month', month) AS month,
  SUM(CASE 
    WHEN billing_period = 'annual' THEN amount / 12
    WHEN billing_period = 'monthly' THEN amount
    ELSE 0
  END) AS mrr
FROM subscriptions
WHERE status = 'active'
GROUP BY 1
ORDER BY 1 DESC;
```

**MRR Movement:**
- **New MRR**: From new customers
- **Expansion MRR**: Upgrades from existing customers
- **Contraction MRR**: Downgrades from existing customers
- **Churned MRR**: Lost from cancelled subscriptions

**Net MRR Change:**
```
Net Change = New + Expansion - Contraction - Churned
```

### ARR (Annual Recurring Revenue)

**Definition:**
MRR × 12

**Use cases:**
- B2B SaaS reporting
- Investor updates
- Strategic planning

### Gross Margin

**Definition:**
(Revenue - Cost of Goods Sold) / Revenue × 100%

**COGS includes:**
- [ ] Hosting/infrastructure costs
- [ ] Support team costs
- [ ] Payment processing fees
- [ ] [Other direct costs]

**Target margin:**
- Our target: [X%]
- Industry benchmark: [Y%]

### Churn Rate

**Definition:**
Percentage of customers or revenue lost in a period.

**Customer churn:**
```sql
SELECT 
  DATE_TRUNC('month', churn_date) AS month,
  COUNT(*) * 100.0 / (
    SELECT COUNT(*) 
    FROM customers 
    WHERE status = 'active' 
    AT TIME ZONE month
  ) AS customer_churn_rate
FROM customers
WHERE status = 'churned'
GROUP BY 1
ORDER BY 1 DESC;
```

**Revenue churn (MRR churn):**
```sql
SELECT 
  month,
  churned_mrr * 100.0 / starting_mrr AS mrr_churn_rate
FROM monthly_mrr_summary;
```

**Acceptable levels:**
- Customer churn: [X%] per month
- Revenue churn: [Y%] per month
- Industry average: [Z%]

## Financial Reporting Periods

**Fiscal year:**
- Start: [Month, e.g., January or July]
- Quarters: [Q1: Jan-Mar, Q2: Apr-Jun, etc.]

**Reporting schedules:**
- Monthly close: [Day X of following month]
- Quarterly close: [X days after quarter end]
- Annual close: [X days after year end]

**Data availability:**
- Revenue data: Available within [X] days of month end
- COGS allocation: Updated [frequency]
- Accruals: Recorded by [day X]

## Revenue Categories

### By Product/Service

**Product line breakdown:**
1. [Product A]: [% of revenue]
   - Pricing: $[X]/month
   - Target segment: [customers]

2. [Product B]: [% of revenue]
   - Pricing: $[Y]/month
   - Target segment: [customers]

### By Customer Segment

**Segment breakdown:**
- Enterprise (>500 employees): [% of revenue]
- Mid-market (50-500 employees): [% of revenue]
- SMB (<50 employees): [% of revenue]

### By Geography

**Regional revenue:**
- North America: [%]
- Europe: [%]
- Asia-Pacific: [%]
- Other: [%]

## Pricing & Packaging

**Current plans:**
| Plan | Price | Features | Target Customer |
|------|-------|----------|-----------------|
| Starter | $[X]/mo | [features] | Small teams |
| Pro | $[Y]/mo | [features] | Growing companies |
| Enterprise | Custom | [features] | Large orgs |

**Discounting policy:**
- Annual prepay: [X%] discount
- Volume: [Y%] for >50 seats
- Non-profit: [Z%] discount
- Maximum discount: [threshold]

## Payment Terms

**Standard terms:**
- Small customers (<$1k/mo): Credit card, pay upfront
- Medium customers ($1k-$10k/mo): Net 30
- Enterprise (>$10k/mo): Net 30 or Net 60

**Collections:**
- Dunning process: [describe]
- Write-off policy: [after X days]

## Data Quality Notes

**Known issues:**
- Multi-currency: [How handled?]
- Refunds: [Timing of recognition?]
- Failed payments: [Retry logic?]
- Manual invoices: [Process?]

**Data sources:**
- Billing system: [Stripe, Chargebee, etc.]
- Accounting system: [QuickBooks, NetSuite, etc.]
- Sync frequency: [Real-time, daily, weekly?]

---

## Example Finance Questions

- "What's our MRR growth this quarter?"
- "Show me revenue by product line"
- "What's our churn rate trending?"
- "Compare ARR by customer segment"
- "What's our gross margin by region?"
- "How much expansion revenue did we generate?"

