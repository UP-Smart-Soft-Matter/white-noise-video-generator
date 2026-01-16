import math
import time
import numpy as np
import screeninfo
from PIL import Image, ImageTk
import tkinter as tk
import matplotlib.pyplot as plt
from pax1000_controller import PAX1000
import threading
from tkinter import messagebox

monitor = 1
# max. FPS for SLM is 60
fps = 10
temporal_white_noise = True

period = math.ceil(1/fps * 1000)

class ImageDisplay(tk.Toplevel):
    def __init__(self, monitor: int):
        assert isinstance(monitor, int) and monitor >= 0, "Monitor must be a non-negative integer!"

        super().__init__()

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

        self.protocol("WM_DELETE_WINDOW", self.close)

        self.measure_thread = MeasuringThread()
        self.measure_thread.start()
        time.sleep(1)

        print('PAX1000 starting up')
        while self._is_result_none():
            pass
        print('PAX1000 start up finished')

        self.rand_values = []
        self.azimuth = []

        if temporal_white_noise:
            self.run_temporal_white_noise()
            self.show_histogram()
        else:
            self.run_spatial_white_noise()

        self.mainloop()

    def run_spatial_white_noise(self):
        random_grayscale_matrix = np.random.randint(low=0, high=256, size=(self.image_display.height, self.image_display.width), dtype=np.uint8)
        frame = Image.fromarray(random_grayscale_matrix)
        self.image_display.show_image(frame)
        self.after(period, self.run_spatial_white_noise)

    def run_temporal_white_noise(self):
        random_grayscale_value = np.random.randint(low=0, high=256)
        self.rand_values.append(random_grayscale_value)
        frame = Image.fromarray(np.full((self.image_display.height, self.image_display.width), random_grayscale_value, dtype=np.uint8))
        with self.measure_thread.azimuth_lock:
            azimuth = self.measure_thread.azimuth
            print(azimuth)
        self.azimuth.append(azimuth)
        self.image_display.show_image(frame)
        self.after(period, self.run_temporal_white_noise)

    def show_histogram(self):
        np.savetxt("histogram.txt", self.rand_values)
        np.savetxt("azimuth.txt", self.azimuth)
        fig, ax = plt.subplots(1, 2, figsize=(12, 4))
        ax[0].set_title('Histogram Grayscale values')
        ax[0].hist(self.rand_values, bins=256)
        ax[0].set_xlabel('Grayscale values')
        ax[0].set_ylabel('counts')
        ax[1].set_title('Histogram Azimuth')
        ax[1].hist(self.azimuth, bins=180)
        ax[1].set_xlabel('Azimuth in degrees')
        plt.text(0.5, 0.8, f"N={len(self.rand_values)}", ha='center', va='center')
        fig.tight_layout()
        plt.show()
        self.after(1000, self.show_histogram)

    def _is_result_none(self):
        with (self.measure_thread.azimuth_lock):
            result = self.measure_thread.azimuth
        time.sleep(0.2)

        if result is None:
            return True
        else:
            return False

    def close(self):
        with self.measure_thread.kill_flag_lock:
            self.measure_thread.kill_flag = True

def init_pax():
    """
    Initializes a connection to a PAX1000 device.

    Repeatedly attempts to create a PAX1000 instance until successful.
    Displays an error dialog if the device is not detected.

    Returns
    -------
    PAX1000
        Initialized PAX1000 controller object.
    """
    while True:
        try:
            pax = PAX1000()
            return pax
        except Exception:
            messagebox.showerror("Error", "No PAX 1000 found, please connect device and try again")
            continue

class MeasuringThread(threading.Thread):
    """
    Thread that continuously polls azimuth values from the PAX1000 device.

    Stores the latest reading and stops when the kill flag is set.
    """
    def __init__(self):
        """
        Initializes the measuring thread and required synchronization locks.
        """
        super().__init__()
        self.kill_flag = False
        self.kill_flag_lock = threading.Lock()

        self.azimuth = None
        self.azimuth_lock = threading.Lock()

        self.__pax = None

    def run(self):
        """
        Connects to the PAX1000 and continuously updates the azimuth value
        until the kill flag is triggered.
        """
        self.__pax = init_pax()
        while not self.kill_flag:
            azimuth = self.__pax.measure()["azimuth"]
            with self.azimuth_lock:
                self.azimuth = azimuth
        self.__pax.close()

App(monitor)