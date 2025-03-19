import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
import os
import matplotlib.pyplot as plt

# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './lstm_model_with_extra_layer.h5'
SEED = 12

np.random.seed(SEED)
tf.random.set_seed(SEED)

# Process RTSP Packet
def process_rtsp_packet(packet):
    packet_array = np.array([int(byte) for byte in packet])
    if len(packet_array) < MAX_FILE_SIZE:
        packet_array = np.pad(packet_array, (0, MAX_FILE_SIZE - len(packet_array)), 'constant')
    else:
        packet_array = packet_array[:MAX_FILE_SIZE]
    return packet_array / 255.0  # Normalize to range [0, 1]

# Load Labels
def load_labels(labels_df, message_name):
    label_row = labels_df[labels_df['Mutated File'] == message_name]
    if label_row.empty:
        print(f"No match found for '{message_name}'.")
        return None
    return float(label_row['Fitness Score'].values[0])  # Assuming fitness score is the probability

# Load Training Data
def load_training_data():
    messages = []
    labels = []
    try:
        labels_df = pd.read_csv(LABELS_FILE)
    except FileNotFoundError:
        raise FileNotFoundError(f"Labels file not found at {LABELS_FILE}.")
    
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith('.raw'):
            file_path = os.path.join(DATA_DIR, file_name)
            with open(file_path, 'rb') as f:
                rtsp_message = f.read()
            processed_message = process_rtsp_packet(rtsp_message)
            message_name = os.path.splitext(file_name)[0] + ".sancov"
            label = load_labels(labels_df, message_name)
            if label is not None:
                messages.append(processed_message)
                labels.append(label)
    if not messages:
        raise ValueError("No valid RTSP messages were loaded.")
    return np.array(messages), np.array(labels)

# Load Data
print("Loading data...")
X, y = load_training_data()
X = np.expand_dims(X, axis=-1)  # Add channel dimension for LSTM
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=SEED, shuffle=True)

# Build LSTM Model with an Extra LSTM Layer
def build_lstm_model(input_shape):
    model = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=True),
        BatchNormalization(),
        LSTM(64, return_sequences=True),  # Additional LSTM layer
        BatchNormalization(),
        LSTM(32, return_sequences=False),  # Final LSTM layer
        BatchNormalization(),
        Dense(32, activation='relu'),
        BatchNormalization(),
        Dense(1, activation='sigmoid')  # Output a probability
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae', 'mse'])
    return model

input_shape = (MAX_FILE_SIZE, 1)
model = build_lstm_model(input_shape)
model.summary()

# Train the Model
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
print("Training the model...")
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=30,
    batch_size=64,
    callbacks=[early_stopping],
    verbose=1
)

# Save the Model
print(f"Saving the model to {SAVE_MODEL_PATH}...")
model.save(SAVE_MODEL_PATH)

# Evaluate the Model
print("Evaluating the model...")
y_pred = model.predict(X_val)
r2 = r2_score(y_val, y_pred)
mae = mean_absolute_error(y_val, y_pred)
mse = mean_squared_error(y_val, y_pred)

print(f"R2 Score: {r2}")
print(f"MAE: {mae}")
print(f"MSE: {mse}")

# Plot Training and Validation Loss
plt.figure(figsize=(10, 6))
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.show()

