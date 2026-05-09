from pathlib import Path

from .api_client import GitHubClient
from ..config.loader import get_config


def push_project(message: str = "chore: auto-push") -> dict:
  cfg = get_config()
  client = GitHubClient(
      token=cfg.github_token,
      owner=cfg.github_owner,
      repo=cfg.github_repo,
      branch=cfg.github_branch,
  )
  project_root = Path(__file__).resolve().parent.parent.parent
  client.ensure_repo_exists()
  return client.push_directory(project_root, message)
