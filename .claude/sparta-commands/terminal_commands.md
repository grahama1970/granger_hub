/ncdu
Description: Find out what's taking up so much space on your hard drive. Visual and interactive, allowing deletion and drilling down into folders. (Better than df and du).
Arguments: None explicitly mentioned, but it operates on the current or specified directory.

/df
Description: Shows drive usage. (Mentioned as a precursor to `duff`).
Arguments: None specified in this context.

/du
Description: Shows disk usage. (Mentioned as a precursor to `ncdu`).
Arguments: None specified in this context.

/duff
Description: A prettier version of `df`. Shows drive usage in a nicer visual format.
Arguments: None specified.

/rg [pattern] [path]
Description: Like `grep` but faster (powered by Rust). Used for searching text in files.
Examples:
  `/rg 'error'` - Quickly find errors in logs.
  `/rg 'def ' --type py` - Find all Python functions.
  `/rg 'API_KEY'` - Find files that mention an API key.
Arguments: `[pattern]`, `[path]`, can include flags like `--type`.

/mosh [user]@[server_address]
Description: Like SSH, but supports roaming and keeps your session open even if your connection drops or changes (e.g., Wi-Fi to cellular). Requires Mosh to be installed on both client and server.
Arguments: `[user]@[server_address]`

/lshw
Description: Shows detailed information about hardware resources in the system.
Arguments:
  `-c [class]` - Filter by hardware class.
Examples:
  `/lshw -c cpu` - Show CPU info.
  `/lshw -c memory` - Show memory info.
  `/lshw -c network` - Show network interface info.
  `/lshw -c disk` - Show disk info.

/mtr [host]
Description: A combination of `ping` and `traceroute`. Tracks latency and packet loss hop-by-hop live.
Arguments: `[host]`

/fd [search_term]
Description: Like `find`, but often faster and with better default settings (recursive search, case-insensitive, ignores hidden files, colorized output).
Arguments: `[search_term]`

/fzf
Description: FuzzyFinder, an interactive filter for any list or piped input. Allows searching through lists.
Examples:
  `history | /fzf` - Search through command history.
  `ps aux | /fzf | awk '{print $2}' | xargs kill -9` - Interactively find and kill a running process.
Arguments: Typically used with piped input.

/ranger
Description: A terminal-based file manager with a GUI-like interface, Vim keybindings, bulk rename capabilities, and file previews.
Arguments: None specified to launch.

/z [directory_name_fragment]
Description: A "smarter" `cd` command (e.g., Zoxide). Learns frequent and recently used directories and allows quick navigation using partial names.
Examples:
  `/z downloads` - Navigate to a directory whose path includes "downloads" based on usage history.
Arguments: `[directory_name_fragment]`

/zi
Description: An extension of `zoxide` (or similar tool like `z`) that uses `fzf` to interactively select a directory to navigate to from your frequently used directories.
Arguments: None.

/exa
Description: A modern replacement for `ls` with better color-coding, built-in tree view, and icon support.
Arguments:
  `--tree` - Display files in a tree structure.
  `--icons` - Show icons next to file and directory names.
Examples:
  `/exa`
  `/exa --tree`
  `/exa --icons`

/glances
Description: An all-in-one system monitoring dashboard showing CPU, RAM, disk, network, etc., at a glance.
Arguments:
  `-w` - Run as a web server.
  (Implied) Can run an API for remote monitoring.

/iotop
Description: Displays a top-style list of processes using the most disk I/O, updating in real-time. Helps identify what's stressing your disks. Requires sudo.
Arguments: None specified.

/stat [file_name]
Description: Shows detailed information about a file or filesystem, including inode number, birth date, etc.
Arguments: `[file_name]`
  `-f` - Show file system-specific information.
Examples:
  `/stat [file_name]`
  `/stat -f [file_name]`

/dstat
Description: A versatile tool for generating system resource statistics. Combines aspects of `vmstat`, `iostat`, `ifstat`, and `netstat`. Shows CPU, RAM, disk, network, memory in a combined timeline view.
Arguments:
  `--top-cpu` - Show the process using the most CPU.
