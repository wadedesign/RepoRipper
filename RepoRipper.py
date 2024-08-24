import os
import base64
import asyncio
import time
import aiohttp
import aiofiles
import logging
import json
from tqdm.asyncio import tqdm as async_tqdm
from dotenv import load_dotenv
from colorama import init, Fore, Style
from argparse import ArgumentParser, Namespace
from utils.rate_limiting import check_rate_limit, TokenBucket
from utils import async_io
from functools import wraps
from typing import Set, Tuple

init()
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SAVE_DIRECTORY = os.getenv('SAVE_DIRECTORY', '.')
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
CACHE = {}
EXCLUSION_SET: Set[str] = set()

bucket = TokenBucket(rate=5000, capacity=5000)

def cached(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Convert sets to lists in args and kwargs to make them JSON serializable
        serializable_args = tuple(list(arg) if isinstance(arg, set) else arg for arg in args[1:])
        serializable_kwargs = {k: (list(v) if isinstance(v, set) else v) for k, v in kwargs.items()}
        
        key = json.dumps(serializable_args) + json.dumps(serializable_kwargs)
        if key in CACHE:
            return CACHE[key]
        result = await func(*args, **kwargs)
        CACHE[key] = result
        return result
    return wrapper

def load_exclusion_list(filename: str) -> Set[str]:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

@cached
async def fetch_repo_files(session: aiohttp.ClientSession, repo_full_name: str, exclusion_set: Set[str]) -> Set[str]:
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/main?recursive=1"
    async with session.get(url, headers=HEADERS) as response:
        bucket.consume()
        if response.status == 200:
            data = await response.json()
            return {item["path"] for item in data.get("tree", []) 
                    if item["type"] == "blob" and not any(exclusion in item["path"] for exclusion in exclusion_set)}
        elif response.status == 403:
            reset_time = response.headers.get("X-RateLimit-Reset")
            if reset_time:
                reset_time = int(reset_time) - int(time.time())
                logger.warning(f"Rate limit exceeded. Waiting for {reset_time} seconds.")
                await asyncio.sleep(reset_time)
            return await fetch_repo_files(session, repo_full_name, exclusion_set)
        else:
            logger.error(f"Failed to fetch repo files for {repo_full_name}. Status: {response.status}")
    return set()

@cached
async def fetch_file_content(session: aiohttp.ClientSession, repo_full_name: str, path: str) -> str:
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    async with session.get(url, headers=HEADERS) as response:
        bucket.consume()
        if response.status == 200:
            try:
                data = await response.json()
                encoded_content = data.get('content')
                return base64.b64decode(encoded_content).decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"Skipping binary or non-UTF-8 file: {path}")
        else:
            logger.error(f"Failed to fetch content for {path}. Status: {response.status}")
    return None

async def fetch_and_save_files(repo_full_name: str, exclusion_set: Set[str], concurrency: int = 5):
    remaining_requests, reset_time = check_rate_limit(HEADERS)
    if remaining_requests < 10:
        await asyncio.sleep(max(reset_time - int(time.time()), 0) + 1)

    async with aiohttp.ClientSession() as session:
        files = await fetch_repo_files(session, repo_full_name, exclusion_set)

        semaphore = asyncio.Semaphore(concurrency)
        tasks = [fetch_file_content_with_semaphore(session, repo_full_name, path, semaphore) for path in files]
        contents = await async_tqdm.gather(*tasks, desc=Fore.YELLOW + "Fetching files" + Style.RESET_ALL)

    contents = [content for content in contents if content]

    repo_name = repo_full_name.split('/')[-1]
    save_path = os.path.join(SAVE_DIRECTORY, f"{repo_name}.txt")
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    
    # Asynchronously write the contents to the file
    await async_io.write_files_async(save_path, contents)
    logger.info(f"All files saved in: {save_path}")

async def fetch_file_content_with_semaphore(session, repo_full_name, path, semaphore):
    async with semaphore:
        return await fetch_file_content(session, repo_full_name, path)

def parse_arguments() -> Namespace:
    parser = ArgumentParser(description="Fetch and save all files from a GitHub repository.")
    parser.add_argument("repo_url", help="The GitHub repository URL")
    parser.add_argument("-o", "--output", default=SAVE_DIRECTORY, help="The directory to save files to")
    parser.add_argument("-e", "--exclude", default="exclusion_list.txt", help="File with list of paths to exclude")
    parser.add_argument("-c", "--concurrency", type=int, default=5, help="Number of concurrent tasks")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate the process without saving files")
    return parser.parse_args()

def main():
    args = parse_arguments()

    global SAVE_DIRECTORY
    SAVE_DIRECTORY = args.output

    global EXCLUSION_SET
    EXCLUSION_SET = load_exclusion_list(args.exclude)

    repo_full_name = '/'.join(args.repo_url.rstrip('/').split('/')[-2:])

    if not EXCLUSION_SET:
        logger.warning("No exclusion list found or it's empty. Skipping exclusion step.")
        combined_exclusion_set = set()
    else:
        exclusion_list = list(EXCLUSION_SET)
        print("\nSelect the items you want to exclude from the list below (enter the corresponding numbers separated by spaces):")
        for idx, item in enumerate(exclusion_list, start=1):
            print(f"{idx}. {item}")

        selected_indices = input(Fore.YELLOW + "\nEnter your choices (e.g., 1 3 5): " + Style.RESET_ALL).split()
        selected_exclusions = {exclusion_list[int(idx) - 1] for idx in selected_indices}

        combined_exclusion_set = EXCLUSION_SET.union(selected_exclusions)

    if args.dry_run:
        logger.info("Dry run complete. No files were saved.")
    else:
        print(Fore.BLUE + "Fetching files, please wait..." + Style.RESET_ALL)
        asyncio.run(fetch_and_save_files(repo_full_name, combined_exclusion_set, args.concurrency))
        print(Fore.GREEN + "All operations completed successfully!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
