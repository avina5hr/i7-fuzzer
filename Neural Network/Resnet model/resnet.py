import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt

# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './resnet_model.h5'
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

def residual_block(input_tensor, filters, strides=1):
    """Defines a single residual block with a shortcut connection."""
    shortcut = input_tensor

    # Main path
    x = layers.Conv1D(filters, kernel_size=3, strides=strides, padding='same', activation='relu')(input_tensor)
    x = layers.BatchNormalization()(x)
    x = layers.Conv1D(filters, kernel_size=3, strides=1, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)

    # Shortcut path to match the main path's output shape
    if input_tensor.shape[-1] != filters or strides != 1:  # Adjust dimensions or strides if needed
        shortcut = layers.Conv1D(filters, kernel_size=1, strides=strides, padding='same')(shortcut)
        shortcut = layers.BatchNormalization()(shortcut)

    # Add the shortcut connection
    x = layers.add([x, shortcut])
    x = layers.ReLU()(x)

    return x

def build_resnet_model(input_size):
    """Builds a ResNet model for predicting probabilities as a regression task."""
    inputs = layers.Input(shape=(input_size, 1))  # 1D input (e.g., sequence data)

    # Initial Conv layer
    x = layers.Conv1D(
        64, kernel_size=7, strides=2, padding='same',
        activation='relu', kernel_regularizer=regularizers.l2(1e-4)
    )(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(pool_size=3, strides=2, padding='same')(x)

    # Residual blocks
    x = residual_block(x, 64)
    x = residual_block(x, 128, strides=2)  # Strides for downsampling
    x = residual_block(x, 256, strides=2)
    x = residual_block(x, 512, strides=2)

    # Global Average Pooling
    x = layers.GlobalAveragePooling1D()(x)

    # Dense output layer
    outputs = layers.Dense(1, activation='sigmoid')(x)  # Sigmoid for probabilities

    # Compile the model
    model = models.Model(inputs, outputs)
    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.0001),
        loss='mse',  # Mean Squared Error for regression over probabilities
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
    X = X[..., np.newaxis]  # Add a channel dimension for 1D Conv input
    print("Splitting dataset...")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=SEED)

    print("Building the ResNet model...")
    model = build_resnet_model(MAX_FILE_SIZE)

    print("Training the model...")
    history = model.fit(
        X_train, y_train, epochs=30, batch_size=64,
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

