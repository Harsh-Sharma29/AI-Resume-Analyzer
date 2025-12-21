# resume_utils/helpers.py
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

__all__ = [
    "safe_strip",
    "safe_list_str",
    "normalize_tokens",
    "robust_experience",
    "calculate_resume_score",
    "estimate_company_count",
    "fallback_colleges_from_text",
    "calculate_ats_score",
]

# -------------------------
# Text utilities
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


def normalize_tokens(text: str) -> Set[str]:
    """
    Tokenize for matching while keeping tech tokens like: c++, node.js, api, sql, etc.
    """
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


def fallback_colleges_from_text(text: str, max_items: int = 3) -> List[str]:
    """
    Simple heuristic fallback when pyresparser returns college_name as None.
    Not perfect, but better than showing nothing.
    """
    if not text:
        return []
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    pat = re.compile(r"\b(university|college|institute|iit|nit|iiit)\b", re.IGNORECASE)

    out: List[str] = []
    for ln in lines:
        if pat.search(ln) and 4 <= len(ln) <= 120:
            out.append(ln)
        if len(out) >= max_items:
            break

    # de-dupe
    seen = set()
    uniq: List[str] = []
    for x in out:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


# -------------------------
# Experience calculation
# -------------------------
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_PRESENT_WORDS = {"present", "current", "till", "tilldate", "now", "ongoing"}


def _safe_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, list):
        return "\n".join(_safe_text(i) for i in x)
    return str(x)


def _pick_section(text: str) -> str:
    """
    Try to isolate the experience section so education years don't pollute results.
    If no headings found, returns full text.
    """
    if not text:
        return ""

    low = text.lower()

    start_keys = [
        "experience",
        "work experience",
        "employment",
        "work history",
        "professional experience",
        "career",
        "internship",
        "internships",
        "positions",
        "employment history",
        "professional history",
    ]
    end_keys = [
        "education",
        "projects",
        "skills",
        "certifications",
        "awards",
        "achievements",
        "publications",
        "summary",
        "objective",
        "academic",
        "qualifications",
        "training",
        "certificate",
    ]

    starts: List[int] = []
    for k in start_keys:
        pattern = rf"(?:^|\n|\r|\s)({re.escape(k)})(?:\s|$|:)"
        for m in re.finditer(pattern, low, re.IGNORECASE | re.MULTILINE):
            starts.append(m.start(1))

    if not starts:
        return text

    s = min(starts)
    tail = low[s:]

    end_positions: List[int] = []
    for k in end_keys:
        pattern = rf"(?:^|\n|\r|\s)({re.escape(k)})(?:\s|$|:)"
        for m in re.finditer(pattern, tail, re.IGNORECASE | re.MULTILINE):
            end_positions.append(m.start(1))

    e = (s + min(end_positions)) if end_positions else len(text)
    return text[s:e]


def _to_ym(month_token: str, year_token: str, is_end: bool, today_: date) -> Optional[Tuple[int, int]]:
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


