import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './transformer_model.h5'
SEED = 12
np.random.seed(SEED)
tf.random.set_seed(SEED)

# Data processing functions
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
        return None
    return float(label_row['Fitness Score'].values[0])

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

# Model building
def build_transformer_model(input_size):
    inputs = layers.Input(shape=(input_size, 1))

    x = layers.Conv1D(64, kernel_size=1, strides=1, padding='same')(inputs)
    positional_encoding = tf.expand_dims(tf.range(input_size, dtype=tf.float32), axis=0)
    positional_encoding = tf.tile(positional_encoding, [tf.shape(inputs)[0], 1])
    positional_encoding = layers.Embedding(input_size, 64)(positional_encoding)
    x += positional_encoding

    for _ in range(3):
        attn_output = layers.MultiHeadAttention(num_heads=4, key_dim=64)(x, x)
        attn_output = layers.Dropout(0.1)(attn_output)
        x = layers.LayerNormalization()(x + attn_output)

        ff_output = layers.Conv1D(128, kernel_size=1, activation="relu")(x)
        ff_output = layers.Conv1D(64, kernel_size=1)(ff_output)
        ff_output = layers.Dropout(0.1)(ff_output)
        x = layers.LayerNormalization()(x + ff_output)

    x = layers.GlobalAveragePooling1D()(x)
    outputs = layers.Dense(1, activation='sigmoid')(x)

    model = models.Model(inputs, outputs)
    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.0001),
        loss='mse',
        metrics=['mae', 'mse']
    )
    model.summary()
    return model

# Main training script
def main():
    X, y = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    model = build_transformer_model(MAX_FILE_SIZE)
    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=30,
        batch_size=32,
        verbose=1
    )

    model.save(SAVE_MODEL_PATH)

    y_pred = model.predict(X_test).squeeze()
    print(f"R2 Score: {r2_score(y_test, y_pred)}")
    print(f"MAE: {mean_absolute_error(y_test, y_pred)}")
    print(f"MSE: {mean_squared_error(y_test, y_pred)}")

    plt.figure(figsize=(10, 5))
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()

if __name__ == "__main__":
    main()

