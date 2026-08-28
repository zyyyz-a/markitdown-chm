from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FakeArchive:
    payloads: Mapping[str, bytes] = {}

    @classmethod
    def from_bytes(cls, data: bytes) -> FakeArchive:
        assert data.startswith(b"ITSF")
        return cls()

    def files(self, *, include_system: bool = True) -> list[dict[str, Any]]:
        assert include_system
        return [
            {
                "name": path,
                "size": len(payload),
                "offset": 0,
                "section_id": 0,
                "section": "uncompressed",
                "is_system": path.startswith("::"),
            }
            for path, payload in self.payloads.items()
        ]

    def read(self, name: str, *, max_size: int) -> bytes:
        payload = self.payloads[name]
        if len(payload) > max_size:
            raise RuntimeError("too large")
        return payload


def sample_payloads() -> dict[str, bytes]:
    project = (
        b"""[OPTIONS]\nTitle=Widget SDK Manual\nContents file=toc.hhc\nDefault topic=intro.html\n"""
    )
    toc = b"""<!doctype html><ul>
    <li><object type="text/sitemap">
      <param name="Name" value="Introduction">
      <param name="Local" value="intro.html">
    </object></li>
    <li><ul><li><object type="text/sitemap">
      <param name="Name" value="API Reference">
      <param name="Local" value="guide/api.htm">
    </object></li></ul></li>
    </ul>"""
    intro = b"""<html><head><title>Getting Started</title><script>bad()</script></head>
    <body><h1>Welcome</h1><a href="guide/api.htm">API</a>
    <a href="javascript:bad()" onclick="bad()">unsafe</a></body></html>"""
    api = """<html><head><meta charset="gb18030"><title>API 参考</title></head>
    <body><h1>客户端</h1><p>调用接口。</p><a href="../intro.html">Back</a></body></html>""".encode(
        "gb18030"
    )
    extra = b"<html><title>Appendix</title><body><p>Extra page.</p></body></html>"
    return {
        "/manual.hhp": project,
        "/toc.hhc": toc,
        "/intro.html": intro,
        "/guide/api.htm": api,
        "/z-extra.html": extra,
        "::DataSpace/Storage/MSCompressed/Content": b"system",
    }
