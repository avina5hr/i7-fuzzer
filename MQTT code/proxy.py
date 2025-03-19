import os
import json
import socket
import threading
import logging
from datetime import datetime

# Constants for MQTT server
MQTT_SERVER_IP = "127.0.0.1"  # Set to your actual MQTT server IP
MQTT_SERVER_PORT = 1883       # MQTT server port
PROXY_IP = "127.0.0.1"        # Proxy IP where the proxy listens
PROXY_PORT = 8888             # Port where the proxy listens
OUTPUT_DIR = "output_mqtt"    # Directory to save logs

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

class MQTTProxy:
    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self.server_socket = None
        self.current_state = None
        self.transitions = []
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self.handle_client, daemon=True).start()

    def handle_client(self):
        try:
            self.connect_to_server()
            threading.Thread(target=self.receive_from_server, daemon=True).start()

            while True:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                self.server_socket.sendall(data)
                self.process_client_command(data)
        except (OSError, socket.error) as e:
            logging.error(f"Socket error handling client: {e}")
        finally:
            self.cleanup_sockets()

    def connect_to_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((MQTT_SERVER_IP, MQTT_SERVER_PORT))
        logging.info(f"Connected to MQTT server at {MQTT_SERVER_IP}:{MQTT_SERVER_PORT}")

    def receive_from_server(self):
        try:
            while True:
                data = self.server_socket.recv(4096)
                if not data:
                    break
                self.client_socket.sendall(data)
                self.process_server_response(data)
        except (OSError, socket.error) as e:
            logging.error(f"Socket error receiving from server: {e}")
        finally:
            self.cleanup_sockets()

    def parse_mqtt_packet(self, data):
        if len(data) < 2:
            return "UNKNOWN", data

        packet_type = (data[0] >> 4) & 0x0F
        mqtt_packet_types = {
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
        }

        packet_type_name = mqtt_packet_types.get(packet_type, "UNKNOWN")
        return packet_type_name, data

    def process_client_command(self, data):
        packet_type, _ = self.parse_mqtt_packet(data)
        self.current_state = packet_type
        self.log_raw_message(data, packet_type, "client")

    def process_server_response(self, data):
        packet_type, _ = self.parse_mqtt_packet(data)
        if self.current_state:
            with self.lock:
                self.transitions.append([self.current_state, packet_type])
                self.write_transition_map()
        self.current_state = packet_type
        # Also log the server response in binary format
        self.log_raw_message(data, packet_type, "server")

    def log_raw_message(self, message, command_type, source):
        try:
            # Use a timestamp to create a unique filename for each message.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(OUTPUT_DIR, f"{command_type}_{source}_{timestamp}.raw")
            with open(filename, 'wb') as file:
                file.write(message)
            logging.info(f"{source.capitalize()} message logged in {filename}.")
        except Exception as e:
            logging.error(f"Error logging {source} message: {e}")

    def write_transition_map(self):
        try:
            filename = os.path.join(OUTPUT_DIR, 'transition_map.json')
            with open(filename, 'w') as file:
                json.dump(self.transitions, file, indent=2)
            logging.info("Transition map updated.")
        except Exception as e:
            logging.error(f"Error writing transition map: {e}")

    def cleanup_sockets(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                logging.error(f"Error closing client socket: {e}")

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logging.error(f"Error closing server socket: {e}")

def start_proxy():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((PROXY_IP, PROXY_PORT))
    server_socket.listen(5)
    logging.info(f"MQTT Proxy Server listening on {PROXY_IP}:{PROXY_PORT}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            logging.info(f"Accepted connection from {client_address}")
            proxy = MQTTProxy(client_socket, client_address)
            proxy.start()
    except Exception as e:
        logging.error(f"Error starting proxy: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_proxy()
