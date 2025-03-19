import csv
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def extract_timestamp(filename: str) -> datetime:
    """
    Extract a timestamp of the form YYYYMMDD_HHMMSS from the filename.
    E.g. from "SETUP_wav_pos_103_mutation_42_replacement_20250218_103022.sancov"
    it extracts '20250218_103022' and converts it into a datetime object.
    """
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        tstamp_str = match.group(1)
        return datetime.strptime(tstamp_str, '%Y%m%d_%H%M%S')
    return None

def process_csv(csv_file: str):
    """
    Reads the CSV and returns:
      - timestamps: list of datetime objects (one per CSV row)
      - cumulative_coverage: running count of unique coverage addresses
    
    Assumes each row has:
      [0]: filename (from which we extract a timestamp)
      [1]: an unused number
      [2]: semicolon-separated addresses (hex strings)
    
    Also prints the extracted addresses and the updated unique set.
    """
    timestamps = []
    cumulative_coverage = []
    unique_addresses = set()
    
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header row if present
        
        for row in reader:
            if len(row) < 3:
                continue  # Skip rows with insufficient data
            filename = row[0].strip()
            addresses_str = row[2].strip()
            ts = extract_timestamp(filename)
            if ts is None:
                continue  # Skip rows without a valid timestamp
            
            # Extract addresses from the third column
            addresses = [addr.strip() for addr in addresses_str.split(';') if addr.strip()]
            print("Extracted addresses from row:", addresses)
            
            # Update the cumulative set of unique addresses
            unique_addresses.update(addresses)
            print("Unique addresses so far:", unique_addresses, "\n")
            
            timestamps.append(ts)
            cumulative_coverage.append(len(unique_addresses))
    
    print("Final cumulative coverage list:", cumulative_coverage)
    return timestamps, cumulative_coverage

def bin_coverage(timestamps, coverage_counts, bin_minutes=30):
    """
    Bins the cumulative coverage data into intervals of 'bin_minutes' minutes.
    For each bin, it uses the maximum cumulative coverage seen so far.
    
    Returns:
      - binned_hours: elapsed time (in hours) for each bin (starting at 0)
      - binned_cov: the maximum cumulative coverage up to that bin
    """
    # Combine and sort by time in case the CSV isn't in order.
    data = sorted(zip(timestamps, coverage_counts), key=lambda x: x[0])
    sorted_ts, sorted_cov = zip(*data)
    
    start_time = sorted_ts[0]
    end_time = sorted_ts[-1]
    current_time = start_time
    
    binned_hours = []
    binned_cov = []
    
    # For each bin, we look at all rows with a timestamp <= current_time
    while current_time <= end_time:
        elapsed_hours = (current_time - start_time).total_seconds() / 3600.0
        
        # Find all cumulative coverage values up to the current bin
        current_values = [cov for ts, cov in zip(sorted_ts, sorted_cov) if ts <= current_time]
        # Use the maximum value seen so far (ensuring non-decreasing behavior)
        bin_val = max(current_values) if current_values else 0
        
        binned_hours.append(elapsed_hours)
        binned_cov.append(bin_val)
        print(f"At {elapsed_hours:.2f} hours, binned coverage is {bin_val}")
        
        current_time += timedelta(minutes=bin_minutes)
    
    return binned_hours, binned_cov

def plot_coverage(x, coverage):
    """
    Plots cumulative coverage vs. elapsed time in hours.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(x, coverage, marker='o', linestyle='-', color='red', label='Coverage')
    plt.xlabel("Time (hours)")
    plt.ylabel("Cumulative Edge Coverage")
    plt.title("Fuzzing Coverage Over Time (30-Minute Bins)")
    plt.xlim(0, max(x) + 0.5)
    plt.ylim(0, None)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

def main():
    csv_file = 'ftp.csv'  # Change to your CSV file path
    
    # Process CSV to extract timestamps and cumulative coverage
    raw_ts, raw_cov = process_csv(csv_file)
    if not raw_ts:
        print("No valid timestamps found.")
        return
    
    # Bin data into 30-minute intervals and convert to elapsed hours
    binned_hours, binned_cov = bin_coverage(raw_ts, raw_cov, bin_minutes=30)
    
    # Plot the binned data
    plot_coverage(binned_hours, binned_cov)

if __name__ == '__main__':
    main()

