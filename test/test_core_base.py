import pytest

from gym_manager.core.base import ValidationError, Number


def test_Number_validInputType():
    Number(5, min_value=0, max_value=100)
    Number("5", min_value=0, max_value=100)


def test_Number_raisesValidationError_invalidInputType():
    with pytest.raises(ValidationError) as valid_err:
        Number([5])
    assert str(valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type([5])}]"

    with pytest.raises(ValidationError) as valid_err:
        Number(())
    assert str(valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type(())}]"

    with pytest.raises(ValidationError) as valid_err:
        Number({"5"})
    assert str(valid_err.value) == f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type({5})}]"


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
    assert str(valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={max_value}]"

    # Given value is str and above given minimum
    with pytest.raises(ValidationError) as valid_err:
        Number(str(max_value), min_value=min_value, max_value=max_value)
    assert str(valid_err.value) == f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={max_value}]"
