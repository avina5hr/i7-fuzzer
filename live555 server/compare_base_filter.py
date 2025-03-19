
import os
import subprocess
import csv

# Define the directory paths
UNMUTATED_DIR = '/home/rajendra2024/mutation_py_code/coverage_sancov'  # Path where unmutated files are stored
BASE_MUTATED_DIR = '/home/rajendra2024/live555_clang/coverage_1/'  # Base path for mutated files

def extract_edges(sancov_file):
    """Extracts edges from a sancov file using sancov.py."""
    try:
        print(f"Running sancov.py on {sancov_file}")  # Debug: Command starting
        result = subprocess.run(['python3', 'sancov.py', 'print', sancov_file], stdout=subprocess.PIPE, check=True)
        output = result.stdout.decode().strip()
        print(f"Edges from {sancov_file}: {output}")  # Debug: Print the raw output
        edges = set(int(edge, 16) for edge in output.split() if edge)
        return len(edges), edges
    except subprocess.CalledProcessError as e:
        print(f"Error processing {sancov_file}: {e}")
        return 0, set()

def find_similar_edges(base_file, mutated_files, output_file):
    """Find and write similar edges between the base file and mutated files to a CSV."""
    base_total, base_edges = extract_edges(base_file)  # Get number of edges and edges set for unmutated file
    results = []

    for mutated_file in mutated_files:
        print(f"Comparing with {mutated_file}")  # Debug: File comparison starting
        mutated_total, mutated_edges = extract_edges(mutated_file)
        common_edges = base_edges & mutated_edges
        total_common = len(common_edges)
        
        # Get only the file name from the full path
        mutated_file_name = os.path.basename(mutated_file)
        
        # Append only the mutated file details and the total number of edges
        results.append([mutated_file_name, mutated_total, base_total, total_common])

    save_to_csv(results, output_file)
    print(f"Comparison results saved to {output_file}")

def save_to_csv(results, output_file):
    """Save the comparison results to a CSV file."""
    print(f"Writing results to {output_file}")  # Debug: Starting CSV write
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Add columns for the total number of edges
        writer.writerow(['File', 'Total Mutated Edges', 'Total Base Edges', 'Number of Common Edges'])
        for row in results:
            writer.writerow(row)

def main():
    # Iterate over each message type directory in the base mutated directory
    for message_type in os.listdir(BASE_MUTATED_DIR):
        message_path = os.path.join(BASE_MUTATED_DIR, message_type)
        
        if os.path.isdir(message_path):
            print(f"Processing message type directory: {message_type}")
            
            # Construct the unmutated file path for this message type
            base_file_name = f"edge_coverage_{message_type.split('_')[0]}.sancov"
            base_file = os.path.join(UNMUTATED_DIR, base_file_name)
            
            if not os.path.exists(base_file):
                print(f"Unmutated file for {message_type} not found: {base_file}")
                continue
            
            # Gather all mutated sancov files for this message type
            mutated_files = [os.path.join(message_path, f) for f in os.listdir(message_path) if f.endswith('.sancov')]
            
            if not mutated_files:
                print(f"No mutated files found for {message_type} in {message_path}")
                continue

            # Output CSV file named after the message type
            csv_output_file = f"{message_type}_coverage_comparison_1_bit.csv"
        
            # Compare the base file to all mutated ones
            find_similar_edges(base_file, mutated_files, csv_output_file)

if __name__ == "__main__":
    main()
