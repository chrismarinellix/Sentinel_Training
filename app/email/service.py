import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

settings = get_settings()


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email using SMTP."""
    reset_url = f"{settings.base_url}/reset-password?token={reset_token}"

    # Create message
    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = "Password Reset Request - Vysus Training Platform"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #005454, #00E3A9);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: #00E3A9;
                color: #005454;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Vysus Training Platform</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password for the Vysus Training Platform.</p>
            <p>Click the button below to reset your password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <p>If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        </div>
        <div class="footer">
            <p>Vysus Group - Grid Connection Engineering Training</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text fallback
    text_content = f"""
    Vysus Training Platform - Password Reset Request

    You have requested to reset your password.

    Click the link below to reset your password:
    {reset_url}

    This link will expire in 1 hour.

    If you didn't request this password reset, you can safely ignore this email.

    - Vysus Training Team
    """

    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    # Send email
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
    )
