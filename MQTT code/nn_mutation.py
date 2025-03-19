import os
import random
import re
import shutil
import numpy as np
import pandas as pd
import tensorflow as tf
from collections import defaultdict

# === Configuration Constants ===
INPUT_DIR = '/home/rajendra2024/mqtt_code/output'
MUTATION_DIR = '/home/rajendra2024/mqtt_code/mutated_message'
FILTERED_OUTPUT_DIR = './filtered_files/'
SAVE_MODEL_PATH = './lstm_model_with_extra_layer.h5'
PREDICTIONS_CSV = './predicted_probabilities.csv'

MAX_FILE_SIZE = 200             # Maximum number of bytes per packet for NN processing
THRESHOLD = 0.40                # Threshold for filtering mutated packets
MAX_POSITIONS_TO_MUTATE = 5     # Mutate over 1 to 5 positions
NUM_MUTATIONS_PER_POSITION = 1000  # 1000 mutations per combination

# Regex for protected segments (applied to the latin1-decoded version)
ip_port_session_pattern = re.compile(
    r'\b(\d{1,3}\.){3}\d{1,3}\b|\b\d{1,5}\b|Session: [\w-]+', re.IGNORECASE
)

def random_byte():
    """Return a random integer between 0 and 255."""
    return random.randint(0, 255)

def clear_directory(directory):
    """Delete all files in the specified directory."""
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.makedirs(directory, exist_ok=True)

def count_files_in_directory(directory):
    return sum(1 for entry in os.listdir(directory) if os.path.isfile(os.path.join(directory, entry)))

def process_mqtt_packet(packet):
    """
    Convert a raw MQTT packet (bytes) to a normalized numerical array.
    Each byte is normalized to [0, 1]. The array is padded or truncated to MAX_FILE_SIZE.
    """
    packet_array = np.array(list(packet))
    if len(packet_array) < MAX_FILE_SIZE:
        packet_array = np.pad(packet_array, (0, MAX_FILE_SIZE - len(packet_array)), 'constant')
    else:
        packet_array = packet_array[:MAX_FILE_SIZE]
    return packet_array / 255.0

def load_prediction_data():
    """
    Load mutated MQTT messages from MUTATION_DIR (as binary files)
    and process them for prediction.
    """
    messages = []
    file_names = []
    for file_name in os.listdir(MUTATION_DIR):
        if file_name.endswith('.raw'):
            file_path = os.path.join(MUTATION_DIR, file_name)
            with open(file_path, 'rb') as f:
                message = f.read()
            processed_message = process_mqtt_packet(message)
            messages.append(processed_message)
            file_names.append(file_name)
    if not messages:
        raise ValueError("No valid messages were loaded.")
    return np.array(messages), file_names

def extract_packet_and_media_type(file_name):
    """
    Extract the packet type and media type from the filename.
    If the filename (without extension) contains an underscore (e.g., CONNECT_mqtt.raw),
    the part before the underscore is the packet type and the rest is the media type.
    Otherwise, use the whole base name as the packet type and default the media type to "mqtt".
    """
    base_name = file_name.split('.')[0]
    parts = base_name.split('_')
    if len(parts) >= 2:
        return parts[0].upper(), parts[1].lower()
    else:
        return base_name.upper(), "mqtt"

def generate_mutations(value, positions, mutation_type, num_mutations):
    """
    Generate mutations for the given binary message (value) at specified positions.
    For checking protected segments, the binary is decoded using latin1.
    If any position falls in a protected segment, no mutations are generated.
    Returns a list of tuples: (mutated_bytes, mutation_type, positions).
    """
    value_str = value.decode('latin1')
    protected_segments = [(m.start(), m.end()) for m in ip_port_session_pattern.finditer(value_str)]
    if any(any(pos >= start and pos < end for pos in positions) for start, end in protected_segments):
        return []
    
    mutations = []
    for _ in range(num_mutations):
        mutated_value = bytearray(value)  # Make a mutable copy
        for pos in positions:
            b = random_byte()
            if mutation_type == 'insertion':
                mutated_value.insert(pos, b)
            elif mutation_type == 'replacement':
                mutated_value[pos] = b
        mutations.append((bytes(mutated_value), mutation_type, positions))
    return mutations

def save_mutated_packet(payload, packet_type, positions, mutation_num, mutation_type, output_dir, media_type):
    """
    Save the mutated payload (bytes) to a file.
    The filename is constructed to include the packet type, media type,
    mutation positions, mutation number, and mutation type.
    """
    pos_str = "_".join(map(str, positions))
    filename = f"{packet_type}_{media_type}_pos_{pos_str}_mutation_{mutation_num}_{mutation_type}.raw"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(payload)

