import ipaddress
import os
import re
import socket
import time

import paramiko
from flask import Flask, jsonify, request, send_from_directory


FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

USERNAME = os.getenv("ROUTER_USER", "admin")
PASSWORD = os.getenv("ROUTER_PASSWORD", "cisco")

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
INITIAL_PROMPT = re.compile(
    r"([A-Za-z0-9_.:/-]+)(?:\([^\r\n()]*\))*[>#][ \t]*"
)
IOS_ERROR = re.compile(
    r"(?mi)^%\s*(?:Invalid input|Incomplete command|"
    r"Ambiguous command|Unknown command|"
    r"Authorization failed|Error)"
)


class RouterCommandError(Exception):
    pass


def read_until_prompt(channel, pattern, timeout=15):
    """Collect output until the router prompt returns."""
    buffer = bytearray()
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if channel.recv_ready():
            chunk = channel.recv(4096)

            if not chunk:
                raise RouterCommandError("Router closed the SSH channel.")

            buffer.extend(chunk)

            if len(buffer) > 1_000_000:
                raise RouterCommandError("Router output is too large.")

            text = buffer.decode("utf-8", errors="replace")
            text = ANSI_ESCAPE.sub("", text).replace("\r", "")
            last_line = text.rstrip().split("\n")[-1]

            if pattern.fullmatch(last_line):
                return text

        elif channel.closed:
            raise RouterCommandError("Router closed the SSH channel.")

        time.sleep(0.05)

    partial = buffer.decode("utf-8", errors="replace")
    message = "Timed out waiting for the router prompt."

    if partial.strip():
        message += "\n\nPartial output:\n" + partial.strip()

    raise RouterCommandError(message)


def execute_router_command(router_ip, command):
    ssh = paramiko.SSHClient()

    # Accept unknown host keys for this isolated classroom lab.
    # Real deployments should verify the router's stored host key.
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=router_ip,
            port=22,
            username=USERNAME,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
            channel_timeout=10,
        )

        shell = ssh.invoke_shell(width=200, height=1000)
        shell.settimeout(10)

        initial_output = read_until_prompt(shell, INITIAL_PROMPT)
        initial_line = initial_output.rstrip().split("\n")[-1]
        hostname = INITIAL_PROMPT.fullmatch(initial_line).group(1)

        prompt = re.compile(
            re.escape(hostname)
            + r"(?:\([^\r\n()]*\))*[>#][ \t]*"
        )

        # Prevent long output from stopping at --More--.
        shell.sendall("terminal length 0\n")
        setup_output = read_until_prompt(shell, prompt)

        if IOS_ERROR.search(setup_output):
            raise RouterCommandError(
                "Could not disable pagination:\n" + setup_output
            )

        shell.sendall(command + "\n")
        raw_output = read_until_prompt(shell, prompt)

        lines = raw_output.rstrip().splitlines()

        if lines and prompt.fullmatch(lines[-1]):
            lines.pop()

        if lines and lines[0].strip() == command:
            lines.pop(0)

        output = "\n".join(lines).strip()

        if IOS_ERROR.search(output):
            raise RouterCommandError(output)

        return output or "Command completed with no text output."

    finally:
        ssh.close()


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.post("/api/execute")
def execute():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False, message="A JSON object is required."
        ), 400

    router_ip = data.get("ip")
    command = data.get("command")

    if not isinstance(router_ip, str) or not isinstance(command, str):
        return jsonify(
            success=False, message="Router IP and command must be text."
        ), 400

    router_ip = router_ip.strip()
    command = command.strip()

    try:
        address = ipaddress.IPv4Address(router_ip)
    except ValueError:
        return jsonify(
            success=False, message="Enter a valid IPv4 router address."
        ), 400

    if (
        not command
        or len(command) > 500
        or any(ord(char) < 32 or ord(char) == 127 for char in command)
    ):
        return jsonify(
            success=False,
            message="Enter one single-line command, up to 500 characters.",
        ), 400

    try:
        output = execute_router_command(str(address), command)
        return jsonify(success=True, output=output)

    except paramiko.AuthenticationException:
        message = "SSH authentication failed. Check username and password."
    except RouterCommandError as error:
        message = str(error)
    except (socket.timeout, TimeoutError):
        message = "SSH connection timed out. Check router connectivity."
    except paramiko.SSHException as error:
        message = f"SSH error: {error}"
    except OSError as error:
        message = f"Network error: {error}"
    except Exception:
        app.logger.exception("Unexpected router execution error")
        message = "Unexpected server error. Check the container logs."

    return jsonify(success=False, message=message), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
