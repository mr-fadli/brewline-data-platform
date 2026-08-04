## ME
so yeah, before continuing, I have a couple of question that I need to ask.

- what is the difference between the shopify system and recharge system?
- how is your product categorized and what kind of product do you have?
- is the order in shopify also can be cancelled?
- do you guys have an inventory data for product or should I assume that your product always ready in stock?
- how do you guys define a refund?
- how does a customer apply a complaints to the store? 

for now, that's all the question I have before we can continue

## Sarah
*Sarah responds:*

Good questions — these are exactly the kind of things that would've bitten us later if we hadn't talked about them. Here's what I know:

**1. Shopify vs. Recharge**
Recharge is a subscription app that plugs into our Shopify store — it's not a separate storefront. When a subscription renews, Recharge actually creates a normal order *inside* Shopify (so it shows up in Shopify's order data too), but Recharge is the system of record for the subscription schedule itself — next charge date, frequency, pause/cancel status, upgrades. So subscription revenue technically flows through Shopify's order data, but you won't understand *why* an order happened (one-off purchase vs. auto-renewal) unless you cross-reference Recharge.

**2. Product catalog**
We sell coffee bags (whole bean or ground, a few roast levels, three bag sizes), some brewing equipment (grinders, drippers, mugs), and the subscription box itself — which is really a bundle of coffee SKUs picked either by us (curated) or the customer (customize). So one "subscription" can map to different products each shipment.

**3. Can Shopify orders be cancelled?**
Yes. A customer or one of our staff can cancel before it ships, and sometimes we've had to cancel after shipping too (rare — like a fraud flag). I honestly don't know off the top of my head whether a cancelled order also automatically gets refunded in Shopify's data or if that's a separate step. Might be worth you checking that directly if you get access to test data.

**4. Inventory**
We do track stock levels in Shopify for our physical products, yeah. I hadn't really thought about whether you'd need it — I only asked for revenue and customer/churn reporting. If you think stockouts matter for explaining a revenue dip, that's your call, but it's not something I explicitly asked for. Wouldn't want you spending a week building an inventory pipeline nobody asked for.

**5. Refunds**
Money returned to the customer — could be a full refund (order fully reversed) or partial (like a $5 credit for a damaged bag). Both happen in Shopify and Square. Just to be clear, that's different from a cancellation — a cancellation is usually *before* the order ships, a refund is *after* money changed hands. Sometimes people use the words interchangeably around here, which honestly might be part of why finance's numbers are messy.

**6. Complaints**
Customers reach us through Zendesk — email, live chat on the site, or a contact form. Some complaints reference an order number, but a lot don't (people just say "my coffee tastes off" or "where's my box"), so I wouldn't assume every ticket is cleanly tied to a specific order.

---

## ME
1. I still need clarity in some spaces, especially about how does the Recharge system works.
2. regarding the subscription team, how does Recharge actually charges customer, was it based on date or based on the last activation time?
3. about the weekly revenue, does it based on fixated date or from the last 7 days?
4. what's the main data exported from Square POS and what kind of file does it used to export the data?

## Sarah
*Sarah responds:*

**1. How Recharge actually works, in more detail**

Each subscription in Recharge has a schedule tied to the *customer's* selected frequency (e.g. "every 30 days," "every 2 weeks"). When a charge date hits, Recharge attempts to bill the saved payment method, and if it succeeds, it pushes a new order into Shopify automatically. If the charge *fails* (expired card, insufficient funds), Recharge retries a few times over a several-day window before marking the subscription "cancelled" for non-payment — which is different from a customer actively hitting "cancel." I mention that because I know churn reporting is going to care about that distinction. Recharge also lets customers pause a subscription for 1-3 cycles instead of cancelling outright, which — again — isn't the same thing as churn, but I could see it accidentally getting counted as churn if you're not careful.

**2. Date-based or based on last activation?**

Date-based, not relative to "last activation." So if someone signs up on the 5th with a 30-day frequency, they're charged on the 5th of each cycle — not 30 days after their *previous successful charge*. This matters because if a charge fails and retries succeed a few days late, the next cycle's date doesn't shift to compensate — it can drift the "expected" charge date out of sync with the "actual" charge date over time. I don't fully understand the mechanics myself, honestly — this might be something you have to dig into Recharge's docs or test data for once you're building.

**3. Weekly revenue — fixed calendar week or trailing 7 days?**

