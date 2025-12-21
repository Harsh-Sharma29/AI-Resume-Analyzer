# Courses.py

__all__ = [
    "COURSES",
    "ds_course",
    "web_course",
    "android_course",
    "ios_course",
    "uiux_course",
    "resume_videos",
    "interview_videos",
]

# Unified course objects with metadata
# level: beginner / intermediate / advanced
# provider: Coursera, Udemy, YouTube, Google, LinkedIn, Datacamp, etc.
# is_free: bool

COURSES = [
    {
        "id": "ml_google_crashcourse",
        "title": "Machine Learning Crash Course by Google",
        "url": "https://developers.google.com/machine-learning/crash-course",
        "role_tracks": ["data-science", "ml-engineer"],
        "tags": ["python", "machine-learning", "supervised", "google"],
        "level": "beginner",
        "provider": "Google",
        "is_free": True,
    },
    {
        "id": "ml_az_udemy",
        "title": "Machine Learning A-Z (Udemy)",
        "url": "https://www.udemy.com/course/machinelearning/",
        "role_tracks": ["data-science", "ml-engineer"],
        "tags": ["python", "r", "machine-learning"],
        "level": "intermediate",
        "provider": "Udemy",
        "is_free": False,
    },
    {
        "id": "ml_andrew_ng",
        "title": "Machine Learning (Andrew Ng)",
        "url": "https://www.coursera.org/learn/machine-learning",
        "role_tracks": ["data-science", "ml-engineer"],
        "tags": ["matlab", "octave", "machine-learning"],
        "level": "beginner",
        "provider": "Coursera",
        "is_free": False,  # audit free, but keep simple flag
    },
    {
        "id": "ds_simplilearn_master",
        "title": "Data Scientist Master Program (Simplilearn, IBM)",
        "url": "https://www.simplilearn.com/big-data-and-analytics/senior-data-scientist-masters-program-training",
        "role_tracks": ["data-science"],
        "tags": ["python", "machine-learning", "big-data"],
        "level": "advanced",
        "provider": "Simplilearn",
        "is_free": False,
    },
    {
        "id": "ds_linkedin_foundations",
        "title": "Data Science Foundations (LinkedIn Learning)",
        "url": "https://www.linkedin.com/learning/data-science-foundations-fundamentals-5",
        "role_tracks": ["data-science"],
        "tags": ["data-analysis", "statistics"],
        "level": "beginner",
        "provider": "LinkedIn",
        "is_free": False,
    },
    {
        "id": "ds_datacamp_track",
        "title": "Data Scientist with Python (DataCamp)",
        "url": "https://www.datacamp.com/tracks/data-scientist-with-python",
        "role_tracks": ["data-science"],
        "tags": ["python", "pandas", "statistics", "machine-learning"],
        "level": "intermediate",
        "provider": "DataCamp",
        "is_free": False,
    },
    {
        "id": "django_crashcourse",
        "title": "Django Crash Course (YouTube)",
        "url": "https://youtu.be/e1IyzVyrLSU",
        "role_tracks": ["backend", "fullstack"],
        "tags": ["python", "django", "web"],
        "level": "beginner",
        "provider": "YouTube",
        "is_free": True,
    },
    {
        "id": "django_fullstack_udemy",
        "title": "Python Django Full Stack Bootcamp",
        "url": "https://www.udemy.com/course/python-and-django-full-stack-web-developer-bootcamp",
        "role_tracks": ["backend", "fullstack"],
        "tags": ["python", "django", "javascript"],
        "level": "intermediate",
        "provider": "Udemy",
        "is_free": False,
    },
    {
        "id": "react_crashcourse",
        "title": "React Crash Course (YouTube)",
        "url": "https://youtu.be/Dorf8i6lCuk",
        "role_tracks": ["frontend", "fullstack"],
        "tags": ["javascript", "react"],
        "level": "beginner",
        "provider": "YouTube",
        "is_free": True,
    },
    {
        "id": "node_express_crashcourse",
        "title": "Node.js & Express (YouTube)",
        "url": "https://youtu.be/Oe421EPjeBE",
        "role_tracks": ["backend", "fullstack"],
        "tags": ["javascript", "node", "express"],
        "level": "beginner",
        "provider": "YouTube",
        "is_free": True,
    },
    {
        "id": "android_youtube_beginners",
        "title": "Android Development for Beginners (YouTube)",
        "url": "https://youtu.be/fis26HvvDII",
        "role_tracks": ["android", "mobile"],
        "tags": ["android", "java"],
        "level": "beginner",
        "provider": "YouTube",
        "is_free": True,
    },
    {
        "id": "android_kotlin_udacity",
        "title": "Android Kotlin Developer (Udacity)",
        "url": "https://www.udacity.com/course/android-kotlin-developer-nanodegree--nd940",
        "role_tracks": ["android", "mobile"],
        "tags": ["android", "kotlin"],
        "level": "intermediate",
        "provider": "Udacity",
        "is_free": False,
    },
    {
        "id": "ios_udemy_bootcamp",
        "title": "iOS App Development Bootcamp",
        "url": "https://www.udemy.com/course/ios-13-app-development-bootcamp/",
        "role_tracks": ["ios", "mobile"],
        "tags": ["ios", "swift"],
        "level": "beginner",
        "provider": "Udemy",
        "is_free": False,
    },
    {
        "id": "ios_udacity_nanodegree",
        "title": "iOS Developer Nanodegree (Udacity)",
        "url": "https://www.udacity.com/course/ios-developer-nanodegree--nd003",
        "role_tracks": ["ios", "mobile"],
        "tags": ["ios", "swift"],
        "level": "intermediate",
        "provider": "Udacity",
        "is_free": False,
    },
    {
        "id": "google_ux_certificate",
        "title": "Google UX Design Certificate",
        "url": "https://www.coursera.org/professional-certificates/google-ux-design",
        "role_tracks": ["uiux"],
        "tags": ["ux", "ui", "figma"],
        "level": "beginner",
        "provider": "Coursera",
        "is_free": False,
    },
    {
        "id": "coursera_uiux_specialization",
        "title": "UI / UX Design Specialization",
        "url": "https://www.coursera.org/specializations/ui-ux-design",
        "role_tracks": ["uiux"],
        "tags": ["ux", "ui", "wireframing"],
        "level": "intermediate",
        "provider": "Coursera",
        "is_free": False,
    },
]

# Legacy lists kept for backward compatibility
ds_course = [
    [c["title"], c["url"]]
    for c in COURSES
    if "data-science" in c["role_tracks"] or "ml-engineer" in c["role_tracks"]
]

web_course = [
    [c["title"], c["url"]]
    for c in COURSES
    if any(r in c["role_tracks"] for r in ["backend", "frontend", "fullstack"])
]

android_course = [[c["title"], c["url"]] for c in COURSES if "android" in c["role_tracks"]]
ios_course = [[c["title"], c["url"]] for c in COURSES if "ios" in c["role_tracks"]]
uiux_course = [[c["title"], c["url"]] for c in COURSES if "uiux" in c["role_tracks"]]

resume_videos = [
    "https://youtu.be/Tt08KmFfIYQ",
    "https://youtu.be/y8YH0Qbu5h4",
    "https://youtu.be/u75hUSShvnc",
]

interview_videos = [
    "https://youtu.be/HG68Ymazo18",
    "https://youtu.be/BOvAAoxM4vg",
    "https://youtu.be/KukmClH1KoA",
]
