import re


# Words that show a caption is about food
FOOD_WORDS = {
    "apple", "apricot", "asparagus", "aubergine", "avocado", "banana",
    "beans", "beansprout", "beetroot", "bento", "berry", "bibimbap",
    "biscuit", "biscuits", "black coffee", "blackberry", "blueberry",
    "bok choy", "bread", "broccoli", "brown rice", "brownie", "burger",
    "burrito", "cabbage", "cake", "candy", "cantaloupe", "carrot",
    "cauliflower", "celery", "cereal", "cereal bar", "cheese", "cherry",
    "chicken", "chips", "chocolate", "chocolate bar", "chow mein",
    "clear soup", "clementine", "coca cola", "coffee", "coke", "cola",
    "congee", "cookie", "cookies", "courgette", "cranberry", "croissant",
    "cucumber", "cup noodles", "cupcake", "curry", "date", "deep fried",
    "dessert", "donut", "donuts", "doughnut", "doughnuts", "dragonfruit",
    "dumpling", "dumplings", "edamame", "egg", "eggplant", "eggs",
    "energy drink", "fanta", "fig", "fish", "fish soup", "fried", "fries",
    "fruit", "granola", "granola bar", "grape", "grapefruit", "green tea",
    "greens", "guava", "hamburger", "honeydew", "hot chocolate",
    "ice cream", "instant noodles", "jam", "juice", "kale", "kiwi", "latte",
    "leek", "lemon", "lentils", "lettuce", "lime", "lychee", "mandarin",
    "mango", "meat", "melon", "milk", "milk tea", "milkshake", "mixed rice",
    "muesli", "muffin", "mushroom", "nectarine", "noodles", "nuts",
    "oatmeal", "okra", "onion", "orange", "overnight oats", "pancake",
    "pancakes", "papaya", "pasta", "pastry", "peach", "peanut butter",
    "pear", "pepper", "pepsi", "persimmon", "pho", "pineapple", "pizza",
    "plum", "poke bowl", "pomegranate", "porridge", "potato",
    "prawn crackers", "produce", "protein bar", "pumpkin", "radish",
    "rambutan", "ramen", "raspberry", "rice", "salad", "salad greens",
    "salmon", "sandwich", "sandwich wrap", "sashimi", "smoothie", "soda",
    "soft drink", "soup", "soy milk", "spinach", "sprite",
    "steamed chicken", "steamed fish", "strawberry", "sushi", "sushi roll",
    "sweet and sour", "sweetcorn", "syrup", "taco", "tacos", "tangerine",
    "tea", "toast", "tofu", "tomato", "vegetable", "vegetables", "waffle",
    "waffles", "water", "watermelon", "wholemeal toast", "wrap", "yoghurt",
    "yogurt", "zucchini",
}


# Words around a meal that also show the photograph is about food
FOOD_CONTEXT_WORDS = {
    "food",
    "meal",
    "dish",
    "plate",
    "bowl",
    "breakfast",
    "lunch",
    "dinner",
    "takeaway",
    "drink",
    "drinks",
    "beverage",
    "snack",
    "mug",
    "tub",
    "jar",
}


