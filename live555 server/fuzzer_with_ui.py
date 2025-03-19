#!/usr/bin/env python3
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
import argparse
import sys
from datetime import datetime

# === Global Configuration Constants ===
OUTPUT_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/output"
RTSP_SERVER_IP = "131.188.37.115"
RTSP_SERVER_PORT = 8554
SERVER_EXECUTABLE = "/home/rajendra2024/live555_clang/mediaServer/live555MediaServer"
# For ASAN coverage (sancov files will be dumped here)
SANCOV_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/lstm"
MUTATION_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/filtered_files"
CONNECTION_TIMEOUT = 0.01
SERVER_STARTUP_WAIT = 0.1
SANITIZER_LOG = "sanitizer_output.log"
RECV_BUFFER_SIZE = 4096  # Buffer size for socket.recv()

# === Logging Configuration ===
PROCESS_LOG_FILE = "/home/rajendra2024/mutation_py_code/live_555_code/process_mutations.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROCESS_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# Record the script start time.
script_start_time = datetime.now()

# --- Open Log Terminal ---
def open_log_terminal():
    """
    Opens a new GNOME Terminal window that tails the log file.
    Adjust the command if using a different terminal.
    """
    try:
        subprocess.Popen(["gnome-terminal", "--", "tail", "-f", PROCESS_LOG_FILE])
    except Exception as e:
        logging.error("Could not open log terminal: " + str(e))

# --- UI Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="RTSP Mutation Fuzzing UI (ASAN coverage only)")
    parser.add_argument("--stop_mode", choices=["time", "mutation"], required=True,
                        help="Stop condition: 'time' for time-based, 'mutation' for mutation count based.")
    parser.add_argument("--time_duration", type=int, default=3600,
                        help="Duration (in seconds) for time-based execution.")
    parser.add_argument("--mutation_count", type=int, default=1000,
                        help="Total number of mutations to process for mutation-based execution.")
    parser.add_argument("--json_file", type=str, default="oracle_map_client_9.json",
                        help="JSON file with transitions.")
    return parser.parse_args()

# --- Helper Functions ---
def ensure_directory_exists(path):
    os.makedirs(path, exist_ok=True)

def load_json_file(json_filename):
    try:
        with open(os.path.join(OUTPUT_DIR, json_filename), 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"{json_filename} not found.")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {json_filename}: {e}")
        return None

def extract_session_id(response, current_session_id=None):
    if current_session_id is not None:
        return current_session_id
    match = re.search(r'Session:\s*(\S+)', response)
    if match:
        session = match.group(1).split(';')[0]
        return session
    return current_session_id

# Cache for raw messages.
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

    # Remove previous Session header if present (except for SETUP)
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
    except socket.timeout:
        logging.error("No response received (timeout).")
        return None
    except socket.error as e:
        logging.exception("Socket error:")
        return None

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

# --- Server Start Functions (ASAN Only) ---
def start_server_with_asan_coverage(_media_type=None, _json_filename=None, _mutation_file="unused"):
    """
    Starts the server using AddressSanitizer coverage.
    Returns a tuple: (server_pid, None)
    """
    env = os.environ.copy()
    ensure_directory_exists(SANCOV_DIR)
    env["ASAN_OPTIONS"] = f"coverage=1:coverage_dir={SANCOV_DIR}:verbosity=1"
    pid = os.fork()
    if pid == 0:
        os.environ.update(env)
        try:
            os.execv(SERVER_EXECUTABLE, [SERVER_EXECUTABLE])
        except Exception as e:
            logging.error("Failed to exec ASAN server: " + str(e))
            os._exit(1)
    else:
        time.sleep(SERVER_STARTUP_WAIT)
        if not wait_for_server_ready(RTSP_SERVER_IP, RTSP_SERVER_PORT, timeout=0.01, max_attempts=1):
            logging.error("Forked ASAN server not ready.")
            os.kill(pid, signal.SIGTERM)
            return None, None
        logging.info(f"ASAN server started with PID {pid}.")
        return pid, None

def stop_server(server_pid):
    """Stops the ASAN server given its PID."""
    if server_pid:
        try:
            os.kill(server_pid, signal.SIGTERM)
        except Exception as e:
            logging.error("Error sending SIGTERM to ASAN server: " + str(e))
        try:
            os.waitpid(server_pid, 0)
        except Exception as e:
            logging.warning("Error waiting for ASAN server termination: " + str(e))
        logging.info("ASAN server terminated.")

def rename_sancov_file(mutated_file_base):
    sancov_files = glob.glob(os.path.join(SANCOV_DIR, "live555MediaServer.*.sancov"))
    if not sancov_files:
        logging.info("No ASAN coverage file found to rename.")
        return
    latest_sancov_file = max(sancov_files, key=os.path.getmtime)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = os.path.join(SANCOV_DIR, f"{mutated_file_base}_{timestamp}.sancov")
    try:
        os.rename(latest_sancov_file, new_name)
        logging.info(f"Renamed ASAN coverage file to {new_name}")
    except Exception as e:
        logging.error(f"Error renaming ASAN coverage file: {e}")

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

def send_suffix_messages(client_socket, transitions, session_id, cseq_counter, state_index, media_type):
    for i in range(state_index + 1, len(transitions)):
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

def send_unmutated_sequence_up_to_state(client_socket, transitions, session_id, cseq_counter, state_index, media_type):
    for i in range(state_index):
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

