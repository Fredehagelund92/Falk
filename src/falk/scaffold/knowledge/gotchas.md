# Data Gotchas & Known Issues

Things the agent should know about your data so it can give accurate answers and warn people when needed.
By default, this file is loaded at startup when `agent.knowledge.enabled: true` in `falk_project.yaml`.

## When Data Updates

**What's fresh (updates immediately):**
[Example: User activity events, page views, clicks]

**What's delayed (batch updates):**
[Example: Revenue data refreshes every morning at 6 AM UTC]

**Important timing notes:**
- Today's revenue won't show until [time tomorrow]
- Yesterday's data is final by [time]
- [Any other timing quirks]

## Metric-Specific Gotchas

### Revenue

**What to know:**
[Example: "Revenue has a 24-hour processing delay" or "Includes refunds as negative values"]

**When to warn about it:**
[Example: "If someone asks about today's revenue, tell them it won't be available until tomorrow morning"]

### Customer Counts

**What to know:**
[Example: "Active customers = paid subscription in last 30 days" or "Customer count includes test accounts until we filter them"]

**Edge cases:**
[Example: "Customers who pause subscription still count as 'active' for 30 days"]

### Orders / Transactions

**What to know:**
[Example: "Canceled orders stay in the data but marked with status='canceled'" or "Returns appear as separate negative transactions"]

**Watch out for:**
[Example: "Big spike on Dec 1st each year is annual renewals, not new customers"]

## Dimension-Specific Issues

### Region / Geography

**Known issues:**
[Example: "IP-based location is ~90% accurate, some VPN users show up in weird places"]

**Important context:**
[Example: "We group APAC as one region but it includes both Japan (direct) and Southeast Asia (partners)"]

### Customer Segment

**Quirks:**
[Example: "Some old customers have 'Unknown' segment because we added segmentation in 2023"]

**What to mention:**
[Example: "If segment is 'Unknown', those are pre-2023 customers"]

### Product Category

**Known issues:**
[Example: "Products can be in multiple categories, so category totals won't sum to 100%"]

## Historical Data Issues

### [Example: Migration Gap - June 2023]

**What happened:**
[Example: "We migrated systems mid-June 2023, so June 1-15 data is incomplete"]

**How it affects analysis:**
[Example: "Any June 2023 comparisons will look artificially low"]

**What to tell people:**
[Example: "When showing June 2023, mention the migration gap and suggest using July instead"]

### [Example: Pricing Change - March 2024]

**What changed:**
[Example: "We raised prices 15% across all plans"]

**How it affects comparisons:**
[Example: "Revenue growth after March 2024 includes the price increase effect"]

**Context to add:**
[Example: "If someone compares Q2 to Q1, mention that the price increase contributed to the revenue growth"]

## When to Proactively Warn People

The agent should speak up when:

✅ **Someone asks about very recent data:**
"Heads up - today's revenue won't be final until tomorrow morning at 6 AM"

✅ **The data has known issues in their timeframe:**
"Just FYI, June 2023 had a migration gap so those numbers are incomplete"

✅ **Approximations matter:**
"This is based on IP location which is about 90% accurate - some users might be in different regions"

✅ **Comparisons might be misleading:**
"March 2024 includes a 15% price increase, so the revenue jump isn't all from growth"

## Examples in Action

**User asks:** "What's our revenue today?"
**Agent says:** "Today's revenue is sitting at $12,450 so far, but keep in mind it won't be fully processed until tomorrow morning at 6 AM UTC. Want to see yesterday's final numbers instead?"

**User asks:** "Why did revenue jump in March?"
**Agent says:** "Revenue went up $50k in March (that's +20%). Quick context though - we raised prices 15% at the start of March, so part of that growth is from the price increase rather than new customers. Want me to break down orders vs pricing to see the split?"
