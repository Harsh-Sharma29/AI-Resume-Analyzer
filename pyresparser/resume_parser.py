import os
import spacy
from spacy.matcher import Matcher
from . import utils


class ResumeParser:

    def __init__(self, resume):
        self.resume = resume
        self.details = {
            'name': None,
            'email': None,
            'mobile_number': None,
            'skills': [],
            'no_of_pages': 0
        }

        self.nlp = spacy.load("en_core_web_sm")
        self.matcher = Matcher(self.nlp.vocab)

        ext = os.path.splitext(resume)[1]
        self.text_raw = utils.extract_text(resume, ext)
        self.text = " ".join(self.text_raw.split())
        self.doc = self.nlp(self.text)
        self.noun_chunks = list(self.doc.noun_chunks)

        self.extract()

    def extract(self):
        self.details['name'] = utils.extract_name(self.doc, self.matcher)
        self.details['email'] = utils.extract_email(self.text)
        self.details['mobile_number'] = utils.extract_mobile_number(self.text)
        self.details['skills'] = utils.extract_skills(self.doc, self.noun_chunks)
        self.details['no_of_pages'] = utils.get_number_of_pages(self.resume)

    def get_extracted_data(self):
        return self.details
