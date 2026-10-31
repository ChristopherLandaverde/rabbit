"""RFC 7807 problem responses used by the v2 API."""

from fastapi.responses import JSONResponse


class ApiProblem(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str, fix_hint: str, doc_url: str,
                 headers: dict[str, str] | None = None):
        self.headers = headers or {}
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.fix_hint = fix_hint
        self.doc_url = doc_url


def problem_content(status: int, code: str, title: str, detail: str, fix_hint: str, doc_url: str):
    return {
        "type": f"https://docs.rabbit.example/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "fix_hint": fix_hint,
        "doc_url": doc_url,
    }


def problem(status: int, code: str, title: str, detail: str, fix_hint: str, doc_url: str):
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content=problem_content(status, code, title, detail, fix_hint, doc_url),
    )
