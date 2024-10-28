import pystow
import pandas as pd
from gilda import Grounder

from build import get_grounder
from orcid_downloader.standardize import REVERSE_REPLACEMENTS

PATH = pystow.join(
    "orcid", "2023", "output", "roles", name="education_role_unstandardized_summary.tsv"
)

SKIP = {
    "Adjunct Professor",
    "Assistant Lecturer",
    "Assistant Professor",
    "Associate Professor",
    "Department Head",
    "Diploma",
    "Docent",
    "Engineer",
    "Graduate Student",
    "Habilitation",
    "Intern",
    "Lawyer",
    "Lecturer",
    "Medical Resident",
    "Nurse",
    "Physiotherapist",
    "Postdoctoral Researcher",
    "Professor",
    "Psychologist",
    "Research Assistant",
    "Research Associate",
    "Researcher",
    "Software Developer",
    "Specialist",
    "Student",
    "Teaching Assistant",
    "Trainee",
}


def ground_best(grounder: Grounder, text):
    x = grounder.ground_best(text)
    if not x:
        return None
    return x.term.get_curie()


def main():
    grounder = get_grounder()

    n_misses = 0
    n_hits = 0
    for k, synonyms in REVERSE_REPLACEMENTS.items():
        if k in SKIP:
            continue
        term = grounder.ground_best(k)
        if not term:
            print(k, "TOP LEVEL NEEDS GROUNDING")
        for s in synonyms:
            matches = grounder.ground(s)
            if not matches:
                print(k, "=>", s)
                n_misses += 1
            elif len(matches) > 1:
                print("PROB!", s)
            else:
                n_hits += 1
    total = n_hits + n_misses
    print(f"{n_misses:,}/{total:,} ({n_misses/total:.1%}) to go")

    # print(k, term and term.term.get_curie())

    # This is for finding new parts
    pd.read_csv(PATH, sep="\t")
    # for role, count, example in df.head().values:
    #    print(role, count, example, grounder.ground_best(role))


if __name__ == "__main__":
    main()
