# Data Quality Notes

> Document known data issues, quirks, and caveats.
> This helps the agent provide accurate answers and set proper expectations.

## Known Issues

### Issue: [Issue Name/Description]

**What's affected:**
- Tables: [table1, table2]
- Columns: [column names]
- Time period: [when did this issue start/end?]

**Impact:**
- [Describe how this affects analysis]
- [Which metrics are impacted?]

**Workaround:**
```sql
-- Example workaround query
SELECT ...
```

**Status:**
- [ ] Open - Issue ongoing
- [ ] Fixed - Resolved as of [date]
- [ ] Mitigated - Workaround in place

---

### Example: Missing UTM Parameters (Aug 2024)

**What's affected:**
- Table: `events`
- Columns: `utm_source`, `utm_campaign`, `utm_medium`
- Time period: August 1-15, 2024

**Impact:**
- Attribution data incomplete for 2 weeks
- Approximately 30% of web events missing source
- Marketing channel reports show dip in "Paid" traffic

**Workaround:**
- For Aug 1-15, use `referrer` field as fallback
- Known referrers: google.com → "Organic", ads.google.com → "Paid Search"

**Status:**
- [x] Fixed - Tracking code updated on Aug 16, 2024

---

## Data Freshness

### Real-Time Data

**Available immediately:**
- User events (clicks, pageviews, actions)
- API calls
- System metrics

### Batch-Processed Data

**Updated on schedule:**
- **Billing/revenue data**: Synced daily at 6 AM UTC (delay: ~6 hours)
- **CRM data**: Synced every 4 hours
- **Ad platform data**: Synced daily at 8 AM UTC
- **Warehouse analytics**: Updated nightly at 2 AM UTC

**Important:**
- Don't expect today's revenue numbers before 7 AM UTC
- Yesterday's data is "final" by 8 AM UTC

### Historical Data Availability

**Data retention:**
- Events: Last 2 years
- Raw logs: Last 90 days
- Aggregated metrics: All history (since [start date])

## Data Transformations

### Timezone Handling

**Server timezone:** [UTC, EST, PST?]

**Conversion rules:**
- All timestamps stored in UTC
- Display timezone: [User's local, company default?]
- Date boundaries: Use UTC midnight unless specified

**Example:**
```sql
-- Convert to user's timezone
SELECT 
  event_timestamp AT TIME ZONE 'America/New_York' AS event_time_et
FROM events;
```

### Currency Conversions

**Base currency:** [USD, EUR, etc.]

**Conversion logic:**
- Exchange rates updated: [Daily, weekly, monthly?]
- Rate source: [ECB, OANDA, internal?]
- Applied at: [Transaction time, reporting time?]

**Example:**
```sql
-- Convert to USD
SELECT 
  amount_local,
  currency,
  amount_local * exchange_rate_to_usd AS amount_usd
FROM transactions t
LEFT JOIN exchange_rates er 
  ON t.currency = er.currency 
  AND DATE(t.transaction_date) = er.rate_date;
```

### Null Handling

**Common null scenarios:**
1. **User didn't provide data**
   - Example: Company size field optional
   - Treatment: Exclude from aggregates or use "Unknown" category

2. **Data not yet available**
   - Example: Revenue pending for recent orders
   - Treatment: Flag as "pending" or filter out incomplete periods

3. **Historical data gap**
   - Example: Feature didn't exist before [date]
   - Treatment: Note in results when showing historical trends

## Table-Specific Notes

### `users` Table

**Known issues:**
- **Email duplicates**: ~0.5% of users have multiple accounts with same email
  - Workaround: Use `user_id` not `email` for counts
- **Signup date**: Some test accounts have future dates
  - Filter: `WHERE signup_date <= CURRENT_DATE`

**Important columns:**
- `status`: Values are 'active', 'churned', 'suspended'
- `plan_type`: Updated when user upgrades/downgrades (no history)
- `mrr`: Cached value, updated nightly (may lag by 1 day)

### `orders` Table

**Known issues:**
- **Refunds**: Stored as negative amounts in same table
  - Filter: `WHERE amount > 0` to exclude refunds
- **Currency**: Mixed currencies before Jan 2024
  - Use `amount_usd` for consistent reporting

**Important columns:**
- `status`: 'paid', 'pending', 'failed', 'refunded'
- `order_date`: When order placed
- `paid_date`: When payment received (may differ from order_date)

### `events` Table

**Known issues:**
- **Mobile app tracking**: iOS tracking gaps due to ATT (App Tracking Transparency)
  - Estimate: ~40% of iOS users opt out
- **Ad blockers**: ~15% of web events blocked
  - Affected: Pageview counts, session tracking

**Important columns:**
- `event_name`: [List key event names]
- `user_id`: Null for anonymous users
- `session_id`: Resets after 30 minutes of inactivity

## Testing & Staging Data

**How to exclude test data:**
```sql
WHERE user_email NOT LIKE '%@example.com'
  AND user_email NOT LIKE '%+test%'
  AND user_id NOT IN (SELECT user_id FROM test_accounts)
  AND table_name NOT LIKE '%_test'
  AND table_name NOT LIKE '%_staging'
```

**Known test accounts:**
- user_id: [list IDs if applicable]
- Domains: `@test.com`, `@example.com`, `@staging.internal`

## Schema Changes

### Recent Changes

**[Date]: [Change Description]**
- What changed: [New column, renamed table, etc.]
- Why: [Business reason]
- Impact: [Which queries affected?]
- Migration: [How to update existing queries]

**Example: 2024-09-15 - Split `customers` table**
- Old: Single `customers` table
- New: `customers` (base info) + `subscriptions` (plan info)
- Impact: Queries needing plan info now require JOIN
- Migration:
  ```sql
  -- Old way
  SELECT * FROM customers WHERE plan = 'pro';
  
  -- New way
  SELECT c.* 
  FROM customers c
  INNER JOIN subscriptions s ON c.id = s.customer_id
  WHERE s.plan = 'pro' AND s.status = 'active';
  ```

## When to Mention Data Quality

**Agent should proactively mention:**
- Known issues affecting the query
- Data freshness concerns ("Revenue numbers won't be final until tomorrow")
- Approximations or estimates ("Due to ad blockers, actual traffic may be ~15% higher")
- Missing data periods ("Note: Aug 1-15 attribution data is incomplete")

**Example response:**
> "Based on the available data, revenue for today is $12,450. **Note:** Today's revenue numbers are preliminary and will be final after tonight's sync (typically by 7 AM UTC tomorrow)."

---

## Reporting New Issues

If you discover a data quality issue:
1. Document it here following the template above
2. Notify: [data team email/slack channel]
3. Tag affected dashboards/reports
4. Create ticket: [link to issue tracker]