Good catch, I hadn't actually specified that. When I picture it in my head I'm thinking Monday-to-Sunday, matching our internal reporting calendar, not a rolling "last 7 days from today." But I'll be honest — I haven't asked finance if *they* think of it that way too, so don't be surprised if that needs confirming later. I'd lean toward calendar week as your working assumption unless you hear otherwise.

**4. Square POS export**

We get a daily CSV export per location from Square — one file per store per day. Each row is a line item (not a whole order), with a transaction ID, item name/SKU, quantity, price, any discount applied, payment type, employee ID who rang it up, and a timestamp in that store's local time. Customer info is a separate, optional field — populated only if the customer gave their phone number for our loyalty program at checkout.

---

## ME
I still need a little more clarifying information

1. does online customer also buy offline?
2. How many order on average do each channel receive on a daily basis?

## Sarah
*Sarah responds:*

**1. Do online customers also buy offline?**

Yes, and honestly this is probably part of why finance's numbers don't reconcile. We know anecdotally that some of our subscription customers also stop by our retail locations to grab a bag when they run out early, or buy merchandise as gifts. The problem is we have no reliable way to *know* it's the same person unless they happen to use the same phone number for Square's loyalty program that matches... well, nothing, really, since Shopify identifies people by email and Square identifies people by phone number. There's no shared ID between the two systems today. I'd guess it happens more than we realize, but I can't give you a number — that's part of what I'm hoping better reporting will eventually surface, not something I can hand you upfront.

**2. Average daily order volume per channel**

Roughly:
- Shopify (online, including subscription renewals): ~450-600 orders/day, spikes around promotions
- Square (3 retail stores combined): ~200-300 transactions/day total, pretty steady
- Recharge-originated orders are a subset of the Shopify number above, not additional to it — roughly 40% of Shopify orders on a given day are subscription renewals rather than one-off purchases

Nothing at massive scale, but steady enough that you shouldn't design this as a one-time batch script — it needs to run on a schedule.

---

## ME
so when the leadership asked about the weekly revenue broken by channel, does he means only from shopify and square, or you separate one-off shopify from the subscription recharge order made in shopify to get 3 channels?

## Sarah
*Sarah responds:*

Honestly? I said "broken down by channel" without fully thinking that through myself — so let me try to reconstruct what leadership actually cares about, since you're right that there's a real ambiguity here.

When I picture leadership in the boardroom, I think they're picturing **three physical/business channels**: the website, the stores, and "the subscription business" as its own line — because subscriptions are a strategic bet we've been investing in, and the board specifically wants to know if *that* bet is paying off, not just "online vs. offline." So my gut says yes — split Shopify one-off from Shopify-via-Recharge, giving you three channels: **Retail (Square), Online one-off (Shopify), and Subscription (Recharge-originated Shopify orders).**

But I'll be straight with you — I hadn't actually specified that when I wrote the memo, so this is me thinking out loud, not a confirmed answer. If I were you, I wouldn't just take my word for it as gospel either.

---

## ME
I need a little clarification for the meaning of best customers. in my assumption, it's going to be the top customers who spent the highest amount of money and generate the most revenue, but do the company have another definitions for this?

## Sarah
*Sarah responds:*

That's a fair reading of what I said, and honestly, "highest total spend" is probably what most people in the room would nod along to if you showed them that list. But let me push on it a little, because I don't think revenue alone is the *whole* story for us.

Here's the thing — a customer who spent $500 once, six months ago, and never came back isn't really who I'd brag about to the board. Meanwhile, a subscriber who's been paying us $28/month for a year, reliably, is worth more to this business long-term even though their trailing total might look smaller on a simple sum. That's actually *why* I asked for LTV and churn tracking in the same breath as "best customers" — I think of them as related questions, not separate ones. So when I say "best," I'm probably fuzzily gesturing at some mix of: how much they've spent, how long they've stuck around, and whether they're still active — not just a single "total spent" leaderboard.

I don't have a precise formula for you, though. I've heard the term "LTV" thrown around by our marketing team but I'd be lying if I said I could tell you exactly how they calculate it today, or if they even do consistently.

---

## ME

1. does the leadership have any expectations of how often a customer places an order to be called "sticking around"?
2. you said that "stop finding out about refund spikes a month later" means that this was happened before, right? can you elaborate about it more

## Sarah
*Sarah responds:*

**1. Expectations on order frequency for "sticking around"**

