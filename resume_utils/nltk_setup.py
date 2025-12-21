# resume_utils/nltk_setup.py
import os
import nltk


def ensure_nltk() -> None:
    # Keep downloads inside the repo folder so cloud env can write
    download_dir = os.path.join(os.getcwd(), "nltk_data")
    os.makedirs(download_dir, exist_ok=True)

    # Ensure NLTK searches this directory
    if download_dir not in nltk.data.path:
        nltk.data.path.append(download_dir)

    # (resource_path, package_id)
    required = [
        ("corpora/stopwords", "stopwords"),
        ("tokenizers/punkt", "punkt"),
        ("corpora/wordnet", "wordnet"),
    ]

    for resource_path, pkg in required:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            nltk.download(pkg, download_dir=download_dir, quiet=True)
