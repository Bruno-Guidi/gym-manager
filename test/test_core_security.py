from datetime import datetime
from typing import Generator

import pytest

from gym_manager.core.base import String
from gym_manager.core.security import (
    SimpleSecurityHandler, SecurityRepo, Responsible, SecurityError, log_responsible,
    Action)


class MockSecurityRepo(SecurityRepo):

    def responsible(self) -> Generator[Responsible, None, None]:
        to_yield = [Responsible(String("RespA", max_len=10), String("1", max_len=3)),
                    Responsible(String("RespB", max_len=10), String("2", max_len=3))]
        for resp in to_yield:
            yield resp

    def add_responsible(self, *responsible):
        pass

    def log_action(self, when: datetime, responsible: Responsible, action_tag: str, action_name: str):
        pass

    def actions(self, page: int = 1, page_len: int = 20) -> Generator[Action, None, None]:
        pass


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


def test_SimpleSecurityHandler_unregisteredAction():
    security_handler = SimpleSecurityHandler(MockSecurityRepo(), action_tags={"other"}, needs_responsible=set())
    assert security_handler.unregistered_action("tag")
    assert not security_handler.unregistered_action("other")


def test_SimpleSecurityHandler_CantPerformAction():
    security_handler = SimpleSecurityHandler(MockSecurityRepo(), action_tags={"a", "b"}, needs_responsible={"a"})

    # There is no responsible defined, and the action needs one.
    assert security_handler.cant_perform_action("a")
    # The action doesn't need a responsible, so there is no problem.
    assert not security_handler.cant_perform_action("b")

    # There is a responsible, so both actions can be executed.
    security_handler.current_responsible = String("RespA", max_len=15)
    assert not security_handler.cant_perform_action("a")
    assert not security_handler.cant_perform_action("b")

    # There is a responsible, so both actions can be executed.
    security_handler.current_responsible = String("2", max_len=15)
    assert not security_handler.cant_perform_action("a")
    assert not security_handler.cant_perform_action("b")


