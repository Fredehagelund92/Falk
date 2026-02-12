# Data Quality Notes (Gotchas)

> Document known data issues, quirks, and caveats.
> The agent will mention these when relevant to keep answers accurate.

## Data Freshness

**Real-time:** [What updates immediately — e.g. user events]

**Batch-processed:** [What updates on schedule — e.g. "Revenue data synced daily at 6 AM UTC"]

**Important:** Don't expect today's revenue before [time]. Yesterday's data is "final" by [time].

## Known Issues

### [Issue Name]

**What's affected:** Tables/columns, time period

**Impact:** [How this affects analysis]

**Workaround:** [How to handle it]

**Status:** [ ] Open  [ ] Fixed  [ ] Mitigated

---

### Example: Missing UTM Parameters (Aug 2024)

**What's affected:** `events` table, `utm_source`, `utm_campaign`, `utm_medium` — Aug 1-15, 2024

**Impact:** ~30% of web events missing source; marketing reports show dip

**Workaround:** Use `referrer` field as fallback for that period

**Status:** [x] Fixed

## Table-Specific Notes

### `users` Table
- **Email duplicates:** ~0.5% — use `user_id` not `email` for counts
- **Signup date:** Some test accounts have future dates — filter `WHERE signup_date <= CURRENT_DATE`

### `orders` Table
- **Refunds:** Stored as negative amounts — filter `WHERE amount > 0` to exclude

### `events` Table
- **iOS tracking:** ~40% opt out of ATT — traffic may be undercounted
- **Ad blockers:** ~15% of web events blocked

## When to Mention

The agent should proactively mention:
- Known issues affecting the query
- Data freshness ("Revenue won't be final until tomorrow")
- Approximations ("Due to ad blockers, actual traffic may be ~15% higher")
