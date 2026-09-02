import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send(to_email: str, subject: str, body: str):
    logging.info("Sending mail")
    msg = MIMEMultipart()
    msg['From'] = Config.SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as E:
        logging.error(f"Error on send mail {E}")
    else:
        logging.info("Mail sended")
