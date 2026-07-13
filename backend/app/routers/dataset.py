from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.dataset import Dataset, DatasetColumn
from app.routers.auth import get_current_user
from app.storage.local_storage import storage
from app.services.parser import parser_service
from app.services.embedding import embedding_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: str | None
    filename: str
    file_size: int
    row_count: int
    column_count: int
    table_name: str
    status: str
    created_at: str
    columns: list[dict] = []

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    total: int


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = "",
    description: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_exts = {"csv", "xlsx", "xls"}

    if not file.filename or "." not in file.filename:
        raise HTTPException(status_code=400, detail="File must have a valid extension")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_exts)}")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 50MB")

    await file.seek(0)

    dataset = Dataset(
        user_id=user.id,
        name=name or file.filename.rsplit(".", 1)[0],
        description=description,
        filename=file.filename,
        file_path="",
        file_size=len(content),
        table_name="",
        status="processing",
    )
    db.add(dataset)
    await db.flush()

    file_path = await storage.save_file(file, dataset.id)
    dataset.file_path = file_path

    try:
        result = await parser_service.process_file(file_path, dataset, db)
        schema_info = {
            dataset.table_name: {
                "columns": result["columns"],
            }
        }
        await embedding_service.store_schema(dataset.id, schema_info)
        dataset.status = "ready"
    except Exception:
        dataset.status = "error"
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=400, detail="Error processing file. Check format and try again.")

    await db.flush()
    await db.commit()

    columns = result["columns"]

    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        filename=dataset.filename,
        file_size=dataset.file_size,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        table_name=dataset.table_name,
        status=dataset.status,
        created_at=str(dataset.created_at),
        columns=columns,
    )


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.user_id == user.id).order_by(Dataset.created_at.desc()).options(selectinload(Dataset.columns))
    )
    datasets = result.scalars().all()

    items = []
    for ds in datasets:
        columns = []
        for col in ds.columns:
            columns.append({
                "name": col.name,
                "data_type": col.data_type,
                "sample_values": col.sample_values,
                "ordinal_position": col.ordinal_position,
            })
        items.append(DatasetResponse(
            id=ds.id,
            name=ds.name,
            description=ds.description,
            filename=ds.filename,
            file_size=ds.file_size,
            row_count=ds.row_count,
            column_count=ds.column_count,
            table_name=ds.table_name,
            status=ds.status,
            created_at=str(ds.created_at),
            columns=columns,
        ))

    return DatasetListResponse(datasets=items, total=len(items))


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user.id).options(selectinload(Dataset.columns))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    columns = []
    for col in ds.columns:
        columns.append({
            "name": col.name,
            "data_type": col.data_type,
            "sample_values": col.sample_values,
            "ordinal_position": col.ordinal_position,
        })

    return DatasetResponse(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        filename=ds.filename,
        file_size=ds.file_size,
        row_count=ds.row_count,
        column_count=ds.column_count,
        table_name=ds.table_name,
        status=ds.status,
        created_at=str(ds.created_at),
        columns=columns,
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user.id)
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if ds.table_name:
        try:
            await db.execute(text(f'DROP TABLE IF EXISTS "{ds.table_name}"'))
        except Exception:
            pass

    await db.delete(ds)
    await db.commit()

    try:
        await embedding_service.delete_dataset(dataset_id)
    except Exception:
        pass
    try:
        await storage.delete_dataset_dir(dataset_id)
    except Exception:
        pass

    return {"message": "Dataset deleted"}
