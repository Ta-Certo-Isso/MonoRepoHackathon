from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]


def stream_output(name: str, proc: subprocess.Popen) -> None:
    assert proc.stdout is not None
    for raw in iter(proc.stdout.readline, b""):
        try:
            text = raw.decode("utf-8", errors="replace").rstrip()
        except Exception:  # pragma: no cover - defensive decode
            text = str(raw)
        print(f"[{name}] {text}")
    proc.stdout.close()


def wait_for_tunnel(port: int, retries: int = 30, delay: float = 1.0) -> str:
    api_url = "http://127.0.0.1:4040/api/tunnels"
    for _ in range(retries):
        try:
            with urlopen(api_url) as resp:  # nosec - local call
                data = json.load(resp)
                tunnels = data.get("tunnels", [])
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        public = tunnel.get("public_url", "")
                        if public:
                            return public
        except URLError:
            pass
        time.sleep(delay)
    raise RuntimeError("Não consegui obter o endereço do ngrok em 30s. Verifique se o comando está rodando.")


def launch_process(cmd: list[str], name: str) -> subprocess.Popen:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        creationflags=creationflags,
    )
    thread = threading.Thread(target=stream_output, args=(name, proc), daemon=True)
    thread.start()
    return proc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inicia um túnel ngrok HTTPS e acompanha os logs do Evolution API."
    )
    parser.add_argument("--port", type=int, default=8080, help="Porta local exposta pelo Evolution (default: 8080)")
    default_compose = REPO_ROOT / "Nichols" / "evolution" / "docker-compose.yml"
    parser.add_argument(
        "--compose-file",
        type=Path,
        default=default_compose,
        help=f"Arquivo docker-compose a ser monitorado (default: {default_compose})",
    )
    parser.add_argument(
        "--service",
        default="evolution_api",
        help="Nome do serviço a monitorar com docker compose logs (default: evolution_api)",
    )
    args = parser.parse_args()

    compose_file = args.compose_file
    if not compose_file.exists():
        raise FileNotFoundError(f"docker-compose não encontrado em {compose_file}")

    ngrok_cmd = ["ngrok", "http", str(args.port)]
    logs_cmd = ["docker", "compose", "-f", str(compose_file), "logs", "-f", args.service]

    processes: list[subprocess.Popen] = []

    def shutdown() -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    try:
        print(f"Iniciando ngrok: {' '.join(ngrok_cmd)}")
        ngrok_proc = launch_process(ngrok_cmd, "ngrok")
        processes.append(ngrok_proc)

        url = wait_for_tunnel(args.port)
        print(f"→ Túnel HTTPS ativo: {url}")
        os.environ["NGROK_PUBLIC_URL"] = url

        print(f"Iniciando logs: {' '.join(logs_cmd)}")
        logs_proc = launch_process(logs_cmd, "evolution_api")
        processes.append(logs_proc)

        while any(proc.poll() is None for proc in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando processos…")
    finally:
        shutdown()


if __name__ == "__main__":
    main()

