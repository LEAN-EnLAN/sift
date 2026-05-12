"""GitHub OAuth device flow — login sin copiar tokens a mano.

El usuario corre `sift login`, la CLI pide un device code a GitHub,
muestra una URL + código de 8 caracteres, abre el navegador, y espera a que
el usuario autorice. El token queda guardado en ~/.config/sift/config.json
(con fallback a ~/.config/repo-scout/config.json para migración).

Referencia: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from typing import Any

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPE = ""  # no pedimos scopes: alcanza para leer repos públicos y subir rate limit

# Client ID público de la GitHub OAuth App "reposcoutdemo". No es un secreto:
# permite iniciar el device flow, pero el token final sólo lo emite GitHub después
# de que el usuario autoriza en github.com/login/device.
# Para producción/equipos, se puede sobrescribir con GITHUB_CLIENT_ID.
#
# Para registrar una OAuth App gratis:
#   GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
#   Application name: Repo Scout (local)
#   Homepage URL: http://127.0.0.1:8000
#   Callback URL: http://127.0.0.1:8000/callback  (no se usa en device flow real, pero GitHub lo pide)
#   Copiá el Client ID y ponelo en GITHUB_CLIENT_ID.
DEFAULT_CLIENT_ID = "Iv23liV7NaDMRGqtZ9ik"


def _client_id() -> str:
    return os.getenv("GITHUB_CLIENT_ID") or DEFAULT_CLIENT_ID


def config_path() -> Path:
    xdg_config = os.getenv("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    path = Path(xdg_config) / "sift" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _old_config_path() -> Path:
    """Return the old repo-scout config path for backward-compat migration."""
    xdg_config = os.getenv("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(xdg_config) / "repo-scout" / "config.json"


def load_token() -> str | None:
    # 1. Try new sift config first.
    cfg = config_path()
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            token = data.get("github_token")
            if token:
                return token
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Fall back to old repo-scout config path (backward-compat).
    old = _old_config_path()
    if old.exists():
        try:
            data = json.loads(old.read_text(encoding="utf-8"))
            token = data.get("github_token")
            if token:
                # Migrate: save to new path so next read uses sift config.
                save_token(token)
                return token
        except (json.JSONDecodeError, OSError):
            pass

    return None


def save_token(token: str) -> None:
    cfg = config_path()
    data = {}
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data["github_token"] = token
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg.chmod(0o600)


def clear_token() -> None:
    cfg = config_path()
    data = {}
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data.pop("github_token", None)
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _post_json(url: str, payload: dict[str, str]) -> dict[str, Any]:
    """POST con Accept: application/json. GitHub devuelve JSON en el body."""
    data = urllib.parse.urlencode(payload).encode("ascii")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "User-Agent": "sift-zafirus-exercise",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def start_device_flow() -> dict[str, Any]:
    """Pide un device code a GitHub. Devuelve user_code, verification_uri, device_code, interval."""
    payload = {
        "client_id": _client_id(),
    }
    if SCOPE:
        payload["scope"] = SCOPE
    try:
        result = _post_json(DEVICE_CODE_URL, payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub rechazó la solicitud de device code ({e.code}): {body[:400]}") from e

    if "error" in result:
        raise RuntimeError(f"GitHub devolvió error: {result.get('error_description', result['error'])}")

    if "verification_uri" not in result:
        raise RuntimeError(f"Respuesta inesperada de GitHub: {json.dumps(result)}")

    return result


def poll_for_token(device_code: str, interval: int = 5) -> str:
    """Espera a que el usuario autorice el device code. Devuelve el access_token."""
    payload = {
        "client_id": _client_id(),
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }

    started = time.time()
    # GitHub da 15 minutos antes de que expire el device code.
    deadline = started + 15 * 60

    while time.time() < deadline:
        time.sleep(interval)
        try:
            result = _post_json(ACCESS_TOKEN_URL, payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Error al obtener access token ({e.code}): {body[:400]}") from e

        if "access_token" in result:
            return result["access_token"]

        error = result.get("error", "")
        if error == "authorization_pending":
            continue  # el usuario todavía no autorizó, seguimos esperando
        elif error == "slow_down":
            interval += 5  # GitHub pide que esperemos más
            continue
        elif error == "expired_token":
            raise RuntimeError("El código expiró. Volvé a ejecutar `sift login`.")
        elif error == "access_denied":
            raise RuntimeError("Autorización cancelada por el usuario.")
        else:
            raise RuntimeError(f"Error inesperado durante el login: {error} - {result.get('error_description', '')}")

    raise RuntimeError("Timeout: el device code expiró después de 15 minutos.")


def check_token_once(device_code: str) -> dict[str, Any]:
    """Intenta obtener el token UNA sola vez. Para usar desde la web (no bloquea).

    Devuelve {"authenticated": True, "token": str} o {"authenticated": False, "status": "pending"}
    o {"authenticated": False, "error": str}.
    """
    payload = {
        "client_id": _client_id(),
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    try:
        result = _post_json(ACCESS_TOKEN_URL, payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"authenticated": False, "error": f"GitHub error {e.code}: {body[:300]}"}

    if "access_token" in result:
        return {"authenticated": True, "token": result["access_token"]}

    error = result.get("error", "")
    if error == "authorization_pending":
        return {"authenticated": False, "status": "pending"}
    elif error == "slow_down":
        return {"authenticated": False, "status": "pending", "slow_down": True}
    elif error == "expired_token":
        return {"authenticated": False, "error": "El código expiró. Volvé a intentar."}
    elif error == "access_denied":
        return {"authenticated": False, "error": "Autorización cancelada por el usuario."}
    else:
        return {"authenticated": False, "error": f"{error}: {result.get('error_description', '')}"}


def login_interactive(auto_open: bool = True) -> str:
    """Flujo completo de device login para CLI. Devuelve el access token."""
    cid = _client_id()
    if not cid:
        raise RuntimeError(
            "Para usar `sift --login`, configurá GITHUB_CLIENT_ID con una GitHub OAuth App. "
            "Alternativa rápida para automatización: export GITHUB_TOKEN=ghp_xxx. "
            "Instrucciones: https://github.com/settings/developers"
        )

    print("→ Solicitando código de dispositivo a GitHub...")
    device = start_device_flow()

    user_code = device["user_code"]
    verification_uri = device.get("verification_uri", "https://github.com/login/device")
    interval = int(device.get("interval", 5))

    print()
    print(f"   🔗  Abrí {verification_uri}")
    print(f"   🔢  Ingresá el código: {user_code}")
    print()

    if auto_open:
        opened = False
        try:
            with redirect_stderr(StringIO()):
                opened = webbrowser.open(verification_uri)
        except Exception:
            opened = False
        if opened:
            print("   (el navegador debería haberse abierto solo)")
        else:
            print("   (no pude abrir el navegador automáticamente; usá el link de arriba)")

    print("   ⏳  Esperando que autorices en GitHub...")
    token = poll_for_token(device["device_code"], interval)
    save_token(token)
    print()
    print("✅  ¡Login exitoso! El token quedó guardado en:")
    print(f"   {config_path()}")
    return token
