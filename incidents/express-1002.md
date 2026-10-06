# Incident: express-1002 lookup returned HTTP 500

- Affected endpoint: `GET /api/orders/express-1002`
- Signal: `http.server.requests` with `http.response.status_code=500`
- Root cause: `datetime.replace(day=placed_at.day + 2)` constructed an invalid calendar date when an express order was created near the end of a month.
- Fix: calculate the estimate with `placed_at + timedelta(days=2)`, which correctly crosses month and year boundaries.
- Verification: the regression test `test_express_order_crosses_month_boundary` returns HTTP 200 and an estimated-delivery date.
- Rollback: revert the one-line date calculation if an unexpected regression appears.
