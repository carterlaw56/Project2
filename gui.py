# gui.py
# Handles all the windows, buttons, and display for the Chipotle Nutrition Calculator.
# All the data and math is in logic.py.

from tkinter import *
from tkinter import messagebox
import logic

# Colors used throughout the app
BG           = "#F5F0EB"   # page background
CARD_BG      = "#FFFFFF"   # white card background
HEADER_BG    = "#7B1113"   # dark chipotle red header
ACCENT       = "#D85A30"   # chipotle orange-red
ACCENT_DARK  = "#993C1D"   # darker orange for hover
BROWN        = "#4A2C1A"   # dark brown for back button
BROWN_DARK   = "#2E1A0E"   # darker brown for hover
RESET_BG     = "#A32D2D"   # dark red for reset button
TEXT_MAIN    = "#1C1916"   # main dark text
TEXT_MUTED   = "#6B635C"   # lighter gray text
SEL_BG       = "#FAECE7"   # orange tint for selected rows
BORDER_COLOR = "#E0D9D2"   # card border
COLOR_GOOD   = "#3B6D11"   # green — under calorie limit
COLOR_WARN   = "#A32D2D"   # red — over calorie limit
COLOR_CAL    = "#D85A30"   # calories macro card color
COLOR_PRO    = "#185FA5"   # protein macro card color
COLOR_CARB   = "#3B6D11"   # carbs macro card color
COLOR_FAT    = "#854F0B"   # fat macro card color


