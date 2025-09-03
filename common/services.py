import resend
import os
from django.conf import settings
from django.template.loader import render_to_string

resend.api_key = os.environ.get('RESEND_API_KEY')

def send_account_creation_email(user, password):
    try:
        html_content = render_to_string('mail_template.html', {
            'user': user,
            'password': password
        })

        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [user.email],
            "subject": "Welcome to BioAttend - Your Account Details",
            "html": html_content,
        }

        email = resend.Emails.send(params)
        print(f"Email sent successfully: {email}")
        return email
    except Exception as e:
        print(f"Error sending email: {e}")
        return None
