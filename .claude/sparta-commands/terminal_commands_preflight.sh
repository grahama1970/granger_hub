#!/bin/bash

echo "Checking package availability and versions..."
echo "---------------------------------------------"

# Define a function to install missing packages
install_missing_package() {
  local cmd_name="$1"
  local pretty_name="${2:-$cmd_name}"

  echo "Attempting to install $pretty_name..."

  case "$cmd_name" in
    "termshark")
      if sudo apt update && sudo apt install -y termshark; then
        echo "$pretty_name installed successfully."
      else
        echo "Failed to install $pretty_name using apt. Trying manual installation..."
        wget https://github.com/gcla/termshark/releases/download/v2.4.0/termshark_2.4.0_linux_x64.tar.gz
        if tar -xzf termshark_2.4.0_linux_x64.tar.gz && sudo mv termshark_2.4.0_linux_x64/termshark /usr/local/bin/ && rm -rf termshark_2.4.0_linux_x64.tar.gz termshark_2.4.0_linux_x64; then
          echo "$pretty_name installed successfully via manual installation."
        else
          echo "Failed to install $pretty_name manually. Please check manually."
        fi
      fi
      ;;
    "unp")
      if sudo apt update && sudo apt install -y unp; then
        echo "$pretty_name installed successfully."
      else
        echo "Failed to install $pretty_name. Please check manually."
      fi
      ;;
    "fabric")
      if pip3 install --user fabric; then
        echo "$pretty_name installed successfully."
      else
        echo "Failed to install $pretty_name. Trying in a virtual environment..."
        python3 -m venv ~/fabric-venv
        source ~/fabric-venv/bin/activate
        if pip install fabric; then
          echo "$pretty_name installed successfully in ~/fabric-venv."
          echo "Activate the virtual environment with 'source ~/fabric-venv/bin/activate' to use fabric."
        else
          echo "Failed to install $pretty_name in virtual environment. Please check manually."
        fi
      fi
      ;;
    "vipe")
      if sudo apt update && sudo apt install -y moreutils; then
        echo "$pretty_name installed successfully."
      else
        echo "Failed to install $pretty_name. Please check manually."
      fi
      ;;
    "lazydocker")
      if curl https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh | bash; then
        echo "$pretty_name installed successfully."
      else
        echo "Failed to install $pretty_name using installation script. Please check manually."
      fi
      ;;
    *)
      echo "No installation method defined for $pretty_name."
      ;;
  esac
}

