import argparse
from pathlib import Path
import time
import browser_cookie3
import requests
import json
from datetime import datetime
from typing import TypedDict, List, Dict, Optional, Literal

# from config import load_app_config, AppConfig
from jsonconfig import load_config, AppConfig
from ignore import add_ignore_id, is_ignored
import re
from uaforge.core.generator import UserAgentGenerator
import http.cookiejar as cookielib

agent = UserAgentGenerator()
identity = agent.generate()
headers = identity.get_headers()
# print(f"Using User-Agent: {headers['User-Agent']}")
# print(f"Using other headers: {headers}")

cfg: AppConfig = load_config()
# print(f"Configuration loaded: {cfg}")

Role = Literal["user", "assistant"]
ChatType = Literal["t2t"]


class ChatItem(TypedDict):
    id: str
    title: str
    updated_at: int
    created_at: int
    chat_type: ChatType
    project_id: str
    pinned: bool


class ChatsResponse(TypedDict):
    success: bool
    request_id: str
    data: List[ChatItem]


class FileMeta(TypedDict, total=False):
    name: str
    size: int
    content_type: str
    parse_meta: Dict[str, str]


class FileObj(TypedDict):
    created_at: int
    data: Dict[str, object]
    filename: str
    hash: Optional[str]
    id: str
    user_id: str
    meta: FileMeta
    update_at: int


class MessageFile(TypedDict):
    id: str
    name: str
    file_type: str
    type: str
    file_class: str
    size: int
    url: str
    file: FileObj
    collection_name: str
    progress: int
    status: str
    greenNet: str
    error: str
    itemId: str
    showType: str
    uploadTaskId: str


class FeatureConfig(TypedDict):
    thinking_enabled: bool
    output_schema: str
    instructions: Optional[str]
    research_mode: str
    auto_search: bool


class Usage(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ContentListItem(TypedDict):
    content: str
    phase: str
    status: str
    extra: Optional[object]
    role: Role
    response_id: str
    usage: Usage
    timestamp: int


class MessageItem(TypedDict, total=False):
    id: str
    role: Role
    content: str
    reasoning_content: Optional[str]
    chat_type: ChatType
    sub_chat_type: ChatType
    model: Optional[str]
    modelName: Optional[str]
    modelIdx: Optional[int]
    parentId: Optional[str]
    childrenIds: List[str]
    feature_config: FeatureConfig
    content_list: List[ContentListItem]
    is_stop: bool
    edited: bool
    error: Optional[str]
    meta: Dict[str, object]
    extra: Dict[str, object]
    feedbackId: Optional[str]
    turn_id: Optional[str]
    annotation: Optional[str]
    done: bool
    info: Optional[object]
    timestamp: int
    models: Optional[List[str]]
    files: List[MessageFile]


class History(TypedDict):
    messages: Dict[str, MessageItem]
    currentId: str
    currentResponseIds: List[str]


class ChatObj(TypedDict):
    history: History
    models: List[str]
    messages: List[MessageItem]


class MetaObj(TypedDict):
    timestamp: int
    tags: List[str]


class ChatRecord(TypedDict):
    id: str
    user_id: str
    title: str
    chat: ChatObj
    updated_at: int
    created_at: int
    share_id: Optional[str]
    archived: bool
    pinned: bool
    meta: MetaObj
    folder_id: Optional[str]
    currentResponseIds: List[str]
    currentId: str
    chat_type: ChatType
    models: Optional[List[str]]
    project_id: str


default_headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "DNT": "1",
    "Referer": "https://chat.qwen.ai/",
    # kind of unnecessary as of 2026-03 (not widely adopted yet)
    # "Sec-Fetch-Dest": "empty",
    # "Sec-Fetch-Mode": "cors",
    # "Sec-Fetch-Site": "same-origin",
    # did this by merging the dicts below instead
    # "User-Agent": headers["User-Agent"],
    # "Sec-CH-UA": headers["Sec-CH-UA"],
    # "Sec-CH-UA-Mobile": headers["Sec-CH-UA-Mobile"],
    # "Sec-CH-UA-Platform": headers["Sec-CH-UA-Platform"],
    "source": "web",
}
default_headers.update(headers)


