"""麦当劳 MCP (Streamable HTTP) 最小客户端。

协议要点（见 https://github.com/M-China/mcd-mcp-server）：
- 接入地址 https://mcp.mcd.cn，Streamable HTTP 传输
- 请求头 Authorization: Bearer <MCP_TOKEN>
- 限流 600 次/分钟
- 流程：initialize -> notifications/initialized -> tools/list -> tools/call

只依赖标准库。兼容：
- application/json 与 text/event-stream 两种响应体
- 通知（无 id 的请求）返回 202 空响应（MCP 规范行为，不算错误）
- 网关自定义错误信封 {"code": "0001", "msg": "系统错误", "data": null}
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

MCP_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-03-26"
USER_AGENT = "mcd-wrapped/1.0 (+https://github.com) python-urllib"


class MCPError(RuntimeError):
    pass


class McDonaldsMCP:
    def __init__(self, token: str, url: str = MCP_URL, timeout: int = 30, verbose: bool = False):
        if not token:
            raise MCPError("缺少 MCP Token，请先在 https://open.mcd.cn/mcp 免费申请")
        self.token = token
        self.url = url
        self.timeout = timeout
        self.verbose = verbose
        self.session_id: Optional[str] = None
        self._id = 0
        self._tools: Optional[List[Dict[str, Any]]] = None

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[mcp] {msg}", file=sys.stderr)

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    # ---------- 传输层 ----------

    def _post(self, payload: Dict[str, Any], expect_response: bool = True) -> Dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": USER_AGENT,
            "mcp-protocol-version": PROTOCOL_VERSION,
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", 200)
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                raise MCPError(f"401 Token 无效或已过期（响应：{detail}）")
            if e.code == 403:
                raise MCPError(f"403 被拒绝（响应：{detail}）。Token 可能未激活，或请求被网关拦截")
            if e.code == 429:
                raise MCPError("429 触发限流（600 次/分钟），请稍后重试")
            raise MCPError(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            raise MCPError(f"网络错误: {e.reason}")

        self._log(f"{payload.get('method')} -> HTTP {status}, {len(raw)} bytes")
        return self._parse_body(raw, expect_response=expect_response, status=status)

    @staticmethod
    def _parse_body(raw: str, expect_response: bool = True, status: int = 200) -> Dict[str, Any]:
        text = raw.strip()
        if not text:
            if not expect_response:
                return {}  # 通知按 MCP 规范返回 202 空响应，属正常
            raise MCPError(
                f"服务器返回空响应（HTTP {status}）。常见原因：Token 无效/未激活、"
                "网络代理干扰、或服务端暂不可用。可先用 --selftest 排查。"
            )
        # SSE 响应：收集所有 data: 负载，取最后一个可解析的 JSON-RPC 消息
        if text.startswith("event:") or text.startswith("data:") or "\ndata:" in text:
            payloads = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")]
            parsed: List[Dict[str, Any]] = []
            for p in payloads:
                if not p:
                    continue
                try:
                    obj = json.loads(p)
                    if isinstance(obj, dict):
                        parsed.append(obj)
                except json.JSONDecodeError:
                    continue
            if not parsed:
                raise MCPError(f"SSE 响应中无可解析的 data 负载: {raw[:200]}")
            text = json.dumps(parsed[-1], ensure_ascii=False)
        try:
            resp = json.loads(text)
        except json.JSONDecodeError:
            raise MCPError(f"响应不是合法 JSON: {text[:200]}")
        if not isinstance(resp, dict):
            raise MCPError(f"响应不是 JSON 对象: {text[:200]}")
        return resp

    @staticmethod
    def _unwrap(resp: Dict[str, Any]) -> Dict[str, Any]:
        """兼容网关自定义信封 {"code":"0000","msg":"ok","data":{jsonrpc...}}。"""
        if "data" in resp and ("code" in resp or "msg" in resp) and "result" not in resp and "error" not in resp:
            data = resp.get("data")
            code = str(resp.get("code", ""))
            if isinstance(data, dict) and ("result" in data or "error" in data or "jsonrpc" in data):
                return data
            if code not in ("0000", "0", "SUCCESS", "success", ""):
                raise MCPError(f"网关返回错误 code={resp.get('code')} msg={resp.get('msg')}")
            return data if isinstance(data, dict) else {}
        return resp

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._unwrap(self._post(payload))
        if "error" in resp:
            err = resp["error"]
            raise MCPError(f"MCP 错误 {err.get('code')}: {err.get('message')}")
        if "result" in resp:
            return resp["result"]
        if "msg" in resp or "code" in resp:
            raise MCPError(f"网关返回错误 code={resp.get('code')} msg={resp.get('msg')}")
        raise MCPError(f"无法识别的响应格式: {str(resp)[:200]}")

    def _notify(self, method: str) -> None:
        # 通知无响应体（202 Accepted），失败也不影响主流程
        try:
            self._post({"jsonrpc": "2.0", "method": method}, expect_response=False)
        except MCPError as e:
            self._log(f"通知 {method} 失败（已忽略）: {e}")

    # ---------- 会话 ----------

    def connect(self) -> None:
        try:
            self._rpc(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcd-wrapped", "version": "1.0.0"},
                },
            )
        except MCPError as e:
            raise MCPError(f"initialize 握手失败：{e}")
        self._notify("notifications/initialized")

    # ---------- 工具 ----------

    def list_tools(self, refresh: bool = False) -> List[Dict[str, Any]]:
        if self._tools is None or refresh:
            self._tools = self._rpc("tools/list").get("tools", [])
        return self._tools

    def tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        for tool in self.list_tools():
            if tool.get("name") == name:
                return tool
        return None

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if result.get("isError"):
            raise MCPError(f"工具 {name} 调用失败: {' '.join(texts)[:300]}")
        if not texts:
            return result
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return joined

    # ---------- 自检 ----------

    def selftest(self) -> List[str]:
        """连通性自检：握手 + 拉取工具列表，返回工具名列表。"""
        self.connect()
        self._log("握手成功，拉取工具列表…")
        return [t.get("name", "?") for t in self.list_tools()]
