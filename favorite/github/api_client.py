import base64
import json
import os
from pathlib import Path

import requests


class GitHubClient:
  BASE = "https://api.github.com"

  def __init__(self, token: str, owner: str, repo: str, branch: str = "main"):
      self.token = token
      self.owner = owner
      self.repo = repo
      self.branch = branch
      self._headers = {
          "Authorization": f"Bearer {token}",
          "Accept": "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
      }

  def _url(self, path: str) -> str:
      return f"{self.BASE}{path}"

  def ensure_repo_exists(self) -> bool:
      r = requests.get(
          self._url(f"/repos/{self.owner}/{self.repo}"),
          headers=self._headers,
          timeout=15,
      )
      if r.status_code == 200:
          return True
      if r.status_code == 404:
          body = {
              "name": self.repo,
              "description": "FavoriteCLI — Python CLI AI-agent for Termux/Android",
              "private": False,
              "auto_init": True,
          }
          cr = requests.post(
              self._url("/user/repos"),
              headers=self._headers,
              json=body,
              timeout=15,
          )
          return cr.status_code in (200, 201)
      return False

  def _get_file_sha(self, path: str) -> str | None:
      r = requests.get(
          self._url(f"/repos/{self.owner}/{self.repo}/contents/{path}"),
          headers=self._headers,
          params={"ref": self.branch},
          timeout=10,
      )
      if r.status_code == 200:
          return r.json().get("sha")
      return None

  def upsert_file(self, path: str, content: str | bytes, message: str) -> bool:
      if isinstance(content, str):
          content = content.encode("utf-8")
      encoded = base64.b64encode(content).decode()
      sha = self._get_file_sha(path)
      body: dict = {
          "message": message,
          "content": encoded,
          "branch": self.branch,
      }
      if sha:
          body["sha"] = sha
      r = requests.put(
          self._url(f"/repos/{self.owner}/{self.repo}/contents/{path}"),
          headers=self._headers,
          json=body,
          timeout=15,
      )
      return r.status_code in (200, 201)

  def push_directory(self, local_dir: Path, commit_message: str) -> dict:
      results = {"ok": [], "fail": []}
      for file_path in local_dir.rglob("*"):
          if file_path.is_dir():
              continue
          rel = file_path.relative_to(local_dir)
          rel_str = str(rel).replace(os.sep, "/")
          skip_patterns = [".git/", "__pycache__/", ".pyc", "*.session"]
          if any(p.strip("*") in rel_str for p in skip_patterns):
              continue
          try:
              content = file_path.read_bytes()
              ok = self.upsert_file(rel_str, content, commit_message)
              if ok:
                  results["ok"].append(rel_str)
              else:
                  results["fail"].append(rel_str)
          except Exception as e:
              results["fail"].append(f"{rel_str} ({e})")
      return results
