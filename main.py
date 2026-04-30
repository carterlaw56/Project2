from tkinter import Tk, messagebox
import logic
import gui

# Start the app
def main() -> None:
    """
    load menu from csv
    """
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

    # everything is loaded
    root = Tk()
    gui.ChipotleApp(root, menu_data)
    root.mainloop()


if __name__ == "__main__":
    main()