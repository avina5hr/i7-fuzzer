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

---

# 🔍 Proxy & Logs
The proxy acts as an intermediary between the RTSP client and the server. It captures unmutated RTSP messages from the client, forwards them to the server, and logs the communication. The proxy helps in tracking state transitions based on the type of RTSP message and the server’s response code.

## 🔧 Configuration for `proxy.py`

| Parameter      | Explanation |
|--------------|-------------|
| `RTSP_SERVER_IP`  | IP address of the RTSP server. |
| `RTSP_SERVER_PORT`| Port number where the RTSP server listens. |
| `PROXY_IP`        | IP address on which the proxy listens for incoming RTSP requests. |
| `PROXY_PORT`      | Port number on which the proxy listens. |
| `OUTPUT_DIR`      | Directory where proxy logs and captured RTSP messages are stored. |

---

# 🎛️ UI & Configuration

## `rtsp_ui.py`
The user interface script allows control of the RTSP server. It provides options to start, stop, and monitor the server during fuzzing sessions. It helps in configuring the server settings and tracking its status in real time.

## `server_config.json`
A JSON configuration file generated by the UI script is used for fuzzing the server.

# 🛰️ MQTT Fuzzing Configuration

This repository contains scripts for fuzz testing an MQTT server using a neural network-based mutation approach. The fuzzer modifies MQTT messages to discover vulnerabilities and enhance test coverage.

## 📜 Scripts Overview

### 1️⃣ `nn_mutation.py`
This script mutates MQTT messages with the help of a **neural network (NN) model** that predicts mutation probabilities.

#### ⚙️ Configuration Parameters

| Parameter             | Explanation |
|----------------------|-------------|
| `INPUT_DIR`       | Directory containing original MQTT messages for mutation. |
| `MUTATION_DIR`    | Directory where mutated MQTT messages are stored. |
| `FILTERED_OUTPUT_DIR` | Directory for messages that pass NN filtering (based on probability thresholds). |
| `SAVE_MODEL_PATH` | Path to the trained NN model weights used for mutation prediction. |
| `PREDICTIONS_CSV` | CSV file where mutation probabilities are stored. Helps prioritize fuzzing. |
| `THRESHOLD`      | Probability threshold for filtering mutations. Mutations below this threshold are discarded. |

---

### 2️⃣ `proxy.py`
This script acts as an **intermediary** between the MQTT client and the MQTT server. It forwards messages, captures server responses, and allows **mutations** for fuzz testing.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `MQTT_SERVER_IP`     | IP address of the MQTT server. |
| `MQTT_SERVER_PORT`   | Port number of the MQTT server. |
| `MQTT_SERVER_EXECUTABLE` | Path to the Mosquitto MQTT server executable. |
| `UNMUTATED_DIR`      | Directory containing unmutated MQTT messages. |
| `MUTATION_DIR`       | Directory containing mutated MQTT messages. |
| `SANCOV_DIR`         | Directory where `.sancov` coverage files are stored. |
| `SCRIPT_TIMEOUT`     | Time limit for fuzzing execution. |

---

### 3️⃣ `mqtt_fuzzer.py`
This is the **main MQTT fuzzer**, similar to `live555_fuzzer.py`, but modified to send binary MQTT messages to the server.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `MQTT_SERVER_IP`     | IP address of the MQTT server. |
| `MQTT_SERVER_PORT`   | Port number of the MQTT server. |
| `MQTT_SERVER_EXECUTABLE` | Path to the Mosquitto MQTT server executable. |
| `UNMUTATED_DIR`      | Directory containing unmutated MQTT messages. |
| `MUTATION_DIR`       | Directory containing mutated MQTT messages. |
| `SANCOV_DIR`         | Directory where `.sancov` coverage files are stored. |
| `SCRIPT_TIMEOUT`     | Time limit for fuzzing execution. |

---

### 4️⃣ `unmutated.py`
This script sends **unmutated** MQTT messages to the MQTT server to establish a **baseline**. The server’s normal behavior is captured before applying mutations.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `MQTT_SERVER_IP`     | IP address of the MQTT server. |
| `MQTT_SERVER_PORT`   | Port number of the MQTT server. |
| `MQTT_SERVER_EXECUTABLE` | Path to the Mosquitto MQTT server executable. |
| `UNMUTATED_DIR`      | Directory containing unmutated MQTT messages. |
| `SANCOV_DIR`         | Directory where `.sancov` coverage files are stored. |

---

