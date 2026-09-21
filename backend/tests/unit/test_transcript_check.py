# Unit tests for the check that a transcript is about training or feelings
import csv
from pathlib import Path

import pytest

from backend.app.logic.transcript_check import (
    check_transcript,
)


# Real check-ins that must be accepted
REAL_ENTRIES = [
    "I feel like giving up",
    "skipped the gym again",
    "my legs are sore",
    "training has been going well this week",
    "I am exhausted and I did not sleep",
    "no motivation at all today",
    "I hate every session lately",
    "back is stiff but I want to keep going",
    "tired",
    "proud of myself for turning up",
]


# Entries about something else that should get a warning
UNRELATED_ENTRIES = [
    "purple elephant yelloe banana big mountain",
    "the turtle is green and it jumps over the pong",
    "what is the weather in singapore tomorrow",
    "please add cucumber to the shopping list",
]


@pytest.mark.parametrize("transcript", REAL_ENTRIES)
def test_a_real_check_in_is_accepted(transcript):
    assert check_transcript(transcript) is True


@pytest.mark.parametrize("transcript", UNRELATED_ENTRIES)
def test_an_unrelated_transcript_is_turned_away(transcript):
    assert check_transcript(transcript) is False


@pytest.mark.parametrize("transcript", ["", "   ", None])
def test_nothing_at_all_is_turned_away(transcript):
    assert check_transcript(transcript) is False


# "grunt" and "brunch" both hold the letters of "run" without being the word
def test_a_word_inside_another_word_does_not_count():
    assert check_transcript("grunt brunch") is False


# Every Objective 2 journal is a real check-in so none of them should get a warning
def test_every_real_journal_is_accepted():
    cases_path = (
        Path(__file__).resolve().parents[3]
        / "evaluation"
        / "data"
        / "objective2_cases.csv"
    )

    if not cases_path.is_file():
        pytest.skip("the Objective 2 cases are not there")

    with cases_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    rejected = [
        row["reference_transcript"]
        for row in rows
        if not check_transcript(row["reference_transcript"])
    ]

    assert rejected == []
