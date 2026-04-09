import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gcloud_runner import GcloudError, run_gcloud


def _make_process(returncode=0, stdout=b"", stderr=b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.fixture
def mock_subprocess():
    with patch("app.services.gcloud_runner.asyncio.create_subprocess_exec") as mock:
        yield mock


class TestRunGcloud:
    async def test_basic_command_with_json(self, mock_subprocess):
        data = [{"name": "my-api"}]
        proc = _make_process(stdout=json.dumps(data).encode())
        mock_subprocess.return_value = proc

        result = await run_gcloud(["api-gateway", "apis", "list"], project="my-proj")

        assert result == data
        call_args = mock_subprocess.call_args[0]
        assert call_args[0] == "gcloud"
        assert "api-gateway" in call_args
        assert "--project=my-proj" in call_args
        assert "--format=json" in call_args
        assert "--quiet" in call_args

    async def test_no_project(self, mock_subprocess):
        proc = _make_process(stdout=b'"ok"')
        mock_subprocess.return_value = proc

        await run_gcloud(["version"])

        call_args = mock_subprocess.call_args[0]
        assert not any(arg.startswith("--project=") for arg in call_args)

    async def test_parse_json_false(self, mock_subprocess):
        proc = _make_process(stdout=b"Created API [my-api].")
        mock_subprocess.return_value = proc

        result = await run_gcloud(
            ["api-gateway", "apis", "create", "my-api"], parse_json=False
        )

        assert result == "Created API [my-api]."
        call_args = mock_subprocess.call_args[0]
        assert "--format=json" not in call_args

    async def test_empty_stdout_returns_none(self, mock_subprocess):
        proc = _make_process(stdout=b"")
        mock_subprocess.return_value = proc

        result = await run_gcloud(["something"])
        assert result is None

    async def test_nonzero_returncode_raises(self, mock_subprocess):
        proc = _make_process(returncode=1, stderr=b"ERROR: API not found")
        mock_subprocess.return_value = proc

        with pytest.raises(GcloudError, match="API not found"):
            await run_gcloud(["api-gateway", "apis", "describe", "bad"])

    async def test_nonzero_returncode_preserves_code(self, mock_subprocess):
        proc = _make_process(returncode=2, stderr=b"error")
        mock_subprocess.return_value = proc

        with pytest.raises(GcloudError) as exc_info:
            await run_gcloud(["fail"])
        assert exc_info.value.returncode == 2

    async def test_timeout_kills_process(self, mock_subprocess):
        proc = AsyncMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        proc.kill = MagicMock()
        mock_subprocess.return_value = proc

        with pytest.raises(GcloudError, match="timed out"):
            await run_gcloud(["slow-cmd"], timeout=1)

        proc.kill.assert_called_once()

    async def test_invalid_json_returns_raw(self, mock_subprocess):
        proc = _make_process(stdout=b"not-json-content")
        mock_subprocess.return_value = proc

        result = await run_gcloud(["something"], parse_json=True)
        assert result == "not-json-content"


class TestGcloudError:
    def test_message(self):
        err = GcloudError("something broke", returncode=3)
        assert str(err) == "something broke"
        assert err.returncode == 3

    def test_default_returncode(self):
        err = GcloudError("fail")
        assert err.returncode == 1
