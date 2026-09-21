# Turn food names into the 12 shared food groups so the seven food models can be compared
import re

# The words that belong to each of the 12 shared food groups
SHARED_FOOD_GROUP_WORDS = {
    "Bread": [
        "bread", "toast", "bun", "loaf", "baguette", "roll", "croissant",
        "bagel", "brioche", "pita", "naan", "scone", "muffin", "pancake",
        "waffle", "tortilla", "focaccia", "sourdough", "crumpet",
        "chapati", "roti", "biscuit, baking powder",
    ],
    "Dairy": [
        "dairy", "milk", "cheese", "yoghurt", "yogurt", "butter", "cream",
        "cheddar", "mozzarella", "brie", "parmesan", "custard", "latte",
        "paneer",
    ],
    "Dessert": [
        "dessert", "cake", "ice cream", "pudding", "pie", "tart", "sweet",
        "chocolate", "cookie", "donut", "doughnut", "pastry", "brownie",
        "cupcake", "macaron", "mousse", "tiramisu", "gelato", "candy",
        "sundae", "cheesecake", "baklava", "eclair", "trifle", "sorbet",
        "parfait", "churro", "toffee", "caramel", "icing", "jalebi",
        "kulfi", "beignet", "cannoli", "creme brulee", "panna cotta",
        "shortcake", "frozen yogurt",
    ],
    "Egg": [
        "egg", "omelette", "omelet", "scrambled", "frittata", "quiche",
        "benedict", "deviled", "huevos",
    ],
    "Fried Food": [
        "fried", "fries", "crisps", "tempura", "nugget", "croquette",
        "fritter", "cutlet", "katsu", "onion ring", "samosa", "falafel",
        "hush pupp", "calamari", "schnitzel", "pakode", "poutine",
        "spring roll", "bhature",
    ],
    "Fruit": [
        "fruit", "apple", "banana", "orange", "berry", "berries",
        "strawberr", "grape", "melon", "mango", "pear", "peach",
        "pineapple", "lemon", "lime", "cherry", "plum", "kiwi", "papaya",
        "watermelon", "citrus", "apricot", "fig", "date", "raisin",
    ],
    "Meat": [
        "meat", "beef", "chicken", "pork", "lamb", "steak", "sausage",
        "bacon", "rib", "ham", "turkey", "duck", "mutton", "brisket",
        "meatball", "kebab", "satay", "burger", "hamburger", "bulgogi",
        "pastrami", "salami", "prosciutto", "hot dog", "carpaccio",
        "tartare", "filet mignon", "foie gras", "prime rib", "pulled",
    ],
    "Noodles": [
        "noodle", "pasta", "spaghetti", "macaroni", "ramen", "udon",
        "lasagna", "lasagne", "penne", "fettuccine", "linguine",
        "carbonara", "bolognese", "ravioli", "gnocchi", "pad thai",
        "pho", "soba", "vermicelli", "laksa", "mee", "chow mein",
    ],
    "Rice": [
        "rice", "risotto", "paella", "pilaf", "biryani", "sushi",
        "onigiri", "congee", "jambalaya", "nasi", "bibimbap", "idli",
        "dosa",
    ],
    "Seafood": [
        "seafood", "fish", "prawn", "shrimp", "salmon", "tuna", "crab",
        "lobster", "oyster", "squid", "scallop", "mussel", "clam",
        "sardine", "cod", "anchovy", "octopus", "caviar", "ceviche",
        "sashimi", "eel", "mackerel", "trout", "halibut", "escargot",
        "takoyaki",
    ],
    "Soup": [
        "soup", "broth", "stew", "bisque", "chowder", "consomme",
        "minestrone", "gazpacho", "curry", "dal", "chili",
    ],
    "Vegetable": [
        "vegetable", "salad", "greens", "tomato", "carrot", "broccoli",
        "lettuce", "cucumber", "spinach", "kale", "pepper", "onion",
        "potato", "corn", "bean", "pea", "cabbage", "mushroom",
        "asparagus", "beet", "squash", "guacamole", "edamame",
        "caprese", "coleslaw", "hummus", "leek", "seaweed", "bruschetta",
        "celery", "zucchini", "cauliflower",
    ],
}


# A food name can belong to more than one group
def find_shared_food_groups(text: str) -> set:
    lowered = (text or "").lower().replace("_", " ")
    found = set()

    for food_group, words in SHARED_FOOD_GROUP_WORDS.items():
        for word in words:
            if re.search(rf"\b{re.escape(word)}", lowered):
                found.add(food_group)
                break

    return found
