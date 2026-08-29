import logging
from celery import shared_task
from app.infrastructure.mailer.email_service import EmailUtils

logger = logging.getLogger("QCMS.EmailTasks")


@shared_task(
    bind=True,
    name="app.infrastructure.tasks.email_tasks.send_async_email",
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,)
)
def send_async_email(self, recipient: str, subject: str, html_body: str, sender_name: str = None, org_id: int = None):
    """Sends a transactional email with automated Celery retries on provider hiccups."""
    if not recipient or str(recipient).strip().lower() in ('none', 'null', ''):
        return {"status": "skipped", "reason": "invalid_recipient"}
    try:
        res = EmailUtils.send_email(
            to_email=recipient,
            subject=subject,
            html_content=html_body,
            sender_name=sender_name,
            org_id=org_id
        )
        if not res:
            logger.warning(f"[Celery Email] Failed or empty response sending email to {recipient}")
            raise RuntimeError("Email sending failed or returned empty response")
        logger.info(f"[Celery Email] Successfully sent email to {recipient}")
        return {"status": "sent", "recipient": recipient}
    except Exception as exc:
        logger.error(f"[Celery Email] Retry {self.request.retries}/3 for {recipient}: {exc}")
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))


@shared_task(bind=True, name="app.infrastructure.tasks.email_tasks.send_batch_announcements")
def send_batch_announcements(self, org_id: int, subject: str, html_content: str, user_emails: list):
    """Dispatches mass announcement emails in batched chunks."""
    logger.info(f"[Celery Batch Email] Broadcasting to {len(user_emails)} users in org {org_id}")
    sent_count = 0
    
    for email in user_emails:
        try:
            ok = EmailUtils.send_email(to_email=email, subject=subject, html_content=html_content, org_id=org_id)
            if ok:
                sent_count += 1
        except Exception as e:
            logger.warning(f"[Celery Batch Email] Failed for {email}: {e}")

    return {"status": "completed", "total": len(user_emails), "sent": sent_count}

