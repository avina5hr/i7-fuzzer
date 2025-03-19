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


UNMUTATED_DIR = "/home/rajendra2024/mqtt_code/output"

TRANSITIONS_FILE = os.path.join(UNMUTATED_DIR, "transition_map.json")
# Directory where coverage files (.sancov) are dumped
SANCOV_DIR = "/home/rajendra2024/mqtt_code/coverage"
# Directory containing mutated files organized by state
MUTATION_DIR = "/home/rajendra2024/mqtt_code/filtered_files/mqtt"

CONNECTION_TIMEOUT = 0.01
SERVER_STARTUP_WAIT = 2        # Seconds to wait for server startup
MAX_ATTEMPTS = 2              # Maximum connection attempts
SCRIPT_TIMEOUT = 6 * 3600    

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
        # Wait for the server to start.
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

def stop_server(server_pid):
    """Terminate the Mosquitto server process."""
    if server_pid:
        try:
            os.kill(server_pid, signal.SIGTERM)
        except Exception as e:
            logging.error("Error sending SIGTERM to server: " + str(e))
        try:
            os.waitpid(server_pid, 0)
        except Exception as e:
            logging.warning("Error waiting for server termination: " + str(e))
        logging.info("Mosquitto server terminated.")

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

def send_unmutated_sequence_up_to_state(client_socket, transitions, state_index):
    """
    Send unmutated MQTT messages for all states from the start up to (but not including)
    the target state (state_index).
    """
    for i in range(state_index):
        client_msg = transitions[i][0]
        raw_file = os.path.join(UNMUTATED_DIR, f"{client_msg}.raw")
        message = load_raw_message(raw_file)
        if message:
            logging.info(f"Sending unmutated {client_msg} from {raw_file}")
            send_single_message_to_server(client_socket, message)
            time.sleep(0.2)
        else:
            logging.error(f"Unmutated message file for {client_msg} not found.")
    return

def send_suffix_messages(client_socket, transitions, state_index):
    """
    After sending the mutated message, send unmutated messages for states
    after the target state.
    """
    for i in range(state_index+1, len(transitions)):
        client_msg = transitions[i][0]
        raw_file = os.path.join(UNMUTATED_DIR, f"{client_msg}.raw")
        message = load_raw_message(raw_file)
        if message:
            logging.info(f"Sending suffix {client_msg} from {raw_file}")
            send_single_message_to_server(client_socket, message)
            time.sleep(0.2)
        else:
            logging.error(f"Suffix message file for {client_msg} not found.")
    return

def rename_sancov_file(mutated_file_base):
    """
    Rename the latest coverage file (dumped by the server) to associate it with
    the given mutated file base.
    """
    sancov_files = glob.glob(os.path.join(SANCOV_DIR, "mosquitto.*.sancov"))
    if not sancov_files:
        logging.info("No coverage file found to rename.")
        return
    latest_sancov_file = max(sancov_files, key=os.path.getmtime)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = os.path.join(SANCOV_DIR, f"{mutated_file_base}_{timestamp}.sancov")
    try:
        os.rename(latest_sancov_file, new_name)
        logging.info(f"Renamed coverage file to {new_name}")
    except Exception as e:
        logging.error(f"Error renaming coverage file: {e}")