def mutate_mqtt_packet(packet_data, output_dir, file_name,
                         max_positions_to_mutate=MAX_POSITIONS_TO_MUTATE,
                         num_mutations_per_position=NUM_MUTATIONS_PER_POSITION):
    """
    Apply mutations to an MQTT packet (binary data) and save them.
    Returns a tuple (actual_count, potential_count) where:
      - actual_count is the number of mutations actually generated.
      - potential_count is the theoretical total if not blocked by protected segments.
    """
    # Use the unified extraction logic for filename
    packet_type, media_type = extract_packet_and_media_type(file_name)
    
    length = len(packet_data)
    actual_count = 0
    potential_count = 0
    
    for num_positions in range(1, max_positions_to_mutate + 1):
        for start in range(length - num_positions + 1):
            positions = list(range(start, start + num_positions))
            packet_str = packet_data.decode('latin1')
            protected_segments = [(m.start(), m.end()) for m in ip_port_session_pattern.finditer(packet_str)]
            if not any(any(pos >= seg_start and pos < seg_end for pos in positions)
                       for seg_start, seg_end in protected_segments):
                potential_count += 2 * num_mutations_per_position  # Two mutation types: insertion and replacement
            
            insert_mutations = generate_mutations(packet_data, positions, 'insertion', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, pos_list) in enumerate(insert_mutations):
                save_mutated_packet(mutated_payload, packet_type, pos_list, mutation_num, mutation_type, output_dir, media_type)
            replace_mutations = generate_mutations(packet_data, positions, 'replacement', num_mutations_per_position)
            for mutation_num, (mutated_payload, mutation_type, pos_list) in enumerate(replace_mutations):
                save_mutated_packet(mutated_payload, packet_type, pos_list, mutation_num, mutation_type, output_dir, media_type)
            actual_count += len(insert_mutations) + len(replace_mutations)
    return actual_count, potential_count

def save_filtered_file(file_name, prob, mutation_dir, filtered_output_dir):
    """
    Copy a file that passes the prediction threshold into a categorized directory.
    """
    try:
        packet_type, media_type = extract_packet_and_media_type(file_name)
        subfolder_path = os.path.join(filtered_output_dir, media_type, packet_type)
        os.makedirs(subfolder_path, exist_ok=True)
        shutil.copy(os.path.join(mutation_dir, file_name), os.path.join(subfolder_path, file_name))
        return media_type, packet_type, True
    except Exception as e:
        print(f"Error saving file {file_name}: {e}")
        return None, None, False

def summarize_filtered_files(filtered_output_dir):
    """
    Summarize the number of filtered files by media and packet type.
    """
    stats = defaultdict(lambda: {'filtered': 0, 'dropped': 0})
    for media_folder in os.listdir(filtered_output_dir):
        media_folder_path = os.path.join(filtered_output_dir, media_folder)
        if os.path.isdir(media_folder_path):
            for packet_folder in os.listdir(media_folder_path):
                packet_folder_path = os.path.join(media_folder_path, packet_folder)
                if os.path.isdir(packet_folder_path):
                    count = len([f for f in os.listdir(packet_folder_path)
                                 if os.path.isfile(os.path.join(packet_folder_path, f))])
                    stats[f"{media_folder}/{packet_folder}"]['filtered'] += count
    return stats

def main():
    # Clear previous mutated and filtered files
    clear_directory(MUTATION_DIR)
    clear_directory(FILTERED_OUTPUT_DIR)
    
    # --- Mutation Process ---
    raw_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.raw')]
    print(f"Found {len(raw_files)} raw files for mutation.\n")
    
    mutation_summary = {}  # (actual, potential) counts per input file
    for packet_file in raw_files:
        with open(os.path.join(INPUT_DIR, packet_file), 'rb') as f:
            packet_data = f.read()
            actual, potential = mutate_mqtt_packet(packet_data, MUTATION_DIR, packet_file)
            mutation_summary[packet_file] = (actual, potential)
    
    mutated_files_count = count_files_in_directory(MUTATION_DIR)
    print(f"Generated {mutated_files_count} mutated files.\n")
    
    print("Mutation Summary per Input File (Actual / Potential):")
    for file_name, (actual, potential) in mutation_summary.items():
        print(f"{file_name}: {actual}/{potential}")
    
    # --- Prediction and Filtering ---
    print("\nLoading trained model...")
    model = tf.keras.models.load_model(SAVE_MODEL_PATH)
    print("Model loaded successfully.")
    
    print("Loading data for prediction...")
    X_pred, file_names = load_prediction_data()
    X_pred = np.expand_dims(X_pred, axis=-1)  # For LSTM input
    
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
                packet_type, media_type = extract_packet_and_media_type(file_name)
                filtered_stats[f"{media_type}/{packet_type}"]['dropped'] += 1
            except ValueError:
                pass
    
    print("\nFiltering Summary:")
    total_filtered = sum(stat['filtered'] for stat in filtered_stats.values())
    total_dropped = sum(stat['dropped'] for stat in filtered_stats.values())
    print(f"Total files processed: {len(file_names)}")
    print(f"Total files filtered: {total_filtered}")
    print(f"Total files dropped: {total_dropped}")
    
    print("\nOverall Filtering Ratio:")
    if mutated_files_count > 0:
        ratio = total_filtered / mutated_files_count
        print(f"Filtered files: {total_filtered} / Mutated files: {mutated_files_count} ({ratio:.2%})")
    else:
        print("No mutated files generated.")
    
    print("\nFolder-wise Summary:")
    for folder, stats in filtered_stats.items():
        print(f"{folder}: Filtered = {stats['filtered']}, Dropped = {stats['dropped']}")
    
    print(f"\nFiltered files saved to {FILTERED_OUTPUT_DIR}.")

if __name__ == "__main__":
    main()

