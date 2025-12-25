# pyresparser/utils.py
from __future__ import annotations

import re
from datetime import date
from typing import Any, List, Optional, Tuple

import docx2txt
from pdfminer.high_level import extract_text as pdf_extract_text  # avoid name clash


# -------------------------
# File text extraction
# -------------------------
def extract_text(file_path: str, ext: str) -> str:
    """
    Backward-compatible API for pyresparser.
    Many projects expect: pyresparser.utils.extract_text(file_path, extension)
    """
    ext = (ext or "").lower().strip()

    if ext == ".pdf":
        return pdf_extract_text(file_path) or ""

    if ext == ".docx":
        return docx2txt.process(file_path) or ""

    return ""


def extract_resume_text(file_path: str, ext: str) -> str:
    """
    Your newer helper name (kept for your App.py).
    Internally uses extract_text() for a single source of truth.
    """
    return extract_text(file_path, ext)


# -------------------------
# Basic regex fields
# -------------------------
def extract_email(text: str) -> Optional[str]:
    if not text:
        return None
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return emails[0] if emails else None


def extract_mobile_number(text: str) -> Optional[str]:
    if not text:
        return None
    phones = re.findall(r"\+?\d[\d -]{8,12}\d", text)
    return phones[0] if phones else None


# -------------------------
# spaCy-based extractors (kept simple)
# -------------------------
def extract_name(doc, matcher=None) -> Optional[str]:
    """Try PERSON entity first."""
    for ent in getattr(doc, "ents", []):
        if ent.label_ == "PERSON":
            return ent.text
    return None


def extract_skills(doc, noun_chunks=None) -> List[str]:
    """Simple keyword match. Replace with a real skills DB for better accuracy."""
    skills_db = {
        "python", "java", "machine learning", "data science",
        "django", "react", "node", "android", "ios", "ui", "ux",
    }
    skills = set()
    for token in doc:
        t = token.text.lower().strip()
        if t in skills_db:
            skills.add(token.text)
    return sorted(skills)


def get_number_of_pages(file_path: str) -> int:
    # Keep placeholder if you don't need it yet.
    return 1


# -------------------------
# Helpers used by App.py
# -------------------------
def safe_strip(value: Any, default: str = "Not Detected") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value if value else default


def safe_list_str(items: Any) -> List[str]:
    if not items:
        return []
    if not isinstance(items, list):
        items = [items]
    out: List[str] = []
    for x in items:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def normalize_tokens(text: str) -> set:
    if not text:
        return set()
    tokens = re.findall(r"\b[a-zA-Z0-9+#.]+\b", text.lower())
    tokens = [t for t in tokens if len(t) > 1 or t in ["c", "r", "j"]]
    return set(tokens)


def extract_years_from_text(text: str) -> List[int]:
    if not text:
        return []
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    return sorted(set(int(y) for y in years))


# -------------------------
# Robust experience estimation
# (moved from App.py so App.py stays thin)
# -------------------------
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_PRESENT_WORDS = {"present", "current", "till", "tilldate", "now", "ongoing"}


def _safe_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, list):
        return "\n".join(_safe_text(i) for i in x)
    return str(x)


def _pick_section(text: str) -> str:
    """Try to isolate the experience section to avoid education dates polluting results."""
    if not text:
        return ""

    low = text.lower()

    start_keys = [
        "experience", "work experience", "employment", "work history",
        "professional experience", "career", "internship", "internships",
        "positions", "employment history", "professional history",
    ]
    end_keys = [
        "education", "projects", "skills", "certifications", "awards",
        "achievements", "publications", "summary", "objective", "academic",
        "qualifications", "training", "certificate",
    ]

    starts = []
    for k in start_keys:
        pattern = rf"(?:^|\n|\r|\s)({re.escape(k)})(?:\s|$|:)"
        for match in re.finditer(pattern, low, re.IGNORECASE | re.MULTILINE):
            starts.append(match.start(1))

    if not starts:
        return text

    s = min(starts)
    tail = low[s:]
    end_positions = []
    for k in end_keys:
        pattern = rf"(?:^|\n|\r|\s)({re.escape(k)})(?:\s|$|:)"
        for match in re.finditer(pattern, tail, re.IGNORECASE | re.MULTILINE):
            end_positions.append(match.start(1))

    e = (s + min(end_positions)) if end_positions else len(text)
    return text[s:e]


