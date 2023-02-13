def input_prompt(message):
    return input(message + "\n")


def tkinter_input_prompt(message):
    # sorta defeats the purpose of this library, but why not...
    from tkinter import simpledialog
    # avoid "cancel" button?
    answer = simpledialog.askstring("Input", message)
    return answer if answer else ""
