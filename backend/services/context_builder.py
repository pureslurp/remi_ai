from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models import Project, Transaction, Document, EmailThread, ChatMessage
from config import (
    BUDGET_TRANSACTION, BUDGET_PROFILE, BUDGET_DOCUMENTS,
    BUDGET_EMAILS, BUDGET_HISTORY_MESSAGES, ANTHROPIC_MODEL,
)

BASE_PERSONA = """You are REMI, an AI assistant for a Michigan real estate agent. You are an expert in Michigan real estate transactions, purchase agreements, addendums, negotiation strategy, and Michigan-specific requirements (Seller's Disclosure, PRE/tax uncapping, lead paint disclosure for pre-1978 homes). Be professional, precise, and cite specific documents or emails when you reference them."""


def _fmt_money(v):
    return f"${v:,.0f}" if v else "N/A"


def _fmt_date(d):
    if not d:
        return "N/A"
    return d.strftime("%b %d, %Y")


def _days_until(d):
    if not d:
        return None
    now = datetime.utcnow()
    return (d - now).days


def build_transaction_section(project: Project) -> str:
    txs = [t for t in project.transactions if t.status not in ("closed", "dead")]
    if not txs:
        return "No active transactions."

    lines = []
    for tx in txs:
        prop = tx.property
        addr = prop.address if prop else "No property linked"
        lines.append(f"TRANSACTION: {addr}")
        lines.append(f"  Offer: {_fmt_money(tx.offer_price)}  |  Earnest: {_fmt_money(tx.earnest_money)}")
        lines.append(f"  Status: {tx.status.upper()}")
        lines.append(f"  Offer date: {_fmt_date(tx.offer_date)}  |  Accepted: {_fmt_date(tx.accepted_date)}")
        lines.append(f"  Close date: {_fmt_date(tx.close_date)}")
        if tx.contingencies:
            lines.append(f"  Contingencies: {', '.join(tx.contingencies)}")
        if tx.key_dates:
            lines.append("  KEY DATES:")
            for kd in sorted(tx.key_dates, key=lambda k: k.due_date):
                days = _days_until(kd.due_date)
                done = " ✓" if kd.completed_at else ""
                urgency = " ⚠ URGENT" if days is not None and 0 <= days <= 3 and not kd.completed_at else ""
                lines.append(f"    - {kd.label}: {_fmt_date(kd.due_date)}{done}{urgency}")
        if tx.notes:
            lines.append(f"  Notes: {tx.notes}")
        lines.append("")
    return "\n".join(lines)


def build_client_profile(project: Project) -> str:
    emails = ", ".join(project.email_addresses) if project.email_addresses else "None"
    lines = [
        f"CLIENT: {project.name}",
        f"Type: {project.client_type.upper()}",  # buyer | seller | buyer & seller
        f"Email(s): {emails}",
        f"Phone: {project.phone or 'N/A'}",
    ]
    if project.notes:
        lines.append(f"Agent Notes:\n{project.notes}")
    return "\n".join(lines)


def build_documents_section(project: Project, token_budget: int) -> str:
    docs = sorted(project.documents, key=lambda d: d.created_at, reverse=True)
    if not docs:
        return "No documents."

    sections, used = [], 0
    for doc in docs:
        if used >= token_budget:
            break
        if not doc.chunks:
            continue
        header = f"=== {doc.filename} ({doc.source}) ==="
        text_parts = []
        for chunk in doc.chunks:
            if used + (chunk.token_count or 0) > token_budget:
                break
            text_parts.append(chunk.text)
            used += chunk.token_count or len(chunk.text) // 4
        if text_parts:
            sections.append(header + "\n" + "\n".join(text_parts))

    return "\n\n".join(sections) if sections else "No documents with extracted text."


def build_emails_section(project: Project, token_budget: int) -> str:
    threads = sorted(
        project.email_threads,
        key=lambda t: t.last_message_date or datetime.min,
        reverse=True,
    )
    if not threads:
        return "No synced emails."

    sections, used = [], 0
    for thread in threads:
        if used >= token_budget:
            break
        header = f"=== Thread: {thread.subject or '(no subject)'} ==="
        msg_lines = []
        for msg in reversed(thread.messages):
            line = (
                f"[{_fmt_date(msg.date)}] From: {msg.from_addr or '?'}\n"
                f"{msg.body_text or msg.snippet or ''}"
            )
            tokens = len(line) // 4
            if used + tokens > token_budget:
                break
            msg_lines.append(line)
            used += tokens
        if msg_lines:
            sections.append(header + "\n" + "\n---\n".join(msg_lines))

    return "\n\n".join(sections) if sections else "No email content available."


def build_system_prompt(project: Project) -> list[dict]:
    """Return a list of system content blocks with cache_control on stable sections."""
    today = datetime.now().strftime("%B %d, %Y")

    return [
        {
            "type": "text",
            "text": BASE_PERSONA + f"\n\nToday's date: {today}.",
        },
        {
            "type": "text",
            "text": "--- CLIENT PROFILE ---\n" + build_client_profile(project),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "--- ACTIVE TRANSACTIONS ---\n" + build_transaction_section(project),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "--- DOCUMENTS ---\n" + build_documents_section(project, BUDGET_DOCUMENTS),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "--- EMAIL THREADS ---\n" + build_emails_section(project, BUDGET_EMAILS),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def load_history(project: Project, db: Session) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter_by(project_id=project.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(BUDGET_HISTORY_MESSAGES)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]
