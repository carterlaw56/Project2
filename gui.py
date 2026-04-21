# gui.py
# The main GUI file for the Chipotle Nutrition Calculator.
# All the logic and data stuff is handled in logic.py.
# Run this file to start the app.

from tkinter import *
from tkinter import messagebox
import logic

# Colors
BG           = "#F5F0EB"   # page background
CARD_BG      = "#FFFFFF"   # white card
HEADER_BG    = "#7B1113"   # dark chipotle red for the header
ACCENT       = "#D85A30"   # chipotle orange-red for highlights/buttons
ACCENT_DARK  = "#993C1D"   # darker orange for hover
BROWN        = "#4A2C1A"   # dark brown for back button
BROWN_DARK   = "#2E1A0E"   # darker brown for hover
RESET_BG     = "#A32D2D"   # dark red for reset button
TEXT_MAIN    = "#1C1916"   # main text color
TEXT_MUTED   = "#6B635C"   # lighter gray text
SEL_BG       = "#FAECE7"   # highlight color for selected rows
BORDER_COLOR = "#E0D9D2"   # card border color
COLOR_GOOD   = "#3B6D11"   # green — under calorie limit
COLOR_WARN   = "#A32D2D"   # red — over calorie limit
COLOR_CAL    = "#D85A30"   # calories macro card
COLOR_PRO    = "#185FA5"   # protein macro card
COLOR_CARB   = "#3B6D11"   # carbs macro card
COLOR_FAT    = "#854F0B"   # fat macro card


