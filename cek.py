import argparse
import time
from threading import Thread
import requests
import math
import socket
from struct import pack
from urllib.parse import urlparse

timeout = 5
good_list = []

def get_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="ProxyCheck",
        usage="%(prog)s [-h] -i PROXY_FILE [-o OUT_FILE][-s] -t THREADS",
        description="Test list of proxies for response and function",
    )
    parser.add_argument("-i", "--proxy_file", required=True, help="Proxy File Input")
    parser.add_argument("-o", "--output_file", help="Output File")
    parser.add_argument(
        "-s", "--socks", action="store_true", help="is SOCKS4/5 Proxy list"
    )
    parser.add_argument(
        "-t", "--threads", required=True, type=int, help="Number of threads to run on"
    )
    return parser.parse_args(argv)

def is_socks4(ip, port, soc):
    try:
        ipaddr = socket.inet_aton(ip)
        packet = b"\x04\x01" + pack(">H", port) + ipaddr + b"\x00"
        soc.sendall(packet)
        data = soc.recv(8)
        return len(data) >= 2 and data[1] == 0x5A
    except:
        return False

def is_socks5(soc):
    try:
        soc.sendall(b"\x05\x01\x00")
        data = soc.recv(2)
        return len(data) >= 2 and data[0] == 0x05 and data[1] == 0x00
    except:
        return False

def test_socks(proxy_list, thread_number):
    working_list = []
    for item in proxy_list:
        try:
            if "@" in item:
                print(f"[Thread: {thread_number}] Skipping SOCKS proxy with auth: {item}")
                continue  # Not supported
            ip, port = item.split(":")
            port = int(port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))

            if is_socks4(ip, port, s) or is_socks5(s):
                s.close()
                print(f"[Thread: {thread_number}] Proxy Works: {item}")
                working_list.append(item)
            else:
                s.close()
                print(f"[Thread: {thread_number}] Proxy Failed: {item}")
        except Exception as e:
            print(f"[Thread: {thread_number}] Proxy Error: {item} -> {e}")
    good_list.extend(working_list)

def verify_proxy(proxy_list, thread_number):
    working_list = []
    for item in proxy_list:
        try:
            if "@" in item:
                proxy = f"http://{item}"
            else:
                proxy = f"http://{item}"
            proxy_dict = {"http": proxy, "https": proxy}

            r = requests.get("https://api.ipify.org/?format=json", proxies=proxy_dict, timeout=timeout)
            response = r.json()
            proxy_ip = urlparse(proxy).hostname
            actual_ip = response["ip"]

            print(f"[Thread: {thread_number}] Proxy Active: {item}")
            print(
                f'[Thread: {thread_number}] Proxy Works: {"True" if actual_ip == proxy_ip else "False"}'
            )
            working_list.append(item)
        except Exception as e:
            print(f"[Thread: {thread_number}] Proxy Failed: {item} -> {e}")
    good_list.extend(working_list)

def get_proxies(file):
    with open(file, "r") as f:
        return [line.strip() for line in f if line.strip()]

def setup(number_threads):
    proxy_list = get_proxies(args.proxy_file)
    amount = int(math.ceil(len(proxy_list) / float(number_threads)))
    proxy_lists = [
        proxy_list[i:i + amount] for i in range(0, len(proxy_list), amount)
    ]
    return proxy_lists

def main(threads):
    start_time = time.time()
    lists = setup(threads)
    thread_list = []

    target = test_socks if args.socks else verify_proxy

    for i, proxy_group in enumerate(lists):
        t = Thread(target=target, args=(proxy_group, i))
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join()

    filename = args.output_file if args.output_file else "good_proxies.txt"
    with open(filename, "w") as f:
        for proxy in good_list:
            f.write(proxy + "\n")

    print(f"\n✅ Working Proxies Saved to: {filename}")
    print(f"⏱ Completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    args = get_args()
    main(args.threads)
