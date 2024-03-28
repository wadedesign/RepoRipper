import os
import requests
import base64
from dotenv import load_dotenv
from tqdm import tqdm
import time
from colorama import init, Fore, Style

init()

load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
SAVE_DIRECTORY = os.environ.get('SAVE_DIRECTORY', '.')

headers = {"Authorization": f"token {GITHUB_TOKEN}"}

with open('exclusion_list.txt', 'r') as f:
    ALL_EXCLUSION_LIST = [line.strip() for line in f.readlines()]

def get_repo_files(_repo_full_name_, exclusion_list):
    """Recursively fetch all file paths in a repository, excluding files specified in the exclusion list."""
    files = []
    url = f"https://api.github.com/repos/{_repo_full_name_}/git/trees/main?recursive=1"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        tree = resp.json().get("tree", [])
        files = [item["path"] for item in tree if item["type"] == "blob" and all(exclusion not in item["path"] for exclusion in exclusion_list)]
    return files

def fetch_and_save_files(_repo_full_name_, exclusion_list):
    """Fetch files' content from a repo, attempt to decode from Base64, then save it in a single text file."""
    files = get_repo_files(_repo_full_name_, exclusion_list)
    contents = []
    for path in tqdm(files, desc=Fore.YELLOW + "Fetching files" + Style.RESET_ALL, unit="file"):
        url = f"https://api.github.com/repos/{_repo_full_name_}/contents/{path}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            encoded_content = resp.json()['content']
            try:
                decoded_content = base64.b64decode(encoded_content).decode('utf-8')
                contents.append(f"{Fore.GREEN}Path: {path}{Style.RESET_ALL}\n\n{decoded_content}\n\n---\n")
            except UnicodeDecodeError:
                print(f"{Fore.RED}Skipping binary or non-UTF-8 file: {path}{Style.RESET_ALL}")
                continue

    repo_name = _repo_full_name_.split('/')[-1]
    if not os.path.isdir(SAVE_DIRECTORY):
        os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    save_path = os.path.join(SAVE_DIRECTORY, f"{repo_name}.txt")

    with open(save_path, "w") as file:
        file.writelines(contents)

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

    animation = "|/-\\"
    idx = 0
    while True:
        fetch_and_save_files(repo_full_name, exclusion_list)
        if not os.path.exists(os.path.join(SAVE_DIRECTORY, f"{repo_full_name.split('/')[-1]}.txt")):
            print(Fore.CYAN + ".", end="", flush=True)
            idx = (idx + 1) % len(animation)
            print(f"\r{animation[idx]}", end="", flush=True)
            time.sleep(0.1)
        else:
            break

if __name__ == "__main__":
    main()