class ChipotleApp:
    def __init__(self, window, menu_data):
        self.window = window
        self.window.title("Chipotle Nutrition Calculator")
        self.window.geometry("600x600")
        self.window.resizable(False, False)
        self.window.configure(bg=BG)

        # Build lookup structures from the CSV data
        self.menu_data   = menu_data
        self.categories  = logic.build_category_index(menu_data)
        self.item_lookup = {item["item_name"]: item for item in menu_data}

        # tk variables for the current step's selections
        self.single_var   = StringVar()
        self.double_var   = BooleanVar()
        self.qesa_veg_var = BooleanVar()
        self.multi_vars   = {}
        self.single_step  = None

        # Start with a blank order
        self.selections   = logic.fresh_selections()
        self.current_step = 0

        self.build_window()
        self.show_step()

    def build_window(self):
        # Creates all the permanent parts of the window that never change:
        # the header, progress bar, step label, scrollable area, and nav buttons.

        # Dark red header
        self.frame_header = Frame(self.window, bg=HEADER_BG, pady=12)
        self.frame_header.pack(fill='x')
        Label(self.frame_header, text="Chipotle Nutrition Calculator",
              font=("Helvetica", 17, "bold"),
              bg=HEADER_BG, fg="white").pack()
        Label(self.frame_header, text="Build your meal · track your macros",
              font=("Helvetica", 10), bg=HEADER_BG, fg="#FAECE7").pack(pady=(2, 0))

        # Progress bar drawn on a canvas
        self.prog_canvas = Canvas(self.window, height=5, bg=BORDER_COLOR,
                                  highlightthickness=0, bd=0)
        self.prog_canvas.pack(fill='x')
        self.prog_fill = self.prog_canvas.create_rectangle(0, 0, 0, 5,
                                                            fill=ACCENT, outline="")

        # Step counter label e.g. "Step 2 of 11 · Choose your rice"
        self.label_step = Label(self.window, text="", font=("Helvetica", 11),
                                bg=BG, fg=TEXT_MUTED, pady=7)
        self.label_step.pack()

        # Scrollable content area
        self.scroll_canvas = Canvas(self.window, bg=BG, highlightthickness=0, bd=0)
        self.scrollbar = Scrollbar(self.window, orient='vertical',
                                   command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.on_scroll_update)
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

        # Navigation bar at the bottom
        self.frame_nav = Frame(self.window, bg=BG, pady=9)
        self.frame_nav.pack(fill='x', padx=18)
        self.frame_nav.columnconfigure(1, weight=1)

        self.button_reset = Button(
            self.frame_nav, text="Reset", font=("Helvetica", 11, "bold"), width=8,
            bg=RESET_BG, fg="white",
            activebackground="#7A1E1E", activeforeground="white",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6, command=self.reset_all)
        self.button_reset.grid(row=0, column=0)

        self.frame_right_nav = Frame(self.frame_nav, bg=BG)
        self.frame_right_nav.grid(row=0, column=2, sticky='e')

        self.button_back = Button(
            self.frame_right_nav, text="<- Back", font=("Helvetica", 11, "bold"),
            width=9, bg=BROWN, fg="white",
            activebackground=BROWN_DARK, activeforeground="white",
            disabledforeground="#A07860",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6, command=self.go_back)
        self.button_back.pack(side='left', padx=(0, 6))

        self.button_next = Button(
            self.frame_right_nav, text="Next ->", font=("Helvetica", 11, "bold"),
            width=11, bg=ACCENT, fg="white",
            activebackground=ACCENT_DARK, activeforeground="white",
            disabledforeground="#F5C9B8",
            relief='flat', bd=0, highlightthickness=0, cursor="hand2",
            padx=8, pady=6, command=self.go_next)
        self.button_next.pack(side='left')

    def on_scroll_update(self, first, last):
        # Shows the scrollbar only when the content is taller than the window.
        # first and last are 0.0-1.0 values tkinter passes automatically.
        # If first is 0.0 and last is 1.0 the whole content fits — hide the bar.

        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scrollbar.pack_forget()
        else:
            self.scrollbar.pack(side='right', fill='y')
        self.scrollbar.set(first, last)

    def clear_content(self):
        # Destroys all widgets inside the scrollable area so we can redraw
        for widget in self.frame_content.winfo_children():
            widget.destroy()

    def show_step(self):
        # Clears the content area and draws the current step

        self.clear_content()

        steps = logic.active_steps(self.selections)
        step_id, kind, allow_none = steps[self.current_step]
        total = len(steps)

        # Show the last order banner on step 1 if a saved order exists
        if self.current_step == 0:
            last_order = logic.load_last_order()
            if last_order is not None:
                self.render_last_order_banner(last_order)

        # Update progress bar width
        self.prog_canvas.update_idletasks()
        bar_width = self.prog_canvas.winfo_width()
        pct = self.current_step / (total - 1)
        self.prog_canvas.coords(self.prog_fill, 0, 0, int(bar_width * pct), 5)

        self.label_step.config(
            text=f"Step {self.current_step + 1} of {total}  ·  {logic.STEP_TITLES[step_id]}")

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

    def render_last_order_banner(self, last_order):
        # Shows a dark brown banner on step 1 with the last order details
        # and a button to jump straight to the summary with that order loaded

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')

        frame_banner = Frame(frame_outer, bg=BROWN,
                             highlightthickness=1,
                             highlightbackground=BROWN_DARK)
        frame_banner.pack(fill='x')

        frame_top = Frame(frame_banner, bg=BROWN, padx=14, pady=10)
        frame_top.pack(fill='x')

        Label(frame_top, text="Last Order",
              font=("Helvetica", 12, "bold"),
              bg=BROWN, fg="white").pack(side='left')

        Button(frame_top, text="Use This Order",
               font=("Helvetica", 10, "bold"),
               bg=ACCENT, fg="white",
               activebackground=ACCENT_DARK, activeforeground="white",
               relief='flat', bd=0, highlightthickness=0,
               padx=10, pady=4, cursor="hand2",
               command=lambda: self.load_last_order(last_order)).pack(side='right')

        Frame(frame_banner, bg=BROWN_DARK, height=1).pack(fill='x')

        order_lines, totals = logic.build_order_lines(last_order, self.item_lookup)

        # Build a comma separated list of what was in the last order
        items_text = ",  ".join(label for label, _, _ in order_lines)

        frame_body = Frame(frame_banner, bg=BROWN, padx=14, pady=8)
        frame_body.pack(fill='x')

        Label(frame_body, text=items_text,
              font=("Helvetica", 10), bg=BROWN, fg="#FAECE7",
              wraplength=480, justify='left').pack(anchor='w')

        cal_text = (f"{totals['calories']} cal  ·  {totals['protein']}g protein  ·  "
                    f"{totals['carbs']}g carbs  ·  {totals['fat']}g fat")
        Label(frame_body, text=cal_text,
              font=("Helvetica", 10, "bold"), bg=BROWN, fg="white").pack(anchor='w', pady=(4, 0))

    def load_last_order(self, last_order):
        # Loads the saved order into selections and jumps to the summary step

        self.selections = last_order

        # Sync the tk variables to match the loaded order
        self.qesa_veg_var.set(self.selections["qesa_veggies"])
        self.double_var.set(self.selections["double_protein"])

        # Jump straight to the last step (summary)
        steps = logic.active_steps(self.selections)
        self.current_step = len(steps) - 1

        self.show_step()

    def render_single(self, step_id, allow_none):
        # Renders a step where the user picks one option using radio buttons.
        # Clicking any row highlights it and saves the choice.

        self.single_step = step_id
        items = self.categories.get(step_id, [])

        # Restore what was saved before, or default to first item / none
        if self.selections[step_id] is not None:
            init_val = self.selections[step_id]
        elif allow_none:
            init_val = "__none__"
        else:
            init_val = items[0]["item_name"] if items else ""

        self.single_var.set(init_val)

        # Outer card frame
        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        # Keep track of every widget in each row so we can change their color
        # when the user picks a different option
        # row_widgets[val] = list of all widgets in that row
        row_widgets = {}
        accent_bars = {}

        def select(val):
            # Called when user clicks a row — updates color of all rows
            self.single_var.set(val)
            for v in row_widgets:
                if v == val:
                    new_bg = SEL_BG
                    new_accent = ACCENT
                else:
                    new_bg = CARD_BG
                    new_accent = CARD_BG
                for w in row_widgets[v]:
                    try:
                        w.configure(bg=new_bg)
                    except:
                        pass
                accent_bars[v].configure(bg=new_accent)

        def add_row(val, label_text, sublabel_text):
            if val == init_val:
                row_bg = SEL_BG
                accent_bg = ACCENT
            else:
                row_bg = CARD_BG
                accent_bg = CARD_BG

            frame_row = Frame(frame_card, bg=row_bg, cursor="hand2")
            frame_row.pack(fill='x')

            frame_accent = Frame(frame_row, bg=accent_bg, width=4)
            frame_accent.pack(side='left', fill='y')

            frame_inner = Frame(frame_row, bg=row_bg, padx=10, pady=9)
            frame_inner.pack(side='left', fill='x', expand=True)

            rb = Radiobutton(frame_inner, variable=self.single_var, value=val,
                             bg=row_bg, activebackground=row_bg,
                             highlightthickness=0,
                             command=lambda v=val: select(v))
            rb.pack(side='left', padx=(0, 6))

            Label(frame_inner, text=label_text, font=("Helvetica", 11),
                  bg=row_bg, fg=TEXT_MAIN, anchor='w').pack(side='left')

            if sublabel_text:
                Label(frame_inner, text=sublabel_text, font=("Helvetica", 10),
                      bg=row_bg, fg=TEXT_MUTED).pack(side='right', padx=6)

            Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

            # Store every widget in this row so select() can recolor them
            row_widgets[val] = [frame_row, frame_inner, rb]
            accent_bars[val] = frame_accent

            # Clicking anywhere on the row works the same as the radio button
            frame_row.bind('<Button-1>',   lambda e, v=val: select(v))
            frame_inner.bind('<Button-1>', lambda e, v=val: select(v))
            frame_accent.bind('<Button-1>',lambda e, v=val: select(v))

        if allow_none:
            add_row("__none__", "None", "")

        for item in items:
            if item["calories"] > 0:
                sub = f"{item['calories']} cal  ·  {item['portion']}"
            else:
                sub = item["portion"]
            add_row(item["item_name"], item["item_name"], sub)

    def render_toggle(self):
        # Renders the double protein step — just a single checkbox

        self.double_var.set(self.selections["double_protein"])

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        Label(frame_card, text="Double protein?", font=("Helvetica", 12, "bold"),
              bg=CARD_BG, fg=TEXT_MAIN, anchor='w', padx=14, pady=10).pack(fill='x')
        Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

        frame_inner = Frame(frame_card, bg=CARD_BG, padx=14, pady=14)
        frame_inner.pack(fill='x')

        Checkbutton(frame_inner, text="Yes — double my protein",
                    variable=self.double_var,
                    font=("Helvetica", 12),
                    bg=CARD_BG, fg=TEXT_MAIN,
                    activebackground=CARD_BG, selectcolor=CARD_BG,
                    cursor="hand2").pack(anchor='w')

        if self.selections["protein"]:
            note = "Doubles calories, protein, carbs and fat for your protein choice."
        else:
            note = "No protein selected — this option has no effect."

        Label(frame_card, text=note, font=("Helvetica", 10),
              bg=CARD_BG, fg=TEXT_MUTED, padx=14, pady=6,
              wraplength=480, justify='left').pack(anchor='w')

    def render_multi(self, step_id):
        # Renders a step where the user can check multiple options

        self.multi_vars = {}
        items = self.categories.get(step_id, [])

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        if not items:
            Label(frame_card, text="No items available.",
                  font=("Helvetica", 11), bg=CARD_BG, fg=TEXT_MUTED, pady=12).pack()
            return

        # row_widgets and accent_bars let us recolor rows when checked/unchecked
        row_widgets = {}
        accent_bars = {}

        def recolor_row(name):
            if self.multi_vars[name].get():
                new_bg     = SEL_BG
                new_accent = ACCENT
            else:
                new_bg     = CARD_BG
                new_accent = CARD_BG
            for w in row_widgets[name]:
                try:
                    w.configure(bg=new_bg)
                except:
                    pass
            accent_bars[name].configure(bg=new_accent)

        def toggle(name):
            var = self.multi_vars[name]
            if var.get():
                if name not in self.selections[step_id]:
                    self.selections[step_id].append(name)
            else:
                if name in self.selections[step_id]:
                    self.selections[step_id].remove(name)
            recolor_row(name)

        def row_clicked(name):
            # Clicking the row flips the checkbox
            self.multi_vars[name].set(not self.multi_vars[name].get())
            toggle(name)

        for item in items:
            name    = item["item_name"]
            checked = name in self.selections[step_id]
            var     = BooleanVar(value=checked)
            self.multi_vars[name] = var

            if checked:
                row_bg     = SEL_BG
                accent_bg  = ACCENT
            else:
                row_bg     = CARD_BG
                accent_bg  = CARD_BG

            frame_row = Frame(frame_card, bg=row_bg, cursor="hand2")
            frame_row.pack(fill='x')

            frame_accent = Frame(frame_row, bg=accent_bg, width=4)
            frame_accent.pack(side='left', fill='y')

            frame_inner = Frame(frame_row, bg=row_bg, padx=10, pady=9)
            frame_inner.pack(side='left', fill='x', expand=True)

            cb = Checkbutton(frame_inner, variable=var,
                             bg=row_bg, activebackground=row_bg,
                             selectcolor=CARD_BG, highlightthickness=0,
                             cursor="hand2",
                             command=lambda n=name: toggle(n))
            cb.pack(side='left', padx=(0, 6))

            Label(frame_inner, text=name, font=("Helvetica", 11),
                  bg=row_bg, fg=TEXT_MAIN, anchor='w').pack(side='left')

            if item["calories"] > 0:
                sub = f"{item['calories']} cal  ·  {item['portion']}"
            else:
                sub = item["portion"]
            Label(frame_inner, text=sub, font=("Helvetica", 10),
                  bg=row_bg, fg=TEXT_MUTED).pack(side='right', padx=6)

            Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

            row_widgets[name]  = [frame_row, frame_inner, cb]
            accent_bars[name]  = frame_accent

            frame_row.bind('<Button-1>',    lambda e, n=name: row_clicked(n))
            frame_inner.bind('<Button-1>',  lambda e, n=name: row_clicked(n))
            frame_accent.bind('<Button-1>', lambda e, n=name: row_clicked(n))

    def render_qesa_veggies(self):
        # Renders the fajita veggies yes/no step for quesadillas
        # Works just like render_single but with True/False instead of item names

        self.qesa_veg_var.set(self.selections["qesa_veggies"])

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        Label(frame_card, text="Add fajita veggies?", font=("Helvetica", 12, "bold"),
              bg=CARD_BG, fg=TEXT_MAIN, anchor='w', padx=14, pady=10).pack(fill='x')
        Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

        frame_note = Frame(frame_card, bg=CARD_BG, padx=14, pady=6)
        frame_note.pack(fill='x')
        Label(frame_note,
              text="Your quesadilla already includes cheese. "
                   "Would you like fajita veggies added inside?",
              font=("Helvetica", 10), bg=CARD_BG, fg=TEXT_MUTED,
              wraplength=480, justify='left').pack(anchor='w')

        row_widgets = {}
        accent_bars = {}

        def pick(val):
            self.qesa_veg_var.set(val)
            for v in row_widgets:
                if v == val:
                    new_bg     = SEL_BG
                    new_accent = ACCENT
                else:
                    new_bg     = CARD_BG
                    new_accent = CARD_BG
                for w in row_widgets[v]:
                    try:
                        w.configure(bg=new_bg)
                    except:
                        pass
                accent_bars[v].configure(bg=new_accent)

        def add_row(val, label_text, sublabel_text):
            if val == self.qesa_veg_var.get():
                row_bg    = SEL_BG
                accent_bg = ACCENT
            else:
                row_bg    = CARD_BG
                accent_bg = CARD_BG

            frame_row = Frame(frame_card, bg=row_bg, cursor="hand2")
            frame_row.pack(fill='x')

            frame_accent = Frame(frame_row, bg=accent_bg, width=4)
            frame_accent.pack(side='left', fill='y')

            frame_inner = Frame(frame_row, bg=row_bg, padx=10, pady=9)
            frame_inner.pack(side='left', fill='x', expand=True)

            rb = Radiobutton(frame_inner, variable=self.qesa_veg_var, value=val,
                             bg=row_bg, activebackground=row_bg,
                             highlightthickness=0,
                             command=lambda v=val: pick(v))
            rb.pack(side='left', padx=(0, 6))

            Label(frame_inner, text=label_text, font=("Helvetica", 11),
                  bg=row_bg, fg=TEXT_MAIN, anchor='w').pack(side='left')

            if sublabel_text:
                Label(frame_inner, text=sublabel_text, font=("Helvetica", 10),
                      bg=row_bg, fg=TEXT_MUTED).pack(side='right', padx=6)

            Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

            row_widgets[val] = [frame_row, frame_inner, rb]
            accent_bars[val] = frame_accent

            frame_row.bind('<Button-1>',    lambda e, v=val: pick(v))
            frame_inner.bind('<Button-1>',  lambda e, v=val: pick(v))
            frame_accent.bind('<Button-1>', lambda e, v=val: pick(v))

        add_row(False, "No thanks", "")
        add_row(True, "Yes, add fajita veggies", "20 cal  ·  3 oz")

    def render_calorie_goal(self):
        # Renders the calorie limit entry step.
        # The user types a number and clicks Check, or leaves it blank to skip.

        frame_outer = Frame(self.frame_content, bg=BG, padx=16, pady=8)
        frame_outer.pack(fill='x')
        frame_card = Frame(frame_outer, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        Label(frame_card, text="Set your meal calorie limit",
              font=("Helvetica", 12, "bold"),
              bg=CARD_BG, fg=TEXT_MAIN, anchor='w', padx=14, pady=10).pack(fill='x')
        Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

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

        # Pre-fill with what was saved before
        saved = self.selections.get("calorie_goal")
        if saved is None:
            self.entry_calorie_text = StringVar(value="")
        else:
            self.entry_calorie_text = StringVar(value=str(saved))

        self.entry_calorie = Entry(frame_entry, textvariable=self.entry_calorie_text,
                                   font=("Helvetica", 12), width=10,
                                   relief='flat', bd=1,
                                   highlightthickness=1,
                                   highlightbackground=BORDER_COLOR,
                                   highlightcolor=ACCENT)
        self.entry_calorie.pack(side='left', padx=(10, 0))
        self.entry_calorie.focus_set()

        # Error label — shown when input is bad
        self.label_calorie_error = Label(frame_card, text="",
                                          font=("Helvetica", 10),
                                          bg=CARD_BG, fg=RESET_BG,
                                          padx=14, pady=4)
        self.label_calorie_error.pack(anchor='w')

    def render_summary(self):
        # Renders the final summary page with macro cards and item list

        order_lines, totals = logic.build_order_lines(self.selections, self.item_lookup)
        limit     = self.selections.get("calorie_goal")
        cal_total = totals["calories"]

        # Macro cards — calories card goes red if over the limit
        frame_macros = Frame(self.frame_content, bg=BG, padx=16, pady=10)
        frame_macros.pack(fill='x')

        if limit is not None and cal_total > limit:
            cal_color = COLOR_WARN
        else:
            cal_color = COLOR_CAL

        macros = [
            ("Calories", str(cal_total),           cal_color),
            ("Protein",  str(totals["protein"])+"g", COLOR_PRO),
            ("Carbs",    str(totals["carbs"])+"g",   COLOR_CARB),
            ("Fat",      str(totals["fat"])+"g",      COLOR_FAT),
        ]

        col = 0
        for lbl, val, color in macros:
            cell = Frame(frame_macros, bg=color, padx=6, pady=8)
            cell.grid(row=0, column=col, padx=4, sticky='nsew')
            frame_macros.columnconfigure(col, weight=1)
            Label(cell, text=val, font=("Helvetica", 18, "bold"),
                  bg=color, fg="white").pack()
            Label(cell, text=lbl, font=("Helvetica", 9),
                  bg=color, fg="white").pack()
            col += 1

        # Calorie limit bar — only shows if the user set a limit
        if limit is not None:
            frame_outer2 = Frame(self.frame_content, bg=BG, padx=16, pady=4)
            frame_outer2.pack(fill='x')
            frame_limit_card = Frame(frame_outer2, bg=CARD_BG,
                                     highlightthickness=1, highlightbackground=BORDER_COLOR)
            frame_limit_card.pack(fill='x')

            Label(frame_limit_card, text="Meal calorie limit",
                  font=("Helvetica", 12, "bold"),
                  bg=CARD_BG, fg=TEXT_MAIN, anchor='w', padx=14, pady=10).pack(fill='x')
            Frame(frame_limit_card, bg=BORDER_COLOR, height=1).pack(fill='x')

            frame_limit = Frame(frame_limit_card, bg=CARD_BG, padx=14, pady=10)
            frame_limit.pack(fill='x')

            remaining = limit - cal_total
            if cal_total <= limit:
                bar_color = COLOR_GOOD
                status    = f"{remaining} kcal remaining"
            else:
                bar_color = COLOR_WARN
                status    = f"{-remaining} kcal over your limit"

            Label(frame_limit,
                  text=f"{cal_total} / {limit} kcal  —  {status}",
                  font=("Helvetica", 11, "bold"),
                  bg=CARD_BG, fg=bar_color).pack(anchor='w', pady=(0, 6))

            # Draw the bar as two stacked frames (track + fill)
            frame_bar_track = Frame(frame_limit, bg=BORDER_COLOR, height=12)
            frame_bar_track.pack(fill='x')
            frame_bar_track.update_idletasks()
            bar_w = frame_bar_track.winfo_width() or 540
            pct   = min(cal_total / limit, 1.0)
            Frame(frame_bar_track, bg=bar_color, height=12,
                  width=int(bar_w * pct)).place(x=0, y=0)

        # Item list
        frame_outer3 = Frame(self.frame_content, bg=BG, padx=16, pady=4)
        frame_outer3.pack(fill='x')
        frame_card = Frame(frame_outer3, bg=CARD_BG,
                           highlightthickness=1, highlightbackground=BORDER_COLOR)
        frame_card.pack(fill='x')

        Label(frame_card, text="Your order", font=("Helvetica", 12, "bold"),
              bg=CARD_BG, fg=TEXT_MAIN, anchor='w', padx=14, pady=10).pack(fill='x')
        Frame(frame_card, bg=BORDER_COLOR, height=1).pack(fill='x')

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
        # Reads the current step's widget state and saves it to self.selections.
        # Multi steps save automatically on each click so nothing needed there.

        steps = logic.active_steps(self.selections)
        _, kind, _ = steps[self.current_step]

        if kind == "single":
            val = self.single_var.get()
            if val == "__none__":
                self.selections[self.single_step] = None
            else:
                self.selections[self.single_step] = val

        elif kind == "toggle":
            self.selections["double_protein"] = self.double_var.get()

        elif kind == "qesa_veggies":
            self.selections["qesa_veggies"] = self.qesa_veg_var.get()



        elif kind == "calorie_goal":
            # Read from the local entry var we created in render_calorie_goal
            raw = self.entry_calorie_text.get()
            ok, parsed, _ = logic.validate_calorie_goal(raw)
            if ok:
                self.selections["calorie_goal"] = parsed

    def go_next(self):
        # Saves current step and tries to move forward.
        # Shows errors if base not selected or calorie input is bad.
        # Shows a warning popup if the order is over the calorie limit.

        self.save_step()

        steps   = logic.active_steps(self.selections)
        step_id, kind, _ = steps[self.current_step]
        last    = len(steps) - 1

        # Base is required
        if step_id == "base" and not self.selections["base"]:
            self.show_popup("Please choose a base before continuing.")
            return

        # Check calorie input is valid before moving past that step
        if kind == "calorie_goal":
            raw = self.entry_calorie_text.get()
            ok, _, err = logic.validate_calorie_goal(raw)
            if not ok:
                self.label_calorie_error.config(text=err)
                return

        # If moving to summary, check if over the limit
        if self.current_step == last - 1:
            limit = self.selections.get("calorie_goal")
            if limit is not None:
                totals  = logic.calculate_totals(self.selections, self.item_lookup)
                over_by = totals["calories"] - limit
                if over_by > 0:
                    self.show_over_limit_dialog(over_by)
                    return

        if self.current_step < last:
            self.current_step += 1
            self.show_step()

    def show_over_limit_dialog(self, over_by):
        # Pops up a yes/no dialog when the meal is over the calorie limit.
        # Yes = go back one step keeping all selections.
        # No = go to summary anyway.

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

        Label(pop, text="Would you like to go back and change something?",
              font=("Helvetica", 11), bg=CARD_BG, fg=TEXT_MAIN,
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
        # Saves the current step and moves back one step

        self.save_step()
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()

    def update_nav_buttons(self):
        # Updates the Back and Next/Summary/Done buttons based on which step we're on

        steps = logic.active_steps(self.selections)
        last  = len(steps) - 1

        if self.current_step == 0:
            self.button_back.config(state='disabled')
        else:
            self.button_back.config(state='normal')

        if self.current_step == last:
            self.button_next.config(text="Done", state='normal',
                                    command=self.finish_order)
        elif self.current_step == last - 1:
            self.button_next.config(text="Summary ->", state='normal',
                                    command=self.go_next)
        else:
            self.button_next.config(text="Next ->", state='normal',
                                    command=self.go_next)

    def finish_order(self):
        # Called when the user clicks Done on the summary page.
        # Saves the order to the CSV history file then resets.

        try:
            logic.save_order_to_csv(self.selections, self.item_lookup)
        except OSError as e:
            self.show_popup(f"Could not save order:\n{e}")

        self.reset_all()

    def reset_all(self):
        # Resets everything back to a blank order and goes to step 1

        self.selections   = logic.fresh_selections()
        self.current_step = 0
        self.double_var.set(False)
        self.qesa_veg_var.set(False)
        self.show_step()

    def show_popup(self, msg):
        # Shows a small centered dialog with a message and an OK button

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