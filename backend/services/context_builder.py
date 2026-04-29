from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models import Account, Project, Transaction, Document, EmailThread, ChatMessage, ProjectConversationSummary
from config import (
    BUDGET_TRANSACTION, BUDGET_PROFILE, BUDGET_DOCUMENTS,
    BUDGET_EMAILS, BUDGET_HISTORY_MESSAGES, ANTHROPIC_MODEL,
)

BASE_PERSONA = """You are reco-pilot, an AI assistant for a Michigan real estate agent. You are an expert in Michigan real estate transactions, purchase agreements, addendums, negotiation strategy, and Michigan-specific requirements (Seller's Disclosure, PRE/tax uncapping, lead paint disclosure for pre-1978 homes). Be professional, precise, and cite specific documents or emails when you reference them.

Treat transaction-specific facts (who ordered what, what appears on title or closing docs, who is responsible for a given item) as established only when the synced documents, emails, transaction notes, or the agent's message in this chat support them; if not, say what is unknown and use conditional phrasing instead of filling gaps with confident assertions. The human agent is the licensed professional with file-specific and office knowledge—if they correct or narrow the situation, defer and revise without pushing back from generalities alone. When next steps are unclear, prefer verification paths (e.g. confirm on the title commitment or final CD once available) or optional checks over imperative vendor calls; if a single detail would change your answer, ask one focused clarifying question rather than assuming."""

# Role-specific strategy (combined with BASE_PERSONA for each client). Keys match Project.client_type.
STRATEGY_DEFAULT_BUYER = """Your focus for this client is the BUY side. Help the agent with buyer negotiations and leverage strategy, purchase agreement drafting and revisions, inspection and financing contingencies, addenda, appraisal and repair negotiations, coordinating title and the lender as reflected in the contract and synced file (who selected title, split arrangements, conditions, CD timing), walk-through issues, and closing readiness. Prioritize protecting the buyer while keeping the deal executable."""

STRATEGY_DEFAULT_SELLER = """Your focus for this client is the SELL side. Help the agent interpret and compare offers (price, concessions, contingencies, timelines), advise on counter strategy, listing and marketing angles, seller disclosures and Michigan forms, inspection response options, and keeping the transaction moving toward a clean closing."""

STRATEGY_DEFAULT_BUYER_SELLER = """This client is active on BOTH buying and selling. Combine buyer-side help (negotiations, PA/addenda, title and lender coordination) with seller-side help (offer comparison, listing/marketing, seller documents). Pay special attention to coordinating closing dates, bridge timing, rent-backs, and contingent-sale addenda where a purchase depends on this (or another) closing."""

DEFAULT_STRATEGY_BY_CLIENT_TYPE: dict[str, str] = {
    "buyer": STRATEGY_DEFAULT_BUYER,
    "seller": STRATEGY_DEFAULT_SELLER,
    "buyer & seller": STRATEGY_DEFAULT_BUYER_SELLER,
}


def default_strategy_prompts_for_api() -> dict[str, str]:
    """Canonical defaults for settings UI (snake_case keys)."""
    return {
        "default_buyer": STRATEGY_DEFAULT_BUYER,
        "default_seller": STRATEGY_DEFAULT_SELLER,
        "default_buyer_seller": STRATEGY_DEFAULT_BUYER_SELLER,
    }


def resolve_strategy_prompt(project: Project, account: Account | None) -> str:
    ct = project.client_type if project.client_type in DEFAULT_STRATEGY_BY_CLIENT_TYPE else "buyer"
    base = DEFAULT_STRATEGY_BY_CLIENT_TYPE[ct]
    if not account:
        return base
    override = {
        "buyer": account.system_prompt_buyer,
        "seller": account.system_prompt_seller,
        "buyer & seller": account.system_prompt_buyer_seller,
    }[ct]
    if override and override.strip():
        return override.strip()
    return base


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


def build_document_index(project: Project) -> str:
    """Filenames and one-liners; used when the user @-attaches or triage returns a subset."""
    docs = sorted(project.documents, key=lambda d: d.created_at, reverse=True)
    if not docs:
        return "No other documents."
    lines: list[str] = []
    for d in docs:
        summ = (d.short_summary or d.filename or "?").replace("\n", " ")[:400]
        lines.append(f"- {d.filename} ({d.source}): {summ}")
    return "Other project documents (index only):\n" + "\n".join(lines)


def build_documents_section_by_ids(
    project: Project, document_ids: list[str], token_budget: int, *, also_index: bool
) -> str:
    if not document_ids and also_index:
        return build_document_index(project)
    id_set = {x for x in document_ids if x}
    if not id_set and also_index:
        return "No document bodies selected. " + build_document_index(project)
    doc_map = {d.id: d for d in project.documents if d.id in id_set}
    if not doc_map and also_index:
        return "No document bodies could be loaded. " + build_document_index(project)

    order = [i for i in document_ids if i in doc_map]
    sections, used = [], 0
    for doc_id in order:
        if used >= token_budget:
            break
        doc = doc_map.get(doc_id)
        if not doc or not doc.chunks:
            continue
        header = f"=== {doc.filename} ({doc.source}) ==="
        text_parts: list[str] = []
        for chunk in doc.chunks:
            if used + (chunk.token_count or 0) > token_budget:
                break
            text_parts.append(chunk.text)
            used += chunk.token_count or len(chunk.text) // 4
        if text_parts:
            sections.append(header + "\n" + "\n".join(text_parts))
    body = "\n\n".join(sections) if sections else "No document bodies in selection."
    if also_index and body:
        return body + "\n\n" + build_document_index(project)
    if also_index:
        return build_document_index(project)
    return body or "No documents in selection."


