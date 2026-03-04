from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd


@dataclass
class CashFlowAccount:
    balance: float = 0.0
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    total_from_sale: float = 0.0
    records: List[Dict[str, Any]] = field(default_factory=list)
    _balance_history: List[float] = field(default_factory=list)
    
    def deposit(self, amount: float) -> float:
        if amount <= 0:
            return self.balance
        self.balance += amount
        self.total_deposited += amount
        self._balance_history.append(self.balance)
        return self.balance
    
    def withdraw(self, amount: float) -> float:
        if amount <= 0 or self.balance <= 0:
            return 0.0
        actual_amount = min(amount, self.balance)
        self.balance -= actual_amount
        self.total_withdrawn += actual_amount
        self._balance_history.append(self.balance)
        return actual_amount
    
    def receive_from_sale(self, amount: float) -> float:
        if amount <= 0:
            return self.balance
        self.balance += amount
        self.total_from_sale += amount
        self._balance_history.append(self.balance)
        return self.balance
    
    def get_available_amount(self, requested: float) -> float:
        if requested <= 0:
            return 0.0
        return min(requested, self.balance)
    
    def get_cash_utilization(self) -> float:
        if self.total_deposited <= 0:
            return 0.0
        return self.total_withdrawn / self.total_deposited
    
    def add_record(self, date: Any, deposit: float = 0.0, withdraw: float = 0.0,
                   signal: str = '', requested: float = 0.0, actual: float = 0.0,
                   from_sale: float = 0.0) -> None:
        record = {
            'date': date,
            'deposit': deposit,
            'withdraw': withdraw,
            'balance': self.balance,
            'signal': signal,
            'requested': requested,
            'actual': actual,
            'from_sale': from_sale
        }
        self.records.append(record)
    
    def get_records_df(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame()
        return pd.DataFrame(self.records)
    
    def get_records_by_date_range(self, start_date: Any, end_date: Any) -> List[Dict[str, Any]]:
        if not self.records:
            return []
        filtered_records = []
        for record in self.records:
            record_date = record.get('date')
            if record_date is None:
                continue
            if start_date <= record_date <= end_date:
                filtered_records.append(record)
        return filtered_records
    
    def clear_records(self) -> None:
        self.records = []
        self._balance_history = []
    
    def get_statistics(self) -> Dict[str, Any]:
        average_balance = 0.0
        if self._balance_history:
            average_balance = sum(self._balance_history) / len(self._balance_history)
        cash_utilization = self.get_cash_utilization()
        return {
            'total_deposited': self.total_deposited,
            'total_withdrawn': self.total_withdrawn,
            'total_from_sale': self.total_from_sale,
            'cash_utilization': cash_utilization,
            'average_balance': average_balance
        }
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            'balance': self.balance,
            'total_deposited': self.total_deposited,
            'total_withdrawn': self.total_withdrawn,
            'total_from_sale': self.total_from_sale,
            'cash_utilization': self.get_cash_utilization(),
            'record_count': len(self.records)
        }
    
    def reset(self) -> None:
        self.balance = 0.0
        self.total_deposited = 0.0
        self.total_withdrawn = 0.0
        self.total_from_sale = 0.0
        self.records = []
        self._balance_history = []
