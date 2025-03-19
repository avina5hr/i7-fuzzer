import pandas as pd

# Path to your CSV file
LABELS_FILE = '/home/rajendra2024/mutation_py_code/output.csv'

# Load the CSV data into a DataFrame
labels_df = pd.read_csv(LABELS_FILE)

# Perform Min-Max Scaling on the 'Fitness Score' column
min_value = labels_df['Fitness Score'].min()
max_value = labels_df['Fitness Score'].max()

# Apply Min-Max scaling formula
labels_df['Fitness Score'] = (labels_df['Fitness Score'] - min_value) / (max_value - min_value)

# Display the scaled data
print(labels_df)

# Optionally, save the scaled data back to a CSV file
labels_df.to_csv('/home/rajendra2024/mutation_py_code/scaled_output.csv', index=False)

