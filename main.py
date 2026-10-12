import argparse
import os
import random
import signal
import sys
import time

import nltk
from sender import SABRESender


def main():

    # download e-books from Project Gutenberg via the nltk gutenberg corpus
    # this is the data that you will send to the server as payload
    nltk.download("gutenberg", quiet=True)
    corpus_files = nltk.corpus.gutenberg.fileids()

    # argparser reads and processes command line arguments
    argparser = argparse.ArgumentParser(description="SABRE File Sender")
    argparser.add_argument("--host", help="Server IP address", default="sabre.cy350.space")
    argparser.add_argument("--port", type=int, help="Server port", default=5050)
    argparser.add_argument(
        "--filename",
        type=str,
        help="Pick a file from the list: " + ", ".join(corpus_files),
    )
    argparser.add_argument(
        "--window", type=int, default=5, help="Window size (packets)"
    )
    argparser.add_argument(
        "--timeout", type=float, default=1.0, help="Timeout (seconds)"
    )
    argparser.add_argument(
        "--cadet-num", type=str, required=True, help="Your cadet number from CIS to include in packets"
    )
    args = argparser.parse_args()

    if not args.filename:
        args.filename = "shakespeare-macbeth.txt"

    elif args.filename not in corpus_files:
        print(f"❌ Error: {args.filename} not available. Valid options: {', '.join(corpus_files)}")
        sys.exit(1)

    # validate cadet number to include in the packet header; this is used by the server to identify you and notify your instructor when you capture a flag
    cadet_num = str(args.cadet_num).strip()

    if cadet_num[0].isalpha():
        cadet_num = cadet_num[1:]  # drop leading 'C'
    if len(cadet_num) != 8 or not cadet_num.isdigit():
        print("❌ Error: Your cadet number must have exactly 8 digits.")
        sys.exit(1)

    # read the file to send from the corpus
    bytes_to_send = nltk.corpus.gutenberg.raw(args.filename).encode('utf-8')

    print(f"🎖️ Using Cadet Number: {cadet_num}")
    print(f"📄 Sending file: {args.filename} ({bytes_to_send[:50]}...)")

    file_size = len(bytes_to_send)
    # estimate number of packets from the payload size and MTU
    mtu = 1460
    total_packets = (file_size + mtu - 1) // mtu

    start_time = time.monotonic()
    start_datetime = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"📊 Transfer started at {start_datetime}")
    print(f"📦 File size: {file_size} bytes ({file_size / 1024:.2f} KB)")
    print(f"📦 Estimated packets: {total_packets} (MTU={mtu})")

    try:

        # initialize the SABRE sender
        client = SABRESender(
            remote=(args.host, args.port),
            cadet_num=int(cadet_num),
            window_size=args.window,
            timeout=args.timeout
        )

        # perform a 3-way handshake to establish connection with the server
        t_connect_start = time.monotonic()
        client.connect()
        t_connect_end = time.monotonic()

        # send the file data reliably using Go-Back-N protocol
        t_send_start = time.monotonic()
        client.send(bytes_to_send)
        t_send_end = time.monotonic()

        # perform connection teardown with a FIN sequence; this includes the server's final response which contains the flag if you successfully sent the file
        t_close_start = time.monotonic()
        client.close()
        t_close_end = time.monotonic()

    except Exception as e:  # noqa: BLE001
        print("⚠️ An error occurred. Use try/except blocks to find out what went wrong and handle errors gracefully.")
        print(f"⚠️ {e}")
        sys.exit(1)

    end_time = time.monotonic()
    end_datetime = time.strftime("%Y-%m-%d %H:%M:%S")

    # calculate statistics
    total_elapsed = end_time - start_time
    connect_time = t_connect_end - t_connect_start
    send_time = t_send_end - t_send_start
    close_time = t_close_end - t_close_start

    throughput_Bps = (file_size / send_time) if send_time > 0 else float("inf")
    throughput_bps = throughput_Bps * 8
    throughput_kbps = throughput_bps / 1000

    # print statistics summary
    print()
    print("=" * 60)
    print("📊 TRANSFER STATISTICS")
    print("=" * 60)
    print(f"  Start time:    {start_datetime}")
    print(f"  End time:      {end_datetime}")
    print(f"  Total elapsed: {total_elapsed:.3f} s")
    print(f"  Handshake:     {connect_time:.3f} s")
    print(f"  Send time:     {send_time:.3f} s")
    print(f"  Teardown:      {close_time:.3f} s")
    print(f"  File size:     {file_size} bytes ({file_size / 1024:.2f} KB)")
    print(f"  Packets:       {total_packets}")
    print(f"  MTU:           {mtu} bytes")
    print(f"  Window size:   {args.window}")
    print(f"  Timeout:       {args.timeout} s")
    print(f"  Throughput:    {throughput_Bps:.2f} B/s = {throughput_bps:.2f} b/s = ~{throughput_kbps:.2f} Kbps")
    print("=" * 60)


def _handle_sigint(signum, frame):
    print()
    print("🛑 Interrupted. Exiting gracefully.")
    sys.exit(0)


if __name__ == "__main__":
    # if os is not linux, warn and exit
    if os.name != "posix":
        print("⚠️ This program should be run in Linux or WSL or docker.")
        sys.exit(1)

    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"❌ Error: {e}")
        print("❌ This error was not expected. Contact your instructor for help.")
        sys.exit(1)