# Define a function to check a command
check_command() {
  local cmd_name="$1"
  local pretty_name="${2:-$cmd_name}" 
  local version_arg_override="${3}" 

  # Handle cases where the pretty name might be empty if not provided
  if [[ -z "$pretty_name" ]]; then
    pretty_name="$cmd_name"
  fi

  printf "%-28s: " "$pretty_name"

  local actual_cmd_to_run="$cmd_name"
  local cmd_path=""
  local is_missing=false

  # Special handling for fd/fdfind
  if [[ "$cmd_name" == "fd" ]]; then
    if command -v fd &>/dev/null; then
      actual_cmd_to_run="fd"
      cmd_path="$(command -v fd)"
      printf "Installed (Path: %s)" "$cmd_path"
    elif command -v fdfind &>/dev/null; then
      actual_cmd_to_run="fdfind"
      cmd_path="$(command -v fdfind)"
      printf "Found as fdfind (Path: %s)" "$cmd_path"
    else
      printf "NOT INSTALLED or NOT IN PATH\n"
      is_missing=true
    fi
  # Special handling for bat/batcat
  elif [[ "$cmd_name" == "bat" ]]; then
    if command -v bat &>/dev/null; then
      actual_cmd_to_run="bat"
      cmd_path="$(command -v bat)"
      printf "Installed (Path: %s)" "$cmd_path"
    elif command -v batcat &>/dev/null; then
      actual_cmd_to_run="batcat"
      cmd_path="$(command -v batcat)"
      printf "Found as batcat (Path: %s)" "$cmd_path"
    else
      printf "NOT INSTALLED or NOT IN PATH\n"
      is_missing=true
    fi
  # Special handling for fabric/fab
  elif [[ "$cmd_name" == "fabric" ]]; then
    if command -v fab &>/dev/null; then
      actual_cmd_to_run="fab"
      cmd_path="$(command -v fab)"
      printf "Installed (Path: %s)" "$cmd_path"
    else
      printf "NOT INSTALLED or NOT IN PATH\n"
      is_missing=true
    fi
  # General case
  elif command -v "$actual_cmd_to_run" &>/dev/null; then
    cmd_path="$(command -v "$actual_cmd_to_run")"
    printf "Installed (Path: %s)" "$cmd_path"
  else
    printf "NOT INSTALLED or NOT IN PATH\n"
    is_missing=true
  fi

  # Install missing package
  if $is_missing; then
    install_missing_package "$cmd_name" "$pretty_name"
    # Refresh PATH to include ~/.local/bin and /usr/local/bin
    export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
    # Re-check if installed after attempting installation
    if [[ "$cmd_name" == "fabric" ]]; then
      if command -v fab &>/dev/null; then
        actual_cmd_to_run="fab"
        cmd_path="$(command -v fab)"
        printf "Post-install check: Installed (Path: %s)" "$cmd_path"
      else
        printf "Post-install check: Still NOT INSTALLED or NOT IN PATH\n"
        return
      fi
    elif command -v "$actual_cmd_to_run" &>/dev/null; then
      cmd_path="$(command -v "$actual_cmd_to_run")"
      printf "Post-install check: Installed (Path: %s)" "$cmd_path"
    else
      printf "Post-install check: Still NOT INSTALLED or NOT IN PATH\n"
      return
    fi
  fi

  # Attempt to get version
  local version_output="" # Initialize as empty
  local version_found=false
  local err_occurred=false
  local output_and_error="" # To store output from run_version_cmd

  # Helper to run version command and set flags
  run_version_cmd() {
    local cmd_to_exec_str="$1"
    # Clear previous error output
    version_output=""
    output_and_error=""
    
    # Execute command, redirecting stderr to stdout to capture all output
    # Then check exit status
    # Using a subshell to evaluate the command string safely
    if output_and_error=$(eval "$cmd_to_exec_str 2>&1"); then
      version_output="$output_and_error"
      version_found=true
      err_occurred=false
    else
      version_output="$output_and_error" # Store error output
      version_found=false # Explicitly false on error, though can be true if version is in error
      err_occurred=true
      # Check if version info is in the error output for some tools
      if [[ "$version_output" == *version* || "$version_output" == *Version* || "$version_output" == *VERSION* ]]; then
          version_found=true # e.g. mosh-client might put version in stderr
      fi
    fi
  }

  if [[ -n "$version_arg_override" ]]; then
    run_version_cmd "$actual_cmd_to_run $version_arg_override"
  fi

  if ! $version_found; then
    case "$actual_cmd_to_run" in
      "python3"|"pip3"|"ollama"|"lazydocker"|"termshark"|"procs"|"exa"|"zoxide"|\
      "rg"|"fzf"|"cloc"|"jq"|"tree"|"asciinema"|"fab"|"wormhole"|"ipcalc"|\
      "glances"|"dstat"|"ncdu"|"shred"|"unp"|"rsync"|"fdfind"|"batcat"|"bat"|\
      "systemd-analyze"|"wl-copy"|"dog"|"asciinema-agg")
        run_version_cmd "$actual_cmd_to_run --version"
        ;;
      "mosh"|"mosh-client")
        if command -v mosh-client &>/dev/null; then
          run_version_cmd "mosh-client --version"
        elif command -v mosh &>/dev/null; then # Fallback
          run_version_cmd "mosh --version"
        fi
        ;;
      "lshw")
        run_version_cmd "$actual_cmd_to_run -version"
        if $version_found && [[ -n "$version_output" ]]; then version_output=$(echo "$version_output" | grep -i "version" | head -n 1); fi
        ;;
      "mtr"|"dig"|"lsof"|"tshark"|"duff")
        run_version_cmd "$actual_cmd_to_run -v"
        ;;
      "task")
        run_version_cmd "$actual_cmd_to_run --version"
        ;;
      "pytest")
        if command -v pytest &>/dev/null; then
          run_version_cmd "pytest --version"
        else
          version_output="(pytest command not directly in PATH)"
          version_found=false
        fi
        ;;
      "xclip")
        run_version_cmd "xclip -version"
        ;;
      "curl")
        run_version_cmd "$actual_cmd_to_run -V"
        ;;
      "git")
        run_version_cmd "$actual_cmd_to_run --version"
        ;;
    esac
  fi
  
  # Generic fallbacks if specific attempts failed or weren't applicable
  if ! $version_found && ! $err_occurred; then
    run_version_cmd "$actual_cmd_to_run --version"
  fi
  if ! $version_found && ! $err_occurred; then
    run_version_cmd "$actual_cmd_to_run -V"
  fi
  if ! $version_found && ! $err_occurred; then
    run_version_cmd "$actual_cmd_to_run -v"
  fi

  if $version_found && [[ -n "$version_output" ]]; then
    # Clean up common error messages or long outputs, take first line
    # Remove lines that are clearly usage instructions
    version_output=$(echo "$version_output" | grep -v -i "^Usage: " | head -n 1)
    # Remove common error prefixes if they are the only thing on the first line
    version_output=$(echo "$version_output" | sed -e 's/^bash: line [0-9]*: \(.*: \)*command not found$//g' \
                                                 -e 's/^error:.*//gI' \
                                                 -e 's/^Error:.*//gI' \
                                                 -e 's/^[[:space:]]*$//g')
    if [[ -n "$version_output" ]]; then                                             
      printf " | Version: %s\n" "$version_output"
    elif $err_occurred && [[ -n "$output_and_error" ]]; then
      printf " | Error getting version (Output: %s)\n" "$(echo "$output_and_error" | head -n 1)"
    else
      printf " | Version: (Found, but output was empty/cleaned)\n"
    fi
  elif $err_occurred && [[ -n "$version_output" ]] ; then
     printf " | Error getting version (Output: %s)\n" "$(echo "$output_and_error" | head -n 1)"
  else
    # For commands known to lack simple version flags, or if all attempts failed
    if [[ "$actual_cmd_to_run" == "iotop" || "$actual_cmd_to_run" == "ts" || "$actual_cmd_to_run" == "errno" || "$actual_cmd_to_run" == "ifdata" || "$actual_cmd_to_run" == "vidir" || "$actual_cmd_to_run" == "vipe" || "$actual_cmd_to_run" == "ranger" || "$actual_cmd_to_run" == "progress" ]]; then
        printf " | (No simple version flag, but command is present)\n"
    else
        printf " | Version: N/A or specific query needed\n"
    fi
  fi
}

