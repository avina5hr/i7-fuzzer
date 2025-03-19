import os
import random
import string
import re

# Regex pattern to identify IP addresses, ports, and session IDs
ip_port_session_pattern = re.compile(
    r'\b(\d{1,3}\.){3}\d{1,3}\b|\b\d{1,5}\b|Session: [\w-]+', re.IGNORECASE)

# Define a broader character set for mutations
extended_characters = string.printable + ''.join(chr(i) for i in range(128, 256))


def generate_mutations(value, positions, mutation_type, num_mutations):
    """
    Generate mutations for specified positions in the value.
    """
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
    """
    Save mutated payloads with a systematic filename.
    """
    pos_str = "_".join(map(str, positions))
    filename = os.path.join(output_dir, f"{packet_type}_{media_type}_pos_{pos_str}_mutation_{mutation_num}_{mutation_type}.raw")
    with open(filename, 'w') as f:
        f.write(payload)


def identify_rtsp_packet_type(packet_data):
    """
    Identify the RTSP method in the packet data.
    """
    rtsp_methods = ["OPTIONS", "DESCRIBE", "SETUP", "PLAY", "PAUSE", "TEARDOWN"]
    for method in rtsp_methods:
        if packet_data.startswith(method):
            return method
    return "OTHER"


def mutate_rtsp_packet(packet_data, output_dir, file_extension, max_positions_to_mutate=6, num_mutations_per_position=100):
    """
    Apply mutations to RTSP packets and save them.
    """
    packet_type = identify_rtsp_packet_type(packet_data)
    media_type = file_extension
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


def main(input_dir='/home/rajendra2024/mutation_py_code/live_555_code/output',
         output_dir='/home/rajendra2024/mutation_py_code/live_555_code/mutated_message_1',
         max_positions_to_mutate=6, num_mutations_per_position=100):
    """
    Main function to iterate over input files and apply mutations.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory {input_dir} does not exist.")
        return

    os.makedirs(output_dir, exist_ok=True)

    raw_files = [f for f in os.listdir(input_dir) if f.endswith('.raw')]
    if not raw_files:
        print(f"No .raw files found in {input_dir}.")
        return

    for packet_file in raw_files:
        file_extension = os.path.splitext(packet_file)[0].split('_')[-1]
        print(f"Processing file: {packet_file}, with media type: {file_extension}")

        with open(os.path.join(input_dir, packet_file), 'r') as f:
            packet_data = f.read()
            mutate_rtsp_packet(packet_data, output_dir, file_extension, max_positions_to_mutate, num_mutations_per_position)


if __name__ == "__main__":
    main()