def make_session() -> requests.Session:
    """
    Returns a requests.Session that:
      - reuses TCP connections (keep-alive)
      - automatically updates cookies from Set-Cookie
      - can be reused for multiple requests
    """
    s = requests.Session()
    s.headers.update(default_headers)
    if cfg.auth.use_browser_cookies:
        if cfg.auth.browser == "chrome":
            cj = browser_cookie3.chrome(domain_name="qwen.ai")
        elif cfg.auth.browser == "firefox":
            cj = browser_cookie3.firefox(domain_name="qwen.ai")
        else:
            cj = browser_cookie3.load(domain_name="qwen.ai")
    else:
        cj = cookielib.MozillaCookieJar("cookies.txt")
        cj.load(ignore_discard=True, ignore_expires=True)
    s.cookies.update(cj)
    return s


def request_with_session(
    s: requests.Session, method: str, url: str, **kwargs
) -> requests.Response:
    """
    Makes a request with the provided session. Cookies set by the server are stored
    in s.cookies and automatically sent on subsequent requests.
    """
    headers = kwargs.pop("headers", {})
    headers = {**headers, "Timezone": format_gmt_date()}
    resp = s.request(method.upper(), url, headers=headers, **kwargs)
    # s.cookies now includes any Set-Cookie from resp
    return resp


def format_gmt_date(dt: datetime | None = None) -> str:
    """
    Returns a date string like 'Sun Feb 01 2026 13:11:53 GMT+0200'.
    If dt is None, uses current local datetime.
    """
    dt = dt.astimezone() if dt else datetime.now().astimezone()
    return dt.strftime("%a %b %d %Y %H:%M:%S ") + "GMT" + dt.strftime("%z")


def format_epoch_seconds(ts: int) -> str:
    """
    Converts epoch seconds to a human-readable date string like '1 Feb 2026 | 01:11:53 PM'.
    """
    dt = datetime.fromtimestamp(ts)
    # return dt.strftime("%-d %b %Y | %I:%M:%S %p")
    return dt.strftime(cfg.fetch.timestamp_format)


def extract_between_quotes(text: str) -> str:
    """
    Returns substring between the first opening quote (" or “)
    and the last closing quote (" or ”). Trims whitespace.
    """
    if not text:
        return ""
    # Find first opening quote
    open_match = re.search(r'[“"]', text)
    if not open_match:
        return ""
    start = open_match.end()

    # Find last closing quote
    close_match = None
    for m in re.finditer(r'[”"]', text):
        close_match = m
    if not close_match or close_match.start() <= start:
        return ""

    return text[start : close_match.start()].strip()


def get_chat_records(s: requests.Session, last_fetch: int = 0) -> List[ChatItem]:
    result = []
    page = 1
    while True:
        url = f"https://chat.qwen.ai/api/v2/chats/?page={page}&exclude_project=true"
        # print(url)
        print(f"\rFetching chats... (page {page})", end="", flush=True)
        response = request_with_session(s, "GET", url)
        if response.status_code != 200:
            print()
            raise Exception(
                f"Failed to fetch chats: {response.status_code} {response.text}"
            )
        res_json: ChatsResponse = response.json()
        if not res_json.get("success"):
            print()
            raise Exception(f"API returned error: {response.text}")
        data: List[ChatItem] = res_json["data"]
        if not data:
            break
        if len(data) == 0:
            break
        # Filter by last_fetch
        filtered = [c for c in data if c["created_at"] > last_fetch]
        result.extend(filtered)
        if len(data) < 60:
            break
        page += 1
    
    print()
    return result