# Every Food-101 dish is accepted as food
FOOD101_DISH_NAMES = {
    "apple pie",
    "baby back ribs",
    "baklava",
    "beef carpaccio",
    "beef tartare",
    "beet salad",
    "beignets",
    "bibimbap",
    "bread pudding",
    "breakfast burrito",
    "bruschetta",
    "caesar salad",
    "cannoli",
    "caprese salad",
    "carrot cake",
    "ceviche",
    "cheese plate",
    "cheesecake",
    "chicken curry",
    "chicken quesadilla",
    "chicken wings",
    "chocolate cake",
    "chocolate mousse",
    "churros",
    "clam chowder",
    "club sandwich",
    "crab cakes",
    "creme brulee",
    "croque madame",
    "cup cakes",
    "deviled eggs",
    "donuts",
    "dumplings",
    "edamame",
    "eggs benedict",
    "escargots",
    "falafel",
    "filet mignon",
    "fish and chips",
    "foie gras",
    "french fries",
    "french onion soup",
    "french toast",
    "fried calamari",
    "fried rice",
    "frozen yogurt",
    "garlic bread",
    "gnocchi",
    "greek salad",
    "grilled cheese sandwich",
    "grilled salmon",
    "guacamole",
    "gyoza",
    "hamburger",
    "hot and sour soup",
    "hot dog",
    "huevos rancheros",
    "hummus",
    "ice cream",
    "lasagna",
    "lobster bisque",
    "lobster roll sandwich",
    "macaroni and cheese",
    "macarons",
    "miso soup",
    "mussels",
    "nachos",
    "omelette",
    "onion rings",
    "oysters",
    "pad thai",
    "paella",
    "pancakes",
    "panna cotta",
    "peking duck",
    "pho",
    "pizza",
    "pork chop",
    "poutine",
    "prime rib",
    "pulled pork sandwich",
    "ramen",
    "ravioli",
    "red velvet cake",
    "risotto",
    "samosa",
    "sashimi",
    "scallops",
    "seaweed salad",
    "shrimp and grits",
    "spaghetti bolognese",
    "spaghetti carbonara",
    "spring rolls",
    "steak",
    "strawberry shortcake",
    "sushi",
    "tacos",
    "takoyaki",
    "tiramisu",
    "tuna tartare",
    "waffles",
}


# Drinks are refused because they do not say much about what the user eats
DRINK_ONLY_WORDS = {
    "water",
    "coffee",
    "black coffee",
    "iced coffee",
    "espresso",
    "latte",
    "cappuccino",
    "tea",
    "green tea",
    "black tea",
    "herbal tea",
    "milk tea",
    "juice",
    "soda",
    "cola",
    "beer",
    "wine",
    "smoothie",
    "milkshake",
    "drink",
    "drinks",
    "beverage",
    "mug",
    "glass",
    "cup",
    "bottle",
    "can",
}


# Keep only letters and numbers so words can be matched on their own
def clean_caption(caption: str) -> str:
    cleaned = re.sub(
        r"[^a-z0-9]+",
        " ",
        caption.lower(),
    )

    return f" {cleaned.strip()} "


def contains_caption_word(
    caption: str,
    words: set[str],
) -> bool:

    cleaned_caption = clean_caption(caption)

    # Check each word and its plural form so one matching word is enough
    for word in words:
        if f" {word} " in cleaned_caption:
            return True

        if f" {word}s " in cleaned_caption:
            return True

        if word.endswith("y") and f" {word[:-1]}ies " in cleaned_caption:
            return True

    return False


# Turn a dish or caption reading into a band using the food lookup table
def calc_band_from_reading(text: str) -> str | None:
    foods, groups = find_foods_and_groups((text or "").replace("_", " "))

    # The reading is shown as not sure when no food in it is in the table
    if not foods:
        return None

    return calc_b3p2_band(groups)


# The food group classifier cannot name a dish so each of its twelve groups has its own band
FOOD_GROUP_BANDS = {
    "Fruit": "mixed",
    "Vegetable": "mixed",
    "Egg": "mixed",
    "Seafood": "mixed",
    "Meat": "mixed",
    "Dairy": "mixed",
    "Bread": "mixed",
    "Noodles": "mixed",
    "Rice": "mixed",
    "Soup": "mixed",
    "Dessert": "poor",
    "Fried Food": "poor",
}


def calc_band_from_food_group(name: str) -> str | None:
    return FOOD_GROUP_BANDS.get((name or "").strip())


