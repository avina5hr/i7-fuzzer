import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt

# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './advanced_model.h5'
SEED = 12

np.random.seed(SEED)
tf.random.set_seed(SEED)

# Preprocessing functions
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

    # Convert to numpy arrays and shuffle the data
    messages = np.array(messages)
    labels = np.array(labels)
    indices = np.arange(len(messages))
    np.random.shuffle(indices)
    return messages[indices], labels[indices]

# Neural network model
def build_advanced_model(input_size):
    """Builds an advanced CNN-LSTM hybrid model for regression tasks."""
    inputs = layers.Input(shape=(input_size, 1))

    # Convolutional block
    x = layers.Conv1D(64, kernel_size=7, strides=2, padding='same', activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(pool_size=3, strides=2, padding='same')(x)

    # Residual blocks
    for filters in [64, 128, 256]:
        x = layers.Conv1D(filters, kernel_size=3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv1D(filters, kernel_size=3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)

    # LSTM layer
    x = layers.LSTM(128, return_sequences=False)(x)

    # Dense output
    outputs = layers.Dense(1, activation='sigmoid')(x)

    model = models.Model(inputs, outputs)
    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.0001),
        loss='mse',  # Mean Squared Error for regression
        metrics=['mae']  # Only include MAE as an additional metric
    )
    model.summary()
    return model

# Main script
if __name__ == "__main__":
    print("Loading data...")
    messages, labels = load_training_data()

    print("Splitting dataset...")
    X_train, X_test, y_train, y_test = train_test_split(messages, labels, test_size=0.2, random_state=SEED)

    print("Building the model...")
    model = build_advanced_model(MAX_FILE_SIZE)

    print("Training the model...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=30,
        batch_size=32,
        verbose=1
    )

    print(f"Saving the model to {SAVE_MODEL_PATH}...")
    model.save(SAVE_MODEL_PATH)

    print("Evaluating the model...")
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae_val = mean_absolute_error(y_test, y_pred)
    mse_val = mean_squared_error(y_test, y_pred)
    print(f"R2 Score: {r2}")
    print(f"MAE: {mae_val}")
    print(f"MSE: {mse_val}")

    # Plotting training history with separate graphs side by side
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))

    # Loss subplot (loss is mse)
    axs[0].plot(history.history['loss'], label='Training Loss (MSE)')
    axs[0].plot(history.history['val_loss'], label='Validation Loss (MSE)')
    axs[0].set_title('Loss (MSE) Over Epochs')
    axs[0].set_xlabel('Epochs')
    axs[0].set_ylabel('Loss (MSE)')
    axs[0].legend()

    # MAE subplot
    axs[1].plot(history.history['mae'], label='Training MAE')
    axs[1].plot(history.history['val_mae'], label='Validation MAE')
    axs[1].set_title('MAE Over Epochs')
    axs[1].set_xlabel('Epochs')
    axs[1].set_ylabel('MAE')
    axs[1].legend()

    plt.tight_layout()
    plt.show()

