import ipaddress
import socket
import re
import io
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024

def chunks(text, size=1400, overlap=200):
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        result.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return result

def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Use a public HTTPS URL on port 443.")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Private and local network addresses are not allowed.")
    return url

def web_document(url):
    # Redirects are deliberately disabled; production should also enforce an egress firewall.
    validate_url(url)
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", url, headers={"User-Agent": "AtlasPortfolioBot/1.0"}) as response:
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError("Use the final URL; redirects are not followed.")
            if "text/html" not in response.headers.get("content-type", ""):
                raise ValueError("URL must return an HTML page.")
            content = bytearray()
            for part in response.iter_bytes():
                content.extend(part)
                if len(content) > MAX_BYTES:
                    raise ValueError("Page exceeds the 10 MB limit.")
    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup
    return title[:200], [(None, main.get_text("\n", strip=True))]

def pdf_document(data):
    if not data.startswith(b"%PDF-"):
        raise ValueError("This file is not a PDF.")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("Upload an unencrypted PDF.")
    if len(reader.pages) > 200:
        raise ValueError("PDFs may contain at most 200 pages.")
    pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if not any(text.strip() for _, text in pages):
        raise ValueError("No text found. Scanned PDFs need OCR before upload.")
    return pages

def notion_document(page_id, token):
    matches = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", page_id)
    if not matches:
        raise ValueError("Enter a Notion page URL or page ID.")
    page_id = matches[-1]
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    texts = []
    budget = [0]
    with httpx.Client(base_url="https://api.notion.com/v1/", headers=headers, timeout=20) as client:
        page = client.get(f"pages/{page_id}")
        page.raise_for_status()
        title = "Notion page"
        for prop in page.json().get("properties", {}).values():
            if prop.get("type") == "title":
                title = "".join(t.get("plain_text", "") for t in prop.get("title", [])) or title
        def walk(block_id, depth=0):
            if depth > 12:
                raise ValueError("Notion nesting exceeds 12 levels.")
            cursor = None
            while True:
                budget[0] += 1
                if budget[0] > 80:
                    raise ValueError("Notion page is too large (80 request limit).")
                r = client.get(f"blocks/{block_id}/children", params={"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
                r.raise_for_status()
                result = r.json()
                for block in result["results"]:
                    body = block.get(block["type"], {})
                    rich = body.get("rich_text", [])
                    if block["type"] == "table_row":
                        rich = [item for cell in body.get("cells", []) for item in cell]
                    texts.append("".join(t.get("plain_text", "") for t in rich))
                    if block.get("has_children"):
                        walk(block["id"], depth + 1)
                if not result.get("has_more"):
                    break
                cursor = result["next_cursor"]
        walk(page_id)
    return title[:200], [(None, "\n".join(texts))], page.json().get("url", "")
