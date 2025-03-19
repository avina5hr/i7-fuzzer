import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './trained_model.h5'
SEED = 12
np.random.seed(SEED)
tf.random.set_seed(SEED)

def process_rtsp_packet(packet):
    packet_array = np.array([int(byte) for byte in packet])
    if len(packet_array) < MAX_FILE_SIZE:
        packet_array = np.pad(packet_array, (0, MAX_FILE_SIZE - len(packet_array)), 'constant')
    else:
        packet_array = packet_array[:MAX_FILE_SIZE]
    return packet_array / 255.0  # Normalize to range [0, 1]

def load_labels(labels_df, message_name):
    label_row = labels_df[labels_df['Mutated File'] == message_name]
    if label_row.empty:
        print(f"No match found for '{message_name}'.")
        return None
    return float(label_row['Fitness Score'].values[0])  # Assuming fitness score is the probability

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

def build_model(input_size):
    model = models.Sequential([
        layers.Input(shape=(input_size,)),
        layers.Dense(256),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(128),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(64),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(32),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(16),  
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(8),  
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.Dense(1, activation='sigmoid')  # Output layer for probability regression
    ])
    
    optimizer = optimizers.Adam(learning_rate=0.0001)
    model.compile(
        optimizer=optimizer,
        loss='mse',  # Regression loss for probabilities
        metrics=['mae', 'mse']
    )
    model.summary()
    return model


def plot_training_history(history):
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['mae'], label='Training MAE')
    plt.plot(history.history['val_mae'], label='Validation MAE')
    plt.xlabel('Epoch')
    plt.ylabel('Mean Absolute Error')
    plt.title('Training and Validation MAE')
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    print("Preparing data...")
    X, y = load_training_data()
    print("Splitting dataset...")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=SEED)

    print("Building the model...")
    model = build_model(MAX_FILE_SIZE)

    print("Training the model...")
    history = model.fit(
        X_train, y_train, epochs=70, batch_size=64,
        validation_data=(X_val, y_val), shuffle=True
    )

    print(f"Saving the model to {SAVE_MODEL_PATH}...")
    model.save(SAVE_MODEL_PATH)

    print("Plotting training history...")
    plot_training_history(history)

    print("Evaluating the model...")
    y_pred = model.predict(X_val).flatten()

    mae = mean_absolute_error(y_val, y_pred)
    mse = mean_squared_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    print(f"R-squared (R2) Score: {r2}")
    print(f"Mean Absolute Error (MAE): {mae}")
    print(f"Mean Squared Error (MSE): {mse}")

