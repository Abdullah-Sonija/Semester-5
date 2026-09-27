"""
DNS Query Resolution using Socket Programming
------------------------------------------------
Builds and sends a raw DNS query over UDP (port 53) and manually parses
the response (Header, Question, Answer sections) for A records.

No high-level resolver functions (gethostbyname, dns.resolver, etc.) are
used - the DNS wire-format message is constructed and parsed by hand,
per RFC 1035.
"""

import socket
import struct
import random
import sys

# ---------------------------------------------------------------------
# DNS constants
# ---------------------------------------------------------------------
DNS_PORT = 53
TIMEOUT_SECONDS = 4
QTYPE_A = 1          # Host address
QCLASS_IN = 1         # Internet

RCODE_MEANINGS = {
    0: "NOERROR - No error",
    1: "FORMERR - Format error",
    2: "SERVFAIL - Server failure",
    3: "NXDOMAIN - Name does not exist",
    4: "NOTIMP - Not implemented",
    5: "REFUSED - Query refused",
}


# ---------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------
def build_dns_query(domain: str, transaction_id: int) -> bytes:
    """
    Builds a raw DNS query message (Header + Question section) for an
    A-record lookup, as per RFC 1035 section 4.

    Header layout (12 bytes):
        ID (16 bits) | Flags (16 bits) | QDCOUNT (16) | ANCOUNT (16)
        | NSCOUNT (16) | ARCOUNT (16)
    """
    # --- Header ---
    # Flags: QR=0 (query), Opcode=0000 (standard query), AA=0, TC=0,
    # RD=1 (recursion desired), RA=0, Z=000, RCODE=0000
    flags = 0x0100  # 0000 0001 0000 0000  -> RD bit set
    qdcount = 1
    ancount = 0
    nscount = 0
    arcount = 0

    header = struct.pack(
        "!HHHHHH",
        transaction_id, flags, qdcount, ancount, nscount, arcount
    )

    # --- Question section ---
    # QNAME is encoded as a sequence of length-prefixed labels, e.g.
    # "www.example.com" -> 3www7example3com0
    qname = encode_domain_name(domain)
    qtype = struct.pack("!H", QTYPE_A)
    qclass = struct.pack("!H", QCLASS_IN)

    question = qname + qtype + qclass

    return header + question


def encode_domain_name(domain: str) -> bytes:
    """Encodes a domain name into DNS label format, terminated by 0x00."""
    encoded = b""
    for label in domain.strip(".").split("."):
        if not label:
            raise ValueError("Invalid domain name: empty label")
        if len(label) > 63:
            raise ValueError(f"Label too long (max 63 chars): {label}")
        encoded += struct.pack("!B", len(label)) + label.encode("ascii")
    encoded += b"\x00"  # root/terminator
    return encoded


# ---------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------
def decode_domain_name(data: bytes, offset: int):
    """
    Decodes a domain name starting at `offset` in `data`, following
    DNS message compression pointers (RFC 1035 section 4.1.4) where a
    label may be replaced by a pointer to an earlier occurrence.

    Returns (domain_name_string, next_offset_after_this_field).
    `next_offset` refers to the position right after the name in its
    ORIGINAL location (important when a pointer is followed).
    """
    labels = []
    pos = offset
    jumped = False
    original_next_offset = None

    while True:
        length = data[pos]

        if length == 0:
            pos += 1
            if not jumped:
                original_next_offset = pos
            break

        # Top two bits set (0xC0) => compression pointer
        if (length & 0xC0) == 0xC0:
            pointer = ((length & 0x3F) << 8) | data[pos + 1]
            if not jumped:
                original_next_offset = pos + 2
            pos = pointer
            jumped = True
            continue

        pos += 1
        labels.append(data[pos:pos + length].decode("ascii", errors="replace"))
        pos += length

    return ".".join(labels), original_next_offset


def parse_dns_header(data: bytes):
    """Parses the 12-byte DNS header."""
    (tid, flags, qdcount, ancount, nscount, arcount) = struct.unpack(
        "!HHHHHH", data[0:12]
    )

    qr = (flags >> 15) & 0x1
    opcode = (flags >> 11) & 0xF
    aa = (flags >> 10) & 0x1
    tc = (flags >> 9) & 0x1
    rd = (flags >> 8) & 0x1
    ra = (flags >> 7) & 0x1
    rcode = flags & 0xF

    return {
        "id": tid,
        "qr": qr,
        "opcode": opcode,
        "aa": aa,
        "tc": tc,
        "rd": rd,
        "ra": ra,
        "rcode": rcode,
        "qdcount": qdcount,
        "ancount": ancount,
        "nscount": nscount,
        "arcount": arcount,
    }


def parse_question_section(data: bytes, offset: int, qdcount: int):
    """Parses QDCOUNT question entries, returns (list_of_questions, new_offset)."""
    questions = []
    for _ in range(qdcount):
        qname, offset = decode_domain_name(data, offset)
        qtype, qclass = struct.unpack("!HH", data[offset:offset + 4])
        offset += 4
        questions.append({"qname": qname, "qtype": qtype, "qclass": qclass})
    return questions, offset


def parse_resource_records(data: bytes, offset: int, count: int):
    """
    Parses `count` resource records (used for Answer/Authority/Additional
    sections). Returns (list_of_records, new_offset).

    RR format:
        NAME | TYPE (2) | CLASS (2) | TTL (4) | RDLENGTH (2) | RDATA
    """
    records = []
    for _ in range(count):
        name, offset = decode_domain_name(data, offset)
        rtype, rclass, ttl, rdlength = struct.unpack(
            "!HHIH", data[offset:offset + 10]
        )
        offset += 10
        rdata_raw = data[offset:offset + rdlength]

        record = {
            "name": name,
            "type": rtype,
            "class": rclass,
            "ttl": ttl,
            "rdlength": rdlength,
        }

        if rtype == QTYPE_A and rdlength == 4:
            record["address"] = ".".join(str(b) for b in rdata_raw)
        else:
            record["address"] = None  # Not an A record (or unexpected length)

        offset += rdlength
        records.append(record)

    return records, offset


