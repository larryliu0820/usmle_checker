# Created by Larry Liu
#
# Date: 5/4/2019
import getpass
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ERROR_EMAIL_SUBJECT = "Automatic Exam Reservation System Has An Error!"
SUCCESS_EMAIL_SUBJECT = "A Space Is Available!"
RETRY_EMAIL_SUBJECT = "Retry login..."


class EmailUtil:

    def __init__(self):
        self.sender_email = input("Sender email: (default mengweiliu600267@gmail.com)") or "mengweiliu600267@gmail.com"
        self.receiver_email = input("Receiver email: (default yannanyu0123@gmail.com)") or "yannanyu0123@gmail.com"
        self.password = getpass.getpass("Type your password for %s and press enter: " % self.sender_email)

    def send_email(self, subject: str, msg: str, html: str = None):
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = self.receiver_email
        part1 = MIMEText(msg, "plain")
        message.attach(part1)
        if html:
            html = '<a href="https://csessauthentication.ecfmg.org/">Click Me</a>' + html
            part2 = MIMEText(html, "html")
            message.attach(part2)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(
                self.sender_email, self.receiver_email, message.as_string()
            )

