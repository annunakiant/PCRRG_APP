import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Remove any previously broken email blocks
code = re.sub(
    r"# -------------------------------------------------------------[\s\S]*?return send_from_directory",
    "return send_from_directory",
    code
)

# 2. Insert correct placeholder email block BEFORE the return
correct_block = """
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
"""

code = re.sub(
    r"return send_from_directory\(reports_dir, filename, as_attachment=True\)",
    correct_block,
    code,
    count=1
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Fixed job_report_pdf route and inserted safe placeholder email block.")
