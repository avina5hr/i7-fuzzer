import os
import json
import socket
import subprocess
import time
import glob
import signal
import psutil
import logging
import re
import random
from datetime import datetime
import sys

# === Configuration Constants ===
OUTPUT_DIR = "/home/rajendra2024/github/live_555_code/output"
RTSP_SERVER_IP = "131.188.37.115"
RTSP_SERVER_PORT = 8554
SERVER_EXECUTABLE = "/home/rajendra2024/live555_clang/mediaServer/live555MediaServer"
SANCOV_DIR = "/home/rajendra2024/mutation_py_code"
MUTATION_DIR = "/home/rajendra2024/github/live_555_code/Final_Filter_message_by_nn"
SERVER_STARTUP_WAIT = 0.1
SCRIPT_TIMEOUT = 24 * 60 * 60  # 24 hours
RECV_BUFFER_SIZE = 4096  # Buffer size for socket.recv()

# === Logging Configuration ===
PROCESS_LOG_FILE = "/home/rajendra2024/mutation_py_code/process_mutations.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROCESS_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

start_time = datetime.now()

# --- Helper Functions ---
def ensure_directory_exists(path):
    os.makedirs(path, exist_ok=True)

def load_json_file(json_filename):
    try:
        with open(os.path.join(OUTPUT_DIR, json_filename), 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON file {json_filename}: {e}")
        return None

def extract_session_id(response, current_session_id=None):
    if current_session_id is not None:
        return current_session_id
    match = re.search(r'Session:\s*(\S+)', response)
    if match:
        return match.group(1).split(';')[0]
    return current_session_id

def send_single_message_to_server(client_socket, message, cseq_counter, session_id):
    if isinstance(message, str):
        message = message.encode('utf-8')
    cseq_line = f"CSeq: {cseq_counter}\r\n".encode('utf-8')
    if b"CSeq:" in message:
        message = re.sub(b"CSeq:.*\r\n", cseq_line, message)
    else:
        parts = message.split(b'\r\n', 1)
        if len(parts) == 2:
            message = parts[0] + b'\r\n' + cseq_line + parts[1]
        else:
            message += cseq_line

    if not message.lstrip().startswith(b"SETUP"):
        message = re.sub(b"Session:.*\r\n", b"", message)
        if session_id:
            session_line = f"Session: {session_id}\r\n".encode('utf-8')
            header_end = message.find(b"\r\n\r\n")
            if header_end != -1:
                message = message[:header_end] + b'\r\n' + session_line + message[header_end:]
            else:
                message += b'\r\n' + session_line

    logging.debug(f"Sending raw message:\n{message.decode('utf-8', errors='ignore')}")
    try:
        client_socket.sendall(message)
        client_socket.settimeout(0.2)
        response = client_socket.recv(RECV_BUFFER_SIZE).decode('utf-8', errors='ignore')
        logging.info(f"Response: {response}")
        return response
    except (socket.timeout, socket.error) as e:
        logging.error(f"Socket error: {e}")
        return None

raw_message_cache = {}
def load_raw_message(filename):
    if filename in raw_message_cache:
        return raw_message_cache[filename]
    try:
        with open(filename, 'rb') as file:
            content = file.read()
            raw_message_cache[filename] = content
            return content
    except FileNotFoundError:
        logging.error(f"{filename} not found.")
        return None

def get_raw_message_filename(state, media_type):
    filenames = {
        "OPTIONS": f"OPTIONS_{media_type}.raw",
        "DESCRIBE": f"DESCRIBE_{media_type}.raw",
        "SETUP": f"SETUP_{media_type}.raw",
        "PLAY": f"PLAY_{media_type}.raw",
        "PAUSE": f"PAUSE_{media_type}.raw",
        "TEARDOWN": f"TEARDOWN_{media_type}.raw"
    }
    return os.path.join(OUTPUT_DIR, filenames.get(state, None))

def monitor_cpu():
    cpu_percent = psutil.cpu_percent(interval=1)
    logging.info(f"CPU Usage: {cpu_percent}%")

def wait_for_server_ready(ip, port, timeout, max_attempts):
    for attempt in range(max_attempts):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                logging.info("Server is ready.")
                return True
        except (socket.timeout, ConnectionRefusedError):
            logging.info(f"Waiting for server (attempt {attempt + 1}/{max_attempts})...")
            time.sleep(0.1)
    logging.error("Server not ready after maximum attempts.")
    return False

def start_server_with_asan_coverage():
    env = os.environ.copy()
    ensure_directory_exists(SANCOV_DIR)
    env["ASAN_OPTIONS"] = f"coverage=1:coverage_dir={SANCOV_DIR}:verbosity=1"
    pid = os.fork()
    if pid == 0:
        os.environ.update(env)
        try:
            os.execv(SERVER_EXECUTABLE, [SERVER_EXECUTABLE])
        except Exception as e:
            logging.error("Failed to exec server: " + str(e))
            os._exit(1)
    else:
        time.sleep(SERVER_STARTUP_WAIT)
        if not wait_for_server_ready(RTSP_SERVER_IP, RTSP_SERVER_PORT, timeout=0.01, max_attempts=1):
            logging.error("Forked server not ready.")
            os.kill(pid, signal.SIGTERM)
            return None
        logging.info(f"Forked server started with PID {pid}.")
        return pid

def stop_server(server_pid):
    if server_pid:
        try:
            os.kill(server_pid, signal.SIGTERM)
        except Exception as e:
            logging.error("Error sending SIGTERM to server: " + str(e))
        try:
            os.waitpid(server_pid, 0)
        except Exception as e:
            logging.warning("Error waiting for server termination: " + str(e))
        logging.info("Forked server terminated.")

def send_mutated_message(client_socket, mutated_message_path, cseq_counter, session_id):
    mutated_message = load_raw_message(mutated_message_path)
    if mutated_message:
        logging.info(f"Sending mutated message from {mutated_message_path}")
        response = send_single_message_to_server(client_socket, mutated_message, cseq_counter, session_id)
        if not response:
            logging.error("No response for mutated message.")
            return None, None
        session_id = extract_session_id(response, session_id)
        cseq_counter += 1
        return cseq_counter, session_id
    return None, None

def send_suffix_messages(client_socket, transitions, session_id, cseq_counter, fixed_state_index, media_type):
    for i in range(fixed_state_index + 1, len(transitions)):
        request_type = transitions[i][0]
        raw_filename = get_raw_message_filename(request_type, media_type)
        if raw_filename:
            raw_message = load_raw_message(raw_filename)
            if raw_message:
                logging.info(f"Sending suffix message for {request_type}")
                response = send_single_message_to_server(client_socket, raw_message, cseq_counter, session_id)
                if not response:
                    logging.warning(f"No response for {request_type}.")
                    return None, cseq_counter
                session_id = extract_session_id(response, session_id)
                cseq_counter += 1
    return session_id, cseq_counter

def send_unmutated_sequence_up_to_state(client_socket, transitions, session_id, cseq_counter, fixed_state_index, media_type):
    for i in range(fixed_state_index):
        request_type = transitions[i][0]
        raw_filename = get_raw_message_filename(request_type, media_type)
        if raw_filename:
            raw_message = load_raw_message(raw_filename)
            if raw_message:
                logging.info(f"Sending unmutated message for {request_type}")
                response = send_single_message_to_server(client_socket, raw_message, cseq_counter, session_id)
                if not response:
                    logging.warning(f"No response for {request_type}.")
                    return None, cseq_counter
                session_id = extract_session_id(response, session_id)
                cseq_counter += 1
    return session_id, cseq_counter

def handle_crash_signal(signum, frame):
    logging.error(f"Crash detected! Signal: {signum}")
    stop_script()

def stop_script():
    logging.info("Stopping script after timeout.")
    exit(0)

signal.signal(signal.SIGSEGV, handle_crash_signal)
signal.signal(signal.SIGABRT, handle_crash_signal)
signal.signal(signal.SIGILL, handle_crash_signal)
signal.signal(signal.SIGFPE, handle_crash_signal)

def check_script_timeout():
    if (datetime.now() - start_time).total_seconds() > SCRIPT_TIMEOUT:
        stop_script()

def rename_sancov_file(mutated_file_base):
    sancov_files = glob.glob(os.path.join(SANCOV_DIR, "live555MediaServer.*.sancov"))
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

def get_state_selection_method(transitions):
    print("Select state transition selection method:")
    print("1. Length-Based Probability Distribution")
    print("2. Round Robin")
    print("3. Uniform Random")
    selection = input("Enter your choice (1, 2, or 3): ").strip()
    if selection == "1":
        def select_index():
            weights = [len(state[0]) for state in transitions]
            return random.choices(range(len(transitions)), weights=weights, k=1)[0]
        return select_index
    elif selection == "2":
        index = [-1]
        def select_index():
            index[0] = (index[0] + 1) % len(transitions)
            return index[0]
        return select_index
    elif selection == "3":
        def select_index():
            return random.randint(0, len(transitions) - 1)
        return select_index
    else:
        print("Invalid selection, defaulting to uniform random.")
        def select_index():
            return random.randint(0, len(transitions) - 1)
        return select_index

def process_mutations(transitions, json_filename, fixed_state_index, state_selector_func):
    """
    Processes mutation files for 24 hours. For each state, it processes 10 messages,
    then selects the next state using the user-selected state selection method.
    """
    media_types = ['mp3', 'aac', 'wav', 'webm', 'mkv']
    current_state = transitions[fixed_state_index][0].strip()
    logging.info(f"Starting 24-hour processing with state: {current_state} (index {fixed_state_index})")
    
    duration = 24 * 3600   # 24 hours duration
    start_time_loop = time.time()
    message_count = 0  # Number of messages processed for the current state
    
    while time.time() - start_time_loop < duration:
        for media_type in media_types:
            mutation_base_dir = os.path.join(MUTATION_DIR, media_type)
            if not os.path.isdir(mutation_base_dir):
                logging.warning(f"Mutation directory does not exist for media type {media_type}. Skipping.")
                continue

            # Find the folder for current_state (case-insensitive)
            available_folders = os.listdir(mutation_base_dir)
            folder_match = None
            for folder in available_folders:
                if folder.strip().upper() == current_state.upper():
                    folder_match = folder
                    break
            if not folder_match:
                logging.warning(f"No mutation folder found for state {current_state} in media type {media_type}.")
                continue

            mutation_path = os.path.join(mutation_base_dir, folder_match)
            if not os.path.isdir(mutation_path):
                continue

            # Get list of mutation files for the current state (case-insensitive)
            mutated_files = [
                f for f in os.listdir(mutation_path)
                if f.strip().upper().startswith(current_state.upper()) and f.strip().endswith('.raw')
            ]
            if not mutated_files:
                logging.info(f"No new messages to process for state {current_state} in {media_type}")
                continue

            # Randomly select one file from the list
            mutated_file = random.choice(mutated_files)
            full_file_path = os.path.join(mutation_path, mutated_file)
            logging.info(f"Selected random file {mutated_file} for processing in {media_type}")

            server_pid = start_server_with_asan_coverage()
            if not server_pid:
                logging.error("Failed to start server; skipping file.")
                try:
                    os.remove(full_file_path)
                    logging.info(f"Deleted file {full_file_path} (server not started).")
                except Exception as e:
                    logging.error(f"Error deleting file {full_file_path}: {e}")
                continue

            try:
                session_id = None
                cseq_counter = 1

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                    client_socket.connect((RTSP_SERVER_IP, RTSP_SERVER_PORT))
                    logging.info(f"Connected to {RTSP_SERVER_IP}:{RTSP_SERVER_PORT} for file {mutated_file}")

                    session_id, cseq_counter = send_unmutated_sequence_up_to_state(
                        client_socket, transitions, session_id, cseq_counter, fixed_state_index, media_type
                    )
                    if session_id is None:
                        logging.error("Unmutated sequence failed.")
                    else:
                        try:
                            with open(full_file_path, 'r') as mf:
                                message_content = mf.read()
                            logging.info(f"Mutated message content for {mutated_file}: {message_content}")
                        except Exception as e:
                            logging.error(f"Failed to read mutated message {mutated_file}: {e}")

                        result = send_mutated_message(client_socket, full_file_path, cseq_counter, session_id)
                        if result is None or result[0] is None:
                            logging.error("Mutated message failed.")
                        else:
                            cseq_counter, session_id = result
                            session_id, cseq_counter = send_suffix_messages(
                                client_socket, transitions, session_id, cseq_counter, fixed_state_index, media_type
                            )
            except socket.error as e:
                logging.exception(f"Socket error while processing {mutated_file}:")
            finally:
                stop_server(server_pid)
                rename_sancov_file(os.path.splitext(mutated_file)[0])
                try:
                    os.remove(full_file_path)
                    logging.info(f"Deleted file {full_file_path} after processing.")
                except Exception as e:
                    logging.error(f"Failed to delete file {full_file_path}: {e}")

            message_count += 1
            logging.info(f"Processed {message_count} message(s) for state {current_state}")

            # When 10 messages have been processed for the current state, break to change state.
            if message_count >= 10:
                break

        # After processing 10 messages, select the next state using the user's method.
        if message_count >= 10:
            fixed_state_index = state_selector_func()
            current_state = transitions[fixed_state_index][0].strip()
            logging.info(f"Switching to new state: {current_state} (index {fixed_state_index})")
            message_count = 0  # Reset counter for the new state

        logging.info("Iteration complete. Sleeping briefly before re-scanning for new files...")
        time.sleep(0.1)
    
    logging.info("24-hour processing completed.")

    for media_type in media_types:
        mutation_path = os.path.join(MUTATION_DIR, media_type, current_state)
        if os.path.isdir(mutation_path):
            remaining_files = [
                f for f in os.listdir(mutation_path)
                if f.strip().upper().startswith(current_state.upper()) and f.strip().endswith('.raw')
            ]
            logging.info(f"After processing, {len(remaining_files)} files remain in {mutation_path}.")

if __name__ == "__main__":
    json_file = 'oracle_map_client_9.json'
    ensure_directory_exists(OUTPUT_DIR)
    
    transitions = load_json_file(json_file)
    if transitions:
        # Get the user's chosen state selection method.
        state_selector_func = get_state_selection_method(transitions)
        fixed_state_index = state_selector_func()
        print(f"Initial state selected: {transitions[fixed_state_index][0].strip()} (index {fixed_state_index})")
        process_mutations(transitions, json_file, fixed_state_index, state_selector_func)
    else:
        print("No transitions loaded.")
    
    check_script_timeout()
    monitor_cpu()

