# Business Requirement Memo

**From:** Sarah Nguyen, Head of Analytics — Brewline Coffee Co.
**To:** Data Engineering
**Subject:** Unified sales & subscription reporting — need this before the board meeting

---

Hi,

As you know we've grown fast this year — we now sell through three channels and leadership has zero visibility into how they compare. I need a single source of truth for revenue and customer behavior. Right now everyone pulls their own numbers and nothing matches, which is embarrassing in exec meetings.

**Our current systems:**

1. **Shopify** (online store) — exports order data. Each order has a customer email, line items, totals, discounts, currency (we sell in USD and CAD), and timestamps in the customer's local timezone.
2. **Square POS** (3 physical retail locations) — exports daily transaction batches. Customers here are often "walk-ins" with no email captured, but repeat customers can be identified by a loyalty phone number if they opted in.
3. **Recharge** (subscription billing for our coffee subscription boxes) — tracks recurring orders, upgrades/downgrades, pauses, and cancellations. Subscription customers also show up in Shopify as regular orders when they buy one-off products, using the same email.
4. **Zendesk** (support tickets) — not a sales system, but leadership wants to know if customers who file complaints are more likely to churn. Low priority, but noted here so you're aware it may come up later.

**What leadership actually wants (their words, not mine):**

- "A weekly revenue number we can trust, broken down by channel."
- "Know who our best customers are and whether they're sticking around."
- "See subscription churn before it happens, not after."
- "Stop finding out about refund spikes a month later."

**Known pain points from the team:**

- Finance says Shopify and Square revenue "never reconciles" — nobody's been able to explain why.
- Marketing wants customer lifetime value but admits they don't have a consistent definition of "customer" across systems.
- The subscriptions team flagged that a "cancelled" subscription in Recharge sometimes gets reactivated within 48 hours (people cancel by mistake or to dodge a charge date), and counting that as churn has caused false alarms before.
- Retail store timestamps are in local store time; online orders are stored in customer browser time; nobody has agreed on which timezone reporting should standardize to.

**Timeline:** Leadership wants a first version in front of them in "a few weeks." I'd rather you take the time to do it right than rush something we have to redo.

**Budget/tooling:** No constraints from me — use whatever stack you think is right, as long as it's something we could realistically run and maintain, not a one-off script.

Let me know what questions you have before you start building.

— Sarah

---

## Your task

Treat this memo the way you'd treat a real one: it's incomplete on purpose. Before or while building, work out:

- What questions you'd actually need answered before writing a single line of pipeline code (and what reasonable assumption you'd make if you *couldn't* get an answer in time).
- What "a customer" means across three systems that don't share a clean ID.
- How you'd define and detect subscription churn given the reactivation-within-48-hours wrinkle.
- How timestamps get normalized, and why that decision matters for a "weekly revenue" number.
- What your target schema looks like, and why.
- What in this memo is a real requirement vs. a vague aspiration you'd need to scope down or push back on.

When you're ready, share your approach (data model, assumptions, architecture, or the pipeline itself) and I'll review it as a mentor would — pointing out what's solid, what a senior engineer would question, and what a reviewer/interviewer is likely to probe on.