def get_chat(chat_id: str, s: requests.Session) -> ChatRecord:
    url = f"https://chat.qwen.ai/api/v2/chats/{chat_id}"
    response = request_with_session(s, "GET", url)
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch chat {chat_id}: {response.status_code} {response.text}"
        )
    result = response.json()
    if not result.get("success"):
        raise Exception(f"API returned error: {response.text}")
    return response.json()["data"]


# def get_user_messages(chat: ChatRecord) -> List[MessageItem]:
#     messages: List[MessageItem] = chat["chat"]["messages"]
#     messages.extend(chat["chat"]["history"]["messages"].values())
#     unique_messages = {m["id"]: m for m in messages}
#     user_messages = [
#         m for m in unique_messages.values() if m["role"] == "user"
#     ]
#     # remove dupes by checking value of extract_between_quotes(content)
#     seen_contents = set()
#     filtered_user_messages = []
#     for m in user_messages:
#         content = extract_between_quotes(m["content"])
#         if content not in seen_contents:
#             seen_contents.add(content)
#             filtered_user_messages.append(m)
#     # filter messages where extract_between_quotes(content).strip() is empty
#     filtered_user_messages = [
#         m for m in filtered_user_messages if extract_between_quotes(m["content"]).strip()
#     ]
#     return filtered_user_messages


def _normalized_content(message: MessageItem) -> str:
    if not cfg.fetch.extract_text_in_quotes:
        return message["content"].strip()
    return extract_between_quotes(message["content"]).strip()


def get_user_messages(chat: ChatRecord) -> List[MessageItem]:
    messages: List[MessageItem] = chat["chat"]["messages"] + list(
        chat["chat"]["history"]["messages"].values()
    )
    messages.sort(key=lambda m: m["timestamp"])
    # keep only user role
    users = [m for m in messages if m.get("role") == "user"]
    # dedupe by normalized content and drop empties
    dedupe_by_content: dict[str, MessageItem] = {}
    for m in users:
        content = _normalized_content(m)
        if not content:
            continue
        # first occurrence wins
        dedupe_by_content.setdefault(content, m)
    return list(dedupe_by_content.values())


def format_as_md(message: MessageItem) -> str:
    content = message["content"]
    # copy from first double quote, either " or “
    # up to last quote, either " or ”
    fixed_content = content.strip()
    if cfg.fetch.extract_text_in_quotes:
        fixed_content = extract_between_quotes(fixed_content)
    md = fixed_content
    md += "\n\n"
    md += format_epoch_seconds(int(message["timestamp"]))
    md += "\nTags: \n"
    md += "References: \n"
    md += "\n---\n"
    return md


def format_as_md_v2(message: MessageItem) -> str:
    content = message["content"]
    fixed_content = content.strip()
    if cfg.fetch.extract_text_in_quotes:
        fixed_content = extract_between_quotes(fixed_content)
    timestamp_string = format_epoch_seconds(int(message["timestamp"]))
    template = (
        cfg.fetch.output_template
        or "[[content]]\n\n[[timestamp_string]]\nTags: \nReferences: \n\n---\n"
    )

    # Simple placeholder replacement
    md = template.replace("[[content]]", fixed_content).replace(
        "[[timestamp_string]]", timestamp_string
    )

    return md


def matches_search(chat: ChatRecord) -> bool:
    if len(cfg.fetch.search_strings) == 0:
        return True
    blob = json.dumps(chat)
    if cfg.fetch.search_mode == "all":
        return all(s in blob for s in cfg.fetch.search_strings)
    if cfg.fetch.search_mode == "any":
        return any(s in blob for s in cfg.fetch.search_strings)
    return True


def hydrate_file_template(template: str, message: MessageItem) -> str:
    # filename = f"{str(um['timestamp'])}_{um['id']}.md"
    timestamp = str(message["timestamp"])
    message_id = message["id"]
    filename = template.replace("[[timestamp]]", timestamp).replace(
        "[[message_id]]", message_id
    )
    return filename


