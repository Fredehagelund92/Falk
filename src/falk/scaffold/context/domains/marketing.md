# Marketing Context

> Domain-specific knowledge for marketing questions and analysis.
> The agent reads this file when answering marketing-related queries.

## Key Metrics

### Customer Acquisition Cost (CAC)

**Definition:**
Total marketing spend divided by new customers acquired in that period.

**SQL Formula:**
```sql
SELECT 
  DATE_TRUNC('month', acquisition_date) AS month,
  SUM(marketing_spend) / COUNT(DISTINCT customer_id) AS cac
FROM customers c
LEFT JOIN marketing_spend ms ON DATE_TRUNC('month', c.acquisition_date) = ms.month
WHERE c.acquisition_date >= '2024-01-01'
GROUP BY 1
ORDER BY 1 DESC;
```

**Important notes:**
- Include all marketing spend: ads, content, events, salaries
- Attribution window: 30 days from first touch to acquisition
- Exclude: Sales team costs (goes in Sales CAC)

**Benchmarks:**
- Our target CAC: $[target]
- Industry average: $[benchmark]
- Acceptable range: $[low] - $[high]

### Conversion Rate

**Definition:**
Percentage of visitors/leads that convert to customers.

**Conversion stages:**
1. Visitor → Lead (form fill, signup)
2. Lead → Trial (trial activation)
3. Trial → Customer (paid conversion)

**SQL Formula:**
```sql
SELECT 
  COUNT(DISTINCT CASE WHEN status = 'customer' THEN user_id END) * 100.0 /
  COUNT(DISTINCT user_id) AS conversion_rate
FROM users
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';
```

**Benchmarks:**
- Visitor → Lead: [X%]
- Lead → Trial: [Y%]
- Trial → Customer: [Z%]
- Overall: [XYZ%]

### Marketing Qualified Lead (MQL)

**Definition:**
A lead that meets specific criteria indicating sales-readiness.

**Qualification criteria:**
- [ ] Company size: [criteria]
- [ ] Job title: [criteria]
- [ ] Engagement score: [threshold]
- [ ] Geographic location: [criteria]
- [ ] Industry: [relevant industries]

**SQL to identify MQLs:**
```sql
SELECT 
  lead_id,
  email,
  company_size,
  engagement_score
FROM leads
WHERE company_size >= 50
  AND engagement_score >= 75
  AND industry IN ('Technology', 'Financial Services')
  AND status = 'active';
```

## Campaign Analysis

### Campaign Performance Metrics

**For every campaign, track:**
- Impressions
- Clicks (CTR = clicks / impressions)
- Leads generated
- Cost per lead (CPL = spend / leads)
- Conversions
- Cost per acquisition (CPA = spend / conversions)
- ROI (revenue / spend)

### Campaign Types

**1. Acquisition Campaigns**
- Goal: Attract new leads/prospects
- Channels: Paid search, display ads, content marketing
- Success metric: CAC, lead volume

**2. Retention Campaigns**
- Goal: Keep existing customers engaged
- Channels: Email, in-app messaging, webinars
- Success metric: Churn rate, engagement

**3. Expansion Campaigns**
- Goal: Upsell/cross-sell to existing customers
- Channels: Email, sales outreach, in-app offers
- Success metric: Expansion revenue, upgrade rate

## Attribution

**Attribution model:**
- Default: [Last-touch, first-touch, multi-touch?]
- Window: [7 days, 30 days, 90 days?]

**Attribution logic:**
```sql
-- Example: Last-touch attribution
SELECT 
  c.customer_id,
  ca.channel AS attributed_channel,
  ca.campaign AS attributed_campaign
FROM customers c
LEFT JOIN campaign_touchpoints ca ON c.customer_id = ca.user_id
WHERE ca.touched_at = (
  SELECT MAX(touched_at) 
  FROM campaign_touchpoints 
  WHERE user_id = c.customer_id 
    AND touched_at <= c.acquisition_date
);
```

## Channel Performance

**Primary channels:**
1. **Organic Search**
   - Traffic source: Google, Bing
   - Typical CAC: $[X]
   - Conversion rate: [Y%]

2. **Paid Search**
   - Platforms: Google Ads, Bing Ads
   - Typical CAC: $[X]
   - Conversion rate: [Y%]

3. **Social Media**
   - Platforms: LinkedIn, Twitter, Facebook
   - Typical CAC: $[X]
   - Conversion rate: [Y%]

4. **Email Marketing**
   - Types: Newsletter, drip campaigns, promotional
   - Typical open rate: [X%]
   - Typical CTR: [Y%]

## Data Quality Notes

**Known issues:**
- UTM parameters: Sometimes missing for [channel X]
- Attribution window: Changed from 30→90 days on [date]
- Spend data: Manual uploads for offline events (may lag by 1 week)

**Data refresh schedule:**
- Ad platform data: Synced daily at 6 AM UTC
- Website analytics: Real-time
- Campaign spend: Updated weekly

---

## Example Marketing Questions

- "What's our CAC by channel this quarter?"
- "Which campaigns drove the most conversions last month?"
- "Show me conversion funnel by source"
- "Compare paid vs organic performance"
- "What's our best-performing ad set?"

