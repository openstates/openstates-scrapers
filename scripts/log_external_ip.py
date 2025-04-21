import requests
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def log_external_ip():
    try:
        response = requests.get("https://ipecho.net/plain", verify=False)
        print(f"Requests lib external IP for this scraper run is: {response.text}")
    except Exception as e:
        print(f"Failed to obtain external IP used by requests library with error: {e}")


if __name__ == "__main__":
    log_external_ip()
    sys.exit()
