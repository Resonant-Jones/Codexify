"""Platform-qualified MLX dependency contract for the private-preview Docker runtime.

This is a deterministic lock regression test. It reads the canonical input
and generated lock and proves that the MLX-family declarations support both
Darwin (Metal) and Linux (CPU) without leaking one platform into the other.
"""

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
AI_IN = REPO / "requirements" / "ai.in"
ALL_TXT = REPO / "requirements" / "all.txt"


def read_lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def find_line_containing(lines: list[str], substring: str) -> str | None:
    for line in lines:
        if substring in line and not line.strip().startswith("#"):
            return line
    return None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _lock_version(lines: list[str], pkg: str) -> str | None:
    """Return the locked version string for *pkg* (e.g. 'mlx-lm==0.28.3')."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{pkg}=="):
            return stripped
    return None


def _platform_marker(line: str | None) -> str | None:
    """Extract the platform marker from a dependency line if present."""
    if line is None:
        return None
    # normalise double quotes
    line = line.replace('"', "'")
    if "sys_platform ==" in line:
        m = re.search(r"sys_platform\s*==\s*'(\w+)'", line)
        return m.group(1) if m else None
    return None


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestMlxPlatformDependencyContract:
    """Prove the MLX-family lock respects Darwin Metal / Linux CPU boundaries."""

    def test_mlx_0_29_3_absent_from_lock(self) -> None:
        """mlx==0.29.3 must not appear in the generated lock."""
        lock = read_lines(ALL_TXT)
        assert "mlx==0.29.3" not in lock, "mlx==0.29.3 found in all.txt – must be 0.30.0"

    def test_mlx_metal_0_29_3_absent_from_lock(self) -> None:
        """mlx-metal==0.29.3 must not appear in the generated lock."""
        lock = read_lines(ALL_TXT)
        assert "mlx-metal==0.29.3" not in lock, (
            "mlx-metal==0.29.3 found in all.txt – must be 0.30.0"
        )

    # -- canonical input ----------------------------------------------------

    def test_ai_in_declares_darwin_mlx_0_30_0(self) -> None:
        inputs = read_lines(AI_IN)
        line = find_line_containing(inputs, "mlx==0.30.0")
        assert line is not None, "Darwin mlx==0.30.0 not found in ai.in"
        marker = _platform_marker(line)
        assert marker == "darwin", f"Expected darwin marker, got {marker}"

    def test_ai_in_declares_linux_mlx_cpu_0_30_0(self) -> None:
        inputs = read_lines(AI_IN)
        line = find_line_containing(inputs, "mlx[cpu]==0.30.0")
        assert line is not None, "Linux mlx[cpu]==0.30.0 not found in ai.in"
        marker = _platform_marker(line)
        assert marker == "linux", f"Expected linux marker, got {marker}"

    # -- generated lock platform isolation ----------------------------------

    def test_lock_has_linux_mlx_cpu(self) -> None:
        lock = read_lines(ALL_TXT)
        line = find_line_containing(lock, "mlx-cpu==0.30.0")
        assert line is not None, "mlx-cpu==0.30.0 not found in all.txt"
        marker = _platform_marker(line)
        assert marker == "linux", (
            f"mlx-cpu must have linux marker, got {marker}"
        )

    def test_lock_has_darwin_mlx_metal(self) -> None:
        lock = read_lines(ALL_TXT)
        line = find_line_containing(lock, "mlx-metal==0.30.0")
        assert line is not None, "mlx-metal==0.30.0 not found in all.txt"
        marker = _platform_marker(line)
        assert marker == "darwin", (
            f"mlx-metal must have darwin marker, got {marker}"
        )

    def test_mlx_metal_not_linux(self) -> None:
        """mlx-metal must not install under the Linux platform marker."""
        lock = read_lines(ALL_TXT)
        line = find_line_containing(lock, "mlx-metal==")
        assert line is not None, "mlx-metal not found"
        marker = _platform_marker(line)
        assert marker != "linux", (
            "mlx-metal must not be marked for linux"
        )

    def test_mlx_cpu_not_darwin(self) -> None:
        """mlx-cpu must not install under the Darwin platform marker."""
        lock = read_lines(ALL_TXT)
        line = find_line_containing(lock, "mlx-cpu==")
        assert line is not None, "mlx-cpu not found"
        marker = _platform_marker(line)
        assert marker != "darwin", (
            "mlx-cpu must not be marked for darwin"
        )

    # -- higher-level package versions unchanged ----------------------------

    def test_mlx_lm_version_unchanged(self) -> None:
        lock = read_lines(ALL_TXT)
        version = _lock_version(lock, "mlx-lm")
        assert version == "mlx-lm==0.28.3", (
            f"mlx-lm version changed: {version}"
        )

    def test_mlx_vlm_version_unchanged(self) -> None:
        lock = read_lines(ALL_TXT)
        version = _lock_version(lock, "mlx-vlm")
        assert version == "mlx-vlm==0.3.4", (
            f"mlx-vlm version changed: {version}"
        )
