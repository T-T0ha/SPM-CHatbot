from sqlalchemy.orm import Session
from sqlalchemy import func
from database import Conversation, ConversationSession
from llm import call_ollama

WINDOW_SIZE = 10
SUMMARY_THRESHOLD = 20
SUMMARY_REFRESH_GAP = 3
SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant. "
    "Answer questions clearly and concisely. "
    "If you don't know something, say so honestly."
)


def build_context(
    db: Session,
    session_id: int,
    new_user_message: str,
) -> list[dict]:
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == session_id)
        .first()
    )
    if not session:
        return []

    maybe_update_summary(db, session)

    window_messages = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.timestamp.desc())
        .limit(WINDOW_SIZE)
        .all()
    )
    window_messages.reverse()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if session.summary:
        messages.append({
            "role": "assistant",
            "content": f"Here is a summary of our earlier conversation: {session.summary}",
        })

    for msg in window_messages:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": new_user_message})

    return messages


def maybe_update_summary(db: Session, session: ConversationSession) -> None:
    total_msgs = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.session_id == session.id)
        .scalar()
    )

    if total_msgs <= SUMMARY_THRESHOLD:
        return

    outside_window = total_msgs - WINDOW_SIZE
    already_summarised = session.summary_msg_count or 0

    if (outside_window - already_summarised) < SUMMARY_REFRESH_GAP:
        return

    old_messages = (
        db.query(Conversation)
        .filter(Conversation.session_id == session.id)
        .order_by(Conversation.timestamp)
        .limit(outside_window)
        .all()
    )

    transcript_lines = []
    for msg in old_messages:
        label = "User" if msg.role == "user" else "Assistant"
        transcript_lines.append(f"{label}: {msg.content}")
    transcript = "\n".join(transcript_lines)

    summary = call_ollama([
        {
            "role": "system",
            "content": (
                "Summarise the following conversation in 3-5 sentences. "
                "Capture the key topics, questions, and answers. "
                "Write in third person past tense."
            ),
        },
        {"role": "user", "content": transcript},
    ])

    session.summary = summary
    session.summary_msg_count = outside_window
    db.commit()
