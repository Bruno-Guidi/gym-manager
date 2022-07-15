from __future__ import annotations

import abc
import logging
from typing import Callable, ClassVar, Generator

from gym_manager.core.base import String

logger = logging.getLogger(__name__)


class Responsible:
    def __init__(self, name: String, code: String):
        self.name = name
        self.code = code


class SecurityError(Exception):
    """Exception raised when there is a security related problem.
    """
    INVALID_RESP: ClassVar[int] = 0

    def __init__(
            self,
            cause: str,
            code: int,
            responsible: Responsible | None = None,
            executed_fn: Callable = None,
            action_tag: str | None = None,
            action_name: str | None = None,
            *args: object
    ) -> None:
        super().__init__(cause, *args)
        self.responsible = responsible
        self.executed_fn = executed_fn
        self.action_tag = action_tag
        self.action_name = action_name
        self.code = code


class log_responsible:
    """Decorator used to facilitate the registering of action's responsible.

    Before executing a function, checks if it requires a responsible and then checks if the responsible was set in
    the handler. If both conditions are met, raise a SecurityException.

    After executing a function, calls ResponsibleHandler.handle(args), so it can do whatever action is required. This
    action could be logging in a file, in a database, etc.
    """
    handler: ClassVar[SecurityHandler] = None

    @classmethod
    def config(cls, handler: SecurityHandler):
        cls.handler = handler

    def __init__(self, action_tag: str, action_name: str):
        """Init method.

        Args:
            action_tag: tag used to identify the function being performed.
            action_name: display name of the function being performed.
        """
        self.action_tag = action_tag
        self.action_name = action_name

    def __call__(self, fn):
        def wrapped(*args):
            if self.handler is None:
                raise ValueError("There is no SecurityHandler defined.")
            if self.handler.unregister_action(self.action_tag):
                raise SecurityError("Tried to execute an unregistered action.",
                                    self.handler.current_responsible, fn, self.action_tag, self.action_name)
            if self.handler.cant_perform_action(self.action_tag):
                raise SecurityError("Tried to execute action without a defined responsible.",
                                    self.handler.current_responsible, fn, self.action_tag, self.action_name)
            result = fn(*args)
            self.handler.handle_action(self.action_tag, self.action_name)
            return result
        return wrapped


class SecurityRepo(abc.ABC):
    @abc.abstractmethod
    def responsible(self) -> Generator[Responsible, None, None]:
        raise NotImplementedError


class SecurityHandler(abc.ABC):
    @property
    @abc.abstractmethod
    def current_responsible(self) -> String:
        raise NotImplementedError

    @current_responsible.setter
    @abc.abstractmethod
    def current_responsible(self, responsible_id: String):
        raise NotImplementedError

    @abc.abstractmethod
    def unregister_action(self, action_tag: str) -> bool:
        """Returns true if the action with *action_tag* isn't registered in the security handler-
        """
        raise NotImplementedError

    @abc.abstractmethod
    def cant_perform_action(self, action_tag: str) -> bool:
        """Returns True if the action with *action_tag* can't be performed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def handle_action(self, action_level: str, action_name: str):
        """Does whatever is needed after executing a given action.
        """
        raise NotImplementedError


class SimpleSecurityHandler(SecurityHandler):
    def __init__(self, security_repo: SecurityRepo, action_tags: set[str], needs_responsible: set[str]):
        """Init method.

        Args:
            security_repo: repository that stores security related things.
            action_tags: tags of existing actions in the system.
            needs_responsible: tags of existing actions that need a responsible to be executed. It must be a subset of
                *action_tags*.

        Raises:
            ValueError if *needs_responsible* is not a subset of *action_tags*.
        """
        if not needs_responsible.issubset(action_tags):
            raise ValueError(f"Argument [needs_responsible={needs_responsible}] must be a subset of argument ["
                             f"action_tags={action_tags}].")

        self.security_repo = security_repo
        self._responsible_names, self._responsible_codes = set(), set()
        for responsible in security_repo.responsible():
            self._responsible_names.add(responsible.name)
            self._responsible_codes.add(responsible.code)

        self._responsible = String("", optional=True, max_len=30)

        self.action_tags = action_tags
        self._needs_responsible = needs_responsible

    @property
    def current_responsible(self) -> String:
        return self._responsible

    @current_responsible.setter
    def current_responsible(self, responsible_id: String):
        # The *responsible_id* must match with an existing name or id.
        if not (responsible_id in self._responsible_names or responsible_id in self._responsible_codes):
            raise SecurityError(f"Responsible [responsible_id={responsible_id}] not recognized.",
                                code=SecurityError.INVALID_RESP)
        self._responsible = responsible_id

    def unregister_action(self, action_tag: str) -> bool:
        """Returns true if the action with *action_tag* isn't registered in the security handler-
        """
        return action_tag not in self.action_tags

    def cant_perform_action(self, action_tag: str) -> bool:
        """Returns True if *action_tag* needs a responsible to be executed and there is no responsible specified.
        """
        return action_tag in self._needs_responsible and len(self._responsible) == 0

    def handle_action(self, action_level: str, action_name: str):
        """Creates a logger entry. ToDo create a record in db.
        """
        logger.info(
            f"Responsible '{self._responsible}' did the action '{action_name}' that has a level '{action_level}'."
        )
