import hashlib
import struct

# SABRE packet flags
FLAG_DATA = 0x00
FLAG_ACK = 0x01
FLAG_SYN = 0x02
FLAG_FIN = 0x04
FLAG_RST = 0x08


class SabrePacket:
    # TYPE_SABRE is the fixed first byte of the header to identify this as a SABRE packet
    TYPE_SABRE = 0xDD
    # Use a single 8-byte unsigned integer (Q) to pack all header fields
    HEADER_FORMAT = "!Q"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    # maximum payload size to avoid IP fragmentation
    MAX_PAYLOAD = 1460

    def __init__(self, flags, seq, ack, cadet_hash, payload=b""):
        """
        Initialize a SABRE packet.

        Attributes:
        - flags: 1-bit packet flags (DATA, ACK, SYN, FIN, RST)
        - seq: sequence number
        - ack: acknowledgment number
        - cadet_hash: 2-byte Blake2s hash of the cadet identifier
        - payload: packet payload
        """

        self.flags = flags
        self.length = len(payload)
        self.seq = seq
        self.ack = ack
        # cadet_hash is a 2-byte Blake2s hash of the cadet identifier
        if isinstance(cadet_hash, int):
            self.cadet_hash = (cadet_hash & 0xFFFF).to_bytes(2, byteorder="big")
        else:
            self.cadet_hash = bytes(cadet_hash)
        self.payload = payload

        if flags not in (
            FLAG_DATA,
            FLAG_ACK,
            FLAG_SYN,
            FLAG_FIN,
            FLAG_RST,
            FLAG_SYN | FLAG_ACK,
            FLAG_FIN | FLAG_ACK,
        ):
            raise ValueError(f"Invalid packet flags: {flags:#04x}")

        if len(payload) > SabrePacket.MAX_PAYLOAD:
            raise ValueError(
                f"Payload too large: {len(payload)} bytes (max {SabrePacket.MAX_PAYLOAD})"
            )

        # Updated limit check for 12-bit boundaries (max 4095)
        if seq < 0 or seq > 0xFFF or ack < 0 or ack > 0xFFF:
            raise ValueError("Sequence or Acknowledgment number out of range.")

    def encode(self):
        payload = self.payload or b""
        encoded_length = self.length if self.length is not None else len(payload)

        # Shift and mask fields into their specific bit positions
        header_int = (
            ((SabrePacket.TYPE_SABRE & 0xFF) << 56)
            | ((self.flags & 0x0F) << 52)
            | ((self.seq & 0xFFF) << 40)
            | ((self.ack & 0xFFF) << 28)
            | ((encoded_length & 0xFFF) << 16)
            | (int.from_bytes(self.cadet_hash, byteorder="big") & 0xFFFF)
        )

        header = struct.pack(SabrePacket.HEADER_FORMAT, header_int)
        return header + payload

    @staticmethod
    def decode(data):
        """Decode raw bytes into a SabrePacket instance."""

        if len(data) < SabrePacket.HEADER_SIZE:
            raise ValueError("Packet too short to contain SABRE header")

        header = data[: SabrePacket.HEADER_SIZE]
        payload = data[SabrePacket.HEADER_SIZE :]

        (header_int,) = struct.unpack(SabrePacket.HEADER_FORMAT, header)

        # Unmask and unshift back out of the 64-bit integer
        pkt_type = (header_int >> 56) & 0xFF
        flags = (header_int >> 52) & 0x0F
        seq = (header_int >> 40) & 0xFFF
        ack = (header_int >> 28) & 0xFFF
        length = (header_int >> 16) & 0xFFF
        cadet_hash = (header_int & 0xFFFF).to_bytes(2, byteorder="big")

        if pkt_type != SabrePacket.TYPE_SABRE:
            raise ValueError("Invalid packet type, definitely not a SABRE packet")

        if len(payload) > length:
            payload = payload[:length]

        return SabrePacket(flags, seq, ack, cadet_hash, payload)

    @staticmethod
    def hash_cadet_num(value: int | str) -> bytes:
        # NOTE: You'll want to update this to output/return your 2-byte hash
        text = str(value).strip().upper()
        if text[0].isalpha():
            text = text[1:]
        try:
            value = int(text)
        except ValueError:
            raise ValueError(f"Invalid cadet ID value: {value}")
        return SabrePacket.hash16(value)

    @staticmethod
    def hash16(value: int):
        # Mask to unsigned 32-bit to handle negative values safely
        value = value & 0xFFFFFFFF
        # Convert integer to 4-byte big-endian bytes for hashing
        data = value.to_bytes(4, byteorder="big", signed=False)
        # Return 2-byte Blake2s digest
        return hashlib.blake2s(data, digest_size=2).digest()

    def __str__(self):
        """Return a one-line string representation for debugging."""

        payload_str = ""

        MAX_PAYLOAD_DISPLAY = 30
        if self.flags & FLAG_FIN or len(self.payload) <= MAX_PAYLOAD_DISPLAY:
            payload_str = self.payload.decode()
        else:
            payload_str = self.payload[: MAX_PAYLOAD_DISPLAY - 3].decode() + "..."

        if payload_str:
            payload_str = payload_str.replace("\n", " ")
            return f'SABRE[flags=0x{self.flags:X} seq={self.seq} ack={self.ack} len={self.length} payload="{payload_str}"]'

        return f"SABRE[flags=0x{self.flags:X} seq={self.seq} ack={self.ack} len={self.length}]"
