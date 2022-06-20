from datetime import date
from decimal import Decimal

import pytest

from gym_manager.core import constants as consts

from gym_manager.core.base import ValidationError, Number, String, Currency, Inscription, Transaction, Client, Activity


def test_Number_validInputType():
    Number(5, min_value=0, max_value=100)
    Number("5", min_value=0, max_value=100)


def test_Number_raisesValidationError_invalidInputType():
    with pytest.raises(ValidationError) as valid_err:
        Number([5])
    assert str(
        valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type([5])}]"

    with pytest.raises(ValidationError) as valid_err:
        Number(())
    assert str(
        valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type(())}]"

    with pytest.raises(ValidationError) as valid_err:
        Number({"5"})
    assert str(
        valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type({5})}]"


def test_Number_raisesValidationError_notANumber():
    with pytest.raises(ValidationError) as valid_err:
        Number("abc")
    assert str(valid_err.value) == f"The argument 'value' is not a valid number. [value=abc]"


def test_Number_inputInRange():
    min_value, max_value = 0, 100_000

    Number(min_value, min_value=min_value, max_value=max_value)
    Number(max_value - 1, min_value=min_value, max_value=max_value)


def test_Number_raisesValidationError_outOfRange():
    min_value, max_value = 0, 100_000

    # Given value is int and below given minimum
    with pytest.raises(ValidationError) as valid_err:
        Number(-1, min_value=min_value, max_value=max_value)
    assert str(valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={-1}]"

    # Given value is str and below given minimum
    with pytest.raises(ValidationError) as valid_err:
        Number("-1", min_value=min_value, max_value=max_value)
    assert str(valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={-1}]"

    # Given value is int and above given minimum
    with pytest.raises(ValidationError) as valid_err:
        Number(max_value, min_value=min_value, max_value=max_value)
    assert str(
        valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={max_value}]"

    # Given value is str and above given minimum
    with pytest.raises(ValidationError) as valid_err:
        Number(str(max_value), min_value=min_value, max_value=max_value)
    assert str(
        valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={max_value}]"


def test_Number_equality():
    as_int = 5
    as_number = Number(5)

    assert as_number == as_int and as_int == as_number


def test_Number_hashing():
    as_int = 5
    as_number = Number(5)

    assert len({as_int, as_number}) == 1

    assert as_int in {as_int} and as_int in {as_number}
    assert as_number in {as_int} and as_number in {as_number}


def test_String_raisesKeyError_missingKwarg():
    with pytest.raises(KeyError):
        String("test")  # Missing max_len.

    with pytest.raises(KeyError):
        String("test", optional=False)  # Missing max_len.

    with pytest.raises(KeyError):
        String("test", optional=True)  # Missing max_len.

    with pytest.raises(KeyError):
        String("test", max_le=10)  # max_len misspelled.


def test_String_raisesValidationError_invalidInput():
    with pytest.raises(ValidationError) as valid_err:
        String("", max_len=10)  # Empty str and optional=False.
    assert str(valid_err.value) == f"The argument 'value' cannot be empty. [value={''}, optional=False]"

    with pytest.raises(ValidationError) as valid_err:
        String("", optional=False, max_len=10)  # Empty str and optional=False.
    assert str(valid_err.value) == f"The argument 'value' cannot be empty. [value={''}, optional=False]"

    with pytest.raises(ValidationError) as valid_err:
        String("abcde", optional=False, max_len=5)  # Character limit exceeded.
    assert str(valid_err.value) == (f"The argument 'value' has more characters than allowed. "
                                    f"[len(value)={len('abcde')}, max_len=5]")


def test_Currency_raisesKeyError_missingKwarg():
    with pytest.raises(KeyError):
        Currency("test")  # Missing max_currency.

    with pytest.raises(KeyError):
        Currency("test")  # Missing max_currency.

    with pytest.raises(KeyError):
        Currency("test")  # Missing max_currency.

    with pytest.raises(KeyError):
        Currency("test", max_crrency=10)  # max_currency misspelled.


def test_Currency_raisesValidationError_invalidCurrency():
    with pytest.raises(ValidationError) as valid_err:
        Currency("", max_currency=Decimal("100"))
    assert str(valid_err.value) == f"The argument 'value' is not a valid currency. [value={''}]"

    with pytest.raises(ValidationError) as valid_err:
        Currency("abcd", max_currency=Decimal("100"))
    assert str(valid_err.value) == f"The argument 'value' is not a valid currency. [value=abcd]"

    with pytest.raises(ValidationError) as valid_err:
        Currency("1e", max_currency=Decimal("100"))
    assert str(valid_err.value) == f"The argument 'value' is not a valid currency. [value=1e]"

    with pytest.raises(ValidationError) as valid_err:
        Currency("a1", max_currency=Decimal("100"))
    assert str(valid_err.value) == f"The argument 'value' is not a valid currency. [value=a1]"


def test_Currency_raisesValidationError_maxCurrencyExceeded():
    with pytest.raises(ValidationError) as valid_err:
        Currency("100", max_currency=Decimal("100"))
    assert str(valid_err.value) == f"The argument 'value' must be lesser than {'100'}. [value=100]"


# noinspection PyTypeChecker
def test_Inscription_payDayPassed():
    inscription = Inscription(date(2022, 8, 8), client=None, activity=None)

    # The client wasn't charged for the activity after he signed up. 06/09/2022 is the 30st day after the inscription
    # date, so the inscription charge day hasn't passed yet.
    assert not inscription.charge_day_passed(today=date(2022, 9, 6))

    # The client wasn't charged for the activity after he signed up. 07/09/2022 is the 31st day after the inscription
    # date, so the inscription charge day has passed.
    assert inscription.charge_day_passed(today=date(2022, 9, 7))

    # The client is charged for the inscription.
    inscription.transaction = Transaction(1, type=None, client=None, when=date(2022, 9, 7), amount=None, method=None,
                                          responsible=None, description=None)

    assert not inscription.charge_day_passed(today=date(2022, 9, 7))
    assert not inscription.charge_day_passed(today=date(2022, 10, 6))  # Only 30 days have passed since the charge.
    assert inscription.charge_day_passed(today=date(2022, 10, 7))  # 31 days have passed since the charge.


# noinspection PyTypeChecker
def test_Inscription_registerCharge_raisesValueError():
    client = Client(Number(1), name=None, admission=None, telephone=None, direction=None, is_active=True)
    other_client = Client(Number(2), name=None, admission=None, telephone=None, direction=None, is_active=True)
    activity = Activity(0, String("name", max_len=20), price=None, pay_once=True, description=None)

    with pytest.raises(ValueError):
        trans = Transaction(1, type=None, client=other_client, when=None, amount=None, method=None, responsible=None,
                            description=None)
        Inscription(when=None, client=client, activity=activity).register_charge(trans)

    with pytest.raises(ValueError):
        trans = Transaction(1, type=None, client=client, when=None, amount=None, method=None, responsible=None,
                            description=None)
        Inscription(when=None, client=other_client, activity=activity).register_charge(trans)
