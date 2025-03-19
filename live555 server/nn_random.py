import os
import random
import string
import re
import shutil
import numpy as np
from collections import defaultdict

# Constants
INPUT_DIR = '/home/rajendra2024/mutation_py_code/live_555_code/output'
MUTATION_DIR = '/home/rajendra2024/mutation_py_code/live_555_code/mutated_message'
MAX_FILE_SIZE = 200
MAX_POSITIONS_TO_MUTATE = 7  # Max 7 bits per mutation
MIN_POSITIONS_TO_MUTATE = 4  # Min 4 bits per mutation
NUM_MUTATIONS_PER_PACKET = 100  # Number of mutations per packet

# Extended character set for mutations
extended_characters = string.printable + ''.join(chr(i) for i in range(128, 256))

# Regex for protected segments
ip_port_session_pattern = re.compile(
    r'\b(\d{1,3}\.){3}\d{1,3}\b|\b\d{1,5}\b|Session: [\w-]+', re.IGNORECASE
)

def generate_mutations(value, positions, mutation_type):
    """Generate mutations for specified positions in the value."""
    mutations = []
    protected_segments = [(m.start(), m.end()) for m in ip_port_session_pattern.finditer(value)]
    
    # Ensure mutations do not fall in protected segments
    if any(any(start <= pos < end for pos in positions) for start, end in protected_segments):
        return mutations
    
    mutated_value = list(value)
    for pos in positions:
        random_char = random.choice(extended_characters)
        if mutation_type == 'insertion':
            mutated_value.insert(pos, random_char)
        elif mutation_type == 'replacement':
            mutated_value[pos] = random_char
    
    return ''.join(mutated_value)

def save_mutated_packet(payload, file_name, positions, mutation_num, mutation_type, output_dir):
    """Save mutated payloads with structured filename."""
    pos_str = "_".join(map(str, positions))  # Mutation positions
    filename = f"{file_name}_pos_{pos_str}_mutation_{mutation_num}_{mutation_type}.raw"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(payload)

def mutate_rtsp_packet(packet_data, output_dir, file_name):
    """Apply mutations to RTSP packets at random positions and save them."""
    length = len(packet_data)
    if length < MIN_POSITIONS_TO_MUTATE:
        return  # Skip short packets
    
    for _ in range(NUM_MUTATIONS_PER_PACKET):
        num_positions = random.randint(MIN_POSITIONS_TO_MUTATE, MAX_POSITIONS_TO_MUTATE)  # Randomly pick 4-7 positions
        positions = random.sample(range(length), num_positions)  # Select unique random positions
        
        # Generate insertion mutation
        mutated_payload = generate_mutations(packet_data, positions, 'insertion')
        if mutated_payload:
            save_mutated_packet(mutated_payload, file_name, positions, _, 'insertion', output_dir)

        # Generate replacement mutation
        mutated_payload = generate_mutations(packet_data, positions, 'replacement')
        if mutated_payload:
            save_mutated_packet(mutated_payload, file_name, positions, _, 'replacement', output_dir)

def main():
    """Main function to mutate RTSP packets."""
    raw_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.raw')]
    print(f"Found {len(raw_files)} raw files for mutation.")
    
    for packet_file in raw_files:
        with open(os.path.join(INPUT_DIR, packet_file), 'r') as f:
            packet_data = f.read()
            mutate_rtsp_packet(packet_data, MUTATION_DIR, packet_file)
    
    print(f"Mutation process completed. Files saved in {MUTATION_DIR}.")

if __name__ == "__main__":
    main()
