"""
logic.py
--------
All business logic for the Chipotle Nutrition Calculator.
Handles menu data loading from CSV, step definitions, selection state,
calorie-goal validation, and nutrition totals calculation.

No tkinter imports — this module is completely GUI-independent.
"""

import csv
import os
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

CSV_FILE = "nutrition_info.csv"

# Calorie-goal bounds for keyboard input validation
CALORIE_GOAL_MIN = 100
CALORIE_GOAL_MAX = 9999

# ── Step definitions ──────────────────────────────────────────────────────────
# Each step is a tuple: (step_id, kind, allow_none)
#   step_id    — key used in the selections dict and in STEP_TITLES
#   kind       — "single" | "multi" | "toggle" | "qesa_veggies" |
#                "calorie_goal" | "summary"
#   allow_none — only used by "single" steps; adds a "None / skip" option

ALL_STEPS: list[tuple[str, str, bool]] = [
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

# Quesadillas skip rice, beans, salsa, dairy, extras, and double-protein.
# Cheese is always included. Only protein (optional) and fajita veggies (yes/no).
QUESADILLA_STEPS: list[tuple[str, str, bool]] = [
    ("base",           "single",       False),
    ("protein",        "single",       True),
    ("qesa_veggies",   "qesa_veggies", False),
    ("calorie_goal",   "calorie_goal", False),
    ("summary",        "summary",      False),
]

STEP_TITLES: dict[str, str] = {
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


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_menu_from_csv(filepath: str = CSV_FILE) -> list[dict[str, Any]]:
    """
    Load menu items from a CSV file and return them as a list of dicts.

    Each row is expected to have the columns:
        item_name, category, portion, calories, protein, carbs, fat

    The numeric columns (calories, protein, carbs, fat) are cast to int.

    Parameters
    ----------
    filepath : str
        Path to the CSV file. Defaults to ``nutrition_info.csv`` in the
        current working directory.

    Returns
    -------
    list[dict[str, Any]]
        List of item dicts with string and integer fields.

    Raises
    ------
    FileNotFoundError
        Re-raised with a friendly message when the CSV is missing.
    ValueError
        Raised when a numeric field cannot be parsed as an integer.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Menu file '{filepath}' not found. "
            "Make sure nutrition_info.csv is in the same folder as this script."
        )

    menu: list[dict[str, Any]] = []
    int_fields = ("calories", "protein", "carbs", "fat")

    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for line_num, row in enumerate(reader, start=2):   # start=2: row 1 is header
            try:
                for field in int_fields:
                    row[field] = int(row[field])            # type: ignore[arg-type]
            except (KeyError, ValueError) as exc:
                raise ValueError(
                    f"Could not parse numeric field on CSV line {line_num}: {exc}"
                ) from exc
            menu.append(dict(row))

    return menu


# ── Category index ────────────────────────────────────────────────────────────

def build_category_index(
    data: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """
    Group a flat list of menu-item dicts by their ``category`` field.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Flat list of menu items as returned by :func:`load_menu_from_csv`.

    Returns
    -------
    dict[str, list[dict[str, Any]]]
        Mapping of ``category`` -> list of item dicts in insertion order.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for item in data:
        index.setdefault(item["category"], []).append(item)
    return index


# ── Selection state ───────────────────────────────────────────────────────────

def fresh_selections() -> dict[str, Any]:
    """
    Return a blank selections dict representing an empty order.

    Returns
    -------
    dict[str, Any]
        Keys and their default values:

        * ``base`` / ``rice`` / ``beans`` / ``protein`` → ``None``
        * ``double_protein`` / ``qesa_veggies`` → ``False``
        * ``veggies`` / ``salsa`` / ``dairy`` / ``extras`` → ``[]``
        * ``calorie_goal`` → ``None``  (no goal set)
    """
    return {
        "base":           None,   # str item name or None
        "rice":           None,
        "beans":          None,
        "protein":        None,
        "double_protein": False,  # bool
        "veggies":        [],     # list of str item names
        "salsa":          [],
        "dairy":          [],
        "extras":         [],
        "qesa_veggies":   False,  # bool — fajita veggies inside quesadilla
        "calorie_goal":   None,   # int or None — user-entered daily calorie goal
    }


# ── Calorie-goal validation ───────────────────────────────────────────────────

def validate_calorie_goal(raw: str) -> tuple[bool, int | None, str]:
    """
    Validate a raw string calorie-goal value entered via the keyboard.

    Accepts an empty string (goal cleared / skipped).
    Rejects non-numeric input, decimals, and values outside
    :data:`CALORIE_GOAL_MIN` – :data:`CALORIE_GOAL_MAX`.

    Parameters
    ----------
    raw : str
        The raw text from the Entry widget (may include spaces).

    Returns
    -------
    tuple[bool, int | None, str]
        * ``(True,  goal_int, "")``  — valid; ``goal_int`` is the parsed int
          or ``None`` when the field was left blank.
        * ``(False, None,     error_message)`` — invalid; show ``error_message``
          to the user.
    """
    text = raw.strip()

    # Blank input is allowed — means "no goal"
    if text == "":
        return True, None, ""

    # Must be a plain integer (no decimal point)
    if "." in text:
        return False, None, "Please enter a whole number, not a decimal."

    try:
        goal = int(text)
    except ValueError:
        return False, None, "Calorie goal must be a number."

    if goal < CALORIE_GOAL_MIN:
        return False, None, f"Calorie goal must be at least {CALORIE_GOAL_MIN}."
    if goal > CALORIE_GOAL_MAX:
        return False, None, f"Calorie goal cannot exceed {CALORIE_GOAL_MAX}."

    return True, goal, ""


# ── Step routing ──────────────────────────────────────────────────────────────

def is_quesadilla(selections: dict[str, Any]) -> bool:
    """
    Return ``True`` when the user has selected a Quesadilla base.

    Parameters
    ----------
    selections : dict[str, Any]
        Current selections dict (as returned by :func:`fresh_selections`).
    """
    return selections.get("base") == "Quesadilla"


def active_steps(selections: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """
    Return the appropriate step list based on the chosen base.

    Parameters
    ----------
    selections : dict[str, Any]
        Current selections dict.

    Returns
    -------
    list[tuple[str, str, bool]]
        :data:`QUESADILLA_STEPS` when the base is Quesadilla,
        otherwise :data:`ALL_STEPS`.
    """
    return QUESADILLA_STEPS if is_quesadilla(selections) else ALL_STEPS


# ── Nutrition calculation ─────────────────────────────────────────────────────

def build_order_lines(
    selections: dict[str, Any],
    item_lookup: dict[str, dict[str, Any]],
) -> tuple[list[tuple[str, str, dict[str, Any]]], dict[str, int]]:
    """
    Build the ordered list of items and compute nutrition totals.

    Parameters
    ----------
    selections : dict[str, Any]
        Current selections dict (from :func:`fresh_selections`).
    item_lookup : dict[str, dict[str, Any]]
        Mapping of ``item_name`` -> item dict, built from the menu data.

    Returns
    -------
    tuple[list[tuple[str, str, dict[str, Any]]], dict[str, int]]
        * ``order_lines`` — list of ``(display_label, category_tag, item_dict)``
          in the order they should appear in the summary.
        * ``totals`` — dict with keys ``calories``, ``protein``, ``carbs``,
          ``fat``, each an integer sum across all selected items.
    """
    totals: dict[str, int] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    order_lines: list[tuple[str, str, dict[str, Any]]] = []

    def _add(item: dict[str, Any], mult: int = 1) -> None:
        """Add one item's macros to the running totals, scaled by mult."""
        for key in totals:
            totals[key] += item[key] * mult

    if is_quesadilla(selections):
        # Quesadilla shell
        base_item = item_lookup["Quesadilla"]
        order_lines.append(("Quesadilla", "base", base_item))
        _add(base_item)

        # Cheese is always included in every quesadilla
        cheese = item_lookup["Cheese"]
        order_lines.append(("Cheese (included)", "dairy", cheese))
        _add(cheese)

        # Optional protein
        if selections["protein"]:
            it = item_lookup[selections["protein"]]
            order_lines.append((selections["protein"], "protein", it))
            _add(it)

        # Optional fajita veggies
        if selections["qesa_veggies"]:
            veg = item_lookup["Fajita Veggies"]
            order_lines.append(("Fajita Veggies", "veggies", veg))
            _add(veg)

    else:
        # Standard bowl / burrito / taco build
        for cat in ("base", "rice", "beans"):
            name = selections[cat]
            if name:
                it = item_lookup[name]
                order_lines.append((name, cat, it))
                _add(it)

        if selections["protein"]:
            it = item_lookup[selections["protein"]]
            mult = 2 if selections["double_protein"] else 1
            label = selections["protein"] + (" (×2)" if mult == 2 else "")
            order_lines.append((label, "protein", it))
            _add(it, mult)

        for cat in ("veggies", "salsa", "dairy", "extras"):
            for name in selections[cat]:
                it = item_lookup[name]
                order_lines.append((name, cat, it))
                _add(it)

    return order_lines, totals