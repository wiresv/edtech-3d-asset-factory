import json
import sys
from pathlib import Path

import pytest

from asset_factory.runners.base import RunnerRequest
from asset_factory.runners.trellis import BatchTrellisCommandRunner, TrellisCommandRunner


_FAKE_BATCH_SCRIPT = """
import sys
from pathlib import Path

print("READY", flush=True)
for line in sys.stdin:
    line = line.rstrip("\\n")
    if not line:
        continue
    image_str, output_str = line.split("\\t", 1)
    out = Path(output_str)
    if image_str.endswith("FAIL.png"):
        print(f"ERR\\t{output_str}\\tFakeError: simulated", flush=True)
        continue
    out.mkdir(parents=True, exist_ok=True)
    (out / "raw.glb").write_bytes(b"glTF-fake-batch")
    print(f"verbose: processed {image_str}", flush=True)
    print(f"OK\\t{output_str}", flush=True)
"""


def test_trellis_runner_requires_env(monkeypatch):
    monkeypatch.delenv("TRELLIS2_COMMAND", raising=False)

    try:
        TrellisCommandRunner.from_env()
    except RuntimeError as exc:
        assert "TRELLIS2_COMMAND" in str(exc)
    else:
        raise AssertionError("TrellisCommandRunner.from_env should require TRELLIS2_COMMAND")


