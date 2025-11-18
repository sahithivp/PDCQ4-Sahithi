from flask import Flask, redirect, url_for, session, request
from flask import render_template_string
import google_auth_oauthlib.flow
import googleapiclient.discovery
from dotenv import load_dotenv
import os
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow http

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

def generate_pattern(n):
    WORD = "FORMULAQSOLUTIONS"
    Length = len(WORD)

    lengths = []
    for i in range(n):
        if i <= n // 2:
            lengths.append(1 + 2 * i)
        else:
            lengths.append(lengths[n - i - 1])

    max_length = max(lengths)
    rows = []

    for row in range(n):
        length = lengths[row]
        start = row % Length

        if row % 2 == 1 and length > 2:  
            full_word = WORD[start] + "-" * (length - 2) + WORD[(start + length - 1) % Length]
        else:  
            full_word = ""
            for k in range(length):
                full_word += WORD[(start + k) % Length]

        spaces = " " * ((max_length - length) // 2)
        rows.append(f"{spaces}{''.join(full_word)}")

    return "<pre>" + "\n".join(rows) + "</pre>"



@app.route("/")
def index():
    if "state" in session:
        return render_template_string("""
            <h2>Welcome! You are logged in.</h2>
            <a href="/logout">
                <button style='padding:8px 14px; background:red; color:white; border:none; border-radius:6px; cursor:pointer;'>
                    Sign Out
                </button>
            </a>
        """)
    else:
        return render_template_string("""
            <h2>Flask Google Login</h2>
            <a href="/login">
            <button style='padding:8px 14px; background:red; color:white; border:none; border-radius:6px; cursor:pointer;'>
                Login with Google
            </button>
            </a>
        """)


@app.route("/login")
def login():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {
            "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [url_for("callback", _external=True)]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = url_for("callback", _external=True)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )

    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    state = session["state"]

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
         {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for("callback", _external=True)]
            }
        }, 
        scopes=SCOPES, 
        state=state
    )
    flow.redirect_uri = url_for("callback", _external=True)

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    oauth2 = googleapiclient.discovery.build(
        "oauth2", "v2", credentials=credentials
    )
    user_info = oauth2.userinfo().get().execute()

    indian_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    return f"""
        <h1>Login Successful!</h1>
        <img src="{user_info['picture']}" width="120">
        <p>Hello {user_info['name']}</p>
        <p>You are signed in with the {user_info['email']}</p>
        <p><b>Current Indian Time:</b> {indian_time}</p>
        <a href="/logout">
            <button style='padding:8px 14px; background:red; color:white; border:none; border-radius:6px; cursor:pointer;'>
                Sign Out
            </button>
        </a>
        <hr>
        <h3>Generate Pattern</h3>
        <form action="/pattern" method="POST">
            <input type="number" name="lines" placeholder="Enter number of lines" required>
            <button type="submit" 
                style="padding:8px 14px; background:green; color:white; border:none; border-radius:6px; cursor:pointer;">
                Generate
            </button>
        </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/pattern", methods=["POST"])
def pattern():
    if "state" not in session:
        return redirect(url_for("index"))

    n = int(request.form["lines"])
    output = generate_pattern(n)
    return f"<pre>{output}</pre><br><a href='/'>Back</a>"


if __name__ == "__main__":
    app.run(debug=True)