def process_mutations(transitions, json_filename):
    """
    Process mutated MQTT messages for each state.
    For each state, process up to 100 mutated files from the corresponding folder in MUTATION_DIR.
    For each mutated file:
      1. Start a fresh MQTT server with coverage enabled.
      2. Connect to the broker.
      3. Send the unmutated sequence up to the target state.
      4. Send the mutated message.
      5. Send the suffix (remaining) unmutated messages.
      6. Shutdown the server, dump coverage, and delete the mutated file.
    """
    MESSAGE_LIMIT_PER_STATE = 100
    total_count = {}
    for transition in transitions:
        state = transition[0]
        total_count[state] = 0

    processed_files = set()
    duration = SCRIPT_TIMEOUT
    start_time_loop = time.time()

    while time.time() - start_time_loop < duration:
        # Iterate over each state (round-robin)
        for i, transition in enumerate(transitions):
            state = transition[0]
            if total_count[state] >= MESSAGE_LIMIT_PER_STATE:
                logging.info(f"Limit reached for {state} ({total_count[state]} messages). Resetting counter.")
                total_count[state] = 0

            mutation_path = os.path.join(MUTATION_DIR, state)
            if not os.path.isdir(mutation_path):
                logging.warning(f"Mutation directory for {state} does not exist. Skipping.")
                continue

            mutated_files = [
                f for f in os.listdir(mutation_path)
                if f.endswith('.raw') and os.path.join(mutation_path, f) not in processed_files
            ]
            if not mutated_files:
                logging.info(f"No new mutated files for {state}.")
                continue

            remaining_limit = MESSAGE_LIMIT_PER_STATE - total_count[state]
            batch_files = mutated_files[:remaining_limit]
            logging.info(f"Processing {len(batch_files)} mutated files for {state}.")

            for mutated_file in batch_files:
                full_file_path = os.path.join(mutation_path, mutated_file)
                server_pid = start_mosquitto_with_coverage()
                if not server_pid:
                    logging.error("Failed to start MQTT server; skipping file.")
                    processed_files.add(full_file_path)
                    total_count[state] += 1
                    continue

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                        client_socket.connect((MQTT_SERVER_IP, MQTT_SERVER_PORT))
                        logging.info(f"Connected to {MQTT_SERVER_IP}:{MQTT_SERVER_PORT} for mutated file {mutated_file}")
                        # Send unmutated sequence for states before the target state.
                        send_unmutated_sequence_up_to_state(client_socket, transitions, i)
                        # Send the mutated message for the current state.
                        mutated_message = load_raw_message(full_file_path)
                        if mutated_message:
                            logging.info(f"Sending mutated {state} message from {full_file_path}")
                            response = send_single_message_to_server(client_socket, mutated_message)
                            if not response:
                                logging.error("Mutated message did not get a response.")
                            else:
                                # Send suffix messages for states after the target state.
                                send_suffix_messages(client_socket, transitions, i)
                        else:
                            logging.error(f"Failed to load mutated file {full_file_path}.")
                except socket.error as e:
                    logging.exception(f"Socket error while processing {mutated_file}:")
                finally:
                    stop_server(server_pid)
                    rename_sancov_file(os.path.splitext(mutated_file)[0])
                    processed_files.add(full_file_path)
                    total_count[state] += 1
                    # Delete the mutated file unconditionally.
                    try:
                        os.remove(full_file_path)
                        logging.info(f"Deleted mutated file {full_file_path}.")
                    except Exception as e:
                        logging.error(f"Failed to delete file {full_file_path}: {e}")

        logging.info("Iteration complete. Sleeping briefly before re-scanning for new mutated files...")
        time.sleep(0.1)
    logging.info("12-hour processing completed.")
    # Final report.
    for transition in transitions:
        state = transition[0]
        mutation_path = os.path.join(MUTATION_DIR, state)
        if os.path.isdir(mutation_path):
            remaining_files = [f for f in os.listdir(mutation_path) if f.endswith('.raw')]
            logging.info(f"After processing, {len(remaining_files)} mutated files remain in {mutation_path}.")

if __name__ == "__main__":
    json_file = 'oracle_map_mqtt.json'
    transitions = load_transitions()
    if transitions is None:
        logging.info("Using default transitions.")
        transitions = [
            ["CONNECT", "CONNACK"],
            ["SUBSCRIBE", "SUBACK"],
            ["PUBLISH", "PUBACK"],
            ["UNSUBSCRIBE", "UNSUBACK"],
            ["PINGREQ", "PINGRESP"],
            ["DISCONNECT", ""]
        ]
    process_mutations(transitions, json_file)

