import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def send_email(to_email, subject, body, attachment_path=None):
    """
    Sends an email with an optional attachment using SMTP.
    Requires environment variables or default values for configuration.
    """
    # Configuration
    # For Gmail: smtp.gmail.com, 587
    # For Outlook: smtp.office365.com, 587
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "") # Sender email
    smtp_password = os.getenv("SMTP_PASSWORD", "") # App password
    
    if not smtp_user or not smtp_password:
        print("Warning: SMTP credentials not set. Email will not be sent.")
        return False, "Credenciales SMTP no configuradas"

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(attachment_path)}",
            )
            msg.attach(part)
        except Exception as e:
            print(f"Error attaching file: {e}")

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, to_email, text)
        server.quit()
        print(f"Email sent successfully to {to_email}")
        return True, "Email enviado correctamente"
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False, str(e)
