import streamlit as st
import json
import random
import pandas as pd
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from datetime import datetime

# ── Page config ─────────────────────────────────────────────

st.set_page_config(
    page_title="GB English Quiz",
    page_icon="🇬🇧",
    layout="centered"
)

# ── Professional Styles ─────────────────────────────────────

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"]  {
font-family: 'Inter', sans-serif;
}

.stApp {
background: linear-gradient(180deg, #0B0F1A 0%, #111827 100%);
color:white;
}

.title {
font-size: 42px;
font-weight: 700;
margin-bottom: 5px;
background: linear-gradient(90deg,#4F46E5,#22C55E);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
}

.subtitle {
color:#9CA3AF;
margin-bottom:20px;
}

.card {
background: rgba(17,24,39,0.7);
backdrop-filter: blur(10px);
border:1px solid rgba(255,255,255,0.05);
padding:30px;
border-radius:18px;
margin-top:20px;
}

.stButton>button {
background: linear-gradient(90deg,#4F46E5,#6366F1);
color:white;
border:none;
border-radius:10px;
padding:12px 20px;
font-weight:600;
transition:0.3s;
}

.stButton>button:hover {
transform: translateY(-2px);
box-shadow:0px 8px 20px rgba(99,102,241,0.4);
}

.stTextInput>div>div>input {
background:#111827;
border:1px solid #374151;
border-radius:10px;
color:white;
}

[data-testid="metric-container"] {
background:#111827;
border:1px solid #1F2937;
padding:15px;
border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# ── Gemini API ──────────────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── Google Sheets ───────────────────────────────────────────

@st.cache_resource
def connect_sheet():

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client = gspread.authorize(creds)
    sheet = client.open("English Quiz Leaderboard").sheet1

    return sheet


def save_score(name, score, total, pct):

    sheet = connect_sheet()

    sheet.append_row([
        name,
        score,
        total,
        pct,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ])


def get_leaderboard():

    sheet = connect_sheet()

    data = sheet.get_all_records()

    return pd.DataFrame(data)

# ── Question Bank ───────────────────────────────────────────

FIXED_BANK = [
{"text":"She ___ to school every day.","options":["go","goes","is go","going"],"correct":1},
{"text":"There ___ milk in the fridge.","options":["are","is","am","be"],"correct":1},
{"text":"How ___ brothers?","options":["much","many","old","big"],"correct":1},
{"text":"I ___ TV now.","options":["watch","watches","am watching","watching"],"correct":2},
{"text":"___ your parents home?","options":["Was","Were","Are","Is"],"correct":1},

{"text":"He ___ soccer.","options":["play","plays","playing","played"],"correct":1},
{"text":"They ___ happy.","options":["is","are","be","am"],"correct":1},
{"text":"I ___ coffee.","options":["like","likes","liked","liking"],"correct":0},
{"text":"She ___ tired.","options":["is","are","be","am"],"correct":0},
{"text":"We ___ late.","options":["is","are","be","am"],"correct":1},

{"text":"I ___ yesterday.","options":["go","went","gone","going"],"correct":1},
{"text":"She ___ English.","options":["study","studies","studied","studying"],"correct":1},
{"text":"They ___ dinner.","options":["eat","ate","eaten","eating"],"correct":1},
{"text":"He ___ tall.","options":["is","are","be","am"],"correct":0},
{"text":"We ___ friends.","options":["is","are","be","am"],"correct":1},

{"text":"I ___ hungry.","options":["is","are","be","am"],"correct":3},
{"text":"She ___ fast.","options":["run","runs","ran","running"],"correct":1},
{"text":"They ___ here.","options":["is","are","be","am"],"correct":1},
{"text":"He ___ pizza.","options":["like","likes","liked","liking"],"correct":1},
{"text":"We ___ early.","options":["arrive","arrives","arrived","arriving"],"correct":0},
]

# ── AI Questions ───────────────────────────────────────────

def generate_ai_questions(n=5):

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Generate {n} A1 English grammar questions.

Return JSON:

[
{{"text":"","options":["","","",""],"correct":0}}
]
"""

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except:
        return []

# ── Build Quiz ─────────────────────────────────────────────

def build_quiz():

    fixed = random.sample(FIXED_BANK,20)
    ai = generate_ai_questions(5)

    pool = fixed + ai
    random.shuffle(pool)

    return pool

# ── Init ───────────────────────────────────────────────────

def init_quiz(name):

    st.session_state.player = name
    st.session_state.questions = build_quiz()
    st.session_state.current = 0
    st.session_state.score = 0
    st.session_state.phase = "quiz"

# ── Landing ────────────────────────────────────────────────

def page_landing():

    st.markdown("<div class='title'>GB English Quiz</div>", unsafe_allow_html=True)

    st.markdown("<div class='subtitle'>25 Questions • Grammar • A1 Level</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)

    name = st.text_input("Your name")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start", use_container_width=True):
            if name:
                init_quiz(name)
                st.rerun()

    with col2:
        if st.button("🏆 Leaderboard", use_container_width=True):
            st.session_state.phase="leaderboard"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ── Quiz ───────────────────────────────────────────────────

def page_quiz():

    qs = st.session_state.questions
    idx = st.session_state.current
    q = qs[idx]

    total = len(qs)

    st.progress((idx+1)/total)

    col1,col2 = st.columns(2)

    with col1:
        st.metric("Score", st.session_state.score)

    with col2:
        st.metric("Remaining", total-idx)

    st.markdown("<div class='card'>", unsafe_allow_html=True)

    st.markdown(f"### {q['text']}")

    for i,opt in enumerate(q["options"]):

        if st.button(opt, use_container_width=True):

            if i == q["correct"]:
                st.session_state.score += 1

            st.session_state.current += 1

            if st.session_state.current >= total:

                pct = round(st.session_state.score/total*100)

                save_score(
                    st.session_state.player,
                    st.session_state.score,
                    total,
                    pct
                )

                st.session_state.phase="results"

            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ── Results ────────────────────────────────────────────────

def page_results():

    score = st.session_state.score
    total = len(st.session_state.questions)
    pct = round(score/total*100)

    st.title("Your Result")

    st.progress(pct/100)
    st.metric("Score", f"{score}/{total}")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("Play Again", use_container_width=True):
            st.session_state.phase="landing"
            st.rerun()

    with col2:
        if st.button("Leaderboard", use_container_width=True):
            st.session_state.phase="leaderboard"
            st.rerun()

# ── Leaderboard ────────────────────────────────────────────

def page_leaderboard():

    st.title("🏆 Leaderboard")

    df = get_leaderboard()

    if not df.empty:
        df = df.sort_values("Percent", ascending=False)
        st.dataframe(df.head(10), use_container_width=True)

    if st.button("Back"):
        st.session_state.phase="landing"
        st.rerun()

# ── Router ────────────────────────────────────────────────

if "phase" not in st.session_state:
    st.session_state.phase="landing"

if st.session_state.phase=="landing":
    page_landing()

elif st.session_state.phase=="quiz":
    page_quiz()

elif st.session_state.phase=="results":
    page_results()

elif st.session_state.phase=="leaderboard":
    page_leaderboard()