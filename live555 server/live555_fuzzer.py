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
from datetime import datetime
import sys

# === Configuration Constants ===
OUTPUT_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/output"
RTSP_SERVER_IP = "131.188.37.115"
RTSP_SERVER_PORT = 8554
SERVER_EXECUTABLE = "/home/rajendra2024/live555_clang/mediaServer/live555MediaServer"
SANCOV_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/lstm"
MUTATION_DIR = "/home/rajendra2024/mutation_py_code/live_555_code/filtered_files"
CONNECTION_TIMEOUT = 0.01
SERVER_STARTUP_WAIT = 0.1
SANITIZER_LOG = "sanitizer_output.log"
SCRIPT_TIMEOUT = 24 * 60 * 60  # 24 hours
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
start_time = datetime.now()

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
    """
    Forks a new process and execs the RTSP server.
    The child process inherits ASAN_OPTIONS so that coverage is enabled.
    """
    env = os.environ.copy()
    ensure_directory_exists(SANCOV_DIR)
    env["ASAN_OPTIONS"] = f"coverage=1:coverage_dir={SANCOV_DIR}:verbosity=1"
    pid = os.fork()
    if pid == 0:
        # Child process: update environment and exec the server.
        os.environ.update(env)
        try:
            os.execv(SERVER_EXECUTABLE, [SERVER_EXECUTABLE])
        except Exception as e:
            logging.error("Failed to exec server: " + str(e))
            os._exit(1)
    else:
        # Parent process: wait a bit and check readiness.
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

# Register signal handlers for crashes.
signal.signal(signal.SIGSEGV, handle_crash_signal)
signal.signal(signal.SIGABRT, handle_crash_signal)
signal.signal(signal.SIGILL, handle_crash_signal)
signal.signal(signal.SIGFPE, handle_crash_signal)

def check_script_timeout():
    if (datetime.now() - start_time).total_seconds() > SCRIPT_TIMEOUT:
        stop_script()

def rename_sancov_file(mutated_file_base):
    """
    Renames the latest coverage file (dumped by the server) to associate it with the given mutated file base.
    The new filename will include a timestamp for uniqueness.
    """
    sancov_files = glob.glob(os.path.join(SANCOV_DIR, "live555MediaServer.*.sancov"))
    if not sancov_files:
        logging.info("No coverage file found to rename.")
        return
    
    # Sort by modification time to get the latest sancov file
    latest_sancov_file = max(sancov_files, key=os.path.getmtime)

    # Get current timestamp in YYYYMMDD_HHMMSS format
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Construct new filename with timestamp
    new_name = os.path.join(SANCOV_DIR, f"{mutated_file_base}_{timestamp}.sancov")
    
    try:
        os.rename(latest_sancov_file, new_name)
        logging.info(f"Renamed coverage file to {new_name}")
    except Exception as e:
        logging.error(f"Error renaming coverage file: {e}")


def process_mutations(transitions, json_filename):
    """
    Continuously scans the mutation directories for 12 hours and processes mutation files.
    After processing 100 messages for a given (RTSP state, media type) combination,
    the counter for that combination is reset so that new messages will be processed
    starting from the initial state.
    """
    media_types = ['mp3', 'aac', 'wav', 'webm', 'mkv']
    MESSAGE_LIMIT_PER_STATE = 100 # per-cycle threshold

    # Initialize counters per (state, media_type)
    total_count = {}
    for transition in transitions:
        for media in media_types:
            total_count[(transition[0], media)] = 0

    processed_files = set()  # Tracks full path of processed files.
    duration = 24 * 3600   # 12 hours
    start_time_loop = time.time()

    while time.time() - start_time_loop < duration:
        # For each state and each media type, scan for new files.
        for i, transition in enumerate(transitions):
            request_type = transition[0]
            for media_type in media_types:
                # If counter for this (state, media_type) has reached the threshold, reset it.
                key = (request_type, media_type)
                if total_count[key] >= MESSAGE_LIMIT_PER_STATE:
                    logging.info(f"Global limit reached for {request_type} in {media_type} ({total_count[key]} messages). Resetting counter.")
                    total_count[key] = 0

                mutation_path = os.path.join(MUTATION_DIR, media_type, request_type)
                if not os.path.isdir(mutation_path):
                    logging.warning(f"Mutation directory does not exist for {request_type} ({media_type}). Skipping.")
                    continue

                # List files that are new (not processed)
                mutated_files = [
                    f for f in os.listdir(mutation_path)
                    if f.startswith(request_type) and f.endswith('.raw') and os.path.join(mutation_path, f) not in processed_files
                ]
                if not mutated_files:
                    logging.info(f"No new files for {request_type} ({media_type}).")
                    continue

                # Limit the number of files processed in this iteration for this (state, media_type)
                remaining_limit = MESSAGE_LIMIT_PER_STATE - total_count[key]
                batch_files = mutated_files[:remaining_limit]
                logging.info(f"Processing {len(batch_files)} new messages for {request_type} in {media_type}")

                for mutated_file in batch_files:
                    full_file_path = os.path.join(mutation_path, mutated_file)
                    # Start a fresh forked server for each file.
                    server_pid = start_server_with_asan_coverage()
                    if not server_pid:
                        logging.error("Failed to start server; skipping file.")
                        processed_files.add(full_file_path)
                        total_count[key] += 1
                        continue

                    try:
                        session_id = None
                        cseq_counter = 1
                        success = False

                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                            client_socket.connect((RTSP_SERVER_IP, RTSP_SERVER_PORT))
                            logging.info(f"Connected to {RTSP_SERVER_IP}:{RTSP_SERVER_PORT} for file {mutated_file}")
                            
                            # Pass the current media_type to the unmutated sequence function.
                            session_id, cseq_counter = send_unmutated_sequence_up_to_state(
                                client_socket, transitions, session_id, cseq_counter, i, media_type
                            )
                            if session_id is None:
                                logging.error("Unmutated sequence failed. Marking file as processed.")
                            else:
                                try:
                                    with open(full_file_path, 'r') as mf:
                                        message_content = mf.read()
                                    logging.info(f"Mutated message content for {mutated_file}: {message_content}")
                                except Exception as e:
                                    logging.error(f"Failed to read mutated message {mutated_file}: {e}")

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
                        if success:
                            logging.info(f"Successfully processed {mutated_file}")
                        else:
                            logging.warning(f"Processing failed for {mutated_file}, but marked as processed.")

        logging.info("Iteration complete. Sleeping briefly before re-scanning for new files...")
        time.sleep(0.1)

    logging.info("12-hour processing completed.")

    # Final logging: Report remaining files in each mutation directory.
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

if __name__ == "__main__":
    json_file = 'oracle_map_client_9.json'
    ensure_directory_exists(OUTPUT_DIR)
    
    transitions = load_json_file(json_file)
    if transitions:
        process_mutations(transitions, json_file)
    
    check_script_timeout()
    monitor_cpu()

