import os
import json
import socket
import threading
import logging
from urllib.parse import urlparse

RTSP_SERVER_IP = "131.188.37.115"
RTSP_SERVER_PORT = 8555
PROXY_IP = "127.0.0.1"
PROXY_PORT = 8888
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

class RTSPProxy:
    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self.server_socket = None
        self.state = "INITIAL"
        self.last_client_request = None
        self.sequence_number = 0
        self.oracle_map = []
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self.handle_client).start()

    def handle_client(self):
        self.connect_to_server()
        threading.Thread(target=self.receive_from_server).start()

        try:
            while True:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                self.server_socket.sendall(data)
                self.process_client_request(data)
        except Exception as e:
            logging.error(f"Error handling client: {e}")
        finally:
            self.client_socket.close()
            self.server_socket.close()

    def connect_to_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((RTSP_SERVER_IP, RTSP_SERVER_PORT))
        logging.info(f"Connected to RTSP server at {RTSP_SERVER_IP}:{RTSP_SERVER_PORT}")

    def receive_from_server(self):
        try:
            while True:
                data = self.server_socket.recv(4096)
                if not data:
                    break
                self.client_socket.sendall(data)
                self.process_server_response(data)
        except Exception as e:
            logging.error(f"Error receiving from server: {e}")
        finally:
            self.client_socket.close()
            self.server_socket.close()

    def process_client_request(self, data):
        self.log_raw_message(data)
        payload = self.extract_payload(data)
        abstracted_packet = self.abstract_packet(payload)

        self.last_client_request = abstracted_packet["type"]  # Track last client request
        # No state update here; wait until the response is processed

    def process_server_response(self, data):
        self.log_raw_message(data)
        payload = self.extract_payload(data)
        abstracted_packet = self.abstract_packet(payload)

        # Use the last client request as the previous state for the server response
        previous_state = self.last_client_request

        # Update the state now, after processing the response
        self.state = abstracted_packet["type"]

        self.update_oracle_map(abstracted_packet, previous_state)

    def log_raw_message(self, message):
        try:
            with open(f'{OUTPUT_DIR}/raw_messages_client.log', 'ab') as file:
                file.write(message + b'\n')
            logging.info("Raw message logged for client.")
        except Exception as e:
            logging.error(f"Error logging message: {e}")

    def extract_payload(self, data):
        try:
            return data.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            logging.error("UnicodeDecodeError encountered while decoding payload.")
            return None

    def abstract_packet(self, payload):
        if payload is None:
            return {'type': 'UNKNOWN'}
        return {'type': self.determine_packet_type(payload)}

    def determine_packet_type(self, payload):
        packet_types = {
            "OPTIONS": "OPTIONS",
            "DESCRIBE": "DESCRIBE",
            "SETUP": "SETUP",
            "PLAY": "PLAY",
            "PAUSE": "PAUSE",
            "TEARDOWN": "TEARDOWN"
        }

        for key, value in packet_types.items():
            if key in payload:
                return value

        if payload.startswith("RTSP/1.0"):
            status_line = payload.splitlines()[0]
            return status_line

        return "UNKNOWN"

    def update_oracle_map(self, abstracted_packet, previous_state):
        state_transition = (previous_state, abstracted_packet['type'])

        try:
            with self.lock:
                # Always update the oracle map and save it
                self.oracle_map.append(state_transition)
                json_filename = f'oracle_map_client_{self.sequence_number}.json'
                with open(f'{OUTPUT_DIR}/{json_filename}', 'w') as file:
                    json.dump(self.oracle_map, file, indent=2)
                logging.info(f"Oracle map updated and saved as {json_filename}.")

                self.sequence_number += 1
        except Exception as e:
            logging.error(f"Error updating oracle map: {e}")

    def extract_media_type(self, payload):
        url = self.extract_url(payload)
        if url:
            parsed_url = urlparse(url)
            path = parsed_url.path
            ext = os.path.splitext(path)[-1].lower().replace('.', '')
            if ext in {"aac", "wav", "ac3", "webm", "mkv", "mp3", "mpg"}:
                return ext

        payload_lower = payload.lower()
        for ext in ["aac", "wav", "ac3", "webm", "mkv", "mp3", "mpg"]:
            if ext in payload_lower:
                return ext

        return None

    def extract_url(self, payload):
        if not payload:
            return None
        
        lines = payload.splitlines()
        
        for line in lines:
            if line.startswith("SETUP"):
                parts = line.split()
                for part in parts:
                    if part.startswith("rtsp://"):
                        return part.rstrip('/')
                break
        
        return None

    def save_raw_message(self, message, filename):
        try:
            with open(f'{OUTPUT_DIR}/{filename}', 'wb') as file:
                file.write(message)
            logging.info(f"Raw message saved: {filename}")
        except Exception as e:
            logging.error(f"Error saving raw message: {e}")

def start_proxy():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((PROXY_IP, PROXY_PORT))
    server_socket.listen(5)
    logging.info(f"RTSP Proxy Server listening on {PROXY_IP}:{PROXY_PORT}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            logging.info(f"Accepted connection from {client_address}")
            proxy = RTSPProxy(client_socket, client_address)
            proxy.start()
    except Exception as e:
        logging.error(f"Error starting proxy: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_proxy()

