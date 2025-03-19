import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import r2_score

# Constants
DATA_DIR = '/home/rajendra2024/mutation_py_code/filtered_rtsp_message/'
LABELS_FILE = '/home/rajendra2024/mutation_py_code/scaled_output.csv'
MAX_FILE_SIZE = 200
SAVE_MODEL_PATH = './trained_ffn_model_with_bn.h5'
SEED = 12
np.random.seed(SEED)
tf.random.set_seed(SEED)

def process_rtsp_packet(packet):
    packet_array = np.array([int(byte) for byte in packet])
    if len(packet_array) < MAX_FILE_SIZE:
        packet_array = np.pad(packet_array, (0, MAX_FILE_SIZE - len(packet_array)), 'constant')
    else:
        packet_array = packet_array[:MAX_FILE_SIZE]
    return packet_array / 255.0

def load_labels(labels_df, message_name):
    label_row = labels_df[labels_df['Mutated File'] == message_name]
    if label_row.empty:
        print(f"No exact match found for message name '{message_name}'.")
        return None

    prob = float(label_row['Fitness Score'].values[0])
    try:
        start_index = message_name.index("_pos_") + len("_pos_")
        end_index = message_name.index("_mutation")
        position_range = message_name[start_index:end_index]
        positions = [int(pos) for pos in position_range.split('_')]
    except ValueError:
        print(f"Error parsing positions in '{message_name}'.")
        return None

    if not positions:
        print(f"No valid positions found for '{message_name}'.")
        return None

    labels = np.zeros(MAX_FILE_SIZE)
    equal_prob = prob / len(positions)
    for position in positions:
        if 0 <= position < MAX_FILE_SIZE:
            labels[position] = equal_prob
        else:
            print(f"Warning: Position {position} is out of bounds for MAX_FILE_SIZE.")

    return labels

def load_training_data():
    messages = []
    labels = []
    try:
        labels_df = pd.read_csv(LABELS_FILE)
    except FileNotFoundError:
        raise FileNotFoundError(f"Labels file not found at {LABELS_FILE}. Please provide the correct path.")

    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith('.raw'):
            file_path = os.path.join(DATA_DIR, file_name)
            try:
                with open(file_path, 'rb') as f:
                    rtsp_message = f.read()


                if len(rtsp_message) == 0:
                    print(f"Warning: {file_path} is empty, skipping.")
                    continue

                processed_message = process_rtsp_packet(rtsp_message)
                message_name = os.path.splitext(file_name)[0] + ".sancov"

                label = load_labels(labels_df, message_name)
                if label is not None:
                    messages.append(processed_message)
                    labels.append(label)
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}, skipping.")

    if len(messages) == 0:
        raise ValueError("No valid RTSP messages were loaded.")
    return np.array(messages), np.array(labels)

# Modified model with Batch Normalization
def build_ffn_model_with_bn(input_size):
    model = models.Sequential([
        layers.Input(shape=(input_size,)),
        layers.Dense(200, activation='relu', kernel_regularizer=regularizers.l2(0.01)),
        layers.BatchNormalization(),
        
        
        layers.Dense(200, activation='relu', kernel_regularizer=regularizers.l2(0.01)),
        layers.BatchNormalization(),
       
        
        layers.Dense(200, activation='relu', kernel_regularizer=regularizers.l2(0.01)),
        layers.BatchNormalization(),
        
        layers.Dense(input_size, activation='sigmoid')  # Output layer for probabilities
    ])

    optimizer = optimizers.Adam(learning_rate=0.0001)
    model.compile(
        optimizer=optimizer,
        loss=weighted_mae_loss,
        metrics=[tf.keras.metrics.MeanAbsoluteError()]
    )
    model.summary()
    return model

def weighted_mae_loss(y_true, y_pred):
    weights = tf.where(tf.equal(y_true, 0), 0.1, 10.0)  # Adjust weight for mutated bits
    mae = tf.abs(y_true - y_pred)
    weighted_mae = tf.reduce_sum(mae * weights) / tf.reduce_sum(weights)
    return weighted_mae

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
    plt.plot(history.history['mean_absolute_error'], label='Training MAE')
    plt.plot(history.history['val_mean_absolute_error'], label='Validation MAE')
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

    print("Building the FFN model with Batch Normalization...")
    model = build_ffn_model_with_bn(MAX_FILE_SIZE)
    
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)

    print("Training the FFN model...")
    history = model.fit(X_train, y_train, epochs=20, batch_size=64, validation_data=(X_val, y_val), shuffle=True)

    print(f"Saving the model to {SAVE_MODEL_PATH}...")
    model.save(SAVE_MODEL_PATH)

    print("Plotting training history...")
    plot_training_history(history)

    print("Evaluating the model...")
    y_pred = model.predict(X_val)

    mae = mean_absolute_error(y_val, y_pred)
    mse = mean_squared_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)

    print(f"Mean Absolute Error (MAE): {mae}")
    print(f"Mean Squared Error (MSE): {mse}")
    print(f"R-squared (R2) Score: {r2}")

