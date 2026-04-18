"""Delivery node executor."""

from helm.config import logger


async def execute_deliver_node(node: dict, context: str) -> str:
    """Send context to a configured delivery channel."""
    channel = node.get("deliver_channel", "").lower()
    template = node.get("task", "").strip()
    message = template.replace("{{output}}", context) if template else context

    if channel == "telegram":
        return await _deliver_telegram(node, message)
    if channel == "email":
        return await _deliver_email(node, message)
    if channel == "log":
        logger.info("DELIVER[log]: %s", message[:200])
        return "OK: delivered to log"
    return f"Error: unsupported deliver_channel '{channel}'"


async def _deliver_telegram(node: dict, message: str) -> str:
    try:
        from helm.integrations import get_telegram_bot
        bot = get_telegram_bot()
        if not bot:
            return "Error: Telegram bot not configured"
        chat_id = node.get("deliver_to", "")
        if not chat_id:
            return "Error: deliver_to (chat_id) required for telegram channel"
        for chunk_start in range(0, len(message), 4000):
            await bot.send_message(chat_id=chat_id, text=message[chunk_start:chunk_start + 4000])
        return f"OK: delivered {len(message)} chars to Telegram chat {chat_id}"
    except Exception as exc:
        return f"Error delivering to Telegram: {exc}"


async def _deliver_email(node: dict, message: str) -> str:
    import os
    import smtplib
    from email.mime.text import MIMEText

    to_addr = node.get("deliver_to", "")
    if not to_addr:
        return "Error: deliver_to (email address) required for email channel"
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if not smtp_host or not smtp_user:
        return "Error: SMTP_HOST and SMTP_USER env vars required for email delivery"

    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = node.get("deliver_subject", "Agent Results")
    msg["From"] = smtp_user
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return f"OK: email sent to {to_addr}"
    except Exception as exc:
        return f"Error sending email: {exc}"
