# Business Context

This file helps the agent understand your business, so it can answer questions in context and make smart suggestions.
By default, this file is loaded at startup when `agent.knowledge.enabled: true` in `falk_project.yaml`.

## What We Do

**Our business in one sentence:**
[Example: We're a B2B SaaS company that helps e-commerce businesses analyze their customer data]

**Business model:** [B2B/B2C/Marketplace] + [Subscription/Transactional/Freemium/Advertising]

**Main products:**
- [Product 1]: [What it does]
- [Product 2]: [What it does]

## How People Talk About Our Data

When someone on your team says these things, here's what they actually mean:

**"Customer" means:**
[Your specific definition - e.g., "An organization with an active subscription" or "Anyone who's made a purchase"]

**"Active user" means:**
[Your definition - e.g., "Logged in within last 30 days" or "Made a transaction this month"]

**"Conversion" means:**
[What counts - e.g., "Trial → Paid" or "Free → Premium tier"]

**"Churn" means:**
[Your definition - e.g., "Canceled subscription" or "No activity for 90 days"]

Add more terms as your team uses them. The agent will use these definitions when answering questions.

## How Our Business Works

**The customer journey:**
[Example: Someone signs up (Lead) → Starts trial (Trial User) → Subscribes (Customer) → Upgrades plan (Premium Customer)]

**What drives our revenue:**
[Example: Revenue = Active Customers × Average Subscription Price]
or
[Example: Revenue = Orders × Average Order Value]

**Geographic breakdown:**
[Which regions you operate in and any important differences - e.g., "US and EU are direct sales, APAC is through partners"]

**Product lines:**
[If you have different product categories with different economics - e.g., "Basic plan vs Enterprise" or "Hardware vs Software"]

## What Matters Most

**Our North Star Metric:**
[The #1 metric your company tracks - e.g., "Monthly Recurring Revenue (MRR)" or "Daily Active Users (DAU)"]

**Why it matters:**
[Brief explanation - e.g., "MRR shows our business health and growth trajectory"]

**How we measure success:**
- [Key metric 1] - [Why you track it]
- [Key metric 2] - [Why you track it]
- [Key metric 3] - [Why you track it]

## Important Context for Analysis

**Seasonality:**
[Any seasonal patterns - e.g., "Q4 is 40% of our annual revenue" or "Summer is slow, back-to-school in Sept is our peak"]

**Business events:**
[Major events that affect data - e.g., "Launched new pricing March 2024" or "Entered EU market Q2 2024"]

**Comparison periods:**
[What makes sense to compare - e.g., "Always compare month-over-month, not week-over-week due to billing cycles"]
