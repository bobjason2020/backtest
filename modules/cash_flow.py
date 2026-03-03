from dataclasses import dataclass, field
from typing import List, Dict, Any
import pandas as pd


@dataclass
class CashFlowRecord:
    single_record = {
        'date': None,
        'deposit': 0.0,
        'withdraw': 0.0,
        'balance': 0.0,
        'signal': '',
        'requested': 0.0,
        'actual': 0.0
    }


@dataclass
class CashFlowAccount:
    balance: float = 0.0
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    records: List[Dict[str, Any]] = field(default_factory=list)
    
    def deposit(self, amount: float) -> float:
        if amount <= 0:
            return self.balance
        self.balance += amount
        self.total_deposited += amount
        return self.balance
    
    def withdraw(self, amount: float) -> float:
        if amount <= 0 or self.balance <= 0:
            return 0.0
        actual_amount = min(amount, self.balance)
        self.balance -= actual_amount
        self.total_withdrawn += actual_amount
        return actual_amount
    
    def get_available_amount(self, requested: float) -> float:
        if requested <= 0:
            return 0.0
        return min(requested, self.balance)
    
    def get_cash_utilization(self) -> float:
        if self.total_deposited <= 0:
            return 0.0
        return self.total_withdrawn / self.total_deposited
    
    def add_record(self, date, deposit: float = 0.0, withdraw: float = 0.0,
                   signal: str = '', requested: float = 0.0, actual: float = 0.0):
        record = {
            'date': date,
            'deposit': deposit,
            'withdraw': withdraw,
            'balance': self.balance,
            'signal': signal,
            'requested': requested,
            'actual': actual
        }
        self.records.append(record)
    
    def get_records_df(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame()
        return pd.DataFrame(self.records)
    
    def reset(self):
        self.balance = 0.0
        self.total_deposited = 0.0
        self.total_withdrawn = 0.0
        self.records = []
