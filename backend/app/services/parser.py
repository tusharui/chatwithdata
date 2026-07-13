import json
import re
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.dataset import Dataset, DatasetColumn


class ParserService:
    async def process_file(
        self, file_path: str, dataset: Dataset, db: AsyncSession
    ) -> dict:
        import pandas as pd

        file_ext = file_path.rsplit(".", 1)[-1].lower()

        if file_ext == "csv":
            for encoding in ("utf-8", "latin-1", "cp1252", "utf-16"):
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            else:
                raise ValueError("Could not read CSV file with any supported encoding")
        elif file_ext in ("xlsx", "xls"):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        if df.empty:
            raise ValueError("File contains no data rows")

        df = df.dropna(how="all")
        df = df.reset_index(drop=True)

        # Auto-detect and clean numeric-ish text columns
        for col in df.columns:
            if df[col].dtype == "object":
                cleaned = df[col].dropna().head(20)
                if len(cleaned) == 0:
                    continue
                numeric_count = 0
                for val in cleaned:
                    s = str(val).strip()
                    s = s.replace(",", "").replace("$", "").replace("€", "").replace("£", "")
                    has_suffix = s.lower().endswith("k") or s.lower().endswith("m")
                    s_core = s
                    if has_suffix:
                        s_core = s[:-1]
                    try:
                        float(s_core)
                        numeric_count += 1
                    except ValueError:
                        pass
                if numeric_count / len(cleaned) >= 0.8:
                    converted = []
                    for val in df[col]:
                        if pd.isna(val):
                            converted.append(None)
                            continue
                        s = str(val).strip()
                        multiplier = 1
                        if s.lower().endswith("k") and len(s) > 1:
                            multiplier = 1000
                            s = s[:-1]
                        elif s.lower().endswith("m") and len(s) > 1:
                            multiplier = 1_000_000
                            s = s[:-1]
                        s = s.replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
                        try:
                            converted.append(float(s) * multiplier)
                        except ValueError:
                            converted.append(None)
                    df[col] = converted

        # Sanitize column names (do this BEFORE building columns_info)
        clean_cols = []
        for c in df.columns:
            name = str(c).strip()
            name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
            name = re.sub(r"_+", "_", name).strip("_")
            if not name:
                name = f"col_{len(clean_cols)}"
            clean_cols.append(name)
        df.columns = clean_cols

        table_name = f"ds_{dataset.id.replace('-', '_')}"
        dataset.table_name = table_name
        dataset.row_count = len(df)
        dataset.column_count = len(df.columns)

        dtype_map = {
            "int64": "BIGINT",
            "float64": "DOUBLE PRECISION",
            "object": "TEXT",
            "bool": "BOOLEAN",
            "datetime64[ns]": "TIMESTAMP",
            "datetime64[ns, UTC]": "TIMESTAMP",
            "timedelta64[ns]": "INTERVAL",
        }

        columns_info = []
        for idx, (orig_col, clean_col) in enumerate(zip(list(str(c) for c in df.columns), clean_cols)):
            pg_type = dtype_map.get(str(df[clean_col].dtype), "TEXT")
            raw_samples = df[clean_col].dropna().head(5).tolist()
            sample_vals = [str(v) for v in raw_samples]

            columns_info.append(
                {
                    "name": clean_col,
                    "original_name": orig_col,
                    "pg_type": pg_type,
                    "dtype": str(df[clean_col].dtype),
                    "sample": sample_vals,
                    "nullable": bool(df[clean_col].isnull().any()),
                    "ordinal": idx + 1,
                }
            )

            safe_sample = json.dumps(sample_vals, default=str)
            col_obj = DatasetColumn(
                dataset_id=dataset.id,
                name=clean_col,
                data_type=str(df[clean_col].dtype),
                sample_values=safe_sample,
                is_nullable=bool(df[clean_col].isnull().any()),
                ordinal_position=idx + 1,
            )
            db.add(col_obj)

        # Create table — use sanitized column names (same as INSERT)
        create_cols = ", ".join(
            [f'"{info["name"]}" {info["pg_type"]}' for info in columns_info]
        )
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({create_cols})'
        await db.execute(text(create_sql))

        # Build batch inserts (500 rows at a time)
        BATCH_SIZE = 500
        col_names = ", ".join([f'"{c}"' for c in clean_cols])
        placeholders = ", ".join([f":p{i}" for i in range(len(clean_cols))])
        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

        for start in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[start : start + BATCH_SIZE]
            rows = []
            for _, row in batch.iterrows():
                params = {}
                for i, col in enumerate(clean_cols):
                    val = row[col]
                    if pd.isna(val):
                        params[f"p{i}"] = None
                    elif isinstance(val, bool):
                        params[f"p{i}"] = val
                    elif isinstance(val, (int, float, np.integer, np.floating)):
                        params[f"p{i}"] = float(val) if isinstance(val, (float, np.floating)) else int(val)
                    else:
                        params[f"p{i}"] = str(val)
                rows.append(params)

            await db.execute(text(insert_sql), rows)

        return {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_info,
        }


parser_service = ParserService()
