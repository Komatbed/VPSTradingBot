import git
import logging
from typing import Tuple, Optional

logger = logging.getLogger("updater.git")

class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.repo = None
        try:
            self.repo = git.Repo(repo_path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            logger.warning(f"No valid git repository found at {repo_path}. Update features disabled.")
            self.repo = None

    def fetch(self) -> bool:
        if not self.repo: return False
        try:
            logger.info("Fetching origin...")
            self.repo.remotes.origin.fetch()
            return True
        except Exception as e:
            logger.error(f"Git fetch failed: {e}")
            return False

    def check_updates(self) -> Tuple[bool, str]:
        """Returns (has_updates, message)"""
        if not self.repo: 
            return False, "⚠️ Git repo not found. Auto-updates disabled."
        try:
            self.fetch()
            local_commit = self.repo.head.commit
            remote_commit = self.repo.refs['origin/main'].commit # Assuming main
            
            if local_commit != remote_commit:
                msg = f"Update available.\nLocal: {local_commit.hexsha[:7]}\nRemote: {remote_commit.hexsha[:7]}\nMsg: {remote_commit.message}"
                return True, msg
            return False, "System is up to date."
        except Exception as e:
            return False, f"Check failed: {e}"

    def update_hard(self) -> bool:
        """
        Executes: git reset --hard origin/main
        WARNING: Overwrites tracked files.
        """
        if not self.repo: return False
        try:
            logger.info("Resetting to origin/main...")
            self.repo.git.reset('--hard', 'origin/main')
            return True
        except Exception as e:
            logger.error(f"Git reset failed: {e}")
            return False

    def get_current_version(self) -> str:
        if self.repo:
            try:
                return self.repo.head.commit.hexsha[:7]
            except Exception:
                pass
        
        # Fallback: try to read version.txt
        import os
        version_file = os.path.join(self.repo_path, "version.txt")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass

        return "unknown (no-git)"
