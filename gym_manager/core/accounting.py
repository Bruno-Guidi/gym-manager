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

    def transactions(
            self, from_date: date | None = None, to_date: date | None = None, page_number: int = 1,
            items_per_page: int = 15
    ) -> Iterable[Transaction]:
        """Returns transactions.
        """
        cache = {}
        yield from self.transaction_repo.all(cache, from_date, to_date, page_number=page_number, items_per_page=items_per_page)

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