# Each food is listed with the nutrition groups it offers based on the HPB guidance
FOOD_LOOKUP_TABLE = {
    # Protein foods
    "chicken": {"protein"}, "turkey": {"protein"}, "beef": {"protein"},
    "pork": {"protein"}, "lamb": {"protein"}, "steak": {"protein"},
    "fish": {"protein"}, "salmon": {"protein"}, "tuna": {"protein"},
    "cod": {"protein"}, "tilapia": {"protein"}, "shrimp": {"protein"},
    "prawn": {"protein"}, "crab": {"protein"}, "egg": {"protein"},
    "tofu": {"protein"}, "tempeh": {"protein"},
    "yogurt": {"protein"}, "yoghurt": {"protein"},
    "cottage cheese": {"protein"},
    "milk": {"protein"}, "soy milk": {"protein"},

    # Protein foods that also bring saturated fat or sodium
    "cheese": {"protein", "satfat"},
    "cheddar": {"protein", "satfat"},
    "mozzarella": {"protein", "satfat"},
    "parmesan": {"protein", "satfat", "sodium"},
    "bacon": {"protein", "satfat", "sodium"},
    "sausage": {"protein", "satfat", "sodium"},
    "ham": {"protein", "sodium"},
    "salami": {"protein", "satfat", "sodium"},
    "pepperoni": {"protein", "satfat", "sodium"},

    # Foods that give both protein and fibre
    "beans": {"protein", "fibre"}, "black beans": {"protein", "fibre"},
    "chickpeas": {"protein", "fibre"}, "lentils": {"protein", "fibre"},
    "hummus": {"protein", "fibre"}, "edamame": {"protein", "fibre"},
    "peanut butter": {"protein", "fibre"},
    "peanuts": {"protein", "fibre"}, "almonds": {"protein", "fibre"},
    "walnuts": {"protein", "fibre"}, "nuts": {"protein", "fibre"},
    "chia": {"protein", "fibre"}, "flax": {"protein", "fibre"},
    "pumpkin seeds": {"protein", "fibre"}, "seeds": {"protein", "fibre"},

    # Vegetables
    "spinach": {"produce", "fibre"}, "kale": {"produce", "fibre"},
    "broccoli": {"produce", "fibre"}, "cabbage": {"produce", "fibre"},
    "carrot": {"produce", "fibre"}, "carrots": {"produce", "fibre"},
    "lettuce": {"produce"}, "romaine": {"produce"},
    "salad greens": {"produce"}, "mixed salad": {"produce"},
    "tomato": {"produce"}, "tomatoes": {"produce"},
    "cucumber": {"produce"}, "onion": {"produce"}, "onions": {"produce"},
    "pepper": {"produce"}, "peppers": {"produce"},
    "mushroom": {"produce"}, "mushrooms": {"produce"},
    "zucchini": {"produce"}, "squash": {"produce"},
    "cauliflower": {"produce", "fibre"}, "asparagus": {"produce"},
    "green beans": {"produce", "fibre"}, "peas": {"produce", "fibre"},
    "corn": {"produce", "fibre"}, "celery": {"produce"},
    "avocado": {"produce", "fibre"}, "salsa": {"produce"},
    "sweet potato": {"produce", "fibre"},
    "potato": {"produce"}, "vegetable": {"produce"},
    "vegetables": {"produce", "fibre"},

    # Fruit
    "banana": {"produce"}, "apple": {"produce", "fibre"},
    "orange": {"produce"}, "berries": {"produce", "fibre"},
    "blueberries": {"produce", "fibre"},
    "strawberries": {"produce", "fibre"},
    "raspberries": {"produce", "fibre"},
    "grapes": {"produce"}, "melon": {"produce"},
    "watermelon": {"produce"}, "mango": {"produce"},
    "pear": {"produce", "fibre"}, "peach": {"produce"},
    "pineapple": {"produce"}, "fruit": {"produce"},

    # Wholegrains
    "oatmeal": {"wholegrain", "fibre"}, "oats": {"wholegrain", "fibre"},
    "granola": {"wholegrain", "fibre"},
    "whole wheat": {"wholegrain", "fibre"},
    "whole grain": {"wholegrain", "fibre"},
    "wholemeal": {"wholegrain", "fibre"},
    "brown rice": {"wholegrain", "fibre"},
    "quinoa": {"wholegrain", "fibre", "protein"},
    "bran": {"wholegrain", "fibre"},
    "cereal": {"wholegrain", "fibre"},
    "shredded wheat": {"wholegrain", "fibre"},

    # Carbs which offer none of the balanced nutrition groups
    "bread": set(), "white bread": set(), "toast": set(),
    "bagel": set(), "roll": set(), "bun": set(), "tortilla": set(),
    "rice": set(), "white rice": set(), "pasta": set(),
    "noodles": set(), "spaghetti": set(), "crackers": set(),
    "pita": set(), "naan": set(), "couscous": set(),

    # Fats and oils
    "butter": {"satfat"}, "cream": {"satfat"},
    "coffee creamer": {"satfat", "sugar"},
    "sour cream": {"satfat"}, "mayonnaise": {"satfat"},
    "coconut milk": {"satfat"},
    "olive oil": set(), "oil": set(),

    # Foods high in saturated fat, sodium or sugar
    "fried": {"satfat"}, "deep fried": {"satfat"},
    "chips": {"satfat", "sodium"}, "fries": {"satfat", "sodium"},
    "crisps": {"satfat", "sodium"},
    "soy sauce": {"sodium"}, "salt": {"sodium"},
    "sugar": {"sugar"}, "syrup": {"sugar"}, "honey": {"sugar"},
    "jam": {"sugar"}, "jelly": {"sugar"},
    "cookie": {"sugar", "satfat"}, "cookies": {"sugar", "satfat"},
    "cake": {"sugar", "satfat"}, "cupcake": {"sugar", "satfat"},
    "brownie": {"sugar", "satfat"}, "pastry": {"sugar", "satfat"},
    "donut": {"sugar", "satfat"}, "doughnut": {"sugar", "satfat"},
    "muffin": {"sugar"}, "ice cream": {"sugar", "satfat"},
    "chocolate": {"sugar", "satfat"}, "candy": {"sugar"},
    "soda": {"sugar"}, "soft drink": {"sugar"},
    "juice": {"sugar"}, "sweetened": {"sugar"},
    "pie": {"sugar", "satfat"}, "pudding": {"sugar"},
    "frosting": {"sugar"}, "icing": {"sugar"},

    # Food-101 dishes that the dish classifier can name
    "baby back ribs": {"protein", "satfat", "sodium"},
    "baklava": {"satfat", "sugar"},
    "beet salad": {"fibre", "produce"},
    "beignet": {"satfat", "sugar"},
    "bibimbap": {"protein", "fibre", "produce"},
    "breakfast burrito": {"protein", "satfat", "sodium"},
    "bruschetta": {"produce"},
    "caesar salad": {"protein", "produce", "satfat"},
    "cannoli": {"satfat", "sugar"},
    "caprese salad": {"protein", "produce", "satfat"},
    "ceviche": {"protein", "produce"},
    "cheesecake": {"satfat", "sugar"},
    "churro": {"satfat", "sugar"},
    "clam chowder": {"protein", "satfat", "sodium"},
    "club sandwich": {"protein", "satfat", "sodium"},
    "creme brulee": {"satfat", "sugar"},
    "croque madame": {"protein", "satfat", "sodium"},
    "dumpling": {"protein", "sodium"},
    "escargot": {"protein", "satfat"},
    "falafel": {"protein", "fibre"},
    "filet mignon": {"protein"},
    "foie gras": {"satfat"},
    "french toast": {"satfat", "sugar"},
    "garlic bread": {"satfat", "sodium"},
    "gnocchi": set(),
    "greek salad": {"protein", "fibre", "produce", "satfat"},
    "guacamole": {"fibre", "produce"},
    "gyoza": {"protein", "sodium"},
    "hamburger": {"protein", "satfat", "sodium"},
    "burger": {"protein", "satfat", "sodium"},
    "hot and sour soup": {"protein", "sodium"},
    "hot dog": {"protein", "satfat", "sodium"},
    "huevos rancheros": {"protein", "fibre", "produce"},
    "lasagna": {"protein", "satfat", "sodium"},
    "lobster bisque": {"protein", "satfat"},
    "lobster roll sandwich": {"protein", "satfat"},
    "macaron": {"sugar"},
    "miso soup": {"protein", "sodium"},
    "mussel": {"protein"},
    "nacho": {"satfat", "sodium"},
    "omelette": {"protein"},
    "oyster": {"protein"},
    "pad thai": {"protein", "sodium", "sugar"},
    "paella": {"protein", "produce"},
    "pancake": {"sugar"},
    "panna cotta": {"satfat", "sugar"},
    "peking duck": {"protein", "satfat", "sodium"},
    "pho": {"protein", "sodium"},
    "pizza": {"protein", "satfat", "sodium"},
    "poutine": {"satfat", "sodium"},
    "prime rib": {"protein", "satfat"},
    "ramen": {"protein", "sodium"},
    "ravioli": {"protein", "satfat"},
    "risotto": {"satfat"},
    "samosa": {"satfat", "sodium"},
    "sashimi": {"protein"},
    "scallop": {"protein"},
    "seaweed salad": {"produce", "sodium"},
    "spaghetti bolognese": {"protein", "produce"},
    "spaghetti carbonara": {"protein", "satfat", "sodium"},
    "spring roll": {"produce", "satfat"},
    "strawberry shortcake": {"produce", "satfat", "sugar"},
    "sushi": {"protein"},
    "taco": {"protein", "produce"},
    "takoyaki": {"protein", "satfat", "sodium"},
    "tiramisu": {"satfat", "sugar"},
    "waffle": {"satfat", "sugar"},

    # Common foods that show up in captions
    "salad": {"produce"},
    "sandwich": {"protein"},
    "meat": {"protein"},
    "burrito": {"protein", "fibre"},
    "soup": set(),
    "popcorn": {"fibre", "wholegrain"},
    "greens": {"fibre", "produce"},
    "lemon": {"produce"},
    "lime": {"produce"},
    "ketchup": {"sodium", "sugar"},
}


