"""
Cliente para o Google Analytics Data API v1.
Requer: pip install google-analytics-data
Autenticação via Service Account JSON (não OAuth interativo).
"""

from __future__ import annotations

import os
from pathlib import Path


def get_top_pages(
    property_id: str,
    credentials_path: str,
    limit: int = 25,
) -> list[dict]:
    """
    Retorna as top N páginas por sessões nos últimos 30 dias.
    Executa de forma síncrona — chamar via run_in_executor no servidor async.
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
        Path(credentials_path).resolve()
    )

    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    )

    response = client.run_report(request)

    return [
        {
            "path": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
        }
        for row in response.rows
    ]
