import numpy as np
import screeninfo
from PIL import Image, ImageTk
import tkinter as tk

monitor = 0

def generate_white_noise_frame(width, height):
    return Image.fromarray(np.random.randint(low=0, high=255, size=(height, width), dtype=np.uint8))


class ImageDisplay(tk.Toplevel):
    def __init__(self, monitor: int):
        assert isinstance(monitor, int) and monitor >= 0, "Monitor must be a non-negative integer!"

        super().__init__()

        # Get information about all monitors
        monitors = screeninfo.get_monitors()



        if len(monitors) <= monitor:
            raise Exception(f"Monitor index {monitor} is out of range. Found {len(monitors)} monitors.")

        # Select the specified monitor
        selected_monitor = monitors[monitor]
        self.width, self.height = selected_monitor.width, selected_monitor.height

        self.geometry(f"{self.width}x{self.height}+{selected_monitor.x}+{selected_monitor.y}")
        self.configure(background='black')

        self.overrideredirect(True)

        # Initialize the label to None
        self.label = None

    def show_image(self, image_object):
        assert isinstance(image_object, Image.Image), "Image must be a PIL Image object"

        photo = ImageTk.PhotoImage(image_object)

        if self.label is None:
            # Create a label to hold the image
            self.label = tk.Label(self, image=photo)
            self.label.image = photo  # Keep a reference to avoid garbage collection
            self.label.pack()
        else:
            self.__update_image(photo)

    def __update_image(self, photo):
        assert isinstance(photo, ImageTk.PhotoImage), "Image must be a PhotoImage object"

        # Update the image in the existing label
        self.label.configure(image=photo)
        self.label.image = photo  # Update the reference to avoid garbage collection

    class NoSecondMonitorError(Exception):
        pass


class App(tk.Tk):
    def __init__(self, monitor: int):
        super().__init__()
        self.image_display = ImageDisplay(monitor)

        self.protocol("WM_DELETE_WINDOW")

        self.run_white_noise()

        self.mainloop()

    def run_white_noise(self):
        frame = generate_white_noise_frame(self.image_display.width, self.image_display.height)
        self.image_display.show_image(frame)
        self.after(20, self.run_white_noise)


App(monitor)