# List of commands to check: "command_binary_name;Pretty Name for display;Optional_specific_version_flag"
commands_to_check_structured=(
  "ncdu"
  "duff"
  "rg;ripgrep (rg)"
  "mosh" 
  "lshw"
  "mtr"
  "fd;fd (or fdfind)" 
  "fzf"
  "ranger"
  "zoxide;z (zoxide)"
  "exa"
  "glances"
  "iotop" 
  "dstat"
  "progress" 
  "dig"
  "dog;dog (DNS client)"
  "tshark"
  "termshark"
  "lsof"
  "ipcalc"
  "wormhole"
  "systemd-analyze"
  "procs"
  "lazydocker"
  "rsync"
  "shred" 
  "ts;ts (moreutils)"
  "errno;errno (moreutils)"
  "ifdata;ifdata (moreutils)"
  "vidir;vidir (moreutils)"
  "vipe;vipe (moreutils)"
  "unp"
  "jq"
  "task;task (Taskwarrior)"
  "asciinema"
  "asciinema-agg;agg (GIF for asciinema)"
  "fabric;fabric (CLI tool)"
  "ollama"
  "cloc"
  "git"
  "python3"
  "pip3"
  "pytest"
  "xclip"
  "wl-copy;wl-copy (wl-clipboard)"
  "tree"
  "bat;bat (or batcat)" 
  "curl"
)

# Initial notes for fd and bat if the primary command isn't found but alternative is
if ! command -v fd &>/dev/null && command -v fdfind &>/dev/null; then
  echo "Note: 'fd' command not found, but 'fdfind' is. Script will check 'fdfind'."
  echo "      Consider creating an alias: alias fd=fdfind"
fi
if ! command -v bat &>/dev/null && command -v batcat &>/dev/null; then
  echo "Note: 'bat' command not found, but 'batcat' is. Script will check 'batcat'."
  echo "      Consider creating an alias: alias bat=batcat"
fi
echo # Newline for better formatting after notes

# Array to store missing commands for summary
missing_commands=()

for item_str in "${commands_to_check_structured[@]}"; do
  IFS=';' read -r cmd_val pretty_val version_flag_val <<< "$item_str"
  # Capture output to check for missing commands
  output=$(check_command "$cmd_val" "$pretty_val" "$version_flag_val" 2>&1)
  if echo "$output" | grep -q "NOT INSTALLED or NOT IN PATH"; then
    missing_commands+=("$pretty_val ($cmd_val)")
  fi
done

echo "---------------------------------------------"
echo "Installation Summary:"
if [ ${#missing_commands[@]} -eq 0 ]; then
  echo "All checked commands are installed or available."
else
  echo "The following commands were missing and installation was attempted:"
  for cmd in "${missing_commands[@]}"; do
    echo "- $cmd"
  done
fi

echo "---------------------------------------------"
echo "Notes & Interpretation:"
echo "- 'Installed' means the command was found in your PATH."
echo "- 'Version: N/A or specific query needed' means a simple version flag didn't work or isn't standard."
echo "- 'Error getting version' indicates the version command failed or produced error output."
echo "- For tools like Ollama, Fabric, Lazydocker: 'Installed' checks the CLI client. Ensure any necessary servers or services are also running and correctly configured for full functionality."
echo "- Some tools from 'moreutils' (ts, errno, vipe, etc.) or tools like 'iotop', 'ranger', 'progress' might not have individual version flags easily accessible; their presence in PATH is the primary check here."
echo "- 'pytest' check looks for the 'pytest' command in PATH. If you invoke it via 'python3 -m pytest', that's a different check not performed here. The 'Cannot read termcap database' error for pytest is an environment issue, not a script bug."
echo "- 'xclip' errors like 'Can't open display' mean it cannot connect to an X server, which is expected in headless environments. Its version check might still succeed if 'xclip -version' works independently."
echo "This script verifies command accessibility and attempts to install missing packages. Full operational status may require further specific tests for each tool."