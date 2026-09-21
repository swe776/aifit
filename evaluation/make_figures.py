# Draws the charts and tables for Chapters 4 and 5 and Appendices A and B from the results files
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent / "shared")
)

from paths import DATA_DIRECTORY, PROJECT_ROOT, RESULTS_DIRECTORY

import csv
import json
import re
import textwrap

FIGURES_DIRECTORY = PROJECT_ROOT / "docs" / "figures"


import matplotlib

# Draw the figures straight to files without opening a window
matplotlib.use("Agg")

import matplotlib.pyplot as plt


# The colours used in every figure
ACCENT = "#4f57a8"
ACCENT_LIGHT = "#9ba1d5"
WARNING_RED = "#a2404c"
GREY = "#83889b"
INK = "#191b26"
GRID_LINE = "#e0e2ec"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": GRID_LINE,
        "axes.labelcolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.bbox": "tight",
    }
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tidy_axes(axis, keep_left: bool = True) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_visible(keep_left)
    axis.spines["bottom"].set_color(GRID_LINE)


# Every figure is saved into docs/figures
def save_figure(figure, name: str) -> None:
    FIGURES_DIRECTORY.mkdir(parents=True, exist_ok=True)

    figure.savefig(FIGURES_DIRECTORY / f"{name}.png", dpi=300)

    plt.close(figure)
    print(f"  {name}.png")


# Objective 2 results
def draw_objective2_table() -> None:
    data = load_json(RESULTS_DIRECTORY / "objective2_summary.json")

    rows = [
        [name, f"{result['correct']}/{result['cases']}",
         f"{result['accuracy_percent']:.2f}%"]
        for name, result in (
            ("Voice entry only", data["voice_only"]),
            ("Both voice and meal photograph", data["both_together"]),
            ("Meal photograph only", data["meal_only"]),
        )
    ]
    figure, axis = plt.subplots(figsize=(7.4, 2.4))
    axis.axis("off")
    table = axis.table(cellText=rows, colLabels=["Configuration", "Correct cases", "Accuracy"], cellLoc="left", colLoc="left", colWidths=[0.52, 0.25, 0.23], bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(GRID_LINE)
        cell.set_linewidth(1)
        cell.PAD = 0.025
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("white" if row % 2 else "#f4f5fa")
            cell.get_text().set_color(INK)

    save_figure(figure, "table_objective2_results")


# Compares the six emotion models fig
def draw_emotion_models_figure() -> None:
    data = load_json(RESULTS_DIRECTORY / "emotion_model_summary.json")

    rows = sorted(
        data["models"],
        key=lambda model: -model["overall"]["high_risk_recall_percent"],
    )

    chosen = next(
        model["model_name"] for model in data["models"] if model["application_model"]
    )

    def short(name):
        return (
            name.replace(" MNLI FEVER ANLI", "")
            .replace(" Ling WANLI", " (Ling WANLI)")
            .replace(" MNLI", "")
        )

    figure, (chart, table) = plt.subplots(
        2, 1, figsize=(10.6, 6.4),
        gridspec_kw={"height_ratios": [1.05, 1], "hspace": 0.34},
    )

    names = [short(model["model_name"]) for model in rows]
    recall = [model["overall"]["high_risk_recall_percent"] for model in rows]
    picked = [model["model_name"] == chosen for model in rows]

    positions = range(len(rows))

    bars = chart.barh(
        list(positions), recall, height=0.6,
        color=[ACCENT if is_picked else GREY for is_picked in picked], zorder=2,
    )
    for bar, value, is_app in zip(bars, recall, picked):
        chart.text(
            value + 1.0, bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%", va="center", fontsize=8.6,
            fontweight="bold" if is_app else "normal",
        )

    chart.set_yticks(list(positions))
    chart.set_yticklabels(
        [name + ("  (in the app)" if is_picked else "") for name, is_picked in zip(names, picked)],
        fontsize=8.4,
    )
    chart.invert_yaxis()
    chart.set_xlim(0, 108)
    chart.set_xticks([0, 20, 40, 60, 80, 100])
    chart.set_xlabel("High risk recall (%)")
    chart.xaxis.grid(True, color=GRID_LINE, linewidth=0.8)
    chart.set_axisbelow(True)
    tidy_axes(chart, keep_left=False)

    table.axis("off")

    headers = [
        "Model", "Burnout", "Low motiv.", "High risk recall",
        "Fatigue", "High motiv.", "Neutral", "Time",
    ]
    columns = [0.0, 0.335, 0.445, 0.60, 0.70, 0.80, 0.885, 1.0]

    for x, header in zip(columns, headers):
        table.text(
            x, 0.90, header, fontsize=7.8, fontweight="bold", color=ACCENT,
            ha="left" if x == 0.0 else "right",
        )

    table.plot([0, 1], [0.83, 0.83], color=GRID_LINE, linewidth=1.2,
               clip_on=False)

    for index, model in enumerate(rows):
        y = 0.70 - index * 0.112
        is_app = model["model_name"] == chosen
        weight = "bold" if is_app else "normal"
        overall = model["overall"]
        per = overall["per_label"]

        found = (
            per["burnout"]["true_positive"]
            + per["low motivation"]["true_positive"]
        )

        cells = [
            short(model["model_name"]),
            f"{per['burnout']['true_positive']}",
            f"{per['low motivation']['true_positive']}",
            f"{found}/120 = {overall['high_risk_recall_percent']:.2f}%",
            f"{per['fatigue']['true_positive']}",
            f"{per['high motivation']['true_positive']}",
            f"{per['neutral']['true_positive']}",
            f"{overall['mean_inference_seconds']:.2f}s",
        ]

        for x, cell in zip(columns, cells):
            table.text(
                x, y, cell, fontsize=7.8, fontweight=weight, color=INK,
                ha="left" if x == 0.0 else "right",
            )


    table.set_xlim(0, 1)
    table.set_ylim(0, 1)

    save_figure(figure, "emotion_model_comparison")


# How often each food model identified a food fig
def draw_food_recognition_figure() -> None:
    summary = load_json(RESULTS_DIRECTORY / "food_recognition.json")

    from backend.app.config import settings

    # The three models the app uses are shown in the main colour
    app_checkpoints = {
        settings.dish_model,
        settings.food_group_model,
        settings.caption_model,
    }
    in_the_app = {
        row["configuration"]
        for row in summary["configurations"]
        if row["checkpoint"] in app_checkpoints
    }

    rows = sorted(
        summary["configurations"],
        key=lambda row: -row["recognised_percent"],
    )

    figure, (chart, table) = plt.subplots(
        2, 1, figsize=(10.4, 6.0),
        gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.34},
    )

    names = [
        row["configuration"].replace("Food Categories", "Food Cat.")
        for row in rows
    ]
    values = [row["recognised_percent"] for row in rows]
    colours = [
        ACCENT if row["configuration"] in in_the_app else GREY
        for row in rows
    ]

    bars = chart.barh(
        range(len(names)), values, height=0.58, color=colours, zorder=2
    )

    for bar, row, value in zip(bars, rows, values):
        chart.text(
            value + 1.0,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            fontsize=9.5,
            fontweight=(
                "bold" if row["configuration"] in in_the_app else "normal"
            ),
        )

    chart.set_yticks(range(len(names)))
    chart.set_yticklabels(
        [
            name + ("  (in the app)" if row["configuration"] in in_the_app
                    else "")
            for name, row in zip(names, rows)
        ],
        fontsize=9,
    )
    chart.invert_yaxis()
    chart.set_xlim(0, 78)
    chart.set_xlabel(
        "Named a food the person recorded eating (% of photographs)"
    )
    chart.xaxis.grid(True, color=GRID_LINE, linewidth=0.8)
    chart.set_axisbelow(True)
    tidy_axes(chart, keep_left=False)

    table.axis("off")

    headers = ["Configuration", "Kind", "Recognised", "Rate", "Time"]
    columns = [0.0, 0.42, 0.63, 0.80, 1.0]

    for x, header in zip(columns, headers):
        table.text(
            x, 0.92, header,
            fontsize=8.6, fontweight="bold", color=ACCENT,
            ha="left" if x == 0.0 else "right",
        )

    table.plot(
        [0, 1], [0.855, 0.855], color=GRID_LINE, linewidth=1.2, clip_on=False
    )

    def kind_of(row: dict) -> str:
        if row["kind"] == "caption":
            return "caption"

        if "Kaludi" in row["configuration"]:
            return "group classifier"

        return "dish classifier"

    for index, row in enumerate(rows):
        y = 0.75 - index * 0.108
        bold = "bold" if row["configuration"] in in_the_app else "normal"
        cells = [
            row["configuration"].replace("Food Categories", "Food Cat."),
            kind_of(row),
            f"{row['recognised']}/{row['photographs']}",
            f"{row['recognised_percent']:.2f}%",
            f"{row['seconds_per_photograph']:.2f}s",
        ]

        for x, cell in zip(columns, cells):
            table.text(
                x, y, cell,
                fontsize=8.4, fontweight=bold, color=INK,
                ha="left" if x == 0.0 else "right",
            )

        if index < len(rows) - 1:
            table.plot(
                [0, 1], [y - 0.036, y - 0.036],
                color=GRID_LINE, linewidth=0.7, clip_on=False,
            )


    table.set_xlim(0, 1)
    table.set_ylim(0, 1)

    save_figure(figure, "food_recognition_snapme")


