import streamlit as st
import anthropic
import json
import random
import pandas as pd
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="English A1 Quiz",
    page_icon="🇬🇧",
    layout="centered"
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0f0f14; }
.stApp { background: #0f0f14; }
.quiz-card {
    background: #18181f;
    border: 1px solid #2a2a38;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
}
.topic-tag {
    background: #1e1e2e;
    color: #6366f1;
    border: 1px solid #2a2a38;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    font-family: monospace;
    letter-spacing: 1px;
}
.correct { color: #22c55e; font-weight: 600; }
.wrong   { color: #ef4444; font-weight: 600; }
h1, h2, h3 { color: #e8e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Fixed question bank (A1 – upper end) ─────────────────────────────────────
FIXED_BANK = [
    {"text": "She ___ to school every day.", "options": ["go","goes","is go","going"], "correct": 1, "topic": "simple present"},
    {"text": "There ___ some milk in the fridge.", "options": ["are","is","am","be"], "correct": 1, "topic": "there is/are"},
    {"text": "How ___ brothers do you have?", "options": ["much","many","old","big"], "correct": 1, "topic": "countable nouns"},
    {"text": "I ___ TV right now.", "options": ["watch","watches","am watching","watching"], "correct": 2, "topic": "present continuous"},
    {"text": "___ your parents at home yesterday?", "options": ["Was","Were","Are","Is"], "correct": 1, "topic": "past be"},
    {"text": "We don't have ___ sugar.", "options": ["some","any","a","an"], "correct": 1, "topic": "some/any"},
    {"text": "He ___ born in 1998.", "options": ["is","was","were","be"], "correct": 1, "topic": "past be"},
    {"text": "Can you help ___?", "options": ["I","my","me","mine"], "correct": 2, "topic": "object pronouns"},
    {"text": "This is ___ book. It belongs to her.", "options": ["hers","her","she","my"], "correct": 1, "topic": "possessives"},
    {"text": "I ___ like spicy food.", "options": ["don't","doesn't","am not","isn't"], "correct": 0, "topic": "negation"},
    {"text": "The children ___ playing in the park.", "options": ["is","am","are","be"], "correct": 2, "topic": "present continuous"},
    {"text": "What ___ you do last night?", "options": ["do","does","did","were"], "correct": 2, "topic": "simple past"},
    {"text": "She ___ a letter yesterday.", "options": ["write","writes","wrote","writing"], "correct": 2, "topic": "simple past"},
    {"text": "Is there ___ coffee left?", "options": ["some","any","many","much"], "correct": 1, "topic": "some/any"},
    {"text": "___ he speak French?", "options": ["Do","Does","Is","Are"], "correct": 1, "topic": "questions"},
    {"text": "I am taller ___ my sister.", "options": ["then","than","that","as"], "correct": 1, "topic": "comparatives"},
    {"text": "She never ___ late to class.", "options": ["come","comes","is coming","came"], "correct": 1, "topic": "frequency adverbs"},
    {"text": "We went ___ the supermarket.", "options": ["in","at","to","on"], "correct": 2, "topic": "prepositions"},
    {"text": "The movie starts ___ 8 o'clock.", "options": ["in","on","at","to"], "correct": 2, "topic": "prepositions of time"},
    {"text": "I have lived here ___ 2019.", "options": ["for","since","ago","from"], "correct": 1, "topic": "for/since"},
    {"text": "They ___ dinner when I called.", "options": ["have","were having","had","are having"], "correct": 1, "topic": "past continuous"},
    {"text": "He is ___ student in the class.", "options": ["tall","taller","tallest","the tallest"], "correct": 3, "topic": "superlatives"},
    {"text": "I ___ never tried sushi.", "options": ["have","had","has","am"], "correct": 0, "topic": "present perfect"},
    {"text": "She works ___ a hospital.", "options": ["in","on","at","by"], "correct": 2, "topic": "prepositions"},
    {"text": "Would you like ___ water?", "options": ["a","an","some","any"], "correct": 2, "topic": "some/any"},
]

# ── Leaderboard (session-based, use st.session_state as simple store) ─────────
if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = []

# ── Claude API: generate extra questions ─────────────────────────────────────
def generate_ai_questions(n: int = 5) -> list:
    """Ask Claude to generate n A1 English questions and return parsed list."""
    client = anthropic.Anthropic()
    prompt = f"""Generate {n} A1-level English grammar multiple-choice questions.
Return ONLY a valid JSON array, no markdown, no extra text.
Each item must have exactly these keys:
  "text": question string with ___ for the blank,
  "options": array of exactly 4 strings,
  "correct": integer index (0-3) of the correct option,
  "topic": short grammar topic label

Example item:
{{"text":"She ___ a teacher.","options":["am","is","are","be"],"correct":1,"topic":"verb to be"}}

Make the questions slightly challenging for A1 (upper-beginner level).
Do NOT repeat these topics in the same batch: vary between tenses, prepositions, pronouns, articles, comparatives."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        questions = json.loads(raw)
        # Validate structure
        valid = []
        for q in questions:
            if all(k in q for k in ("text", "options", "correct", "topic")):
                if len(q["options"]) == 4 and isinstance(q["correct"], int):
                    valid.append(q)
        return valid
    except Exception as e:
        st.warning(f"AI question generation failed: {e}. Using bank only.")
        return []

# ── Build a quiz session ───────────────────────────────────────────────────────
def build_quiz(n_questions: int = 15) -> list:
    """Combine fixed bank + AI questions, shuffle, return n_questions."""
    fixed = random.sample(FIXED_BANK, min(10, len(FIXED_BANK)))
    ai_qs = generate_ai_questions(n=5)
    pool = fixed + ai_qs
    random.shuffle(pool)
    return pool[:n_questions]

# ── Session state init ────────────────────────────────────────────────────────
def init_quiz(name: str):
    st.session_state.player_name = name
    st.session_state.questions   = build_quiz(15)
    st.session_state.current     = 0
    st.session_state.score       = 0
    st.session_state.selected    = None
    st.session_state.confirmed   = False
    st.session_state.answers     = []
    st.session_state.phase       = "quiz"

# ── UI: Landing ───────────────────────────────────────────────────────────────
def page_landing():
    st.markdown("## 🇬🇧 English A1 Quiz")
    st.markdown("15 questions · Grammar · Upper-beginner level")
    st.markdown("---")

    name = st.text_input("Your name", placeholder="e.g. Yan Carlos", max_chars=30)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("▶ Start Quiz", use_container_width=True, type="primary"):
            if name.strip():
                with st.spinner("Generating your quiz with AI..."):
                    init_quiz(name.strip())
                st.rerun()
            else:
                st.error("Enter your name first.")
    with col2:
        if st.button("🏆 Leaderboard", use_container_width=True):
            st.session_state.phase = "leaderboard"
            st.rerun()

# ── UI: Quiz ──────────────────────────────────────────────────────────────────
def page_quiz():
    qs      = st.session_state.questions
    idx     = st.session_state.current
    q       = qs[idx]
    total   = len(qs)
    score   = st.session_state.score

    # Progress bar
    st.progress(idx / total)
    st.markdown(f"`Question {idx+1}/{total}` &nbsp;&nbsp; ✓ {score} correct",
                unsafe_allow_html=True)

    st.markdown(f"<span class='topic-tag'>{q['topic']}</span>", unsafe_allow_html=True)
    st.markdown(f"### *\"{q['text']}\"*")

    # Options
    labels = ["A", "B", "C", "D"]
    confirmed = st.session_state.confirmed
    selected  = st.session_state.selected

    for i, opt in enumerate(q["options"]):
        label = f"{labels[i]}.  {opt}"
        if confirmed:
            if i == q["correct"]:
                label += "  ✓"
            elif i == selected and i != q["correct"]:
                label += "  ✗"

        if st.button(label, key=f"opt_{idx}_{i}",
                     use_container_width=True,
                     disabled=confirmed):
            st.session_state.selected = i
            st.rerun()

    # Highlight selected
    if selected is not None and not confirmed:
        st.info(f"Selected: **{q['options'][selected]}** — click Check Answer to confirm.")

    st.markdown("---")

    if not confirmed:
        if st.button("✅ Check Answer", type="primary",
                     disabled=(selected is None), use_container_width=True):
            st.session_state.confirmed = True
            if selected == q["correct"]:
                st.session_state.score += 1
            st.session_state.answers.append({
                **q, "chosen": selected
            })
            st.rerun()
    else:
        # Feedback
        if selected == q["correct"]:
            st.success("Correct! 🎉")
        else:
            st.error(f"Wrong. Correct answer: **{q['options'][q['correct']]}**")

        next_label = "Next →" if idx + 1 < total else "See Results →"
        if st.button(next_label, type="primary", use_container_width=True):
            if idx + 1 >= total:
                # Save to leaderboard
                pct = round((st.session_state.score / total) * 100)
                st.session_state.leaderboard.append({
                    "name":  st.session_state.player_name,
                    "score": st.session_state.score,
                    "total": total,
                    "pct":   pct,
                    "date":  datetime.now().strftime("%b %d %H:%M")
                })
                st.session_state.phase = "results"
            else:
                st.session_state.current   += 1
                st.session_state.selected   = None
                st.session_state.confirmed  = False
            st.rerun()

# ── UI: Results ───────────────────────────────────────────────────────────────
def page_results():
    total = len(st.session_state.questions)
    score = st.session_state.score
    pct   = round((score / total) * 100)
    name  = st.session_state.player_name

    if pct >= 90:
        msg, color = "Excellent! Solid A1 foundation.", "green"
    elif pct >= 70:
        msg, color = "Good job! A few gaps to fix.", "orange"
    elif pct >= 50:
        msg, color = "Fair. More practice needed.", "orange"
    else:
        msg, color = "Keep studying. These are A1 basics.", "red"

    st.markdown(f"## Results for {name}")
    st.markdown(f"### Score: {score}/{total} — {pct}%")
    st.markdown(f"*{msg}*")
    st.markdown("---")

    # Answer review
    st.markdown("#### Review")
    for i, a in enumerate(st.session_state.answers):
        correct = a["chosen"] == a["correct"]
        icon    = "✅" if correct else "❌"
        ans     = a["options"][a["correct"]]
        st.markdown(f"{icon} **Q{i+1}** _{a['text']}_ → `{ans}`")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Play Again", use_container_width=True, type="primary"):
            st.session_state.phase = "landing"
            st.rerun()
    with col2:
        if st.button("🏆 Leaderboard", use_container_width=True):
            st.session_state.phase = "leaderboard"
            st.rerun()

# ── UI: Leaderboard ────────────────────────────────────────────────────────────
def page_leaderboard():
    st.markdown("## 🏆 Leaderboard")
    lb = st.session_state.leaderboard

    if not lb:
        st.info("No scores yet. Be the first to play!")
    else:
        df = pd.DataFrame(lb)
        df = df.sort_values("pct", ascending=False).reset_index(drop=True)
        df.index += 1
        df.columns = ["Name", "Score", "Total", "%", "Date"]
        top10 = df.head(10)

        # Medal for top 3
        def medal(i):
            return {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))

        top10.index = [medal(i) for i in top10.index]
        st.dataframe(top10[["Name", "Score", "Total", "%", "Date"]],
                     use_container_width=True)

    st.markdown("---")
    if st.button("← Back", use_container_width=True):
        st.session_state.phase = "landing"
        st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
if "phase" not in st.session_state:
    st.session_state.phase = "landing"

phase = st.session_state.phase

if phase == "landing":
    page_landing()
elif phase == "quiz":
    page_quiz()
elif phase == "results":
    page_results()
elif phase == "leaderboard":
    page_leaderboard()
