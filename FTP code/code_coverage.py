import os
import csv
import subprocess
import logging

# Configure logging (optional)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def extract_coverage_entries(coverage_file):
    """
    Runs sancov.py to extract coverage entries from a file.
    Returns a list of entries (edges) if successful, or None on error.
    """
    result = subprocess.run(
        ['python3', 'sancov.py', 'print', coverage_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Error processing coverage file {coverage_file}:\n{result.stderr}")
        return None

    # Split the output into individual lines (coverage edges)
    entries = result.stdout.strip().splitlines()
    return entries

def process_coverage_folder(coverage_folder, output_csv):
    """
    Processes all coverage files in the given folder and writes the results
    to a CSV file with columns: filename, total_count, and edges.
    """
    # List only files (ignore directories)
    coverage_files = [
        f for f in os.listdir(coverage_folder)
        if os.path.isfile(os.path.join(coverage_folder, f))
    ]
    
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write CSV header
        writer.writerow(['filename', 'total_count', 'edges'])
        
        for filename in coverage_files:
            full_path = os.path.join(coverage_folder, filename)
            logging.info(f"Processing file: {filename}")
            entries = extract_coverage_entries(full_path)
            if entries is None:
                logging.warning(f"Skipping file due to error: {filename}")
                continue
            
            total_count = len(entries)
            # Join the list of entries into one string with semicolon as separator.
            edges_str = ";".join(entries)
            writer.writerow([filename, total_count, edges_str])
            logging.info(f"File '{filename}': {total_count} entries extracted.")
    
    logging.info(f"CSV output written to: {output_csv}")
if __name__ == "__main__":
    # Hard-coded paths - modify these as needed
    coverage_folder = "/home/rajendra2024/mutation_py_code/ftp_code/code_coverage"
    output_csv = "ftp.csv"
    
    process_coverage_folder(coverage_folder, output_csv)


