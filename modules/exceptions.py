from typing import Any, Optional


class BacktestError(Exception):
    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - 详情: {self.details}"
        return self.message


class DataValidationError(BacktestError):
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Any = None,
        details: Optional[dict] = None
    ) -> None:
        self.field_name = field_name
        self.invalid_value = invalid_value
        super().__init__(message, details)


class ConfigError(BacktestError):
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict] = None
    ) -> None:
        self.config_key = config_key
        super().__init__(message, details)


class CalculationError(BacktestError):
    def __init__(
        self,
        message: str,
        calculation_type: Optional[str] = None,
        details: Optional[dict] = None
    ) -> None:
        self.calculation_type = calculation_type
        super().__init__(message, details)


class StrategyError(BacktestError):
    def __init__(
        self,
        message: str,
        strategy_type: Optional[str] = None,
        details: Optional[dict] = None
    ) -> None:
        self.strategy_type = strategy_type
        super().__init__(message, details)
