import re


# Words about training
TRAINING_WORDS = {
    "workout", "workouts", "train", "training", "trained", "gym",
    "exercise", "exercising", "exercised", "session", "sessions",
    "run", "running", "ran", "jog", "jogging", "walk", "walking",
    "swim", "swimming", "cycle", "cycling", "lift", "lifting",
    "lifted", "weights", "cardio", "reps", "sets", "yoga", "pilates",
    "class", "classes", "practice", "match", "game", "sport", "sports",
    "routine", "programme", "program", "plan", "schedule",
}

# Words about the body
BODY_WORDS = {
    "tired", "exhausted", "exhausting", "sore", "aching", "ache",
    "aches", "pain", "painful", "injured", "injury", "hurt", "hurts",
    "sleep", "slept", "sleeping", "rest", "rested", "resting",
    "recovery", "recover", "recovered", "energy", "energetic",
    "drained", "heavy", "stiff", "strong", "weak", "body", "legs",
    "shoulders", "back", "knee", "knees",
}

# Words about feelings
FEELING_WORDS = {
    "feel", "feels", "feeling", "felt", "motivated", "motivation",
    "unmotivated", "burnt", "burned", "burnout", "stressed", "stress",
    "anxious", "anxiety", "low", "down", "flat", "frustrated",
    "frustrating", "happy", "excited", "proud", "good", "bad", "great",
    "awful", "terrible", "fine", "okay", "alright", "struggling",
    "struggle", "hard", "difficult", "easy", "enjoy", "enjoying",
    "enjoyed", "hate", "hated", "love", "loved", "dread", "dreading",
    "want", "wanted", "mood", "mentally", "mind",
}

# Words about stopping or carrying on
STOPPING_WORDS = {
    "quit", "quitting", "stop", "stopping", "stopped", "give", "giving",
    "keep", "keeping", "continue", "continuing", "consistent",
    "consistency", "skip", "skipped", "skipping", "miss", "missed",
    "missing", "back", "again", "streak", "goal", "goals", "progress",
    "improve", "improving", "better", "worse",
}

# A transcript is about checking in when it uses any of these words
CHECKIN_TOPIC_WORDS = (
    TRAINING_WORDS | BODY_WORDS | FEELING_WORDS | STOPPING_WORDS
)


# Whole words only so "run" does not match inside "brunch"
def split_into_words(text: str) -> set:
    return set(re.findall(r"[a-z']+", (text or "").lower()))


# This only warns the user because turning away a real check-in is worse than letting an unrelated one  go through
def check_transcript(transcript: str) -> bool:
    if not transcript or not transcript.strip():
        return False

    # One matching word is enough
    return bool(split_into_words(transcript) & CHECKIN_TOPIC_WORDS)
