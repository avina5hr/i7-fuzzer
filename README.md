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
- The script monitors the server’s response and logs it.
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

This repository contains scripts for generating and filtering **mutated RTSP messages** for fuzz testing. The mutation process includes **insertion** and **replacement** techniques, affecting **1 to 5 bits** in each message. LSTM-based neural network predicts the **code coverage probability** of each mutated message, allowing for intelligent filtering.

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
- Messages with low-probability than threshold are discarded.

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

## 🎯 State Selection Strategies
The script supports three state selection strategies to control which RTSP message sequence to mutate and send to the server:

### 1. 🎲 Weighted State Selection (selection = "1")
- The probability of selecting a state is based on the number of transitions from that state.
- States with more transitions are more likely to be selected.

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
## 📂 FTP Fuzzing Configuration

### 1️⃣ `nn_mutation_ftp.py`
The `nn_mutation_ftp.py` script is responsible for mutating and filtering FTP messages using a neural network (NN)-based approach.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `INPUT_DIR`          | Directory containing original FTP messages. |
| `MUTATION_DIR`       | Directory where mutated FTP messages will be saved. |
| `FILTERED_OUTPUT_DIR` | Directory where FTP messages that pass NN filtering are saved. |
| `SAVE_MODEL_PATH`     | Path to the trained NN model's weights. |
| `PREDICTIONS_CSV`    | CSV file path where mutation probabilities are stored. |
| `THRESHOLD`          | Probability threshold for filtering FTP mutations. |
| `MAX_POSITIONS_TO_MUTATE` | Maximum number of positions in an FTP message to mutate. |

---

### 2️⃣ `fuzzer_ftp.py`
The `fuzzer_ftp.py` script automates fuzzing of an FTP server by sending both mutated and unmutated FTP messages. This script is similar to `live555_fuzzer.py` but adapted for the FTP protocol.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `OUTPUT_DIR`         | Directory containing unmutated FTP messages and state transition data. |
| `FTP_SERVER_IP`      | IP address of the FTP server being fuzzed. |
| `FTP_SERVER_PORT`    | Port number of the FTP server. |
| `SERVER_EXECUTABLE`  | Path to the FTP server executable under test. |
| `CONFIG_FILE`        | Path to the FTP server configuration file. |
| `SANCOV_DIR`        | Directory where `.sancov` coverage files are dumped. |
| `MUTATION_DIR`      | Directory containing mutated FTP messages. |# i7-Fuzzer

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
- The script monitors the server’s response and logs it.
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

This repository contains scripts for generating and filtering **mutated RTSP messages** for fuzz testing. The mutation process includes **insertion** and **replacement** techniques, affecting **1 to 5 bits** in each message. LSTM-based neural network predicts the **code coverage probability** of each mutated message, allowing for intelligent filtering.

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
- Messages with low-probability than threshold are discarded.

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

## 🎯 State Selection Strategies
The script supports three state selection strategies to control which RTSP message sequence to mutate and send to the server:

### 1. 🎲 Weighted State Selection (selection = "1")
- The probability of selecting a state is based on the number of transitions from that state.
- States with more transitions are more likely to be selected.

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
## 📂 FTP Fuzzing Configuration

### 1️⃣ `nn_mutation_ftp.py`
The `nn_mutation_ftp.py` script is responsible for mutating and filtering FTP messages using a neural network (NN)-based approach.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `INPUT_DIR`          | Directory containing original FTP messages. |
| `MUTATION_DIR`       | Directory where mutated FTP messages will be saved. |
| `FILTERED_OUTPUT_DIR` | Directory where FTP messages that pass NN filtering are saved. |
| `SAVE_MODEL_PATH`     | Path to the trained NN model's weights. |
| `PREDICTIONS_CSV`    | CSV file path where mutation probabilities are stored. |
| `THRESHOLD`          | Probability threshold for filtering FTP mutations. |
| `MAX_POSITIONS_TO_MUTATE` | Maximum number of positions in an FTP message to mutate. |

---

### 2️⃣ `fuzzer_ftp.py`
The `fuzzer_ftp.py` script automates fuzzing of an FTP server by sending both mutated and unmutated FTP messages. This script is similar to `live555_fuzzer.py` but adapted for the FTP protocol.

