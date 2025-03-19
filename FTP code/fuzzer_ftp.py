import os
import json
import socket
import subprocess
import time
import glob
import signal
import logging
from collections import Counter

from datetime import datetime, timedelta
import random
# Configuration
OUTPUT_DIR = "/home/rajendra2024/mutation_py_code/output_ftp"
FTP_SERVER_IP = "127.0.0.1"
FTP_SERVER_PORT = 2201
SERVER_EXECUTABLE = "/home/rajendra2024/server/LightFTP_1/Source/Release/fftp"
CONFIG_FILE = "/home/rajendra2024/server/LightFTP_1/Source/Release/fftp.conf"
SANCOV_DIR = "/home/rajendra2024/mutation_py_code/ftp_code/coverage_sancov_length"
MUTATION_DIR = "/home/rajendra2024/mutation_py_code/ftp_code/filtered_files_ftp"
RECV_BUFFER_SIZE = 4096
CONNECTION_TIMEOUT = 0.2
MAX_RETRIES = 1
ABORT_DELAY = 0.2
# Configure logging
LOG_FILE = os.path.join(SANCOV_DIR, f"process_log_{time.strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_message(level, message):
    """Log a message with the specified level."""
    print(message)  # Ensure messages are also printed to the console
    if level == "debug":
        logging.debug(message)
    elif level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    else:
        logging.info(message)

def ensure_directory_exists(directory):
    """Ensure the specified directory exists."""
    os.makedirs(directory, exist_ok=True)

def load_json_file(json_filename):
    """Load the JSON transitions file."""
    try:
        with open(os.path.join(OUTPUT_DIR, json_filename), 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON file {json_filename}: {e}")
        return None

def load_message_from_file(file_path):
    """Load the message from the specified .raw file."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Error: No .raw file found at {file_path}")
        return None

def is_port_in_use(port):
    """Check if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_server_with_asan_coverage():
    """Start the FTP server with ASAN coverage enabled."""
    if is_port_in_use(FTP_SERVER_PORT):
        print(f"Port {FTP_SERVER_PORT} is already in use. Ensure no other instance is running.")
        return None

    env = os.environ.copy()
    ensure_directory_exists(SANCOV_DIR)
    env["ASAN_OPTIONS"] = f"coverage=1:coverage_dir={SANCOV_DIR}:verbosity=1"

    working_dir = "/home/rajendra2024/server/LightFTP_1/Source/Release"

    try:
        server_process = subprocess.Popen(
            [SERVER_EXECUTABLE, CONFIG_FILE],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(0.4)  # Allow time for the server to start
        print("FTP Server started with ASAN coverage.")
        return server_process
    except Exception as e:
        print(f"Error starting FTP server: {e}")
        return None

def wait_for_ready_response(client_socket):
    """Wait for the server's initial readiness response."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client_socket.recv(RECV_BUFFER_SIZE).decode('utf-8', errors='ignore')
            print(f"Initial server response: {response}")
            if "220 LightFTP server ready" in response:
                return True
        except socket.timeout:
            print(f"Timeout waiting for server readiness. Attempt {attempt + 1}/{MAX_RETRIES}")
        time.sleep(0.1)  # Short wait before retry
    return False
def monitor_resource_usage(process):
    """Monitor and log CPU and memory usage of the server process."""
    if process and psutil.pid_exists(process.pid):
        proc = psutil.Process(process.pid)
        cpu_usage = proc.cpu_percent(interval=1)
        memory_info = proc.memory_info()
        print(f"CPU Usage: {cpu_usage}%")
        print(f"Memory Usage: {memory_info.rss / (1024 ** 2):.2f} MB")
    else:
        print("Process not found for resource monitoring.")

def send_abort(client_socket):
    """Send ABOR command to clear any in-progress operations."""
    try:
        client_socket.sendall("ABOR\r\n".encode('utf-8'))
        response = client_socket.recv(RECV_BUFFER_SIZE).decode('utf-8', errors='ignore')
        print(f"ABOR response: {response}")
        time.sleep(ABORT_DELAY)  # Short wait to let the server reset
    except socket.timeout:
        print("Timeout while sending ABOR command.")

def send_single_message_to_server(client_socket, command, expected_response, wait_for_response=False):
    """Send a single command to the server and check the expected response."""
    try:
        print(f"Sending command: {command.strip()}")
        client_socket.sendall(f"{command}\r\n".encode('utf-8'))
        client_socket.settimeout(CONNECTION_TIMEOUT)

        while True:
            try:
                response = client_socket.recv(RECV_BUFFER_SIZE).decode('utf-8', errors='ignore')
                print(f"Response received: {response.strip()}")

                if "Another action is in progress" in response:
                    print(f"Action in progress. Sending ABOR.")
                    send_abort(client_socket)
                    break

                if expected_response in response:
                    print(f"Expected response '{expected_response}' received.")
                    break

                if not wait_for_response:
                    break

            except socket.timeout:
                print(f"Timeout for command {command}. Retrying...")
                if not wait_for_response:
                    break

        if wait_for_response:
            print(f"Waiting after {command} for server readiness.")
            time.sleep(0.5)

    except socket.timeout:
        print(f"Error: No response within {CONNECTION_TIMEOUT} seconds.")

def send_unmutated_sequence_up_to_state(client_socket, transitions, state_index):
    """Send all unmutated messages leading up to the specified state."""
    for i in range(state_index):
        command, expected_response = transitions[i]
        message_file = os.path.join(OUTPUT_DIR, f"{command}.raw")
        message = load_message_from_file(message_file)
        if message:
            send_single_message_to_server(client_socket, message, expected_response)
        else:
            print(f"Skipping {command} due to missing message.")

def send_mutated_message(client_socket, mutation_file):
    """Send the mutated message."""
    raw_file_path = os.path.join(MUTATION_DIR, mutation_file)
    print(f"Attempting to send mutated message from {raw_file_path}")
    mutated_message = load_message_from_file(raw_file_path)
    if mutated_message:
        print(f"Sending mutated message from {raw_file_path}")
        response = send_single_message_to_server(client_socket, mutated_message, "Expected Response")  # Replace as needed
        return response
    else:
        print(f"Error: Mutated message file {raw_file_path} not found.")
        return None
# Configuration
SANITIZER_LOGS_DIR = os.path.join(SANCOV_DIR, f"sanitizer_logs_{time.strftime('%Y%m%d_%H%M%S')}")

def ensure_sanitizer_log_dir():
    """Create a unique directory for sanitizer logs with a timestamp."""
    os.makedirs(SANITIZER_LOGS_DIR, exist_ok=True)
    print(f"Sanitizer logs directory created: {SANITIZER_LOGS_DIR}")

def stop_server_and_collect_coverage(server_process, chosen_state):
    """Stop the FTP server and collect the coverage file."""
    if server_process:
        try:
            print("Sending SIGINT to gracefully stop the server.")
            server_process.send_signal(signal.SIGINT)
            server_process.wait(timeout=0.1)  # Allow the server to shut down
            
            stdout, stderr = server_process.communicate()
            sanitizer_log_file = os.path.join(SANITIZER_LOGS_DIR, f"sanitizer_log_{chosen_state}_{time.strftime('%Y%m%d_%H%M%S')}.log")
            
            # Write logs to the sanitizer log file
            with open(sanitizer_log_file, 'w') as log_file:
                log_file.write("Server stdout:\n")
                log_file.write(stdout.decode())
                log_file.write("\nServer stderr:\n")
                log_file.write(stderr.decode())
            print(f"Sanitizer logs saved to {sanitizer_log_file}")

            # Handle coverage files
            sancov_files = glob.glob(os.path.join(SANCOV_DIR, "fftp.*.sancov"))
            if sancov_files:
                for i, sancov_file in enumerate(sancov_files):
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    new_filename = os.path.join(SANCOV_DIR, f"edge_coverage_{chosen_state}_{timestamp}_{i}.sancov")
                    os.rename(sancov_file, new_filename)
                    print(f"Coverage data saved to {new_filename}")
            else:
                print(f"No coverage file generated for state {chosen_state}.")
        except subprocess.TimeoutExpired:
            print("Server did not terminate within the timeout. Forcing it to stop...")
            server_process.kill()
        except Exception as e:
            print(f"Error stopping the server: {e}")

def process_mutations(transitions):
    """
    Process states by selecting a state based on its length probability and sending one mutated message per state in sequence, cycling until 8 hours have passed.
    """
    ensure_sanitizer_log_dir()
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=6)

    # Count the frequency of each request type
    state_counts = Counter(transition[0] for transition in transitions)
    total_transitions = sum(state_counts.values())

    # Calculate probabilities for each state
    state_probabilities = {state: count / total_transitions for state, count in state_counts.items()}

    # Track sent mutations for each state
    sent_mutations = {state: set() for state in state_counts.keys()}

    while datetime.now() < end_time:
        # Select a state based on probabilities
        request_type = random.choices(
            population=list(state_probabilities.keys()),
            weights=list(state_probabilities.values()),
            k=1
        )[0]
        mutation_path = os.path.join(MUTATION_DIR, request_type)

        if os.path.isdir(mutation_path):
            mutation_files = [f for f in os.listdir(mutation_path) if f.endswith('.raw')]

            # Filter out already sent mutations
            unsent_files = [f for f in mutation_files if f not in sent_mutations[request_type]]

            if unsent_files:
                mutation_file = random.choice(unsent_files)  # Pick a random unsent file
                sent_mutations[request_type].add(mutation_file)  # Mark it as sent

                server_process = start_server_with_asan_coverage()
                if not server_process:
                    continue

                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                        client_socket.connect((FTP_SERVER_IP, FTP_SERVER_PORT))
                        log_message("info", f"Connected to FTP server at {FTP_SERVER_IP}:{FTP_SERVER_PORT}")

                        if wait_for_ready_response(client_socket):
                            # Send unmutated messages up to the selected state
                            state_index = next(i for i, t in enumerate(transitions) if t[0] == request_type)
                            send_unmutated_sequence_up_to_state(client_socket, transitions, state_index)
                            
                            # Send the randomly selected mutated message
                            response = send_mutated_message(client_socket, os.path.join(request_type, mutation_file))
                            if not response:
                                log_message("warning", "No response for mutated message, skipping.")
                                continue

                    # Monitor resource usage
                    monitor_resource_usage(server_process)

                except socket.error as e:
                    log_message("error", f"Socket error: {e}")
                finally:
                    stop_server_and_collect_coverage(server_process, mutation_file)
            else:
                log_message("info", f"No unsent mutation files left for state {request_type}.")
        else:
            log_message("warning", f"Mutation path {mutation_path} does not exist.")


if __name__ == "__main__":
    json_filename = 'oracle_map_client_19.json'
    transitions = load_json_file(json_filename)
    if transitions:
        ensure_directory_exists(SANCOV_DIR)
        process_mutations(transitions)  
