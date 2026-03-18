# qwen-dl

A simple little CLI to download and delete chats from Qwen AI.

## Background

I wanted to back up my conversations from [chat.qwen.ai](https://chat.qwen.ai) mostly for archival purposes and to have my notes in a format I could actually work with (Markdown files in my knowledge base).

The Qwen AI web interface is great, but I wanted my chats stored locally, searchable, organized the way I like them and downloadable with 1 command, so I wrote this.

## What it does

- **Fetches** your chat history from Qwen AI
- **Exports** user messages as Markdown files with customizable templates
- **Filters** chats by search strings (so you only download what matters)
- **Deletes** chats in bulk (because sometimes you need to clean house)

That's it.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (for dependency management)
- A browser with Qwen AI cookies (Chrome or Firefox)

## How to use

- clone the repo and navigate to the project directory
```bash
git clone https://github.com/lkekana/qwen-dl.git
cd qwen-dl
```

- install dependencies
If you're using `uv`, just run:
```bash
uv sync
```

Or with pip:
```bash
pip install .
```

- create a default config file (`config.jsonc`)
```bash
uv run run.py init
# or python3 run.py init
```

- fetch your chats
```bash
uv run run.py fetch
# or python3 run.py fetch
```

- (optionally) delete chats listed in `del.txt`
```bash
uv run run.py delete
# or python3 run.py delete
```

## Configuration

Edit `config.jsonc` to customize behavior:

```jsonc
{
    "auth": {
        "use_browser_cookies": true,
        "browser": "chrome"
    },
    "fetch": {
        "last_fetch": "1773532800",
        "search_strings": [],
        "output_directory": "./output",
        "output_template": "[[content]]\n\n[[timestamp_string]]",
        "use_chat_subfolder": true,
        "ignore_processed": true
    },
    "delete": {
        "confirm_delete": true
    }
}
```

## How it works

The CLI authenticates using your browser's cookies for `chat.qwen.ai`, then paginates through the API to fetch chat records. For each chat, it extracts user messages, formats them using your template, and writes them to Markdown files.

Downloaded (and previously skipped) chats are tracked via `.fileignore` so you don't re-download them on the next fetch.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
