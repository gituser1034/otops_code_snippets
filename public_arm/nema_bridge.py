# Olly, Ihsan 
# Jetson to Arduino Serial Bridge
# Jetson Receives controller input for the arm from aresui + aresgo
# Jetson sends this controller input to the arduino (which connects to arm motors)

import time
import threading
import socket
import json
import signal
import serial

# Serial connection to arduino (to send controls to arduino connected to nema motors)
arduino = serial.Serial(
    # We need to change this number to match actual value - similiar to 
    # finding ethercat adapter number
    port="/dev/ttyACM0",  
    baudrate=115200,
    timeout=0.02
)

# UDP configuration (receiving data from ui/go)
UDP_HOST = "0.0.0.0"
UDP_PORT = 5999
COMMAND_TIMEOUT_S = 0.4  # no valid packet within this window -> motors forced to 0
HEARTBEAT_INTERVAL_S = 10.0  # while a diagnostic problem persists, re-announce it at this cadence

# stuff for diagnostics
running = True
last_packet_seen_time = 0.0
last_command_time = 0.0
udp_packet_count = 0
udp_malformed_count = 0
udp_bound_event = threading.Event()

# Function that sends data to the arduino
def send_to_arduino(cmd):
    try:
        print("Writing to arduino")
        msg = json.dumps(cmd) + "\n"
        arduino.write(msg.encode("utf-8"))
    except Exception as e:
        print("Arduino write error:", e)

# UDP listener thread. Receives the ControlState JSON packets
# sent ~60x/sec by aresgo (see aresgo/internal/model/control.go),
# applies "drive" to the motors, and ignores arm (those
# fields are for the Mega's steppers, not the SEW EtherCAT drives).
def udp_listener_thread():
    # Code to receive udp packets hidden
        try:
            packet = json.loads(data.decode("utf-8"))

            # Grabs arm data from ui/go (json when running main.go -print-control)
            arm = packet["arm"]
            base_velocity = float(arm["base"])
            #shoulder_velocity = float(arm["shoulder"])
            elbow_velocity = float(arm["elbow"])
            wrist_velocity = float(arm["wrist"])
            gripper_velocity = float(arm["gripper"])
            # Think we are getting rid of speed scale?
            # speed_scale = float(packet["speed_scale"])

            arm_command = {
                "base": base_velocity,
                #"shoulder": shoulder_velocity,
                "elbow": elbow_velocity,
                "wrist": wrist_velocity,
                "gripper": gripper_velocity
            }

            # Debugging seeing if actually receiving
            print(arm_command)

            last_command_time = time.time()

        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            udp_malformed_count += 1
            # Malformed/partial packet - drop it and keep listening.
            #continue

        # Call send to arduino function here
        send_to_arduino(arm_command)

    #sock.close()
        print("[udp] listener stopped")

# ------------------------------------------------------------------
# Diagnostics thread. Read-only with respect to motor control - it never
# touches motor_rpm or master.slaves[i].output, it only reads state written
# by the other two threads and prints operator-facing warnings that explain
# *why* the rover isn't responding. Distinguishes three distinct failure
# points along the pipeline, checked every 0.5s and reported on change:
#   1. No UDP traffic is reaching this socket at all (network problem -
#      wrong IP/port, firewall, sender not running).
#   2. UDP traffic is arriving but failing to parse into a valid drive
#      command (payload shape/JSON key mismatch).
#   3. Valid drive commands are being applied to motor_rpm, but they
#      aren't making it to the physical motors (EtherCAT working counter
#      degraded, or a drive reporting fault/not-ready/STO-not-ok while
#      being commanded to move).
# ------------------------------------------------------------------
def diagnostics_thread():
    global running

    udp_arriving = None       # None = not yet evaluated (startup grace period)
    udp_parsing = None

    # Last time each category printed anything, used to re-announce a
    # persisting problem every HEARTBEAT_INTERVAL_S instead of going silent
    # forever after the first warning (last_*_time == 0.0 at startup means
    # "never happened yet", not "0 seconds ago" - handled explicitly below).
    last_arriving_print = 0.0
    last_parsing_print = 0.0

    while running:
        time.sleep(0.5)

        now = time.time()

        # ---- 1. Is any UDP traffic reaching the socket at all? ----
        arriving_now = last_packet_seen_time > 0 and (now - last_packet_seen_time) <= COMMAND_TIMEOUT_S
        if arriving_now != udp_arriving or (not arriving_now and now - last_arriving_print >= HEARTBEAT_INTERVAL_S):
            if arriving_now:
                print(f"[diag] UDP traffic detected on {UDP_HOST}:{UDP_PORT} "
                      f"({udp_packet_count} packet(s) seen so far)")
            else:
                since_desc = f"{now - last_packet_seen_time:.1f}s ago" if last_packet_seen_time > 0 else "since startup"
                print(f"[diag] WARNING: no UDP packets of any kind received ({since_desc}) "
                      f"on {UDP_HOST}:{UDP_PORT}. Check the sender is running and can reach "
                      f"this host/port (firewall, wrong IP, wrong port).")
            udp_arriving = arriving_now
            last_arriving_print = now

        # ---- 2. Is that traffic parsing into valid drive commands? ----
        if arriving_now:
            parsing_now = last_command_time > 0 and (now - last_command_time) <= COMMAND_TIMEOUT_S
            if parsing_now != udp_parsing or (not parsing_now and now - last_parsing_print >= HEARTBEAT_INTERVAL_S):
                if parsing_now:
                    print("[diag] UDP packets are parsing into valid arm commands")
                else:
                    print(f"[diag] WARNING: receiving UDP packets but none have parsed "
                          f"into a valid arm command recently "
                          f"({udp_malformed_count} malformed packet(s) so far this run). "
                          f"Check the sender's JSON matches the expected "
                          # shoulder is gone so should never have shoulder data stored
                          # If we get errors remove shoulder from here
                          "{'arm': {'base', 'shoulder', 'elbow', 'wrist', 'gripper'}, 'speed_scale'} shape.")
                udp_parsing = parsing_now
                last_parsing_print = now
        else:
            udp_parsing = None

        # Are commands actually reaching arduino/nema - we implementing something here 
        # later to debug?

def handle_shutdown_signal(signum, frame):
    global running
    print(f"\n[main] received signal {signum}, shutting down...")
    running = False

signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)

# start the UDP command listener thread.
udp_thread = threading.Thread(target=udp_listener_thread, daemon=True)
udp_thread.start()

# start the diagnostics thread (UDP reception + motor forwarding health checks).
diag_thread = threading.Thread(target=diagnostics_thread, daemon=True)
diag_thread.start()

time.sleep(0.5)

# Only claim to be ready if udp_listener_thread actually got its socket bound -
# previously this printed unconditionally even if that thread had already
# died on startup (e.g. OSError: Address already in use).
if udp_bound_event.wait(timeout=2.0):
    print(f"[main] ready - listening for arm commands on udp {UDP_HOST}:{UDP_PORT}")
else:
    print("[main] WARNING: UDP command listener did not start - nemas will "
          "never receive arm commands. Check the [udp] FATAL message above.")
