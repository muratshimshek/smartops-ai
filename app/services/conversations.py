from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message, utc_now


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self) -> Conversation:
        conversation = Conversation()
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get(self, conversation_id: UUID) -> Conversation | None:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == str(conversation_id))
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def add_message(self, conversation: Conversation, role: str, content: str) -> Message:
        timestamp = utc_now()
        message = Message(conversation_id=conversation.id, role=role, content=content, timestamp=timestamp)
        conversation.updated_at = timestamp
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.commit()

