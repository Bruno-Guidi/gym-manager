from datetime import date
from typing import Iterable

from gym_manager.core import constants as consts
from gym_manager.core.base import Transaction, Client, Activity, String
from gym_manager.core.persistence import TransactionRepo, InscriptionRepo


class AccountingSystem:

    def __init__(
            self,
            transaction_repo: TransactionRepo,
            inscription_repo: InscriptionRepo,
            transaction_types: list[str]
    ) -> None:
        self.transaction_repo = transaction_repo
        self.inscription_repo = inscription_repo
        self.transaction_types = {name: String(name, max_len=consts.TRANSACTION_TYPE_CHARS)
                                  for name in transaction_types}

    def methods(self) -> Iterable[String]:
        methods = [String("Efectivo", max_len=consts.TRANSACTION_METHOD_CHARS),
                   String("Débito", max_len=consts.TRANSACTION_METHOD_CHARS),
                   String("Crédito", max_len=consts.TRANSACTION_METHOD_CHARS)]
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
        yield from self.transaction_repo.all(page, page_len, **filters)

    def charge(
            self, when: date, client: Client, activity: Activity, method: String, responsible: String,
            description: String
    ) -> int:
        """Register a new charge transaction of an *activity* done by the *client*.

        Raises:
            NotRegistered if *client* doesn't do the *activity*.
        """
        # Creates the transaction.
        trans_type = self.transaction_types["charge"]
        transaction = self.transaction_repo.create(trans_type, client, when, activity.price, method, responsible,
                                                   description)

        # For the activities that are not 'charge once', record that the client was charged for it.
        # A 'charge once' activity is, for example, an activity related to bookings.
        if not activity.pay_once:
            client.register_charge(activity, transaction)
            self.inscription_repo.register_charge(client, activity, transaction)

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