#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `OUTPUT_DIR`         | Directory containing unmutated FTP messages and state transition data. |
| `FTP_SERVER_IP`      | IP address of the FTP server being fuzzed. |
| `FTP_SERVER_PORT`    | Port number of the FTP server. |
| `SERVER_EXECUTABLE`  | Path to the FTP server executable under test. |
| `CONFIG_FILE`        | Path to the FTP server configuration file. |
| `SANCOV_DIR`        | Directory where `.sancov` coverage files are dumped. |
| `MUTATION_DIR`      | Directory containing mutated FTP messages. |
# 🛰️ MQTT Fuzzing Configuration

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
This script acts as an **intermediary** between the MQTT client and the MQTT server. It forwards messages, captures server responses.

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
This script sends **unmutated** MQTT messages to the MQTT server to establish a **baseline**. 
#### ⚙️ Configuration Parameters

| Parameter              | Explanation |
|----------------------|-------------|
| `MQTT_SERVER_IP`     | IP address of the MQTT server. |
| `MQTT_SERVER_PORT`   | Port number of the MQTT server. |
| `MQTT_SERVER_EXECUTABLE` | Path to the Mosquitto MQTT server executable. |
| `UNMUTATED_DIR`      | Directory containing unmutated MQTT messages. |
| `SANCOV_DIR`         | Directory where `.sancov` coverage files are stored. |

---

# 📡 Live555 Setup and Compilation Using Clang

This document provides step-by-step instructions to download, build, and run the Live555 RTSP server. 🎥

## 📥 Downloading Live555
There are two primary methods to obtain the Live555 source code.

### 🗂️ Method 1: Download Tarball
Download the latest version of Live555 using `wget`:
```bash
wget http://www.live555.com/liveMedia/public/live555-latest.tar.gz
```
💡 **Explanation:** This command downloads a compressed tarball containing the latest Live555 source code.

### 🖥️ Method 2: Clone from GitHub
Alternatively, clone the repository from GitHub:
```bash
git clone https://github.com/rgaufman/live555.git live555
```
💡 **Explanation:** This command clones the Live555 repository into a folder named `live555`.

## 📦 Extracting the Tarball
If you downloaded the tarball, extract it using the following command:
```bash
tar -xzf live555-latest.tar.gz
```
💡 **Explanation:** The `-xzf` options extract the contents of the compressed tarball, creating the source directory.

## 🔧 Building Live555
Follow these steps to build Live555 on a Linux environment:

### 📂 Navigate to the Source Directory
Change to the directory that contains the Live555 source code:
```bash
cd <directory>
```
💡 **Explanation:** This navigates to the extracted source folder.

### ⚙️ Generate Makefiles
Generate the Makefiles for a Linux environment:
```bash
./genMakefiles linux
```
💡 **Explanation:** This script configures the build system by generating the necessary Makefiles tailored for Linux.

### 🔨 Compile the Code
Compile the Live555 libraries and tools:
```bash
make
```
💡 **Explanation:** This command builds the project based on the generated Makefiles.

## 🚀 Running the RTSP Server
Once the build completes, the next step is to run the RTSP server.

### 📂 Navigate to the Media Server Directory
Change to the directory that contains the RTSP server executable:
```bash
cd mediaServer
```
💡 **Explanation:** This command navigates to the folder where the RTSP server executable is located.

### ▶️ Start the RTSP Server
Start the server by executing the following command:
```bash
./live555MediaServer
```
💡 **Explanation:** This command starts the Live555 RTSP server, which listens for incoming RTSP requests and streams media files accordingly.

## 🎬 Testing the RTSP Server

### 🎥 Using VLC Media Player
Open VLC Media Player and select **Media** → **Open Network Stream**. Then enter:
```bash
rtsp://<server-ip>:<server_port>/<media-file>
```
💡 **Explanation:** Replace `<server-ip>`, `<server_port>`, and `<media-file>` with your server's IP address, the port number, and the name of the media file to stream.

### 🖥️ Using the Live555 Sample Client
Live555 also provides a sample client for testing:
```bash
cd ~/live555/testProgs
./testRTSPClient rtsp://<server-ip>:<server_port>/<media-file>
```
💡 **Explanation:** This command navigates to the test programs directory and runs the sample RTSP client.

---

# 🔥 LightFTP Setup and Compilation Using Clang
This guide provides step-by-step instructions to set up and run the LightFTP server on a Linux system.  🖧

## 📦 Installing Dependencies
First, install the GNU TLS development library required by LightFTP:
```bash
sudo apt-get install -y libgnutls-dev
```
💡 **Explanation:** This command installs the `libgnutls-dev` package necessary for secure communications.

## 📥 Cloning the Repository
Clone the LightFTP repository from GitHub:
```bash
git clone https://github.com/hfiref0x/LightFTP.git
```
💡 **Explanation:** This command downloads the source code from the official repository.

