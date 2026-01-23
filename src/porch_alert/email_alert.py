from __future__ import annotations

import io
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from PIL import Image

from porch_alert.config import EmailConfig

logger = logging.getLogger(__name__)


def apply_porch_roi(
    image: Image.Image, roi: tuple[float, float, float, float] | None
) -> Image.Image:
    if roi is None:
        return image
    width, height = image.size
    x1, y1, x2, y2 = roi
    box = (int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height))
    return image.crop(box)


def frame_to_jpeg(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def build_subject(prefix: str, detected_at: datetime) -> str:
    stamp = detected_at.strftime("%Y-%m-%d %H:%M:%S")
    return f"{prefix}: person detected at {stamp}"


def build_body(detections_summary: str, detected_at: datetime) -> str:
    stamp = detected_at.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Porch motion alert at {stamp}.\n\n"
        f"Detection summary:\n{detections_summary}\n"
    )


def build_mime_message(
    email_cfg: EmailConfig,
    subject: str,
    body: str,
    jpeg_bytes: bytes,
    attachment_name: str = "porch_snapshot.jpg",
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = email_cfg.from_addr
    msg["To"] = email_cfg.to

    text_part = MIMEText(body, "plain", "utf-8")
    msg.attach(text_part)

    attachment = MIMEApplication(jpeg_bytes, _subtype="jpeg")
    attachment.add_header(
        "Content-Disposition", "attachment", filename=attachment_name
    )
    msg.attach(attachment)
    return msg


def format_detection_summary(targets: list) -> str:
    if not targets:
        return "  (none)"
    lines = [f"  - {d.label}: {d.score:.2f}" for d in targets]
    return "\n".join(lines)


class SmtpEmailSender:
    def __init__(self, email_cfg: EmailConfig, dry_run: bool) -> None:
        self._email = email_cfg
        self._dry_run = dry_run

    def send_alert(
        self,
        subject: str,
        body: str,
        jpeg_bytes: bytes,
        attachment_name: str = "porch_snapshot.jpg",
    ) -> None:
        if self._dry_run:
            logger.info(
                "DRY RUN: would email %s with attachment %s (%d bytes) subject=%r",
                self._email.to,
                attachment_name,
                len(jpeg_bytes),
                subject,
            )
            return

        if not self._email.smtp_host:
            raise RuntimeError("SMTP host not configured (set PORCH_ALERT_SMTP_HOST)")

        msg = build_mime_message(
            self._email, subject, body, jpeg_bytes, attachment_name
        )

        if self._email.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                self._email.smtp_host, self._email.smtp_port, context=context
            ) as smtp:
                if self._email.smtp_user:
                    smtp.login(self._email.smtp_user, self._email.smtp_password)
                smtp.sendmail(
                    self._email.from_addr, [self._email.to], msg.as_string()
                )
        else:
            with smtplib.SMTP(self._email.smtp_host, self._email.smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                if self._email.smtp_user:
                    smtp.login(self._email.smtp_user, self._email.smtp_password)
                smtp.sendmail(
                    self._email.from_addr, [self._email.to], msg.as_string()
                )

        logger.info("email sent to %s subject=%r", self._email.to, subject)