# How well the three selected models assign the nutrition band fig
def draw_food_banding_figure() -> None:
    summary = load_json(RESULTS_DIRECTORY / "food_banding.json")

    def kind_of(name: str) -> str:
        if name.startswith("BLIP"):
            return "caption"
        if "Kaludi" in name:
            return "group classifier"
        return "dish classifier"

    rows = sorted(
        summary["each_model"].items(),
        key=lambda pair: -pair[1]["macro_f1_percent"],
    )

    figure, (chart, table) = plt.subplots(
        2, 1, figsize=(10.4, 6.0),
        gridspec_kw={"height_ratios": [1.3, 0.7], "hspace": 0.26},
    )

    names = [
        name.replace("Food Categories", "Food Cat.") for name, _ in rows
    ]
    values = [result["macro_f1_percent"] for _, result in rows]
    bars = chart.barh(
        range(len(names)), values, height=0.58, color=ACCENT, zorder=2
    )

    for bar, value in zip(bars, values):
        chart.text(
            value + 0.7,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            fontsize=9.5,
            fontweight="bold",
        )

    chart.set_yticks(range(len(names)))
    chart.set_yticklabels(names, fontsize=9)
    chart.invert_yaxis()
    chart.set_ylim(len(names) - 0.4, -0.4)
    chart.set_xlim(0, max(values) + 8)
    chart.set_xlabel("Nutrition band, macro F1 (%)")
    chart.xaxis.grid(True, color=GRID_LINE, linewidth=0.8)
    chart.set_axisbelow(True)
    tidy_axes(chart, keep_left=False)

    table.axis("off")

    headers = [
        "Configuration", "Kind", "Macro F1",
        "Balanced F1", "Mixed F1", "Poor F1",
    ]
    columns = [0.0, 0.34, 0.50, 0.66, 0.82, 1.0]

    for x, header in zip(columns, headers):
        table.text(
            x, 0.92, header,
            fontsize=8.4, fontweight="bold", color=ACCENT,
            ha="left" if x == 0.0 else "right",
        )

    table.plot(
        [0, 1], [0.855, 0.855], color=GRID_LINE, linewidth=1.2, clip_on=False
    )

    for index, (name, result) in enumerate(rows):
        y = 0.68 - index * 0.2

        cells = [
            name.replace("Food Categories", "Food Cat."),
            kind_of(name),
            f"{result['macro_f1_percent']:.2f}%",
            f"{result['per_band']['balanced']['f1_percent']:.2f}%",
            f"{result['per_band']['mixed']['f1_percent']:.2f}%",
            f"{result['per_band']['poor']['f1_percent']:.2f}%",
        ]

        for x, cell in zip(columns, cells):
            table.text(
                x, y, cell,
                fontsize=8.2, fontweight="bold", color=INK,
                ha="left" if x == 0.0 else "right",
            )

        if index < len(rows) - 1:
            table.plot(
                [0, 1], [y - 0.1, y - 0.1],
                color=GRID_LINE, linewidth=0.7, clip_on=False,
            )

    table.set_xlim(0, 1)
    table.set_ylim(0, 1)

    save_figure(figure, "food_banding_snapme")