def _to_ym(month_token: str, year_token: str, is_end: bool, today_: date):
    if not year_token:
        return None
    try:
        y = int(year_token)
    except ValueError:
        return None

    if y < 1900 or y > today_.year + 1:
        return None

    if not month_token:
        m = 12 if is_end else 1
    else:
        m = _MONTHS.get(month_token.lower(), 12 if is_end else 1)

    m = max(1, min(12, m))
    return (y, m)


def _months_between(a: tuple, b: tuple) -> int:
    (sy, sm), (ey, em) = a, b
    if (sy, sm) > (ey, em):
        return 0
    return max(0, (ey - sy) * 12 + (em - sm) + 1)


def _merge_ranges(ranges: List[Tuple[Tuple[int, int], Tuple[int, int]]]):
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda r: r[0])
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ms, me = merged[-1]
        if s <= me:
            merged[-1] = (ms, max(me, e))
        else:
            merged.append((s, e))
    return merged


def _extract_date_ranges(text: str, today_: date):
    if not text:
        return []

    month_re = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    year_re = r"((?:19|20)\d{2})"
    present_re = r"(present|current|till|tilldate|now|ongoing)"

    ranges = []
    seen = set()

    # MM/YYYY - Present
    pat_present = re.compile(
        rf"(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}\s*(?:-|–|—)\s*{present_re}",
        re.IGNORECASE,
    )
    for m in pat_present.finditer(text):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)
        sm, sy = m.group(1), m.group(2)
        try:
            start_month = int(sm)
            start_year = int(sy)
            if 1900 <= start_year <= today_.year + 2:
                ranges.append(((start_year, start_month), (today_.year, today_.month)))
        except (ValueError, TypeError):
            pass

    # Month Year - Month Year/Present
    pat_a = re.compile(
        rf"({month_re})\s*[,./ -]*\s*{year_re}\s*(?:-|–|—|to|through)\s*({month_re}|{present_re})?\s*[,./ -]*\s*({year_re})?",
        re.IGNORECASE,
    )
    for m in pat_a.finditer(text):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)

        sm, sy = m.group(1), m.group(2)
        em_or_present, ey = m.group(3), m.group(4)

        start_ym = _to_ym(sm, sy, is_end=False, today_=today_)
        if not start_ym:
            continue

        if isinstance(em_or_present, str) and em_or_present.lower().strip() in _PRESENT_WORDS:
            ranges.append((start_ym, (today_.year, today_.month)))
        else:
            end_ym = _to_ym(em_or_present or "", ey or "", is_end=True, today_=today_)
            if end_ym:
                if start_ym > end_ym:
                    start_ym, end_ym = end_ym, start_ym
                if end_ym <= (today_.year, today_.month):
                    ranges.append((start_ym, end_ym))

    # MM/YYYY - MM/YYYY or Present
    pat_num = re.compile(
        rf"(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}\s*(?:-|–|—|to|through)\s*((?:0?[1-9]|1[0-2])\s*[/-]\s*{year_re}|{present_re})",
        re.IGNORECASE,
    )
    for m in pat_num.finditer(text):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)

        sm, sy = m.group(1), m.group(2)
        end_part = m.group(3)

        try:
            start_ym = (int(sy), int(sm))
        except (ValueError, TypeError):
            continue

        if isinstance(end_part, str) and end_part.lower().strip() in _PRESENT_WORDS:
            ranges.append((start_ym, (today_.year, today_.month)))
        else:
            end_match = re.search(rf"(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}", end_part or "", re.IGNORECASE)
            if end_match:
                try:
                    end_ym = (int(end_match.group(2)), int(end_match.group(1)))
                    if start_ym > end_ym:
                        start_ym, end_ym = end_ym, start_ym
                    if end_ym <= (today_.year, today_.month):
                        ranges.append((start_ym, end_ym))
                except (ValueError, TypeError):
                    pass

    # Year - Year/Present
    pat_b = re.compile(
        rf"({year_re})\s*(?:-|–|—|to|through)\s*({year_re}|{present_re})",
        re.IGNORECASE,
    )
    for m in pat_b.finditer(text):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)

        sy = m.group(1)
        ey_or_present = m.group(2)

        start_ym = _to_ym("", sy, is_end=False, today_=today_)
        if not start_ym:
            continue

        if isinstance(ey_or_present, str) and ey_or_present.lower().strip() in _PRESENT_WORDS:
            ranges.append((start_ym, (today_.year, today_.month)))
        else:
            end_ym = _to_ym("", ey_or_present, is_end=True, today_=today_)
            if end_ym:
                if start_ym > end_ym:
                    start_ym, end_ym = end_ym, start_ym
                if end_ym <= (today_.year, today_.month):
                    ranges.append((start_ym, end_ym))

    return ranges


