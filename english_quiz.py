import streamlit as st
import anthropic
import json
import random
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="English A1 Quiz",
    page_icon="YAN",
    layout="centered"
)

# ── Google Sheets Connection ─────────────────────────────────────────────────

@st.cache_resource
def connect_sheet():
    creds_dict = st.secrets["gcp_service_account"]

    creds = Credentials.from_service_account_info(
        creds_dict,
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


# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0f0f14; }
.stApp { background: #0f0f14; }
.topic-tag {
    background: #1e1e2e;
    color: #6366f1;
    border: 1px solid #2a2a38;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-family: monospace;
}
</style>
""", unsafe_allow_html=True)


# ── Question Bank ────────────────────────────────────────────────────────────

FIXED_BANK = [
    {"text": "She ___ to school every day.", "options": ["go","goes","is go","going"], "correct": 1, "topic": "simple present"},
    {"text": "There ___ some milk in the fridge.", "options": ["are","is","am","be"], "correct": 1, "topic": "there is/are"},
    {"text": "How ___ brothers do you have?", "options": ["much","many","old","big"], "correct": 1, "topic": "countable nouns"},
    {"text": "I ___ TV right now.", "options": ["watch","watches","am watching","watching"], "correct": 2, "topic": "present continuous"},
    {"text": "___ your parents at home yesterday?", "options": ["Was","Were","Are","Is"], "correct": 1, "topic": "past be"},
]


# ── Claude AI Questions ──────────────────────────────────────────────────────

def generate_ai_questions(n=5):

    client = anthropic.Anthropic(
        api_key=st.secrets["ANTHROPIC_API_KEY"]
    )

    prompt = f"""Generate {n} A1 English grammar questions JSON only"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text
        questions = json.loads(raw)

        return questions

    except Exception as e:
        st.warning("AI generation failed")
        return []


# ── Build Quiz ───────────────────────────────────────────────────────────────

def build_quiz():

    fixed = random.sample(FIXED_BANK, 5)
    ai = generate_ai_questions(5)

    pool = fixed + ai
    random.shuffle(pool)

    return pool


# ── Init Quiz ────────────────────────────────────────────────────────────────

def init_quiz(name):

    st.session_state.player_name = name
    st.session_state.questions = build_quiz()
    st.session_state.current = 0
    st.session_state.score = 0
    st.session_state.selected = None
    st.session_state.confirmed = False
    st.session_state.answers = []
    st.session_state.phase = "quiz"


# ── Landing Page ─────────────────────────────────────────────────────────────

def page_landing():

    st.title("🇬🇧 English A1 Quiz")

    name = st.text_input("Your name")

    if st.button("Start Quiz"):

        if name:
            init_quiz(name)
            st.rerun()


    if st.button("Leaderboard"):
        st.session_state.phase = "leaderboard"
        st.rerun()


# ── Quiz Page ────────────────────────────────────────────────────────────────

def page_quiz():

    qs = st.session_state.questions
    idx = st.session_state.current
    q = qs[idx]

    total = len(qs)

    st.progress((idx+1)/total)

    st.write(q["text"])

    for i,opt in enumerate(q["options"]):

        if st.button(opt):

            st.session_state.selected = i

            if i == q["correct"]:
                st.session_state.score += 1

            st.session_state.current += 1

            if st.session_state.current >= total:

                pct = round(
                    (st.session_state.score/total)*100
                )

                save_score(
                    st.session_state.player_name,
                    st.session_state.score,
                    total,
                    pct
                )

                st.session_state.phase="results"

            st.rerun()


# ── Results ──────────────────────────────────────────────────────────────────

def page_results():

    score = st.session_state.score
    total = len(st.session_state.questions)

    pct = round((score/total)*100)

    st.title("Results")

    st.write(score,total,pct)

    if st.button("Play Again"):

        st.session_state.phase="landing"
        st.rerun()


    if st.button("Leaderboard"):

        st.session_state.phase="leaderboard"
        st.rerun()


# ── Leaderboard ──────────────────────────────────────────────────────────────

def page_leaderboard():

    st.title("Leaderboard")

    df = get_leaderboard()

    if not df.empty:

        df = df.sort_values("Percent",ascending=False)

        st.dataframe(df.head(10))

    if st.button("Back"):

        st.session_state.phase="landing"
        st.rerun()


# ── Router ───────────────────────────────────────────────────────────────────

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