class ChipotleApp:
    def __init__(self, window, menu_data):
        self.window = window
        self.window.title("Chipotle Nutrition Calculator")
        self.window.geometry("600x600")
        self.window.resizable(False, False)
        self.window.configure(bg=BG)

        # Build lookup structures from the loaded CSV data
        self.menu_data   = menu_data
        self.categories  = logic.build_category_index(menu_data)
        self.item_lookup = {item["item_name"]: item for item in menu_data}

        # These tk variables hold the current selection on each step
        self.single_var   = StringVar()   # for radio button steps
        self.double_var   = BooleanVar()  # for the double protein checkbox
        self.qesa_veg_var = BooleanVar()  # for the quesadilla fajita veggies yes/no
        self.calorie_var  = StringVar()   # for the calorie limit text entry
        self.multi_vars   = {}            # checkboxes for multi-select steps
        self.single_step  = None          # tracks which category single_var belongs to

        # Start with a blank order and go to step 0
        self.selections  = logic.fresh_selections()
        self.current_step = 0

        self.build_window()
        self.show_step()

    def build_window(self):
        # Builds the parts of the window that stay the same on every step:
        # header, progress bar, step label, scrollable area, and nav buttons.

        # Used Claude to help create a more user-friendly interface in this function

        # Header banner — dark chipotle red
        self.frame_header = Frame(self.window, bg=HEADER_BG, pady=12)
        self.frame_header.pack(fill='x')
        Label(self.frame_header, text="Chipotle Nutrition Calculator",
              font=("Helvetica", 17, "bold"),
              bg=HEADER_BG, fg="white").pack()
        Label(self.frame_header, text="Build your meal · track your macros",
              font=("Helvetica", 10), bg=HEADER_BG, fg="#FAECE7").pack(pady=(2, 0))

        # Progress bar
        self.prog_canvas = Canvas(self.window, height=5, bg=BORDER_COLOR,
                                  highlightthickness=0, bd=0)
        self.prog_canvas.pack(fill='x')
        self.prog_fill = self.prog_canvas.create_rectangle(0, 0, 0, 5,
                                                            fill=ACCENT, outline="")

        # Step counter label
        self.label_step = Label(self.window, text="", font=("Helvetica", 11),
                                bg=BG, fg=TEXT_MUTED, pady=7)
        self.label_step.pack()

        # Scrollable content area
        self.scroll_canvas = Canvas(self.window, bg=BG, highlightthickness=0, bd=0)
        scrollbar = Scrollbar(self.window, orient='vertical',
                              command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.scroll_canvas.pack(fill='both', expand=True)

        self.frame_content = Frame(self.scroll_canvas, bg=BG)
        self.content_window = self.scroll_canvas.create_window(
            (0, 0), window=self.frame_content, anchor='nw')

        self.frame_content.bind('<Configure>', lambda e:
            self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox('all')))
        self.scroll_canvas.bind('<Configure>', lambda e:
            self.scroll_canvas.itemconfig(self.content_window, width=e.width))
        self.scroll_canvas.bind_all('<MouseWheel>', lambda e:
            self.scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        # Bottom navigation bar
        self.frame_nav = Frame(self.window, bg=BG, pady=9)
        self.frame_nav.pack(fill='x', padx=18)
        self.frame_nav.columnconfigure(1, weight=1)

        self.button_reset = Button(
            self.frame_nav, text="Reset", font=("Helvetica", 11, "bold"), width=8,
            bg=RESET_BG, fg="white",
            activebackground="#7A1E1E", activeforeground="white",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self.reset_all)
        self.button_reset.grid(row=0, column=0)

        self.frame_right_nav = Frame(self.frame_nav, bg=BG)
        self.frame_right_nav.grid(row=0, column=2, sticky='e')

        self.button_back = Button(
            self.frame_right_nav, text="<- Back", font=("Helvetica", 11, "bold"),
            width=9, bg=BROWN, fg="white",
            activebackground=BROWN_DARK, activeforeground="white",
            disabledforeground="#A07860",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self.go_back)
        self.button_back.pack(side='left', padx=(0, 6))

        self.button_next = Button(
            self.frame_right_nav, text="Next ->", font=("Helvetica", 11, "bold"),
            width=11, bg=ACCENT, fg="white",
            activebackground=ACCENT_DARK, activeforeground="white",
            disabledforeground="#F5C9B8",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6,
            command=self.go_next)
        self.button_next.pack(side='left')

    def clear_content(self):
        # Destroys all widgets in the scrollable content frame
        for widget in self.frame_content.winfo_children():
            widget.destroy()

    def show_step(self):
        # Clears and redraws the current step
        self.clear_content()

        steps = logic.active_steps(self.selections)
        step_id, kind, allow_none = steps[self.current_step]
        total = len(steps)

        # Update the progress bar
        self.prog_canvas.update_idletasks()
        bar_width = self.prog_canvas.winfo_width()
        pct = self.current_step / (total - 1)
        self.prog_canvas.coords(self.prog_fill, 0, 0, int(bar_width * pct), 5)

        # Update the step label
        self.label_step.config(
            text=f"Step {self.current_step + 1} of {total}  ·  {logic.STEP_TITLES[step_id]}")

        # Call the right render method for this step type
        if kind == "single":
            self.render_single(step_id, allow_none)
        elif kind == "toggle":
            self.render_toggle()
        elif kind == "multi":
            self.render_multi(step_id)
        elif kind == "qesa_veggies":
            self.render_qesa_veggies()
        elif kind == "calorie_goal":
            self.render_calorie_goal()
        elif kind == "summary":
            self.render_summary()

        self.update_nav_buttons()
        self.scroll_canvas.yview_moveto(0)

    def make_card(self, title=None):
        # Creates a white bordered card in the content area and returns it.
        # Optionally adds a bold title at the top.

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1,
                           highlightbackground=BORDER_COLOR,
                           highlightcolor=BORDER_COLOR)
        frame_card.pack(fill='x')

        if title:
            Label(frame_card, text=title, font=("Helvetica", 12, "bold"),
                  bg=CARD_BG, fg=TEXT_MAIN, anchor='w',
                  padx=14, pady=10).pack(fill='x')
            Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

        return frame_card

    def recolor_row(self, container, bg):
        # Recursively sets the background color on a widget and all its children.
        # Used to highlight/unhighlight selected rows.
        try:
            container.configure(bg=bg)
        except TclError:
            pass
        for child in container.winfo_children():
            self.recolor_row(child, bg)

    def make_option_row(self, frame_card, label, sublabel, is_selected, make_control):
        # Builds one clickable row inside a card.
        # make_control is a function that creates the radio or checkbox widget.
        # Returns (row_frame, accent_bar, inner_frame) so we can recolor later.

        bg = SEL_BG if is_selected else CARD_BG

        frame_row = Frame(frame_card, bg=bg, cursor="hand2")
        frame_row.pack(fill='x')

        # Colored left bar shown when this row is selected
        frame_accent = Frame(frame_row, bg=ACCENT if is_selected else CARD_BG, width=4)
        frame_accent.pack(side='left', fill='y')

        frame_inner = Frame(frame_row, bg=bg, padx=10, pady=9)
        frame_inner.pack(side='left', fill='x', expand=True)

        # Create the control (radio or checkbox) inside frame_inner
        ctrl = make_control(frame_inner)
        ctrl.pack(side='left', padx=(0, 6))

        Label(frame_inner, text=label, font=("Helvetica", 11),
              bg=bg, fg=TEXT_MAIN, anchor='w').pack(side='left')

        if sublabel:
            Label(frame_inner, text=sublabel, font=("Helvetica", 10),
                  bg=bg, fg=TEXT_MUTED).pack(side='right', padx=6)

        Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

        return frame_row, frame_accent, frame_inner

    def render_single(self, step_id, allow_none):
        # Renders a step where you pick exactly one option (radio buttons).

        self.single_step = step_id
        items = self.categories.get(step_id, [])

        # Restore whatever was saved before
        saved = self.selections[step_id]
        if saved is not None:
            init_val = saved
        elif allow_none:
            init_val = "__none__"
        else:
            init_val = items[0]["item_name"] if items else ""

        self.single_var.set(init_val)

        frame_card = self.make_card()
        row_frames = {}  # val -> (frame_row, frame_accent)

        def select(val):
            # Updates the radio var and recolors all rows
            self.single_var.set(val)
            for v, (rf, ab) in row_frames.items():
                sel = (v == val)
                self.recolor_row(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def add_row(val, label, sublabel):
            sel = (val == init_val)

            def make_ctrl(frame_inner):
                return Radiobutton(frame_inner,
                                   variable=self.single_var,
                                   value=val,
                                   bg=SEL_BG if sel else CARD_BG,
                                   activebackground=SEL_BG if sel else CARD_BG,
                                   highlightthickness=0,
                                   command=lambda v=val: select(v))

            rf, ab, fi = self.make_option_row(frame_card, label, sublabel, sel, make_ctrl)
            row_frames[val] = (rf, ab)

            for w in (rf, fi, ab):
                w.bind('<Button-1>', lambda e, v=val: select(v))

        if allow_none:
            add_row("__none__", "None", "")
        for item in items:
            sub = f"{item['calories']} cal  ·  {item['portion']}" if item['calories'] > 0 else item['portion']
            add_row(item["item_name"], item["item_name"], sub)

    def render_toggle(self):
        # Renders the double protein yes/no checkbox step.

        self.double_var.set(self.selections["double_protein"])
        frame_card = self.make_card(title="Double protein?")

        frame_inner = Frame(frame_card, bg=CARD_BG, padx=14, pady=14)
        frame_inner.pack(fill='x')

        Checkbutton(frame_inner,
                    text="Yes — double my protein",
                    variable=self.double_var,
                    font=("Helvetica", 12),
                    bg=CARD_BG, fg=TEXT_MAIN,
                    activebackground=CARD_BG,
                    selectcolor=CARD_BG,
                    cursor="hand2").pack(anchor='w')

        if self.selections["protein"]:
            note = "Doubles calories, protein, carbs and fat for your protein choice."
        else:
            note = "No protein selected — this option has no effect."

        Label(frame_card, text=note, font=("Helvetica", 10),
              bg=CARD_BG, fg=TEXT_MUTED, padx=14, pady=6,
              wraplength=480, justify='left').pack(anchor='w')

    def render_multi(self, step_id):
        # Renders a step where you can pick multiple options (checkboxes).

        self.multi_vars = {}
        items = self.categories.get(step_id, [])
        frame_card = self.make_card()

        if not items:
            Label(frame_card, text="No items available.",
                  font=("Helvetica", 11),
                  bg=CARD_BG, fg=TEXT_MUTED, pady=12).pack()
            return

        row_frames = {}  # name -> (frame_row, frame_accent)

        def recolor_all():
            for name, (rf, ab) in row_frames.items():
                sel = self.multi_vars[name].get()
                self.recolor_row(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def toggle(name):
            var = self.multi_vars[name]
            if var.get():
                if name not in self.selections[step_id]:
                    self.selections[step_id].append(name)
            else:
                self.selections[step_id] = [n for n in self.selections[step_id] if n != name]
            recolor_all()

        for item in items:
            name    = item["item_name"]
            checked = name in self.selections[step_id]
            var     = BooleanVar(value=checked)
            self.multi_vars[name] = var

            sub = f"{item['calories']} cal  ·  {item['portion']}" if item['calories'] > 0 else item['portion']

            def make_ctrl(frame_inner, n=name, v=var):
                return Checkbutton(frame_inner,
                                   variable=v,
                                   bg=SEL_BG if v.get() else CARD_BG,
                                   activebackground=SEL_BG if v.get() else CARD_BG,
                                   selectcolor=CARD_BG,
                                   highlightthickness=0,
                                   cursor="hand2",
                                   command=lambda nm=n: toggle(nm))

            rf, ab, fi = self.make_option_row(frame_card, name, sub, checked, make_ctrl)
            row_frames[name] = (rf, ab)

            for w in (rf, fi, ab):
                w.bind('<Button-1>', lambda e, n=name, v=var: (v.set(not v.get()), toggle(n)))

    def render_qesa_veggies(self):
        # Renders the yes/no fajita veggies step for quesadillas.

        self.qesa_veg_var.set(self.selections["qesa_veggies"])
        frame_card = self.make_card(title="Add fajita veggies?")

        frame_note = Frame(frame_card, bg=CARD_BG, padx=14, pady=6)
        frame_note.pack(fill='x')
        Label(frame_note,
              text="Your quesadilla already includes cheese. "
                   "Would you like fajita veggies added inside?",
              font=("Helvetica", 10), bg=CARD_BG, fg=TEXT_MUTED,
              wraplength=480, justify='left').pack(anchor='w')

        row_frames = {}  # val -> (frame_row, frame_accent)

        def pick(val):
            self.qesa_veg_var.set(val)
            for v, (rf, ab) in row_frames.items():
                sel = (v == val)
                self.recolor_row(rf, SEL_BG if sel else CARD_BG)
                ab.configure(bg=ACCENT if sel else CARD_BG)

        def add_row(val, label, sublabel):
            sel = (val == self.qesa_veg_var.get())

            def make_ctrl(frame_inner, v=val):
                return Radiobutton(frame_inner,
                                   variable=self.qesa_veg_var,
                                   value=v,
                                   bg=SEL_BG if sel else CARD_BG,
                                   activebackground=SEL_BG if sel else CARD_BG,
                                   highlightthickness=0,
                                   command=lambda vv=v: pick(vv))

            rf, ab, fi = self.make_option_row(frame_card, label, sublabel, sel, make_ctrl)
            row_frames[val] = (rf, ab)
            for w in (rf, fi, ab):
                w.bind('<Button-1>', lambda e, v=val: pick(v))

        add_row(False, "No thanks", "")
        add_row(True, "Yes, add fajita veggies", "20 cal  ·  3 oz")

    def render_calorie_goal(self):
        # Renders the calorie limit entry step.
        # The user types a number or leaves it blank to skip.

        frame_card = self.make_card(title="Set your meal calorie limit")

        frame_info = Frame(frame_card, bg=CARD_BG, padx=14, pady=10)
        frame_info.pack(fill='x')
        Label(frame_info,
              text=f"How many calories do you want this meal to be? "
                   f"({logic.CALORIE_MIN}-{logic.CALORIE_MAX} kcal). "
                   f"Leave blank to skip.",
              font=("Helvetica", 10), bg=CARD_BG, fg=TEXT_MUTED,
              wraplength=480, justify='left').pack(anchor='w')

        frame_entry = Frame(frame_card, bg=CARD_BG, padx=14, pady=6)
        frame_entry.pack(fill='x')

        Label(frame_entry, text="Calorie limit (kcal):",
              font=("Helvetica", 11), bg=CARD_BG, fg=TEXT_MAIN).pack(side='left')

        # Pre-fill the field with whatever was saved before
        saved = self.selections.get("calorie_goal")
        self.calorie_var.set("" if saved is None else str(saved))

        self.entry_calorie = Entry(frame_entry, textvariable=self.calorie_var,
                                   font=("Helvetica", 12), width=10,
                                   relief='flat', bd=1,
                                   highlightthickness=1,
                                   highlightbackground=BORDER_COLOR,
                                   highlightcolor=ACCENT)
        self.entry_calorie.pack(side='left', padx=(10, 0))
        self.entry_calorie.focus_set()

        # Error label — stays hidden until the user types something invalid
        self.label_calorie_error = Label(frame_card, text="",
                                          font=("Helvetica", 10),
                                          bg=CARD_BG, fg=RESET_BG,
                                          padx=14, pady=4)
        self.label_calorie_error.pack(anchor='w')

        # Validate on every keystroke
        def on_calorie_change(*args):
            ok, _, err = logic.validate_calorie_goal(self.calorie_var.get())
            self.label_calorie_error.config(text="" if ok else err)

        self.calorie_var.trace_add("write", on_calorie_change)

    def render_summary(self):
        # Renders the final summary page with macro cards and item breakdown.

        # Used Claude AI to help us generate a nice summary page that renders calorie information, goal bar
        order_lines, totals = logic.build_order_lines(self.selections, self.item_lookup)
        limit     = self.selections.get("calorie_goal")
        cal_total = totals["calories"]

        # Macro cards row — calories card turns red if over the limit
        frame_macros = Frame(self.frame_content, bg=BG, padx=16, pady=10)
        frame_macros.pack(fill='x')

        cal_color = COLOR_WARN if (limit is not None and cal_total > limit) else COLOR_CAL

        macros = [
            ("Calories", str(cal_total),          cal_color),
            ("Protein",  f"{totals['protein']}g", COLOR_PRO),
            ("Carbs",    f"{totals['carbs']}g",   COLOR_CARB),
            ("Fat",      f"{totals['fat']}g",      COLOR_FAT),
        ]
        for i, (lbl, val, color) in enumerate(macros):
            cell = Frame(frame_macros, bg=color, padx=6, pady=8)
            cell.grid(row=0, column=i, padx=4, sticky='nsew')
            frame_macros.columnconfigure(i, weight=1)
            Label(cell, text=val, font=("Helvetica", 18, "bold"),
                  bg=color, fg="white").pack()
            Label(cell, text=lbl, font=("Helvetica", 9),
                  bg=color, fg="white").pack()

        # Calorie limit progress bar — only shows if a limit was set - Help from Claude AI
        if limit is not None:
            frame_limit_card = self.make_card(title="Meal calorie limit")
            frame_limit = Frame(frame_limit_card, bg=CARD_BG, padx=14, pady=10)
            frame_limit.pack(fill='x')

            pct       = min(cal_total / limit, 1.0)
            remaining = limit - cal_total
            bar_color = COLOR_GOOD if cal_total <= limit else COLOR_WARN

            if remaining >= 0:
                status = f"{remaining} kcal remaining"
            else:
                status = f"{-remaining} kcal over your limit"

            Label(frame_limit,
                  text=f"{cal_total} / {limit} kcal  —  {status}",
                  font=("Helvetica", 11, "bold"),
                  bg=CARD_BG, fg=bar_color).pack(anchor='w', pady=(0, 6))

            # Bar track + fill - Help from Claude AI
            frame_bar = Frame(frame_limit, bg=BORDER_COLOR, height=12)
            frame_bar.pack(fill='x')
            frame_bar.update_idletasks()
            bar_w = frame_bar.winfo_width() or 540
            Frame(frame_bar, bg=bar_color, height=12,
                  width=int(bar_w * pct)).place(x=0, y=0)

        # Item breakdown list
        frame_card = self.make_card(title="Your order")

        if not order_lines:
            Label(frame_card, text="No items selected.",
                  font=("Helvetica", 11),
                  bg=CARD_BG, fg=TEXT_MUTED, pady=12).pack()
        else:
            for label, cat_tag, item in order_lines:
                frame_row = Frame(frame_card, bg=CARD_BG, padx=14, pady=7)
                frame_row.pack(fill='x')
                Label(frame_row, text=label, font=("Helvetica", 11),
                      bg=CARD_BG, fg=TEXT_MAIN, anchor='w').pack(side='left')
                Label(frame_row, text=f"{item['calories']} cal",
                      font=("Helvetica", 10),
                      bg=CARD_BG, fg=TEXT_MUTED).pack(side='right')
                Label(frame_row, text=cat_tag, font=("Helvetica", 9),
                      bg=BG, fg=TEXT_MUTED, padx=6, pady=1).pack(side='right', padx=6)
                Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

    def save_step(self):
        # Saves whatever the user has selected on the current step.
        # Multi-select steps save automatically on each click, so nothing needed there.

        steps = logic.active_steps(self.selections)
        _, kind, _ = steps[self.current_step]

        if kind == "single":
            val = self.single_var.get()
            self.selections[self.single_step] = None if val == "__none__" else val

        elif kind == "toggle":
            self.selections["double_protein"] = self.double_var.get()

        elif kind == "qesa_veggies":
            self.selections["qesa_veggies"] = self.qesa_veg_var.get()

        elif kind == "calorie_goal":
            ok, parsed, _ = logic.validate_calorie_goal(self.calorie_var.get())
            if ok:
                self.selections["calorie_goal"] = parsed

    def go_next(self):
        # Saves the current step and moves forward.
        # Blocks if base is not chosen or calorie entry is invalid.
        # Shows a yes/no popup if the order is over the calorie limit.

        self.save_step()

        steps   = logic.active_steps(self.selections)
        step_id, kind, _ = steps[self.current_step]
        last    = len(steps) - 1

        # Must pick a base before moving on
        if step_id == "base" and not self.selections["base"]:
            self.show_popup("Please choose a base before continuing.")
            return

        # Block if calorie entry is invalid
        if kind == "calorie_goal":
            ok, _, err = logic.validate_calorie_goal(self.calorie_var.get())
            if not ok:
                self.show_popup(err)
                return

        # Before going to the summary, check if the order is over the limit
        if self.current_step == last - 1:
            limit = self.selections.get("calorie_goal")
            if limit is not None:
                _, totals = logic.build_order_lines(self.selections, self.item_lookup)
                over_by = totals["calories"] - limit
                if over_by > 0:
                    self.show_over_limit_dialog(over_by)
                    return

        if self.current_step < last:
            self.current_step += 1
            self.show_step()

    def show_over_limit_dialog(self, over_by):
        # Shows a popup asking if the user wants to go back or continue anyway.
        # This function was created with the assistance of Claude AI

        pop = Toplevel(self.window)
        pop.title("Over your limit")
        pop.resizable(False, False)
        pop.configure(bg=CARD_BG)
        pop.grab_set()

        frame_msg = Frame(pop, bg=CARD_BG)
        frame_msg.pack(padx=24, pady=(20, 0))
        Label(frame_msg,
              text=f"Your meal is {over_by} kcal over your limit.",
              font=("Helvetica", 12, "bold"),
              bg=CARD_BG, fg=COLOR_WARN).pack()

        Label(pop,
              text="Would you like to go back and change something?",
              font=("Helvetica", 11),
              bg=CARD_BG, fg=TEXT_MAIN,
              padx=24, pady=8, wraplength=320).pack()

        frame_buttons = Frame(pop, bg=CARD_BG)
        frame_buttons.pack(padx=24, pady=(4, 20))

        def go_back_choice():
            pop.destroy()
            if self.current_step > 0:
                self.current_step -= 1
                self.show_step()

        def continue_anyway():
            pop.destroy()
            steps = logic.active_steps(self.selections)
            if self.current_step < len(steps) - 1:
                self.current_step += 1
                self.show_step()

        Button(frame_buttons, text="Yes, go back",
               font=("Helvetica", 11, "bold"), width=14,
               bg=ACCENT, fg="white",
               activebackground=ACCENT_DARK, activeforeground="white",
               relief='flat', bd=0, highlightthickness=0,
               padx=8, pady=6, cursor="hand2",
               command=go_back_choice).pack(side='left', padx=(0, 8))

        Button(frame_buttons, text="No, continue",
               font=("Helvetica", 11, "bold"), width=14,
               bg=BROWN, fg="white",
               activebackground=BROWN_DARK, activeforeground="white",
               relief='flat', bd=0, highlightthickness=0,
               padx=8, pady=6, cursor="hand2",
               command=continue_anyway).pack(side='left')

        pop.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - pop.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - pop.winfo_height()) // 2
        pop.geometry(f"+{x}+{y}")

    def go_back(self):
        # Saves the current step and moves back one step.

        self.save_step()
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()

    def update_nav_buttons(self):
        # Updates the Back and Next buttons based on which step we're on.

        steps = logic.active_steps(self.selections)
        last  = len(steps) - 1

        # Disable Back on the first step
        if self.current_step == 0:
            self.button_back.config(state='disabled')
        else:
            self.button_back.config(state='normal')

        # Change the Next button label and action on the last step
        if self.current_step == last:
            self.button_next.config(text="Done", state='normal',
                                    command=self.reset_all)
        elif self.current_step == last - 1:
            self.button_next.config(text="Summary ->", state='normal',
                                    command=self.go_next)
        else:
            self.button_next.config(text="Next ->", state='normal',
                                    command=self.go_next)

    def reset_all(self):
        # Resets everything and goes back to step 1.

        self.selections   = logic.fresh_selections()
        self.current_step = 0
        self.qesa_veg_var.set(False)
        self.calorie_var.set("")
        self.show_step()

    def show_popup(self, msg):
        # Shows a small centered error/info dialog with an OK button.

        pop = Toplevel(self.window)
        pop.title("")
        pop.resizable(False, False)
        pop.configure(bg=CARD_BG)
        pop.grab_set()

        Label(pop, text=msg, font=("Helvetica", 11),
              bg=CARD_BG, fg=TEXT_MAIN,
              padx=24, pady=16, wraplength=300).pack()

        Button(pop, text="OK", font=("Helvetica", 11, "bold"),
               bg=ACCENT, fg="white",
               activebackground=ACCENT_DARK, activeforeground="white",
               relief='flat', bd=0, highlightthickness=0,
               padx=20, pady=6,
               command=pop.destroy).pack(pady=(0, 14))

        pop.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - pop.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - pop.winfo_height()) // 2
        pop.geometry(f"+{x}+{y}")


# Start the app
def main():
    try:
        menu_data = logic.load_menu_from_csv()
    except FileNotFoundError as e:
        root = Tk()
        root.withdraw()
        messagebox.showerror("File not found", str(e))
        root.destroy()
        return
    except ValueError as e:
        root = Tk()
        root.withdraw()
        messagebox.showerror("CSV error", str(e))
        root.destroy()
        return

    root = Tk()
    ChipotleApp(root, menu_data)
    root.mainloop()


if __name__ == "__main__":
    main()