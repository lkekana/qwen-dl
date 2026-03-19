from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import commentjson as json  # Allows comments in JSON files

VALID_ROLES = {"user", "assistant", "system"}
VALID_BROWSERS = {
    "chrome",
    "chromium",
    "opera",
    "opera_gx",
    "brave",
    "edge",
    "vivaldi",
    "firefox",
    "librewolf",
    "safari",
    "lynx",
    "w3m",
    "arc",
    "other",
}
VALID_SEARCH_MODES = {"any", "all"}


@dataclass
class AuthSection:
    use_browser_cookies: bool
    browser: str


@dataclass
class FetchSection:
    message_roles: list[str]
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
    update_last_fetch: bool


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
        "use_browser_cookies": True,
        "browser": "chrome",
    },
    "fetch": {
        "message_roles": ["user", "assistant"],
        "last_fetch": "1764460800",
        "search_strings": [],
        "search_mode": "any",
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
        "update_last_fetch": True,
    },
    "delete": {
        "add_fetched_chats_to_delete_list": False,
        "confirm_delete": True,
    },
}


def _config_path() -> Path:
    return Path.cwd() / CONFIG_FILENAME


def default_config_exists() -> bool:
    return _config_path().exists()


def create_default_config_if_not_exists() -> None:
    cfg_path = _config_path()
    if not cfg_path.exists():
        with cfg_path.open("w") as f:
            json.dump(DEFAULTS, f, indent=4)


def default_config() -> AppConfig:
    return AppConfig(
        auth=AuthSection(
            use_browser_cookies=DEFAULTS["auth"]["use_browser_cookies"],
            browser=DEFAULTS["auth"]["browser"],
        ),
        fetch=FetchSection(
            message_roles=DEFAULTS["fetch"]["message_roles"],
            last_fetch=_parse_int(DEFAULTS["fetch"]["last_fetch"]),
            search_strings=_parse_string_list(DEFAULTS["fetch"]["search_strings"]),
            search_mode=DEFAULTS["fetch"]["search_mode"],
            output_directory=Path(DEFAULTS["fetch"]["output_directory"]),
            output_template=_unescape_chars(DEFAULTS["fetch"]["output_template"]),
            timestamp_format=DEFAULTS["fetch"]["timestamp_format"],
            output_filename=DEFAULTS["fetch"]["output_filename"],
            fetch_new_only=_parse_bool(DEFAULTS["fetch"]["fetch_new_only"]),
            ignore_processed=_parse_bool(DEFAULTS["fetch"]["ignore_processed"]),
            use_chat_subfolder=_parse_bool(DEFAULTS["fetch"]["use_chat_subfolder"]),
            chat_folder_name_template=DEFAULTS["fetch"]["chat_folder_name_template"],
            include_chat_header=_parse_bool(DEFAULTS["fetch"]["include_chat_header"]),
            extract_text_in_quotes=_parse_bool(
                DEFAULTS["fetch"]["extract_text_in_quotes"]
            ),
            update_last_fetch=_parse_bool(DEFAULTS["fetch"]["update_last_fetch"]),
        ),
        delete=DeleteSection(
            add_fetched_chats_to_delete_list=_parse_bool(
                DEFAULTS["delete"]["add_fetched_chats_to_delete_list"]
            ),
            confirm_delete=_parse_bool(DEFAULTS["delete"]["confirm_delete"]),
        ),
    )


def load_config(path: Optional[Path] = None) -> AppConfig:
    if path is not None:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found at specified path: {path}")
        else:
            config_path = path
    else:
        create_default_config_if_not_exists()
        config_path = _config_path()

    with config_path.open("r") as f:
        cfg = json.load(f)

    # sections with fallback to DEFAULTS
    auth = {**DEFAULTS["auth"], **cfg.get("auth", {})}
    fetch = {**DEFAULTS["fetch"], **cfg.get("fetch", {})}
    delete = {**DEFAULTS["delete"], **cfg.get("delete", {})}

    if not isinstance(fetch["message_roles"], list) or not all(
        isinstance(role, str) for role in fetch["message_roles"]
    ):
        raise ValueError("Invalid message_roles in config: must be a list of strings")

    if fetch["search_mode"] not in VALID_SEARCH_MODES:
        raise ValueError("Invalid search_mode in config: must be 'any' or 'all'")

    if auth["browser"] not in VALID_BROWSERS:
        raise ValueError(
            "Invalid browser in config: must be 'chrome', 'firefox', or 'other'"
        )

    if any(role not in VALID_ROLES for role in fetch["message_roles"]):
        raise ValueError(
            f"Invalid message_roles in config: each role must be one of {VALID_ROLES}"
        )

    return AppConfig(
        auth=AuthSection(
            use_browser_cookies=_parse_bool(auth["use_browser_cookies"]),
            browser=auth["browser"],
        ),
        fetch=FetchSection(
            message_roles=fetch["message_roles"],
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
            update_last_fetch=_parse_bool(fetch["update_last_fetch"]),
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
            "message_roles": config.fetch.message_roles,
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
            "update_last_fetch": config.fetch.update_last_fetch,
        },
        "delete": {
            "add_fetched_chats_to_delete_list": config.delete.add_fetched_chats_to_delete_list,
            "confirm_delete": config.delete.confirm_delete,
        },
    }

    if not isinstance(data["fetch"]["message_roles"], list) or not all(
        isinstance(role, str) for role in data["fetch"]["message_roles"]
    ):
        raise ValueError("Invalid message_roles in config: must be a list of strings")

    if data["fetch"]["search_mode"] not in VALID_SEARCH_MODES:
        raise ValueError("Invalid search_mode in config: must be 'any' or 'all'")

    if data["auth"]["browser"] not in VALID_BROWSERS:
        raise ValueError(
            "Invalid browser in config: must be 'chrome', 'firefox', or 'other'"
        )

    if any(role not in VALID_ROLES for role in data["fetch"]["message_roles"]):
        raise ValueError(
            f"Invalid message_roles in config: each role must be one of {VALID_ROLES}"
        )

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
