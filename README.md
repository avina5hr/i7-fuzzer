# i7-Fuzzer

## LIVE555 Code Fuzzing
The `live555_fuzzer.py` script is the main fuzzing tool used to test the Live555 RTSP server. It works by sending both unmutated and mutated RTSP messages to the server, monitoring its responses, and analyzing code coverage to detect potential vulnerabilities.

## 🎯 Sending Messages to the Server
- The script first sends an **unmutated RTSP message**.
- Then, it sends a **mutated RTSP message** to test the server.
- After sending a mutated message, the script waits for a response from the server.

## 📊 Code Coverage Collection
- After processing the mutated message, the script resends the unmutated message to compare responses.
- The **code coverage data** is then dumped into the specified directory.

## 💥 Crash Detection
- The script monitors the server’s response to detect any **abnormal behavior or crashes**.
- If a crash occurs, the fuzzer logs the failure for further analysis.

## ⚙️ Configuration Before Running the Fuzzer
Before running `live555_fuzzer.py`, the user must configure key parameters related to the **server, message storage, and coverage output** as shown in Table 1. These parameters ensure that the fuzzer runs correctly and collects the necessary data.

### Configuration Parameters for `live555_fuzzer.py`

| Parameter               | Explanation |
|-------------------------|-------------|
| `OUTPUT_DIR`           | Directory containing unmutated messages and the state transition JSON file. |
| `RTSP_SERVER_IP`       | IP address of the RTSP server being fuzzed. |
| `RTSP_SERVER_PORT`     | Port number of the RTSP server. |
| `SERVER_EXECUTABLE`    | Path to the RTSP server executable under test. |
| `SANCOV_DIR`          | Directory where `.sancov` coverage files are dumped. |
| `MUTATION_DIR`        | Directory containing mutated RTSP message files. |
| `SANITIZER_LOG`       | Log file name for sanitizer output. |
| `SCRIPT_TIMEOUT`      | Time limit for fuzzing execution. |

---

# 🛠️ Mutation & Filtering

This repository contains scripts for generating and filtering **mutated RTSP messages** for fuzz testing. The mutation process includes **insertion** and **replacement** techniques, affecting **1 to 5 bits** in each message. Additionally, an LSTM-based neural network predicts the **code coverage probability** of each mutated message, allowing for intelligent filtering.

## 📜 Scripts Overview

### 1. `mutation.py`
- Generates **mutated RTSP messages** by applying:
  - **Insertion**: Randomly adding new bits within the message.
  - **Replacement**: Replacing existing bits with new values.
- Each mutation affects **1 to 5 bits** per message.
- Saves all mutated messages in a designated directory for further processing.

### 2. `nn_mutation.py`
- Uses a **trained LSTM neural network** to evaluate mutated messages.
- Predicts the **code coverage probability** of each mutation.
- Messages with high probability values are retained, while low-probability ones are discarded.

---

## 🔧 `nn_mutation.py` Configuration

### Parameters

| Parameter               | Explanation |
|-------------------------|-------------|
| `INPUT_DIR`            | Directory containing original (unmutated) RTSP messages. |
| `MUTATION_DIR`         | Directory where mutated messages (1-5 bit changes) are stored. |
| `FILTERED_OUTPUT_DIR`  | Directory where NN-filtered mutated messages are saved. |
| `SAVE_MODEL_PATH`      | Path to the trained LSTM model used for prediction. |
| `PREDICTIONS_CSV`      | Path to a CSV file storing predicted **code coverage probabilities** for each mutation. |
| `THRESHOLD`            | Probability threshold for filtering mutations based on coverage impact. |

---

## ⚡ How It Works
1. **Mutation Process**: `mutation.py` generates RTSP mutations with small bit-level modifications.
2. **Prediction**: `nn_mutation.py` loads the LSTM model to predict the probability of improved **code coverage**.
3. **Filtering**: Only mutations exceeding the probability threshold are saved.

This approach ensures efficient mutation generation while prioritizing **mutations with a higher chance of increasing code coverage**, making fuzz testing more effective.

---

# 🏹 `state_selection_fuzzer.py`
The `state_selection_fuzzer.py` script is responsible for implementing state-aware fuzzing strategies. It selects specific RTSP message sequences based on state transitions and previous responses to maximize code coverage and vulnerability discovery.

## 🚀 State-Aware Fuzzing
- Reads unmutated RTSP messages and state transition data from `OUTPUT_DIR`.
- Selects a message and applies a mutation based on a defined strategy (e.g., probability-based, state-based).
- Sends the mutated message to the RTSP server.
- Monitors server responses for crashes and unexpected behavior.
- Uses code coverage feedback to refine future state selections.

