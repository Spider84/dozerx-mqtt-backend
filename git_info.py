"""
Git information retrieval for version display.
"""
import subprocess
from logger_config import setup_logger

logger = setup_logger(__name__)

def get_git_info():
    """
    Get git commit hash and branch name if available.
    
    Returns:
        dict: Dictionary with 'commit' and 'branch' keys, None if git not available
    """
    try:
        # Get commit hash
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2
        )
        commit_hash = commit.stdout.strip() if commit.returncode == 0 else None
        
        # Get branch name
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2
        )
        branch_name = branch.stdout.strip() if branch.returncode == 0 else None
        
        if commit_hash or branch_name:
            return {
                "commit": commit_hash,
                "branch": branch_name
            }
        return None
    except FileNotFoundError:
        logger.debug("Git not found in system")
        return None
    except subprocess.TimeoutExpired:
        logger.debug("Git command timeout")
        return None
    except Exception as e:
        logger.debug(f"Error getting git info: {e}")
        return None

def get_version_string():
    """
    Get formatted version string with git information.
    
    Returns:
        str: Version string with git info if available
    """
    git_info = get_git_info()
    if git_info:
        parts = []
        if git_info.get("branch"):
            parts.append(f"branch: {git_info['branch']}")
        if git_info.get("commit"):
            parts.append(f"commit: {git_info['commit']}")
        return f" ({', '.join(parts)})" if parts else ""
    return ""
