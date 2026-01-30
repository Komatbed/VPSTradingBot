import git
import logging
from typing import Tuple, Optional

logger = logging.getLogger("updater.git")

class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            logger.error("Invalid git repository")
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
        if not self.repo: return False, "No git repo"
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
        if not self.repo: return "unknown"
        return self.repo.head.commit.hexsha[:7]
