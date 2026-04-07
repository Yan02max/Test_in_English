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
    page_icon="📘",
    layout="centered"
)

# ── Styles + Animations ─────────────────────────────

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body {
font-family: 'Inter', sans-serif;
}

.stApp {
background: linear-gradient(-45deg, #020617, #020617, #0f172a, #020617);
background-size: 400% 400%;
animation: gradient 12s ease infinite;
}

@keyframes gradient {
0% {background-position:0% 50%;}
50% {background-position:100% 50%;}
100% {background-position:0% 50%;}
}

/* Book animation */

.book {
width:120px;
height:90px;
background:#6366f1;
border-radius:6px;
margin:auto;
animation: float 3s ease-in-out infinite;
}

.book:before {
content:"";
position:absolute;
width:50%;
height:90px;
background:#4f46e5;
right:0;
border-left:2px solid white;
}

@keyframes float {
0% {transform: translateY(0px);}
50% {transform: translateY(-10px);}
100% {transform: translateY(0px);}
}

.card {
background: rgba(17,24,39,0.7);
padding:25px;
border-radius:15px;
margin-top:20px;
}

</style>
""", unsafe_allow_html=True)

# ── Sounds ─────────────────────────────────────────

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

# ── Gemini ─────────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── Google Sheets ──────────────────────────────────

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


def save_score(name,score,total,pct,level):

    connect_sheet().append_row([
        name,
        score,
        total,
        pct,
        level,
        datetime.now().strftime("%Y-%m-%d")
    ])


def get_leaderboard():

    data = connect_sheet().get_all_records()

    return pd.DataFrame(data)

# ── Question bank ─────────────────────────────────

FIXED_BANK = [
{"text":"She ___ to school every day.","options":["go","goes","is go","going"],"correct":1,"explanation":"She is third person singular"},
{"text":"I ___ hungry.","options":["is","are","am","be"],"correct":2,"explanation":"I use am"},
{"text":"They ___ soccer.","options":["play","plays","playing","played"],"correct":0,"explanation":"Plural subject"},
{"text":"He ___ tired.","options":["is","are","be","am"],"correct":0,"explanation":"He uses is"},
{"text":"We ___ ready.","options":["is","are","be","am"],"correct":1,"explanation":"Plural subject"}
]*10

# ── AI questions ─────────────────────────────────

def generate_ai_questions(n=5):

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Generate {n} A1 English questions JSON
"""

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except:
        return []

# ── Build quiz ─────────────────────────────────

def build_quiz():

    fixed = random.sample(FIXED_BANK,20)
    ai = generate_ai_questions(5)

    pool = fixed + ai

    random.shuffle(pool)

    return pool

# ── Init ─────────────────────────────────

def init_quiz(name,level):

    st.session_state.player=name
    st.session_state.level=level
    st.session_state.questions=build_quiz()
    st.session_state.current=0
    st.session_state.score=0
    st.session_state.phase="quiz"

# ── Landing ─────────────────────────────

def page_landing():

    st.markdown("<div class='book'></div>",unsafe_allow_html=True)

    st.title("GB English Quiz")

    level = st.selectbox("Level",["A1","A2","B1"])

    name = st.text_input("Your name")

    if st.button("Start"):

        if name:
            init_quiz(name,level)
            st.rerun()

    if st.button("Leaderboard"):
        st.session_state.phase="leaderboard"
        st.rerun()

# ── Quiz ─────────────────────────────

def page_quiz():

    qs = st.session_state.questions
    idx = st.session_state.current
    q = qs[idx]

    total = len(qs)

    st.progress((idx+1)/total)

    st.metric("Score",st.session_state.score)

    timer=st.empty()

    for i in range(10,0,-1):

        timer.metric("Time",i)

        time.sleep(1)

    st.markdown("<div class='card'>",unsafe_allow_html=True)

    st.write(q["text"])

    for i,opt in enumerate(q["options"]):

        if st.button(opt):

            if i==q["correct"]:
                st.markdown(correct_sound,unsafe_allow_html=True)
                st.success("Correct")
                st.info(q["explanation"])
                st.session_state.score+=1

            else:
                st.markdown(wrong_sound,unsafe_allow_html=True)
                st.error("Incorrect")
                st.info(q["explanation"])

            st.session_state.current+=1

            if st.session_state.current>=total:

                pct=round(
                    st.session_state.score/total*100
                )

                save_score(
                    st.session_state.player,
                    st.session_state.score,
                    total,
                    pct,
                    st.session_state.level
                )

                st.session_state.phase="results"

            st.rerun()

# ── Results ─────────────────────────────

def page_results():

    score=st.session_state.score

    total=len(st.session_state.questions)

    pct=round(score/total*100)

    st.title("Results")

    st.progress(pct/100)

    st.metric("Score",f"{score}/{total}")

    if st.button("Play Again"):
        st.session_state.phase="landing"
        st.rerun()

# ── Leaderboard ─────────────────────────

def page_leaderboard():

    st.title("🏆 Top 10")

    df=get_leaderboard()

    if not df.empty:

        df=df.sort_values("Percent",ascending=False)

        st.dataframe(df.head(10))

    if st.button("Back"):
        st.session_state.phase="landing"
        st.rerun()

# ── Router ─────────────────────────

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