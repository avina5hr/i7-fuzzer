<h1 align="center">🚀 i7-Fuzzer 🚀</h1>
The live555_fuzzer.py script is the main fuzzing tool used to test the Live555 RTSP server. 
It works by sending both unmutated and mutated RTSP messages to the server, monitoring its responses, and analyzing code coverage to detect potential vulnerabilities.


📌 Sending Messages to the Server
The script first sends an unmutated RTSP message.
Then, it sends a mutated RTSP message to test the server.
After sending a mutated message, the script waits for a response from the server.


📌 Code Coverage Collection
After the mutated message is processed, the script resends the unmutated message to compare the responses.
The code coverage data is then dumped into the specified directory.

📌Crash Detection
The script monitors the server’s response to detect any abnormal behavior or crashes.
If a crash occurs, the fuzzer logs the failure for further analysis.

⚙️ Configuration Before Running the Fuzzer
Before running live555_fuzzer.py, the user must configure a few parameters related to the server, message storage, and coverage output are shown in tabel 1. 
These parameters ensure that the fuzzer runs correctly and collects the necessary data.

| Parameter                                     | Explanation                                                                 |
|-----------------------------------------------|-----------------------------------------------------------------------------|
| `OUTPUT_DIR`                                  | Directory containing unmutated messages and the state transition JSON file. |
| `RTSP_SERVER_IP`                              | IP address of the RTSP server being fuzzed.                                 |
| `RTSP_SERVER_PORT`                            | Port number of the RTSP server.                                             |
| `SERVER_EXECUTABLE`                           | Path to the RTSP server executable under test.                              |
| `SANCOV_DIR`                                  | Directory where `.sancov` coverage files are dumped.                        |
| `MUTATION_DIR`                                | Directory containing mutated RTSP message files.                            |
| `SANITIZER_LOG`                               | Log file name for sanitizer output.                                         |
| `SCRIPT_TIMEOUT`                              | Time limit for fuzzing execution.                                           |

Table 1: Configuration Parameters for `live555_fuzzer.py`.
