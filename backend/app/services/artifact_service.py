from pathlib import Path

from app.exceptions import NotFoundError


class ArtifactService:
    @staticmethod
    def _artifacts_dir(project_path: str, issue_id: str) -> Path:
        return Path(project_path) / ".manager_ai" / "issues" / issue_id / "artifacts"

    @staticmethod
    def save_artifact(project_path: str, issue_id: str, filename: str, content: str) -> str:
        dir_path = ArtifactService._artifacts_dir(project_path, issue_id)
        dir_path.mkdir(parents=True, exist_ok=True)
        filepath = dir_path / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    @staticmethod
    def read_artifact(project_path: str, issue_id: str, filename: str) -> str:
        filepath = ArtifactService._artifacts_dir(project_path, issue_id) / filename
        if not filepath.exists():
            raise NotFoundError(f"Artifact not found: {filename}")
        return filepath.read_text(encoding="utf-8")

    @staticmethod
    def list_artifacts(project_path: str, issue_id: str) -> list[str]:
        dir_path = ArtifactService._artifacts_dir(project_path, issue_id)
        if not dir_path.exists():
            return []
        return sorted([f.name for f in dir_path.iterdir() if f.is_file()])