def robust_experience(data: dict) -> float:
    """
    Calculate total work experience in years.
    Priority:
    1) Use parser total_experience (if valid)
    2) Parse date ranges from experience section
    3) Parse date ranges from full text
    4) Fallback year-span heuristic
    """
    today_ = date.today()

    raw_exp = data.get("total_experience")
    if raw_exp is not None:
        try:
            val = float(raw_exp)
            if 0.0 <= val <= 60.0:
                return round(val, 1)
        except (TypeError, ValueError):
            pass

    full_text = _safe_text(data.get("text"))
    exp_text = _safe_text(data.get("experience"))
    combined = "\n".join([exp_text, full_text]).strip() if exp_text else full_text

    exp_section = _pick_section(combined)

    ranges = _extract_date_ranges(exp_section, today_=today_)
    if not ranges and exp_section != combined:
        ranges = _extract_date_ranges(combined, today_=today_)

    if ranges:
        merged = _merge_ranges(ranges)
        total_months = sum(_months_between(s, e) for s, e in merged)
        years = total_months / 12.0
        return round(min(years, 60.0), 1)

    years_list = extract_years_from_text(exp_section)
    if len(years_list) >= 2:
        span = years_list[-1] - years_list[0]
        return float(min(span, 60))
    if len(years_list) == 1 and years_list[0] <= today_.year:
        return float(min(today_.year - years_list[0], 60))

    return 0.0


def estimate_company_count(data: dict) -> int:
    names = set()

    companies = data.get("company_names") or []
    if isinstance(companies, list):
        for c in companies:
            if c:
                names.add(str(c).strip())
    elif companies:
        names.add(str(companies).strip())

    exp_list = data.get("experience") or []
    if isinstance(exp_list, list):
        for e in exp_list:
            if isinstance(e, dict):
                for k in ("company", "organization", "employer"):
                    v = e.get(k)
                    if v:
                        names.add(str(v).strip())

    return len({n for n in names if n})


def calculate_resume_score(data: dict) -> Tuple[int, dict]:
    breakdown = {
        "Contact Info": 0,
        "Professional Summary": 0,
        "Skills": 0,
        "Experience": 0,
        "Education": 0,
        "Projects": 0,
    }

    # Contact (10)
    contact_points = 0
    name = safe_strip(data.get("name"), default="")
    email = safe_strip(data.get("email"), default="")
    phone = safe_strip(data.get("mobile_number"), default="")
    if name and len(name) > 2:
        contact_points += 3
    if email and "@" in email:
        contact_points += 4
    if phone and len(phone) >= 10:
        contact_points += 3
    breakdown["Contact Info"] = min(contact_points, 10)

    # Summary (10)
    text = data.get("text") or ""
    if not isinstance(text, str):
        text = str(text)
    summary_keywords = ["objective", "summary", "professional", "experienced", "skilled"]
    if any(kw in text.lower()[:500] for kw in summary_keywords):
        breakdown["Professional Summary"] = 10
    elif len(text) > 2000:
        breakdown["Professional Summary"] = 5

    # Skills (20)
    skills = safe_list_str(data.get("skills"))
    if skills:
        breakdown["Skills"] = min(20, len(skills) * 2)

    # Experience (30)
    exp_points = 0
    total_exp_years = robust_experience(data)
    if total_exp_years >= 6:
        exp_points = 30
    elif total_exp_years >= 3:
        exp_points = 20
    elif total_exp_years >= 1:
        exp_points = 10
    else:
        company_count = estimate_company_count(data)
        if company_count >= 3:
            exp_points = 30
        elif company_count == 2:
            exp_points = 20
        elif company_count == 1:
            exp_points = 10
    breakdown["Experience"] = exp_points

    # Education (15)
    degrees = safe_list_str(data.get("degree"))
    colleges = safe_list_str(data.get("college_name"))
    if degrees and colleges:
        breakdown["Education"] = 15
    elif degrees or colleges:
        breakdown["Education"] = 8

    # Projects (15)
    project_keywords = ["project", "achievement", "award", "certificate", "publication", "portfolio"]
    project_mentions = sum(1 for kw in project_keywords if kw in text.lower())
    if project_mentions >= 2:
        breakdown["Projects"] = 15
    elif project_mentions == 1:
        breakdown["Projects"] = 8
    elif len(text) > 3000:
        breakdown["Projects"] = 5

    total_score = sum(breakdown.values())
    return min(total_score, 100), breakdown
