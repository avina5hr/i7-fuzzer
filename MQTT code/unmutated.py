#!/usr/bin/env python3
import os
import socket
import time
import glob
import signal
import logging
import sys
import json
from datetime import datetime

# === Configuration Constants ===
MQTT_SERVER_IP = "127.0.0.1"    # MQTT server IP
MQTT_SERVER_PORT = 1883         # MQTT server port
MQTT_SERVER_EXECUTABLE = "/home/rajendra2024/server/mosquitto/src/mosquitto"  # Path to Mosquitto executable

# Folder containing unmutated MQTT messages and transitions
UNMUTATED_DIR = "/home/rajendra2024/mqtt_code/output"
# Optional JSON file containing transitions. Each transition is a pair:
# [client_message, expected_broker_response]
TRANSITIONS_FILE = os.path.join(UNMUTATED_DIR, "transition_map.json")

# Directory where coverage files (.sancov) are dumped
SANCOV_DIR = "/home/rajendra2024/mqtt_code/coverage_1"

CONNECTION_TIMEOUT = 0.01
SERVER_STARTUP_WAIT = 2        # Wait (in seconds) for the server to start
MAX_ATTEMPTS = 20              # Maximum number of connection attempts

# === Logging Configuration ===
LOG_FILE = "process_base.log"
os.makedirs(SANCOV_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)

start_time = datetime.now()

# --- Helper Functions ---

def load_raw_message(filename):
    """Load a raw MQTT message from a file."""
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"File not found: {filename}")
        return None

def wait_for_server_ready(ip, port, timeout, max_attempts):
    """Attempt to connect repeatedly until the server is ready."""
    for attempt in range(max_attempts):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                logging.info("Server is ready.")
                return True
        except (socket.timeout, ConnectionRefusedError):
            logging.info(f"Waiting for server (attempt {attempt+1}/{max_attempts})...")
            time.sleep(0.2)
    logging.error("Server not ready after maximum attempts.")
    return False

def dump_coverage_file(label):
    """
    Look for the latest coverage file (with a .sancov extension) in SANCOV_DIR
    and rename it to include the provided label and a timestamp.
    """
    sancov_files = glob.glob(os.path.join(SANCOV_DIR, "*.sancov"))
    if not sancov_files:
        logging.info("No coverage file found to dump.")
        return
    latest_file = max(sancov_files, key=os.path.getmtime)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = os.path.join(SANCOV_DIR, f"{label}_{timestamp}.sancov")
    try:
        os.rename(latest_file, new_name)
        logging.info(f"Dumped coverage file: {new_name}")
    except Exception as e:
        logging.error(f"Error dumping coverage file: {e}")

def get_mqtt_message_type(response):
    """
    Decode the MQTT message type from the first byte of the response.
    The MQTT control packet type is stored in the high nibble (bits 7-4).
    """
    if not response:
        return None
    first_byte = response[0]
    msg_type_num = first_byte >> 4
    mapping = {
        1: "CONNECT",
        2: "CONNACK",
        3: "PUBLISH",
        4: "PUBACK",
        5: "PUBREC",
        6: "PUBREL",
        7: "PUBCOMP",
        8: "SUBSCRIBE",
        9: "SUBACK",
        10: "UNSUBSCRIBE",
        11: "UNSUBACK",
        12: "PINGREQ",
        13: "PINGRESP",
        14: "DISCONNECT",
        15: "AUTH"
    }
    return mapping.get(msg_type_num, f"UNKNOWN({msg_type_num})")

def send_single_message_to_server(client_socket, message):
    """
    Send a raw MQTT message (in binary) to the server and attempt to receive a response.
    Returns the raw response.
    """
    if isinstance(message, str):
        message = message.encode('utf-8')
    logging.info(f"Sending message (hex): {message.hex()}")
    try:
        client_socket.sendall(message)
        client_socket.settimeout(0.5)
        response = client_socket.recv(4096)
        if response:
            logging.info(f"Received response (hex): {response.hex()}")
        else:
            logging.info("No response received.")
        return response
    except socket.timeout:
        logging.error("No response received (timeout).")
        return None
    except socket.error as e:
        logging.exception("Socket error:")
        return None

