import asyncio
import os
import requests
import base64
from dotenv import load_dotenv
from utils.rate_limiting import check_rate_limit
from tqdm import tqdm
import time
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools
from utils import async_io


init()
load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
SAVE_DIRECTORY = os.environ.get('SAVE_DIRECTORY', '.')
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

with open('exclusion_list.txt', 'r') as f:
    ALL_EXCLUSION_LIST = [line.strip() for line in f.readlines()]
    EXCLUSION_SET = set(ALL_EXCLUSION_LIST)

def get_repo_files(_repo_full_name_, _exclusion_list_):
    """Recursively fetch all file paths in a repository, excluding files specified in the exclusion list."""
    files = []
    url = f"https://api.github.com/repos/{_repo_full_name_}/git/trees/main?recursive=1"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        tree = resp.json().get("tree", [])
        files = [item["path"] for item in tree if item["type"] == "blob" and not any(exclusion in item["path"] for exclusion in _exclusion_list_)]
    return files

def fetch_file_content(_repo_full_name_, path):
    url = f"https://api.github.com/repos/{_repo_full_name_}/contents/{path}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        encoded_content = resp.json()['content']
        try:
            decoded_content = base64.b64decode(encoded_content).decode('utf-8')
            return f"{Fore.GREEN}Path: {path}{Style.RESET_ALL}\n\n{decoded_content}\n\n---\n"
        except UnicodeDecodeError:
            print(f"{Fore.RED}Skipping binary or non-UTF-8 file: {path}{Style.RESET_ALL}")
    return None

async def fetch_and_save_files(_repo_full_name_, _exclusion_list_):
    """Fetch files' content from a repo, attempt to decode from Base64, then save it in a single text file."""
    remaining_requests, reset_time = check_rate_limit(headers)
    if remaining_requests < 10:
        reset_wait_time = reset_time - int(time.time())
        print(f"Approaching GitHub API rate limit. Waiting for reset in {reset_wait_time} seconds.")
        time.sleep(max(reset_wait_time, 0) + 1)

    files = get_repo_files(_repo_full_name_, _exclusion_list_)

    with ThreadPoolExecutor() as executor:
        fetch_tasks = [executor.submit(fetch_file_content, _repo_full_name_, path) for path in files]
        contents = [future.result() for future in tqdm(as_completed(fetch_tasks), total=len(files), desc=Fore.YELLOW + "Fetching files" + Style.RESET_ALL, unit="file")]

    contents = [content for content in contents if content is not None]

    repo_name = _repo_full_name_.split('/')[-1]
    if not os.path.isdir(SAVE_DIRECTORY):
        os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    save_path = os.path.join(SAVE_DIRECTORY, f"{repo_name}.txt")

    await async_io.write_files_async(save_path, contents)

    print(f"{Fore.GREEN}All files saved in: {save_path}{Style.RESET_ALL}")

def main():
    repo_url = input(Fore.YELLOW + "Enter the GitHub repository URL: " + Style.RESET_ALL)
    repo_full_name = '/'.join(repo_url.split('/')[-2:])

    print("\nSelect the items you want to exclude from the list below (enter the corresponding numbers separated by spaces):")
    for idx, item in enumerate(ALL_EXCLUSION_LIST, start=1):
        print(f"{idx}. {item}")

    selected_indices = input(Fore.YELLOW + "\nEnter your choices (e.g., 1 3 5): " + Style.RESET_ALL).split()
    exclusion_list = [ALL_EXCLUSION_LIST[int(idx) - 1] for idx in selected_indices]

    print(Fore.BLUE + "Fetching files, please wait..." + Style.RESET_ALL)
    with tqdm(total=100, desc=Fore.BLUE + "Processing", bar_format="{desc}: |{bar}| {percentage:3.0f}%", leave=False) as pbar:
        for _ in range(100):
            time.sleep(0.02) 
            pbar.update(1)

    asyncio.run(fetch_and_save_files(repo_full_name, exclusion_list)), 
    print(Fore.GREEN + "All operations completed successfully!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()