def build_emails_section_by_ids(project: Project, thread_ids: list[str], token_budget: int) -> str:
    tmap = {t.id: t for t in project.email_threads if t.id in set(thread_ids)}
    order = [i for i in thread_ids if i in tmap]
    if not order:
        return "No email threads in selection."
    sections, used = [], 0
    for tid in order:
        thread = tmap.get(tid)
        if not thread:
            continue
        if used >= token_budget:
            break
        header = f"=== Thread: {thread.subject or '(no subject)'} ==="
        msg_lines = []
        for msg in reversed(thread.messages or ()):
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
    return "\n\n".join(sections) if sections else "No email content in selection."


def get_conversation_summary_text(db: Session, project_id: str) -> str | None:
    row = db.get(ProjectConversationSummary, project_id)
    t = (row.summary_text or "").strip() if row else ""
    if not t:
        return None
    return t


def build_context_system(
    project: Project,
    account: Account | None = None,
    doc_section: str = "",
    email_section: str = "",
    conv_summary: str | None = None,
    property_public_section: str = "",
) -> list[dict[str, Any]]:
    """Assemble system blocks (persona, profile, tx, optional public property, summary, doc, email)."""
    today = datetime.now().strftime("%B %d, %Y")
    strategy = resolve_strategy_prompt(project, account)
    calendar_anchor = (
        f"Today's date: {today}. "
        "Use this as the authoritative calendar anchor for this conversation. "
        "Relative wording in drafts, emails, or pasted text (e.g. \"tomorrow,\" \"tonight,\" weekdays) may be stale or written for another timezone—resolve those phrases against Today's date above, and say so when you are translating relative language to a specific calendar day. "
        "If the agent corrects a date or timing detail, defer to their correction; do not invent a different \"today\" to agree with them. "
        "Prior turns below may be prefixed with [Sent YYYY-MM-DD HH:MM UTC] — that is when each message was stored (server time), not necessarily when the agent typed it; use it to tell yesterday's chat from today's."
    )
    persona_block = (
        BASE_PERSONA
        + "\n\n--- ROLE-SPECIFIC GUIDANCE ---\n"
        + strategy
        + "\n\n"
        + calendar_anchor
    )
    extra: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": persona_block,
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
    ]
    if (property_public_section or "").strip():
        # No cache_control: Anthropic allows at most 4 cached blocks; profile, transactions,
        # documents, and emails keep cache. Public property (incl. /search /comps injects) varies
        # per turn, so it is a plain block.
        extra.append(
            {
                "type": "text",
                "text": "--- PUBLIC PROPERTY DATA (RealEstateAPI — not MLS) ---\n"
                + (property_public_section or "").strip(),
            }
        )
    if (conv_summary or "").strip():
        # No cache_control here: Anthropic caps breakpoints at 4, and this block
        # turns over every SUMMARY_TRIGGER_COUNT messages so it has the weakest
        # cache value among the system chunks.
        extra.append(
            {
                "type": "text",
                "text": "--- EARLIER CONVERSATION (SUMMARY) ---\n" + (conv_summary or "").strip(),
            }
        )
    extra.extend(
        [
            {
                "type": "text",
                "text": "--- DOCUMENTS ---\n" + (doc_section or "No documents."),
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": "--- EMAIL THREADS ---\n" + (email_section or "No synced emails."),
                "cache_control": {"type": "ephemeral"},
            },
        ]
    )
    return extra


def build_system_prompt(project: Project, account: Account | None = None) -> list[dict[str, Any]]:
    """Recency full-pack (no triage) — for tests and legacy call sites."""
    return build_context_system(
        project,
        account,
        build_documents_section(project, BUDGET_DOCUMENTS),
        build_emails_section(project, BUDGET_EMAILS),
        None,
    )


def _chat_content_for_llm(m: ChatMessage) -> str:
    """Include stored time so the model can place prior turns relative to Today's date."""
    ts = m.created_at
    if ts is None:
        return m.content
    # created_at defaults to datetime.utcnow — naive UTC
    stamp = ts.strftime("%Y-%m-%d %H:%M UTC")
    return f"[Sent {stamp}]\n{m.content}"


def load_history(project: Project, db: Session) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter_by(project_id=project.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(BUDGET_HISTORY_MESSAGES)
        .all()
    )
    return [{"role": m.role, "content": _chat_content_for_llm(m)} for m in reversed(messages)]
