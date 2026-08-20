# Ares' Amazing Cameras (OTOPS 2026) - testing with test sources
# Olly Love
# 2025/2026 Interface for controlling the OTOPS rover cameras at CIRC
# Helpful Source: https://www.youtube.com/watch?v=FszqUfibD3w
# Note: Server must be running for cameras to be able to connect to it
# Make sure the IP addresses match that of the server

# Installs: 
# sudo apt update
# sudo apt install python3 python3-pip python3-venv
# Install Gstreamer here: https://gstreamer.freedesktop.org/documentation/installing/on-linux.html?gi-language=c
# sudo apt install libgtk-3-dev gir1.2-gtk-3.0 python3-gi python3-gi-cairo
# sudo apt install gstreamer1.0-gtk3

# If face issues on groundstation, run like this:
# GDK_BACKEND=x11 python3 gui_v2.py

# How to run stream when developing - will later be just ./rtspstream
# gcc latest-rtspstream.c $(pkg-config --cflags --libs gstreamer-rtsp-server-1.0)
# ./a.out

# Debugging purposes:
# Scan for camera specs: 
# v4l2-ctl --list-devices
# v4l2-ctl --list-formats-ext --device /dev/video0

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from base_cam_grid import BaseCamGrid, LargeCamGrid

# Main window of the software, displays everything in a root container
# Controls swap functionality
class MainWindow(Gtk.Window):
    def __init__(self):
        # Super classes constructor
        Gtk.Window.__init__(self, title="Ares' Amazing Cameras (OTOPS 2026)")
        # Size to perfectly fit groundstation
        self.set_default_size(1850,1000)
        # Light gray background
        self.override_background_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(0.5, 0.5, 0.5, 1)
        )

        # Main root container which holds everything
        root_grid = Gtk.Grid()
        self.add(root_grid)

        # Allign in the center and padding between items
        root_grid.set_halign(Gtk.Align.CENTER)
        root_grid.set_valign(Gtk.Align.CENTER)
        root_grid.set_row_spacing(2)
        root_grid.set_column_spacing(2)

        # 1 H264 webcam, 3 mjpeg innomakers
        
        # Gstreamer connection pipeline strings - This ip for on rover nanobeam/prism network
        # Large and small streams to fit large and small windows
        self.front_line = "rtspsrc location=rtsp://localhost:8554/front latency=0 drop-on-latency=true ! rtph264depay ! queue ! h264parse ! avdec_h264 ! videoconvert ! gtksink name=sink"
        self.front_line_small = "rtspsrc location=rtsp://localhost:8554/front latency=0 drop-on-latency=true ! rtph264depay ! queue ! h264parse ! avdec_h264 ! videoconvert ! videoscale ! video/x-raw, width=525, height=295 ! gtksink name=sink"
        self.left_line_small = "jpeg line placeholder"
        self.left_line_large = "jpeg line placeholder"
        self.right_line_small = "jpeg line placeholder"
        self.right_line_large = "jpeg line placeholder"
        self.back_line_small = "jpeg line placeholder"
        self.back_line_large = "jpeg line placeholder"

        self.front_cam_sink = "sink"
        self.left_cam_sink = "sink2"
        self.right_cam_sink = "sink3"
        self.back_cam_sink = "sink4"

        # opencv accesses these to take pictures
        self.front_url = "portion of url for pictures placeholder"
        self.left_url = "portion of url for pictures placeholder"
        self.right_url = "portion of url for pictures placeholder"
        self.back_url = "portion of url for pictures placeholder"

        # Uses a callback function to request data from the swap button pressed
        self.front_cam_grid = LargeCamGrid("Front", self.front_line, self.front_cam_sink, self.front_url, self.swap)
        self.left_cam_grid = BaseCamGrid("Left", self.left_line_small, self.left_cam_sink)
        self.right_cam_grid = BaseCamGrid("Right", self.right_line_small, self.right_cam_sink)
        self.back_cam_grid = BaseCamGrid("Back", self.back_line_small, self.back_cam_sink)
        
        # Col, Row, Width, Height
        root_grid.attach(self.front_cam_grid,0,0,1,3)
        root_grid.attach(self.left_cam_grid,1,0,1,1)
        root_grid.attach(self.right_cam_grid,1,1,1,1)
        root_grid.attach(self.back_cam_grid,1,2,1,1)

    # Swapping Front and target grid by switching pipelines and sinks around
    def front_swap(self, target_grid:BaseCamGrid,pipeline_str,sink,url,label_text):
        self.front_cam_grid.stream_off()
        target_grid.stream_off()

        # set to url of stream passed in for screenshots
        self.front_cam_grid.url = url

        # Show big target stream in main grid
        self.front_cam_grid.pipeline_str = pipeline_str
        self.front_cam_grid.sink = sink
        self.front_cam_grid.stream_on()
        self.front_cam_grid.cam_lbl.set_markup(f"<big>{label_text}</big>")

        # Show front stream in small target grid
        target_grid.pipeline_str = self.front_line_small
        target_grid.sink = self.front_cam_sink
        target_grid.stream_on()
        target_grid.cam_lbl.set_markup("<big>Front</big>")

    # Reset camera to its originally set stream to undo swaps
    def cam_reset(self,cam_grid:BaseCamGrid,pipeline_str,sink,label_text):
        cam_grid.stream_off()
        cam_grid.pipeline_str = pipeline_str
        cam_grid.sink = sink
        cam_grid.stream_on()
        cam_grid.cam_lbl.set_markup(f"<big>{label_text}</big>")

    # Swap controller, takes swap type and calls swap and reset methods
    # Swap always between a large front camera and a smaller camera
    def swap(self, value):
        if value == "Left" and self.front_cam_grid.left_shown == False:
            
            # Need to reset all other cams during swaps as otherwise front would just swap with
            # everything and all the small cams would be front, don't want to lose track of cams
            if self.right_cam_grid.pipeline:
                self.cam_reset(self.right_cam_grid,self.right_line_small, self.right_cam_sink,"Right")
            if self.back_cam_grid.pipeline:
                self.cam_reset(self.back_cam_grid,self.back_line_small, self.back_cam_sink,"Back")

            self.front_swap(self.left_cam_grid,self.left_line_large,self.left_cam_sink,self.left_url,value)

        # Many other lines for swaps confidential, deleted here
        
        else:
            print(f"ERROR: Swap error, streams already swapped")

window = MainWindow()
window.connect("delete-event", Gtk.main_quit)
window.show_all()
Gtk.main()