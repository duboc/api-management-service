import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GcloudError(Exception):
    """Raised when a gcloud command fails."""

    def __init__(self, message: str, returncode: int = 1) -> None:
        super().__init__(message)
        self.returncode = returncode


async def run_gcloud(
    args: list[str],
    project: Optional[str] = None,
    parse_json: bool = True,
    timeout: int = 300,
) -> dict | list | str | None:
    """Run a gcloud CLI command asynchronously.

    Args:
        args: Command arguments after 'gcloud'.
        project: GCP project ID. Appended as --project flag if provided.
        parse_json: If True, append --format=json and parse output.
        timeout: Max seconds to wait.

    Returns:
        Parsed JSON (dict/list) if parse_json=True, else raw stdout string.

    Raises:
        GcloudError: If command exits non-zero.
    """
    cmd = ["gcloud"] + args
    if project:
        cmd.append(f"--project={project}")
    if parse_json:
        cmd.append("--format=json")
    cmd.append("--quiet")

    logger.info("Running: %s", " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        raise GcloudError(f"gcloud command timed out after {timeout}s")

    stdout_str = stdout.decode().strip()
    stderr_str = stderr.decode().strip()

    if process.returncode != 0:
        logger.error(
            "gcloud failed (rc=%d): %s", process.returncode, stderr_str
        )
        raise GcloudError(stderr_str, process.returncode)

    if not stdout_str:
        return None

    if parse_json:
        try:
            return json.loads(stdout_str)
        except json.JSONDecodeError:
            logger.warning(
                "Could not parse JSON from gcloud output, returning raw"
            )
            return stdout_str

    return stdout_str