# Benefit of showing three readings fig
def draw_three_readings_table() -> None:
    data = load_json(RESULTS_DIRECTORY / "three_readings.json")
    recognised = data["at_least_one_model_recognised_the_food"]
    band_right = data["at_least_one_reading_gave_the_right_band"]
    total = data["photographs"]

    readings = data["each_reading"]
    figure, table = plt.subplots(figsize=(8.4, 4.5))
    table.axis("off")
    headings = ["Reading", "Food\nrecognised", "Correct\nband"]
    rows = []
    display_names = {
        "Food-101 dish": "Food-101 SigLIP2 93M",
        "Food-group classifier": "Kaludi Food Cat. 12",
        "BLIP caption": "BLIP Large",
    }
    for name, result in readings.items():
        rows.append([
            display_names.get(name, name),
            f"{result['food_recognised']}/{total}\n{result['food_recognised_percent']:.2f}%",
            f"{result['correct_band']}/{total}\n{result['correct_band_percent']:.2f}%",
        ])

    rows.append([
        "At least one of the three readings",
        f"{recognised['count']}/{total}\n{recognised['percent']:.2f}%",
        f"{band_right['count']}/{total}\n{band_right['percent']:.2f}%",
    ])

    display = table.table(
        cellText=rows,
        colLabels=headings,
        cellLoc="center",
        colLoc="center",
        colWidths=[0.48, 0.26, 0.26],
        bbox=[0, 0, 1, 1],
    )
    display.auto_set_font_size(False)
    display.set_fontsize(8.2)
    for (row, column), cell in display.get_celld().items():
        cell.set_edgecolor(GRID_LINE)
        cell.set_linewidth(0.7)
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        elif row == len(rows):
            cell.set_facecolor(ACCENT_LIGHT)
            cell.get_text().set_weight("bold")
            if column == 0:
                cell.get_text().set_ha("left")
        elif column == 0:
            cell.get_text().set_ha("left")
    figure.tight_layout()
    save_figure(figure, "three_food_readings_comparison")


# Macro F1 of all 20 nutrient group combinations fig
def draw_band_rules_figure() -> None:
    data = load_json(RESULTS_DIRECTORY / "band_rules.json")
    current_rule = data["in_the_application"]
    rows = [
        (name, result["macro_f1_percent"])
        for name, result in data["results"].items()
    ]
    rows.sort(key=lambda row: row[1], reverse=True)

    labels = [name.replace("balanced ", "B").replace(", poor ", ", P")
              for name, _ in rows]
    scores = [score for _, score in rows]
    colours = [ACCENT if name == current_rule else ACCENT_LIGHT
               for name, _ in rows]

    figure, axis = plt.subplots(figsize=(8.5, 9.2))
    positions = list(range(len(rows)))
    bars = axis.barh(positions, scores, color=colours, height=0.68)

    for bar, (name, score) in zip(bars, rows):
        axis.text(
            score + 0.55, bar.get_y() + bar.get_height() / 2,
            f"{score:.2f}%", va="center", fontsize=8.5,
            fontweight="bold" if score == scores[0] else "normal",
        )
        if name == current_rule:
            axis.text(
                1.0, bar.get_y() + bar.get_height() / 2,
                "Chosen", va="center", fontsize=8.2,
                color="white", fontweight="bold",
            )

    axis.set_yticks(positions)
    axis.set_yticklabels(labels, fontsize=8.7)
    axis.invert_yaxis()
    axis.set_xlim(0, max(scores) + 8)
    axis.set_xlabel("Macro F1 (%)")
    axis.xaxis.grid(True, color=GRID_LINE, linewidth=0.8)
    axis.set_axisbelow(True)
    tidy_axes(axis)

    figure.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(figure, "b3p2_rule_combinations")


