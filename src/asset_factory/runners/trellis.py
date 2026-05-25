from __future__ import annotations

import json
import os
import shlex
import string
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from asset_factory.runners.base import RunnerRequest, RunnerResult

_SUPPORTED_PLACEHOLDERS = frozenset({"image", "output", "resolution"})
_BATCH_READY_MARKER = "READY"
_BATCH_OK_PREFIX = "OK\t"
_BATCH_ERR_PREFIX = "ERR\t"


@dataclass(frozen=True)
class TrellisCommandRunner:
    command_template: str

    runner_type = "trellis"
    runner_version = "trellis2-command"

    @classmethod
    def from_env(cls) -> TrellisCommandRunner:
        command_template = os.environ.get("TRELLIS2_COMMAND")
        if not command_template:
            raise RuntimeError(
                "TRELLIS2_COMMAND is required, for example: "
                "python /path/to/trellis2.py {image} {output}"
            )
        return cls(command_template=command_template)

    def run(
        self,
        request: RunnerRequest,
        on_start: Callable[[subprocess.Popen[str]], None] | None = None,
    ) -> RunnerResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        raw_glb_path = request.output_dir / "raw.glb"
        report_path = request.output_dir / "raw_report.json"

        started_at = datetime.now(tz=UTC)
        command: str | None = None
        command_args: list[str] | None = None
        returncode: int | None = None
        stdout: str | None = None
        stderr: str | None = None
        error_type: str | None = None
        error_message: str | None = None

        try:
            command_args = _build_command_args(self.command_template, request)
            command = shlex.join(command_args)
            process = subprocess.Popen(
                command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if on_start is not None:
                on_start(process)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode != 0:
                error_type = "NonZeroReturnCodeError"
                error_message = f"TRELLIS command exited with status {returncode}"
            elif not raw_glb_path.exists():
                error_type = "MissingRawGlbError"
                error_message = f"TRELLIS command completed but did not create {raw_glb_path}"
        except (OSError, ValueError) as exc:
            error_type = type(exc).__name__
            error_message = str(exc)
        ended_at = datetime.now(tz=UTC)

        success = error_type is None and returncode == 0 and raw_glb_path.exists()
        _write_report(
            report_path=report_path,
            runner_type=self.runner_type,
            runner_version=self.runner_version,
            request=request,
            raw_glb_path=raw_glb_path,
            started_at=started_at,
            ended_at=ended_at,
            success=success,
            command_template=self.command_template,
            command=command,
            command_args=command_args,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            error_type=error_type,
            error_message=error_message,
        )

        if not success:
            raise RuntimeError(f"TRELLIS command failed; see {report_path}")

        return RunnerResult(
            raw_glb_path=raw_glb_path,
            report_path=report_path,
            runner_type=self.runner_type,
            runner_version=self.runner_version,
            success=True,
        )


def _build_command_args(command_template: str, request: RunnerRequest) -> list[str]:
    placeholder_values = {
        "image": str(request.concept_image.resolve()),
        "output": str(request.output_dir.resolve()),
        "resolution": str(request.resolution),
    }
    sentinel_command, placeholder_tokens = _build_sentinel_command(command_template)
    try:
        sentinel_args = shlex.split(sentinel_command)
    except ValueError as exc:
        raise ValueError(f"Invalid TRELLIS2_COMMAND shell syntax: {exc}") from exc
    if not sentinel_args:
        raise ValueError("TRELLIS2_COMMAND must include an executable")

    command_args: list[str] = []
    for arg in sentinel_args:
        for token, placeholder in placeholder_tokens.items():
            arg = arg.replace(token, placeholder_values[placeholder])
        command_args.append(arg)
    return command_args


def _build_sentinel_command(command_template: str) -> tuple[str, dict[str, str]]:
    formatter = string.Formatter()
    parts: list[str] = []
    placeholder_tokens: dict[str, str] = {}
    try:
        parsed_template = formatter.parse(command_template)
        for index, (
            literal_text,
            field_name,
            format_spec,
            conversion,
        ) in enumerate(parsed_template):
            parts.append(literal_text)
            if field_name is None:
                continue
            if field_name not in _SUPPORTED_PLACEHOLDERS:
                raise ValueError(
                    f"Unsupported placeholder {{{field_name}}}; supported placeholders are "
                    "{image}, {output}, and {resolution}"
                )
            if format_spec or conversion:
                raise ValueError(
                    f"Unsupported format syntax for {{{field_name}}}; use only "
                    "{image}, {output}, or {resolution}"
                )
            token = f"__TRELLIS_PLACEHOLDER_{index}_{uuid.uuid4().hex}__"
            placeholder_tokens[token] = field_name
            parts.append(token)
    except ValueError as exc:
        if str(exc).startswith(("Unsupported placeholder", "Unsupported format syntax")):
            raise
        raise ValueError(f"Invalid TRELLIS2_COMMAND format: {exc}") from exc
    return "".join(parts), placeholder_tokens


def _write_report(
    *,
    report_path: Path,
    runner_type: str,
    runner_version: str,
    request: RunnerRequest,
    raw_glb_path: Path,
    started_at: datetime,
    ended_at: datetime,
    success: bool,
    command_template: str,
    command: str | None,
    command_args: list[str] | None,
    returncode: int | None,
    stdout: str | None,
    stderr: str | None,
    error_type: str | None,
    error_message: str | None,
) -> None:
    report = {
        "runner_type": runner_type,
        "runner_version": runner_version,
        "command_template": command_template,
        "command": command,
        "command_args": command_args,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "raw_glb": str(raw_glb_path),
        "resolution": request.resolution,
        "concept_image": str(request.concept_image),
        "success": success,
    }
    if error_type is not None:
        report["error_type"] = error_type
    if error_message is not None:
        report["error_message"] = error_message
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class BatchTrellisCommandRunner:
    """One warm subprocess; multiplex many RunnerRequests over its stdin.

    The command (TRELLIS2_BATCH_COMMAND) must launch a process that prints
    "READY" once initialization is done, then reads "<image>\\t<output>" lines
    from stdin and prints "OK\\t<output>" or "ERR\\t<output>\\t<message>" per
    line (other stdout is captured but ignored for control flow).
    """

    command_template: str
    _proc: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    _command_args: list[str] | None = field(default=None, init=False, repr=False)
    _command: str | None = field(default=None, init=False, repr=False)
    _stderr_lines: list[str] = field(default_factory=list, init=False, repr=False)

    runner_type = "trellis-batch"
    runner_version = "trellis2-batch-command"

    @classmethod
    def from_env(cls) -> BatchTrellisCommandRunner:
        command_template = os.environ.get("TRELLIS2_BATCH_COMMAND")
        if not command_template:
            raise RuntimeError(
                "TRELLIS2_BATCH_COMMAND is required, for example: "
                "'docker run --rm -i --gpus all ... trellis2:blackwell --batch'"
            )
        return cls(command_template=command_template)

    def __enter__(self) -> BatchTrellisCommandRunner:
        try:
            self._command_args = shlex.split(self.command_template)
        except ValueError as exc:
            raise RuntimeError(f"Invalid TRELLIS2_BATCH_COMMAND shell syntax: {exc}") from exc
        if not self._command_args:
            raise RuntimeError("TRELLIS2_BATCH_COMMAND must include an executable")
        self._command = shlex.join(self._command_args)
        self._proc = subprocess.Popen(
            self._command_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._await_ready()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
            try:
                self._proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._proc.terminate()
                self._proc.wait(timeout=5)
        finally:
            if self._proc.stderr:
                tail = self._proc.stderr.read()
                if tail:
                    self._stderr_lines.append(tail)
            self._proc = None

    def run(self, request: RunnerRequest) -> RunnerResult:
        if self._proc is None:
            raise RuntimeError("BatchTrellisCommandRunner used outside its context manager")
        request.output_dir.mkdir(parents=True, exist_ok=True)
        raw_glb_path = request.output_dir / "raw.glb"
        report_path = request.output_dir / "raw_report.json"
        output_token = str(request.output_dir.resolve())

        started_at = datetime.now(tz=UTC)
        stdout_lines: list[str] = []
        error_type: str | None = None
        error_message: str | None = None

        try:
            self._send(f"{str(request.concept_image.resolve())}\t{output_token}")
            response = self._read_response(output_token, stdout_lines)
        except (BrokenPipeError, RuntimeError) as exc:
            error_type = type(exc).__name__
            error_message = str(exc)
            response = None

        if response is not None:
            kind, payload = response
            if kind == "ERR":
                error_type = "BatchAssetError"
                error_message = payload
            elif not raw_glb_path.exists():
                error_type = "MissingRawGlbError"
                error_message = (
                    f"TRELLIS batch reported OK but {raw_glb_path} is missing"
                )
        ended_at = datetime.now(tz=UTC)

        success = error_type is None and raw_glb_path.exists()
        _write_report(
            report_path=report_path,
            runner_type=self.runner_type,
            runner_version=self.runner_version,
            request=request,
            raw_glb_path=raw_glb_path,
            started_at=started_at,
            ended_at=ended_at,
            success=success,
            command_template=self.command_template,
            command=self._command,
            command_args=self._command_args,
            returncode=None,
            stdout="".join(stdout_lines) or None,
            stderr=None,
            error_type=error_type,
            error_message=error_message,
        )

        if not success:
            raise RuntimeError(f"TRELLIS batch command failed; see {report_path}")
        return RunnerResult(
            raw_glb_path=raw_glb_path,
            report_path=report_path,
            runner_type=self.runner_type,
            runner_version=self.runner_version,
            success=True,
        )

    def _send(self, line: str) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def _await_ready(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(
                    "TRELLIS2_BATCH_COMMAND exited before printing READY"
                )
            if line.rstrip("\n") == _BATCH_READY_MARKER:
                return

    def _read_response(
        self, output_token: str, stdout_lines: list[str]
    ) -> tuple[str, str] | None:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(
                    "TRELLIS2_BATCH_COMMAND closed stdout before responding"
                )
            stripped = line.rstrip("\n")
            if stripped.startswith(_BATCH_OK_PREFIX):
                token = stripped[len(_BATCH_OK_PREFIX):]
                if token == output_token:
                    return ("OK", token)
                raise RuntimeError(
                    f"TRELLIS2_BATCH_COMMAND responded OK for {token!r} "
                    f"but expected {output_token!r}"
                )
            if stripped.startswith(_BATCH_ERR_PREFIX):
                rest = stripped[len(_BATCH_ERR_PREFIX):]
                token, _, message = rest.partition("\t")
                if token != output_token:
                    raise RuntimeError(
                        f"TRELLIS2_BATCH_COMMAND responded ERR for {token!r} "
                        f"but expected {output_token!r}"
                    )
                return ("ERR", message)
            stdout_lines.append(line)
