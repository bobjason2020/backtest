import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class FeeParams:
    purchase_fee_rate: float = 0
    management_fee_rate: float = 0
    custody_fee_rate: float = 0
    redemption_fee_rate: float = 0
    cash_ratio: float = 0
    tracking_error: float = 0
    tracking_error_mode: str = "固定折扣"
    random_seed: Optional[int] = None


class FeeCalculator:
    def __init__(
        self,
        purchase_fee_rate: float = 0,
        management_fee_rate: float = 0,
        custody_fee_rate: float = 0,
        redemption_fee_rate: float = 0,
        cash_ratio: float = 0,
        tracking_error: float = 0,
        tracking_error_mode: str = "固定折扣",
        random_seed: Optional[int] = None
    ):
        self.purchase_fee_rate = purchase_fee_rate
        self.management_fee_rate = management_fee_rate
        self.custody_fee_rate = custody_fee_rate
        self.redemption_fee_rate = redemption_fee_rate
        self.cash_ratio = cash_ratio
        self.tracking_error = tracking_error
        self.tracking_error_mode = tracking_error_mode
        self.random_seed = random_seed

        if random_seed is not None:
            np.random.seed(random_seed)

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> 'FeeCalculator':
        return cls(
            purchase_fee_rate=params.get('purchase_fee_rate', 0),
            management_fee_rate=params.get('management_fee_rate', 0),
            custody_fee_rate=params.get('custody_fee_rate', 0),
            redemption_fee_rate=params.get('redemption_fee_rate', 0),
            cash_ratio=params.get('cash_ratio', 0),
            tracking_error=params.get('tracking_error', 0),
            tracking_error_mode=params.get('tracking_error_mode', '固定折扣'),
            random_seed=params.get('random_seed', None)
        )

    def calculate_purchase_fee(self, amount: float) -> float:
        return amount * self.purchase_fee_rate

    def calculate_daily_management_fee(self, shares: float, price: float) -> float:
        daily_fee_rate = (self.management_fee_rate + self.custody_fee_rate) / 365
        return shares * daily_fee_rate * price

    def calculate_redemption_fee(self, asset_value: float) -> float:
        return asset_value * self.redemption_fee_rate

    def apply_tracking_error(self, price: float) -> float:
        if self.tracking_error_mode == "固定折扣":
            adjusted_price = price * (1 - self.tracking_error)
        else:
            daily_tracking_error = self.tracking_error / np.sqrt(252)
            random_factor = np.random.normal(0, daily_tracking_error)
            adjusted_price = price * (1 + random_factor)

        return max(0, adjusted_price)

    def calculate_total_fees(
        self,
        investment_amount: float,
        shares: float,
        price: float,
        days: int
    ) -> Dict[str, float]:
        purchase_fee = self.calculate_purchase_fee(investment_amount)
        daily_mgmt_fee = self.calculate_daily_management_fee(shares, price)
        total_mgmt_fee = daily_mgmt_fee * days
        redemption_fee = self.calculate_redemption_fee(shares * price)

        return {
            'purchase_fee': purchase_fee,
            'management_fee': total_mgmt_fee,
            'redemption_fee': redemption_fee,
            'total_fees': purchase_fee + total_mgmt_fee + redemption_fee
        }

    def get_fee_summary(self) -> Dict[str, Any]:
        return {
            'purchase_fee_rate': self.purchase_fee_rate,
            'management_fee_rate': self.management_fee_rate,
            'custody_fee_rate': self.custody_fee_rate,
            'redemption_fee_rate': self.redemption_fee_rate,
            'cash_ratio': self.cash_ratio,
            'tracking_error': self.tracking_error,
            'tracking_error_mode': self.tracking_error_mode
        }


def calculate_purchase_fee(amount: float, rate: float) -> float:
    calculator = FeeCalculator(purchase_fee_rate=rate)
    return calculator.calculate_purchase_fee(amount)


def calculate_daily_management_fee(shares: float, price: float, mgmt_rate: float, custody_rate: float) -> float:
    calculator = FeeCalculator(management_fee_rate=mgmt_rate, custody_fee_rate=custody_rate)
    return calculator.calculate_daily_management_fee(shares, price)


def calculate_redemption_fee(asset_value: float, rate: float) -> float:
    calculator = FeeCalculator(redemption_fee_rate=rate)
    return calculator.calculate_redemption_fee(asset_value)


def apply_tracking_error(price: float, tracking_error: float, mode: str = "固定折扣") -> float:
    calculator = FeeCalculator(tracking_error=tracking_error, tracking_error_mode=mode)
    return calculator.apply_tracking_error(price)
