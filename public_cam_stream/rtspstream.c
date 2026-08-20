// Ares' Amazing Camera Stream (OTOPS 2026)
// Olly Love
// rtsp multi-camera stream. One rtsp server and port, multiple mounts, 
// each to view a different camera

// v4l2-ctl --list-devices
// Scan for hardware specs: 
// v4l2-ctl --list-formats-ext --device /dev/video0

// How to run:
// gcc latest-rtspstream.c $(pkg-config --cflags --libs gstreamer-rtsp-server-1.0)
// ./a.out

// Rename
// gcc latest-rtspstream.c -o rtspstream ...

// Monitor usb with lsusb -tv

#include <stdio.h>
#include <gst/gst.h>
#include <gst/rtsp-server/rtsp-server.h>

#define NUM_CAMERAS 4

// prev passed in char char * host, int port
void gst_rtsp_server_run(int port)
{
    GMainLoop *loop;
    GstRTSPServer *server;
    GstRTSPMountPoints *mounts;

    // Array of factory pointers - need a factory for each port
    GstRTSPMediaFactory *factories[NUM_CAMERAS];

    // Try a mjpeg pipeline for better cpu
    char *pipeline_descs[NUM_CAMERAS] = {
        
        // 640 by 480 highest quality for no delay so far - also 600 by 800 might be ok w rover setup
        // on real setup 1280 by 720 works
        "( v4l2src device=/dev/video0 is-live=true ! video/x-h264, width=640, height=480, framerate=30/1 ! \
		  h264parse ! rtph264pay name=pay0 pt=96 config-interval=1 )",
		   
		// 3 other lines for jpeg streams
    };

    gst_init(NULL, NULL);

    loop = g_main_loop_new(NULL, FALSE);

    server = gst_rtsp_server_new();
    g_object_set(server, "service", g_strdup_printf("%d", port), NULL);

    // Stores mount points
    mounts = gst_rtsp_server_get_mount_points(server);

    // Testing w 4 cameras, can easily add more
    const char *mount_points[] = {"/front", "/left", "/right", "/back"};

    // Confidential: Code for building and mounting pipelines + unreferencing objects
}

int main(int argc, char const *argv[])
{
    // Default RTSP port
    int port = 8554;

    gst_rtsp_server_run(port);

    return 0;
}