Examples:
  `/dstat`
  `/dstat --top-cpu`

/watch [options] [command_string]
Description: Reruns a specified command at regular intervals, displaying its output.
Arguments: `[options]` (e.g., `-n [seconds]`), `"[command_string]"` (the command to run, often needs quotes if it has spaces or special characters).
Examples:
  `/watch -n 0.5 "nvidia-smi"` - Monitor GPU by running `nvidia-smi` every half a second.

/progress
Description: Monitors the progress of coreutils commands like `cp`, `mv`, `dd`, `tar`, `gzip`, `cat`, etc., that are currently running. Can monitor multiple commands. (Requires `progress` to be installed: `sudo apt install progress`).
Arguments: None specified for basic invocation, it finds running commands.

/dig [domain_name]
Description: A DNS lookup utility. (Mentioned as older/messier than `dog`).
Arguments: `[domain_name]`

/dog [domain_name]
Description: A prettier and more user-friendly DNS lookup utility than `dig`, with colored output, DNS over TLS support, and JSON output.
Arguments: `[domain_name]`
  `--tls` - Perform DNS lookup over TLS.
  `--json` - Output in JSON format.
Examples:
  `/dog example.com`
  `/dog example.com --tls`
  `/dog example.com --json`

/tcpdump
Description: A command-line packet analyzer. Requires sudo.
Arguments: Varies widely based on capture needs (e.g., `tcpdump -i eth0 -n port 80`).

/tshark
Description: A terminal-based version of Wireshark. Often requires sudo for live capture.
Arguments: Varies widely.

/termshark
Description: A terminal user interface for `tshark`, allowing interactive packet sniffing and analysis in the terminal, with mouse support. Often requires sudo for live capture.
Arguments:
  `-r [pcap_file]` - Load a pcap file for examination.
Examples:
  `/termshark` (for live capture)
  `/termshark -r capture.pcap`
  (Within termshark) `dns` (as a display filter)

/lsof -i :[port_number]
Description: Lists open files, and with the `-i` option, shows processes using specific internet ports or all active network connections.
Arguments: `-i :[port_number]` (to show processes for a specific port) or `-i` (to show all network connections).
Examples:
  `/lsof -i :22` - Show process using port 22.
  `/lsof -i :80` - Show process using port 80.
  `/lsof -i -P -n` - Show all network connections without resolving hostnames or port numbers.

/ipcalc [ip_address]/[cidr]
Description: A command-line subnet calculator. Provides network information like range, mask, wildcard info from an IP address and CIDR notation. (Requires `ipcalc` to be installed).
Arguments: `[ip_address]/[cidr]`
Examples:
  `/ipcalc 10.7.8.94/18`

/wormhole send [file_name]
Description: Initiates a peer-to-peer, end-to-end encrypted file transfer. Generates a code to be used by the receiver. (Requires `magic-wormhole` to be installed).
Arguments: `send [file_name]`

/wormhole receive [code]
Description: Receives a file sent via `wormhole send` using the provided code. (Requires `magic-wormhole` to be installed).
Arguments: `receive [code]`

/systemd-analyze blame
Description: Shows which systemd services took the longest to start up during the last boot.
Arguments: `blame`

/systemd-analyze critical-chain
Description: Highlights the critical path of dependencies during boot, helping to understand bottlenecks caused by sequential initialization.
Arguments: `critical-chain [optional_unit_name]`

/ps
Description: Lists currently running processes. (Mentioned as older/lamer than `procs`).
Arguments: Varies, e.g., `aux`, `ef`.

/procs
Description: A prettier, more friendly, and modern replacement for `ps`. (Requires `procs` to be installed).
Arguments:
  `--sort cpu` - Sort processes by CPU usage.
  `--tree` - View processes in a tree structure.
Examples:
  `/procs`
  `/procs --sort cpu`
  `/procs --tree`

/lazydocker
Description: A terminal user interface for managing Docker containers and services. Provides an interactive way to perform Docker operations. (Requires `lazydocker` to be installed).
Arguments: None to launch.

