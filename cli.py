import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://api:8000")


def resolve_token(cli_token: str | None = None) -> str:
    if cli_token is not None and cli_token.strip():
        return cli_token.strip()
    return os.getenv("CLI_TOKEN", "").strip()


def request_api(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            return resp.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            detail = json.loads(raw)
        except ValueError:
            detail = {"detail": raw or exc.reason}
        return exc.code, detail


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="CLI oficial do CRUD de Produtos (Loja Virtual)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help="URL base da API (padrao: $API_BASE_URL ou http://api:8000)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Bearer token CLI (ou defina a variavel de ambiente CLI_TOKEN)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser(
        "health",
        help="Verifica o healthcheck exclusivo da CLI (/api/cli/health)",
    )
    health_parser.add_argument(
        "--auth",
        action="store_true",
        help="Envia o Bearer token para validar autenticacao opcional no healthcheck",
    )

    token_parser = subparsers.add_parser(
        "token",
        help="Autentica na API (/api/cli/token) e emite um Bearer token para a CLI",
    )
    token_parser.add_argument("--username", required=True, help="Usuario de acesso")
    token_parser.add_argument("--password", required=True, help="Senha de acesso")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "health":
        token = resolve_token(args.token) if args.auth else None
        if args.auth and not token:
            print(
                json.dumps(
                    {"status": "error", "detail": "Informe --token ou defina CLI_TOKEN"}
                ),
                file=sys.stderr,
            )
            return 1
        status, body = request_api(args.base_url, "GET", "/api/cli/health", token=token)
    else:
        status, body = request_api(
            args.base_url,
            "POST",
            "/api/cli/token",
            payload={"username": args.username, "password": args.password},
        )

    print(json.dumps(body, ensure_ascii=False))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
