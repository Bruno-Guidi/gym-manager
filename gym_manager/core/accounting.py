from datetime import date
from typing import Iterable

from gym_manager.core.base import Payment, Client, Activity, String
from gym_manager.core.persistence import PaymentRepo


class PaymentSystem:

    def __init__(self, payment_repo: PaymentRepo) -> None:
        self.payment_repo = payment_repo

    def methods(self) -> Iterable[String]:
        methods = [String("Efectivo", optional=False, max_len=20), String("Débito", optional=False, max_len=20),
                   String("Crédito", optional=False, max_len=20)]
        for m in methods:
            yield m

    def payments(
            self, from_date: date | None = None, to_date: date | None = None, page_number: int = 1,
            items_per_page: int = 15
    ) -> Iterable[Payment]:
        """Returns payments.
        """
        cache = {}
        yield from self.payment_repo.all(cache, from_date, to_date, page_number=page_number, items_per_page=items_per_page)

    def charge(
            self, when: date, client: Client, activity: Activity, method: String, responsible: String,
            description: String
    ) -> int:
        """Registers the payment of an *activity* done by the *client*.

        Raises:
            NotRegistered if *client* doesn't do the *activity*.
        """
        # Register the payment.
        payment = self.payment_repo.charge(client, when, activity.price, method, responsible, description)

        # For the activities that are not 'paid once', record that the client paid it.
        # A 'paid once' activity is, for example, an activity related to bookings.
        # if not activity.pay_once:
        #     entry = client.record_payment(activity, payment)  # Raises NotRegistered.
        #     self.activity_entry_repo.update_or_create(entry)

        return payment.id

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