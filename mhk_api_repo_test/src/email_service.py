from pathlib import Path
from email.message import EmailMessage
import smtplib
import os

from dotenv import load_dotenv


class EmailService:
    def __init__(self):
        load_dotenv()

        self._email_address = os.getenv("O365_EMAIL")
        self._email_password = os.getenv("O365_PASSWORD")

        if not self._email_address or not self._email_password:
            raise ValueError(
                "O365_EMAIL and O365_PASSWORD must be configured in .env"
            )

        self._receiver = None
        self._subject = None
        self._body = None
        self._attachment = None

    # ---------------------------
    # Setters
    # ---------------------------

    def set_receiver(self, receiver: str):
        self._receiver = receiver
        return self

    def set_subject(self, subject: str):
        self._subject = subject
        return self

    def set_body(self, body: str):
        self._body = body
        return self

    def set_attachment(self, attachment: str | Path):
        self._attachment = Path(attachment) if attachment else None
        return self

    # ---------------------------
    # Compose
    # ---------------------------

    def compose(
        self,
        receiver: str = None,
        subject: str = None,
        body: str = None,
        attachment: str | Path = None,
    ):
        """
        Compose email using parameters
        or previously set values.
        """

        if receiver:
            self._receiver = receiver

        if subject:
            self._subject = subject

        if body:
            self._body = body

        if attachment:
            self._attachment = Path(attachment)

        msg = EmailMessage()

        msg["From"] = self._email_address
        msg["To"] = self._receiver
        msg["Subject"] = self._subject

        msg.set_content(self._body)

        if self._attachment:
            with open(self._attachment, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=self._attachment.name,
                )

        return msg

    # ---------------------------
    # Send
    # ---------------------------

    def send(self, message: EmailMessage = None):
        """
        Send supplied message.
        If no message is supplied,
        compose using existing state.
        """

        if message is None:
            message = self.compose()

        with smtplib.SMTP("smtp.office365.com", 587) as smtp:
            smtp.starttls()
            smtp.login(
                self._email_address,
                self._email_password
            )
            smtp.send_message(message)

        print("Email sent successfully.")