# How many meals change band without the hidden nutrients fig
def draw_hidden_nutrients_table() -> None:
    data = load_json(RESULTS_DIRECTORY / "hidden_nutrients.json")
    total = data["meals"]
    moves = data["where_they_move"]
    changed = data["meals_that_change_band"]

    band_changes = [
        ("Poor", "Mixed", moves["poor to mixed"]),
        ("Poor", "Balanced", moves["poor to balanced"]),
        ("Mixed", "Balanced", moves["mixed to balanced"]),
    ]
    rows = [
        [before, after, str(count), f"{count / total * 100:.1f}%"]
        for before, after, count in band_changes
    ]
    rows.append(["Total changed", "", str(changed), f"{changed / total * 100:.1f}%"])
    unchanged = total - changed
    rows.append(["Unchanged", "Same band", str(unchanged), f"{unchanged / total * 100:.1f}%"])

    figure, axis = plt.subplots(figsize=(8.4, 4.5))
    axis.axis("off")
    table = axis.table(
        cellText=rows,
        colLabels=[
            "Original band",
            "Band without saturated fat,\nsodium and added sugar",
            "Meals",
            "% of meals",
        ],
        cellLoc="center",
        colLoc="center",
        colWidths=[0.23, 0.43, 0.16, 0.18],
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.8)
    total_changed_row = 1 + len(band_changes)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor(GRID_LINE)
        cell.set_linewidth(0.7)
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        elif row == total_changed_row:
            cell.set_facecolor(ACCENT_LIGHT)
            cell.get_text().set_weight("bold")
        elif row == total_changed_row + 1:
            cell.set_facecolor("#F0F1FA")

    figure.tight_layout()
    save_figure(figure, "hidden_nutrient_band_changes")


# Split long text into lines so it fits inside a table
def wrap_to(text, characters):
    words = str(text).split()
    lines = []
    line = ""

    for word in words:
        if len(line) + len(word) + 1 > characters and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()

    if line:
        lines.append(line)

    return lines or [""]


# Draw a table where every row is as tall as its longest cell
def draw_table(rows, widths, name, header, characters_per_inch=13, title=None):
    limits = [max(8, int(width * characters_per_inch)) for width in widths]

    wrapped = []
    line_counts = []

    for row in rows:
        cells = [
            wrap_to(value, limit)
            for value, limit in zip(row, limits)
        ]
        line_counts.append(max(len(cell_lines) for cell_lines in cells))
        wrapped.append([chr(10).join(cell_lines) for cell_lines in cells])

    header_lines = max(str(value).count(chr(10)) + 1 for value in header)
    line_inches = 0.16
    padding_inches = 0.14

    header_height = header_lines * line_inches + padding_inches
    row_heights = [count * line_inches + padding_inches for count in line_counts]
    table_height = header_height + sum(row_heights)
    title_height = 0.5 if title else 0.0
    figure_height = table_height + title_height

    figure, axis = plt.subplots(figsize=(sum(widths), figure_height))
    figure.subplots_adjust(left=0, right=1, top=table_height / figure_height, bottom=0)

    if title:
        figure.text(0, 1, title, ha="left", va="top", fontsize=14, fontweight="bold", color=INK)
    axis.axis("off")

    table = axis.table(
        cellText=wrapped,
        colLabels=header,
        colWidths=[width / sum(widths) for width in widths],
        cellLoc="left",
        bbox=[0, 0, 1, 1],
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)

    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor(GRID_LINE)
        cell.set_linewidth(0.8)
        cell.set_text_props(va="center")
        cell.PAD = 0.04

        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.set_text_props(color="white", fontweight="bold", va="center")
            cell.set_height(header_height / table_height)
        else:
            cell.set_height(row_heights[row - 1] / table_height)

            if row % 2 == 0:
                cell.set_facecolor("#f6f7fb")

    save_figure(figure, name)


# Compare the eight label wordings fig
def draw_label_wording_table() -> None:
    data = load_json(RESULTS_DIRECTORY / "label_wording.json")
    labels = [
        "burnout", "low motivation", "fatigue", "high motivation",
        "neutral",
    ]
    rows = []

    for name, result in data["wordings"].items():
        wording = name.split(". ", 1)[0]
        shown = result["labels_shown_to_the_model"]
        recall = result["per_label_recall"]

        rows.append([
            wording,
            " | ".join(shown[label] for label in labels),
            f"{result['accuracy_percent']:.0f}%",
            f"{recall['burnout']['recall_percent']:.0f}%",
            f"{recall['low motivation']['recall_percent']:.0f}%",
            "Chosen" if wording == "D" else "",
        ])

    draw_table(
        rows,
        widths=[1.2, 6.0, 0.85, 1.4, 1.65, 0.85],
        name="label_wording_comparison",
        header=[
            "Combination",
            "Label words",
            "Accuracy",
            "Burnout recall",
            "Low motivation\nrecall",
            "Decision",
        ],
        characters_per_inch=15,
    )


