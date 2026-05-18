# Synthetic fixture — concrete service method with empty body masquerading as implemented.
# HIGH: concrete methods, no @abstractmethod decorator, bodies are bare `pass` / `...`.


class BillingService:
    def charge(self, amount: int) -> None:
        pass

    def refund(self, txn_id: str) -> None:
        ...
