from datetime import datetime
from unittest import mock

from porch_alert.config import EmailConfig
from porch_alert.email_alert import (
    SmtpEmailSender,
    build_mime_message,
    build_subject,
    frame_to_jpeg,
)
from PIL import Image


def test_build_subject_format():
    subject = build_subject("Porch alert", datetime(2026, 5, 29, 14, 32, 1))
    assert subject == "Porch alert: person detected at 2026-05-29 14:32:01"


def test_mime_has_attachment():
    cfg = EmailConfig(to="stephanos@papatsaras.com", from_addr="a@b.com")
    msg = build_mime_message(cfg, "subj", "body", b"jpegdata")
    payload = msg.get_payload()
    assert len(payload) == 2
    assert payload[1].get_filename() == "porch_snapshot.jpg"


def test_dry_run_no_smtp():
    cfg = EmailConfig(to="stephanos@papatsaras.com", smtp_host="smtp.example.com")
    sender = SmtpEmailSender(cfg, dry_run=True)
    with mock.patch("porch_alert.email_alert.smtplib.SMTP") as smtp_cls:
        sender.send_alert("subj", "body", b"jpeg")
        smtp_cls.assert_not_called()


def test_frame_to_jpeg_non_empty():
    img = Image.new("RGB", (32, 24), color=(10, 20, 30))
    data = frame_to_jpeg(img)
    assert data[:2] == b"\xff\xd8"


def test_smtp_send_starttls():
    cfg = EmailConfig(
        to="stephanos@papatsaras.com",
        from_addr="from@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
    )
    sender = SmtpEmailSender(cfg, dry_run=False)
    mock_smtp = mock.MagicMock()
    mock_smtp.__enter__.return_value = mock_smtp
    with mock.patch("porch_alert.email_alert.smtplib.SMTP", return_value=mock_smtp):
        sender.send_alert("subj", "body", b"jpeg")
    mock_smtp.starttls.assert_called_once()
    mock_smtp.sendmail.assert_called_once()