def hydrate_chat_folder_name_template(template: str, chat: ChatRecord) -> str:
    created_at = str(chat["created_at"])
    chat_id = chat["id"]
    folder_name = template.replace("[[created_at]]", created_at).replace(
        "[[chat_id]]", chat_id
    )
    return folder_name


def fetch():
    if not cfg.fetch.output_directory.exists():
        cfg.fetch.output_directory.mkdir(parents=True)
    print(
        f"Last fetch time: {cfg.fetch.last_fetch} ({datetime.fromtimestamp(cfg.fetch.last_fetch)})"
    )
    s = make_session()
    fetched_urls = []
    chat_records = get_chat_records(s, last_fetch=cfg.fetch.last_fetch)
    print(f"Found {len(chat_records)} new chat records.")
    for cr in chat_records:
        # print('#'*60)
        # print(f"Chat ID: {cr['id']}")
        # print(f"Title: {cr['title']}")
        # print(f"Created at: {format_epoch_seconds(cr['created_at'])}")
        # print(f"Updated at: {format_epoch_seconds(cr['updated_at'])}")
        chat = get_chat(cr["id"], s)
        if cfg.fetch.ignore_processed and is_ignored(cr["id"]):
            print(f"Skipping chat {cr['id']} - in ignore list.")
            continue

        # if json.dumps(chat).find(search_string) == -1:
        #     print(f"Skipping chat {cr['id']} - does not contain search string.")
        #     add_ignore_id(cr["id"])
        #     continue

        # for ss in cfg.search_strings:
        #     if json.dumps(chat).find(ss) == -1:
        #         print(f"Skipping chat {cr['id']} - does not contain search string '{ss}'.")
        #         add_ignore_id(cr["id"])
        #         continue

        if not matches_search(chat):
            print(f"Skipping chat {cr['id']} - does not match search criteria.")
            if cfg.fetch.ignore_processed:
                add_ignore_id(cr["id"])
            continue

        user_messages = get_user_messages(chat)
        if not user_messages:
            print(f"No user messages found for chat {cr['id']}. Skipping.")
            if cfg.fetch.ignore_processed:
                add_ignore_id(cr["id"])
            continue
        # print(f"Processing chat {cr['id']} - contains search string.")
        # print(f"Found {len(user_messages)} user messages.")
        print(f"Processing chat {cr['id']} with {len(user_messages)} user messages.")
        user_messages.sort(key=lambda m: m["timestamp"])
        chat_path = cfg.fetch.output_directory
        if cfg.fetch.use_chat_subfolder:
            # chat_path = cfg.fetch.output_directory / f"{cr['created_at']}_{cr['id']}"
            folder_name = hydrate_chat_folder_name_template(
                cfg.fetch.chat_folder_name_template, cr
            )
            chat_path = cfg.fetch.output_directory / folder_name
        if not chat_path.exists():
            chat_path.mkdir(parents=True)

        for idx, um in enumerate(user_messages):
            ts = datetime.fromtimestamp(int(um["timestamp"]))
            chat_link = f"https://chat.qwen.ai/c/{cr['id']}"
            if (
                cfg.delete.add_fetched_chats_to_delete_list
                and chat_link not in fetched_urls
            ):
                fetched_urls.append(chat_link)
            md = ""
            if cfg.fetch.include_chat_header:
                md += f"# Original Chat: [{cr['title']}]({chat_link})\n\n"
                prospective_filename = (
                    f"# r_{ts.year}.{ts.month:02}.{ts.day:02}.{idx + 1}.md\n"
                )
                md += prospective_filename
            # md += format_as_md(um)
            md += format_as_md_v2(um)
            # filename = f"{str(um['timestamp'])}_{um['id']}.md"
            # filename = "[[timestamp]]_[[id]].md"
            filename = hydrate_file_template(cfg.fetch.output_filename, um)
            file_path = chat_path / filename
            with file_path.open("w") as f:
                f.write(md)
            # print(f"Wrote message {um['id']} to {filename}.")

        # Update last_fetch
        # if cr["created_at"] > last_fetch:
        #     last_fetch = cr["created_at"]
        #     set_value("last_fetch", str(last_fetch))
        #     print(f"Updated last_fetch to {last_fetch}.")
        time.sleep(1)

    # add fetched_urls to del.txt
    if cfg.delete.add_fetched_chats_to_delete_list and len(fetched_urls) > 0:
        del_path = Path("del.txt")
        with del_path.open("a") as f:
            for url in fetched_urls:
                f.write(url + "\n")
        print(f"Added {len(fetched_urls)} fetched chat URLs to del.txt for deletion.")