## 🎯 State Selection Strategies
The script supports three state selection strategies to control which RTSP message sequence to mutate and send to the server:

### 1. 🎲 Weighted State Selection (selection = "1")
- The probability of selecting a state is based on the number of transitions from that state.
- States with more transitions are more likely to be selected, encouraging exploration of complex state paths.

### 2. 🔄 Round-Robin State Selection (selection = "2")
- The script selects states in a cyclic (round-robin) order.
- This ensures that every state is tested uniformly over time.

### 3. 🎲 Uniform Random State Selection (selection = "3")
- The script selects a state randomly with equal probability.

## 🛠️ Configuration Before Running `state_selection_fuzzer.py`
Before running `state_selection_fuzzer.py`, configure the following parameters:

| Parameter               | Explanation |
|-------------------------|-------------|
| `OUTPUT_DIR`           | Directory containing unmutated messages and state transitions. |
| `RTSP_SERVER_IP`       | IP address of the RTSP server being fuzzed. |
| `RTSP_SERVER_PORT`     | Port number of the RTSP server. |
| `SERVER_EXECUTABLE`    | Path to the RTSP server executable under test. |
| `SANCOV_DIR`          | Directory where LLVM `.sancov` files are stored. |
| `MUTATION_DIR`        | Directory containing mutated RTSP messages. |
| `SANITIZER_LOG`       | Log file where sanitizer output (e.g., crashes, memory errors) is recorded. |
| `SCRIPT_TIMEOUT`      | Time limit for each fuzzing run. |

collects the necessary data.

### Configuration Parameters for `live555_fuzzer.py`

| Parameter               | Explanation |
|-------------------------|-------------|
| `OUTPUT_DIR`           | Directory containing unmutated messages and the state transition JSON file. |
| `RTSP_SERVER_IP`       | IP address of the RTSP server being fuzzed. |
| `RTSP_SERVER_PORT`     | Port number of the RTSP server. |
| `SERVER_EXECUTABLE`    | Path to the RTSP server executable under test. |
| `SANCOV_DIR`          | Directory where `.sancov` coverage files are dumped. |
| `MUTATION_DIR`        | Directory containing mutated RTSP message files. |
| `SANITIZER_LOG`       | Log file name for sanitizer output. |
| `SCRIPT_TIMEOUT`      | Time limit for fuzzing execution. |

---

# Mutation & Filtering

This repository contains scripts for generating and filtering **mutated RTSP messages** for fuzz testing. The mutation process includes **insertion** and **replacement** techniques, affecting **1 to 5 bits** in each message. Additionally, an LSTM-based neural network predicts the **code coverage probability** of each mutated message, allowing for intelligent filtering.

## Scripts Overview

### 1. `mutation.py`
- Generates **mutated RTSP messages** by applying:
  - **Insertion**: Randomly adding new bits within the message.
  - **Replacement**: Replacing existing bits with new values.
- Each mutation affects **1 to 5 bits** per message.
- Saves all mutated messages in a designated directory for further processing.

### 2. `nn_mutation.py`
- Uses a **trained LSTM neural network** to evaluate mutated messages.
- Predicts the **code coverage probability** of each mutation.
- Messages with high probability values are retained, while low-probability ones are discarded.

---

## `nn_mutation.py` Configuration

### Parameters

| Parameter               | Explanation |
|-------------------------|-------------|
| `INPUT_DIR`            | Directory containing original (unmutated) RTSP messages. |
| `MUTATION_DIR`         | Directory where mutated messages (1-5 bit changes) are stored. |
| `FILTERED_OUTPUT_DIR`  | Directory where NN-filtered mutated messages are saved. |
| `SAVE_MODEL_PATH`      | Path to the trained LSTM model used for prediction. |
| `PREDICTIONS_CSV`      | Path to a CSV file storing predicted **code coverage probabilities** for each mutation. |
| `THRESHOLD`            | Probability threshold for filtering mutations based on coverage impact. |

---

## How It Works
1. **Mutation Process**: `mutation.py` generates RTSP mutations with small bit-level modifications.
2. **Prediction**: `nn_mutation.py` loads the LSTM model to predict the probability of improved **code coverage**.
3. **Filtering**: Only mutations exceeding the probability threshold are saved.

This approach ensures efficient mutation generation while prioritizing **mutations with a higher chance of increasing code coverage**, making fuzz testing more effective.