# Appendix A shows the risk level for every combination and why it was set
def draw_appendix_a_risk_grid() -> None:
    grid = load_csv(
        DATA_DIRECTORY / "risk_grid.csv"
    )

    order = [
        "burnout",
        "low motivation",
        "fatigue",
        "high motivation",
        "neutral",
    ]
    meals = ["balanced", "mixed", "poor"]

    by_cell = {
        (row["emotion_label"], row["nutrition_category"]): row
        for row in grid
    }

    def with_source(reason: str, source: str) -> str:
        names = []

        for part in source.split(";"):
            part = part.strip()

            if not part:
                continue

            names.append(re.sub(r"\s*\((\d{4})\)$", r", \1", part))

        if not names:
            return reason

        return f"{reason.rstrip().rstrip('.')} ({'; '.join(names)})."

    rows = []

    for signal in order:
        for meal in meals:
            cell = by_cell[(signal, meal)]

            rows.append([
                signal.title(),
                meal.title(),
                cell["intended_risk_level"].title(),
                with_source(cell["reason"], cell["source"]),
            ])

    # Split Appendix A over three pages so it is easier to read
    pages = [rows[0:6], rows[6:12], rows[12:15]]

    for number, page_rows in enumerate(pages, start=1):
        draw_table(
            page_rows,
            widths=[1.3, 1.0, 0.9, 4.6],
            name=f"appendix_a_reference_grid_page_{number}",
            title="Appendix A" if number == 1 else "Appendix A (continued)",
            header=[
                "Signal",
                "Meal band",
                "Risk level",
                "Why it was set this way",
            ],
            characters_per_inch=12,
        )


# Nutrient banding rules fig
def draw_band_rule_grid() -> None:
    from backend.app.logic.meal_band_rules import (
        POSITIVE_NUTRITION_GROUPS,
        POOR_NUTRITION_GROUPS,
        calc_b3p2_band,
    )

    positive_groups = list(POSITIVE_NUTRITION_GROUPS)
    poor_groups = list(POOR_NUTRITION_GROUPS)

    colours = {
        "balanced": ACCENT,
        "mixed": ACCENT_LIGHT,
        "poor": WARNING_RED,
    }

    figure, axis = plt.subplots(figsize=(6.4, 4.2))

    for balanced in range(5):
        for poor in range(4):
            meal_groups = set(positive_groups[:balanced]) | set(poor_groups[:poor])
            band = calc_b3p2_band(meal_groups)

            axis.add_patch(
                plt.Rectangle(
                    (poor - 0.5, balanced - 0.5), 1, 1,
                    facecolor=colours[band],
                    edgecolor="white",
                    linewidth=2,
                )
            )

            axis.text(
                poor, balanced, band,
                ha="center", va="center", fontsize=9,
                color="white" if band != "mixed" else INK,
                fontweight="bold",
            )

    axis.set_xlim(-0.5, 3.5)
    axis.set_ylim(-0.5, 4.5)
    axis.set_xticks(range(4))
    axis.set_yticks(range(5))
    axis.set_xlabel("poor nutrient groups")
    axis.set_ylabel("balanced nutrient groups")

    for spine in axis.spines.values():
        spine.set_visible(False)

    axis.tick_params(length=0)

    figure.tight_layout()
    save_figure(figure, "nutrition_band_grid")


# Points for each reading and the risk level grid fig
def draw_points_and_levels_figure() -> None:
    from backend.app.logic.dropout_risk_score import (
        EMOTIONAL_SIGNAL_POINTS,
        MEAL_BAND_POINTS,
        REFERENCE_RISK_GRID,
    )

    figure, (left, right) = plt.subplots(
        1, 2, figsize=(9.0, 3.4), gridspec_kw={"width_ratios": [1.15, 1]}
    )

    labels = list(EMOTIONAL_SIGNAL_POINTS) + list(MEAL_BAND_POINTS)
    points = (
        list(EMOTIONAL_SIGNAL_POINTS.values())
        + list(MEAL_BAND_POINTS.values())
    )
    colours = (
        [ACCENT] * len(EMOTIONAL_SIGNAL_POINTS)
        + [ACCENT_LIGHT] * len(MEAL_BAND_POINTS)
    )

    positions = range(len(labels))
    left.barh(list(positions), points, color=colours, height=0.62)

    for position, value in zip(positions, points):
        left.text(
            value + 0.15, position, f"{value}",
            va="center", fontsize=8, color=INK,
        )

    left.set_yticks(list(positions))
    left.set_yticklabels(labels, fontsize=8)
    left.invert_yaxis()
    left.set_xlim(0, 10)
    left.set_xlabel("points out of 10")
    tidy_axes(left)

    signals = list(EMOTIONAL_SIGNAL_POINTS)
    meals = list(MEAL_BAND_POINTS)

    shade = {
        "low": ACCENT_LIGHT,
        "medium": ACCENT,
        "high": WARNING_RED,
    }

    for row, signal in enumerate(signals):
        for column, meal in enumerate(meals):
            level = REFERENCE_RISK_GRID[(signal, meal)]

            right.add_patch(
                plt.Rectangle(
                    (column - 0.5, row - 0.5), 1, 1,
                    facecolor=shade[level], alpha=0.55,
                    edgecolor="white", linewidth=1.5,
                )
            )

            right.text(
                column, row, level,
                ha="center", va="center", fontsize=8, color=INK,
            )

    right.set_xlim(-0.5, len(meals) - 0.5)
    right.set_ylim(len(signals) - 0.5, -0.5)
    right.set_xticks(range(len(meals)))
    right.set_xticklabels(meals, fontsize=8)
    right.set_yticks(range(len(signals)))
    right.set_yticklabels(signals, fontsize=8)
    right.set_xlabel("meal band")

    for spine in right.spines.values():
        spine.set_visible(False)

    right.tick_params(length=0)

    figure.tight_layout()
    save_figure(figure, "risk_grid_points_and_levels")


