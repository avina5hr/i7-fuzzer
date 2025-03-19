import os
import random
import string
import re
import shutil
import numpy as np
import pandas as pd
import tensorflow as tf

# Constants
INPUT_DIR = '/home/rajendra2024/mutation_py_code/output_ftp'
MUTATION_DIR = '/home/rajendra2024/mutation_py_code/ftp_code/mutated_message'
FILTERED_OUTPUT_DIR = './filtered_files_ftp/'
SAVE_MODEL_PATH = './lstm_model_with_extra_layer.h5'
PREDICTIONS_CSV = './predicted_probabilities_ftp.csv'
MAX_FILE_SIZE = 200
THRESHOLD = 0.26
MAX_POSITIONS_TO_MUTATE = 6
NUM_MUTATIONS_PER_POSITION = 100

# Regex for protected segments (IP, port, session patterns)
ip_port_session_pattern = re.compile(
    r'\b(\d{1,3}\.){3}\d{1,3}\b|\b\d{1,5}\b', re.IGNORECASE
)

# Define extended character set
extended_characters = string.printable + ''.join(chr(i) for i in range(128, 256))

# FTP-specific message types
ftp_commands = [
    "USER", "PASS", "QUIT", "DELE", "EPSV", "FEAT", "LIST", "MKD", "RMD", 
    "RETR", "SIZE", "STOR", "SYST", "TYPE"
]

def process_ftp_packet(packet):
    """Convert raw FTP packet to normalized numerical array."""
    packet_array = np.array([int(byte) for byte in packet])
    if len(packet_array) < MAX_FILE_SIZE:
        packet_array = np.pad(packet_array, (0, MAX_FILE_SIZE - len(packet_array)), 'constant')
    else:
        packet_array = packet_array[:MAX_FILE_SIZE]
    return packet_array / 255.0  # Normalize to range [0, 1]

def load_prediction_data():
    """Load raw files from MUTATION_DIR and process them for prediction."""
    messages = []
    file_names = []
    for file_name in os.listdir(MUTATION_DIR):
        if file_name.endswith('.raw'):
            file_path = os.path.join(MUTATION_DIR, file_name)
            with open(file_path, 'rb') as f:
                ftp_message = f.read()
            processed_message = process_ftp_packet(ftp_message)
            messages.append(processed_message)
            file_names.append(file_name)
    if not messages:
        raise ValueError("No valid FTP messages were loaded.")
    return np.array(messages), file_names

def generate_mutations(value, positions, mutation_type, num_mutations):
    """Generate mutations for specified positions in the value."""
    mutations = []
    protected_segments = [(m.start(), m.end()) for m in ip_port_session_pattern.finditer(value)]

    # Skip mutations if any positions fall in protected segments
    if any(any(start <= pos < end for pos in positions) for start, end in protected_segments):
        return mutations

    for _ in range(num_mutations):
        mutated_value = list(value)
        for pos in positions:
            random_char = random.choice(extended_characters)
            if mutation_type == 'insertion':
                mutated_value.insert(pos, random_char)
            elif mutation_type == 'replacement':
                mutated_value[pos] = random_char
        mutations.append((''.join(mutated_value), mutation_type, positions))
    return mutations

def save_mutated_packet(payload, packet_type, positions, mutation_num, mutation_type, output_dir):
    """Save mutated payloads with a systematic filename."""
    pos_str = "_".join(map(str, positions))  # Positions where mutations occurred
    packet_type = packet_type.upper()
    filename = f"{packet_type}_pos_{pos_str}_mutation_{mutation_num}_{mutation_type}.raw"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists
    with open(filepath, 'w') as f:
        f.write(payload)

def identify_ftp_packet_type(packet_data):
    """Identify the FTP command in the packet data."""
    for command in ftp_commands:
        if packet_data.startswith(command):
            return command
    return "UNKNOWN"