def delete_chats():
    del_path = Path("del.txt")
    if not del_path.exists():
        print("del.txt not found. Exiting.")
        return

    urls = []

    # use regex to extract chat IDs from lines like "https://chat.qwen.ai/c/[id]"
    with del_path.open() as f:
        for line in f:
            match = re.search(r"https://chat\.qwen\.ai/c/([a-zA-Z0-9\-]+)", line)
            if match:
                chat_id = match.group(1)
                urls.append(f"https://chat.qwen.ai/api/v2/chats/{chat_id}")

    if len(urls) == 0:
        print("No valid chat URLs found in del.txt. Exiting.")
        return

    print(f"Found {len(urls)} chat URLs to delete.")
    s = make_session()
    print("Fetching chat records for confirmation...")
    chats = []
    total = len(urls)
    for i, url in enumerate(urls, start=1):
        id = url.split("/")[-1]
        print(f"\rFetching {i}/{total}: {id}", end="", flush=True)

        # if not uuid
        if not re.match(r"^[a-zA-Z0-9\-]+$", id):
            print(f"Invalid chat ID: {id}. Skipping.")
            continue

        chat_record = get_chat(id, s)
        chats.append(chat_record)
        time.sleep(0.5)

    print()
    print("The following chats will be deleted:")
    for chat in chats:
        user_messages = get_user_messages(chat)
        if not user_messages:
            print(f"No user messages found for chat {chat['id']}. Skipping.")
            continue
        user_messages.sort(key=lambda m: m["timestamp"])
        first_message = user_messages[0]
        first_message_content = _normalized_content(first_message)
        print(
            f'\033[1m{chat["id"]}\033[0m: \033[3m{chat["title"]}\033[0m, beginning with "{first_message_content[:100]}"'
        )

    s.headers.update(
        {
            "Origin": "https://chat.qwen.ai",
        }
    )

    if cfg.delete.confirm_delete:
        print(
            "\033[91mThis will permanently delete the above chats. Are you sure? (yes/no)\033[0m"
        )
        confirm = input().strip().lower()
        if confirm[0] != "y":
            print("Aborting...")
            return

    total = len(chats)
    for i, chat in enumerate(chats, start=1):
        print(f"\rDeleting {i}/{total}: {chat['id']}", end="", flush=True)
        url = f"https://chat.qwen.ai/api/v2/chats/{chat['id']}"
        response = request_with_session(s, "DELETE", url)
        if response.status_code != 200:
            print(
                f"Failed to delete chat {chat['id']}: {response.status_code} {response.text}"
            )
        time.sleep(0.5)
    print()
    print("Done.")


if __name__ == "__main__":
    # print("Starting qwen-dl...")
    # fetch()
    # delete_chats()
    parser = argparse.ArgumentParser(
        prog="qwen-dl", description="Fetch and process chat records from qwen.ai"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_fetch = subparsers.add_parser(
        "fetch", help="Fetch new chat records and save user messages as markdown files"
    )
    parser_fetch.set_defaults(func=fetch)

    parser_delete = subparsers.add_parser(
        "delete", help="Delete chats listed in del.txt"
    )
    parser_delete.set_defaults(func=delete_chats)

    args = parser.parse_args()
    args.func()
