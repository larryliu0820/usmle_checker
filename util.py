# Created by Larry Liu
#
# Date: 5/4/2019
import getpass
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv

ERROR_EMAIL_SUBJECT = "Automatic Exam Reservation System Has An Error!"
SUCCESS_EMAIL_SUBJECT = "A Space Is Available!"
RESERVED_EMAIL_SUBJECT = "RESERVE ASAP!!!"
RETRY_EMAIL_SUBJECT = "Retry login..."

logging.basicConfig(filename='checker.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)


class EmailUtil:

    def __init__(self):
        load_dotenv()
        self.sender_email = os.getenv('SENDER_EMAIL') or input("Sender email: ")
        self.receiver_email = os.getenv('RECEIVER_EMAIL') or input("Receiver email: ")
        self.password = os.getenv('SENDER_EMAIL_PASSWORD') or getpass.getpass(
            "Type your password for %s and press enter: " % self.sender_email)

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
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.sender_email, self.password)
                server.sendmail(
                    self.sender_email, self.receiver_email, message.as_string()
                )
        except (ssl.SSLError, smtplib.SMTPAuthenticationError) as e:
            logging.error('Error occurred!', exc_info=True)
            pass


class PhoneCallUtil:

    def __init__(self):
        load_dotenv()
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.to = os.getenv('TO_PHONE_NUM')
        self.from_ = os.getenv('FROM_PHONE_NUM')
        self.client = Client(self.account_sid, self.auth_token)

    def call(self):
        self.client.calls.create(url='http://demo.twilio.com/docs/voice.xml', to=self.to,
                                 from_=self.from_)