def mutate_ftp_packet(packet_data, output_dir, file_name, max_positions_to_mutate=6, num_mutations_per_position=100):
    """Apply mutations to FTP packets and save them."""
    try:
        packet_type = file_name.split('.')[0]  # Extract packet type from filename
    except ValueError:
        packet_type = "UNKNOWN"  # Default fallback

    packet_type = packet_type.upper()
    length = len(packet_data)

    for num_positions in range(1, max_positions_to_mutate + 1):  # Mutating 1 to max_positions_to_mutate
        for start in range(length - num_positions + 1):  # Loop through all valid starting positions
            positions = list(range(start, start + num_positions))

            # Generate insertion mutations
            insert_mutations = generate_mutations(packet_data, positions, 'insertion', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, positions) in enumerate(insert_mutations):
                save_mutated_packet(mutated_payload, packet_type, positions, mutation_num, mutation_type, output_dir)

            # Generate replacement mutations
            replace_mutations = generate_mutations(packet_data, positions, 'replacement', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, positions) in enumerate(replace_mutations):
                save_mutated_packet(mutated_payload, packet_type, positions, mutation_num, mutation_type, output_dir)

def count_files_in_directory(directory):
    """Count the number of files in a given directory and its subdirectories."""
    total_count = 0
    for root, _, files in os.walk(directory):
        total_count += len(files)
    return total_count

def count_filtered_files_by_type(filtered_output_dir):
    """Count the filtered files grouped by FTP command."""
    command_counts = {}
    for command_folder in os.listdir(filtered_output_dir):
        command_folder_path = os.path.join(filtered_output_dir, command_folder)
        if os.path.isdir(command_folder_path):
            file_count = len([f for f in os.listdir(command_folder_path) if os.path.isfile(os.path.join(command_folder_path, f))])
            command_counts[command_folder] = file_count
    return command_counts

def main():
    # Mutation Process
    raw_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.raw')]
    print(f"Found {len(raw_files)} raw files for mutation.")
    
    for packet_file in raw_files:
        with open(os.path.join(INPUT_DIR, packet_file), 'r') as f:
            packet_data = f.read()
            mutate_ftp_packet(packet_data, MUTATION_DIR, packet_file)

    mutated_files_count = count_files_in_directory(MUTATION_DIR)
    print(f"Generated {mutated_files_count} mutated files.")

    # Prediction and Filtering
    print("Loading trained model...")
    model = tf.keras.models.load_model(SAVE_MODEL_PATH)
    print("Model loaded successfully.")

    print("Loading data for prediction...")
    X_pred, file_names = load_prediction_data()
    X_pred = np.expand_dims(X_pred, axis=-1)  # Add channel dimension for LSTM

    print("Predicting probabilities...")
    predicted_probs = model.predict(X_pred)

    print(f"Saving predictions to {PREDICTIONS_CSV}...")
    predictions_df = pd.DataFrame({
        'File Name': file_names,
        'Predicted Probability': predicted_probs.flatten()
    })
    predictions_df.to_csv(PREDICTIONS_CSV, index=False)

    print("Filtering files based on threshold...")
    os.makedirs(FILTERED_OUTPUT_DIR, exist_ok=True)
    for file_name, prob in zip(file_names, predicted_probs.flatten()):
        if prob >= THRESHOLD:
            try:
                packet_type = file_name.split('_')[0].upper()  # Extract command type
                
                # Create subfolder for each FTP command
                subfolder_path = os.path.join(FILTERED_OUTPUT_DIR, packet_type)
                os.makedirs(subfolder_path, exist_ok=True)
                
                # Save the file in the appropriate subfolder
                shutil.copy(os.path.join(MUTATION_DIR, file_name), os.path.join(subfolder_path, file_name))
            except Exception as e:
                print(f"Error filtering file {file_name}: {e}")

    # Display filtered file counts
    filtered_counts = count_filtered_files_by_type(FILTERED_OUTPUT_DIR)
    print("Filtered file counts by FTP command:")
    for command, count in filtered_counts.items():
        print(f"{command}: {count}")

if __name__ == "__main__":
    main()

