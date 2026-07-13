import re
from app.services.ai_service import ai_service

NL2SQL_SYSTEM_PROMPT = """You are an expert PostgreSQL SQL generator. 
Convert natural language questions into precise, optimized SQL queries.

CRITICAL RULES:
- Use PostgreSQL syntax only
- Do NOT use FLOOR() — use CAST(x AS INTEGER) or TRUNC(x) instead
- Do NOT use CEILING() — use CAST(x AS INTEGER) or TRUNC(x) + 1 instead
- Use double quotes for column names that contain spaces or are case-sensitive
- Use ILIKE for case-insensitive text matching
- Use LIKE for partial matching
- Return aggregate functions when appropriate (COUNT, SUM, AVG, MAX, MIN)
- Use ORDER BY to sort results meaningfully
- Use LIMIT when the question implies top N
- Handle NULL values with COALESCE when needed
- Always alias computed columns
- Do NOT use SELECT * unless explicitly asked
- When a column is TEXT but contains numeric data (like "72k", "$50,000"), clean it first:
  - Remove non-numeric characters: REGEXP_REPLACE(column, '[^0-9.-]', '', 'g')
  - Then CAST to NUMERIC: CAST(REGEXP_REPLACE(column, '[^0-9.-]', '', 'g') AS NUMERIC)
  - For suffixes like "k" (thousands): multiply by 1000
- Return ONLY the SQL query, nothing else"""

_DANGEROUS_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)


class NL2SQLService:
    async def generate_sql(
        self, question: str, schema_info: dict, sample_data: str = ""
    ) -> str:
        schema_text = self._format_schema(schema_info)

        prompt = f"""Database Schema:
{schema_text}

{f'Sample data (first 3 rows):{chr(10)}{sample_data}' if sample_data else ''}

Question: {question}

Generate a PostgreSQL SQL query to answer this question. Return ONLY the SQL query:"""

        response = await ai_service.generate_text(prompt, NL2SQL_SYSTEM_PROMPT)

        sql = response.strip()
        # Remove markdown code fences properly (as substrings, not char sets)
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[-1] if "\n" in sql else sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        if not sql.upper().startswith(("SELECT", "WITH")):
            raise ValueError("Generated SQL was not a SELECT query")

        # Block dangerous SQL inside CTEs or subqueries
        # Split off the WITH clause body, check all statements
        if _DANGEROUS_SQL_PATTERNS.search(sql):
            raise ValueError("Generated SQL contains forbidden operations")

        return sql

    async def generate_insight(
        self, question: str, sql: str, results: list[dict]
    ) -> str:
        if not results:
            return "No results found for your query."

        # Truncate results for token safety
        safe_results = []
        for row in results[:20]:
            safe_row = {}
            for k, v in row.items():
                s = str(v)
                safe_row[k] = s[:200] if len(s) > 200 else s
            safe_results.append(safe_row)

        prompt = f"""Question: {question}
SQL Query: {sql}
Results: {safe_results}

Provide a brief, clear insight about these results in 1-2 sentences. Be specific with numbers.
Focus on the most important finding:"""

        return await ai_service.generate_text(prompt)

    async def recommend_chart(self, question: str, columns: list[str], results: list[dict]) -> dict:
        if not results:
            return {"type": "table", "config": {}}

        results_sample = str(results[:10])

        prompt = f"""Question: {question}
Columns: {columns}
Data sample: {results_sample}

Choose the best chart type and determine x-axis and y-axis columns.
Return JSON: {{"type": "bar|line|pie|scatter|table", "x_column": "column_name", "y_column": "column_name", "title": "chart title"}}"""

        try:
            return await ai_service.generate_json(prompt)
        except Exception:
            return self._default_chart(columns, results)

    def _default_chart(self, columns: list[str], results: list[dict]) -> dict:
        if not results or not columns:
            return {"type": "table", "config": {}}

        numeric_cols = []
        text_cols = []
        for col in columns:
            if not results:
                continue
            val = results[0].get(col)
            if isinstance(val, (int, float)):
                numeric_cols.append(col)
            elif val is not None:
                text_cols.append(col)

        if numeric_cols and text_cols:
            return {
                "type": "bar",
                "x_column": text_cols[0],
                "y_column": numeric_cols[0],
                "title": f"{numeric_cols[0]} by {text_cols[0]}",
            }
        elif len(numeric_cols) >= 2:
            return {
                "type": "scatter",
                "x_column": numeric_cols[0],
                "y_column": numeric_cols[1],
                "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
            }
        elif numeric_cols and len(results) > 1 and len(results) <= 6:
            return {
                "type": "pie",
                "x_column": columns[0],
                "y_column": numeric_cols[0],
                "title": f"Distribution of {numeric_cols[0]}",
            }

        return {"type": "table", "config": {}}

    def _format_schema(self, schema_info: dict) -> str:
        lines = []
        for table_name, table_info in schema_info.items():
            lines.append(f"Table: {table_name}")
            for col in table_info.get("columns", []):
                nullable = "NULL" if col.get("nullable") else "NOT NULL"
                lines.append(f"  - {col['name']} ({col.get('pg_type', 'TEXT')}) {nullable}")
            if table_info.get("sample"):
                lines.append(f"  Sample: {table_info['sample'][:2]}")
            lines.append("")
        return "\n".join(lines)


nl2sql_service = NL2SQLService()
