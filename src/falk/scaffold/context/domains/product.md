# Product Context

> Domain-specific knowledge for product usage and adoption questions.
> The agent reads this file when answering product-related queries.

## Key Metrics

### Active Users

**Definitions:**
- **DAU (Daily Active Users)**: Users with activity in last 24 hours
- **WAU (Weekly Active Users)**: Users with activity in last 7 days
- **MAU (Monthly Active Users)**: Users with activity in last 30 days

**Activity definition:**
- What counts as "active"? [Login, specific action, API call, etc.]
- Example: "At least one query executed" or "Logged in and viewed dashboard"

**SQL Formula:**
```sql
SELECT 
  DATE(event_date) AS date,
  COUNT(DISTINCT user_id) AS dau
FROM events
WHERE event_name IN ('query_executed', 'dashboard_viewed', 'report_generated')
  AND event_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 1
ORDER BY 1 DESC;
```

**Stickiness:**
```
Stickiness = DAU / MAU × 100%
```
- Target: [X%]
- Benchmark: [Y%]

### Feature Adoption

**Key features to track:**
1. **[Feature A]**
   - What: [Description]
   - Why important: [Business value]
   - Adoption target: [X% of users]
   - Current adoption: [Y%]

2. **[Feature B]**
   - What: [Description]
   - Why important: [Business value]
   - Adoption target: [X% of users]
   - Current adoption: [Y%]

**Feature adoption query:**
```sql
SELECT 
  feature_name,
  COUNT(DISTINCT user_id) * 100.0 / (
    SELECT COUNT(DISTINCT user_id) FROM users WHERE status = 'active'
  ) AS adoption_rate
FROM feature_usage
WHERE used_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY feature_name
ORDER BY adoption_rate DESC;
```

### User Engagement

**Engagement score:**
Based on:
- Login frequency: [weight]
- Feature usage depth: [weight]
- Time spent: [weight]
- Social sharing: [weight]

**Engagement tiers:**
- **Power users**: Score ≥ 80
- **Regular users**: Score 40-79
- **Casual users**: Score 10-39
- **At-risk users**: Score < 10

**SQL to calculate:**
```sql
WITH user_activity AS (
  SELECT 
    user_id,
    COUNT(DISTINCT DATE(event_date)) AS days_active,
    COUNT(DISTINCT feature_used) AS features_used,
    SUM(session_duration_mins) AS total_time
  FROM events
  WHERE event_date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY user_id
)
SELECT 
  user_id,
  (days_active * 2) + (features_used * 5) + (total_time * 0.1) AS engagement_score
FROM user_activity;
```

### Retention

**Cohort retention:**
% of users from a given signup cohort still active after N days/weeks/months.

**Retention periods:**
- D1 (Day 1): % active next day
- D7 (Day 7): % active after 1 week
- D30 (Day 30): % active after 1 month
- M3 (Month 3): % active after 3 months

**Target retention:**
- D1: [X%]
- D7: [Y%]
- D30: [Z%]

**SQL for cohort retention:**
```sql
WITH cohort AS (
  SELECT 
    user_id,
    DATE_TRUNC('month', signup_date) AS cohort_month
  FROM users
),
activity AS (
  SELECT 
    user_id,
    DATE_TRUNC('month', event_date) AS activity_month
  FROM events
  GROUP BY 1, 2
)
SELECT 
  c.cohort_month,
  COUNT(DISTINCT c.user_id) AS cohort_size,
  COUNT(DISTINCT a.user_id) AS retained_users,
  COUNT(DISTINCT a.user_id) * 100.0 / COUNT(DISTINCT c.user_id) AS retention_rate
FROM cohort c
LEFT JOIN activity a 
  ON c.user_id = a.user_id 
  AND a.activity_month = c.cohort_month + INTERVAL '1 month'
GROUP BY 1
ORDER BY 1 DESC;
```

## Product Features

### Core Features

**Must-use features** (all customers need these):
1. [Feature 1]
   - Purpose: [What it does]
   - Usage: [How often used]
   - Adoption: [Current %]

2. [Feature 2]
   - Purpose: [What it does]
   - Usage: [How often used]
   - Adoption: [Current %]

### Premium Features

**Available on higher tiers:**
1. [Premium Feature 1]
   - Plan: [Pro, Enterprise]
   - Adoption among eligible: [X%]
   - Correlation with retention: [High, medium, low]

2. [Premium Feature 2]
   - Plan: [Pro, Enterprise]
   - Adoption among eligible: [X%]
   - Correlation with retention: [High, medium, low]

## User Journey & Onboarding

**Activation milestone:**
What does "activated" mean for your product?
- Example: "Completed first report" or "Invited 3+ team members"

**Typical onboarding flow:**
1. Sign up → [X%] complete
2. Connect data source → [Y%] complete
3. Create first dashboard → [Z%] complete
4. Invite team member → [W%] complete
5. **Activated!**

**Time to value:**
- Target: Users reach activation within [X] days
- Current: [Y] days average
- Benchmark: [Z] days

## Usage Patterns

**Typical usage frequency:**
- Power users: [X] times/week
- Regular users: [Y] times/week
- Casual users: [Z] times/month

**Peak usage times:**
- Day of week: [Monday/Tuesday/etc.]
- Time of day: [morning/afternoon]
- Month of year: [seasonality notes]

**Session patterns:**
- Average session duration: [X] minutes
- Pages per session: [Y]
- Feature switches per session: [Z]

## Product-Led Growth

**Virality metrics:**
- **Invite rate**: % of users who invite others
- **Invite acceptance**: % of invited users who join
- **K-factor**: Invites × Acceptance rate

**Self-serve conversion:**
- Trial → Paid: [X%]
- Free → Paid: [Y%]
- Time to convert: [Z] days average

## Data Quality Notes

**Event tracking:**
- Platform: [Segment, Mixpanel, Amplitude, custom?]
- Events: [What's tracked?]
- Properties: [What metadata is captured?]

**Known issues:**
- Mobile app events: [Any gaps?]
- Safari ITP: [Impact on tracking?]
- Ad blockers: [Estimated % loss?]

**Data freshness:**
- Real-time: [Which events?]
- Batch processed: [Which events? Delay?]

---

## Example Product Questions

- "What's our DAU/MAU ratio this month?"
- "Which features have the highest adoption?"
- "Show me retention by signup cohort"
- "How many users activated this week?"
- "What's the average time to first value?"
- "Which customer segment is most engaged?"

