import numpy as np


def calculate_purchase_fee(amount, rate):
    return amount * rate


def calculate_daily_management_fee(shares, price, mgmt_rate, custody_rate):
    daily_fee_rate = (mgmt_rate + custody_rate) / 365
    return shares * daily_fee_rate * price


def calculate_redemption_fee(asset_value, rate):
    return asset_value * rate


def apply_tracking_error(price, tracking_error, mode="固定折扣"):
    if mode == "固定折扣":
        return price * (1 - tracking_error)
    else:
        daily_tracking_error = tracking_error / np.sqrt(252)
        random_factor = np.random.normal(0, daily_tracking_error)
        return price * (1 + random_factor)
