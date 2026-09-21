# The daily HPB guidance divided by three to estimate the amount for one meal
PROTEIN_G = 16.0
FIBRE_G = 7.67
FRUIT_VEG = 1.33
WHOLEGRAIN_OZ = 0.67
SATURATED_FAT_PERCENT = 10.0
SODIUM_MG = 667.0
ADDED_SUGARS_TSP = 3.33


# Saturated fat is measured as a share of the meal's energy
def calc_saturated_fat_percent(record: dict) -> float:
    calories = float(record["KCAL"])

    if calories <= 0:
        return 0.0

    return float(record["SFAT"]) * 9 / calories * 100


# The same B3/P2 rule the app uses is applied to the nutrient amounts SNAPMe measured
def calc_reference_band(record: dict) -> str:
    # Protein, fibre, fruit with vegetables and wholegrain count as balanced
    positive_checks = [
        float(record["PROT"]) >= PROTEIN_G,
        float(record["FIBE"]) >= FIBRE_G,
        float(record["F_TOTAL"]) + float(record["V_TOTAL"]) >= FRUIT_VEG,
        float(record["G_WHOLE"]) >= WHOLEGRAIN_OZ,
    ]
    # Saturated fat, sodium and added sugar count as poor
    poor_checks = [
        calc_saturated_fat_percent(record) >= SATURATED_FAT_PERCENT,
        float(record["SODI"]) >= SODIUM_MG,
        float(record["ADD_SUGARS"]) >= ADDED_SUGARS_TSP,
    ]

    num_positive = sum(positive_checks)
    num_poor = sum(poor_checks)

    if num_positive >= 3 and num_poor == 0:
        return "balanced"

    if num_poor >= 2 or (num_poor >= 1 and num_positive == 0):
        return "poor"

    return "mixed"
