from flask import Flask, redirect, url_for, session, request, render_template
from flask import render_template_string
import google_auth_oauthlib.flow
import googleapiclient.discovery
from dotenv import load_dotenv
import os
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)

# Secret key for the flask app for secure session management to store the state and user info
app.secret_key = os.getenv("FLASK_SECRET_KEY")  

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow http for local development

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    # Defines permissions your app requests from the user
    "openid",  # Basic authentication 
    "https://www.googleapis.com/auth/userinfo.email",     # User email and profile info
    "https://www.googleapis.com/auth/userinfo.profile"
]

def generate_pattern(n):
    # Function to generate pattern based on the input n
    WORD = "FORMULAQSOLUTIONS" # Main word used to make the pattern
    Length = len(WORD) 
    
    if n % 2 == 0:  
        n += 1  

    lengths = []
    for i in range(n):      # Computing number of charcters in each row
        if i <= n // 2:
            lengths.append(1 + 2 * i)
        else:
            lengths.append(lengths[n - i - 1])

    max_length = max(lengths)   # Longest row length
    rows = []      # Storing each row of the pattern

    for row in range(n):
        length = lengths[row]
        start = row % Length

        if row % 2 == 1 and length > 2:  # Checks for odd numbered rows starting from 0, to insert hyphens in between
            full_word = WORD[start] + "-" * (length - 2) + WORD[(start + length - 1) % Length]
        else:  
            full_word = ""
            for k in range(length):     # Take consecutive characters from WORD starting from 'start' index
                full_word += WORD[(start + k) % Length]

        spaces = "" * ((max_length - length) // 2)    # Adding spaces to align the rows
        rows.append(f"{spaces}{' '.join(full_word)}")
 
    return "<pre>" + "\n".join(rows) + "</pre>"     # Joins all rows together and <pre> used to render it in HTML as it is



@app.route("/")
def index():
    if "state" in session:
        return redirect(url_for("home"))     # Checks if user is logged in or has an active session
    return render_template("login.html")     # Rendering HTML template for the UI for login page

@app.route("/home")
def home():
    if "state" not in session:
        return redirect(url_for("index"))

    user_info = session.get("user_info")
    indian_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
    return render_template("home.html", user_info=user_info, indian_time=indian_time)


@app.route("/login")
def login():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        # OAuth Flow object
        {
            "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [url_for("callback", _external=True)]    # _external=True - to make sure in redirection the whole url is called including the domain
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = url_for("callback", _external=True)

    authorization_url, state = flow.authorization_url(
        access_type="offline",     # Allows refresh tokens for long time access
        include_granted_scopes="true",
        prompt="select_account"    # To force the user to select an account every  time so that a browser can help to login to multiple accounts
    )

    session["state"] = state  # State of the flask session
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    state = session["state"]
    if not state:
        return redirect(url_for("index"))

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        # Recreates the object to safely exchange authorization code for tokens
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

    flow.fetch_token(authorization_response=request.url)   # Fetches access token and refresh token from google

    credentials = flow.credentials

    oauth2 = googleapiclient.discovery.build(
        "oauth2", "v2", credentials=credentials
    )
    user_info = oauth2.userinfo().get().execute()
    session["state"] = state
    session["user_info"] = user_info

    indian_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        "home.html",
        user_info=user_info,
        indian_time=indian_time,
        output=None  
    )

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

    user_info = session.get("user_info")
    indian_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
    return render_template("home.html", user_info=user_info, indian_time=indian_time, output=output)


if __name__ == "__main__":
    app.run(debug=True)