# Protein, fibre, produce and wholegrain are counted as balanced
POSITIVE_NUTRITION_GROUPS = {"protein", "fibre", "produce", "wholegrain"}
# Saturated fat, sodium and sugar are counted as poor
POOR_NUTRITION_GROUPS = {"satfat", "sodium", "sugar"}


def find_foods_and_groups(text: str) -> tuple[set, set]:
    lowered = (text or "").lower()
    foods: set = set()
    found: set = set()

    # Check longer foods first so "brown rice" is found before "rice"
    for food in sorted(FOOD_LOOKUP_TABLE, key=len, reverse=True):
        plural = rf"|{re.escape(food[:-1])}ies" if food.endswith("y") else ""

        if re.search(rf"\b(?:{re.escape(food)}(?:s|es)?{plural})\b", lowered):
            foods.add(food)
            found |= FOOD_LOOKUP_TABLE[food]
            # Remove a food once it is found so it is not counted twice
            lowered = lowered.replace(food, " ")

    return foods, found


# This is the B3/P2 rule that places a meal in a band
def calc_b3p2_band(groups: set) -> str:
    num_positive = len(groups & POSITIVE_NUTRITION_GROUPS)
    num_poor = len(groups & POOR_NUTRITION_GROUPS)

    # A meal is only balanced when it brings three balanced groups and zero poor ones
    if num_positive >= 3 and num_poor == 0:
        return "balanced"

    # A meal is poor when it has two poor groups or only one poor group and nothing balanced
    if num_poor >= 2 or (num_poor >= 1 and num_positive == 0):
        return "poor"

    # Any other meal is counted as mixed
    return "mixed"


ALL_FOOD_WORDS = FOOD_WORDS | FOOD_CONTEXT_WORDS | FOOD101_DISH_NAMES


# Use the BLIP caption to check that the photograph shows food
def photo_reject_reason(caption: str) -> str:
    if not contains_caption_word(caption or "", ALL_FOOD_WORDS):
        return "not food"

    # A photograph with only a drink in it is rejected
    if not contains_caption_word(caption, ALL_FOOD_WORDS - DRINK_ONLY_WORDS):
        return "drink"

    return ""
