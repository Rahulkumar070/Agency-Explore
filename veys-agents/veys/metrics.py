"""Compute checkout-start rates from aggregate, user-supplied counts."""
import csv
from decimal import Decimal


def checkout_metrics(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["period", "visitors", "checkout_starts"]:
            raise ValueError("Metrics CSV header must be period,visitors,checkout_starts.")
        summary = {}
        for row in rows:
            period = (row["period"] or "").strip()
            if not period or period in summary or len(summary) >= 100 or None in row:
                raise ValueError("Use at most 100 uniquely named reporting periods.")
            try:
                visitors = int(row["visitors"])
                starts = int(row["checkout_starts"])
            except (TypeError, ValueError) as exc:
                raise ValueError("Visitors and checkout starts must be integer counts.") from exc
            if not 0 <= starts <= visitors <= 10**12:
                raise ValueError("Counts must satisfy 0 <= checkout starts <= visitors <= 1 trillion.")
            rate = str(round(Decimal(starts) * 100 / visitors, 2)) if visitors else None
            summary[period] = {"visitors": visitors, "checkout_starts": starts, "checkout_start_percent": rate}
        if not summary:
            raise ValueError("Metrics CSV contains no data rows.")
        return summary