Honestly, no — nobody's given me a number. If you'd asked me to guess off the top of my head, I'd probably say something like "ordered at least once in the last 60-90 days," since that roughly matches how often even our slower subscribers renew (our shortest frequency is 14 days, longest I've seen customers pick is close to 60). But that's me pulling a number out of the air just now, not something the board agreed on. If you need a concrete threshold to build against, I'd treat that as your own documented assumption rather than wait on us to define it formally — we probably won't, not before your deadline anyway.

**2. The refund spike story**

Yeah, this actually happened, and it's part of why I brought it up. About two months ago we ran a promotion on one of our darker roasts, and it turned out we'd mislabeled the grind size on a big batch of bags — people ordered "whole bean" and got "ground" instead, or something close to that mix-up. Customers noticed, complained, and asked for refunds. The problem wasn't that it happened — mistakes happen — the problem was **nobody noticed until our monthly finance close**, almost four weeks after the batch shipped, when someone finally asked "why does this month's refund total look so much higher than usual." By then we'd already shipped a few more batches of the same mislabeled product because nobody had flagged it early. If we'd seen refund volume tick up within a few days of the first batch going out, we could've caught the labeling issue and stopped it before it compounded.

So when I say "stop finding out a month later," I mean it literally — I want something closer to daily or weekly visibility into refund volume/rate, ideally with enough of a signal that a spike stands out instead of getting buried until someone runs a monthly report.

---

## ME
do the company have any other data source such as shipment status or was everything just from the three channels alone?

## Sarah
*Sarah responds:*

Actually, yes — I probably should've mentioned this earlier, sorry. We use **ShipStation** for fulfillment, which pulls orders from Shopify once they're paid and pushes back tracking status — things like "label created," "shipped," "in transit," "delivered," and occasionally "delivery exception" (lost package, delivery attempt failed, etc.). It updates the Shopify order record with a tracking number and fulfillment status, but the more detailed tracking history — the carrier's scan events — really only lives in ShipStation itself, not in Shopify.

I hadn't listed it originally because nobody explicitly asked me for shipping visibility, but now that you ask... I could see it being relevant to a couple of things I *did* ask for. Remember those "where's my box" complaints in Zendesk? A support rep can't tell if that's a real problem or just an impatient customer without checking tracking status, and I don't think our systems currently make that easy. So there might be a connection there, but I want to be upfront that this wasn't part of my original ask — I'm just thinking out loud as you ask me about it.

## ME
to sarah, is there any store policies regarding the refund system? such as How long is the time limit for customers to request a refund after receiving the goods? and what is the regulation about the partially refund items?

## Sarah
*Sarah responds:*

Good question, and honestly one I should have thought to mention given how much refunds have come up. Here's what I know:

**Refund window:** Officially, our policy page says customers can request a refund within **30 days of delivery** — not order date, delivery date, since obviously shipping takes time and it wouldn't be fair to start the clock before they even have the product. That said, I know for a fact our support team has approved refunds outside that window before, especially for quality issues that are clearly our fault (like the mislabeling incident) rather than the customer just changing their mind. So the *written* policy is 30 days from delivery, but the *actual enforced* behavior has exceptions our system probably doesn't track as a clean flag anywhere — it's more "the rep used their judgment," which I realize isn't very helpful for you trying to build clean logic around it.

**Partial refunds:** There's no fixed formula, unfortunately — it's case-by-case based on what the support rep decides is fair. A damaged item might get a partial refund equal to just that item's price (like the $5 example from earlier), or occasionally a rep will throw in extra credit as a goodwill gesture that has nothing to do with the actual item price. So you can't assume `refund_amount` always maps cleanly back to a specific line item's price — sometimes it will, sometimes it won't, and there's no field anywhere that says "this refund was goodwill vs. exact item cost."

I don't think there's a written internal policy doc for partial refunds — this is genuinely just "whatever the support rep and their manager agree on."

---

## ME (Final Judgment)
see in the docs/design_decisions_log.md

## Sarah
*Sarah responds:*

This reads like something I could actually bring to the board, so — good work, genuinely. I like that you separated "walk-in" from "loyalty" instead of pretending you can identify people who never gave us anything to identify them by. And I appreciate you flagging Zendesk/ShipStation as "captured but not used yet" rather than either ignoring them or trying to force them in — that's the kind of thing that makes me trust the roadmap. Two weeks sounds reasonable to me too. Go ahead and start building — just flag it if something turns out harder than expected, like you said.

---