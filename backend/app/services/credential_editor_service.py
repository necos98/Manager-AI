import json
import os
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.credential_preset import CredentialPreset
from app.services.credential_service import CredentialService


SENSITIVE_PATTERNS = ("KEY", "SECRET", "TOKEN")


def _is_sensitive_key(key: str) -> bool:
    return any(p in key.upper() for p in SENSITIVE_PATTERNS)


def _credentials_path() -> Path:
    home = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ".")))
    return home / ".claude" / "credentials.json"


def _read_credentials_file() -> dict:
    path = _credentials_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_credentials_file(data: dict) -> None:
    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(".json.bak"))
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class CredentialEditorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -- file ops --

    def read_env(self) -> dict[str, str]:
        data = _read_credentials_file()
        return data.get("env", {})

    def write_env(self, variables: dict[str, str]) -> dict[str, str]:
        data = _read_credentials_file()
        data["env"] = variables
        _write_credentials_file(data)
        return variables

    # -- preset CRUD --

    async def list_presets(self) -> list[CredentialPreset]:
        result = await self.db.execute(
            select(CredentialPreset).order_by(CredentialPreset.name)
        )
        return list(result.scalars().all())

    async def get_preset(self, preset_id: str) -> CredentialPreset:
        result = await self.db.execute(
            select(CredentialPreset).where(CredentialPreset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if preset is None:
            raise NotFoundError(f"Preset '{preset_id}' not found")
        return preset

    async def create_preset(self, name: str, variables: dict[str, str]) -> CredentialPreset:
        plain = {}
        encrypted = {}
        f = CredentialService._get_fernet()
        for k, v in variables.items():
            if _is_sensitive_key(k):
                encrypted[k] = f.encrypt(v.encode()).decode()
            else:
                plain[k] = v
        preset = CredentialPreset(
            name=name,
            variables=json.dumps(plain),
            encrypted_fields=json.dumps(encrypted),
        )
        self.db.add(preset)
        await self.db.flush()
        return preset

    async def update_preset(self, preset_id: str, name: str | None, variables: dict[str, str] | None) -> CredentialPreset:
        preset = await self.get_preset(preset_id)
        if name is not None:
            preset.name = name
        if variables is not None:
            plain = {}
            encrypted = {}
            f = CredentialService._get_fernet()
            for k, v in variables.items():
                if _is_sensitive_key(k):
                    encrypted[k] = f.encrypt(v.encode()).decode()
                else:
                    plain[k] = v
            preset.variables = json.dumps(plain)
            preset.encrypted_fields = json.dumps(encrypted)
        await self.db.flush()
        return preset

    async def delete_preset(self, preset_id: str) -> None:
        preset = await self.get_preset(preset_id)
        await self.db.delete(preset)
        await self.db.flush()

    async def apply_preset(self, preset_id: str) -> dict[str, str]:
        preset = await self.get_preset(preset_id)
        plain = json.loads(preset.variables) if preset.variables else {}
        encrypted_raw = json.loads(preset.encrypted_fields) if preset.encrypted_fields else {}
        f = CredentialService._get_fernet()
        decrypted = {}
        for k, v in encrypted_raw.items():
            try:
                decrypted[k] = f.decrypt(v.encode()).decode()
            except Exception:
                decrypted[k] = ""
        merged = {**plain, **decrypted}
        return self.write_env(merged)

    # -- helpers --

    @staticmethod
    def decode_preset(preset: CredentialPreset) -> dict:
        plain = json.loads(preset.variables) if preset.variables else {}
        encrypted_raw = json.loads(preset.encrypted_fields) if preset.encrypted_fields else {}
        has_secrets = bool(encrypted_raw)
        f = CredentialService._get_fernet()
        all_vars = dict(plain)
        for k, v in encrypted_raw.items():
            try:
                all_vars[k] = f.decrypt(v.encode()).decode()
            except Exception:
                all_vars[k] = ""
        return {
            "id": preset.id,
            "name": preset.name,
            "variables": all_vars,
            "has_secrets": has_secrets,
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }
