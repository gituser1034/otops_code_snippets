# Ares' Amazing Cameras (OTOPS 2026)
# Olly Love
# 2025/2026 Interface for controlling the OTOPS rover cameras at CIRC
# Layouts/Design for each camera stream and its controls

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

gi.require_version("Gst", "1.0")
from gi.repository import Gst

# for taking 
# I have version 4.6.0 - GS version just needs to match the features im using
# sudo apt update
# sudo apt install python3-dev python3-pip -y
# pip install opencv-python
import cv2 as cv
import time
import glob

# Make sure file paths match groundstation

# Grid Layout of a camera stream interface, with the stream, and control buttons
# Consists of a main outer grid (Placeholder/stream, inner grid)
# inner grid is a small menu for button placement
class BaseCamGrid(Gtk.Grid):
    def __init__(self, placement, pipeline_str, sink):
        Gst.init(None)
        Gtk.Grid.__init__(self)
        self.placement = placement
        # Stores string used to create gstreamer pipeline
        self.pipeline_str = pipeline_str
        self.pipeline = None
        self.sink = sink
        # Size of small stream, overwritten in child for large camera
        self.width = 525
        self.height = 295
        
        # Main grid everythings added to
        self.main_cam_grid = Gtk.Grid()
        self.add(self.main_cam_grid)
        self.main_cam_grid.set_row_spacing(2)
        self.main_cam_grid.set_column_spacing(2)
        # Inner grid for on/off buttons and camera label 
        self.inner_cam_grid = Gtk.Grid()
        self.inner_cam_grid.set_row_spacing(2)
        self.inner_cam_grid.set_column_spacing(5)

        self.placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_screen_size()
        self.placeholder.set_halign(Gtk.Align.START)
        self.placeholder.set_valign(Gtk.Align.START)
        # Background color is black
        self.placeholder.override_background_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(0, 0, 0, 1)
        )

        self.cam_lbl = Gtk.Label()
        # Change text color
        color = Gdk.RGBA()
        color.parse("black")
        self.cam_lbl.override_color(Gtk.StateFlags.NORMAL, color)
        # Large text - can't seem to control font with numbers
        self.cam_lbl.set_markup(f"<big>{self.placement}</big>")

        # Create, connect, and add buttons to the display
        self.on_btn = Gtk.Button(label="On")
        self.off_btn = Gtk.Button(label="Off")

        self.on_btn.connect("clicked", self.on_btn_click)
        self.off_btn.connect("clicked", self.off_btn_click)

        self.inner_cam_grid.attach(self.cam_lbl,0,0,1,1)
        self.inner_cam_grid.attach(self.on_btn,1,0,1,1)
        self.inner_cam_grid.attach(self.off_btn,2,0,1,1)
        self._build_swaps()
        self._build_pic_takers()
        self.main_cam_grid.attach(self.placeholder,0,0,1,1)
        self.main_cam_grid.attach(self.inner_cam_grid,0,1,1,1)

    def set_screen_size(self):
        self.placeholder.set_size_request(self.width, self.height)

    def stream_on(self):
        # Only turn stream on when its off
        if not self.pipeline:
            self.pipeline = Gst.parse_launch(self.pipeline_str)
            gtksink = self.pipeline.get_by_name(self.sink)
            # Bunch of other lines hidden for confidentiality
        else:
            print("Error: Stream already on.")

    def stream_off(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            # Other lines hidden for confidentiality
        else:
            print("ERROR: Stream already disconnected.")

    def on_btn_click(self, widget):
        self.stream_on()

    def off_btn_click(self, widget):
        self.stream_off()
        
    # Overwritten by large cam grid child - basecam does nothing with this
    def _build_swaps(self):
        pass

    # Overwritten by large cam grid child - basecam ignores
    def _build_pic_takers(self):
        pass

# This grid fits the large placeholder and has extra buttons to control swapping 
# and resetting cameras 
class LargeCamGrid(BaseCamGrid):
    def __init__(self, placement, pipeline_str, sink, url, swap_callback):
        super().__init__(placement, pipeline_str, sink)

        self.url = url
        self.swap_callback = swap_callback
        self.width = 1280
        self.height = 960
        self.set_screen_size()
        # For tracking swaps
        self.left_shown = False
        self.front_shown = False
        self.right_shown = False
        self.back_shown = False

    def set_screen_size(self):
        self.placeholder.set_size_request(self.width, self.height)

    # Swap buttons to allow swapping camera streams
    def _build_swaps(self):
        self.show_left_btn = Gtk.Button(label="Show Left")
        self.show_left_btn.connect("clicked", self.show_left_btn_click)
        self.inner_cam_grid.attach(self.show_left_btn,3,0,1,1)

        # ... 

    # Build buttons for taking pictures and panoramas
    # may need callbacks like how swap works for main to request pics
    def _build_pic_takers(self):
        self.pic_taker_btn = Gtk.Button(label="Take Picture")
        self.pic_taker_btn.connect("clicked", self.pic_taker_btn_click)
        self.inner_cam_grid.attach(self.pic_taker_btn,7,0,1,1)

        # ...

    # Using a callback function in main window, sending keyword "Left"
    # back to main window controlling swaps to swap based on the button pressed
    # ...

    # Captures a single frame (picture) from camera stream
    def snap(self, path):
        # code to grab a frame from stream, hidden
        pass

    # Take picture from stream
    def pic_taker_btn_click(self, widget):
        # Get time of photo to prevent overwriting - creates unique photo names
        ts = int(time.time())
        path = f"public_cam_gui/pictures/photo{ts}.jpg"
        self.snap(path)

    # Every interval take a pic as user rotating the rover, then stitch together as a panorama
    # If rotation fast, interval < 0.5 seconds, if slow 1 second or even higher
    # May later add GPS
    def panorama_btn_click(self, widget):
        ts = int(time.time())
        pan_frames = []
        pan_data = "public_cam_gui/panorama_data"
        pan_complete = "public_cam_gui/panoramas"

        # Create list of images from panorama_data folder
        for img_path in glob.glob(f"{pan_data}/*.jpg"):
            img = cv.imread(img_path)
            if img is not None:
                # Debugging
                # print("Image in list")
                # cv.imshow("test",img)
                # cv.waitKey(0)
                # cv.destroyAllWindows()
                pan_frames.append(img)

        print("Panorama pictures gathered.")

        # Stitch pics together for a finished panorama
        # Creating from list of frames
        stitcher = cv.Stitcher_create(cv.Stitcher_PANORAMA)
        status, panorama = stitcher.stitch(pan_frames)
        if status == cv.Stitcher_OK:
            cv.imwrite(f"{pan_complete}/pan{ts}.jpg", panorama)
        else:
            print("ERROR: Failed to stitch panorama:", status)
        
