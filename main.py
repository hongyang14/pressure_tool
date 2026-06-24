import tkinter as tk

from app.gui.main_window import PressureTestMainWindow


def main():
    root = tk.Tk()
    PressureTestMainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()