# --- Mutation Processing ---
def process_mutations(transitions, stop_mode, time_duration, mutation_count_limit, json_filename):
    """
    Process mutation files until either the time_duration (in seconds) or a total mutation count limit is reached.
    Only ASAN (sancov) coverage is used.
    """
    media_types = ['mp3', 'aac', 'wav', 'webm', 'mkv']
    MESSAGE_LIMIT_PER_STATE = 100  # per-cycle threshold

    # Initialize per-(state, media) counters and a global mutation counter.
    total_count = {(transition[0], media): 0 for transition in transitions for media in media_types}
    global_mutation_count = 0
    start_time_loop = time.time()
    processed_files = set()  # Tracks full path of processed files.

    while True:
        # Check stop conditions.
        elapsed = time.time() - start_time_loop
        if stop_mode == "time" and elapsed >= time_duration:
            logging.info("Time duration reached. Stopping mutation processing.")
            break
        if stop_mode == "mutation" and global_mutation_count >= mutation_count_limit:
            logging.info("Mutation count limit reached. Stopping mutation processing.")
            break

        for i, transition in enumerate(transitions):
            request_type = transition[0]
            for media_type in media_types:
                key = (request_type, media_type)
                if total_count[key] >= MESSAGE_LIMIT_PER_STATE:
                    logging.info(f"Limit reached for {request_type} in {media_type} (processed {total_count[key]} messages). Resetting counter.")
                    total_count[key] = 0

                mutation_path = os.path.join(MUTATION_DIR, media_type, request_type)
                if not os.path.isdir(mutation_path):
                    logging.warning(f"Mutation directory does not exist for {request_type} ({media_type}).")
                    continue

                mutated_files = [
                    f for f in os.listdir(mutation_path)
                    if f.startswith(request_type) and f.endswith('.raw') and os.path.join(mutation_path, f) not in processed_files
                ]
                if not mutated_files:
                    continue

                remaining_limit = MESSAGE_LIMIT_PER_STATE - total_count[key]
                batch_files = mutated_files[:remaining_limit]
                logging.info(f"Processing {len(batch_files)} new messages for {request_type} in {media_type}.")

                for mutated_file in batch_files:
                    full_file_path = os.path.join(mutation_path, mutated_file)
                    # Start the ASAN server.
                    server_pid, _ = start_server_with_asan_coverage()
                    if not server_pid:
                        logging.error("Failed to start server; skipping file.")
                        processed_files.add(full_file_path)
                        total_count[key] += 1
                        global_mutation_count += 1
                        continue

                    try:
                        session_id = None
                        cseq_counter = 1
                        success = False

                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                            client_socket.connect((RTSP_SERVER_IP, RTSP_SERVER_PORT))
                            logging.info(f"Connected to {RTSP_SERVER_IP}:{RTSP_SERVER_PORT} for file {mutated_file}")
                            
                            session_id, cseq_counter = send_unmutated_sequence_up_to_state(
                                client_socket, transitions, session_id, cseq_counter, i, media_type
                            )
                            if session_id is None:
                                logging.error("Unmutated sequence failed. Marking file as processed.")
                            else:
                                result = send_mutated_message(client_socket, full_file_path, cseq_counter, session_id)
                                if result is None or result[0] is None:
                                    logging.error("Mutated message failed. Not deleting file.")
                                else:
                                    cseq_counter, session_id = result
                                    try:
                                        os.remove(full_file_path)
                                        logging.info(f"Deleted file {full_file_path} after successful sending.")
                                    except Exception as e:
                                        logging.error(f"Failed to delete file {full_file_path}: {e}")
                                    session_id, cseq_counter = send_suffix_messages(
                                        client_socket, transitions, session_id, cseq_counter, i, media_type
                                    )
                                    success = True
                    except socket.error as e:
                        logging.exception(f"Socket error while processing {mutated_file}:")
                    finally:
                        stop_server(server_pid)
                        rename_sancov_file(os.path.splitext(mutated_file)[0])
                        processed_files.add(full_file_path)
                        total_count[key] += 1
                        global_mutation_count += 1
                        if success:
                            logging.info(f"Successfully processed {mutated_file}")
                        else:
                            logging.warning(f"Processing failed for {mutated_file}, but marked as processed.")

        logging.info("Iteration complete. Sleeping briefly before re-scanning for new files...")
        time.sleep(0.1)

    logging.info(f"Processing completed. Total mutations processed: {global_mutation_count}")
    for media_type in media_types:
        for transition in transitions:
            request_type = transition[0]
            mutation_path = os.path.join(MUTATION_DIR, media_type, request_type)
            if os.path.isdir(mutation_path):
                remaining_files = [
                    f for f in os.listdir(mutation_path)
                    if f.startswith(request_type) and f.endswith('.raw')
                ]
                logging.info(f"After processing, {len(remaining_files)} files remain in {mutation_path}.")

# --- Main Execution ---
if __name__ == "__main__":
    args = parse_arguments()
    ensure_directory_exists(OUTPUT_DIR)
    
    # Open a new terminal to display the log output.
    open_log_terminal()
    
    transitions = load_json_file(args.json_file)
    if transitions:
        process_mutations(transitions,
                          stop_mode=args.stop_mode,
                          time_duration=args.time_duration,
                          mutation_count_limit=args.mutation_count,
                          json_filename=args.json_file)
    else:
        logging.error("Transitions could not be loaded. Exiting.")
    
    monitor_cpu()

