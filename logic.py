# logic.py
# Handles all the data and calculations for the Chipotle Nutrition Calculator.
# No GUI code here, just the menu, steps, and math.

import csv
import os

# The CSV file that holds all the menu nutrition info
CSV_FILE = "nutrition_info.csv"

# Min and max calories a user can enter as their meal limit
CALORIE_MIN = 100
CALORIE_MAX = 9999

# All the steps for a regular order (bowl, burrito, tacos)
ALL_STEPS = [
    ("base",           "single",       False),
    ("rice",           "single",       True),
    ("beans",          "single",       True),
    ("protein",        "single",       True),
    ("double_protein", "toggle",       False),
    ("veggies",        "multi",        False),
    ("salsa",          "multi",        False),
    ("dairy",          "multi",        False),
    ("extras",         "multi",        False),
    ("calorie_goal",   "calorie_goal", False),
    ("summary",        "summary",      False),
]

# Quesadilla skips most steps — cheese is always included
QUESADILLA_STEPS = [
    ("base",           "single",       False),
    ("protein",        "single",       True),
    ("qesa_veggies",   "qesa_veggies", False),
    ("calorie_goal",   "calorie_goal", False),
    ("summary",        "summary",      False),
]

# What each step shows as its title in the UI
STEP_TITLES = {
    "base":           "Choose your base",
    "rice":           "Choose your rice",
    "beans":          "Choose your beans",
    "protein":        "Choose your protein",
    "double_protein": "Double protein?",
    "veggies":        "Choose your veggies",
    "salsa":          "Choose your salsa",
    "dairy":          "Choose your dairy",
    "extras":         "Choose your extras",
    "qesa_veggies":   "Add fajita veggies?",
    "calorie_goal":   "Set your meal calorie limit",
    "summary":        "Your order summary",
}


def load_menu_from_csv(filepath=CSV_FILE):
    # Reads the nutrition_info.csv and returns a list of item dictionaries.
    # Raises FileNotFoundError if the file is missing,
    # and ValueError if a row has bad data.

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Could not find '{filepath}'. "
            "Make sure nutrition_info.csv is in the same folder as gui.py."
        )

    menu = []
    int_fields = ("calories", "protein", "carbs", "fat")

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            try:
                for field in int_fields:
                    row[field] = int(row[field])
            except (KeyError, ValueError) as e:
                raise ValueError(
                    f"Bad data on line {line_num} of the CSV: {e}"
                ) from e
            menu.append(dict(row))

    return menu


def build_category_index(menu):
    # Groups the menu list into a dict by category.
    # Example: {"base": [...], "rice": [...], ...}

    index = {}
    for item in menu:
        index.setdefault(item["category"], []).append(item)
    return index


def fresh_selections():
    # Returns a blank order — called at startup and when the user resets.

    return {
        "base":           None,
        "rice":           None,
        "beans":          None,
        "protein":        None,
        "double_protein": False,
        "veggies":        [],
        "salsa":          [],
        "dairy":          [],
        "extras":         [],
        "qesa_veggies":   False,
        "calorie_goal":   None,
    }


def is_quesadilla(selections):
    # Returns True if the user picked Quesadilla as their base.

    return selections.get("base") == "Quesadilla"


def active_steps(selections):
    # Returns the right step list depending on what base was chosen.

    if is_quesadilla(selections):
        return QUESADILLA_STEPS
    return ALL_STEPS


def validate_calorie_goal(raw_text):
    # Checks if the calorie limit the user typed is valid.
    # Returns (True, number, "") if good, or (False, None, error message) if bad.

    text = raw_text.strip()

    # Blank is fine — means they skipped the limit
    if text == "":
        return True, None, ""

    # No decimals allowed
    if "." in text:
        return False, None, "Please enter a whole number, not a decimal."

    # Must actually be a number
    try:
        goal = int(text)
    except ValueError:
        return False, None, "Calorie limit must be a number."

    # Check it's in a reasonable range
    if goal < CALORIE_MIN:
        return False, None, f"Calorie limit must be at least {CALORIE_MIN}."
    if goal > CALORIE_MAX:
        return False, None, f"Calorie limit cannot exceed {CALORIE_MAX}."

    return True, goal, ""


