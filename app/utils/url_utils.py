from urllib.parse import urlsplit, urlunsplit, quote


def encode_url(url: str) -> str:
    """
    对 URL 中的 path 和 query 做安全编码，避免 URL 中有中文时报错。
    """
    parts = urlsplit(url)

    scheme = parts.scheme
    netloc = parts.netloc
    path = quote(parts.path, safe="/%")
    query = quote(parts.query, safe="=&%:/?+-_.~")
    fragment = quote(parts.fragment, safe="=&%:/?+-_.~")

    return urlunsplit((scheme, netloc, path, query, fragment))