from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class CircuitBreakerOpenError(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    failure_threshold: int
    recovery_seconds: int
    failure_count: int = 0
    opened_at: datetime | None = None

    def allow_request(self) -> bool:
        if self.opened_at is None:
            return True
        now = datetime.now(UTC)
        elapsed = now - self.opened_at
        return elapsed >= timedelta(seconds=self.recovery_seconds)

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = datetime.now(UTC)

    @property
    def is_open(self) -> bool:
        return not self.allow_request()
