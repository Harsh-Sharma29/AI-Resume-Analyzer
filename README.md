# AI Resume Analyzer

A Streamlit web app that analyzes resumes, estimates experience and resume quality, matches skills against a job description, and recommends learning paths based on the target role.

---

## Features

- Upload a PDF resume and preview it inside the app.
- Parse key fields (name, email, phone, skills, education, companies, raw text) using `pyresparser`.
- Estimate total work experience in years with robust date‑range parsing.
- Compute an overall resume quality score with a category‑wise breakdown.
- Match extracted skills with a pasted job description and highlight missing skills.
- Recommend courses and learning paths based on target role and detected skills.
- Basic location info lookup using IP (best‑effort, optional).

---

## Project Structure

AI-RESUME-ANALYZER/
├─ .venv/ # Local virtual environment (not committed)
├─ pyresparser_local_backup/ # Backup of experimental pyresparser code (not used in app)
│ ├─ init.py
│ ├─ resume_parser.py
│ └─ utils.py
├─ resume_utils/ # All custom helper logic actually used by the app
│ ├─ init.py
│ └─ helpers.py
├─ Uploaded_Resumes/ # Sample resumes / user uploads (safe to delete in repo)
│ ├─ Aditya Singh - Resume.pdf
│ └─ Harsh Sharma - Resume.pdf
├─ App.py # Main Streamlit application
├─ Courses.py # Course lists used for recommendations
├─ requirements.txt # Python dependencies
└─ README.md

text

The running app imports helper functions only from `resume_utils/helpers.py` and uses the pip‑installed `pyresparser` for `ResumeParser`. The `pyresparser_local_backup` folder is kept only as reference and is not imported by `App.py`.

---

## Tech Stack

- **Language:** Python  
- **Web UI:** Streamlit  
- **NLP & Parsing:** pyresparser, spaCy, NLTK, pdfminer.six, docx2txt  
- **Data:** pandas, numpy  
- **Others:** plotly, geocoder

---

## Setup & Installation

1. **Clone the repository**

git clone https://github.com/<your-username>/AI-Resume-Analyzer.git
cd AI-Resume-Analyzer

text

2. **Create and activate a virtual environment** (recommended)

python -m venv .venv

Windows
.venv\Scripts\activate

Linux / macOS
source .venv/bin/activate

text

3. **Install dependencies**

pip install -r requirements.txt

text

4. **Download NLP models / data required by pyresparser**

python -m spacy download en_core_web_sm
python -m nltk.downloader words

text

5. **Run the Streamlit app**

streamlit run App.py

text

Then open the local URL shown in the terminal (typically `http://localhost:8501`).

---

## Usage

- On the main page, upload a **PDF** resume.
- Optionally paste a job description and choose a target role from the sidebar.
- View:
  - Extracted profile information (name, contact, degrees, institutes).
  - Total experience, skills, companies, degrees, and other metrics.
  - Overall resume score and textual feedback.
  - JD match percentage, matched skills, and missing skills.
  - Recommended courses for the selected role.

Sample resumes are provided in the `Uploaded_Resumes/` folder for testing; you can delete them in your public repo if they contain real personal data.

---

## Notes & Credits

- Resume parsing is powered by [`pyresparser`](https://github.com/OmkarPathak/pyresparser) and its dependencies (spaCy, NLTK, pdfminer).  
- The `pyresparser_local_backup/` directory contains experimental/local copies of parser code kept only for reference and is **not** used by `App.py` at runtime.  
- Feel free to extend the scoring logic, add more role‑specific recommendations, or connect this app to a database for admin/analytics features.