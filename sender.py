import socket
import time
from simpletimer import SimpleTimer
from typing import List, Tuple
from packet import SabrePacket, FLAG_ACK, FLAG_SYN, FLAG_FIN, FLAG_RST, FLAG_DATA

# never exceed 1460 bytes to avoid IP fragmentation
# 1500 - 20 byte IP header - 8 byte UDP header - 8 byte SABRE header = 1464
MTU = 1460

# 12-bit sequence/acknowledgment field space (matches SabrePacket's 0xFFF limit)
MAX_SEQ = 2 ** 12  # 4096


class SABRESender:
    def __init__(self, remote: Tuple[str, int], cadet_num: int = 0, window_size: int = 5, timeout: float = 1.0):
        """
        Initialize the SABRE sender and its state.

        This class sends data over UDP while implementing reliability in software
        using a TCP-like workflow:
        1. establish a connection with a handshake,
        2. send data reliably using a Go-Back-N sliding window,
        3. close the connection with a FIN exchange.

        Important notes for the SABRE protocol:
        - Sequence numbers increase by 1 per packet, not by number of bytes.
        - ACK values are Cumulative Acknowledgements that represent the next sequence number the
          receiver expects.

        Attributes:
        - remote: (IP, port) tuple of the receiver
        - cadet_hash: 16-bit hash of the cadet identifier, matching what the receiver expects
        - WINDOW_SIZE: maximum number of unacknowledged packets allowed in flight
        - TIMEOUT: retransmission timeout in seconds
        - sock: UDP socket for sending/receiving packets
        - timer: SimpleTimer instance for managing retransmission timeouts
        - connected: whether the handshake has completed successfully
        - next_seq: sequence number to use for the next outgoing packet
        - send_base: sequence number of the oldest unacknowledged packet
        """
        self.remote = remote
        # Hash the cadet ID to a 16-bit value, matching what the receiver
        # expects (it stores hash_cadet_num() results from roster.csv).
        self.cadet_hash = SabrePacket.hash_cadet_num(cadet_num)
        self.WINDOW_SIZE = int(window_size)
        self.TIMEOUT = float(timeout)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))  # bind to ephemeral port to ensure we can receive responses
        self.sock.settimeout(self.TIMEOUT)

        self.timer = SimpleTimer(self.TIMEOUT)

        self.connected = False

        # next sequence number to send (initially 0, will be updated after handshake)
        self.next_seq = 0

        # Oldest unacknowledged packet/window base.
        # Starts at 0 and will move forward as ACKs are received.
        self.send_base = 0

        print(f"{time.time():.6f} 🎖️ Cadet: C{cadet_num}, Remote: {self.remote}, Window Size: {self.WINDOW_SIZE}, Timeout: {self.TIMEOUT}")

    # DO NOT MODIFY THIS FUNCTION
    def _make_packets(self, start_seq: int, data: bytes) -> List[SabrePacket]:
        """
        Split a byte string into SABRE data packets.

        Each packet carries up to MTU bytes of payload and is assigned a sequence
        number starting at start_seq.

        Example:
            If start_seq = 4 and the data becomes 3 packets, the packets will use
            sequence numbers 4, 5, and 6.
        """
        packets = []
        seq = start_seq
        for i in range(0, len(data), MTU):
            chunk = data[i:i + MTU]
            pkt = SabrePacket(FLAG_DATA, seq=seq, ack=0, cadet_hash=self.cadet_hash, payload=chunk)
            packets.append(pkt)
            seq += 1
        return packets

    # DO NOT MODIFY THIS FUNCTION
    def _send_packet(self, pkt: SabrePacket, ack_num=0) -> None:
        """Encode and send a single packet to the receiver."""
        pkt.ack = ack_num
        print(f"{time.time():.6f} 📨 {pkt}")
        self.sock.sendto(pkt.encode(), self.remote)

    # DO NOT MODIFY THIS FUNCTION
    def _recv_packet(self, timeout: float = None) -> SabrePacket:
        """
        Receive a single packet, waiting up to timeout seconds.

        Returns:
        - SabrePacket on success
        - None on socket timeout
        - None on decode failure

        This helper only reads one packet at a time, so you may need to call it
        repeatedly depending on the protocol state.

        The timeout is configurable because different phases of the protocol may
        want different waiting behavior.
        """

        if timeout is None:
            timeout = self.TIMEOUT
        self.sock.settimeout(timeout)

        try:
            data, _ = self.sock.recvfrom(SabrePacket.HEADER_SIZE + MTU)
        except socket.timeout:
            return None

        try:
            pkt = SabrePacket.decode(data)
            print(f"{time.time():.6f} 📬 {pkt}")
            return pkt
        except Exception as e:
            print(f"{time.time():.6f} ⚠️ Error decoding packet: {e}")
            return None

    def connect(self) -> None:
        """
        Perform a three-way handshake to establish a SABRE connection.

        The expected flow is conceptually similar to TCP:
        1. Sender sends SYN with its current starting sequence number.
        2. Receiver replies with SYN+ACK if it is willing to connect.
        3. Sender validates the response and sends a final ACK.

        ACK reminder:
        - The ACK field means "the next sequence number expected."
        - If we send SYN with sequence number X, a valid SYN+ACK should acknowledge X + 1.

        If the receiver sends RST or never responds correctly after 10 retries,
        treat the connection as failed.
        """

        # Create a SYN packet using the current starting sequence number.
        # pkt_syn = ...
        # print(f"{time.time():.6f} 📡 INITIATE HANDSHAKE with {self.remote}: {pkt_syn}")

        # The SYN is not an ACK-only packet, so it consumes a sequence number.
        # Increment next_seq by 1 since we are sending something other than an ACK-only packet.
        # (We capture syn_seq here and will set self.next_seq = syn_seq + 1 after the handshake.)

        # Retry the handshake up to 10 times in case the SYN or SYN+ACK is lost.

            # Transmit the SYN packet to the receiver.

            # Wait for a SYN+ACK response for up to self.TIMEOUT seconds.
            # If you receive RST, the receiver has rejected the connection.
            # expect SYN+ACK with ack == syn_seq + 1
            # If you receive a SYN+ACK, verify that its ACK field matches the expected value (syn_seq + 1).
            # Ignore unrelated packets and continue retrying as needed.


            # If the response is valid:
                # 1. Set self.send_base and self.next_seq to expected_ack (syn_seq + 1)
                # 2. Send the final ACK to complete the handshake
                # 3. Mark self.connected = True
                # 4. Return from the function

        # If all retries fail without a valid SYN+ACK, treat the connection as failed. Raise an error.
        raise TimeoutError("Handshake failed (no SYN+ACK)")

    def send(self, data: bytes) -> None:
        """
        Send data reliably using the Go-Back-N sliding window protocol.

        High-level idea:
        - Break the data into packets.
        - Send as many packets as the window allows.
        - Track the oldest unacknowledged packet with send_base.
        - Use a single timer for the oldest outstanding packet.
        - When an ACK arrives, slide the window forward.
        - If the timer expires, retransmit all packets currently in the window.

        Important project-specific details:
        - Sequence numbers increase by 1 per packet, not per byte.
        - ACK values represent Cumulative Acknowledgements (the next sequence number the receiver expects).
        - end_seq is the sequence number ONE PAST the last packet in this send() call, i.e., start_seq + total_packets. It is NOT the last packet's sequence number.
        - Because _make_packets() returns a Python list, the packet at sequence number S has list index S - start_seq.

        Useful Variables:
        - send_base: sequence number of the oldest unacknowledged packet; window starts here
        - next_seq: sequence number of the next packet to send
        - end_seq: one past the last packet's sequence number in this send() call (i.e., start_seq + total_packets)
        """

        # First, make sure a connection has already been established.

        # Use _make_packets() to break the data into MTU-sized SABRE packets.
        # Each packet will be given a sequence number starting at self.next_seq.

        # print(f"{time.time():.6f} 🚀 START SEND: {len(data)} bytes, start_seq: {self.next_seq}, total_packets: {total_packets}")

        # end_seq is ONE PAST the last packet's sequence number.

        # Main Go-Back-N loop:
        # Continue looping until every packet has been sent and successfully acknowledged.

        # While there are still unacknowledged packets:

            # Send new packets if the window shifted. No retransmissions yet.
            # Start at next_seq and send up to WINDOW_SIZE packets, but do not go past end_seq.

                # Send each packet in this window.

                # If this is the first unacknowledged packet (the one at send_base), start the timer.
                # Go-Back-N uses one timer for the oldest unacknowledged packet.

            # After sending the current window, check the timer.
            # If it expired, assume a packet or ACK was lost.

                # Retransmit all unacknowledged packets starting from send_base.
                # This is the key idea of Go-Back-N:
                # on timeout, resend everything in the current window.

                # Restart the timer after retransmitting.

            # Figure out how long to wait for a reply.
            # If the timer is running, use the remaining time.
            # Otherwise, use self.TIMEOUT.

            # Attempt to receive all incoming packets in a tight inner loop.
            # Multiple ACKs may be queued, and draining them lets the window
            # slide as far as possible before the next send/receive cycle.

            # while True:
                # Try to receive a packet (usually an ACK, but possibly an RST).

                # If timeout occurs (`_recv_packet()` returns None), break the inner loop

                # If you receive RST, the receiver has reset the connection.
                # Raise an error and stop sending.

                # If you receive ACK:

                    # Check whether this ACK is valid AND moves the window forward.

                        # If the ACK moves the window forward:
                        # update send_base so those packets are now considered acknowledged

                        # If there are still unacknowledged packets left,
                        # restart the timer for the new oldest unacknowledged packet.

                        # If all packets have been acknowledged, stop the timer and break the inner loop.

                    # If the ACK does not move the window forward, it is old or duplicated.

        # Once the loop ends, every packet should have been sent and successfully acknowledged.
        # This is a fantastic place to validate that by checking the values of send_base and end_seq.

        # Update self.next_seq so future sends and close() start at the correct sequence number.

        # Nerdy Note: You don't need to update this after sending each packet because the SABRE
        # protocol calculates the sequence number of each packet at the time of creation in
        # _make_packets(), so next_seq only needs to be updated so that the next time you want
        # to create packets, they get the correct sequence numbers.

        # Stop the timer before returning.

    def close(self) -> None:
        """
        Perform connection teardown using a FIN exchange.

        The goal here is to tell the receiver that the sender is finished and to
        shut down cleanly if possible.

        Expected behavior:
        - If not connected, there is no protocol state to tear down, so just close the socket.
        - If connected, send FIN and wait for a response.
        - A valid FIN-related ACK should acknowledge either fin_seq or fin_seq + 1.
        - If the receiver includes a payload in its FIN response, print it.
        - If the receiver sends RST, treat the connection as closed/reset by remote.

        Because UDP is unreliable, it is reasonable to transmit FIN multiple times
        if necessary.
        """

        # If there is no active connection, simply close the socket and return.
        # No FIN exchange is necessary in that case.

        # Create a FIN packet using the appropriate current sequence number.
        # fin_pkt = SabrePacket(FLAG_FIN, ...)

        # Set the socket timeout used while waiting for the FIN response.

        # Send the FIN multiple times if needed because it or the response may be lost.
        # attempt = 0
        # while attempt < 10:
        #     attempt += 1
        #     self.sock.sendto(fin_pkt.encode(), self.remote)
        #     print(f"🎯 FIN sent")

            # After each FIN transmission, wait for a response from the receiver.

            # If you receive a FIN-ACK that acknowledges our FIN:
            # 1. print the payload contained in that FIN packet
            # 2. treat the connection as closed gracefully
            # 3. exit the retry loop

            # If you receive RST, treat the connection as closed/reset by the remote side
            # and exit the retry loop.

        # Finally, close the socket whether teardown was graceful or forced.
