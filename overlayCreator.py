import tkinter as tk
from queue import Queue
import threading
from time import sleep


class TransparentOverlay:
    def __init__(self, box_size=10, duration=1):
        self.box_size = box_size
        self.duration = duration * 1000
        self.queue = Queue()
        self.root = None
        self.gui_thread = threading.Thread(target=self.init_gui, daemon=True)
        self.gui_thread.start()

    def init_gui(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.after(100, self.process_queue)
        self.root.mainloop()

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get()
            if item[0] == "point":
                _, x, y, callback = item
                self.create_window(x, y, callback)
            elif item[0] == "rect":
                _, pos0, pos1, callback = item
                self.create_rectangle_window(pos0, pos1, callback)
            elif item[0] == "follow_mouse":
                _, width, height, callback = item
                self.follow_mouse_overlay(width, height, callback)
        self.root.after(100, self.process_queue)

    # quadradinho simples no ponto (x, y)
    def create_overlay(self, x, y, callback=None):
        self.queue.put(("point", x, y, callback))

    # retângulo definido por dois pontos (canto sup. esq e inf. dir)
    def rectangle_overlay(self, pos0, pos1, callback=None):
        self.queue.put(("rect", pos0, pos1, callback))

    # retângulo fixo que segue o mouse
    def follow_mouse(self, width, height, callback=None):
        self.queue.put(("follow_mouse", width, height, callback))

    def create_window(self, x, y, callback):
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.wm_attributes('-transparentcolor', 'white')

        canvas = tk.Canvas(
            overlay,
            width=self.box_size * 2,
            height=self.box_size * 2,
            bg="white",
            highlightthickness=0,
        )
        canvas.pack()

        overlay.geometry(f"+{x - self.box_size // 2}+{y - self.box_size // 2}")
        canvas.create_rectangle(
            0, 0, self.box_size, self.box_size, outline="red", width=2
        )

        overlay.after(self.duration, overlay.destroy)
        if callback:
            overlay.after(self.duration, callback)

        return overlay

    def create_rectangle_window(self, pos0, pos1, callback=None):
        (x0, y0), (x1, y1) = pos0, pos1
        width = abs(x1 - x0)
        height = abs(y1 - y0)

        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.wm_attributes('-transparentcolor', 'white')

        canvas = tk.Canvas(
            overlay,
            width=width,
            height=height,
            bg="white",
            highlightthickness=0,
        )
        canvas.pack()

        overlay.geometry(f"{width}x{height}+{min(x0, x1)}+{min(y0, y1)}")
        canvas.create_rectangle(0, 0, width, height, outline="green", width=2, fill="")

        overlay.after(self.duration, overlay.destroy)
        if callback:
            overlay.after(self.duration, callback)
        return overlay

    def follow_mouse_overlay(self, width, height, callback=None):
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.wm_attributes('-transparentcolor', 'white')

        canvas = tk.Canvas(
            overlay,
            width=width,
            height=height,
            bg="white",  # fundo invisível
            highlightthickness=0,
        )
        canvas.pack()

        canvas.create_rectangle(0, 0, width, height, outline="blue", width=2, fill="")

        def update_position():
            if not overlay.winfo_exists():
                return
            x = overlay.winfo_pointerx()
            y = overlay.winfo_pointery()
            # centralizar no mouse:
            overlay.geometry(f"{width}x{height}+{x}+{y}")
            overlay.after(30, update_position)  # ~33 fps

        update_position()

        overlay.after(self.duration, overlay.destroy)
        if callback:
            overlay.after(self.duration, callback)
        
        return overlay

if __name__ == "__main__":
    overlay = TransparentOverlay(duration=2)

    # 1. quadrado em um ponto
    overlay.create_overlay(300, 300)

    # 2. retângulo fixo entre dois pontos
    overlay.rectangle_overlay((100, 100), (250, 180))

    # 3. retângulo que segue o mouse
    overlay.follow_mouse(120, 80)
    
    input()

