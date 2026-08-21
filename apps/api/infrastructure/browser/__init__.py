"""浏览器基础设施实现。"""

from infrastructure.browser.http_browser import HttpBrowser
from infrastructure.browser.stub_browser import StubBrowser

__all__ = ["HttpBrowser", "StubBrowser"]
