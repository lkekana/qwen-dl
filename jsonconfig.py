from pathlib import Path
from dataclasses import dataclass
import commentjson as json  # Allows comments in JSON files


@dataclass
class AuthSection:
    use_browser_cookies: bool
    browser: str


@dataclass
class FetchSection:
    last_fetch: int
    search_strings: list[str]
    search_mode: str
    output_directory: Path
    output_template: str
    timestamp_format: str
    output_filename: str
    fetch_new_only: bool
    ignore_processed: bool
    use_chat_subfolder: bool
    chat_folder_name_template: str
    include_chat_header: bool
    extract_text_in_quotes: bool


@dataclass
class DeleteSection:
    add_fetched_chats_to_delete_list: bool
    confirm_delete: bool


@dataclass
class AppConfig:
    auth: AuthSection
    fetch: FetchSection
    delete: DeleteSection


CONFIG_FILENAME = "config.jsonc"
DEFAULTS = {
    "auth": {
        "use_browser_cookies": True,  # else cookies.txt
        "browser": "chrome",  # or "firefox" or "other", only used if use_browser_cookies is True
    },
    "fetch": {
        "last_fetch": "1764460800",
        "search_strings": [],
        "search_mode": "any",  # "any" or "all"
        "output_directory": "./output",
        "output_template": "[[content]]",
        "timestamp_format": "%-d %b %Y | %I:%M:%S %p",
        "output_filename": "[[timestamp]]_[[message_id]].md",
        "fetch_new_only": True,
        "ignore_processed": True,
        "use_chat_subfolder": True,
        "chat_folder_name_template": "[[created_at]]_[[chat_id]]",
        "include_chat_header": False,
        "extract_text_in_quotes": False,
    },
    "delete": {
        "add_fetched_chats_to_delete_list": False,
        "confirm_delete": True,
    },
}


def _config_path() -> Path:
    return Path.cwd() / CONFIG_FILENAME


def _ensure_config_exists() -> None:
    cfg_path = _config_path()
    if not cfg_path.exists():
        with cfg_path.open("w") as f:
            json.dump(DEFAULTS, f, indent=4)


def load_config() -> AppConfig:
    _ensure_config_exists()
    with _config_path().open("r") as f:
        cfg = json.load(f)

    # sections with fallback to DEFAULTS
    auth = {**DEFAULTS["auth"], **cfg.get("auth", {})}
    fetch = {**DEFAULTS["fetch"], **cfg.get("fetch", {})}
    delete = {**DEFAULTS["delete"], **cfg.get("delete", {})}

    return AppConfig(
        auth=AuthSection(
            use_browser_cookies=_parse_bool(auth["use_browser_cookies"]),
            browser=auth["browser"],
        ),
        fetch=FetchSection(
            last_fetch=_parse_int(fetch["last_fetch"]),
            search_strings=_parse_string_list(fetch["search_strings"]),
            search_mode=fetch["search_mode"],
            output_directory=Path(fetch["output_directory"]),
            output_template=_unescape_chars(fetch["output_template"]),
            timestamp_format=fetch["timestamp_format"],
            output_filename=fetch["output_filename"],
            fetch_new_only=_parse_bool(fetch["fetch_new_only"]),
            ignore_processed=_parse_bool(fetch["ignore_processed"]),
            use_chat_subfolder=_parse_bool(fetch["use_chat_subfolder"]),
            chat_folder_name_template=fetch["chat_folder_name_template"],
            include_chat_header=_parse_bool(fetch["include_chat_header"]),
            extract_text_in_quotes=_parse_bool(fetch["extract_text_in_quotes"]),
        ),
        delete=DeleteSection(
            add_fetched_chats_to_delete_list=_parse_bool(
                delete["add_fetched_chats_to_delete_list"]
            ),
            confirm_delete=_parse_bool(delete["confirm_delete"]),
        ),
    )


def save_config(config: AppConfig) -> None:
    data = {
        "auth": {
            "use_browser_cookies": config.auth.use_browser_cookies,
            "browser": config.auth.browser,
        },
        "fetch": {
            "last_fetch": str(config.fetch.last_fetch),
            "search_strings": config.fetch.search_strings,
            "search_mode": config.fetch.search_mode,
            "output_directory": str(config.fetch.output_directory),
            "output_template": config.fetch.output_template,
            "timestamp_format": config.fetch.timestamp_format,
            "output_filename": config.fetch.output_filename,
            "fetch_new_only": config.fetch.fetch_new_only,
            "ignore_processed": config.fetch.ignore_processed,
            "use_chat_subfolder": config.fetch.use_chat_subfolder,
            "chat_folder_name_template": config.fetch.chat_folder_name_template,
            "include_chat_header": config.fetch.include_chat_header,
            "extract_text_in_quotes": config.fetch.extract_text_in_quotes,
        },
        "delete": {
            "add_fetched_chats_to_delete_list": config.delete.add_fetched_chats_to_delete_list,
            "confirm_delete": config.delete.confirm_delete,
        },
    }
    with _config_path().open("w") as f:
        json.dump(data, f, indent=4)


# def get_value(key: str, section: str = "app") -> str:
#     """
#     Return value from config.json or DEFAULTS[section][key] if missing.
#     """
#     config = load_config()
#     if section in config and key in config[section]:
#         return config[section][key]

#     # Fall back to DEFAULTS
#     try:
#         return DEFAULTS[section][key]
#     except KeyError:
#         raise ValueError(f"Key '{key}' not found in section '{section}' and no default defined.")


# def set_value(key: str, value: str, section: str = "app") -> None:
#     """
#     Setter for a value in the config file.
#     Creates the file, section, and key if they don't exist.
#     """
#     config = load_config()
#     if section not in config:
#         config[section] = {}
#     config[section][key] = value
#     save_config(config)


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
    return raw.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\r", "\r")
