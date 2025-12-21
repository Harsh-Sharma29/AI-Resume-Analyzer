# App.py
from __future__ import annotations

import base64
import csv
import errno
import hashlib
import html
import json
import os
import time
import uuid
from io import StringIO
from typing import List, Tuple

import streamlit as st
from pyresparser.resume_parser import ResumeParser

from Courses import COURSES
from resume_utils.helpers import (
    calculate_ats_score,
    calculate_resume_score,
    fallback_colleges_from_text,
    normalize_tokens,
    robust_experience,
    safe_list_str,
    safe_strip,
)
from resume_utils.nltk_setup import ensure_nltk


# Must be the first Streamlit command
st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure NLTK data exists (download to writable folder if needed)
ensure_nltk()

# -------------------------
# Session state defaults
# -------------------------
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = []
if "current_file_id" not in st.session_state:
    st.session_state.current_file_id = None
if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = {}
if "match_result" not in st.session_state:
    st.session_state.match_result = (0, [], [])  # (match_score, matched, missing)
if "ats_result" not in st.session_state:
    st.session_state.ats_result = None  # (ats_score, breakdown, tips)

# -------------------------
# UI / Styling
# -------------------------
st.markdown(
    """
<style>
/* Page */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Cards */
.card {
    background: #ffffff;
    border: 1px solid rgba(49, 51, 63, 0.12);
    border-radius: 14px;
    padding: 14px 16px;
}
.card-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 6px; }
.muted { color: rgba(49, 51, 63, 0.65); }

/* Chips */
.chip {
    display: inline-block;
    padding: 6px 10px;
    margin: 4px 6px 0 0;
    border-radius: 999px;
    border: 1px solid rgba(49, 51, 63, 0.16);
    background: rgba(49, 51, 63, 0.04);
    font-size: 0.85rem;
}

/* Score colors */
.score-high { color: #1f8a3b; font-weight: 700; }
.score-medium { color: #b7791f; font-weight: 700; }
.score-low { color: #b42318; font-weight: 700; }

/* Compact button spacing for skill grid */
div[data-testid="column"] button[kind="secondary"] {
    width: 100%;
    border-radius: 12px;
    padding: 0.35rem 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)

GENERIC_SKILLS = {
    "teamwork",
    "communication",
    "microsoft",
    "office",
    "word",
    "excel",
    "english",
    "spanish",
    "french",
    "german",
    "presentation",
    "problem solving",
    "leadership",
    "management",
    "research",
    "planning",
    "organizing",
}

ROLE_OPTIONS = [
    "Data Scientist",
    "Data Analyst",
    "Machine Learning Engineer",
    "Backend Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "Android Developer",
    "iOS Developer",
    "DevOps Engineer",
    "Product Manager",
    "Business Analyst",
    "UI/UX Designer",
    "Software Engineer",
    "Other",
]

UPLOAD_DIR = "Uploaded_Resumes"
MAX_UPLOAD_MB = 10


# -------------------------
# Helpers (UI)
# -------------------------
def show_pdf(path: str) -> None:
    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
        pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{pdf}" width="100%" height="600"></iframe>',
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        st.error("❌ PDF file not found (it may have been deleted after parsing).")
    except Exception as e:
        st.error(f"❌ Could not display PDF: {str(e)}")


def score_label(score: int) -> Tuple[str, str]:
    if score >= 85:
        return "Excellent", "score-high"
    if score >= 70:
        return "Good", "score-medium"
    if score >= 50:
        return "Fair", "score-medium"
    return "Needs Work", "score-low"


def render_chips(items: List[str], max_items: int = 60) -> None:
    if not items:
        st.write("—")
        return

    shown = items[:max_items]
    html_out = "".join([f"<span class='chip'>{html.escape(str(x))}</span>" for x in shown])
    st.markdown(html_out, unsafe_allow_html=True)

    if len(items) > max_items:
        st.caption(f"+{len(items) - max_items} more")


# -------------------------
# Security / File handling
# -------------------------
def _safe_filename(original_name: str) -> str:
    base = os.path.basename(original_name or "resume.pdf")
    base = "".join(ch for ch in base if ch.isalnum() or ch in (" ", ".", "-", "_")).strip()
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    if not base:
        base = "resume.pdf"
    return base


def _file_id_from_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def save_upload_to_disk(uploaded_file) -> Tuple[str, str]:
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    raw = uploaded_file.getbuffer()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Max allowed is {MAX_UPLOAD_MB} MB.")

    safe_name = _safe_filename(uploaded_file.name)
    unique_prefix = uuid.uuid4().hex[:10]
    final_name = f"{unique_prefix}__{safe_name}"
    path = os.path.join(UPLOAD_DIR, final_name)

    with open(path, "wb") as f:
        f.write(raw)

    return path, _file_id_from_bytes(bytes(raw))


# -------------------------
# Cached parsing
# -------------------------
@st.cache_data(show_spinner=False)
def parse_resume_cached(file_path: str) -> dict:
    return ResumeParser(file_path).get_extracted_data() or {}


# -------------------------
# Job match
# -------------------------
def calculate_skill_match(jd_text: str, resume_skills: List[str]) -> Tuple[int, List[str], List[str]]:
    if not jd_text or not resume_skills:
        return 0, [], []

    jd_raw = " ".join(jd_text.lower().split())
    jd_tokens = normalize_tokens(jd_raw)

    cleaned_skills: List[str] = []
    for s in resume_skills:
        s2 = str(s).strip()
        if not s2:
            continue
        if s2.lower().strip() in GENERIC_SKILLS:
            continue
        cleaned_skills.append(s2)

    matched: List[str] = []
    for skill in cleaned_skills:
        skill_low = " ".join(skill.lower().split())
        skill_tokens = normalize_tokens(skill_low)

        if len(skill_tokens) == 1:
            token = next(iter(skill_tokens))
            if token in jd_tokens:
                matched.append(skill)
        else:
            if skill_low in jd_raw or all(t in jd_tokens for t in skill_tokens):
                matched.append(skill)

    jd_skill_keywords = [
        "python",
        "java",
        "javascript",
        "sql",
        "react",
        "django",
        "aws",
        "docker",
        "kubernetes",
        "git",
        "api",
        "rest",
        "machine learning",
        "data analysis",
        "agile",
        "scrum",
        "fastapi",
        "flask",
        "next.js",
        "node.js",
    ]

    jd_relevant: List[str] = []
    for kw in jd_skill_keywords:
        kw_low = kw.lower().strip()
        kw_tokens = normalize_tokens(kw_low)
        kw_in_jd = (
            (kw_low in jd_raw)
            or (len(kw_tokens) == 1 and next(iter(kw_tokens)) in jd_tokens)
            or all(t in jd_tokens for t in kw_tokens)
        )
        if kw_in_jd:
            jd_relevant.append(kw)

    if not jd_relevant:
        return 0, matched, []

    missing: List[str] = []
    for kw in jd_relevant:
        kw_low = kw.lower().strip()
        covered = any(kw_low in str(s).lower() for s in matched)
        if not covered:
            missing.append(kw)

    covered_count = len(jd_relevant) - len(missing)
    match_percentage = int(100 * covered_count / len(jd_relevant))
    return match_percentage, matched, missing


# -------------------------
# Sidebar
# -------------------------
st.sidebar.title("⚙️ Settings")
role_choice = st.sidebar.selectbox("🎯 Target role", ROLE_OPTIONS, index=0)
target_role = st.sidebar.text_input("Custom role", "Software Developer") if role_choice == "Other" else role_choice

st.sidebar.markdown("—")
st.sidebar.subheader("📌 Job Description")
jd_text = st.sidebar.text_area(
    "Paste job description (optional)",
    height=220,
    key="jd_text",
    placeholder="Paste the job description here…",
)
st.sidebar.caption("Tip: Click skill buttons in Skills tab to add them here.")

st.sidebar.markdown("—")
st.sidebar.caption("Privacy tip: avoid uploading personal resumes to a public deployment.")

# -------------------------
# Main header
# -------------------------
left, right = st.columns([1.6, 1])
with left:
    st.title("AI Resume Analyzer")
    st.caption("Upload a resume → Extract key info → Get score + JD match + course recommendations.")
with right:
    st.markdown(
        """
<div class="card">
  <div class="card-title">Quick Start</div>
  <div class="muted">Upload a PDF and optionally paste a job description in the sidebar.</div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("---")
uploaded_file = st.file_uploader("📄 Upload your Resume (PDF)", type=["pdf"])

if uploaded_file is None:
    st.info("Upload a resume PDF to begin.")
    st.stop()

# Save upload + compute file_id
try:
    file_path, file_id = save_upload_to_disk(uploaded_file)
except Exception as e:
    st.error(f"❌ Upload failed: {str(e)}")
    st.stop()

st.success(f"✅ Uploaded: {os.path.basename(file_path)}")
st.toast("Resume uploaded", icon="📄")

with st.expander("📄 Preview uploaded resume", expanded=False):
    st.caption("If preview doesn’t load, the PDF may be restricted or large.")
    show_pdf(file_path)

# Parse only if new file
if st.session_state.current_file_id != file_id:
    st.session_state.match_result = (0, [], [])
    st.session_state.ats_result = None

    with st.status("Analyzing resume…", expanded=True) as status:
        status.write("Extracting text + entities (pyresparser)…")
        time.sleep(0.10)
        try:
            parsed = parse_resume_cached(file_path)
            st.session_state.parsed_data = parsed
            st.session_state.current_file_id = file_id
            status.update(label="Resume analyzed successfully", state="complete", expanded=False)
            st.toast("Resume analyzed successfully", icon="✅")
        except Exception as e:
            st.session_state.parsed_data = {}
            st.session_state.current_file_id = file_id
            status.update(label="Failed to parse resume", state="error", expanded=True)
            st.toast("Failed to parse resume", icon="❌")
            st.error(f"❌ Failed to parse resume: {str(e)}")

        # ✅ cleanup uploaded PDF after parsing (privacy)
        try:
            os.remove(file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

# Use parsed data from state
data = st.session_state.parsed_data or {}

# Normalize extracted data
name = safe_strip(data.get("name"))
email = safe_strip(data.get("email"))
phone = safe_strip(data.get("mobile_number"))

skills = safe_list_str(data.get("skills"))
skills_lower_list = [s.lower() for s in skills]

degrees = safe_list_str(data.get("degree"))
colleges = safe_list_str(data.get("college_name"))
if not colleges:
    colleges = fallback_colleges_from_text(str(data.get("text") or ""))

# Compute metrics
total_exp = robust_experience(data)
resume_score, score_breakdown = calculate_resume_score(data)
label, label_cls = score_label(resume_score)

# JD match compute (store in state for stability)
def _compute_and_store_match() -> None:
    ms, m_sk, miss = calculate_skill_match(st.session_state.jd_text, skills)
    st.session_state.match_result = (ms, m_sk, miss)

if jd_text.strip():
    if st.session_state.match_result == (0, [], []):
        _compute_and_store_match()
else:
    st.session_state.match_result = (0, [], [])

match_score, matched_skills, missing_skills = st.session_state.match_result

# Top cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("<div class='card'><div class='card-title'>Experience</div>", unsafe_allow_html=True)
    st.metric("Years", f"{total_exp:.1f}")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='card'><div class='card-title'>Skills</div>", unsafe_allow_html=True)
    st.metric("Detected", len(skills))
    st.markdown("</div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='card'><div class='card-title'>Education</div>", unsafe_allow_html=True)
    st.metric("Degrees", len(degrees))
    st.markdown("</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='card'><div class='card-title'>Resume Score</div>", unsafe_allow_html=True)
    st.metric("Score", f"{resume_score}/100")
    st.markdown(f"<div class='{label_cls}'>{label}</div></div>", unsafe_allow_html=True)

# Resume score section
st.markdown("## Resume Quality")
st.progress(resume_score / 100)

cols = st.columns(3)
for i, (k, v) in enumerate(score_breakdown.items()):
    with cols[i % 3]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.metric(k, v)
        st.markdown("</div>", unsafe_allow_html=True)

# ATS Score section
st.markdown("## ATS Score (ATS-friendly check)")
col_a1, col_a2 = st.columns([1, 1])
with col_a1:
    check_ats = st.button("✅ Check ATS score")
with col_a2:
    st.caption("Uses resume text + sections + JD keyword match. Paste a JD for best accuracy.")

if check_ats:
    with st.spinner("Calculating ATS score..."):
        ats_score, ats_breakdown, ats_tips = calculate_ats_score(data, jd_text)
        st.session_state.ats_result = (ats_score, ats_breakdown, ats_tips)

if st.session_state.ats_result is not None:
    ats_score, ats_breakdown, ats_tips = st.session_state.ats_result
    st.metric("ATS Score", f"{ats_score}/100")
    st.progress(float(ats_score) / 100)

    bcols = st.columns(4)
    for i, (k, v) in enumerate(ats_breakdown.items()):
        with bcols[i % 4]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.metric(k, v)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Fix suggestions")
    for k, items in ats_tips.items():
        if items:
            st.write(f"**{k}**")
            for tip in items[:4]:
                st.write(f"- {tip}")

# JD match section
st.markdown("## Job Description Match")
recalc = st.button("🔄 Recalculate match")
if recalc:
    _compute_and_store_match()
    st.toast("Recalculated", icon="🔁")

if jd_text.strip():
    st.progress(match_score / 100)
    st.write(f"Match score: **{match_score}%** (coverage of key skills found in the JD)")

    m1, m2 = st.columns([1, 1])
    with m1:
        st.markdown("### Matched skills")
        render_chips(sorted(set(matched_skills), key=lambda x: str(x).lower()), max_items=80)
    with m2:
        st.markdown("### Missing skills (from JD)")
        if missing_skills:
            render_chips(sorted(set(missing_skills), key=lambda x: str(x).lower()), max_items=80)
        else:
            st.success("No missing skills detected from the tracked keyword set.")
else:
    st.info("Paste a job description in the sidebar to compute match score.")

# Tabs
tab_overview, tab_skills, tab_courses, tab_debug = st.tabs(["📋 Overview", "🧠 Skills", "🎓 Courses", "🧪 Debug"])

with tab_overview:
    st.markdown("### Profile")
    oc1, oc2 = st.columns([1.2, 1])
    with oc1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write(f"**Name:** {name}")
        st.write(f"**Email:** {email}")
        st.write(f"**Phone:** {phone}")
        st.write(f"**Degrees:** {', '.join(degrees) if degrees else 'Not detected'}")
        st.write(f"**Universities/Colleges:** {', '.join(colleges[:3]) if colleges else 'Not detected'}")
        st.markdown("</div>", unsafe_allow_html=True)

    with oc2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("**Notes**")
        st.write("- If resume is scanned/image-based, parsing will be inaccurate.")
        st.write("- College/University extraction depends heavily on resume formatting.")
        st.markdown("</div>", unsafe_allow_html=True)

with tab_skills:
    st.markdown("### 🧠 Skills Explorer")

    if not skills:
        st.warning("No skills detected. Add a dedicated Skills section in the resume.")
    else:
        s_left, _s_right = st.columns([1.2, 1])

        with s_left:
            query = st.text_input("Search skills", placeholder="Type: python, sql, fastapi…")
            mode = st.radio(
                "View",
                ["All skills", "Matched skills (JD)", "Missing skills (JD keywords)"],
                horizontal=True,
            )

        view_list = skills
        if jd_text.strip():
            if mode == "Matched skills (JD)":
                view_list = matched_skills
            elif mode == "Missing skills (JD keywords)":
                view_list = missing_skills

        view_list = sorted(set(view_list), key=lambda x: str(x).lower())

        if query.strip():
            q = query.lower().strip()
            view_list = [x for x in view_list if q in str(x).lower()]

        st.caption(f"Showing {len(view_list)} items (showing up to 80 buttons for performance)")

        st.markdown("#### Click a skill to add it into the JD box")
        cols_btn = st.columns(4)
        for idx, sk in enumerate(view_list[:80]):
            col = cols_btn[idx % 4]
            label_btn = str(sk)
            if col.button(label_btn, key=f"skill_btn_{mode}_{idx}"):
                if label_btn not in st.session_state.selected_skills:
                    st.session_state.selected_skills.append(label_btn)

                existing = st.session_state.jd_text.strip()
                to_add = f"\n- {label_btn}"
                st.session_state.jd_text = (existing + to_add).strip() if existing else f"- {label_btn}"
                st.toast(f"Added: {label_btn}", icon="➕")

        st.markdown("#### Skill chips (read-only)")
        render_chips(view_list, max_items=120)

with tab_courses:
    st.markdown("### Personalized learning paths")

    providers = sorted({c["provider"] for c in COURSES})
    levels = ["any", "beginner", "intermediate", "advanced"]

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        free_only = st.checkbox("Free only", value=False)
    with col_f2:
        provider_filter = st.selectbox("Provider", ["any"] + providers, index=0)
    with col_f3:
        level_filter = st.selectbox("Level", levels, index=0)

    role_map = {
        "data scientist": "data-science",
        "data analyst": "data-science",
        "machine learning engineer": "ml-engineer",
        "backend developer": "backend",
        "full stack developer": "fullstack",
        "frontend developer": "frontend",
        "android developer": "android",
        "ios developer": "ios",
        "devops engineer": "backend",
        "product manager": "data-science",
        "business analyst": "data-science",
        "ui/ux designer": "uiux",
        "software engineer": "fullstack",
    }

    track = None
    tl = (target_role or "").lower()
    for k, v in role_map.items():
        if k in tl:
            track = v
            break

    base_courses = COURSES
    if track:
        base_courses = [c for c in COURSES if track in c["role_tracks"]]

    all_interest_tags = set()
    for s in skills_lower_list + missing_skills:
        all_interest_tags.update(normalize_tokens(str(s)))

    def _score(course: dict) -> int:
        overlap = len(all_interest_tags.intersection(set(course["tags"])))
        bonus = 2 if track and track in course["role_tracks"] else 0
        return overlap + bonus

    filtered = []
    for c in base_courses:
        if free_only and not c["is_free"]:
            continue
        if provider_filter != "any" and c["provider"] != provider_filter:
            continue
        if level_filter != "any" and c["level"] != level_filter:
            continue
        filtered.append(c)

    filtered.sort(key=lambda x: (_score(x), x["title"].lower()), reverse=True)

    if filtered:
        st.caption(
            "Ranked by overlap between your skills/missing JD skills and course tags, "
            "plus fit with the selected role."
        )

        max_results = st.slider("Max results", min_value=3, max_value=15, value=10, step=1)
        shown = filtered[:max_results]

        for i, c in enumerate(shown, 1):
            meta_bits = [c["provider"].upper(), c["level"].title()]
            if c["is_free"]:
                meta_bits.append("FREE")
            meta = " • ".join(meta_bits)
            st.markdown(f"{i}. [{c['title']}]({c['url']})  \n   _{meta}_")

        st.markdown("#### Download learning plan")

        export_rows = []
        for c in shown:
            export_rows.append(
                {
                    "title": c["title"],
                    "url": c["url"],
                    "provider": c["provider"],
                    "level": c["level"],
                    "is_free": c["is_free"],
                    "role_tracks": ",".join(c.get("role_tracks", [])),
                    "tags": ",".join(c.get("tags", [])),
                    "relevance_score": _score(c),
                }
            )

        csv_buf = StringIO()
        fieldnames = [
            "title",
            "url",
            "provider",
            "level",
            "is_free",
            "role_tracks",
            "tags",
            "relevance_score",
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(export_rows)
        csv_text = csv_buf.getvalue()

        st.download_button(
            label="⬇️ Download CSV",
            data=csv_text,
            file_name="learning_plan.csv",
            mime="text/csv",
            key="dl_learning_plan_csv",
        )

        json_text = json.dumps(
            {
                "target_role": target_role,
                "track": track,
                "filters": {
                    "free_only": free_only,
                    "provider": provider_filter,
                    "level": level_filter,
                    "max_results": max_results,
                },
                "courses": export_rows,
            },
            indent=2,
        )

        st.download_button(
            label="⬇️ Download JSON",
            data=json_text,
            file_name="learning_plan.json",
            mime="application/json",
            key="dl_learning_plan_json",
        )
    else:
        st.info("No courses match the current filters. Try relaxing provider/level/free-only options.")

with tab_debug:
    st.caption("Use this while developing. Remove before public deployment if you want.")
    with st.expander("Full extracted JSON"):
        st.json(data)
    st.download_button(
        "Download extracted JSON",
        data=str(data).encode("utf-8"),
        file_name="extracted_resume.json",
        mime="application/json",
    )
