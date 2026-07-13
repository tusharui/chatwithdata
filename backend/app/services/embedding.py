import os
import json
from app.config import get_settings

settings = get_settings()

SCHEMA_DIR = os.path.join(settings.UPLOAD_DIR, "_schemas")
os.makedirs(SCHEMA_DIR, exist_ok=True)


class EmbeddingService:
    async def store_schema(self, dataset_id: str, schema_info: dict):
        path = os.path.join(SCHEMA_DIR, f"{dataset_id}.json")
        with open(path, "w") as f:
            json.dump(schema_info, f, default=str)

    async def query_context(self, dataset_id: str, question: str, n_results: int = 5) -> str:
        path = os.path.join(SCHEMA_DIR, f"{dataset_id}.json")
        if not os.path.exists(path):
            return ""

        with open(path) as f:
            schema_info = json.load(f)

        docs = []
        for table_name, table_info in schema_info.items():
            for col in table_info.get("columns", []):
                doc = (
                    f"Table: {table_name}, Column: {col['name']}, "
                    f"Type: {col.get('pg_type', 'TEXT')}, "
                    f"Samples: {col.get('sample', [])}"
                )
                docs.append(doc)

        question_lower = question.lower()
        scored = []
        for doc in docs:
            score = sum(1 for word in question_lower.split() if word in doc.lower())
            scored.append((score, doc))

        scored.sort(key=lambda x: -x[0])
        return "\n".join(doc for _, doc in scored[:n_results])

    async def delete_dataset(self, dataset_id: str):
        path = os.path.join(SCHEMA_DIR, f"{dataset_id}.json")
        if os.path.exists(path):
            os.remove(path)


embedding_service = EmbeddingService()
