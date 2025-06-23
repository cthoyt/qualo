"""Constants for autocuration."""

from collections.abc import Iterable

__all__ = [
    "BACHELOR_OF_SCIENCE_PREFIXES",
    "BACHELOR_OF_SCIENCE_PREFIXES_CF",
    "BACHELOR_PREFIXES",
    "BACHELOR_PREFIXES_CF",
    "MASTER_PREFIXES",
    "MSC_PREFIXES",
    "MSC_PREFIXES_CF",
    "PHD_PREFIXES",
    "PHD_PREFIXES_CF",
]


def _cf_set(prefixes: Iterable[str]) -> set[str]:
    return {prefix.casefold() for prefix in prefixes}


BACHELOR_PREFIXES = [
    "bachelor in",
    "bachelor of",
    "bachelors in",
    "bachelors of",
    "bachelor's in",
    "bachelor's of",
    "bachelor degree in",
    "bachelor degree of",
    "bachelors degree in",
    "bachelors degree of",
    "bachelor's degree in",
    "bachelor's degree of",
]
BACHELOR_PREFIXES_CF = _cf_set(BACHELOR_PREFIXES)

BACHELOR_OF_SCIENCE_PREFIXES = [
    "BSc in",
    "BSc. in",
    "B.Sc. in",
    "B.Sc in",
    "B. Sc. in",
    "B. Sc in",
    "B.S. in",
    "BS in",
    "Bachelor of Science in",
    "Bachelor's of Science in",
    "Bachelors of Science in",
]
BACHELOR_OF_SCIENCE_PREFIXES_CF = _cf_set(BACHELOR_OF_SCIENCE_PREFIXES)

BACHELOR_OF_ARTS_PREFIXES = [
    "Bachelors of Arts in",
    "Bachelor's of Arts in",
    "Bachelor of Arts in",
    "Bachelors of Arts (BA) in",
    "Bachelors of Arts (B.A.) in",
    "Bachelor's of Arts (BA) in",
    "Bachelor's of Arts (B.A.) in",
    "Bachelor of Arts (BA) in",
    "Bachelor of Arts (B.A.) in",
    "BA in",
    "B A in",
    "B.A. in",
    "BA. in",
]
BACHELOR_OF_ARTS_PREFIXES_CF = _cf_set(BACHELOR_OF_ARTS_PREFIXES)

MASTER_PREFIXES = [
    "master in",
    "master of",
    "masters of",
    "master's of",
    "master degree of",
    "masters degree of",
    "master's degree in",
]
MASTER_PREFIXES_CF = _cf_set(MASTER_PREFIXES)

MSC_PREFIXES = [
    "MSci in",
    "MSc. in",
    "M.Sc. in",
    "M.Sc in",
    "MS",
    "Master of science in",
    "Masters of science in",
    "Master's of science in",
    "Master in science in",
    "Masters in science in",
    "Master's in science in",
    "Master of science (MSc) in",
    "Masters of science (MSc) in",
    "Master's of science (MSc) in",
    "Master in science (MSc) in",
    "Masters in science (MSc) in",
    "Master's in science (MSc) in",
]
MSC_PREFIXES_CF = _cf_set(MSC_PREFIXES)

MASTER_OF_ARTS_PREFIXES = [
    "Masters of Arts in",
    "Master's of Arts in",
    "Master of Arts in",
    "Masters of Arts (MA) in",
    "Masters of Arts (M.A.) in",
    "Master's of Arts (MA) in",
    "Master of Arts (MA) in",
    "MA in",
    "M A in",
    "M.A. in",
    "MA. in",
]
MASTER_OF_ARTS_PREFIXES_CF = _cf_set(MASTER_OF_ARTS_PREFIXES)

PHD_PREFIXES = {
    "PhD student in",
    "PhD. in",
    "Ph.D in",
    "PhD degree in",
    "Ph. D. in",
    "Ph.D. in",
    "Doctorate in",
    "DPhil in",
    "DPhil. in",
}
PHD_PREFIXES_CF = _cf_set(PHD_PREFIXES)
