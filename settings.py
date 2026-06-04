"""
settings.py — Credentials & Connection Settings Page
Warehouse Rental Management Analytics — Data Analytics MGB Project

Handles:
  - Gmail SMTP credentials (entered in dashboard, session-only)
  - UltraMsg WhatsApp API credentials (entered in dashboard, session-only)
  - Connection testing for both channels
  - How-to guide for setting up both services
"""

import streamlit as st
import smtplib
import ssl
import requests
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from notifications import BUSINESS_NAME, BUSINESS_EMAIL


# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE HELPERS
# ════════════════════════════════════════════════════════════════════════════

def init_settings():
    from data_manager import get_business
    biz = get_business()

    import re
    ph = re.sub(r"\D","", biz.get("phone","9571789145"))
    if not ph.startswith("91"): ph = "91" + ph

    defaults = {
        "gmail_user":          biz.get("email",""),
        "gmail_pass":          "",
        "gmail_configured":    False,
        "ultramsg_instance":   "",
        "ultramsg_token":      "",
        "ultramsg_configured": False,
        "sender_phone":        ph,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_gmail_configured() -> bool:
    return bool(
        st.session_state.get("gmail_user") and
        st.session_state.get("gmail_pass") and
        st.session_state.get("gmail_configured")
    )


def is_whatsapp_configured() -> bool:
    return bool(
        st.session_state.get("ultramsg_instance") and
        st.session_state.get("ultramsg_token") and
        st.session_state.get("ultramsg_configured")
    )


def get_channel_status() -> dict:
    return {
        "email":     "✅ Connected" if is_gmail_configured()    else "⚠️ Not configured",
        "whatsapp":  "✅ Connected" if is_whatsapp_configured() else "⚠️ Not configured",
        "email_ok":     is_gmail_configured(),
        "whatsapp_ok":  is_whatsapp_configured(),
    }


# ════════════════════════════════════════════════════════════════════════════
# WHATSAPP SENDER — UltraMsg API
# ════════════════════════════════════════════════════════════════════════════

def send_whatsapp_ultramsg(to_phone: str, message: str) -> dict:
    """
    Send a real WhatsApp message from your number via UltraMsg API.
    to_phone: format '919571789145' (country code + number, no +)
    """
    instance = st.session_state.get("ultramsg_instance", "")
    token    = st.session_state.get("ultramsg_token", "")

    if not instance or not token:
        return {"success": False, "message": "UltraMsg not configured. Go to Settings."}

    # Clean phone number
    import re
    phone_clean = re.sub(r"\D", "", str(to_phone))
    if not phone_clean.startswith("91"):
        phone_clean = "91" + phone_clean

    url = f"https://api.ultramsg.com/{instance}/messages/chat"
    payload = {
        "token":   token,
        "to":      phone_clean,
        "body":    message,
        "priority": 1,
    }

    try:
        response = requests.post(url, data=payload, timeout=15)
        data = response.json()
        if response.status_code == 200 and data.get("sent") == "true":
            return {"success": True, "message": f"WhatsApp sent to +{phone_clean}"}
        else:
            err = data.get("error", data.get("message", "Unknown error"))
            return {"success": False, "message": f"UltraMsg error: {err}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Network error — check internet connection"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Request timed out — try again"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def test_whatsapp_connection(test_phone: str) -> dict:
    """Send a test WhatsApp message to verify connection."""
    msg = (
        f"✅ *WareHub Analytics — Connection Test*\n\n"
        f"Your WhatsApp integration is working correctly!\n"
        f"Automated invoices and reminders will be sent from this number.\n\n"
        f"_{BUSINESS_NAME}_"
    )
    return send_whatsapp_ultramsg(test_phone, msg)


# ════════════════════════════════════════════════════════════════════════════
# EMAIL SENDER — Gmail SMTP
# ════════════════════════════════════════════════════════════════════════════

def send_email_gmail(
    to_email: str,
    subject: str,
    html_body: str,
    cc_email: str = None,
) -> dict:
    """Send HTML email using stored Gmail credentials."""
    sender_email = st.session_state.get("gmail_user", "")
    sender_pass  = st.session_state.get("gmail_pass", "")

    if not sender_email or not sender_pass:
        return {"success": False, "message": "Gmail not configured. Go to Settings."}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{BUSINESS_NAME} <{sender_email}>"
        msg["To"]      = to_email
        if cc_email:
            msg["Cc"] = cc_email
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_pass)
            recipients = [to_email] + ([cc_email] if cc_email else [])
            server.sendmail(sender_email, recipients, msg.as_string())

        return {"success": True, "message": f"Email sent to {to_email}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Gmail authentication failed. Make sure you're using an App Password, not your regular password."
        }
    except smtplib.SMTPException as e:
        return {"success": False, "message": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def test_email_connection(test_email: str) -> dict:
    """Send a test email to verify Gmail connection."""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:30px auto;
                padding:30px;border-radius:12px;border:1px solid #E5E0D8;background:white">
      <h2 style="color:#1A3C5E;margin:0 0 16px">✅ Gmail Connected Successfully</h2>
      <p style="color:#444;font-size:14px">
        Your WareHub Analytics email integration is working.<br>
        Invoices and reminders will be sent from:
        <strong>{st.session_state.get('gmail_user','')}</strong>
      </p>
      <div style="background:#E8F6F0;border-radius:8px;padding:14px;margin-top:16px;
                  font-size:13px;color:#1D8A5F">
        ✓ Gmail SMTP connected<br>
        ✓ HTML invoices ready to send<br>
        ✓ Payment reminders ready to send
      </div>
      <p style="color:#999;font-size:11px;margin-top:16px">{BUSINESS_NAME}</p>
    </div>
    """
    return send_email_gmail(
        test_email,
        "✅ WareHub Analytics — Gmail Test Successful",
        html,
    )


# ════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE RENDERER
# ════════════════════════════════════════════════════════════════════════════

def render_settings_page():
    init_settings()

    st.markdown(
        '<div style="font-family:DM Serif Display,serif;font-size:22px;'
        'color:#0F1923;letter-spacing:-.02em;margin-bottom:4px">'
        '⚙️ Notification Settings</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:13px;color:#64748B;margin-bottom:20px">'
        'Connect your WhatsApp number and Gmail to send real invoices and reminders</div>',
        unsafe_allow_html=True,
    )

    # ── Status bar ──────────────────────────────────────────────────────────
    status = get_channel_status()
    sc1, sc2 = st.columns(2)
    with sc1:
        bg  = "#E8F6F0" if status["whatsapp_ok"] else "#FDF6E3"
        fg  = "#1D8A5F" if status["whatsapp_ok"] else "#D97706"
        brd = "#A8DDD8" if status["whatsapp_ok"] else "#F0DFA0"
        st.markdown(
            f'<div style="background:{bg};border:1px solid {brd};border-radius:10px;'
            f'padding:14px 18px;font-size:13px;color:{fg}">'
            f'📱 <strong>WhatsApp</strong> — {status["whatsapp"]}<br>'
            f'<span style="font-size:11px;opacity:.8">Sender: +{st.session_state.get("sender_phone","—")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with sc2:
        bg  = "#E8F6F0" if status["email_ok"] else "#FDF6E3"
        fg  = "#1D8A5F" if status["email_ok"] else "#D97706"
        brd = "#A8DDD8" if status["email_ok"] else "#F0DFA0"
        st.markdown(
            f'<div style="background:{bg};border:1px solid {brd};border-radius:10px;'
            f'padding:14px 18px;font-size:13px;color:{fg}">'
            f'✉️ <strong>Gmail</strong> — {status["email"]}<br>'
            f'<span style="font-size:11px;opacity:.8">'
            f'{st.session_state.get("gmail_user","Not set")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ────────────────────────────────────────────────────────────────
    tab_wa, tab_email = st.tabs([
        "📱 WhatsApp Setup (UltraMsg)",
        "✉️ Gmail Setup",
    ])

    # ════════════════════════
    # WHATSAPP TAB
    # ════════════════════════
    with tab_wa:

        st.markdown("#### How to Connect Your WhatsApp Number (+91 9571789145)")

        # Step-by-step guide
        st.markdown(
            """
            <div style="background:#EBF2FA;border:1px solid #BDD5EE;border-radius:12px;
                        padding:20px 24px;font-size:13px;color:#1A3C5E;margin-bottom:20px">
            <strong style="font-size:15px">📋 Setup Guide — Takes ~5 minutes, Free trial available</strong>
            <ol style="margin:14px 0 0 16px;line-height:2">
              <li>Go to <a href="https://ultramsg.com" target="_blank" style="color:#E8612C">
                  <strong>ultramsg.com</strong></a> and create a free account</li>
              <li>Click <strong>"Create Instance"</strong> → you'll get an <strong>Instance ID</strong>
                  (looks like <code>instance12345</code>)</li>
              <li>Open your Instance → go to <strong>"QR Code"</strong> tab</li>
              <li>Open WhatsApp on your phone (+91 9571789145) →
                  <strong>Settings → Linked Devices → Link a Device</strong></li>
              <li>Scan the QR code shown on UltraMsg → your number is now connected ✅</li>
              <li>Go to <strong>"Settings"</strong> tab in UltraMsg → copy your <strong>Token</strong></li>
              <li>Paste the Instance ID and Token below 👇</li>
            </ol>
            <div style="margin-top:14px;padding:10px;background:rgba(255,255,255,.6);
                        border-radius:8px;font-size:12px">
              💡 <strong>Free plan:</strong> 300 messages/month — enough for invoices + reminders.<br>
              💡 <strong>Paid plan:</strong> ₹999/month for unlimited — recommended once you go live.<br>
              💡 <strong>Your number stays yours</strong> — you're just connecting it via QR, like WhatsApp Web.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("wa_settings_form"):
            st.markdown("**Enter Your UltraMsg Credentials**")

            wa_instance = st.text_input(
                "Instance ID",
                value=st.session_state.get("ultramsg_instance", ""),
                placeholder="e.g.  instance12345",
                help="Found on your UltraMsg dashboard under 'My Instances'",
            )
            wa_token = st.text_input(
                "Token",
                type="password",
                value=st.session_state.get("ultramsg_token", ""),
                placeholder="Paste your UltraMsg token here",
                help="Found in UltraMsg Instance → Settings → Token",
            )
            sender_ph = st.text_input(
                "Your WhatsApp Number (sender)",
                value=st.session_state.get("sender_phone", "919571789145"),
                help="This is the number you scanned the QR code with. Format: 919571789145",
            )
            test_ph = st.text_input(
                "Test recipient number",
                placeholder="919571789145",
                help="Send a test message to verify connection. Can be your own number.",
            )

            col_save, col_test = st.columns(2)
            with col_save:
                save_wa = st.form_submit_button("💾 Save Credentials", type="primary")
            with col_test:
                test_wa = st.form_submit_button("📤 Save & Send Test Message")

        if save_wa or test_wa:
            if wa_instance and wa_token:
                st.session_state["ultramsg_instance"]   = wa_instance.strip()
                st.session_state["ultramsg_token"]      = wa_token.strip()
                st.session_state["sender_phone"]        = re.sub(r"\D", "", sender_ph)
                st.session_state["ultramsg_configured"] = True
                st.success("✅ WhatsApp credentials saved for this session.")

                if test_wa and test_ph:
                    with st.spinner(f"Sending test WhatsApp to +{test_ph}..."):
                        result = test_whatsapp_connection(test_ph)
                    if result["success"]:
                        st.success(f"✅ {result['message']} — Check your WhatsApp!")
                    else:
                        st.error(f"❌ {result['message']}")
                        st.info(
                            "**Troubleshooting:**\n"
                            "- Make sure you scanned the QR code on UltraMsg with +91 9571789145\n"
                            "- Check Instance ID is correct (no spaces)\n"
                            "- Verify Token is copied completely\n"
                            "- Ensure your phone has internet and WhatsApp is running"
                        )
            else:
                st.error("Please enter both Instance ID and Token.")

        # Alternative: wa.me links (always available)
        st.markdown("---")
        st.markdown(
            """
            <div style="background:#F7F4EF;border:1px solid #E5E0D8;border-radius:10px;
                        padding:14px 18px;font-size:13px;color:#444">
            <strong>Alternative (no setup needed):</strong> The Invoice & Reminders page also has
            <strong>WhatsApp Quick-Send buttons</strong> that open WhatsApp Web with the message
            pre-filled — you just click Send. This works right now without any API setup.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ════════════════════════
    # GMAIL TAB
    # ════════════════════════
    with tab_email:

        st.markdown("#### Connect Your Gmail Account")

        st.markdown(
            """
            <div style="background:#EBF2FA;border:1px solid #BDD5EE;border-radius:12px;
                        padding:20px 24px;font-size:13px;color:#1A3C5E;margin-bottom:20px">
            <strong style="font-size:15px">📋 Setup Guide — Takes ~3 minutes, Completely Free</strong>
            <ol style="margin:14px 0 0 16px;line-height:2.2">
              <li>Go to <a href="https://myaccount.google.com/security" target="_blank"
                  style="color:#E8612C"><strong>myaccount.google.com/security</strong></a></li>
              <li>Make sure <strong>2-Step Verification</strong> is turned ON
                  (required for App Passwords)</li>
              <li>Search for <strong>"App Passwords"</strong> in the search bar at the top</li>
              <li>Click <strong>App Passwords</strong> → enter your Google account password if asked</li>
              <li>In the dropdown: <strong>Select app → Mail</strong> |
                  <strong>Select device → Other (Custom name)</strong> → type "WareHub"</li>
              <li>Click <strong>Generate</strong> → you'll see a <strong>16-character password</strong>
                  (e.g. <code>abcd efgh ijkl mnop</code>)</li>
              <li>Copy that password (spaces are OK) and paste it below 👇</li>
            </ol>
            <div style="margin-top:14px;padding:10px;background:rgba(255,255,255,.6);
                        border-radius:8px;font-size:12px">
              ⚠️ Use your <strong>Gmail address</strong> as the sender email.<br>
              ⚠️ Use the <strong>App Password</strong>, NOT your regular Google password.<br>
              ✅ <strong>100% free</strong> — Gmail allows 500 emails/day on free accounts.<br>
              🔒 Your credentials are <strong>never stored</strong> — saved only in your
              browser session and cleared when you close the tab.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("email_settings_form"):
            st.markdown("**Enter Your Gmail Credentials**")

            g_user = st.text_input(
                "Your Gmail Address",
                value=st.session_state.get("gmail_user", ""),
                placeholder="yourname@gmail.com",
                help="The Gmail account you want to send invoices from",
            )
            g_pass = st.text_input(
                "Gmail App Password",
                type="password",
                value=st.session_state.get("gmail_pass", ""),
                placeholder="16-character App Password (spaces allowed)",
                help="NOT your regular Gmail password — the App Password from Step 6 above",
            )
            test_email_addr = st.text_input(
                "Test recipient email",
                placeholder="your-test@email.com",
                help="An email address to receive a test message. Can be your own.",
            )

            ec1, ec2 = st.columns(2)
            with ec1:
                save_email = st.form_submit_button("💾 Save Credentials", type="primary")
            with ec2:
                test_email_btn = st.form_submit_button("📧 Save & Send Test Email")

        if save_email or test_email_btn:
            if g_user and g_pass:
                st.session_state["gmail_user"]       = g_user.strip()
                st.session_state["gmail_pass"]       = g_pass.strip()
                st.session_state["gmail_configured"] = True
                st.success(
                    f"✅ Gmail credentials saved for this session.\n\n"
                    f"Emails will be sent from: **{g_user}**"
                )

                if test_email_btn and test_email_addr:
                    with st.spinner(f"Sending test email to {test_email_addr}..."):
                        result = test_email_connection(test_email_addr)
                    if result["success"]:
                        st.success(f"✅ {result['message']} — Check your inbox!")
                    else:
                        st.error(f"❌ {result['message']}")
                        st.info(
                            "**Troubleshooting:**\n"
                            "- Make sure you're using an App Password, not your regular Gmail password\n"
                            "- Ensure 2-Step Verification is enabled on your Google account\n"
                            "- Check that Less Secure Apps is not blocking (App Passwords bypass this)\n"
                            "- Try generating a new App Password if this one doesn't work"
                        )
            else:
                st.error("Please enter both Gmail address and App Password.")

        # Security note
        st.markdown("---")
        st.markdown(
            """
            <div style="background:#E8F6F0;border:1px solid #A8DDD8;border-radius:10px;
                        padding:14px 18px;font-size:12px;color:#1D8A5F">
            🔒 <strong>Security:</strong> Your Gmail App Password is stored only in
            <code>st.session_state</code> — it exists in memory only while your browser tab
            is open, is never written to disk, never sent to any server other than Gmail,
            and is cleared automatically when you close the tab or refresh. This is the
            same mechanism used by all professional Streamlit apps.
            </div>
            """,
            unsafe_allow_html=True,
        )


import re