def build_order_lines(selections, item_lookup):
    # Figures out which items the user picked and adds up the nutrition totals.
    # Returns a list of (label, category, item_dict) and a totals dict.

    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    order_lines = []

    def add_item(item, mult=1):
        # Adds one item's macros to the running totals
        for key in totals:
            totals[key] += item[key] * mult

    if is_quesadilla(selections):
        # Quesadilla always has the shell + cheese
        base_item = item_lookup["Quesadilla"]
        order_lines.append(("Quesadilla", "base", base_item))
        add_item(base_item)

        cheese = item_lookup["Cheese"]
        order_lines.append(("Cheese (included)", "dairy", cheese))
        add_item(cheese)

        # Optional protein
        if selections["protein"]:
            it = item_lookup[selections["protein"]]
            order_lines.append((selections["protein"], "protein", it))
            add_item(it)

        # Optional fajita veggies
        if selections["qesa_veggies"]:
            veg = item_lookup["Fajita Veggies"]
            order_lines.append(("Fajita Veggies", "veggies", veg))
            add_item(veg)

    else:
        # Regular build — bowl, burrito, tacos
        for cat in ("base", "rice", "beans"):
            name = selections[cat]
            if name:
                it = item_lookup[name]
                order_lines.append((name, cat, it))
                add_item(it)

        if selections["protein"]:
            it = item_lookup[selections["protein"]]
            mult = 2 if selections["double_protein"] else 1
            label = selections["protein"] + (" (x2)" if mult == 2 else "")
            order_lines.append((label, "protein", it))
            add_item(it, mult)

        for cat in ("veggies", "salsa", "dairy", "extras"):
            for name in selections[cat]:
                it = item_lookup[name]
                order_lines.append((name, cat, it))
                add_item(it)

    return order_lines, totals


# The file where past orders get saved
ORDER_HISTORY_FILE = "order_history.csv"

# These are the fields we save to the CSV — one row per order
HISTORY_FIELDS = [
    "date", "base", "rice", "beans", "protein",
    "double_protein", "veggies", "salsa", "dairy", "extras",
    "qesa_veggies", "calorie_goal",
    "total_calories", "total_protein", "total_carbs", "total_fat"
]


def save_order_to_csv(selections, item_lookup):
    # Saves the current order to order_history.csv.
    # If the file doesn't exist yet it creates it with a header row.
    # Multi-select fields (veggies, salsa, dairy, extras) are stored
    # as pipe-separated strings like "Tomato Salsa|Corn Salsa".

    import datetime

    _, totals = build_order_lines(selections, item_lookup)

    # Join list fields into a single string so they fit in one CSV cell
    def join_list(lst):
        return "|".join(lst) if lst else ""

    row = {
        "date":           datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "base":           selections["base"] or "",
        "rice":           selections["rice"] or "",
        "beans":          selections["beans"] or "",
        "protein":        selections["protein"] or "",
        "double_protein": selections["double_protein"],
        "veggies":        join_list(selections["veggies"]),
        "salsa":          join_list(selections["salsa"]),
        "dairy":          join_list(selections["dairy"]),
        "extras":         join_list(selections["extras"]),
        "qesa_veggies":   selections["qesa_veggies"],
        "calorie_goal":   selections["calorie_goal"] if selections["calorie_goal"] else "",
        "total_calories": totals["calories"],
        "total_protein":  totals["protein"],
        "total_carbs":    totals["carbs"],
        "total_fat":      totals["fat"],
    }

    file_exists = os.path.exists(ORDER_HISTORY_FILE)

    try:
        with open(ORDER_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except OSError as e:
        raise OSError(f"Could not save order history: {e}") from e


def load_last_order():
    # Reads order_history.csv and returns the last saved order
    # as a selections dict, or None if the file doesn't exist or is empty.

    if not os.path.exists(ORDER_HISTORY_FILE):
        return None

    try:
        with open(ORDER_HISTORY_FILE, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None

    if not rows:
        return None

    last = rows[-1]

    # Helper to split a pipe-separated string back into a list
    def split_list(val):
        if not val:
            return []
        return val.split("|")

    # Helper to convert "True"/"False" strings back to booleans
    def to_bool(val):
        return val.strip().lower() == "true"

    selections = fresh_selections()
    selections["base"]           = last["base"] or None
    selections["rice"]           = last["rice"] or None
    selections["beans"]          = last["beans"] or None
    selections["protein"]        = last["protein"] or None
    selections["double_protein"] = to_bool(last["double_protein"])
    selections["veggies"]        = split_list(last["veggies"])
    selections["salsa"]          = split_list(last["salsa"])
    selections["dairy"]          = split_list(last["dairy"])
    selections["extras"]         = split_list(last["extras"])
    selections["qesa_veggies"]   = to_bool(last["qesa_veggies"])

    # Calorie goal is optional — could be blank
    cal = last.get("calorie_goal", "").strip()
    selections["calorie_goal"]   = int(cal) if cal else None

    return selections