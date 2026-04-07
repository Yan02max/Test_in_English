import streamlit as st
import json
import random
import pandas as pd
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# ── Config ─────────────────────────────────────────

st.set_page_config(
    page_title="GB English Quiz",
    page_icon="🇬🇧",
    layout="centered"
)

# ── Animated Background + Style ─────────────────────

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"]  {
font-family: 'Inter', sans-serif;
}

.stApp {
background: linear-gradient(-45deg, #0f172a, #020617, #020617, #020617);
background-size: 400% 400%;
animation: gradient 15s ease infinite;
}

@keyframes gradient {
0% {background-position: 0% 50%;}
50% {background-position: 100% 50%;}
100% {background-position: 0% 50%;}
}

.title {
font-size: 42px;
font-weight: 700;
background: linear-gradient(90deg,#6366f1,#22c55e);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
}

.card {
background: rgba(17,24,39,0.7);
backdrop-filter: blur(10px);
padding: 25px;
border-radius: 15px;
border: 1px solid rgba(255,255,255,0.05);
margin-top: 20px;
}

</style>
""", unsafe_allow_html=True)

# ── Sound effects ───────────────────────────────────

correct_sound = """
<audio autoplay>
<source src="https://www.soundjay.com/buttons/sounds/button-3.mp3">
</audio>
"""

wrong_sound = """
<audio autoplay>
<source src="https://www.soundjay.com/buttons/sounds/button-10.mp3">
</audio>
"""

# ── Gemini API ──────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── Google Sheets ───────────────────────────────────

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

    return client.open("English Quiz Leaderboard").sheet1


def save_score(name, score, total, pct):

    connect_sheet().append_row([
        name,
        score,
        total,
        pct,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ])


def get_leaderboard():

    data = connect_sheet().get_all_records()

    return pd.DataFrame(data)

# ── Question Bank ───────────────────────────────────

FIXED_BANK = [

{"text":"She ___ to school every day.","options":["go","goes","is go","going"],"correct":1},
{"text":"I ___ hungry.","options":["is","are","am","be"],"correct":2},
{"text":"They ___ soccer.","options":["play","plays","playing","played"],"correct":0},
{"text":"He ___ tired.","options":["is","are","be","am"],"correct":0},
{"text":"We ___ ready.","options":["is","are","be","am"],"correct":1},

{"text":"I ___ yesterday.","options":["go","went","gone","going"],"correct":1},
{"text":"She ___ English.","options":["study","studies","studied","studying"],"correct":1},
{"text":"They ___ dinner.","options":["eat","ate","eaten","eating"],"correct":1},
{"text":"He ___ tall.","options":["is","are","be","am"],"correct":0},
{"text":"We ___ friends.","options":["is","are","be","am"],"correct":1},

{"text":"She ___ fast.","options":["run","runs","ran","running"],"correct":1},
{"text":"He ___ pizza.","options":["like","likes","liked","liking"],"correct":1},
{"text":"We ___ early.","options":["arrive","arrives","arrived","arriving"],"correct":0},

{"text":"They ___ happy.","options":["is","are","be","am"],"correct":1},
{"text":"I ___ coffee.","options":["like","likes","liked","liking"],"correct":0},

{"text":"He ___ soccer.","options":["play","plays","playing","played"],"correct":1},
{"text":"We ___ late.","options":["is","are","be","am"],"correct":1},
{"text":"She ___ tired.","options":["is","are","be","am"],"correct":0},
{"text":"They ___ here.","options":["is","are","be","am"],"correct":1},
{"text":"I ___ ready.","options":["is","are","am","be"],"correct":2}

]

# ── AI Questions ───────────────────────────────────

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

# ── Build Quiz ─────────────────────────────────────

def build_quiz():

    fixed = random.sample(FIXED_BANK,20)
    ai = generate_ai_questions(5)

    pool = fixed + ai

    random.shuffle(pool)

    return pool

# ── Init ───────────────────────────────────────────

def init_quiz(name):

    st.session_state.player = name
    st.session_state.questions = build_quiz()
    st.session_state.current = 0
    st.session_state.score = 0
    st.session_state.timer = 15
    st.session_state.phase = "quiz"

# ── Landing ────────────────────────────────────────

def page_landing():

    st.markdown("<div class='title'>GB English Quiz</div>", unsafe_allow_html=True)

    st.markdown("25 Questions • Grammar • A1")

    st.markdown("<div class='card'>", unsafe_allow_html=True)

    name = st.text_input("Your name")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("Start", use_container_width=True):
            if name:
                init_quiz(name)
                st.rerun()

    with col2:
        if st.button("Leaderboard", use_container_width=True):
            st.session_state.phase="leaderboard"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ── Quiz ───────────────────────────────────────────

def page_quiz():

    qs = st.session_state.questions
    idx = st.session_state.current
    q = qs[idx]

    total = len(qs)

    st.progress((idx+1)/total)

    st.metric("Score", st.session_state.score)

    # Timer

    timer = st.empty()

    for i in range(15,0,-1):
        timer.metric("Time", i)
        time.sleep(1)

    st.markdown("<div class='card'>", unsafe_allow_html=True)

    st.markdown(f"### {q['text']}")

    for i,opt in enumerate(q["options"]):

        if st.button(opt):

            if i == q["correct"]:
                st.markdown(correct_sound, unsafe_allow_html=True)
                st.session_state.score += 1
            else:
                st.markdown(wrong_sound, unsafe_allow_html=True)

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

# ── Results ─────────────────────────────────────────

def page_results():

    score = st.session_state.score
    total = len(st.session_state.questions)

    pct = round(score/total*100)

    st.title("Your Result")

    st.progress(pct/100)

    st.metric("Score", f"{score}/{total}")

    if st.button("Play Again"):
        st.session_state.phase="landing"
        st.rerun()

# ── Leaderboard ─────────────────────────────────────

def page_leaderboard():

    st.title("🏆 Top 10")

    df = get_leaderboard()

    if not df.empty:

        df = df.sort_values("Percent",ascending=False)

        st.dataframe(df.head(10),use_container_width=True)

    if st.button("Back"):
        st.session_state.phase="landing"
        st.rerun()

# ── Router ─────────────────────────────────────────

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