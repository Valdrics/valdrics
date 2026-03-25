from pathlib import Path
import re
import tempfile

directories = (
    "app/modules/optimization/adapters/aws/plugins",
    "app/modules/optimization/adapters/azure/plugins",
    "app/modules/optimization/adapters/gcp/plugins",
    "app/modules/optimization/adapters/kubernetes/plugins",
    "app/modules/optimization/adapters/saas/plugins",
    "app/modules/optimization/adapters/license/plugins",
)

base_sig = """    async def scan(
        self,
        session: Any,
        region: str,
        credentials: Dict[str, str] | None = None,
        config: Any = None,
        inventory: Any = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _plugin_directories() -> tuple[Path, ...]:
    repo_root = _repo_root()
    return tuple(repo_root / directory for directory in directories)


def _write_atomically(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=f"{path.suffix or '.py'}.tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        staged_path = Path(handle.name)

    try:
        staged_path.replace(path)
    except OSError:
        staged_path.unlink(missing_ok=True)
        raise


def process_file(filepath: str | Path) -> int:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")

    # Regex to capture `async def scan(...) -> ...:`
    pattern = re.compile(r'(\s+)async def scan\s*\([^)]+\)\s*->\s*List\[Dict\[str,\s*Any\]\]:', re.MULTILINE)

    def replacer(match):
        indent = match.group(1)
        # Fix the base signature indentation
        new_sig = base_sig.replace("    ", indent)
        return new_sig

    new_content, count = pattern.subn(replacer, content)

    if count > 0:
        # Also need to make sure `Dict` and `Any` and `List` are imported
        if "from typing import" in new_content:
            pass # Usually handled

        _write_atomically(path, new_content)
        print(f"Updated {path} ({count} replacements)")
    return count


def main() -> int:
    replacements = 0
    for directory in _plugin_directories():
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.suffix == ".py":
                replacements += process_file(path)
    return replacements


if __name__ == "__main__":
    raise SystemExit(0 if main() >= 0 else 1)
