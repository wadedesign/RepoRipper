##  RepoRipper

This repository contains a Python script, RepoRipper.py, downloads your whole git repo to a .txt file so you can share it with any AI model (works best with Openai [^1]  and Gemini [^2] )

> [!CAUTION]
> Be aware that large repositories may encounter rate limits when using this script due to GitHub API restrictions. This is an inherent limitation and not a fault of the script itself.

**Requirements:**

* Python 3
* `requests` library
* `base64` library
* `dotenv` library
* `tqdm` library
* `colorama` library

**Setup:**

1. **Create a `.env` file:**
   - In the same directory as the script, create a file named `.env`.
   - Add the following line to the file, replacing the placeholder with your actual GitHub personal access token:

     ```
     GITHUB_TOKEN=your_github_token
     ```

2. **Install dependencies:**
   - Open a terminal in the script's directory and run the following command:

     ```bash
     pip install requests base64 dotenv tqdm colorama
     ```

**Usage:**

1. **Run the script:**
   - Execute the script using:

     ```bash
     python RepoRipper.py
     ```

2. **Enter repository URL:**
   - When prompted, provide the URL of the GitHub repository you want to download from.

3. **Select exclusions (optional):**
   - The script will display a list of file types and directories that can be excluded.
   - Enter the corresponding numbers separated by spaces to exclude specific items.
   - Press Enter to proceed without exclusions.

4. **Wait for download:**
   - The script will fetch the files and save them to a single text file in the current directory or the specified `SAVE_DIRECTORY` in the `.env` file.

**Customization:**

* You can modify the `exclusion_list.txt` file to add or remove file types and directories to be excluded by default.
* You can set the `SAVE_DIRECTORY` environment variable in the `.env` file to specify where the downloaded text file should be saved.

**Note:**

* Make sure your GitHub personal access token has the necessary permissions to access the repository.
* The script will skip binary or non-UTF-8 files.
* The script will overwrite any existing file with the same name in the save directory.











[^1]: My reference.
[^2]: To add line breaks within a footnote, prefix new lines with 2 spaces.
  This is a second line.