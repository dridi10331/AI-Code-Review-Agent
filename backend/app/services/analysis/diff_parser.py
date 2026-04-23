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


def build_diff_review_context(diff_text: str, *, max_hunks: int = 6, max_lines_per_hunk: int = 20) -> str:
    """
    Create a compact diff context intended for LLM review prompts.
    Includes per-hunk new-file line ranges and a short sample of +/- lines.
    """
    hunks = parse_unified_diff(diff_text)
    if not hunks:
        return "No diff provided."

    lines: list[str] = ["Review focus (diff context):"]
    for idx, hunk in enumerate(hunks[:max_hunks], start=1):
        new_range_start = hunk.new_start
        new_range_end = max(hunk.new_start, hunk.new_start + max(hunk.new_count - 1, 0))
        lines.append(
            f"Hunk {idx} — {hunk.file_path} new lines {new_range_start}-{new_range_end} "
            f"(+{len(hunk.added_lines)}/-{len(hunk.removed_lines)})"
        )

        shown = 0
        for added in hunk.added_lines:
            lines.append(f"+ {added}")
            shown += 1
            if shown >= max_lines_per_hunk:
                break

        if shown < max_lines_per_hunk:
            for removed in hunk.removed_lines[: max_lines_per_hunk - shown]:
                lines.append(f"- {removed}")
                shown += 1

        if len(hunk.added_lines) + len(hunk.removed_lines) > max_lines_per_hunk:
            lines.append("… (truncated)")

    if len(hunks) > max_hunks:
        lines.append(f"… ({len(hunks) - max_hunks} more hunks truncated)")

    return "\n".join(lines)