# Compare the four speech-to-text models fig
def draw_speech_models_figure() -> None:
    data = load_json(RESULTS_DIRECTORY / "speech_model_summary.json")

    sets = [
        ("librispeech_test_clean", "LibriSpeech"),
        ("mnsc_asr_part1_test", "MNSC Singapore"),
        ("voxpopuli_en_accented", "VoxPopuli"),
    ]

    rows = []
    for model in data["models"]:
        rows.append(
            {
                "name": model["model_name"],
                "per_set": [
                    model["by_dataset"][key]["wer_percent"]
                    for key, _ in sets
                ],
                "overall": model["overall"]["wer_percent"],
                "time": model["overall"]["median_inference_seconds"],
            }
        )

    rows.sort(key=lambda row: row["overall"])

    from backend.app.config import settings

    chosen = next(
        model["model_name"]
        for model in data["models"]
        if model["checkpoint"] == settings.speech_model
    )

    figure, (chart, table) = plt.subplots(
        2, 1, figsize=(10.4, 5.8),
        gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.32},
    )

    names = [row["name"] for row in rows]
    values = [row["overall"] for row in rows]
    colours = [ACCENT if name == chosen else GREY for name in names]

    bars = chart.barh(
        range(len(names)), values, height=0.58, color=colours, zorder=2
    )

    for bar, value, name in zip(bars, values, names):
        chart.text(
            value + 1.0,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            fontsize=9.5,
            fontweight="bold" if name == chosen else "normal",
        )

    chart.set_yticks(range(len(names)))
    chart.set_yticklabels(
        [name + ("  (in the app)" if name == chosen else "") for name in names],
        fontsize=9,
    )
    chart.invert_yaxis()
    chart.set_xlim(0, 58)
    chart.set_xlabel("Word error rate across all 300 recordings (%)")
    chart.xaxis.grid(True, color=GRID_LINE, linewidth=0.8)
    chart.set_axisbelow(True)
    tidy_axes(chart, keep_left=False)

    table.axis("off")

    headers = (
        ["Model"] + [label for _, label in sets] + ["Overall", "Median time"]
    )
    columns = [0.0, 0.37, 0.575, 0.725, 0.855, 1.0]

    for x, header in zip(columns, headers):
        table.text(
            x, 0.90, header,
            fontsize=8.6, fontweight="bold", color=ACCENT,
            ha="left" if x == 0.0 else "right",
        )

    table.plot(
        [0, 1], [0.83, 0.83], color=GRID_LINE, linewidth=1.2, clip_on=False
    )

    for index, row in enumerate(rows):
        y = 0.70 - index * 0.165
        bold = "bold" if row["name"] == chosen else "normal"

        cells = (
            [row["name"]]
            + [f"{value:.2f}" for value in row["per_set"]]
            + [f"{row['overall']:.2f}", f"{row['time']:.2f}s"]
        )

        for x, cell in zip(columns, cells):
            table.text(
                x, y, cell,
                fontsize=8.4, fontweight=bold, color=INK,
                ha="left" if x == 0.0 else "right",
            )

        if index < len(rows) - 1:
            table.plot(
                [0, 1], [y - 0.055, y - 0.055],
                color=GRID_LINE, linewidth=0.7, clip_on=False,
            )


    table.set_xlim(0, 1)
    table.set_ylim(0, 1)

    save_figure(figure, "speech_model_comparison")


# Appendix B shows every tip the app can give and its source
def draw_appendix_b_advice() -> None:
    from backend.app.logic.recommendation_rules import (
        EMOTIONAL_SIGNAL_TIPS,
        MEAL_BAND_TIPS,
        REPEAT_SIGNAL_TIP,
        RISK_CHANGE_TIPS,
    )

    sources = {
        "burnout": "Meeusen et al. (2013)",
        "fatigue": "Meeusen et al. (2013)",
        "low motivation": "Teixeira et al. (2012); Ryan et al. (1997)",
        "high motivation": "Teixeira et al. (2012)",
        "neutral": "Teixeira et al. (2012); Ryan et al. (1997)",
    }

    tone_shown = {"firm": "High risk", "gentle": "Medium risk"}

    rows = []
    seen = set()

    for signal, tones in EMOTIONAL_SIGNAL_TIPS.items():
        for tone, tips in tones.items():
            for tip in tips:
                if tip in seen:
                    continue

                seen.add(tip)
                rows.append([
                    signal,
                    tone_shown.get(tone, tone),
                    tip,
                    sources[signal],
                ])

    rows.append([
        "poor meal", "Any risk level",
        MEAL_BAND_TIPS["poor"],
        "Naderi et al. (2025); Thomas, Erdman and Burke (2016); Kerksick et al. (2017)",
    ])
    rows.append([
        "mixed meal", "High or medium risk",
        MEAL_BAND_TIPS["mixed"],
        "Thomas, Erdman and Burke (2016)",
    ])
    rows.append([
        "risk rising", "Any risk level",
        RISK_CHANGE_TIPS["increasing"],
        "Rand et al. (2020)",
    ])
    rows.append([
        "burnout/low motivation repeated", "High risk",
        REPEAT_SIGNAL_TIP,
        "Isoard-Gautheur et al. (2016); Sarrazin et al. (2002)",
    ])

    draw_table(
        rows,
        widths=[1.4, 1.5, 4.4, 3.4],
        name="appendix_b_advice_and_sources",
        title="Appendix B",
        header=["Signal", "When it is used", "What the user is told",
                "Source"],
    )


