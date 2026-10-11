import time

import socket

import requests

from urllib.parse import urlparse

def measure_api_performance(url):
    report = {}
    host = urlparse(url).hostname
    started = time.time()
    socket.gethostbyname(host)
    report["dns"] = time.time() - started
    started = time.time()
    response = requests.get(url)
    report["total"] = time.time() - started
    report["headers"] = response.elapsed.total_seconds()
    report["status"] = response.status_code
    report["size"] = len(response.content)




    return report

if __name__ == "__main__":
    results =  measure_api_performance("http://localhost:8000/products")
    for stage, value in results.items():
        print(f"{stage}: {value}")