## 📌 Checking Out a Specific Version
Navigate into the cloned repository and checkout a specific commit:
```bash
cd LightFTP
git checkout 5980ea1
```
💡 **Explanation:** Checking out commit `5980ea1` ensures you are using a stable version of LightFTP as per your requirement.

## 🔨 Building the Source Code
Move into the source directory and compile the code using Clang:
```bash
cd Source/Release
CC=clang make clean all
```
💡 **Explanation:** The `make clean all` command cleans any previous builds and compiles the source code with Clang.

## ⚙️ Running LightFTP
Return to the release directory and start the LightFTP server on port 2200:
```bash
cd $WORKDIR/LightFTP/Source/Release
./fftp fftp.conf 2200
```
💡 **Explanation:** This command launches LightFTP with the specified configuration file and listens for connections on port 2200.

## 🔗 Connecting to the Server
Open a new terminal and use Telnet to connect to the running LightFTP server:
```bash
telnet 127.0.0.1 2200
```
💡 **Explanation:** After connecting, you can use standard FTP commands (e.g., `USER`, `PASS`) to log in and interact with the server. The default username and password are both `ubuntu`.

---

# 📡 Mosquitto Setup and Compilation Using Clang
This document provides step-by-step instructions to install dependencies, clone, and build Mosquitto. 🐝

## 📦 Installing Dependencies
Install the required development libraries:
```bash
apt-get install libssl-dev libwebsockets-dev uuid-dev docbook-xsl docbook xsltproc
```

## 📥 Cloning the Mosquitto Repository
Change to your working directory and clone the repository:
```bash
cd $WORKDIR
git clone https://github.com/eclipse/mosquitto.git
```
💡 **Explanation:** This downloads the Mosquitto source code from the official GitHub repository.

## 📌 Checking Out a Specific Commit
Navigate to the cloned repository and check out a known stable commit:
```bash
cd mosquitto
git checkout 2665705
```
💡 **Explanation:** Using the commit hash `2665705` ensures you build a specific, tested version of Mosquitto.

## 🛠️ Preparing the Build Environment
Enable Address Sanitizer by exporting the environment variable:
```bash
export AFL_USE_ASAN=1
```
💡 **Explanation:** This variable signals the build system to utilize ASAN, which helps detect memory-related errors.

## 🔨 Compiling Mosquitto Using Clang
Set the compiler and flags to use Clang with Address Sanitizer:
```bash
CXXFLAGS="-g -O0 -fsanitize=address -fsanitize-coverage=edge,trace-pc-guard -fno-omit-frame-pointer" \
LDFLAGS="-g -O0 -fsanitize=address -fsanitize-coverage=edge,trace-pc-guard -fno-omit-frame-pointer" \
CXX=clang++ \
make clean all WITH_TLS=no WITH_TLS_PSK=no WITH_STATIC_LIBRARIES=yes WITH_DOCS=no WITH_CJSON=no WITH_EPOLL=no
```
💡 **Explanation:** This ensures Mosquitto is built with security features and debugging enabled.


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

# 📡 Live555 Setup and Compilation Using Clang

This document provides step-by-step instructions to download, build, and run the Live555 RTSP server. 🎥

## 📥 Downloading Live555
There are two primary methods to obtain the Live555 source code.

### 🗂️ Method 1: Download Tarball
Download the latest version of Live555 using `wget`:
```bash
wget http://www.live555.com/liveMedia/public/live555-latest.tar.gz
```
💡 **Explanation:** This command downloads a compressed tarball containing the latest Live555 source code.

### 🖥️ Method 2: Clone from GitHub
Alternatively, clone the repository from GitHub:
```bash
git clone https://github.com/rgaufman/live555.git live555
```
💡 **Explanation:** This command clones the Live555 repository into a folder named `live555`.

## 📦 Extracting the Tarball
If you downloaded the tarball, extract it using the following command:
```bash
tar -xzf live555-latest.tar.gz
```
💡 **Explanation:** The `-xzf` options extract the contents of the compressed tarball, creating the source directory.

## 🔧 Building Live555
Follow these steps to build Live555 on a Linux environment:

### 📂 Navigate to the Source Directory
Change to the directory that contains the Live555 source code:
```bash
cd <directory>
```
💡 **Explanation:** This navigates to the extracted source folder.

### ⚙️ Generate Makefiles
Generate the Makefiles for a Linux environment:
```bash
./genMakefiles linux
```
💡 **Explanation:** This script configures the build system by generating the necessary Makefiles tailored for Linux.

### 🔨 Compile the Code
Compile the Live555 libraries and tools:
```bash
make
```
💡 **Explanation:** This command builds the project based on the generated Makefiles.

