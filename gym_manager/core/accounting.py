from datetime import date
from typing import Iterable

from gym_manager.core import attr_constraints
from gym_manager.core.base import Transaction, Client, Activity, String
from gym_manager.core.persistence import TransactionRepo


class AccountingSystem:

    def __init__(self, transaction_repo: TransactionRepo, transaction_types: list[str]) -> None:
        self.transaction_repo = transaction_repo
        self.transaction_types = {name: String(name, max_len=attr_constraints.TRANSACTION_TYPE_CHARS)
                                  for name in transaction_types}

    def methods(self) -> Iterable[String]:
        methods = [String("Efectivo", max_len=20), String("Débito", max_len=20), String("Crédito", max_len=20)]
        for m in methods:
            yield m

    def transactions(self, page: int = 1, page_len: int = 15, **filters) -> Iterable[Transaction]:
        """Returns transactions.

        Keyword Args:
            client: allows filtering by client name.
            type: allows filtering by transaction type.
            from_date: allows filtering transactions whose *when* is after the given date (inclusive).
            to_date: allows filtering transactions whose *when* is before the given date (inclusive).
            method: allows filtering by transaction method.
            responsible: allows filtering by transaction responsible.
        """
        cache = {}
        yield from self.transaction_repo.all(page, page_len, cache, **filters)

    def charge(
            self, when: date, client: Client, activity: Activity, method: String, responsible: String,
            description: String
    ) -> int:
        """Register a new charge transaction of an *activity* done by the *client*.

        Raises:
            NotRegistered if *client* doesn't do the *activity*.
        """
        # Register the payment.
        trans_type = self.transaction_types["charge"]
        transaction = self.transaction_repo.create(trans_type, client, when, activity.price, method, responsible,
                                                   description)

        # For the activities that are not 'paid once', record that the client paid it.
        # A 'paid once' activity is, for example, an activity related to bookings.
        # if not activity.pay_once:
        #     entry = client.record_payment(activity, payment)  # Raises NotRegistered.
        #     self.activity_entry_repo.update_or_create(entry)

        return transaction.id

#     def all_expired_activities(self, **kwargs) -> Iterable[ActivityEntry]:
#         """Retrieves all activity entries whose pay day has passed.
#
#         Keyword Args:
#             activities: dict[int, Activity] with existing activities.
#             page_number: number of page of the table to return.
#             items_per_page: number of items per page.
#         """
#         yield from self.activity_entry_repo.expired(date.today(), **kwargs)
#
#
# def expired_activities(client: Client, today: date) -> Iterable[ActivityEntry]:
#     """Retrieves all the activities that the *client* is doing and whose pay day has passed.
#     """
#     for entry in client.activities:
#         if entry.pay_day_passed(today):
#             yield entry