def _months_between(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    (sy, sm), (ey, em) = a, b
    if (sy, sm) > (ey, em):
        return 0
    return max(0, (ey - sy) * 12 + (em - sm) + 1)


def _merge_ranges(
    ranges: List[Tuple[Tuple[int, int], Tuple[int, int]]]
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
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


def _extract_date_ranges(
    text: str,
    today_: date,
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Supports common formats:
    - 03/2025 – Present
    - 03/2025 - Present
    - 01/2020 - 03/2022
    - Jan 2020 - Mar 2022
    - 2020 - 2022
    """
    if not text:
        return []

    # Normalize unicode dashes to "-"
    norm = (
        str(text)
        .replace("\u2013", "-")  # en-dash
        .replace("\u2014", "-")  # em-dash
        .replace("–", "-")
        .replace("—", "-")
    )

    month_re = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    year_re = r"((?:19|20)\d{2})"
    present_re = r"(present|current|till|tilldate|now|ongoing)"

    ranges: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    seen = set()

    # MM/YYYY - Present
    pat_mmyyyy_present = re.compile(
        rf"\b(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}\s*-\s*{present_re}\b",
        re.IGNORECASE,
    )
    for m in pat_mmyyyy_present.finditer(norm):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)
        sm, sy = m.group(1), m.group(2)
        try:
            start_ym = (int(sy), int(sm))
            ranges.append((start_ym, (today_.year, today_.month)))
        except (ValueError, TypeError):
            pass

    # MM/YYYY - MM/YYYY
    pat_mmyyyy_mmyyyy = re.compile(
        rf"\b(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}\s*-\s*(0?[1-9]|1[0-2])\s*[/-]\s*{year_re}\b",
        re.IGNORECASE,
    )
    for m in pat_mmyyyy_mmyyyy.finditer(norm):
        pos = (m.start(), m.end())
        if pos in seen:
            continue
        seen.add(pos)
        sm, sy, em, ey = m.group(1), m.group(2), m.group(3), m.group(4)
        try:
            start_ym = (int(sy), int(sm))
            end_ym = (int(ey), int(em))
        except (ValueError, TypeError):
            continue
        if start_ym > end_ym:
            start_ym, end_ym = end_ym, start_ym
        if end_ym <= (today_.year, today_.month):
            ranges.append((start_ym, end_ym))

    # Month Year - Month Year/Present
    pat_words = re.compile(
        rf"({month_re})\s*[,./ -]*\s*{year_re}\s*(?:-|to|through)\s*({month_re}|{present_re})?\s*[,./ -]*\s*({year_re})?",
        re.IGNORECASE,
    )
    for m in pat_words.finditer(norm):
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

    # Year - Year/Present
    pat_year = re.compile(
        rf"\b({year_re})\s*(?:-|to|through)\s*({year_re}|{present_re})\b",
        re.IGNORECASE,
    )
    for m in pat_year.finditer(norm):
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
    Robustly estimate experience in years.

    Priority:
    1) Use parser total_experience if it's non-zero and reasonable.
    2) Parse date ranges from 'experience' text + full resume text.
    3) Fallback: year-span heuristic from extracted section.
    """
    today_ = date.today()

    raw_exp = data.get("total_experience")
    if raw_exp is not None:
        try:
            val = float(raw_exp)
            # pyresparser often returns 0 even when experience exists; treat 0 as "unknown"
            if 0.1 <= val <= 60.0:
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


# -------------------------
# Resume scoring helpers
# -------------------------
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

    # Contact Info (10)
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


# -------------------------
# ATS scoring
# -------------------------
def calculate_ats_score(data: dict, jd_text: str = "") -> Tuple[int, Dict[str, int], Dict[str, list]]:
    """
    Returns:
      ats_score (0-100),
      breakdown (category -> points),
      tips (category -> list[str]) actionable suggestions
    """
    text = data.get("text") or ""
    if not isinstance(text, str):
        text = str(text)

    text_low = text.lower()
    jd_low = (jd_text or "").lower()

    breakdown: Dict[str, int] = {
        "Keywords (JD match)": 0,  # 0-45
        "Sections": 0,  # 0-25
        "Contact & Links": 0,  # 0-15
        "Readability": 0,  # 0-15
    }
    tips: Dict[str, list] = {
        "Keywords (JD match)": [],
        "Sections": [],
        "Contact & Links": [],
        "Readability": [],
    }

    # A) Keywords (0-45)
    match_score, _matched, missing_skills = (0, [], [])
    if jd_low.strip():
        skills = safe_list_str(data.get("skills"))
        match_score, _matched, missing_skills = _ats_keyword_match(jd_low, skills)

        breakdown["Keywords (JD match)"] = int(round((match_score / 100) * 45))
        if missing_skills:
            tips["Keywords (JD match)"].append(
                "Add missing JD keywords naturally in Skills + Experience bullets: "
                + ", ".join(missing_skills[:10])
            )
    else:
        tips["Keywords (JD match)"].append(
            "Paste a Job Description to compute keyword match (largest ATS factor)."
        )
        breakdown["Keywords (JD match)"] = 10

    # B) Sections (0-25)
    sections_points = 0

    skills = safe_list_str(data.get("skills"))
    if skills:
        sections_points += 7
    else:
        tips["Sections"].append("Add a clear 'Skills' section with bullet-separated keywords.")

    exp_years = robust_experience(data)
    if exp_years > 0 or safe_list_str(data.get("experience")) or safe_list_str(data.get("company_names")):
        sections_points += 8
    else:
        tips["Sections"].append("Add an 'Experience' section with dates and measurable impact bullets.")

    deg = safe_list_str(data.get("degree"))
    col = safe_list_str(data.get("college_name"))
    if deg or col:
        sections_points += 5
    else:
        tips["Sections"].append("Add an 'Education' section with degree + institute + year.")

    if any(k in text_low for k in ["project", "projects", "portfolio", "github"]):
        sections_points += 5
    else:
        tips["Sections"].append("Add a 'Projects' section with 2–3 strong projects and links.")

    breakdown["Sections"] = min(25, sections_points)

    # C) Contact & Links (0-15)
    contact_points = 0
    name = safe_strip(data.get("name"), default="")
    email = safe_strip(data.get("email"), default="")
    phone = safe_strip(data.get("mobile_number"), default="")

    if name and len(name) > 2:
        contact_points += 4
    else:
        tips["Contact & Links"].append("Ensure your name is plain text at the top (not inside a header image).")

    if email and "@" in email:
        contact_points += 5
    else:
        tips["Contact & Links"].append("Add a plain-text email address (avoid putting it in headers/footers).")

    if phone and len(phone) >= 10:
        contact_points += 3
    else:
        tips["Contact & Links"].append("Add a phone number in plain text.")

    link_hits = len(re.findall(r"(https?://\S+|www\.\S+)", text))
    if link_hits >= 2:
        contact_points += 3
    elif link_hits == 1:
        contact_points += 2
        tips["Contact & Links"].append("Add both GitHub + LinkedIn/Portfolio links.")
    else:
        tips["Contact & Links"].append("Add GitHub + LinkedIn/Portfolio links (plain text URLs).")

    breakdown["Contact & Links"] = min(15, contact_points)

    # D) Readability (0-15)
    read_points = 0

    lines = [ln.strip() for ln in text.splitlines()]
    bullet_lines = sum(1 for ln in lines if ln.startswith(("•", "-", "*")))
    if bullet_lines >= 6:
        read_points += 6
    elif bullet_lines >= 3:
        read_points += 4
        tips["Readability"].append("Use more bullet points for Experience/Projects (ATS parses bullets well).")
    else:
        tips["Readability"].append("Use bullet points (• or -) instead of paragraphs for achievements.")

    if 800 <= len(text) <= 8000:
        read_points += 5
    else:
        tips["Readability"].append("Keep resume length reasonable and ensure text is extractable (not scanned).")

    pipe_count = text.count("|")
    if pipe_count < 25:
        read_points += 4
    else:
        tips["Readability"].append("Avoid tables/columns; use single-column layout and simple separators.")

    breakdown["Readability"] = min(15, read_points)

    ats_score = sum(breakdown.values())
    ats_score = max(0, min(100, ats_score))
    return ats_score, breakdown, tips


def _ats_keyword_match(jd_low: str, skills: List[str]) -> Tuple[int, List[str], List[str]]:
    if not jd_low.strip():
        return 0, [], []

    jd_tokens = normalize_tokens(" ".join(jd_low.split()))
    jd_stop = {
        "and",
        "or",
        "with",
        "to",
        "in",
        "for",
        "of",
        "a",
        "an",
        "the",
        "on",
        "at",
        "by",
        "we",
        "you",
        "your",
        "our",
        "they",
        "them",
        "this",
        "that",
        "as",
        "is",
        "are",
        "years",
        "year",
        "experience",
        "knowledge",
        "skills",
        "ability",
        "required",
    }
    jd_keywords = {t for t in jd_tokens if t not in jd_stop and (len(t) >= 3 or t in {"c", "r"})}

    resume_tokens = set()
    for s in skills:
        resume_tokens.update(normalize_tokens(str(s).lower()))

    if not jd_keywords:
        return 0, [], []

    matched = sorted(jd_keywords.intersection(resume_tokens))
    missing = sorted(jd_keywords.difference(resume_tokens))

    score = int(round(100 * (len(matched) / len(jd_keywords))))
    return score, matched, missing
