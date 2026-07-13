import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.dataset import Dataset, DatasetColumn
from app.models.conversation import Conversation, Message
from app.routers.auth import get_current_user
from app.services.nl2sql import nl2sql_service
from app.services.chart import chart_service, make_json_safe

router = APIRouter(prefix="/api/chat", tags=["chat"])

_MAX_QUERY_ROWS = 1000


class ChatRequest(BaseModel):
    dataset_id: str
    message: str
    conversation_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    chart_type: str | None = None
    chart_data: dict | None = None
    table_data: dict | None = None
    sql_query: str | None = None
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    messages: list[MessageResponse] = []
    created_at: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


def _sanitize_error_message(error: Exception) -> str:
    msg = str(error)
    # Strip connection strings, file paths, and internal details
    if "password" in msg.lower() or "connect" in msg.lower():
        return "Database connection error. Please try again."
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


@router.post("/", response_model=MessageResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Find dataset
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == request.dataset_id,
            Dataset.user_id == user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.status != "ready":
        raise HTTPException(status_code=400, detail="Dataset is still processing")

    # Step 2: Find or create conversation
    conv_id = request.conversation_id
    if conv_id:
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            user_id=user.id,
            dataset_id=dataset.id,
            title=request.message.strip()[:50] or "New conversation",
        )
        db.add(conversation)
        await db.flush()
        conv_id = conversation.id

    # Step 3: Save user message
    user_msg = Message(
        conversation_id=conv_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # Step 4: Get schema info
    async with AsyncSessionLocal() as schema_db:
        col_result = await schema_db.execute(
            select(DatasetColumn).where(DatasetColumn.dataset_id == dataset.id)
        )
        columns = col_result.scalars().all()

    schema_info = {
        dataset.table_name: {
            "columns": [
                {
                    "name": c.name,
                    "pg_type": c.data_type,
                    "nullable": c.is_nullable,
                    "sample": c.sample_values,
                }
                for c in columns
            ]
        }
    }
    col_names = [c.name for c in columns]

    # Step 5: Generate SQL, execute, and generate insight
    sql_text = None
    try:
        sql_text = await nl2sql_service.generate_sql(request.message, schema_info)

        # Enforce row limit by appending LIMIT if not present
        upper_sql = sql_text.upper().strip()
        if "LIMIT" not in upper_sql:
            sql_text = sql_text.rstrip(";") + f" LIMIT {_MAX_QUERY_ROWS}"

        async with AsyncSessionLocal() as query_db:
            query_result = await query_db.execute(text(sql_text))
            rows = query_result.mappings().all()
            results = [dict(row) for row in rows]

        chart_info = await nl2sql_service.recommend_chart(
            request.message, col_names, results
        )
        chart_data = chart_service.format_chart_data(chart_info, results)

        insight = await nl2sql_service.generate_insight(request.message, sql_text, results)

        ai_content = insight
        ai_chart_type = chart_info.get("type", "table")
        ai_chart_data = chart_data
        ai_table_data = make_json_safe({"rows": results[:50], "total_rows": len(results)})

    except Exception as e:
        ai_content = f"I encountered an error processing your request: {_sanitize_error_message(e)}"
        ai_chart_type = None
        ai_chart_data = None
        ai_table_data = None

    # Step 6: Save AI response in a fresh session
    async with AsyncSessionLocal() as save_db:
        ai_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=ai_content,
            chart_type=ai_chart_type,
            chart_data=ai_chart_data,
            table_data=ai_table_data,
            sql_query=sql_text,
        )
        save_db.add(ai_msg)
        await save_db.commit()
        await save_db.refresh(ai_msg)

    return MessageResponse(
        id=ai_msg.id,
        conversation_id=conv_id,
        role="assistant",
        content=ai_content,
        chart_type=ai_chart_type,
        chart_data=ai_chart_data,
        table_data=ai_table_data,
        sql_query=sql_text,
        created_at=str(ai_msg.created_at),
    )


@router.get("/conversations/{dataset_id}", response_model=ConversationListResponse)
async def list_conversations(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Eagerly load messages to avoid N+1 queries
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user.id,
            Conversation.dataset_id == dataset_id,
        ).order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()

    if not conversations:
        return ConversationListResponse(conversations=[])

    conv_ids = [c.id for c in conversations]
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id.in_(conv_ids)).order_by(Message.created_at)
    )
    all_messages = msg_result.scalars().all()

    # Group messages by conversation_id
    messages_by_conv: dict[str, list[Message]] = {}
    for m in all_messages:
        messages_by_conv.setdefault(m.conversation_id, []).append(m)

    items = []
    for conv in conversations:
        conv_messages = messages_by_conv.get(conv.id, [])
        items.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            messages=[
                MessageResponse(
                    id=m.id,
                    conversation_id=conv.id,
                    role=m.role,
                    content=m.content,
                    chart_type=m.chart_type,
                    chart_data=m.chart_data,
                    table_data=m.table_data,
                    sql_query=m.sql_query,
                    created_at=str(m.created_at),
                )
                for m in conv_messages
            ],
            created_at=str(conv.created_at),
        ))

    return ConversationListResponse(conversations=items)


@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=conv.id,
                role=m.role,
                content=m.content,
                chart_type=m.chart_type,
                chart_data=m.chart_data,
                table_data=m.table_data,
                sql_query=m.sql_query,
                created_at=str(m.created_at),
            )
            for m in messages
        ],
        created_at=str(conv.created_at),
    )
