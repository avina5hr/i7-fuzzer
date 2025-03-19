import os
import random
import string
import re
import shutil
import numpy as np
import pandas as pd
import tensorflow as tf
from collections import defaultdict

# Constants
INPUT_DIR = '/home/rajendra2024/mutation_py_code/live_555_code/output'
MUTATION_DIR = '/home/rajendra2024/mutation_py_code/live_555_code/mutated_message'
FILTERED_OUTPUT_DIR = './filtered_files/'
SAVE_MODEL_PATH = './lstm_model_with_extra_layer.h5'
PREDICTIONS_CSV = './predicted_probabilities.csv'
MAX_FILE_SIZE = 200
THRESHOLD = 0.40
MAX_POSITIONS_TO_MUTATE = 6
NUM_MUTATIONS_PER_POSITION = 100

# Regex for protected segments
ip_port_session_pattern = re.compile(
    r'\b(\d{1,3}\.){3}\d{1,3}\b|\b\d{1,5}\b|Session: [\w-]+', re.IGNORECASE
)

# Define extended character set
extended_characters = string.printable + ''.join(chr(i) for i in range(128, 256))

def count_files_in_directory(directory):
    """Count the number of files in a directory."""
    return sum(1 for entry in os.listdir(directory) if os.path.isfile(os.path.join(directory, entry)))

def process_rtsp_packet(packet):
    """Convert raw RTSP packet to normalized numerical array."""
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
                rtsp_message = f.read()
            processed_message = process_rtsp_packet(rtsp_message)
            messages.append(processed_message)
            file_names.append(file_name)
    if not messages:
        raise ValueError("No valid RTSP messages were loaded.")
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


def save_mutated_packet(payload, packet_type, positions, mutation_num, mutation_type, output_dir, media_type):
    """Save mutated payloads with a systematic filename including media type."""
    pos_str = "_".join(map(str, positions))  # Positions where mutations occurred
    packet_type = packet_type.upper()
    media_type = media_type.lower()
    filename = f"{packet_type}_{media_type}_pos_{pos_str}_mutation_{mutation_num}_{mutation_type}.raw"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists
    with open(filepath, 'w') as f:
        f.write(payload)


def mutate_rtsp_packet(packet_data, output_dir, file_name, max_positions_to_mutate=6, num_mutations_per_position=100):
    """Apply mutations to RTSP packets and save them."""
    try:
        packet_type, media_type = file_name.split('.')[0].split('_')
    except ValueError:
        packet_type, media_type = "UNKNOWN", "unknown"  # Default fallback

    packet_type = packet_type.upper()
    media_type = media_type.lower()

    length = len(packet_data)

    for num_positions in range(1, max_positions_to_mutate + 1):  # Mutating 1 to max_positions_to_mutate
        for start in range(length - num_positions + 1):  # Loop through all valid starting positions
            positions = list(range(start, start + num_positions))

            # Generate insertion mutations
            insert_mutations = generate_mutations(packet_data, positions, 'insertion', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, positions) in enumerate(insert_mutations):
                save_mutated_packet(mutated_payload, packet_type, positions, mutation_num, mutation_type, output_dir, media_type)

            # Generate replacement mutations
            replace_mutations = generate_mutations(packet_data, positions, 'replacement', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, positions) in enumerate(replace_mutations):
                save_mutated_packet(mutated_payload, packet_type, positions, mutation_num, mutation_type, output_dir, media_type)


def save_filtered_file(file_name, prob, mutation_dir, filtered_output_dir):
    """Save filtered files into categorized directories."""
    try:
        packet_type, media_type = file_name.split('_')[:2]  # Extract packet and media type
        subfolder_path = os.path.join(filtered_output_dir, media_type, packet_type)
        os.makedirs(subfolder_path, exist_ok=True)
        shutil.copy(os.path.join(mutation_dir, file_name), os.path.join(subfolder_path, file_name))
        return media_type, packet_type, True
    except Exception as e:
        print(f"Error saving file {file_name}: {e}")
        return None, None, False


def summarize_filtered_files(filtered_output_dir):
    """Summarize the number of filtered files by media and packet type."""
    stats = defaultdict(lambda: {'filtered': 0, 'dropped': 0})
    for media_folder in os.listdir(filtered_output_dir):
        media_folder_path = os.path.join(filtered_output_dir, media_folder)
        if os.path.isdir(media_folder_path):
            for packet_folder in os.listdir(media_folder_path):
                packet_folder_path = os.path.join(media_folder_path, packet_folder)
                if os.path.isdir(packet_folder_path):
                    filtered_count = len([f for f in os.listdir(packet_folder_path) if os.path.isfile(os.path.join(packet_folder_path, f))])
                    stats[f"{media_folder}/{packet_folder}"]['filtered'] += filtered_count
    return stats


def main():
    # Mutation Process
    raw_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.raw')]
    print(f"Found {len(raw_files)} raw files for mutation.")
    
    for packet_file in raw_files:
        with open(os.path.join(INPUT_DIR, packet_file), 'r') as f:
            packet_data = f.read()
            mutate_rtsp_packet(packet_data, MUTATION_DIR, packet_file)

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
    filtered_stats = defaultdict(lambda: {'filtered': 0, 'dropped': 0})

    for file_name, prob in zip(file_names, predicted_probs.flatten()):
        if prob >= THRESHOLD:
            media_type, packet_type, success = save_filtered_file(file_name, prob, MUTATION_DIR, FILTERED_OUTPUT_DIR)
            if success:
                filtered_stats[f"{media_type}/{packet_type}"]['filtered'] += 1
        else:
            try:
                packet_type, media_type = file_name.split('_')[:2]
                filtered_stats[f"{media_type}/{packet_type}"]['dropped'] += 1
            except ValueError:
                pass

    print("\nFiltering Summary:")
    total_filtered = sum(stat['filtered'] for stat in filtered_stats.values())
    total_dropped = sum(stat['dropped'] for stat in filtered_stats.values())
    print(f"Total files processed: {len(file_names)}")
    print(f"Total files filtered: {total_filtered}")
    print(f"Total files dropped: {total_dropped}")

    print("\nFolder-wise Summary:")
    for folder, stats in filtered_stats.items():
        print(f"{folder}: Filtered = {stats['filtered']}, Dropped = {stats['dropped']}")

    print(f"\nFiltered files saved to {FILTERED_OUTPUT_DIR}.")


if __name__ == "__main__":
    main()