TABLE_GRID_LINE = "#dfe2ed"
TABLE_STRIPE = "#f4f5fa"


def draw_result_table(name: str, columns: list[str], rows: list[list[str]],
           widths: list[float] | None = None,
           font_size: int = 13, wrap_width: int | None = None,
           fig_width: float = 14) -> None:
    display_rows = rows
    if wrap_width is not None:
        display_rows = [
            [textwrap.fill(str(cell), width=wrap_width) for cell in row]
            for row in rows
        ]
    line_count = sum(
        max(cell.count("\n") + 1 for cell in row)
        for row in display_rows
    )
    height = 0.45 * (line_count + 1)
    fig, axis = plt.subplots(figsize=(fig_width, height))
    axis.axis("off")
    table = axis.table(
        cellText=display_rows,
        colLabels=columns,
        cellLoc="left",
        colLoc="left",
        colWidths=widths,
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, col), cell in table.get_celld().items():
        cell.set_height(
            1.5 if row == 0 else
            max(value.count("\n") + 1 for value in display_rows[row - 1]) + 0.5
        )
        cell.set_edgecolor(TABLE_GRID_LINE)
        cell.set_linewidth(1)
        cell.PAD = 0.025
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("white" if row % 2 else TABLE_STRIPE)
            cell.get_text().set_color(INK)
            if "chosen setting" in rows[row - 1][0].lower():
                cell.get_text().set_weight("bold")
    FIGURES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIRECTORY / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# Draw the tables of results used in Chapter 5
