# main.py
# This is the entry point for the Chipotle Nutrition Calculator.
# Run this file to start the program.
# - logic.py handles all the data and calculations
# - gui.py handles all the GUI/window stuff
# - main.py just loads the data and starts the window

from tkinter import Tk, messagebox
import logic
import gui


def main():
    # Load the menu data from the CSV file
    # If something goes wrong, show an error and exit cleanly
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

    # Everything loaded fine — create the window and start the app
    root = Tk()
    gui.ChipotleApp(root, menu_data)
    root.mainloop()


if __name__ == "__main__":
    main()