def start_mosquitto_with_coverage():
    """
    Fork a new process to start the Mosquitto server with coverage enabled.
    The child process sets ASAN_OPTIONS so that the server dumps coverage data into SANCOV_DIR.
    """
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = f"coverage=1:coverage_dir={SANCOV_DIR}:verbosity=1"
    pid = os.fork()
    if pid == 0:
        # Child process: update environment and exec the Mosquitto server.
        os.environ.update(env)
        try:
            os.execv(MQTT_SERVER_EXECUTABLE, [MQTT_SERVER_EXECUTABLE])
        except Exception as e:
            logging.error("Failed to exec Mosquitto server: " + str(e))
            os._exit(1)
    else:
        # Wait for the server to start
        time.sleep(SERVER_STARTUP_WAIT)
        if not wait_for_server_ready(MQTT_SERVER_IP, MQTT_SERVER_PORT, CONNECTION_TIMEOUT, MAX_ATTEMPTS):
            logging.error("Mosquitto server not ready; terminating process.")
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as e:
                logging.error("Error killing Mosquitto process: " + str(e))
            return None
        logging.info(f"Mosquitto server started with PID {pid}.")
        return pid

def load_transitions():
    """
    Optionally load the transitions sequence from a JSON file.
    The file should define pairs of [client_message, expected_broker_response].
    If loading fails, fall back to a default list.
    """
    try:
        with open(TRANSITIONS_FILE, 'r') as f:
            transitions = json.load(f)
            logging.info(f"Loaded transitions: {transitions}")
            return transitions
    except Exception as e:
        logging.error(f"Error loading transitions file: {e}")
        return None

def run_fuzzing_iteration(target_index, transitions):
    """
    Run a fuzzing iteration for a selected target state (by index).
    This function:
      1. Starts the Mosquitto server with coverage enabled.
      2. Connects to the server.
      3. Sends MQTT messages (raw data) from the beginning of the transitions list up to the target state.
      4. Optionally sends a DISCONNECT message if available.
      5. Shuts down the server and dumps coverage.
    """
    server_pid = start_mosquitto_with_coverage()
    if server_pid is None:
        logging.error(f"Failed to start Mosquitto server for target index {target_index}.")
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((MQTT_SERVER_IP, MQTT_SERVER_PORT))
            logging.info(f"Connected to Mosquitto server at {MQTT_SERVER_IP}:{MQTT_SERVER_PORT}")

            # Send messages from index 0 up to and including target_index
            for i in range(target_index + 1):
                client_msg = transitions[i][0]
                raw_file = os.path.join(UNMUTATED_DIR, f"{client_msg}.raw")
                message = load_raw_message(raw_file)
                if message:
                    logging.info(f"Sending {client_msg} message from {raw_file}")
                    send_single_message_to_server(client_socket, message)
                    time.sleep(0.2)  # Pause between messages
                else:
                    logging.error(f"Message file for {client_msg} not found.")

            # Optionally, send DISCONNECT if a DISCONNECT.raw file exists.
            disconnect_file = os.path.join(UNMUTATED_DIR, "DISCONNECT.raw")
            if os.path.exists(disconnect_file):
                disconnect_message = load_raw_message(disconnect_file)
                if disconnect_message:
                    logging.info("Sending DISCONNECT message.")
                    send_single_message_to_server(client_socket, disconnect_message)
    except Exception as e:
        logging.error("Error during fuzzing iteration: " + str(e))
    finally:
        logging.info(f"Shutting down Mosquitto server for fuzzing iteration (target index {target_index}).")
        try:
            os.kill(server_pid, signal.SIGTERM)
        except Exception as e:
            logging.error("Error sending SIGTERM to Mosquitto server: " + str(e))
        try:
            os.waitpid(server_pid, 0)
        except Exception as e:
            logging.warning("Error waiting for server termination: " + str(e))
        # Use the state name from transitions for the current target index in the coverage file name.
        state_name = transitions[target_index][0]
        dump_coverage_file(state_name)

if __name__ == "__main__":
    # Load transitions from JSON; if not available, use default transitions.
    transitions = load_transitions()
    if transitions is None:
        logging.info("Using default transitions.")
        transitions = [
            ["CONNECT", "CONNACK"],
            ["SUBSCRIBE", "SUBACK"],
            ["PUBLISH", "PUBLISH"],
            ["UNSUBSCRIBE", "UNSUBACK"],
            ["PINGREQ", "PINGRESP"]
        ]
    # For round-robin fuzzing, create a list of client states (using the first element of each pair).
    states = [pair[0] for pair in transitions]
    num_states = len(states)
    logging.info(f"Starting round-robin fuzzing over {num_states} states.")

    # For each state in round-robin order, run a fuzzing iteration sending messages up to that state.
    for i in range(num_states):
        logging.info(f"Starting fuzzing iteration for state index {i}: {states[i]}")
        run_fuzzing_iteration(i, transitions)

    logging.info("Fuzzing run complete. Exiting.")