def parse_dns_response(data: bytes):
    """Fully parses a raw DNS response into a dictionary."""
    header = parse_dns_header(data)
    offset = 12

    questions, offset = parse_question_section(data, offset, header["qdcount"])
    answers, offset = parse_resource_records(data, offset, header["ancount"])
    # Authority/Additional sections parsed too so offset stays consistent
    # (not required for reporting, but keeps parsing correct/complete).
    authorities, offset = parse_resource_records(data, offset, header["nscount"])
    additionals, offset = parse_resource_records(data, offset, header["arcount"])

    return {
        "header": header,
        "questions": questions,
        "answers": answers,
        "authorities": authorities,
        "additionals": additionals,
    }


# ---------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------
def send_dns_query(domain: str, dns_server: str):
    """
    Sends a DNS A-record query for `domain` to `dns_server` over UDP
    port 53, and returns the raw response bytes (or raises an
    exception on timeout / socket error).
    """
    transaction_id = random.randint(0, 0xFFFF)
    query = build_dns_query(domain, transaction_id)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT_SECONDS)

    try:
        sock.sendto(query, (dns_server, DNS_PORT))
        response, _ = sock.recvfrom(4096)
    finally:
        sock.close()

    # Sanity check: response transaction ID must match the query's
    resp_id = struct.unpack("!H", response[0:2])[0]
    if resp_id != transaction_id:
        raise ValueError(
            f"Transaction ID mismatch (sent {transaction_id}, got {resp_id}) "
            f"- possible spoofed or unrelated response"
        )

    return response, transaction_id


# ---------------------------------------------------------------------
# Display / reporting
# ---------------------------------------------------------------------
def print_result(domain: str, dns_server: str, parsed: dict, transaction_id: int):
    header = parsed["header"]
    rcode = header["rcode"]

    print("\n" + "=" * 60)
    print(f"Query: {domain}   |   DNS Server: {dns_server}")
    print("=" * 60)
    print(f"Transaction ID   : {transaction_id} (0x{transaction_id:04X})")

    if parsed["questions"]:
        q = parsed["questions"][0]
        qtype_str = "A" if q["qtype"] == QTYPE_A else str(q["qtype"])
        print(f"Query Name       : {q['qname']}")
        print(f"Query Type       : {qtype_str}")

    print(f"Flags            : QR={header['qr']} Opcode={header['opcode']} "
          f"AA={header['aa']} TC={header['tc']} RD={header['rd']} RA={header['ra']}")
    print(f"Response Status  : RCODE={rcode} -> "
          f"{RCODE_MEANINGS.get(rcode, 'Unknown RCODE')}")
    print(f"Answer Count     : {header['ancount']}")

    if rcode != 0:
        print("\n[!] Query was not successful - no address resolved.")
        return

    if header["ancount"] == 0:
        print("\n[!] No answer records returned (domain may have no A record).")
        return

    print("\nAnswer Record(s):")
    for i, ans in enumerate(parsed["answers"], start=1):
        print(f"  [{i}] Name : {ans['name']}")
        print(f"      Type : {ans['type']} "
              f"({'A' if ans['type'] == QTYPE_A else 'other'})")
        print(f"      TTL  : {ans['ttl']} seconds")
        if ans["address"]:
            print(f"      Address (IPv4): {ans['address']}")
        else:
            print(f"      RDATA: {ans['rdlength']} bytes (not a parsed A record)")

    # Convenience summary line
    a_records = [a for a in parsed["answers"] if a["address"]]
    if a_records:
        first = a_records[0]
        print(f"\nResolved IPv4 Address : {first['address']}")
        print(f"TTL                    : {first['ttl']} seconds")


# ---------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------
def is_valid_domain(domain: str) -> bool:
    """Basic sanity check on the domain name format."""
    if not domain or len(domain) > 253:
        return False
    labels = domain.strip(".").split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63:
            return False
        if not all(c.isalnum() or c == "-" for c in label):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return True


# ---------------------------------------------------------------------
# Main program loop
# ---------------------------------------------------------------------
def main():
    print("DNS Query Resolution using Socket Programming (UDP, port 53)")
    print("Type 'quit' or 'exit' as the domain name to stop.\n")

    dns_server = input("Enter the DNS server IP address to query (e.g. 8.8.8.8): ").strip()
    try:
        socket.inet_aton(dns_server)
    except OSError:
        print(f"[!] '{dns_server}' is not a valid IPv4 address. Exiting.")
        sys.exit(1)

    while True:
        domain = input("\nEnter a domain name to resolve: ").strip()

        if domain.lower() in ("quit", "exit"):
            print("Exiting. Goodbye.")
            break

        if not is_valid_domain(domain):
            print(f"[!] '{domain}' is not a valid domain name. Please try again.")
            continue

        try:
            response, transaction_id = send_dns_query(domain, dns_server)
            parsed = parse_dns_response(response)
            print_result(domain, dns_server, parsed, transaction_id)

        except socket.timeout:
            print(f"[!] Request timed out - no response from DNS server {dns_server}.")
        except ValueError as ve:
            print(f"[!] Error: {ve}")
        except OSError as oe:
            print(f"[!] Network/socket error: {oe}")
        except Exception as e:
            print(f"[!] Unexpected error while processing response: {e}")


if __name__ == "__main__":
    main()
