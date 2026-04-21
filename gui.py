"""
gui.py
------
Tkinter GUI for the Chipotle Nutrition Calculator.

All data loading, step definitions, validation, and nutrition logic
live in ``logic.py``.  This file is the entry point — run it directly
to launch the application.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

from logic import (
    STEP_TITLES,
    CALORIE_GOAL_MIN,
    CALORIE_GOAL_MAX,
    load_menu_from_csv,
    build_category_index,
    fresh_selections,
    active_steps,
    is_quesadilla,
    build_order_lines,
    validate_calorie_goal,
)

# ── Theme constants ───────────────────────────────────────────────────────────
BG            = "#F5F0EB"   # warm off-white page background
CARD_BG       = "#FFFFFF"   # card surface
ACCENT        = "#D85A30"   # chipotle orange-red
ACCENT_DARK   = "#993C1D"
BROWN         = "#4A2C1A"   # chipotle dark brown — nav buttons
BROWN_DARK    = "#2E1A0E"   # darker brown for hover
TEXT_PRI      = "#1C1916"   # primary text
TEXT_SEC      = "#6B635C"   # muted / secondary text
SEL_BG        = "#FAECE7"   # selected-row tint
BORDER        = "#E0D9D2"   # card border
BTN_DANGER    = "#FFFFFF"   # reset button text (white on red)
BTN_DANGER_BG = "#A32D2D"   # reset button background (dark red)
COLOR_GOOD    = "#3B6D11"   # calorie-goal under-budget indicator
COLOR_WARN    = "#A32D2D"   # calorie-goal over-budget indicator

COLOR_CALORIES = ACCENT
COLOR_PROTEIN  = "#185FA5"
COLOR_CARBS    = "#3B6D11"
COLOR_FAT      = "#854F0B"


class ChipotleApp:
    """
    Main application window for the Chipotle Nutrition Calculator.

    Manages the multi-step wizard UI, delegates all data and logic
    operations to ``logic.py``, and owns the tkinter root window.
    """

    def __init__(self, root: tk.Tk, menu_data: list[dict[str, Any]]) -> None:
        """
        Initialise the application.

        Parameters
        ----------
        root : tk.Tk
            The tkinter root window.
        menu_data : list[dict[str, Any]]
            Menu items loaded from the CSV file (via :func:`logic.load_menu_from_csv`).
        """
        self.root = root
        self.root.title("Chipotle Nutrition Calculator")
        self.root.geometry("600x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Build fast-lookup structures from the loaded menu data
        self.menu_data   = menu_data
        self.categories  = build_category_index(menu_data)
        self.item_lookup = {it["item_name"]: it for it in menu_data}

        # Persistent tk variables — created once and reused across step redraws
        self._single_var    = tk.StringVar()   # radio selection for single-choice steps
        self._double_var    = tk.BooleanVar()  # double-protein checkbox
        self._qesa_veg_var  = tk.BooleanVar()  # fajita veggies yes/no (quesadilla)
        self._calorie_var   = tk.StringVar()   # raw text from calorie-goal Entry
        self._multi_vars: dict[str, tk.BooleanVar] = {}   # rebuilt each multi step
        self._single_step: str | None = None              # category owned by _single_var

        self.selections: dict[str, Any] = fresh_selections()
        self.current_step: int = 0

        self._build_skeleton()
        self._show_step()

    # ── Static skeleton ───────────────────────────────────────────────────────

    def _build_skeleton(self) -> None:
        """
        Build the parts of the window that never change between steps:
        the header banner, progress bar, step label, scrollable content
        canvas, and the bottom navigation bar (Reset / Back / Next).
        """
        # Header banner
        hdr = tk.Frame(self.root, bg=ACCENT, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Chipotle Nutrition Calculator",
                 font=("Helvetica", 17, "bold"),
                 bg=ACCENT, fg="white").pack()
        tk.Label(hdr, text="Build your meal · track your macros",
                 font=("Helvetica", 10), bg=ACCENT, fg="#FAECE7").pack(pady=(2, 0))

        # Thin progress bar
        self.prog_canvas = tk.Canvas(self.root, height=5, bg=BORDER,
                                     highlightthickness=0, bd=0)
        self.prog_canvas.pack(fill="x")
        self.prog_fill = self.prog_canvas.create_rectangle(
            0, 0, 0, 5, fill=ACCENT, outline="")

        # Step counter label
        self.step_lbl = tk.Label(self.root, text="",
                                  font=("Helvetica", 11),
                                  bg=BG, fg=TEXT_SEC, pady=7)
        self.step_lbl.pack()

        # Scrollable content canvas + vertical scrollbar
        self.scroll_canvas = tk.Canvas(self.root, bg=BG,
                                        highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(self.root, orient="vertical",
                            command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.scroll_canvas.pack(fill="both", expand=True)

        self.content = tk.Frame(self.scroll_canvas, bg=BG)
        self._cwin = self.scroll_canvas.create_window(
            (0, 0), window=self.content, anchor="nw")

        self.content.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.itemconfig(
                self._cwin, width=e.width))
        self.scroll_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.scroll_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"))

        # Bottom navigation bar
        nav = tk.Frame(self.root, bg=BG, pady=9)
        nav.pack(fill="x", padx=18)
        nav.columnconfigure(1, weight=1)

        self.reset_btn = tk.Button(
            nav, text="Reset", font=("Helvetica", 11, "bold"), width=8,
            bg=BTN_DANGER_BG, fg=BTN_DANGER,
            activebackground="#7A1E1E", activeforeground="white",
            disabledforeground="#E8A0A0",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self._reset_all)
        self.reset_btn.grid(row=0, column=0)

        right = tk.Frame(nav, bg=BG)
        right.grid(row=0, column=2, sticky="e")

        self.back_btn = tk.Button(
            right, text="← Back", font=("Helvetica", 11, "bold"), width=9,
            bg=BROWN, fg="white",
            activebackground=BROWN_DARK, activeforeground="white",
            disabledforeground="#A07860",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self._go_back)
        self.back_btn.pack(side="left", padx=(0, 6))

        self.next_btn = tk.Button(
            right, text="Next →", font=("Helvetica", 11, "bold"), width=11,
            bg=ACCENT, fg="white",
            activebackground=ACCENT_DARK, activeforeground="white",
            disabledforeground="#F5C9B8",
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self._go_next)
        self.next_btn.pack(side="left")

    # ── Step rendering ────────────────────────────────────────────────────────

    def _clear(self) -> None:
        """Destroy all widgets inside the scrollable content frame."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def _show_step(self) -> None:
        """
        Clear the content area and render the current wizard step.

        Updates the progress bar and step-counter label, then dispatches
        to the appropriate renderer based on the step's ``kind`` field.
        """
        self._clear()

        steps = active_steps(self.selections)
        step_id, kind, allow_none = steps[self.current_step]
        total = len(steps)

        # Update the progress bar fill
        self.prog_canvas.update_idletasks()
        pw = self.prog_canvas.winfo_width()
        pct = self.current_step / (total - 1)
        self.prog_canvas.coords(self.prog_fill, 0, 0, int(pw * pct), 5)

        self.step_lbl.config(
            text=f"Step {self.current_step + 1} of {total}"
                 f"  ·  {STEP_TITLES[step_id]}")

        # Dispatch to the matching renderer
        if kind == "single":
            self._render_single(step_id, allow_none)
        elif kind == "toggle":
            self._render_toggle()
        elif kind == "multi":
            self._render_multi(step_id)
        elif kind == "qesa_veggies":
            self._render_qesa_veggies()
        elif kind == "calorie_goal":
            self._render_calorie_goal()
        elif kind == "summary":
            self._render_summary()

        self._update_nav()
        self.scroll_canvas.yview_moveto(0)

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _make_card(self, parent: tk.Widget, title: str | None = None) -> tk.Frame:
        """
        Create a white bordered card frame inside ``parent``.

        Parameters
        ----------
        parent : tk.Widget
            The frame to pack the card into.
        title : str or None
            Optional bold title rendered at the top of the card with a
            separator line below it.

        Returns
        -------
        tk.Frame
            The inner card frame, ready for child widgets.
        """
        outer = tk.Frame(parent, bg=BG, padx=16, pady=8)
        outer.pack(fill="x")
        card = tk.Frame(outer, bg=CARD_BG,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=BORDER)
        card.pack(fill="x")
        if title:
            tk.Label(card, text=title, font=("Helvetica", 12, "bold"),
                     bg=CARD_BG, fg=TEXT_PRI, anchor="w",
                     padx=14, pady=10).pack(fill="x")
            tk.Frame(card, bg=BORDER, height=1).pack(fill="x")
        return card

    def _recolor_widgets(self, container: tk.Widget, bg: str) -> None:
        """
        Recursively set the background color of a widget and all descendants.

        Parameters
        ----------
        container : tk.Widget
            The root widget of the subtree to recolor.
        bg : str
            Hex color string to apply.
        """
        try:
            container.configure(bg=bg)
        except tk.TclError:
            pass
        for child in container.winfo_children():
            self._recolor_widgets(child, bg)

    def _make_option_row(
        self,
        card: tk.Frame,
        label: str,
        sublabel: str,
        is_selected: bool,
        make_control: Callable[[tk.Frame], tk.Widget],
    ) -> tuple[tk.Frame, tk.Frame, tk.Frame]:
        """
        Build one selectable row inside a card.

        The control widget (Radiobutton or Checkbutton) is created by
        calling ``make_control(inner_frame)``, which guarantees it is
        parented to the correct frame from the start — avoiding tkinter's
        inability to reparent widgets after creation.

        Parameters
        ----------
        card : tk.Frame
            The card frame to append the row to.
        label : str
            Primary label text shown to the right of the control.
        sublabel : str
            Secondary info (e.g. calories / portion) shown on the right edge.
            Pass an empty string to omit.
        is_selected : bool
            Whether to render the row in the selected (highlighted) state.
        make_control : Callable[[tk.Frame], tk.Widget]
            Factory that receives the ``inner`` frame and returns a
            fully configured Radiobutton or Checkbutton parented to it.

        Returns
        -------
        tuple[tk.Frame, tk.Frame, tk.Frame]
            ``(row_frame, accent_bar, inner_frame)`` — used by the caller
            to bind click events and recolor on selection changes.
        """
        bg = SEL_BG if is_selected else CARD_BG

        row = tk.Frame(card, bg=bg, cursor="hand2")
        row.pack(fill="x")

        accent = tk.Frame(row, bg=ACCENT if is_selected else CARD_BG, width=4)
        accent.pack(side="left", fill="y")

        inner = tk.Frame(row, bg=bg, padx=10, pady=9)
        inner.pack(side="left", fill="x", expand=True)

        # Control widget created here with ``inner`` as its parent
        ctrl = make_control(inner)
        ctrl.pack(side="left", padx=(0, 6))

        tk.Label(inner, text=label, font=("Helvetica", 11),
                 bg=bg, fg=TEXT_PRI, anchor="w").pack(side="left")

        if sublabel:
            tk.Label(inner, text=sublabel, font=("Helvetica", 10),
                     bg=bg, fg=TEXT_SEC).pack(side="right", padx=6)

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x")

        return row, accent, inner

    # ── Step renderers ────────────────────────────────────────────────────────

    def _render_single(self, step_id: str, allow_none: bool) -> None:
        """
        Render a radio-button single-choice step.

        Restores the previously saved selection (if any), then builds one
        option row per menu item in the given category. Clicking a row or
        its radio button updates ``_single_var`` and recolors all rows.

        Parameters
        ----------
        step_id : str
            The category key (e.g. ``"base"``, ``"protein"``).
        allow_none : bool
            When ``True``, a "None" option is prepended so the user can
            skip this ingredient.
        """
        self._single_step = step_id
        items = self.categories.get(step_id, [])

        saved = self.selections[step_id]
        init_val = (saved if saved is not None
                    else ("__none__" if allow_none
                          else (items[0]["item_name"] if items else "")))
        self._single_var.set(init_val)

        card     = self._make_card(self.content)
        row_meta: dict[str, tuple[tk.Frame, tk.Frame]] = {}

        def _select(val: str) -> None:
            """Update the radio variable and recolor all rows."""
            self._single_var.set(val)
            for v, (rf, ab) in row_meta.items():
                sel = (v == val)
                self._recolor_widgets(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def _add_row(val: str, label: str, sublabel: str) -> None:
            """Build and register one radio option row."""
            sel = (val == init_val)

            def make_ctrl(inner: tk.Frame) -> tk.Radiobutton:
                return tk.Radiobutton(
                    inner,
                    variable=self._single_var,
                    value=val,
                    bg=SEL_BG if sel else CARD_BG,
                    activebackground=SEL_BG if sel else CARD_BG,
                    highlightthickness=0,
                    command=lambda v=val: _select(v))

            rf, ab, inner_f = self._make_option_row(
                card, label, sublabel, sel, make_ctrl)
            row_meta[val] = (rf, ab)

            for w in (rf, inner_f, ab):
                w.bind("<Button-1>", lambda e, v=val: _select(v))

        if allow_none:
            _add_row("__none__", "None", "")
        for it in items:
            sub = (f"{it['calories']} cal  ·  {it['portion']}"
                   if it["calories"] > 0 else it["portion"])
            _add_row(it["item_name"], it["item_name"], sub)

    def _render_toggle(self) -> None:
        """
        Render the double-protein toggle step.

        Shows a single checkbox. If no protein has been selected the note
        below the checkbox warns the user the option has no effect.
        """
        self._double_var.set(self.selections["double_protein"])

        card  = self._make_card(self.content, title="Double protein?")
        inner = tk.Frame(card, bg=CARD_BG, padx=14, pady=14)
        inner.pack(fill="x")

        tk.Checkbutton(inner,
                        text="Yes — double my protein",
                        variable=self._double_var,
                        font=("Helvetica", 12),
                        bg=CARD_BG, fg=TEXT_PRI,
                        activebackground=CARD_BG,
                        selectcolor=CARD_BG,
                        cursor="hand2").pack(anchor="w")

        note = ("Doubles calories, protein, carbs and fat for your protein choice."
                if self.selections["protein"]
                else "No protein selected — this option has no effect.")
        tk.Label(card, text=note, font=("Helvetica", 10),
                 bg=CARD_BG, fg=TEXT_SEC, padx=14, pady=6,
                 wraplength=480, justify="left").pack(anchor="w")

    def _render_multi(self, step_id: str) -> None:
        """
        Render a checkbox multi-select step.

        Each item can be toggled independently. Selection state is saved
        immediately into ``self.selections[step_id]`` on every toggle so
        no explicit save is needed when navigating away.

        Parameters
        ----------
        step_id : str
            The category key (e.g. ``"salsa"``, ``"extras"``).
        """
        self._multi_vars = {}
        items = self.categories.get(step_id, [])
        card  = self._make_card(self.content)

        if not items:
            tk.Label(card, text="No items available.",
                     font=("Helvetica", 11),
                     bg=CARD_BG, fg=TEXT_SEC, pady=12).pack()
            return

        row_meta: dict[str, tuple[tk.Frame, tk.Frame]] = {}

        def _recolor_all() -> None:
            """Recolor all rows to reflect the current checkbox states."""
            for nm, (rf, ab) in row_meta.items():
                sel = self._multi_vars[nm].get()
                self._recolor_widgets(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def _toggle(name: str) -> None:
            """Add or remove ``name`` from the selections list and recolor."""
            var = self._multi_vars[name]
            if var.get():
                if name not in self.selections[step_id]:
                    self.selections[step_id].append(name)
            else:
                self.selections[step_id] = [
                    n for n in self.selections[step_id] if n != name]
            _recolor_all()

        for it in items:
            name    = it["item_name"]
            checked = name in self.selections[step_id]
            var     = tk.BooleanVar(value=checked)
            self._multi_vars[name] = var

            sub = (f"{it['calories']} cal  ·  {it['portion']}"
                   if it["calories"] > 0 else it["portion"])

            def make_ctrl(inner: tk.Frame, n: str = name, v: tk.BooleanVar = var) -> tk.Checkbutton:
                return tk.Checkbutton(
                    inner,
                    variable=v,
                    bg=SEL_BG if v.get() else CARD_BG,
                    activebackground=SEL_BG if v.get() else CARD_BG,
                    selectcolor=CARD_BG,
                    highlightthickness=0,
                    cursor="hand2",
                    command=lambda nm=n: _toggle(nm))

            rf, ab, inner_f = self._make_option_row(
                card, name, sub, checked, make_ctrl)
            row_meta[name] = (rf, ab)

            for w in (rf, inner_f, ab):
                w.bind("<Button-1>", lambda e, n=name, v=var: (
                    v.set(not v.get()), _toggle(n)))

    def _render_qesa_veggies(self) -> None:
        """
        Render the quesadilla-specific fajita-veggies yes/no step.

        Presents two radio options (No / Yes) and saves the result into
        ``self.selections["qesa_veggies"]`` immediately on selection.
        """
        self._qesa_veg_var.set(self.selections["qesa_veggies"])

        card = self._make_card(self.content, title="Add fajita veggies?")

        note_f = tk.Frame(card, bg=CARD_BG, padx=14, pady=6)
        note_f.pack(fill="x")
        tk.Label(note_f,
                 text="Your quesadilla already includes cheese. "
                      "Would you like fajita veggies added inside?",
                 font=("Helvetica", 10), bg=CARD_BG, fg=TEXT_SEC,
                 wraplength=480, justify="left").pack(anchor="w")

        row_meta: dict[bool, tuple[tk.Frame, tk.Frame]] = {}

        def _pick(val: bool) -> None:
            """Set the fajita-veggies var and recolor all rows."""
            self._qesa_veg_var.set(val)
            for v, (rf, ab) in row_meta.items():
                sel = (v == val)
                self._recolor_widgets(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def _add_row(val: bool, label: str, sublabel: str) -> None:
            """Build and register one yes/no radio row."""
            sel = (val == self._qesa_veg_var.get())

            def make_ctrl(inner: tk.Frame, v: bool = val) -> tk.Radiobutton:
                return tk.Radiobutton(
                    inner,
                    variable=self._qesa_veg_var,
                    value=v,
                    bg=SEL_BG if sel else CARD_BG,
                    activebackground=SEL_BG if sel else CARD_BG,
                    highlightthickness=0,
                    command=lambda vv=v: _pick(vv))

            rf, ab, inner_f = self._make_option_row(
                card, label, sublabel, sel, make_ctrl)
            row_meta[val] = (rf, ab)

            for w in (rf, inner_f, ab):
                w.bind("<Button-1>", lambda e, v=val: _pick(v))

        _add_row(False, "No thanks", "")
        _add_row(True,  "Yes, add fajita veggies", "20 cal  ·  3 oz")

    def _render_calorie_goal(self) -> None:
        """
        Render the meal calorie-limit keyboard-input step.

        The user may type a calorie limit for this specific meal
        (integer between :data:`logic.CALORIE_GOAL_MIN` and
        :data:`logic.CALORIE_GOAL_MAX`) or leave the field blank to skip.
        If the finished order exceeds this limit, the user will be asked
        whether they want to go back and change something before proceeding
        to the summary.
        """
        card = self._make_card(self.content, title="Set your meal calorie limit")

        info = tk.Frame(card, bg=CARD_BG, padx=14, pady=10)
        info.pack(fill="x")
        tk.Label(info,
                 text=f"How many calories do you want this meal to be? "
                      f"({CALORIE_GOAL_MIN}–{CALORIE_GOAL_MAX} kcal). "
                      f"Leave blank to skip.",
                 font=("Helvetica", 10), bg=CARD_BG, fg=TEXT_SEC,
                 wraplength=480, justify="left").pack(anchor="w")

        entry_row = tk.Frame(card, bg=CARD_BG, padx=14, pady=6)
        entry_row.pack(fill="x")

        tk.Label(entry_row, text="Calorie limit (kcal):",
                 font=("Helvetica", 11), bg=CARD_BG, fg=TEXT_PRI).pack(side="left")

        # Pre-fill with whatever was saved before (convert None -> "")
        saved_goal = self.selections.get("calorie_goal")
        self._calorie_var.set("" if saved_goal is None else str(saved_goal))

        entry = tk.Entry(entry_row, textvariable=self._calorie_var,
                         font=("Helvetica", 12), width=10,
                         relief="flat", bd=1,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.pack(side="left", padx=(10, 0))
        entry.focus_set()

        # Inline error label — hidden until validation fails
        self._goal_error_lbl = tk.Label(card, text="", font=("Helvetica", 10),
                                         bg=CARD_BG, fg=BTN_DANGER,
                                         padx=14, pady=4)
        self._goal_error_lbl.pack(anchor="w")

        # Live validation on every keystroke
        def _on_change(*_: Any) -> None:
            """Validate the entry on every keystroke and update the error label."""
            ok, _, err = validate_calorie_goal(self._calorie_var.get())
            self._goal_error_lbl.config(text="" if ok else err)

        self._calorie_var.trace_add("write", _on_change)

    def _render_summary(self) -> None:
        """
        Render the order summary step.

        Displays four macro cards (calories, protein, carbs, fat) followed
        by a detailed breakdown of every selected item.  When a calorie
        limit has been set, a progress bar shows how the order compares to
        that limit, colored green when within budget or red when over.
        """
        order_lines, totals = build_order_lines(self.selections, self.item_lookup)
        limit: int | None = self.selections.get("calorie_goal")
        cal_total          = totals["calories"]

        # ── Macro summary cards ──────────────────────────────────────────────
        macro_row = tk.Frame(self.content, bg=BG, padx=16, pady=10)
        macro_row.pack(fill="x")

        # Flash the calories card red when over the limit
        cal_card_color = (COLOR_WARN
                          if limit is not None and cal_total > limit
                          else COLOR_CALORIES)
        macros = [
            ("Calories", str(cal_total),         cal_card_color),
            ("Protein",  f"{totals['protein']}g", COLOR_PROTEIN),
            ("Carbs",    f"{totals['carbs']}g",   COLOR_CARBS),
            ("Fat",      f"{totals['fat']}g",     COLOR_FAT),
        ]
        for i, (lbl, val, color) in enumerate(macros):
            cell = tk.Frame(macro_row, bg=color, padx=6, pady=8)
            cell.grid(row=0, column=i, padx=4, sticky="nsew")
            macro_row.columnconfigure(i, weight=1)
            tk.Label(cell, text=val, font=("Helvetica", 18, "bold"),
                     bg=color, fg="white").pack()
            tk.Label(cell, text=lbl, font=("Helvetica", 9),
                     bg=color, fg="white").pack()

        # ── Calorie-limit progress bar (only when a limit is set) ─────────────
        if limit is not None:
            goal_card  = self._make_card(self.content, title="Meal calorie limit")
            goal_frame = tk.Frame(goal_card, bg=CARD_BG, padx=14, pady=10)
            goal_frame.pack(fill="x")

            pct       = min(cal_total / limit, 1.0)
            remaining = limit - cal_total
            bar_color = COLOR_GOOD if cal_total <= limit else COLOR_WARN
            status    = (f"{remaining} kcal remaining"
                         if remaining >= 0
                         else f"{-remaining} kcal over your limit")

            tk.Label(goal_frame,
                     text=f"{cal_total} / {limit} kcal  —  {status}",
                     font=("Helvetica", 11, "bold"), bg=CARD_BG,
                     fg=bar_color).pack(anchor="w", pady=(0, 6))

            # Bar track
            bar_bg = tk.Frame(goal_frame, bg=BORDER, height=12)
            bar_bg.pack(fill="x")
            bar_bg.update_idletasks()
            bar_w = bar_bg.winfo_width() or 540
            # Bar fill
            tk.Frame(bar_bg, bg=bar_color,
                     height=12, width=int(bar_w * pct)).place(x=0, y=0)

        # ── Order item list ──────────────────────────────────────────────────
        card = self._make_card(self.content, title="Your order")

        if not order_lines:
            tk.Label(card, text="No items selected.",
                     font=("Helvetica", 11),
                     bg=CARD_BG, fg=TEXT_SEC, pady=12).pack()
        else:
            for label, cat_tag, item in order_lines:
                row = tk.Frame(card, bg=CARD_BG, padx=14, pady=7)
                row.pack(fill="x")
                tk.Label(row, text=label, font=("Helvetica", 11),
                         bg=CARD_BG, fg=TEXT_PRI, anchor="w").pack(side="left")
                tk.Label(row, text=f"{item['calories']} cal",
                         font=("Helvetica", 10),
                         bg=CARD_BG, fg=TEXT_SEC).pack(side="right")
                tk.Label(row, text=cat_tag, font=("Helvetica", 9),
                         bg=BG, fg=TEXT_SEC,
                         padx=6, pady=1).pack(side="right", padx=6)
                tk.Frame(card, bg=BORDER, height=1).pack(fill="x")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _save_step(self) -> None:
        """
        Persist the current step's UI state back into ``self.selections``.

        Called automatically before moving forward or backward.
        Multi-choice steps are saved live on every click so nothing
        extra is needed for them here.
        """
        steps = active_steps(self.selections)
        _, kind, _ = steps[self.current_step]

        if kind == "single":
            val = self._single_var.get()
            self.selections[self._single_step] = (  # type: ignore[index]
                None if val == "__none__" else val)

        elif kind == "toggle":
            self.selections["double_protein"] = self._double_var.get()

        elif kind == "qesa_veggies":
            self.selections["qesa_veggies"] = self._qesa_veg_var.get()

        elif kind == "calorie_goal":
            # Validate before saving; leave the old value intact if invalid
            ok, parsed, _ = validate_calorie_goal(self._calorie_var.get())
            if ok:
                self.selections["calorie_goal"] = parsed

    def _go_next(self) -> None:
        """
        Validate the current step and advance to the next one.

        Special cases:
        - Base step: blocks if nothing is selected.
        - Calorie-goal step: blocks if the typed value is invalid.
        - Last step before summary: if a calorie limit is set and the
          order exceeds it, shows a Yes/No dialog asking whether the user
          wants to go back and change something.  Saying yes moves back
          one step with all selections intact.  Saying no proceeds to the
          summary as-is.
        """
        self._save_step()
        steps   = active_steps(self.selections)
        step_id, kind, _ = steps[self.current_step]
        last    = len(steps) - 1

        # Require a base choice
        if step_id == "base" and not self.selections["base"]:
            self._popup("Please choose a base before continuing.")
            return

        # Block on invalid calorie-limit input
        if kind == "calorie_goal":
            ok, _, err = validate_calorie_goal(self._calorie_var.get())
            if not ok:
                self._popup(err)
                return

        # Check calorie limit before entering the summary step
        if self.current_step == last - 1:
            limit: int | None = self.selections.get("calorie_goal")
            if limit is not None:
                _, totals = build_order_lines(self.selections, self.item_lookup)
                over_by   = totals["calories"] - limit
                if over_by > 0:
                    self._ask_over_limit(over_by)
                    return   # dialog will handle navigation

        if self.current_step < last:
            self.current_step += 1
            self._show_step()

    def _ask_over_limit(self, over_by: int) -> None:
        """
        Show a Yes/No modal dialog when the order exceeds the calorie limit.

        Asking "Yes, go back" decrements current_step by one and redraws
        the previous step with all selections preserved — no reset.
        Asking "No, continue" advances to the summary step as-is.

        Parameters
        ----------
        over_by : int
            Number of calories the order exceeds the user's limit by.
        """
        pop = tk.Toplevel(self.root)
        pop.title("Over your limit")
        pop.resizable(False, False)
        pop.configure(bg=CARD_BG)
        pop.grab_set()

        # Warning icon row
        icon_row = tk.Frame(pop, bg=CARD_BG)
        icon_row.pack(padx=24, pady=(20, 0))
        tk.Label(icon_row,
                 text=f"Your meal is {over_by} kcal over your limit.",
                 font=("Helvetica", 12, "bold"),
                 bg=CARD_BG, fg=COLOR_WARN).pack()

        tk.Label(pop,
                 text="Would you like to go back and change something?",
                 font=("Helvetica", 11),
                 bg=CARD_BG, fg=TEXT_PRI,
                 padx=24, pady=8,
                 wraplength=320).pack()

        btn_row = tk.Frame(pop, bg=CARD_BG)
        btn_row.pack(padx=24, pady=(4, 20))

        def _go_back_choice() -> None:
            """Close the dialog and move back one step, keeping all selections."""
            pop.destroy()
            # Step back without calling _save_step again (already saved)
            if self.current_step > 0:
                self.current_step -= 1
                self._show_step()

        def _continue_anyway() -> None:
            """Close the dialog and proceed to the summary step."""
            pop.destroy()
            steps = active_steps(self.selections)
            if self.current_step < len(steps) - 1:
                self.current_step += 1
                self._show_step()

        tk.Button(btn_row,
                  text="Yes, go back",
                  font=("Helvetica", 11, "bold"), width=14,
                  bg=ACCENT, fg="white",
                  activebackground=ACCENT_DARK, activeforeground="white",
                  relief="flat", bd=0, highlightthickness=0,
                  padx=8, pady=6,
                  cursor="hand2",
                  command=_go_back_choice).pack(side="left", padx=(0, 8))

        tk.Button(btn_row,
                  text="No, continue",
                  font=("Helvetica", 11, "bold"), width=14,
                  bg=BROWN, fg="white",
                  activebackground=BROWN_DARK, activeforeground="white",
                  relief="flat", bd=0, highlightthickness=0,
                  padx=8, pady=6,
                  cursor="hand2",
                  command=_continue_anyway).pack(side="left")

        pop.update_idletasks()
        x = (self.root.winfo_x()
             + (self.root.winfo_width()  - pop.winfo_width())  // 2)
        y = (self.root.winfo_y()
             + (self.root.winfo_height() - pop.winfo_height()) // 2)
        pop.geometry(f"+{x}+{y}")

    def _go_back(self) -> None:
        """Save the current step and move to the previous one."""
        self._save_step()
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def _update_nav(self) -> None:
        """
        Update the Back and Next button states and labels to match the
        current step position.

        On the last step (summary), Next becomes "Done" and restarts
        the wizard when clicked.
        """
        steps = active_steps(self.selections)
        last  = len(steps) - 1

        self.back_btn.config(
            state="disabled" if self.current_step == 0 else "normal")

        if self.current_step == last:
            self.next_btn.config(text="Done", state="normal",
                                  command=self._reset_all)
        elif self.current_step == last - 1:
            self.next_btn.config(text="Summary →", state="normal",
                                  command=self._go_next)
        else:
            self.next_btn.config(text="Next →", state="normal",
                                  command=self._go_next)

    def _reset_all(self) -> None:
        """Reset all selections and return the wizard to step 1."""
        self.selections   = fresh_selections()
        self.current_step = 0
        self._qesa_veg_var.set(False)
        self._calorie_var.set("")
        self._show_step()

    # ── Popup dialog ──────────────────────────────────────────────────────────

    def _popup(self, msg: str) -> None:
        """
        Show a small centered modal dialog with an error or info message.

        Parameters
        ----------
        msg : str
            The message to display to the user.
        """
        pop = tk.Toplevel(self.root)
        pop.title("")
        pop.resizable(False, False)
        pop.configure(bg=CARD_BG)
        pop.grab_set()
        tk.Label(pop, text=msg, font=("Helvetica", 11),
                 bg=CARD_BG, fg=TEXT_PRI,
                 padx=24, pady=16, wraplength=300).pack()
        tk.Button(pop, text="OK", font=("Helvetica", 11, "bold"),
                  bg=ACCENT, fg="white", activebackground=ACCENT_DARK,
                  activeforeground="white",
                  relief="flat", bd=0, highlightthickness=0,
                  padx=20, pady=6,
                  command=pop.destroy).pack(pady=(0, 14))
        pop.update_idletasks()
        x = (self.root.winfo_x()
             + (self.root.winfo_width()  - pop.winfo_width())  // 2)
        y = (self.root.winfo_y()
             + (self.root.winfo_height() - pop.winfo_height()) // 2)
        pop.geometry(f"+{x}+{y}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """
    Application entry point.

    Loads the menu data from ``nutrition_info.csv`` (with exception
    handling for missing or malformed files), then launches the tkinter
    main loop.
    """
    try:
        menu_data = load_menu_from_csv()
    except FileNotFoundError as exc:
        # Show a native error dialog before the main window appears
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("File not found", str(exc))
        root.destroy()
        return
    except ValueError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("CSV error", str(exc))
        root.destroy()
        return

    root = tk.Tk()
    ChipotleApp(root, menu_data)
    root.mainloop()


if __name__ == "__main__":
    main()