/rsync [options] [source] [destination]
Description: A utility for efficiently transferring and synchronizing files. It's smart (delta only, syncing differences), can resume broken transfers, and mirrors over SSH.
Arguments: `[options]`, `[source]`, `[destination]`
Example: `/rsync -avz --progress ./local_dir/ user@remote_host:/remote_dir/`

/rm [file_name]
Description: Removes (unlinks) files from the file system. (Mentioned that it doesn't truly erase data immediately). Use with caution.
Arguments: `[file_name]`

/shred [file_name]
Description: Securely deletes a file by overwriting it multiple times before deletion, making data recovery difficult. Use with caution.
Arguments: `[file_name]`

/ts
Description: (Part of `moreutils`) Adds timestamps to standard input. (Requires `moreutils` to be installed: `sudo apt install moreutils`).
Arguments: None specified, used in a pipe. `[command] | /ts`

/errno [error_number]
Description: (Part of `moreutils`) Displays the descriptive name for a system error number. (Requires `moreutils` to be installed).
Arguments: `[error_number]`

/ifdata [options] [interface]
Description: (Part of `moreutils`) A simpler way to look at network interface information, providing cleaner output than tools like `ip addr` or `ifconfig`. (Requires `moreutils` to be installed).
Arguments: `[options]`, `[interface]` (e.g., `ifdata -pa eth0` for primary IP).

/vidir [directory_path]
Description: (Part of `moreutils`) Allows editing directory names (and filenames within) using a text editor. Use with extreme caution. (Requires `moreutils` to be installed).
Arguments: Optional `[directory_path]`. If no path, current directory is used.

/vip
Description: (Part of `moreutils`) Allows inserting a text editor ($VISUAL or $EDITOR) into a Unix command pipeline to edit the data being piped between programs. (Requires `moreutils` to be installed).
Arguments: None specified, used in a pipe. `[command1] | /vip | [command2]`

/unp [archive_file]
Description: (Part of `moreutils` or a standalone tool like `unar`) Unpacks various types of archive files (zip, tar.gz, rar, etc.) by automatically guessing the correct unpack command. (Requires `unp` or `unar` to be installed).
Arguments: `[archive_file]`

/jq [filter_expression] [json_file_or_pipe]
Description: A command-line JSON processor. Used to query, filter, and transform JSON data.
Arguments: `[filter_expression]` (a jq expression, often in quotes), `[json_file_or_pipe]` (optional, reads from stdin if omitted).
Examples:
  `cat data.json | /jq '.key.subkey'`
  `/jq '.items[] | select(.name=="example")' data.json`

/task add [task_description]
Description: (Taskwarrior) Adds a new task to the task list. (Requires `taskwarrior` to be installed).
Arguments: `add [task_description]`

/task list
Description: (Taskwarrior) Lists all current tasks. (Requires `taskwarrior` to be installed).
Arguments: `list`

/task [task_id] done
Description: (Taskwarrior) Marks a specific task as done. (Requires `taskwarrior` to be installed).
Arguments: `[task_id] done`

/asciinema rec [optional_filename.cast]
Description: Records terminal sessions into small, text-based "cast" files. (Requires `asciinema` to be installed).
Arguments: `rec [optional_filename.cast]` (If no filename, prompts after.)
Example: `/asciinema rec my_session.cast` then `exit` or `Ctrl+D` to stop.

/asciinema play [cast_file]
Description: Plays back a recorded terminal session from a .cast file in the terminal. (Requires `asciinema` to be installed).
Arguments: `[cast_file]`
Example: `/asciinema play my_session.cast`

/asciinema auth
Description: Authenticates with an asciinema server (e.g., asciinema.org or self-hosted) to allow uploading recordings. (Requires `asciinema` to be installed).
Arguments: None.

/asciinema upload [cast_file]
Description: Uploads a recorded .cast file to an asciinema server. (Requires `asciinema` to be installed).
Arguments: `[cast_file]`

/asciinema cat [cast_file] > [output_file.gif]
Description: (Using `asciicast2gif` or similar tool often used with asciinema, though the video calls it `asciinema cat` for this purpose) Converts a .cast file into an animated GIF. The video mentions "ask cinema a" (asciinema-agg) or a similar tool for conversion. (Requires `asciicast2gif` or `agg` to be installed).
Arguments: `[cast_file]` redirected to `[output_file.gif]`.
Example: `agg my_session.cast my_session.gif` or `asciicast2gif my_session.cast -o my_session.gif`

---
### AI-Assisted Commands & LLM Interaction

/fabric -p "[prompt]" [context_or_pipe]
Description: (If `fabric` CLI by Daniel Miessler is installed) A CLI tool to interact with AI models (like Claude, GPT) using patterns. Can process piped input or be given prompts directly.
Arguments: `-p "[prompt]"`
Examples:
  `history | /fabric -p "summarize my most used commands"`
  `lsof -i | /fabric -p "analyze open ports and give recommendations"`
  `cat /var/log/syslog | /fabric -p "analyze this syslog"`

/ollama create [agent_name] -f [Modelfile_content_or_path]
Description: Creates a custom Ollama model (agent) with specific instructions, typically defined in a Modelfile. Requires Ollama to be running.
Arguments:
  `[agent_name]`: Name for your custom model.
  `-f [Modelfile_content_or_path]`: Path to the Modelfile or the Modelfile content itself.
Example: `/ollama create my-command-builder -f ./ModelfileForBuilder`

/ollama run [agent_name] "[prompt_for_model]"
Description: Runs a prompt against a locally served Ollama model/agent. Requires Ollama to be running.
Arguments:
  `[agent_name]`: Name of the Ollama model to run.
  `"[prompt_for_model]"`: The prompt to send to the model.
Examples:
  `/ollama run llama3 "Explain the concept of recursion in Python with an example."`
  `/ollama run my-command-builder "Create a command to find files larger than 1GB"`

/cmdcraft "[natural_language_query]" [ollama_model_name]
Description: (Requires `_ollama_craft_command` function and `cmdcraft` alias in `.zshrc` as described above) Uses a local Ollama model to generate a Linux terminal command based on your natural language query. Outputs the suggested command directly.
Arguments:
  `"[natural_language_query]"`: Your request for a command, in plain English.
  `[ollama_model_name]` (optional): Specify the Ollama model to use (e.g., `codellama`, `llama3`). Defaults to a pre-configured model in the alias (e.g., `codellama:latest`).
Example: `/cmdcraft "find all files over 100MB in my home directory"`
Example: `/cmdcraft "list all running docker containers" llama3`

---
### Additional Ubuntu/LLM Agent Utility Commands

/cat_file [filepath]
Description: Display the entire content of a specific file. Essential for providing full context of a script, configuration, or document to an LLM.
Example: `/cat_file src/my_module.py`

/head_file [filepath] [number_of_lines]
Description: Display the first N lines of a file. Useful for quickly showing the beginning of a large file, like imports and initial declarations, to an LLM.
Arguments:
  `[filepath]`: Path to the file.
  `[number_of_lines]` (optional, default typically 10): Number of lines to display.
Example: `/head_file logs/app.log 20`

/tail_file [filepath] [number_of_lines]
Description: Display the last N lines of a file. Very useful for checking recent log entries, errors, or the end of a data file for LLM analysis.
Arguments:
  `[filepath]`: Path to the file.
  `[number_of_lines]` (optional, default typically 10): Number of lines to display.
Example: `/tail_file /var/log/syslog 50`

/cloc_report [target_path]
Description: (Requires `cloc` to be installed: `sudo apt install cloc`) Count Lines of Code, blank lines, and comment lines for various programming languages within a specified file or directory. Useful for providing codebase scale and composition context to an LLM.
Arguments: `[target_path]`: Path to the file or directory to analyze.
Example: `/cloc_report ./my_project_dir`

/git_current_status
Description: (Assumes a Git repository) Show the working tree status (modified files, staged changes, untracked files). Crucial for an LLM to understand the current state of a project.
Arguments: None.
Example: `/git_current_status`

/git_recent_commits [count] [--oneline]
Description: (Assumes a Git repository) Display the most recent commits. Helps an LLM track recent changes or understand project history.
Arguments:
  `[count]` (optional, default typically 5-10): Number of recent commits to show.
  `--oneline` (optional): For a compact, one-line-per-commit view.
Example: `/git_recent_commits 5 --oneline`

/git_show_diff [file_or_commit]
Description: (Assumes a Git repository) Show changes. Can show unstaged changes for a file, changes for a specific commit, or differences between branches. Essential for an LLM to review specific code changes.
Arguments: `[file_or_commit]` (optional): If a file path, shows unstaged changes for that file. If a commit hash, shows changes for that commit. If blank, shows all unstaged changes. Can also be `branch1..branch2`.
Example: `/git_show_diff src/utils.js` or `/git_show_diff HEAD~1` or `/git_show_diff main..develop`

/git_current_branch
Description: (Assumes a Git repository) Display the currently checked-out Git branch. Provides context to an LLM about the current working branch.
Arguments: None.
Example: `/git_current_branch`

/execute_python_script [script_path] [script_arguments]
Description: Execute a Python script. Useful for an LLM to suggest running or for you to test code it generated.
Arguments:
  `[script_path]`: Path to the Python script.
  `[script_arguments]` (optional): Arguments to pass to the Python script.
Example: `python3 /execute_python_script scripts/process_data.py --input data.csv --output results.json` (Note: Command is `python3` or `python`, then the script path)

/execute_bash_script [script_path] [script_arguments]
Description: Execute a shell (Bash) script. Useful for an LLM to suggest running automation scripts or setup tasks.
Arguments:
  `[script_path]`: Path to the Bash script.
  `[script_arguments]` (optional): Arguments to pass to the Bash script.
Example: `bash /execute_bash_script ./deploy.sh production` (Note: Command is `bash` or `sh`, then the script path)

/run_make [target]
Description: (Assumes a Makefile exists) Execute a specific target in a Makefile. LLM can use this for build, test, or deploy instructions.
Arguments: `[target]` (optional): The Makefile target to run (e.g., `build`, `test`, `clean`). If empty, typically runs the default target.
Example: `/run_make build`

/run_pytest [path_to_tests_or_options]
Description: (Requires `pytest` to be installed) Run Python tests using pytest. An LLM can suggest running this to verify code functionality.
Arguments: `[path_to_tests_or_options]` (optional): Specific file, directory, or pytest options (e.g., `-k "test_my_function"`). If empty, pytest usually discovers tests.
Example: `/run_pytest tests/unit/ -v`

/show_env_var [variable_name]
Description: Display the value of a specific environment variable using `printenv [variable_name]`. If no variable name is given, `env` lists all. Provides LLM with environment context.
Arguments: `[variable_name]` (optional): The name of the environment variable.
Example: `/show_env_var PATH` or `env`

/check_process [process_name_pattern]
Description: Check if a process matching a given name or pattern is running using `ps aux | grep [pattern]`. Useful for an LLM to diagnose if a service is active.
Arguments: `[process_name_pattern]`: The pattern to search for in process list. Remember to exclude the grep command itself (e.g., `ps aux | grep '[n]ginx'`).
Example: `/check_process '[a]pache'`

/disk_usage_summary [path]
Description: Show disk usage for a given path (e.g., using `df -h [path]` for filesystem or `du -sh [path]` for directory). Helps LLM diagnose space issues.
Arguments: `[path]` (optional, default current directory for `du` or all filesystems for `df`).
Example: `/disk_usage_summary /var/log` or `du -sh .`

/memory_usage_summary
Description: Display current system memory usage (e.g., using `free -h`). Gives LLM context on system resources.
Arguments: None.
Example: `/memory_usage_summary`

/fetch_url_content [URL] [curl_options]
Description: (Uses `curl`) Fetch content from a URL. Can be used by an LLM to instruct getting data from APIs or web pages.
Arguments:
  `[URL]`: The URL to fetch.
  `[curl_options]` (optional): Curl options (e.g., `-sL` for silent and follow redirects, `-H "Header: Value"` for custom headers).
Example: `/fetch_url_content https://api.example.com/data -sL -H "Accept: application/json"`

/search_text_files "[pattern]" [path_or_glob] [grep_rg_options]
Description: Search for a text pattern within files (e.g., using `grep -R` or `rg`). Useful for an LLM to locate specific code, configurations, or log entries.
Arguments:
  `"[pattern]"`: The text pattern to search for (can be a regex).
  `[path_or_glob]`: The directory or file glob pattern to search within (e.g., `src/`, `*.py`).
  `[grep_rg_options]` (optional): Additional options for grep or rg (e.g., `-i` for case-insensitive, `--context=5`).
Example: `/search_text_files "my_api_key" . --exclude-dir=node_modules -i` (example uses `rg` style options)

/copy_to_clipboard [text_or_command_output]
Description: (Requires `xclip` or `wl-copy` for Wayland: `sudo apt install xclip` or `wl-copy`) Copies the given text or the output of a command to the system clipboard. Useful for getting information from terminal to GUI for an LLM prompt.
Arguments: Text to copy, or a command whose output should be copied (via pipe).
Example: `cat my_file.txt | xclip -selection clipboard` or `echo "important text" | wl-copy`

/paste_from_clipboard
Description: (Requires `xclip` or `wl-paste` for Wayland) Pastes content from the system clipboard to stdout. Useful for quickly getting clipboard content into the terminal to use with other commands or to send to an LLM.
Arguments: None.
Example: `xclip -o -selection clipboard > from_clipboard.txt` or `wl-paste`

### Installation for packages
Run the shell script
```.claude/sparta-commands/terminal_commands_preflight.sh```

---
### SPARTA-Specific Report Commands

/report
Description: Generate a beautiful HTML report from test results
Arguments: None
```bash
pytest tests/ --html=reports/test_results.html --self-contained-html --cov=src/sparta --cov-report=html
python -m http.server 8000 --directory reports/
```
Open http://localhost:8000/test_results.html

/test-report
Description: Run tests and immediately serve HTML report
Arguments: None
```bash
pytest tests/ --html=reports/test_report.html --self-contained-html && \
echo "Opening report at http://localhost:8000/test_report.html" && \
python -m http.server 8000 --directory reports/
```

/coverage
Description: Generate and serve coverage report
Arguments: None
```bash
pytest tests/ --cov=src/sparta --cov-report=html:reports/coverage --cov-report=term && \
echo "Coverage report at http://localhost:8000/coverage/" && \
python -m http.server 8000 --directory reports/
```

/serve-reports
Description: Start report server on configured IP
Arguments: None
```bash
cd reports && python -m http.server 8 --bind 192.168.86.49
```
Reports available at http://192.168.86.49:8/

/pipeline
Description: Run complete SPARTA pipeline with reports
Arguments: None
```bash
# 1. Run tests
pytest tests/ --html=reports/test_report.html --json-report

# 2. Run SPARTA download
python scripts/run_enhanced_sparta_download.py

# 3. Generate download report
python -c "
from src.sparta.reports.universal_report_generator import UniversalReportGenerator
from src.sparta.reports.report_config import get_report_config
import json

# Load download results
with open('sparta_enhanced_download/download_results.json', 'r') as f:
    results = json.load(f)

# Generate report
config = get_report_config('sparta')
generator = UniversalReportGenerator(**config)
report_file = generator.generate(results, 'reports/download_report.html')
print(f'Report: {report_file}')
"

# 4. Serve all reports
python -m http.server 8000 --directory reports/
```

/full-check
Description: Complete check with reports
Arguments: None
```bash
# Type check
mypy src/ --html-report reports/mypy

# Lint
ruff check src/ > reports/ruff_report.txt

# Tests with coverage
pytest tests/ \
  --html=reports/test_report.html \
  --cov=src/sparta \
  --cov-report=html:reports/coverage \
  --json-report \
  --json-report-file=reports/test_results.json

# Generate summary report
python scripts/generate_summary_report.py 2>/dev/null || echo "Summary script not found"

# Serve all reports
echo "All reports available at http://localhost:8000/"
python -m http.server 8000 --directory reports/
```