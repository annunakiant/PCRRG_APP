import re

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# ---------------------------------------------------------
# 1. Insert safe_redirect_target() if missing
# ---------------------------------------------------------
if "def safe_redirect_target" not in code:
    insert_point = code.find("# AUTH + DASHBOARD")
    if insert_point != -1:
        helper = """
from urllib.parse import urlparse, urljoin

def safe_redirect_target(target):
    \"\"\"Prevents Android/PWA redirect loops by validating next= URLs.\"\"\"
    if not target:
        return None
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    if redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc:
        return redirect_url.path
    return None

"""
        code = code[:insert_point] + helper + code[insert_point:]

# ---------------------------------------------------------
# 2. Patch login redirect logic safely
# ---------------------------------------------------------
pattern = r"next_url\s*=\s*request\.args\.get\('next'\)\s*or\s*url_for\('dashboard'\)"
replacement = (
    "next_url = request.args.get('next')\n"
    "            next_url = safe_redirect_target(next_url)\n"
    "            protected = ('/jobs', '/admin', '/packout', '/contracts')\n"
    "            if not next_url or next_url.startswith(protected):\n"
    "                next_url = url_for('dashboard')"
)

code = re.sub(pattern, replacement, code)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("✔ Android/PWA login redirect fix applied successfully.")
