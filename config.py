from pathlib import Path
from configparser import ConfigParser

# from typing import Optional
from dataclasses import dataclass
import json

CONFIG_FILENAME = "config.ini"
DEFAULTS = {
    "app": {
        "last_fetch": "1764460800",
        "search_strings": [],
        "search_mode": "any",  # "any" or "all"
        "output_directory": "./output",
        "output_template": "[[content]]",
        "timestamp_format": "%-d %b %Y | %I:%M:%S %p".replace(
            "%", "%%"
        ),  # escape % for later formatting
        "output_filename": "[[timestamp]]_[[message_id]].md",
        "fetch_new_only": True,
        "ignore_processed": True,
        "use_chat_subfolder": True,
        "chat_folder_name_template": "[[created_at]]_[[chat_id]]",
        "include_chat_header": False,
        "extract_text_in_quotes": False,
        "add_fetched_chats_to_delete_list": False,
        "confirm_delete": True,
        "use_browser_cookies": True,  # else cookies.txt
        "browser": "chrome",  # or "firefox" or "other", only used if use_browser_cookies is True
    }
}


def _config_path() -> Path:
    return Path.cwd() / CONFIG_FILENAME


def _ensure_config_exists() -> None:
    cfg_path = _config_path()
    if not cfg_path.exists():
        parser = ConfigParser()
        for section, kv in DEFAULTS.items():
            parser[section] = kv
        with cfg_path.open("w") as f:
            parser.write(f)


def _load_config() -> ConfigParser:
    _ensure_config_exists()
    parser = ConfigParser()
    parser.read(_config_path())
    return parser


def get_value(key: str, section: str = "app") -> str:
    """
    Return value from config.ini or DEFAULTS[section][key] if missing.
    """
    parser = _load_config()
    # if not parser.has_section(section):
    #     return None
    # if not parser.has_option(section, key):
    #     return None
    # return parser.get(section, key)
    if parser.has_option(section, key):
        return parser.get(section, key)

    # fall back to DEFAULTS
    try:
        return DEFAULTS[section][key]
    except KeyError:
        raise ValueError(
            f"Key '{key}' not found in section '{section}' and no default defined."
        )


def set_value(key: str, value: str, section: str = "app") -> None:
    """
    Setter for a value in the config file.
    Creates the file, section, and key if they don't exist.
    """
    parser = _load_config()
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, key, value)
    with _config_path().open("w") as f:
        parser.write(f)


@dataclass
class AppConfig:
    search_strings: list[str]
    search_mode: str
    output_directory: Path
    timestamp_format: str
    output_template: str
    output_filename: str
    include_chat_header: bool
    ignore_processed: bool
    use_chat_subfolder: bool
    chat_folder_name_template: str
    confirm_delete: bool
    extract_text_in_quotes: bool
    add_fetched_chats_to_delete_list: bool
    fetch_new_only: bool
    last_fetch: int
    use_browser_cookies: bool
    browser: str


def _parse_int(raw: str | int) -> int:
    if isinstance(raw, int):
        return raw
    return int(raw.strip())


def _parse_bool(raw: str | bool) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _parse_string_list(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        return raw
    try:
        # Try parsing as JSON array
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: split by commas
        return [s.strip() for s in raw.split(",") if s.strip()]


def _unescape_chars(raw: str) -> str:
    # return raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    return raw.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\r", "\r")


def load_app_config() -> AppConfig:
    parser = _load_config()
    return AppConfig(
        search_strings=_parse_string_list(
            parser.get(
                "app",
                "search_strings",
                fallback=json.dumps(DEFAULTS["app"]["search_strings"]),
            )
        ),
        search_mode=parser.get(
            "app", "search_mode", fallback=DEFAULTS["app"]["search_mode"]
        ),
        output_directory=Path(
            parser.get(
                "app", "output_directory", fallback=DEFAULTS["app"]["output_directory"]
            )
        ),
        timestamp_format=parser.get(
            "app", "timestamp_format", fallback=DEFAULTS["app"]["timestamp_format"]
        ),
        output_template=_unescape_chars(
            parser.get(
                "app", "output_template", fallback=DEFAULTS["app"]["output_template"]
            )
        ),
        output_filename=parser.get(
            "app", "output_filename", fallback=DEFAULTS["app"]["output_filename"]
        ),
        include_chat_header=_parse_bool(
            parser.get(
                "app",
                "include_chat_header",
                fallback=str(DEFAULTS["app"]["include_chat_header"]),
            )
        ),
        ignore_processed=_parse_bool(
            parser.get(
                "app",
                "ignore_processed",
                fallback=str(DEFAULTS["app"]["ignore_processed"]),
            )
        ),
        use_chat_subfolder=_parse_bool(
            parser.get(
                "app",
                "use_chat_subfolder",
                fallback=str(DEFAULTS["app"]["use_chat_subfolder"]),
            )
        ),
        chat_folder_name_template=parser.get(
            "app",
            "chat_folder_name_template",
            fallback=DEFAULTS["app"]["chat_folder_name_template"],
        ),
        confirm_delete=_parse_bool(
            parser.get(
                "app", "confirm_delete", fallback=str(DEFAULTS["app"]["confirm_delete"])
            )
        ),
        extract_text_in_quotes=_parse_bool(
            parser.get(
                "app",
                "extract_text_in_quotes",
                fallback=str(DEFAULTS["app"]["extract_text_in_quotes"]),
            )
        ),
        add_fetched_chats_to_delete_list=_parse_bool(
            parser.get(
                "app",
                "add_fetched_chats_to_delete_list",
                fallback=str(DEFAULTS["app"]["add_fetched_chats_to_delete_list"]),
            )
        ),
        fetch_new_only=_parse_bool(
            parser.get(
                "app", "fetch_new_only", fallback=str(DEFAULTS["app"]["fetch_new_only"])
            )
        ),
        last_fetch=_parse_int(
            parser.get("app", "last_fetch", fallback=str(DEFAULTS["app"]["last_fetch"]))
        ),
        use_browser_cookies=_parse_bool(
            parser.get(
                "app",
                "use_browser_cookies",
                fallback=str(DEFAULTS["app"]["use_browser_cookies"]),
            )
        ),
        browser=parser.get("app", "browser", fallback=DEFAULTS["app"]["browser"]),
    )
