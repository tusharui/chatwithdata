from decimal import Decimal
from datetime import datetime, date


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(i) for i in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, set):
        return [make_json_safe(i) for i in sorted(obj, key=str)]
    if isinstance(obj, tuple):
        return [make_json_safe(i) for i in obj]
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    return obj


class ChartService:
    def format_chart_data(self, chart_info: dict, results: list[dict]) -> dict:
        chart_type = chart_info.get("type", "table")
        x_col = chart_info.get("x_column", "")
        y_col = chart_info.get("y_column", "")
        title = chart_info.get("title", "Query Results")

        if chart_type == "table" or not results:
            return make_json_safe({
                "type": "table",
                "title": title,
                "data": results,
                "columns": list(results[0].keys()) if results else [],
            })

        # Validate that referenced columns exist in the results
        available_cols = set(results[0].keys()) if results else set()
        if x_col not in available_cols or y_col not in available_cols:
            return make_json_safe({
                "type": "table",
                "title": title,
                "data": results,
                "columns": list(available_cols),
            })

        chart_data = []
        for row in results:
            x_val = row.get(x_col)
            x_val = "" if x_val is None else str(x_val)
            y_val = row.get(y_col)
            try:
                y_val = float(y_val) if y_val is not None else 0
            except (ValueError, TypeError):
                y_val = 0
            chart_data.append({"name": x_val, "value": y_val})

        return make_json_safe({
            "type": chart_type,
            "title": title,
            "data": chart_data,
            "x_column": x_col,
            "y_column": y_col,
        })


chart_service = ChartService()
