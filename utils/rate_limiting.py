# utils/rate_limiting.py
import requests
from tqdm import tqdm
import time

def check_rate_limit(headers):
    """Checks the remaining GitHub API rate limit and returns it."""
    rate_limit_url = "https://api.github.com/rate_limit"
    response = requests.get(rate_limit_url, headers=headers)
    rate_limit_data = response.json()

    remaining_requests = rate_limit_data['rate']['remaining']
    reset_time = rate_limit_data['rate']['reset']

    return remaining_requests, reset_time


def update_rate_limit_status(headers, pbar=None):
    remaining_requests, _ = check_rate_limit(headers)
    if pbar:
        pbar.set_postfix(rate_limit=remaining_requests, refresh=True)