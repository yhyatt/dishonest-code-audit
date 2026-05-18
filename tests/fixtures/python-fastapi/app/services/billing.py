# Synthetic fixture — concrete service method with empty body masquerading as implemented.


class BillingService:
    def charge(self, amount: int) -> None:
        # HIGH: concrete method, no @abstractmethod decorator, body is bare `pass`.
        pass

    def refund(self, txn_id: str) -> None:
        # HIGH: concrete method using Ellipsis as a placeholder body.
        ...
