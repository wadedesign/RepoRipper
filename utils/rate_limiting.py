import requests
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

class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens=1):
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        refill_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + refill_tokens)
        self.last_refill = now
