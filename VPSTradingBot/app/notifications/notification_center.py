import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

class NotificationCenter:
    """
    Central hub for sending notifications (Email, etc.)
    """
    def __init__(self, smtp_server="smtp.example.com", smtp_port=587, username="", password=""):
        self._log = logging.getLogger("NotificationCenter")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.enabled = False # Disabled by default until config provided

    def send_email(self, to_email: str, subject: str, body: str, html: bool = False) -> bool:
        """
        Sends an email notification.
        """
        if not self.enabled:
            self._log.info("Email notification skipped (disabled): %s", subject)
            return True # Pretend success

        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject

        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        try:
            # Stub implementation - uncomment to enable real sending
            # server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            # server.starttls()
            # server.login(self.username, self.password)
            # server.send_message(msg)
            # server.quit()
            self._log.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as e:
            self._log.error("Failed to send email: %s", e)
            return False

    def send_daily_summary(self, to_email: str, summary_text: str):
        self.send_email(to_email, "Daily Trading Summary", summary_text)
