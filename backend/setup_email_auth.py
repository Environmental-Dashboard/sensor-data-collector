"""
Email Authentication Setup
==========================

Interactive local login for the alert mailbox - works like `gh auth login`:
you type the password directly in YOUR terminal (hidden, never echoed,
never leaves this machine except to the SMTP server itself).

What it does:
1. Asks for the mailbox address + password (password input is hidden)
2. Tests the login against the SMTP server for real
3. On success, saves the settings into backend/.env
4. Optionally sends a test email so you can confirm delivery

Run from the backend folder:
    venv\\Scripts\\python.exe setup_email_auth.py
"""

import getpass
import re
import smtplib
import ssl
import sys
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

# Known SMTP hosts (communityhub.cloud mail is hosted on Titan - verified via MX records)
HOSTS = {
    "1": ("smtp.titan.email", 465, "Titan Email (Hostinger business email) - communityhub.cloud uses this"),
    "2": ("smtp.hostinger.com", 465, "Hostinger classic email"),
    "3": ("smtp.gmail.com", 587, "Gmail (requires App Password)"),
}


def prompt_credentials():
    print()
    print("=" * 60)
    print("EMAIL ALERT AUTHENTICATION")
    print("=" * 60)
    print()

    default_user = "eve@communityhub.cloud"
    user = input(f"Mailbox address [{default_user}]: ").strip() or default_user

    print()
    print("SMTP server:")
    for key, (host, port, desc) in HOSTS.items():
        print(f"  {key}. {host}:{port} - {desc}")
    choice = input("Choose [1]: ").strip() or "1"
    host, port, _ = HOSTS.get(choice, HOSTS["1"])

    print()
    print("Password (typing is hidden - paste is OK):")
    password = getpass.getpass("Password: ")
    if not password:
        print("No password entered. Aborting.")
        sys.exit(1)

    return user, password, host, port


def test_login(user: str, password: str, host: str, port: int) -> bool:
    print()
    print(f"Testing login as {user} on {host}:{port} ...")
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20) as server:
                server.login(user, password)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
        print("[OK] Login successful!")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[FAIL] Authentication rejected: {e.smtp_code} {e.smtp_error}")
        print()
        print("  Things to check:")
        print("  - Password is the mailbox password (verify at https://mail.titan.email)")
        print("  - If 2FA is enabled on the mailbox, create an App Password and use that")
        print("  - The mailbox exists and SMTP is enabled for it")
        return False
    except Exception as e:
        print(f"[FAIL] Connection problem: {type(e).__name__}: {e}")
        return False


def quote_env_value(value: str) -> str:
    """Quote a .env value safely for python-dotenv."""
    if "'" not in value:
        return f"'{value}'"  # single quotes = fully literal
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_env(user: str, password: str, host: str, port: int):
    """Update (or append) the SMTP settings in backend/.env, keeping other lines."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []

    settings = {
        "SMTP_HOST": host,
        "SMTP_PORT": str(port),
        "SMTP_USER": user,
        "SMTP_PASSWORD": quote_env_value(password),
        "FROM_EMAIL": user,
        "STATUS_CHANGE_EMAILS": "true",
    }

    seen = set()
    out = []
    for line in lines:
        m = re.match(r"^\s*([A-Z_]+)\s*=", line)
        key = m.group(1) if m else None
        if key in settings:
            out.append(f"{key}={settings[key]}")
            seen.add(key)
        else:
            out.append(line)

    missing = [k for k in settings if k not in seen]
    if missing:
        out.append("")
        out.append("# Email alert settings (written by setup_email_auth.py)")
        for k in missing:
            out.append(f"{k}={settings[k]}")

    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[OK] Settings saved to {ENV_FILE}")
    print("     (this file is gitignored - the password stays on this machine)")


def offer_test_email(user: str, password: str, host: str, port: int):
    print()
    answer = input("Send a test email to dashboard@oberlin.edu now? [y/N]: ").strip().lower()
    if answer != "y":
        return

    # Reuse the real EmailService so the test exercises the actual code path
    sys.path.insert(0, str(Path(__file__).parent))
    import os
    os.environ.update({
        "SMTP_HOST": host,
        "SMTP_PORT": str(port),
        "SMTP_USER": user,
        "SMTP_PASSWORD": password,
        "FROM_EMAIL": user,
    })
    from app.services.email_service import EmailService

    svc = EmailService()
    ok = svc.send_status_change_alert(
        sensor_id="test-setup-script",
        sensor_name="TEST EMAIL (please ignore)",
        sensor_type="purple_air",
        new_status="inactive",
        old_status="active",
        location="Setup test - no device is actually down",
        ip_address="10.17.192.163",
        last_active="just now",
        reason="Test sent by setup_email_auth.py to confirm SMTP settings work.",
    )
    print("[OK] Test email sent - check the inbox!" if ok else "[FAIL] Sending failed - see error above.")


def main():
    user, password, host, port = prompt_credentials()

    while not test_login(user, password, host, port):
        print()
        retry = input("Try a different password? [Y/n]: ").strip().lower()
        if retry == "n":
            print("Aborted - nothing was saved.")
            sys.exit(1)
        password = getpass.getpass("Password: ")

    save_env(user, password, host, port)
    offer_test_email(user, password, host, port)

    print()
    print("Done. Restart the backend to pick up the new settings")
    print("(e.g. re-run run-continuously.ps1 or the SensorDataCollector task).")


if __name__ == "__main__":
    main()
