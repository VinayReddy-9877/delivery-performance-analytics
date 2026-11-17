# Metric and comparison notes

## Grain

Each row in the prepared order file represents one order. The item file represents order items. The merchandise value of an order is the sum of item prices; it excludes freight. Item totals are reconciled back to the order before reporting.

## Eligible orders

An assessed delivery has both an observed delivery timestamp and an estimated delivery date. `is_late` is true when the actual delivery calendar date is later than the promised calendar date. Non-assessed rows remain in the total-order count but not the late-rate denominator.

## The lane benchmark

Lane comparisons use orders with exactly one seller. The benchmark is the late rate of same-state single-seller deliveries. Expected late orders are calculated as lane count multiplied by this benchmark. Excess is observed late count minus expected count. This comparison is useful for ranking investigation volume, but cannot be interpreted as causal preventable delays.

SP → RJ contributes 1,147 late orders out of 8,048 assessed, compared with a same-state benchmark of 4.56%; its benchmark excess is approximately 780 orders. The top five lanes contribute approximately 1,294 excess orders on the same basis.

## Uncertainty

State-level intervals use the 95% Wilson binomial interval. Smaller states such as AL should not be prioritized solely because their rate is the highest: 85 late orders in 397 assessed contribute only 1.3% of all late orders. RJ accounts for more volume.

## Automation

An alert needs at least 50 completed single-seller deliveries within the week and a late rate above twice the earlier-history same-state benchmark. It is evaluated at the end of the delivery week. No intervention or savings are attributed to an alert.

## Sensitivity: does the priority depend on the baseline?

SP → RJ has 8,048 assessed deliveries and 1,147 late (14.25%).
The same-state benchmark is a *ranking benchmark*, not a fair distance-matched control.
To test whether it is the choice of baseline alone that creates the finding,
I also compare SP → RJ with other cross-state traffic.

| Comparison group | Late rate | Difference for SP → RJ (order benchmark) |
|---|---:|---:|
| Same-state single-seller orders | 4.56% | approximately 780 |
| All cross-state single-seller orders (including SP → RJ) | 8.14% | approximately 492 |
| Other cross-state single-seller orders (excluding SP → RJ) | 7.21% | approximately 567 |

These are simple rate-standardized differences, not causal effects or forecasts.
Shipment distance, route mix, carrier choice and period can confound them.
Even against the stricter cross-state comparisons, SP → RJ remains the
largest high-volume lane for investigation in this extract.

## Weekly alert timing and seller-level attribution

Weekly alerts group orders by the **observed delivery completion date**,
not purchase week. A report for a week is emitted *after that week ends*.
Its benchmark uses only same-state orders delivered **before the start**
of the reporting week. Thus a future completed delivery cannot enter an
earlier weekly alert or its comparison rate. This is a retrospective
exception monitor, not a purchase-time late-risk prediction.

Seller performance SQL joins the set of distinct `(order_id, seller_id)`
combinations from item rows to order outcomes. Multiple items from the
same seller in an order count as **one seller-attributed order**.
For a multi-seller order, its single delivery outcome is attributed to
each participating seller, because the data does not identify which seller
caused the delay; seller-attributed counts should not be summed to obtain
unique order counts.
