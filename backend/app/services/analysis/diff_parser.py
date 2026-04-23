import re
from dataclasses import dataclass, field


@dataclass
class DiffHunk:
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)


HUNK_PATTERN = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")


def parse_unified_diff(diff_text: str) -> list[DiffHunk]:
    if not diff_text.strip():
        return []

    hunks: list[DiffHunk] = []
    current_file = "unknown"
    current_hunk: DiffHunk | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/").strip()
            continue

        if line.startswith("@@"):
            match = HUNK_PATTERN.match(line)
            if not match:
                continue
            old_start, old_count, new_start, new_count = map(int, match.groups())
            current_hunk = DiffHunk(
                file_path=current_file,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
            )
            hunks.append(current_hunk)
            continue

        if current_hunk is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_hunk.added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            current_hunk.removed_lines.append(line[1:])

    return hunks


def summarize_diff(diff_text: str, max_lines: int = 120) -> str:
    hunks = parse_unified_diff(diff_text)
    if not hunks:
        return "No diff hunks detected."

    summary_lines = [f"Detected {len(hunks)} changed hunk(s)."]
    for hunk in hunks:
        summary_lines.append(
            f"{hunk.file_path}: +{len(hunk.added_lines)} / -{len(hunk.removed_lines)} lines"
        )

    summary = "\n".join(summary_lines)
    return summary[:max_lines * 2]
