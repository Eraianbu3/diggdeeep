#!/usr/bin/env python3

import argparse
import requests
import signal
import sys
import os
import json
import subprocess
from colorama import Fore, init
from concurrent.futures import ThreadPoolExecutor, as_completed

init(autoreset=True)

# -------------------------
# CTRL+C handler
# -------------------------
def graceful_exit(sig, frame):
    print(Fore.RED + "\n[!] Interrupted. Exiting safely.")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)

# -------------------------
# Status code coloring
# -------------------------
def color_status(code):
    if code == 200:
        return Fore.GREEN + str(code)
    elif code in [301, 302]:
        return Fore.CYAN + str(code)
    elif code in [401, 403]:
        return Fore.YELLOW + str(code)
    elif code >= 500:
        return Fore.RED + str(code)
    else:
        return Fore.WHITE + str(code)

# -------------------------
# Subdomain Enumeration
# -------------------------
def get_subdomains(domain):
    print(Fore.MAGENTA + f"[+] Enumerating subdomains for {domain}")

    subdomains = set()

    # Try subfinder first
    try:
        result = subprocess.run(
            ["subfinder", "-d", domain, "-silent"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout:
            for line in result.stdout.splitlines():
                subdomains.add(line.strip())

            print(Fore.GREEN + f"[+] Found {len(subdomains)} subdomains via subfinder.")
            return list(subdomains)

    except FileNotFoundError:
        print(Fore.YELLOW + "[!] subfinder not found. Falling back to crt.sh")

    # Fallback to crt.sh
    try:
        url = f"http://crt.sh/?q=%25.{domain}&output=json"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=20)

        data = json.loads(response.text)

        for entry in data:
            name = entry.get("name_value", "")
            for sub in name.split("\n"):
                if domain in sub:
                    subdomains.add(sub.strip().lower())

        print(Fore.GREEN + f"[+] Found {len(subdomains)} subdomains via crt.sh.")

    except Exception as e:
        print(Fore.RED + f"[-] Subdomain enumeration failed: {e}")

    return list(subdomains)

# -------------------------
# Check if subdomain is alive
# -------------------------
def check_alive(subdomain):
    try:
        r = requests.get(
            f"https://{subdomain}",
            timeout=5,
            allow_redirects=False,
            headers={"User-Agent": "DiggDeeep/3.0"}
        )
        return subdomain
    except:
        return None

# -------------------------
# Fuzz paths for subdomain
# -------------------------
def fuzz_subdomain(subdomain, wordlist):
    print(Fore.MAGENTA + f"\n[+] Fuzzing {subdomain}")

    results = []

    with open(wordlist, "r", errors="ignore") as f:
        for line in f:
            path = line.strip()
            if not path:
                continue

            url = f"https://{subdomain}/{path}"

            try:
                r = requests.get(
                    url,
                    timeout=5,
                    allow_redirects=False,
                    headers={"User-Agent": "DiggDeeep/3.0"}
                )

                print(f"[{color_status(r.status_code)}] {url}")

                if r.status_code in [200, 301, 302, 401, 403]:
                    results.append(f"{r.status_code} {url}")

            except:
                continue

    return results

# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="DiggDeeep Recon Tool")
    parser.add_argument("-d", "--domain", required=True, help="Target domain")
    parser.add_argument("-pw", "--pathwordlist", required=True, help="Path wordlist")
    parser.add_argument("-t", "--threads", type=int, default=20, help="Threads")

    args = parser.parse_args()

    if not os.path.isfile(args.pathwordlist):
        print(Fore.RED + "[-] Path wordlist not found!")
        sys.exit(1)

    os.makedirs("results", exist_ok=True)

    # Step 1: Enumerate subdomains
    subdomains = get_subdomains(args.domain)

    if not subdomains:
        print(Fore.RED + "[-] No subdomains found.")
        sys.exit(1)

    # Step 2: Check which are alive
    print(Fore.MAGENTA + "[+] Checking live subdomains...")

    live_subdomains = []

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(check_alive, sub) for sub in subdomains]
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(Fore.GREEN + f"[LIVE] {result}")
                live_subdomains.append(result)

    print(Fore.GREEN + f"[+] {len(live_subdomains)} live subdomains found.")

    # Save discovered subdomains
    with open(f"results/{args.domain}_subdomains.txt", "w") as f:
        for sub in live_subdomains:
            f.write(sub + "\n")

    # Step 3: Fuzz each live subdomain
    for sub in live_subdomains:
        results = fuzz_subdomain(sub, args.pathwordlist)

        output_file = f"results/{sub}.txt"

        with open(output_file, "w") as f:
            for r in results:
                f.write(r + "\n")

        print(Fore.GREEN + f"[+] Saved results to {output_file}")

    print(Fore.GREEN + "\n[+] Recon Completed.")

if __name__ == "__main__":
    main()
