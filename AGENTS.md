# SABRE Sender

## Agent Tasks

1. Support learning of concepts - Focus on explaining concepts, theories, or background knowledge without giving direct solutions.
2. Collaborate in thinking, reasoning and design. Brainstorm, evaluate, or suggest ideas and options.

IMPORTANT: Do not provide a fully formed solution.

## Project Details

Implement a new protocol called SABRE (Simple And Basic Reliable Exchange) that provides reliable data transfer over UDP. You will implement the sender side of the SABRE protocol, and the instructor will host the receiver side for you to test against.

```{mermaid}
packet
title SABRE Packet (64-bit Condensed Header)
+8: "PACKET TYPE"
+4: "FLAGS (RST/FIN/SYN/ACK)"
+12: "SEQUENCE NUMBER"
+12: "ACKNOWLEDGEMENT"
+12: "LENGTH"
+16: "CADET ID"
```

- Establish a connection with the receiver using a 3-way handshake with the SYN flag.
- Use a sliding window mechanism to manage the flow of packets.
- Implement a single timer for the base of the window to detect timeouts.
- Implement cumulative acknowledgements to acknowledge all packets up to a certain sequence number.
- Implement bulk retransmissions of all unacknowledged packets when a timeout occurs.
- Handle connection teardown using a FIN sequence.
- Read the payload in the final FIN packet from the server.

### Learning Objectives

- Explain why UDP is unreliable and describe strategies to achieve reliable data transfer over UDP.
- Design and implement a custom transport header with TCP-like flags and fields.
- Implement 3-way handshake over UDP and a graceful connection teardown.
- Implement sliding window protocols such as Go-Back-N.
    - Use a single base timer, cumulative ACKs, and bulk retransmissions.
- Analyze and understand protocol behavior using Wireshark.
- Reflect on trade-offs between protocol complexity and performance.

### Key Tasks

- Establish a connection with the receiver using a 3-way handshake with the SYN flag.
- Use a sliding window mechanism to manage the flow of packets.
- Implement a single timer for the base of the window to detect timeouts.
- Implement cumulative acknowledgements to acknowledge all packets up to a certain sequence number.
- Implement bulk retransmissions of all unacknowledged packets when a timeout occurs.
- Handle connection teardown using a FIN sequence.
- Read the payload in the final FIN packet from the server.

### Project Files

- `main.py`: Main entry point for your sender. You will run this to start your sender and connect to the server.
- `sender.py`: This is where you will implement the SABRE protocol.
- `packet.py`: This file contains the `Packet` class that defines the structure of a SABRE packet and provides methods for serialization and deserialization.
- `simpletimer.py`: This file contains a simple timer class that you can use for implementing timeouts in your Go-Back-N protocol.
- `corpus.py`: This file downloads the sample text files that you will send to the server as payload. It downloads several e-books from [Project Gutenberg](https://www.gutenberg.org/) to `gutenberg.zip` file and extracts them to the `gutenberg` directory.
- `pyproject.toml`

### Key Tasks

In `sender.py`, implement the following functions:

- `connect()`: Establish a connection with the server using a 3-way handshake.
- `send()`: Send data to the server using the Go-Back-N protocol.
- `close()`: Gracefully close the connection with the server using a FIN sequence.

Upon successful connection and data transfer, inspect the final FIN packet sent by the server.

### Testing

- Run your sender on the WREN. You should see some server responses subject to approximately ~20% packet loss.
- Capture packets with `tcpdump` and analyze them with Wireshark.

```sh
sudo tcpdump -i lo --print -w sabre.pcap 'udp port 5050'
```