def test_trellis_runner_executes_command_template(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_trellis.py"
    script.write_text(
        """
from pathlib import Path
import sys
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
(out / "raw.glb").write_bytes(b"glTF-fake")
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRELLIS2_COMMAND", f"{sys.executable} {script} {{image}} {{output}}")
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")

    runner = TrellisCommandRunner.from_env()
    result = runner.run(RunnerRequest(concept_image=image, output_dir=tmp_path / "trellis"))

    assert result.raw_glb_path.read_bytes() == b"glTF-fake"
    assert result.report_path.exists()
    assert result.runner_type == "trellis"
    assert result.success is True

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["concept_image"] == str(image)
    assert report["command_args"] == [
        sys.executable,
        str(script),
        str(image),
        str(tmp_path / "trellis"),
    ]


def test_trellis_runner_on_start_can_terminate_build(tmp_path: Path, monkeypatch):
    script = tmp_path / "slow_trellis.py"
    script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    monkeypatch.setenv("TRELLIS2_COMMAND", f"{sys.executable} {script} {{image}} {{output}}")
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"

    runner = TrellisCommandRunner.from_env()
    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        runner.run(
            RunnerRequest(concept_image=image, output_dir=output_dir),
            on_start=lambda proc: proc.terminate(),
        )

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["returncode"] is not None
    assert report["returncode"] != 0
    assert not (output_dir / "raw.glb").exists()


def test_trellis_runner_preserves_placeholder_paths_with_spaces(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_trellis.py"
    script.write_text(
        """
from pathlib import Path
import json
import sys

image = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
(out / "argv.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
(out / "raw.glb").write_bytes(b"glTF-fake")
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "TRELLIS2_COMMAND",
        f"{sys.executable} {script} {{image}} {{output}} --resolution {{resolution}}",
    )
    image = tmp_path / "concept images" / "source file.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis output" / "with spaces"

    result = TrellisCommandRunner.from_env().run(
        RunnerRequest(concept_image=image, output_dir=output_dir, resolution=2048)
    )

    assert json.loads((output_dir / "argv.json").read_text(encoding="utf-8")) == [
        str(image),
        str(output_dir),
        "--resolution",
        "2048",
    ]
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["command_args"] == [
        sys.executable,
        str(script),
        str(image),
        str(output_dir),
        "--resolution",
        "2048",
    ]
    assert report["concept_image"] == str(image)


def test_trellis_runner_writes_failure_report_for_missing_executable(tmp_path: Path):
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"
    runner = TrellisCommandRunner(
        command_template=f"{tmp_path / 'missing-trellis'} {{image}} {{output}}"
    )

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        runner.run(RunnerRequest(concept_image=image, output_dir=output_dir))

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["error_type"] == "FileNotFoundError"
    assert "missing-trellis" in report["error_message"]
    assert report["concept_image"] == str(image)


def test_trellis_runner_writes_failure_report_for_whitespace_command_template(tmp_path: Path):
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"
    runner = TrellisCommandRunner(command_template="   ")

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        runner.run(RunnerRequest(concept_image=image, output_dir=output_dir))

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["error_type"] == "ValueError"
    assert report["error_message"] == "TRELLIS2_COMMAND must include an executable"
    assert report["command_args"] is None


def test_trellis_runner_preserves_literal_sentinel_strings(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_trellis.py"
    script.write_text(
        """
from pathlib import Path
import json
import sys

out = Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
(out / "argv.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
(out / "raw.glb").write_bytes(b"glTF-fake")
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "TRELLIS2_COMMAND",
        f"{sys.executable} {script} __TRELLIS_PLACEHOLDER_IMAGE__ {{image}} {{output}}",
    )
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"

    TrellisCommandRunner.from_env().run(RunnerRequest(concept_image=image, output_dir=output_dir))

    assert json.loads((output_dir / "argv.json").read_text(encoding="utf-8")) == [
        "__TRELLIS_PLACEHOLDER_IMAGE__",
        str(image),
        str(output_dir),
    ]


@pytest.mark.parametrize(
    ("template", "expected_message"),
    [
        ("python {missing} {output}", "Unsupported placeholder"),
        ("python {image", "Invalid TRELLIS2_COMMAND format"),
    ],
)
def test_trellis_runner_writes_failure_report_for_bad_format_template(
    tmp_path: Path, template: str, expected_message: str
):
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"
    runner = TrellisCommandRunner(command_template=template)

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        runner.run(RunnerRequest(concept_image=image, output_dir=output_dir))

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["error_type"] == "ValueError"
    assert expected_message in report["error_message"]
    assert report["concept_image"] == str(image)


def test_trellis_runner_writes_failure_report_for_malformed_shell_template(tmp_path: Path):
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"
    runner = TrellisCommandRunner(command_template="python '{image} {output}")

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        runner.run(RunnerRequest(concept_image=image, output_dir=output_dir))

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["error_type"] == "ValueError"
    assert "Invalid TRELLIS2_COMMAND shell syntax" in report["error_message"]
    assert report["concept_image"] == str(image)


def test_trellis_runner_writes_failure_report_when_raw_glb_missing(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_trellis.py"
    script.write_text(
        """
from pathlib import Path
import sys
Path(sys.argv[2]).mkdir(parents=True, exist_ok=True)
print("ok but no asset")
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRELLIS2_COMMAND", f"{sys.executable} {script} {{image}} {{output}}")
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        TrellisCommandRunner.from_env().run(
            RunnerRequest(concept_image=image, output_dir=output_dir)
        )

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["returncode"] == 0
    assert report["error_type"] == "MissingRawGlbError"
    assert "raw.glb" in report["error_message"]
    assert report["stdout"] == "ok but no asset\n"


def test_batch_runner_requires_env(monkeypatch):
    monkeypatch.delenv("TRELLIS2_BATCH_COMMAND", raising=False)
    with pytest.raises(RuntimeError, match="TRELLIS2_BATCH_COMMAND"):
        BatchTrellisCommandRunner.from_env()


def test_batch_runner_serves_multiple_requests(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_batch.py"
    script.write_text(_FAKE_BATCH_SCRIPT, encoding="utf-8")
    monkeypatch.setenv("TRELLIS2_BATCH_COMMAND", f"{sys.executable} {script}")

    images = []
    for name in ("a.png", "b.png"):
        image = tmp_path / name
        image.write_bytes(b"png")
        images.append(image)

    with BatchTrellisCommandRunner.from_env() as runner:
        for index, image in enumerate(images):
            output_dir = tmp_path / f"out_{index}"
            result = runner.run(RunnerRequest(concept_image=image, output_dir=output_dir))
            assert result.success is True
            assert result.raw_glb_path.read_bytes() == b"glTF-fake-batch"
            assert result.runner_type == "trellis-batch"
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            assert report["success"] is True
            assert "verbose: processed" in report["stdout"]


def test_batch_runner_reports_per_asset_errors(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_batch.py"
    script.write_text(_FAKE_BATCH_SCRIPT, encoding="utf-8")
    monkeypatch.setenv("TRELLIS2_BATCH_COMMAND", f"{sys.executable} {script}")

    good_image = tmp_path / "good.png"
    good_image.write_bytes(b"png")
    bad_image = tmp_path / "FAIL.png"
    bad_image.write_bytes(b"png")

    with BatchTrellisCommandRunner.from_env() as runner:
        good_result = runner.run(
            RunnerRequest(concept_image=good_image, output_dir=tmp_path / "good")
        )
        assert good_result.success is True

        with pytest.raises(RuntimeError, match="TRELLIS batch command failed"):
            runner.run(RunnerRequest(concept_image=bad_image, output_dir=tmp_path / "bad"))

    bad_report = json.loads((tmp_path / "bad" / "raw_report.json").read_text(encoding="utf-8"))
    assert bad_report["success"] is False
    assert bad_report["error_type"] == "BatchAssetError"
    assert "FakeError" in bad_report["error_message"]


def test_batch_runner_rejects_use_outside_context(tmp_path: Path):
    runner = BatchTrellisCommandRunner(command_template="true")
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    with pytest.raises(RuntimeError, match="outside its context manager"):
        runner.run(RunnerRequest(concept_image=image, output_dir=tmp_path / "trellis"))


def test_trellis_runner_writes_failure_report_for_nonzero_return_code(tmp_path: Path, monkeypatch):
    script = tmp_path / "fake_trellis.py"
    script.write_text(
        """
import sys
print("bad input", file=sys.stderr)
raise SystemExit(7)
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRELLIS2_COMMAND", f"{sys.executable} {script} {{image}} {{output}}")
    image = tmp_path / "concept.png"
    image.write_bytes(b"png")
    output_dir = tmp_path / "trellis"

    with pytest.raises(RuntimeError, match="TRELLIS command failed; see"):
        TrellisCommandRunner.from_env().run(
            RunnerRequest(concept_image=image, output_dir=output_dir)
        )

    report = json.loads((output_dir / "raw_report.json").read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["returncode"] == 7
    assert report["error_type"] == "NonZeroReturnCodeError"
    assert "bad input" in report["stderr"]