def draw_result_tables() -> None:
    baseline_summary = json.loads((RESULTS_DIRECTORY / "baseline_settings.json").read_text(encoding="utf-8"))
    baseline_score = baseline_summary["app_combined_score_percent"]
    prev_scores_taken = baseline_summary["app_prev_scores_taken"]
    change_threshold = baseline_summary["app_change_threshold"]
    with (RESULTS_DIRECTORY / "baseline_settings.csv").open(encoding="utf-8-sig", newline="") as handle:
        baseline_settings = list(csv.DictReader(handle))
    # Every baseline setting that was tested fig
    baseline = []
    for row in sorted(baseline_settings, key=lambda setting: (int(setting["prev_scores_taken"]), float(setting["change_threshold"]))):
        used_by_app = int(row["prev_scores_taken"]) == prev_scores_taken and float(row["change_threshold"]) == change_threshold
        baseline.append([
            f"{prev_scores_taken} previous scores (chosen setting)" if used_by_app else f"{row['prev_scores_taken']} previous scores",
            row["change_threshold"],
            row["combined_score_percent"] + "%",
        ])
    draw_result_table("table_baseline_parameter_sweep",
           ["Window (previous scores taken)", "Change threshold", "Combined score"], baseline,
           [0.42, 0.28, 0.30])

    with (RESULTS_DIRECTORY / "recommendations.json").open(encoding="utf-8") as handle:
        recommendation = json.load(handle)
    checks = recommendation["checks"]

    def passed(name):
        return f"{checks[name]['passed']}/{checks[name]['total']}"

    # The recommendation rule checks for Objective 3
    recommendation_rows = [
        ["Risk grid", passed("risk_grid"), "Passed"],
        ["Risk changes\n(increasing/decreasing/stable/no baseline yet)", passed("risk_changes"), "Passed"],
        ["High risk advice", passed("high_risk_advice"), "Passed"],
        ["Medium risk advice", passed("medium_risk_advice"), "Passed"],
        ["Low risk silence", passed("low_risk_silence"), "Passed"],
        ["Repeat-signal rule", passed("repeat_signal_rule"), "Passed"],
        ["Rising risk", passed("increasing_risk"), "Passed"],
        ["No recommendations (silent)", passed("no_recommendations_for_a_decreasing_low_risk"), "Passed"],
    ]
    draw_result_table("table_recommendation_evaluation",
           ["Check", "Cases passed", "Decision"], recommendation_rows,
           [0.58, 0.22, 0.20])

    # Objective 3 results
    objective3_rows = [
        ["Baseline (chosen setting)", f"{prev_scores_taken} previous scores, threshold {change_threshold}", f"{baseline_score:.2f}%\ncombined score"],
        *recommendation_rows,
    ]
    draw_result_table("table_objective3_results",
           ["Evaluation", "Result", "Decision"], objective3_rows,
           [0.45, 0.34, 0.21])

    with (RESULTS_DIRECTORY / "objective4_summary.json").open(encoding="utf-8") as handle:
        objective4 = json.load(handle)
    # SUS answers for each question fig
    question_rows = [
        [f"Q{item['number']}", str(item["answers"]), f"{item['mean_answer_1_to_5']:.2f}/5"]
        for item in objective4["per_question"]
    ]
    participants = objective4["complete_responses"]
    question_rows.append(["Mean SUS", str(participants), f"{objective4['mean_sus_score']:.2f}/100"])
    draw_result_table("table_objective4_sus_questions",
           ["Question", "Responses", "Mean answer"], question_rows,
           [0.25, 0.25, 0.50])

    # Unit, integration and system testing fig
    testing_levels = [
        ["Unit testing\n232 pytest cases", "Individual rules - scoring, B3/P2, baseline,\nrecommendations, transcript and file validation", "232 passed"],
        ["Integration testing\n59 pytest cases", "API routes - authentication, database,\nmodel outputs between stages and cleanup", "59 passed"],
        ["System testing\n51 checks", "User experience - upload, analysis, corrections,\nadvice and cleanup with real models", "51 passed"],
    ]
    draw_result_table("table_testing_levels",
           ["Level", "What it checked", "Result"], testing_levels,
           [0.30, 0.50, 0.20])

    # Successes, failures, limitations and possible extensions fig
    evaluation_summary_rows = [
        [
            "All four objectives were met",
            "The meal photo lowered the combined result",
            "Objective 2 used written journals and computer generated voice",
            "Repeat with real voice recordings",
        ],
        [
            "Models were selected using unseen data",
            "Food recognition and banding were not always correct",
            "No suitable labelled Singapore food dataset was available",
            "Repeat with Singapore food data when available",
        ],
        [
            "The three readings and B3/P2 rule were used consistently",
            "Some foods were recognised but given the wrong band",
            "Photos cannot show portions, oil, salt or sauces",
            "Add a feature where users can enter portion and preparation details",
        ],
        [
            f"The baseline reached a {baseline_score:.2f}% combined score",
            "Baseline results came from created test cases",
            "Created test cases may not match real users",
            "Use real check in histories",
        ],
        [
            "All recommendation cases passed",
            "Prepared cases do not show if users follow advice",
            "The recommendation test used prepared cases",
            "Ask fitness and nutrition professionals to review the advice, then check if it changes exercise attendance",
        ],
        [
            f"The SUS score was {objective4['mean_sus_score']:.2f} out of 100",
            "None",
            f"{participants} people completed the usability study",
            "Repeat with a larger group",
        ],
        [
            "Unit, integration and system checks passed",
            "Real models take longer to run",
            "AI.FIT is for general fitness support only and is not designed for medical use",
            "Improve model processing speed and reduce waiting time",
        ],
        [
            "Users could check and correct the results",
            "The app cannot prove real dropout",
            "Dropout risk labels were rater judgements of low, medium or high",
            "Use a real study to observe dropout and compare results with real users",
        ],
        [
            "Five emotion signal labels were tested",
            "The five labels may not cover every user",
            "The labels were chosen for this project",
            "Use a real study to see which emotion labels should be added",
        ],
        [
            "Written outputs, transcript correction, meal-band correction and a consent form support inclusive design",
            "No dedicated accessibility study was completed",
            "Full born accessible testing for blind users was not completed",
            "Use a typed check-in, screen-reader testing and radical inclusion with users with different access needs",
        ],
    ]
    draw_result_table(
        "table_successes_failures_limitations_extensions",
        ["Successes", "Failures", "Limitations", "Possible extensions"],
        evaluation_summary_rows,
        [0.25, 0.25, 0.25, 0.25],
        font_size=10,
        wrap_width=32,
        fig_width=20,
    )

    # The inclusive design part of the critique
    inclusive_design = [
        [
            "Inclusive design - speech was tested on three datasets with different accents",
            "This does not cover every accent or speaking style",
            "Test more accents and involve users with different speech needs",
        ],
        [
            "Born accessible design - the voice entry becomes written text that users can check and correct",
            "A transcript alone does not make the complete app accessible to blind users",
            "Add a typed check-in option and test the full flow with a screen reader",
        ],
        [
            "Born accessible design - food readings, risk levels, recommendations and errors are shown as text",
            "Full screen-reader and disability-user testing was not completed",
            "Check keyboard use, screen-reader labels, contrast and text descriptions for charts and images",
        ],
        [
            "Inclusive design - users can correct the transcript and choose a manual meal band",
            "The project did not include a formal accessibility study",
            "Repeat the evaluation with blind, deaf and hard-of-hearing users",
        ],
    ]
    draw_result_table(
        "table_inclusive_design",
        ["What AI.FIT includes", "Limitation or failure", "Possible extension"],
        inclusive_design,
        [0.34, 0.33, 0.33],
        font_size=10,
        wrap_width=34,
        fig_width=20,
    )


# Draw every figure and report any that could not be drawn
def main() -> None:
    print("Drawing the report figures from the results files.")
    print()

    failed: list[str] = []
    total = 0

    for name, draw in [
        ("the band grid", draw_band_rule_grid),
        ("band rule combinations", draw_band_rules_figure),
        ("hidden nutrient band changes", draw_hidden_nutrients_table),
        ("points and levels", draw_points_and_levels_figure),
        ("the speech models", draw_speech_models_figure),
        ("the emotion models", draw_emotion_models_figure),
        ("naming a food on the plate",
         draw_food_recognition_figure),
        ("banding a photographed meal",
         draw_food_banding_figure),
        ("three readings together", draw_three_readings_table),
        ("Objective 2", draw_objective2_table),
        ("emotion label wording combinations",
         draw_label_wording_table),
        ("Appendix A, the reference grid", draw_appendix_a_risk_grid),
        ("Appendix B, advice and sources", draw_appendix_b_advice),
        ("Chapter 5, the result tables", draw_result_tables),
    ]:
        total += 1
        print(name)

        try:
            draw()
        except Exception as error:
            print(f"  could not be drawn - {error}")
            failed.append(name)

    print()

    if failed:
        print(f"{len(failed)} of {total} figures did not draw")

        for name in failed:
            print(f"  {name}")

        print()
        print("The files for those are whatever was there before.")

        raise SystemExit(1)

    print(f"All {total} figures drawn into {FIGURES_DIRECTORY}")


if __name__ == "__main__":
    main()
