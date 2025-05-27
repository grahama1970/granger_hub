# MCP Setup Guide for Claude Code

This guide explains how to configure Model Context Protocol (MCP) servers in Claude Code when you encounter the "No MCP servers configured" error.

## Problem Description

When running `claude mcp` in a project, you may see:
```
No MCP servers configured. Run `claude mcp` to learn about how to configure MCP servers.
```

This happens even when you have a valid `.mcp.json` file in your project directory. The issue is that Claude Code needs the servers to be explicitly registered using the CLI.

## Solution

### Step 1: Navigate to Your Project

```bash
cd /path/to/your/project
```

### Step 2: Add MCP Servers Using CLI

Run the following commands to register each MCP server with Claude Code:

```bash
# Add Perplexity Ask server
claude mcp add perplexity-ask npx -- -y server-perplexity-ask

# Add Brave Search server
claude mcp add brave-search npx -- -y @modelcontextprotocol/server-brave-search

# Add GitHub server
claude mcp add github npx -- -y @modelcontextprotocol/server-github

# Add Desktop Commander server
claude mcp add desktop-commander npx -- -y @wonderwhy-er/desktop-commander

# Add Context7 server
claude mcp add context7 npx -- -y @upstash/context7-mcp@latest

# Add Ripgrep server
claude mcp add ripgrep npx -- -y mcp-ripgrep@latest
```

### Step 3: Configure API Keys and Environment Variables

Create or update the `.mcp.json` file in your project root with the necessary API keys:

```json
{
  "mcpServers": {
    "perplexity-ask": {
      "command": "npx",
      "args": ["-y", "server-perplexity-ask"],
      "env": {
        "PERPLEXITY_API_KEY": "your-perplexity-api-key-here"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-brave-api-key-here"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-token-here"
      }
    },
    "desktop-commander": {
      "command": "npx",
      "args": ["-y", "@wonderwhy-er/desktop-commander"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "ripgrep": {
      "command": "npx",
      "args": ["-y", "mcp-ripgrep@latest"]
    }
  }
}
```

### Step 4: Verify Configuration

Check that all servers are properly configured:

```bash
claude mcp list
```

You should see output like:
```
perplexity-ask: npx -y server-perplexity-ask
brave-search: npx -y @modelcontextprotocol/server-brave-search
github: npx -y @modelcontextprotocol/server-github
desktop-commander: npx -y @wonderwhy-er/desktop-commander
context7: npx -y @upstash/context7-mcp@latest
ripgrep: npx -y mcp-ripgrep@latest
```

## Complete Setup Script

Here's a complete script you can run to set up all MCP servers at once:

```bash
#!/bin/bash
# setup-mcp-servers.sh

# Navigate to project directory (update this path)
cd /path/to/your/project

# Add all MCP servers
echo "Adding MCP servers to Claude Code..."
claude mcp add perplexity-ask npx -- -y server-perplexity-ask
claude mcp add brave-search npx -- -y @modelcontextprotocol/server-brave-search
claude mcp add github npx -- -y @modelcontextprotocol/server-github
claude mcp add desktop-commander npx -- -y @wonderwhy-er/desktop-commander
claude mcp add context7 npx -- -y @upstash/context7-mcp@latest
claude mcp add ripgrep npx -- -y mcp-ripgrep@latest

# Create .mcp.json with API keys
echo "Creating .mcp.json configuration..."
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "perplexity-ask": {
      "command": "npx",
      "args": ["-y", "server-perplexity-ask"],
      "env": {
        "PERPLEXITY_API_KEY": "REPLACE_WITH_YOUR_PERPLEXITY_KEY"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "REPLACE_WITH_YOUR_BRAVE_KEY"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "REPLACE_WITH_YOUR_GITHUB_TOKEN"
      }
    },
    "desktop-commander": {
      "command": "npx",
      "args": ["-y", "@wonderwhy-er/desktop-commander"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "ripgrep": {
      "command": "npx",
      "args": ["-y", "mcp-ripgrep@latest"]
    }
  }
}
EOF

# Verify setup
echo -e "\nVerifying MCP server configuration..."
claude mcp list

echo -e "\n✅ MCP servers setup complete!"
echo "⚠️  Remember to update the API keys in .mcp.json with your actual keys"
```

## Troubleshooting

### Issue: "command not found" errors
If you're using nvm or have Node.js installed in a non-standard location, you may need to use absolute paths:

```bash
# Find your npx location
which npx
# Example output: /home/username/.nvm/versions/node/v22.15.0/bin/npx

# Then use the absolute path when adding servers:
claude mcp add perplexity-ask /home/username/.nvm/versions/node/v22.15.0/bin/npx -- -y server-perplexity-ask
```

### Issue: Servers still not loading
1. Restart Claude Code after configuration
2. Check that Node.js is properly installed: `node --version`
3. Ensure npx is available: `npx --version`

### Issue: API keys not working
- Make sure the `.mcp.json` file is in your project root
- Verify the JSON syntax is correct
- Check that API keys are valid and have the necessary permissions

## Configuration Files

Claude Code uses multiple configuration files:
- `.mcp.json` - Project-specific MCP server configuration (includes API keys)
- `.claude/settings.local.json` - Project-specific permissions and settings
- `~/.claude.json` - Global Claude Code configuration

## Security Notes

1. **Never commit API keys to version control**
   - Add `.mcp.json` to your `.gitignore` file
   - Use environment variables or secure key management for production

2. **API Key Sources**
   - Perplexity: https://www.perplexity.ai/settings/api
   - Brave Search: https://brave.com/search/api/
   - GitHub: https://github.com/settings/tokens

## Using This Setup Across Projects

To apply this configuration to other projects:

1. Copy the setup script to each project
2. Update the API keys in the script or `.mcp.json`
3. Run the script in each project directory
4. Each project maintains its own MCP server configuration

## Additional MCP Servers

To add more MCP servers:
```bash
# Generic format
claude mcp add <server-name> npx -- -y <npm-package-name>

# Example: Adding a custom server
claude mcp add my-server npx -- -y @myorg/my-mcp-server
```

Then update `.mcp.json` with any required environment variables.

---

**Last Updated:** December 2024  
**Claude Code Version:** 1.0.3+