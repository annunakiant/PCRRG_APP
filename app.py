# app.py - PCRRG SUPER-MEGA Field Operations Platform v2.5 FINAL COMPLETE

import os
import logging
import json
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for,
    request, flash, jsonify, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename

return send_from_directory(UPLOAD_ROOT, filename)


    # -------------------------------------------------------------
    # OPTIONAL EMAIL SEND (disabled until you add an address)
    # -------------------------------------------------------------
    REPORT_EMAIL = ""  # <-- add your email here when ready

    if REPORT_EMAIL:
        from email.message import EmailMessage
        import smtplib

        msg = EmailMessage()
        msg['Subject'] = f"Job Report: {job.job_number} - {job.title}"
        msg['From'] = os.environ.get('SMTP_USER')
        msg['To'] = REPORT_EMAIL
        msg.set_content(f"Attached is the job report for {job.title}.")

        with open(path, 'rb') as f_pdf:
            msg.add_attachment(
                f_pdf.read(),
                maintype='application',
                subtype='pdf',
                filename=filename
            )

        smtp_host = os.environ.get('SMTP_HOST')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')

        if smtp_host and smtp_user and smtp_pass:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

    return send_from_directory(reports_dir, filename, as_attachment=True)

