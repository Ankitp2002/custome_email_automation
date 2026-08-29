import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union


class EmailService:
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_email: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.use_tls = use_tls
        self.signature = None  # Initialize signature to None
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        if not self.smtp_user or not self.smtp_password:
            raise ValueError("SMTP credentials (user and password) are required.")

    def set_up_default_signature(self, signature_file: str) -> str:
        """Returns the default email signature.
        signature_file: should be HTML file
        """
        with open(signature_file, "r", encoding="utf-8") as f:
            gmail_signature = f.read()
        self.signature = gmail_signature

    def _create_message(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body: str,
    ) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
        msg["Subject"] = subject

        # Append signature if available
        if self.signature:
            sig = self.signature
            full_content = body
            full_content += f"<br><br>{sig}"
            msg.attach(MIMEText(full_content, "html"))

        return msg

    def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body: str,
    ) -> bool:
        """Sends an email with an optional appended signature via SMTP."""
        msg = self._create_message(to_email, subject, body)
        recipients = [to_email] if isinstance(to_email, str) else to_email

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.ehlo()
            if self.use_tls:
                server.starttls()
                server.ehlo()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.sender_email, recipients, msg.as_string())

        return True
