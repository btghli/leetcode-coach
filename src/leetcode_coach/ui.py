"""Small browser launcher for the hosted official Agent Chat UI."""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode


AGENT_CHAT_BASE_URL = "https://agentchat.vercel.app"
DEPLOYMENT_URL = "http://localhost:2024"
GRAPH_ID = "leetcode_coach"
AGENT_CHAT_URL = f"{AGENT_CHAT_BASE_URL}?{urlencode({'apiUrl': DEPLOYMENT_URL, 'assistantId': GRAPH_ID})}"


def _server_command(root: Path) -> list[str]:
    local = root / ".venv" / "bin" / "langgraph"
    executable = str(local) if local.is_file() else shutil.which("langgraph")
    if not executable:
        raise RuntimeError("Agent Server 未安装。请运行：.venv/bin/pip install -e '.[ui]'")
    return [executable, "dev", "--no-browser", "--port", "2024"]


def _wait_for_server(host: str = "127.0.0.1", port: int = 2024, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    try:
        command = _server_command(root)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    print("正在启动 LeetCode Coach 网页服务…")
    server = subprocess.Popen(command, cwd=root)
    try:
        if not _wait_for_server():
            print("Agent Server 启动超时，请查看上面的错误信息。", file=sys.stderr)
            return 1
        print(f"Agent Chat UI: {AGENT_CHAT_URL}")
        print(f"Deployment URL: {DEPLOYMENT_URL}")
        print(f"Graph ID: {GRAPH_ID}")
        print("浏览器中首次填写以上两项；LangSmith API key 留空。关闭此窗口会停止本地服务。")
        webbrowser.open(AGENT_CHAT_URL)
        return server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
