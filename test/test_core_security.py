from typing import Generator

import pytest

from gym_manager.core.base import String
from gym_manager.core.security import SimpleSecurityHandler, SecurityRepo, Responsible, SecurityError


class MockSecurityRepo(SecurityRepo):

    def responsible(self) -> Generator[Responsible, None, None]:
        to_yield = [Responsible(String("RespA", max_len=10), String("1", max_len=3)),
                    Responsible(String("RespB", max_len=10), String("2", max_len=3))]
        for resp in to_yield:
            yield resp


def test_SimpleSecurityHandler_currentResponsibleSetter():
    security_handler = SimpleSecurityHandler(MockSecurityRepo(), action_tags=set(), needs_responsible=set())

    # There is a name match.
    security_handler.current_responsible = String("RespA", max_len=10)
    # There is a code match.
    security_handler.current_responsible = String("1", max_len=3)

    with pytest.raises(SecurityError) as sec_err:
        # optional kwarg is True because responsible field is optional by default, to allow executing actions without
        # responsible. If a particular action needs a responsible, then it's the job of SecurityHandler to block the
        # execution.
        security_handler.current_responsible = String("RespC", optional=True, max_len=10)
    assert sec_err.value.code == SecurityError.INVALID_RESP

