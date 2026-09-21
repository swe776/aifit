# Section 5.5.4 works out the System Usability Scale score from the Google Form responses
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import EVALUATION_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
import statistics

SUS_RESPONSES_PATH = (
    EVALUATION_DIRECTORY
    / "user_testing"
    / "sus_responses.csv"
)

# The published average SUS score is 68
PUBLISHED_AVERAGE = 68.0

# Objective 4 needs at least ten complete responses
MINIMUM_RESPONSES = 10

# The ten SUS questions and if each one is worded positively or negatively
QUESTIONS = [
    ("I think that I would like to use this system frequently", "positive"),
    ("I found the system unnecessarily complex", "negative"),
    ("I thought the system was easy to use", "positive"),
    (
        "I think that I would need the support of a technical person",
        "negative",
    ),
    (
        "I found the various functions in this system were well integrated",
        "positive",
    ),
    ("I thought there was too much inconsistency in this system", "negative"),
    (
        "I would imagine that most people would learn to use this system",
        "positive",
    ),
    ("I found the system very cumbersome to use", "negative"),
    ("I felt very confident using the system", "positive"),
    ("I needed to learn a lot of things before I could get going", "negative"),
]

def normalise_question(text: str) -> str:
    return " ".join((text or "").split()).lower()


# Find each question's column in the exported Google Form
def find_question_columns(header: list[str]) -> list[str]:
    simple_to_original = {normalise_question(name): name for name in header}
    columns = []

    for question, _ in QUESTIONS:
        opening = normalise_question(question)
        match = next(
            (
                original
                for simple_question, original in simple_to_original.items()
                if simple_question.startswith(opening) or opening in simple_question
            ),
            None,
        )

        if match is None:
            raise SystemExit(
                f"Could not find the column for this SUS question in the exported form\n  {question}"
                "\n\nThe columns in the file are\n  " + "\n  ".join(header)
            )

        columns.append(match)

    return columns


# Score one participant using Brooke's scoring
def calc_sus_score(row: dict, columns: list[str]) -> float | None:
    total = 0

    for column, (_, wording) in zip(columns, QUESTIONS):
        raw = (row.get(column) or "").strip()

        if not raw:
            return None

        try:
            answer = int(float(raw))
        except ValueError:
            return None

        if not 1 <= answer <= 5:
            return None

        # Positive questions score the answer minus one and negative ones score five minus the answer
        total += answer - 1 if wording == "positive" else 5 - answer

    # The total is multiplied by 2.5 to give a score from 0 to 100
    return total * 2.5


# The mean answer to each question for the results table
def average_per_question(rows: list[dict], columns: list[str]) -> list[dict]:
    summary = []

    for index, (column, (question, wording)) in enumerate(
        zip(columns, QUESTIONS), start=1
    ):
        answers = []

        for row in rows:
            raw = (row.get(column) or "").strip()

            if not raw:
                continue

            try:
                value = int(float(raw))
            except ValueError:
                continue

            if 1 <= value <= 5:
                answers.append(value)

        if not answers:
            continue

        summary.append({
            "number": index,
            "question": question,
            "wording": wording,
            "mean_answer_1_to_5": round(statistics.mean(answers), 2),
            "answers": len(answers),
        })

    return summary


def main() -> None:
    if not SUS_RESPONSES_PATH.is_file():
        raise SystemExit(
            f"No responses found at {SUS_RESPONSES_PATH}.\n Export the Google Form responses as CSV and save them there."
        )

    with SUS_RESPONSES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = list(reader)

    columns = find_question_columns(header)

    scored = []
    incomplete = 0

    for row in rows:
        score = calc_sus_score(row, columns)

        if score is None:
            incomplete += 1
            continue

        scored.append(score)

    if not scored:
        raise SystemExit("No complete responses were found.")

    mean = statistics.mean(scored)

    enough_responses = len(scored) >= MINIMUM_RESPONSES
    above_average = mean > PUBLISHED_AVERAGE

    questions = average_per_question(rows, columns)

    print()
    print("AI.FIT OBJECTIVE 4 - USABILITY")
    print("=" * 66)
    print(f"  Responses           {len(rows)}")
    print(f"  Complete            {len(scored)}")

    if incomplete:
        print(f"  Incomplete          {incomplete}  (not scored)")

    print()
    print(f"  Mean SUS score      {mean:.2f}  out of 100")
    print(f"  Published average   {PUBLISHED_AVERAGE}")
    print()
    print("EACH QUESTION")
    print("-" * 66)
    print(f"  {'':<3}{'mean':>6}  question")

    for entry in questions:
        print(
            f"  {entry['number']:<3}{entry['mean_answer_1_to_5']:>6}  "
            f"{entry['question'][:52]}"
        )

    print()
    print("CRITERIA")
    print("-" * 66)
    mark = lambda passed: "MET" if passed else "NOT MET"
    print(f"  At least {MINIMUM_RESPONSES} complete responses"
          f"          {mark(enough_responses)}")
    print(f"  Score above the published average       "
          f"{mark(above_average)}")
    print()
    print(f"  Objective met - "
          f"{'YES' if enough_responses and above_average else 'NO'}")

    summary = {
        "evaluation": "AI.FIT Objective 4 evaluation",
        "responses": len(rows),
        "complete_responses": len(scored),
        "incomplete_responses": incomplete,
        "mean_sus_score": round(mean, 2),
        "published_average": PUBLISHED_AVERAGE,
        "per_question": questions,
        "enough_responses": enough_responses,
        "score_above_the_published_average": above_average,
        "objective_met": enough_responses and above_average,
    }

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIRECTORY / "objective4_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print()
    print(f"Saved - {RESULTS_DIRECTORY / 'objective4_summary.json'}")


if __name__ == "__main__":
    main()