## 🚀 Running the RTSP Server
Once the build completes, the next step is to run the RTSP server.

### 📂 Navigate to the Media Server Directory
Change to the directory that contains the RTSP server executable:
```bash
cd mediaServer
```
💡 **Explanation:** This command navigates to the folder where the RTSP server executable is located.

### ▶️ Start the RTSP Server
Start the server by executing the following command:
```bash
./live555MediaServer
```
💡 **Explanation:** This command starts the Live555 RTSP server, which listens for incoming RTSP requests and streams media files accordingly.

## 🎬 Testing the RTSP Server

### 🎥 Using VLC Media Player
Open VLC Media Player and select **Media** → **Open Network Stream**. Then enter:
```bash
rtsp://<server-ip>:<server_port>/<media-file>
```
💡 **Explanation:** Replace `<server-ip>`, `<server_port>`, and `<media-file>` with your server's IP address, the port number, and the name of the media file to stream.

### 🖥️ Using the Live555 Sample Client
Live555 also provides a sample client for testing:
```bash
cd ~/live555/testProgs
./testRTSPClient rtsp://<server-ip>:<server_port>/<media-file>
```
💡 **Explanation:** This command navigates to the test programs directory and runs the sample RTSP client.

---

# 🔥 LightFTP Setup and Compilation Using Clang
This guide provides step-by-step instructions to set up and run the LightFTP server on a Linux system.  🖧

## 📦 Installing Dependencies
First, install the GNU TLS development library required by LightFTP:
```bash
sudo apt-get install -y libgnutls-dev
```
💡 **Explanation:** This command installs the `libgnutls-dev` package necessary for secure communications.

## 📥 Cloning the Repository
Clone the LightFTP repository from GitHub:
```bash
git clone https://github.com/hfiref0x/LightFTP.git
```
💡 **Explanation:** This command downloads the source code from the official repository.

## 📌 Checking Out a Specific Version
Navigate into the cloned repository and checkout a specific commit:
```bash
cd LightFTP
git checkout 5980ea1
```
💡 **Explanation:** Checking out commit `5980ea1` ensures you are using a stable version of LightFTP as per your requirement.

## 🔨 Building the Source Code
Move into the source directory and compile the code using Clang:
```bash
cd Source/Release
CC=clang make clean all
```
💡 **Explanation:** The `make clean all` command cleans any previous builds and compiles the source code with Clang.

## ⚙️ Running LightFTP
Return to the release directory and start the LightFTP server on port 2200:
```bash
cd $WORKDIR/LightFTP/Source/Release
./fftp fftp.conf 2200
```
💡 **Explanation:** This command launches LightFTP with the specified configuration file and listens for connections on port 2200.

## 🔗 Connecting to the Server
Open a new terminal and use Telnet to connect to the running LightFTP server:
```bash
telnet 127.0.0.1 2200
```
💡 **Explanation:** After connecting, you can use standard FTP commands (e.g., `USER`, `PASS`) to log in and interact with the server.
---

# 📡 Mosquitto Setup and Compilation Using Clang
This document provides step-by-step instructions to install dependencies, clone, and build Mosquitto. 🐝

## 📦 Installing Dependencies
Install the required development libraries:
```bash
apt-get install libssl-dev libwebsockets-dev uuid-dev docbook-xsl docbook xsltproc
```

## 📥 Cloning the Mosquitto Repository
Change to your working directory and clone the repository:
```bash
git clone https://github.com/eclipse/mosquitto.git
```
💡 **Explanation:** This downloads the Mosquitto source code from the official GitHub repository.

## 📌 Checking Out a Specific Commit
Navigate to the cloned repository and check out a known stable commit:
```bash
cd mosquitto
git checkout 2665705
```
💡 **Explanation:** Using the commit hash `2665705` ensures you build a specific, tested version of Mosquitto.

## 🛠️ Preparing the Build Environment
Enable Address Sanitizer by exporting the environment variable:
```bash
export AFL_USE_ASAN=1
```

## 🔨 Compiling Mosquitto Using Clang
Set the compiler and flags to use Clang with Address Sanitizer:
```bash
CXXFLAGS="-g -O0 -fsanitize=address -fsanitize-coverage=edge,trace-pc-guard -fno-omit-frame-pointer" \
LDFLAGS="-g -O0 -fsanitize=address -fsanitize-coverage=edge,trace-pc-guard -fno-omit-frame-pointer" \
CXX=clang++ \
make clean all WITH_TLS=no WITH_TLS_PSK=no WITH_STATIC_LIBRARIES=yes WITH_DOCS=no WITH_CJSON=no WITH_EPOLL=no
```

