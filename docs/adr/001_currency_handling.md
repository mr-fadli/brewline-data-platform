# ADR-001 : Base Currency and Exchange Rate Handling

## Status
Accepted

## Context
The currency stored in Shopify used USD and CAD. This will make the revenue not reconciles with the actual data.

## Decision
- The Currency will be stored in USD to match the local store base currency (US).
- The Exchange Rate will use the one based on the date the order happened (not at the rate the report-run happens).

## Alternative Considerations
- separate the USD and CAD Report - Rejected. The leadership specifically wanted **single source of truth**.
- Convert the currency using the report's run date time - Rejected. This will make the historical data invalid since the exchange rate always fluctuating.

## Consequences
Required a fixed error rate tables. for v1, we will use fixed mock data for the exchange rate and not connect it to LIVE API.