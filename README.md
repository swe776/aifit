# AI.FIT

AI.FIT is a web application which uses multiple pre-trained AI models to help users stay consistent with their fitness journey. A user completes a check-in by recording a short voice entry and taking a photograph of a meal. The voice entry is converted into text and analysed for emotional signals linked to dropout and the meal photograph is analysed for nutrition information that might affect energy and recovery which could lead to fitness inconsistency. These results are combined to classify the user's dropout risk as low, medium or high. Each completed check-in is saved and compared with the user's recent results to see if their risk is increasing, decreasing or stable. Recommendations are then given based on the emotional signals, meal information and risk change.

This is my final year project for CM3070 (University of London, BSc Computer Science) following Topic 4.1: Orchestrating AI models to achieve a goal.

Swetha Suresh

## Contents

1. [How a check-in works](#how-a-check-in-works)
2. [Models used](#models-used)
3. [Running the application](#running-the-application)
4. [Running the tests](#running-the-tests)
5. [Project structure](#project-structure)
6. [Evaluation](#evaluation)
7. [Evaluation data](#evaluation-data)
8. [Results](#results)
9. [Limitations](#limitations)
10. [Privacy and ethics](#privacy-and-ethics)

## How a check-in works

A check-in is split into three steps so that a wrong reading can be caught
by the user before anything is scored.

**1. Voice entry.** The user records up to thirty seconds or uploads an audio
file. Whisper Base turns it into a transcript. The recording is checked for
silence and repetition first so an invalid recording is not sent to the
model. The transcript is shown to the user so they can correct it because
even the best speech model tested still gets roughly one word in eight wrong.
The transcript is also checked against a list of words about training, the
body, feelings and stopping. If none of them appear, the user is warned but
the entry is not rejected because turning away a real check-in is worse than
letting an unrelated one through.

**2. Meal photograph.** BLIP first checks that the photograph shows food.
Three models then read it; SigLIP2 names a dish from Food-101, the Kaludi
food category classifier names one of twelve everyday food groups and BLIP
Large describes the plate. All three readings are shown and the user taps the
one that matches their meal or chooses a band themselves. A dish or caption
reading is looked up in a food lookup table that lists which nutrition groups
each food offers and the meal is placed in a band. A food group reading has a
band set for each of the twelve groups because it names a category and not
the food itself.

A dish or caption reading (SigLIP2, BLIP Large):

- **Balanced** when it has at least three positive groups (protein, fibre,
  produce, wholegrain) and no poor ones
- **Poor** when it has two or more poor groups (saturated fat, sodium,
  sugar) or one poor group and no positive ones
- **Mixed** for everything else

Food group reading (Kaludi):

- **Balanced** never because a category only brings one positive group
- **Poor** for dessert and fried food
- **Mixed** for the other ten; fruit, vegetable, egg, seafood, meat, dairy,
  bread, noodles, rice and soup

The nutrition groups follow the Health Promotion Board's My Healthy Plate
guidance. In the code this counting rule is called B3/P2.

**3. Scoring.** DeBERTa-v3-base reads the checked transcript and gives a
confidence for each of the five emotional signals; burnout, low motivation,
fatigue, high motivation and neutral. Burnout and low motivation are high
risk signals (8.5 points), fatigue is medium (5.5) and high motivation and
neutral are low (2.0). The emotion points are the confidence-weighted average
of all five. The meal band uses fixed points (balanced 2.0, mixed 5.5, poor
8.5) because the user is the one confirming the food and the band. The two
are combined as 0.75 × emotion + 0.25 × meal because the literature review
showed that emotional signals are linked directly to dropout and nutrition is
linked indirectly. The low, medium or high risk level comes from a fixed
reference grid of the 15 signal and band combinations in Appendix A.

After scoring, the check-in is compared with the average of the user's
previous ten dropout scores (at least two are needed). A difference of 1.5 or
more means the risk is increasing or decreasing. If not, it is stable.

Recommendations follow fixed rules instead of an AI model so the same
situation always gets the same advice and every rule can be tested. Advice is
given at medium and high risk, when the risk is increasing and when the meal
is poor. A user whose same high risk signal appeared in at least two of their
previous three check-ins is also told so. At a time, at most three tips are
shown.

Users can correct the emotional signal or meal band after a check-in and the
score, risk level and advice are worked out again from the correction. They
can also rate the advice, see their history and risk chart on the dashboard
and delete any check-in.

## Models used

| Stage | Model | Why it was chosen |
|---|---|---|
| Speech to text | `openai/whisper-base` | Lowest word error rate overall (12.47%) and on Singapore-accented speech (14.08%) |
| Emotional signal | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | Found 76.67% of high risk sentences in 8.87 s each. The large version found 80% but took almost 27 s |
| Meal, dish | `prithivMLmods/Food-101-93M` (SigLIP2) | Best of the three Food-101 classifiers at recognising food |
| Meal, food group | `Kaludi/food-category-classification-v2.0` | Best of the two food group classifiers |
| Meal, caption | `Salesforce/blip-image-captioning-large` | Best of the two caption models and of all seven food models |

None of these models were trained to know what fitness dropout is. The work
is in combining their readings into one result. The model names are all kept
in `backend/app/config.py`.

The emotion model is not given the label names directly. Zero-shot models
compare the text against a sentence such as "This person is feeling {label}".
The words shown to the model are "burnt out", "unmotivated", "physically
tired", "high motivation" and "neutral" which were chosen by comparing eight
wordings. The rest of the application still uses the original labels of
burnout, low motivation, fatigue, high motivation and neutral.

## Running the application


Note: This application was built on Windows System so the
instructions for macOS or Linux might not be 100% correct.


What is needed?
Python 3.14, Node 20.19 or newer and FFmpeg available on
PATH (Whisper uses it to read audio). On macOS you can install FFmpeg with
`brew install ffmpeg`.

**1. Set up.** From the project folder, open visual studio, a new terminal and
use cmd and type

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux there is no cmd so use the normal Terminal.
Type `python3 -m venv .venv` instead of `python -m venv .venv` for the first command
and activate with `source .venv/bin/activate` instead. Once the environment is
active `python` works on its own so every later command in this README is the same.


`requirements.txt` lists every package with the exact versions the
application and the evaluations were run with.


**2. Add a secret key.** Create a file and name it `.env` and copy
`.env.example` to `.env` and set `SECRET_KEY` to a long and random value.
This signs the login tokens. You can make one by

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` is ignored by git so the secret key stays only on your computer

**3. Start the backend.** use cmd

```bash
uvicorn backend.app.main:app --reload
```

**4. Start the frontend** use cmd in a second terminal

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.
The models are downloaded from Hugging Face the first time they are needed so
the first check-in takes longer. After that they stay in memory. Everything
runs on a CPU.

## Running the tests

use cmd on terminal

```bash
python -B -m pytest backend/tests -q
```

This runs 291 tests; 232 unit tests on the rules
(scoring, meal banding, baseline, recommendations, transcript and upload
checks) and 59 integration tests on the routes, accounts and database. The
models are replaced with test replacements so the tests can run quick.

There is also a system check with 51 tests that runs check-ins through the
real models from upload (start) to advice (end). It is not part of pytest
because it takes a few minutes to run

use cmd on terminal

```bash
python -B backend/tests/system/real_model_system_check.py
```

## Project structure

```
backend/
  app/
    main.py                     starts the FastAPI app
    config.py                   settings and the model names
    auth.py                     password hashing (Argon2) and login tokens (JWT)
    database.py, db_models.py   SQLite through SQLAlchemy: accounts and check-ins
    schemas.py                  what the API accepts and returns
    models/
      speech_to_text.py         the speech-to-text model (Whisper)
      emotional_signal.py       the emotional signal model (DeBERTa) and its label wording
      meal_photo.py             the food check and the three meal photograph readings
    logic/
      transcript_check.py       checks the transcript is about training or feelings
      meal_band_rules.py        the food lookup table and the B3/P2 band rule
      dropout_risk_score.py     emotion and meal points, the dropout score and risk level
      personal_baseline.py      the personal baseline and risk change
      recommendation_rules.py   the advice rules
    routers/
      account_routes.py         register, log in, privacy notice
      checkin_routes.py         transcribe, read a meal, score, history, corrections
  tests/
    unit/                       the rules: scoring, B3/P2, baseline, advice, transcript and uploads
    integration/                the routes, accounts and database
    system/                     real_model_system_check.py, whole check-ins with the real models
frontend/
  src/
    App.jsx, main.jsx           the main app and switching between screens
    api.js, auth.jsx            to the backend and the logged-in user
    features/                   one file per screen or part of a screen: CheckInScreen,
                                VoiceEntryInput, MealPhotoInput, CheckInResultScreen,
                                DropoutRiskEstimate, RecommendationCard, DashboardScreen,
                                RiskTrendChart, PrivacyNoticeScreen, AccountScreen
    styles.css
evaluation/                     every evaluation in Chapter 5 (see below)
docs/figures/                   the figures and tables used in the report
requirements.txt                every Python package with exact versions
```

The API is under `/api/accounts` (`/register`, `/login`, `/me`,
`/privacy-notice`) and `/api/checkins` (`/transcribe`, `/analyse-meal`,
creating and listing check-ins, `/trend`, `/stats`, and `/{id}/feedback`,
`/{id}/correction` and deleting a check-in).

## Evaluation

The evaluation follows the four levels in Chapter 5 of the report; models,
application logic, parameters and objectives. Every number in the report
comes from a file in `evaluation/results/` and each file is written by one
script.

| # | Script | What it does | Results file |
|---|---|---|---|
| 1 | `model/evaluate_speech_models.py` | Word error rate of 4 models on 300 recordings | `speech_model_summary.json` |
| 2 | `model/evaluate_emotion_models.py` | High risk recall and time for 6 models on 300 sentences | `emotion_model_summary.json` |
| 3 | `model/evaluate_food_models.py` | How often 7 models name a food on the plate (184 SNAPMe photographs) | `food_recognition.json` |
| 4 | `logic/evaluate_food_banding.py` | Macro F1 of the band the app gives on the 3 selected models' readings | `food_banding.json` |
| 5 | `logic/evaluate_label_wording.py` | Accuracy and high risk recall for 8 label wordings | `label_wording.json` |
| 6 | `logic/evaluate_three_readings.py` | If at least one of the three readings is right | `three_readings.json` |
| 7 | `logic/evaluate_band_rules.py` | Macro F1 of all balanced and poor counting rules on 1,477 meals | `band_rules.json` |
| 8 | `logic/evaluate_hidden_nutrients.py` | How many meals change band without saturated fat, sodium and sugar | `hidden_nutrients.json` |
| 9 | `parameters/evaluate_baseline_settings.py` | Combined score of all 15 window and threshold settings on 1,200 generated histories | `baseline_settings.json`, `baseline_settings.csv` |
| 10 | `objectives/evaluate_objective2.py` | Voice only, meal only and both together on 36 rated cases | `objective2_summary.json` |
| 11 | `logic/evaluate_recommendations.py` | The recommendation rules (the baseline is tested by 9) | `recommendations.json` |
| 12 | `objectives/evaluate_objective4.py` | System Usability Scale from 17 participants | `objective4_summary.json` |

Objective 1 is answered by 1) to 4), Objective 2 by 10), Objective 3 by 9) and 11) and Objective 4 by 12).

Run any of them from the project folder using cmd:

```bash
python evaluation/model/evaluate_speech_models.py
python evaluation/model/evaluate_emotion_models.py
python evaluation/model/evaluate_food_models.py
python evaluation/logic/evaluate_food_banding.py
python evaluation/logic/evaluate_label_wording.py
python evaluation/logic/evaluate_three_readings.py
python evaluation/logic/evaluate_band_rules.py
python evaluation/logic/evaluate_hidden_nutrients.py
python evaluation/parameters/evaluate_baseline_settings.py
python evaluation/objectives/evaluate_objective2.py
python evaluation/logic/evaluate_recommendations.py
python evaluation/objectives/evaluate_objective4.py
```

Some of these read the model names from the application settings so `.env`
has to exist before they can run. If you have not made it yet, please copy
`.env.example` to `.env` following step 2 of Running the application.

The three model comparisons 1), 2) and 3) take a long time on a CPU so they
can also rebuild their results from the predictions saved in the last full run
without having to load any models:

```bash
python evaluation/model/evaluate_speech_models.py --from-saved-predictions
python evaluation/model/evaluate_emotion_models.py --from-saved-predictions
python evaluation/model/evaluate_food_models.py --from-saved-readings
```

Some scripts read the results of others. 3) writes `food_recognition.csv`
which both 4) and 6) read so after a full rerun of 3) you must run 4) and 6)
again in that order.

`python evaluation/make_figures.py` draws the charts and tables in Chapters 4
and 5 and Appendices A and B into `docs/figures/` from the results files so a
figure cannot show a different number from the evaluation it came from. It
reads every results file so run it last. The Chapter 4 code pictures are in `docs/figures/code/`.

Evaluation measures used;

- **Word error rate** is over every word in a dataset after
  lowercasing and removing punctuation
- **High risk recall** is how many of the 120 burnout and low motivation
  sentences were given exactly the right label.
- **Macro F1** works out F1 for balanced, mixed and poor separately and
  averages them so the most common band does not skew the result.
- **Combined score** for the baseline is the average of two rates: how many
  increasing or decreasing histories were caught and how many stable
  histories were correctly left as stable.
- **Fleiss' kappa** measures how much the three raters agreed
  (Fleiss, 1971). Each case's reference label takes the majority vote and if
  there is a tie, the more serious label is kept.

The shared helpers are in `evaluation/shared/`: `paths.py` finds the project
folders, `food_text.py` turns food names into the 12 shared food groups for
the food recognition test 3), `snapme_sampling.py` reads the 184 photographs file names and checks if those images are present and `hpb_reference_band.py` gives a meal its reference band from the
Health Promotion Board guidance.

## Evaluation data

Everything the evaluations use is in `evaluation/data/`

| Folder or file | What it holds | Used by |
|---|---|---|
| `manifests/` | Which 300 speech recordings and 184 SNAPMe photographs were used | 1), 3) |
| `librispeech/`, `voxpopuli_accented/`, `mnsc_asr_test/` | 100 recordings each of clear, accented and Singapore-accented speech | 1) |
| `emotion/emotion_evaluation_examples.csv` | 300 sentences written by 10 participants with consent, 60 per signal | 2), 5) |
| `snapme_photos/` | The 184 SNAPMe meal photographs | 3), 6) |
| `snapme_meals.csv` | Food descriptions, nutrients and reference band of all 1,477 cleaned SNAPMe meals | 3), 4), 6), 7), 8) |
| `objective2_cases.csv`, `objective2_photos/`, `objective2_recordings/` | The 36 Objective 2 cases, their meal photographs and the 12 journal recordings | 10) |
| `rater_sheets/` | The three raters' risk labels | 10) |
| `journals.csv` | The 12 written journals the recordings were made from | 10) |
| `risk_grid.csv` | The 15 row reference risk grid | 11), figures |
| `system_test_images/` | A drink and a pair of shoes to check not food photographs are refused | System check |

The usability study is in `evaluation/user_testing/`: the consent form,
the Google Form and the anonymised responses in `sus_responses.csv` which 12)
reads.

The reference band for each SNAPMe meal comes from the nutrients SNAPMe
measured compared with Health Promotion Board daily guidance divided by
three meals. The journal recordings were made with a Windows system voice
from text participants wrote so no real voice recordings are stored.

**Nothing needs to be downloaded to rerun the evaluations.** Every recording
and photograph used is already in `evaluation/data/`. The full SNAPMe
dataset is about 5.7 GB so only the photographs used are kept and the
speech datasets are cut down to the 300 recordings used.

The recordings come from LibriSpeech, VoxPopuli and the
Multitask National Speech Corpus. The food images come from SNAPMe from the
USDA. Each stays under its own licence.

## Results

**Objective 1** was met. Four speech models, six emotion models and seven
food model configurations were compared on data they were not trained on
and the model used at each stage was the best trade-off for its job.

**Objective 2** was met. All three combinations were tested against
the same reference labels but the meal photograph did not help. The voice
entry alone was correct in 26 of 36 cases (72.22%), both together in 24
(66.67%) and the meal alone in 13 (36.11%). The raters agreed with a Fleiss'
kappa of 0.861.

**Objective 3** was met. The baseline with ten previous scores and a 1.5
threshold reached a 94.56% combined score which is above the 85% target, and
the recommendation rules gave the expected output in all 60 risk change cases
and every other check.

**Objective 4** was met. 17 participants used AI.FIT for a week and gave a
mean System Usability Scale score of 94.85 out of 100 which is above the
published average of 68.

For food, at least one of the three readings recognised the food in 150 of
184 photographs (81.52%) and gave the right band in 136 (73.91%). Removing
saturated fat, sodium and sugar from the reference changes the band of 711 of
1,477 meals (48.1%) which shows how much of the band a photograph cannot
see.

## Limitations

- The meal photograph did not improve the dropout result so it is best
  treated as supporting information.
- Food banding is weak even when the food is recognised because a
  photograph cannot show portion size, oil, salt, sugar or sauces.
- No suitable labelled Singapore food dataset was available so the food
  models could not be evaluated on Singapore dishes. However, HPB was still
  used for food evaluation to bring a Singapore context.
- The emotion model finds 76.67% of high risk sentences so some are missed.
  This is why the user can correct the signal.
- The baseline settings were chosen on random seed generated histories
  instead of real users' check-ins.
- Objective 2 used written journals read by a system voice so it did not
  test natural speech.
- The recommendation tests use prepared cases and do not show if users
  actually follow the advice.
- AI.FIT has never been tested against real dropout.

## Privacy and ethics

AI.FIT follows Singapore's Personal Data Protection Act guidelines. Users
must accept a privacy notice before their first check-in and this is checked
by both the frontend and the backend. Voice recordings and photographs are
deleted as soon as the models have read them so only the checked transcript,
the readings and the scores are stored. Passwords are hashed with Argon2 and
never stored and every route that touches a check-in makes sure it belongs to
the user asking for / accessing it.

AI.FIT is not a medical tool. It does not diagnose burnout, eating disorders
or any other condition and its results are only meant as general fitness
support. This is on every screen to re-iterate the important message. It is
also mentioned in the privacy notice that users have to acknowledge.