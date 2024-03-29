from __future__ import annotations

import abc
import logging
from datetime import datetime
from typing import Callable, ClassVar, Generator, TypeAlias, Iterable, Any

from gym_manager.core.base import String

logger = logging.getLogger(__name__)


class Responsible:
    def __init__(self, name: String, code: String):
        self.name = name
        self.code = code

    def __eq__(self, other: Responsible) -> bool:
        return self.name == other.name and self.code == other.code


class SecurityError(Exception):
    """Exception raised when there is a security related problem.
    """
    INVALID_RESP: ClassVar[int] = 0
    UNREGISTERED_ACTION: ClassVar[int] = 1
    NEEDS_RESP: ClassVar[int] = 2

    def __init__(
            self,
            cause: str,
            code: int,
            responsible: Responsible | None = None,
            executed_fn: Callable = None,
            action_tag: str | None = None,
            *args: object
    ) -> None:
        super().__init__(cause, *args)
        self.responsible = responsible
        self.executed_fn = executed_fn
        self.action_tag = action_tag
        self.code = code


# noinspection PyPep8Naming
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

    def __init__(self, action_tag: str, to_str: Callable[[Any], str]):
        """Init method.

        Args:
            action_tag: tag used to identify the function being performed.
            to_str: function that generates a str that describes the executed action. This function must check whether
                the received object type is correct or not.
        """
        self.action_tag = action_tag
        self.to_str = to_str

    def __call__(self, fn):
        def wrapped(*args):
            if self.handler is None:
                raise ValueError("There is no SecurityHandler defined.")
            if self.handler.unregistered_action(self.action_tag):
                raise SecurityError("Tried to execute an unregistered action.", SecurityError.UNREGISTERED_ACTION,
                                    self.handler.current_responsible, fn, self.action_tag)
            if self.handler.cant_perform_action(self.action_tag):
                raise SecurityError("Tried to execute action without a defined responsible.", SecurityError.NEEDS_RESP,
                                    self.handler.current_responsible, fn, self.action_tag)
            result = fn(*args)
            self.handler.handle_action(self.action_tag, self.to_str(result))
            return result

        return wrapped


Action: TypeAlias = tuple[datetime, Responsible, str, str]


class SecurityRepo(abc.ABC):
    @abc.abstractmethod
    def responsible(self) -> Generator[Responsible, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_responsible(self, responsible: Responsible):
        raise NotImplementedError

    @abc.abstractmethod
    def log_action(self, when: datetime, responsible: Responsible, action_tag: str, action_name: str):
        raise NotImplementedError

    @abc.abstractmethod
    def actions(self, page: int = 1, page_len: int = 20, tag: str | None = None) -> Generator[Action, None, None]:
        raise NotImplementedError


class SecurityHandler(abc.ABC):
    @property
    @abc.abstractmethod
    def action_tags(self) -> Iterable[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_responsible(self, responsible: Responsible):
        raise NotImplementedError

    @abc.abstractmethod
    def all_responsible(self) -> Iterable[Responsible]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def current_responsible(self) -> Responsible:
        raise NotImplementedError

    @current_responsible.setter
    @abc.abstractmethod
    def current_responsible(self, responsible_id: String):
        raise NotImplementedError

    @abc.abstractmethod
    def unregistered_action(self, action_tag: str) -> bool:
        """Returns true if the action with *action_tag* isn't registered in the security handler-
        """
        raise NotImplementedError

    @abc.abstractmethod
    def cant_perform_action(self, action_tag: str) -> bool:
        """Returns True if the action with *action_tag* can't be performed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def handle_action(self, action_level: str, action_description: str):
        """Does whatever is needed after executing a given action.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def actions(self, page: int = 1, page_len: int = 20, tag: str | None = None) -> Iterable[Action]:
        raise NotImplementedError


NO_RESPONSIBLE = Responsible(name=String("", optional=True), code=String("", optional=True))


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
        self._responsible_dict: dict[String, Responsible] = {}  # Keys can be responsible codes or names.
        for responsible in security_repo.responsible():
            self._responsible_dict[responsible.code] = responsible
            self._responsible_dict[responsible.name] = responsible

        self._responsible = NO_RESPONSIBLE

        self._action_tags = action_tags
        self._needs_responsible = needs_responsible

    @property
    def action_tags(self) -> Iterable[str]:
        yield from self._action_tags

    def add_responsible(self, responsible: Responsible):
        self.security_repo.add_responsible(responsible)
        self._responsible_dict[responsible.code] = responsible
        self._responsible_dict[responsible.name] = responsible

    def all_responsible(self) -> Iterable[Responsible]:
        yield from self.security_repo.responsible()

    @property
    def current_responsible(self) -> Responsible:
        return self._responsible

    @current_responsible.setter
    def current_responsible(self, responsible_id: String):
        # The responsible field was empty. Do nothing, this situation is covered log_responsible decorator.
        if len(responsible_id) == 0:
            self._responsible = NO_RESPONSIBLE
            return

        # The *responsible_id* must match with an existing name or id.
        if not (responsible_id in self._responsible_dict or responsible_id in self._responsible_dict):
            raise SecurityError(f"Responsible [responsible_id={responsible_id}] not recognized.",
                                code=SecurityError.INVALID_RESP)
        self._responsible = self._responsible_dict[responsible_id]

    def unregistered_action(self, action_tag: str) -> bool:
        """Returns true if the action with *action_tag* isn't registered in the security handler-
        """
        return action_tag not in self._action_tags

    def cant_perform_action(self, action_tag: str) -> bool:
        """Returns True if *action_tag* needs a responsible to be executed and there is no responsible specified.
        """
        return action_tag in self._needs_responsible and self._responsible == NO_RESPONSIBLE

    def handle_action(self, action_level: str, action_description: str):
        """Creates a logger entry.
        """
        logger.getChild(type(self).__name__).info(
            f"Responsible '{self._responsible.name}' did the action '{action_description}'."
        )
        if action_level in self._needs_responsible:
            self.security_repo.log_action(datetime.now(), self.current_responsible, action_level, action_description)

    def actions(self, page: int = 1, page_len: int = 20, tag: str | None = None) -> Iterable[Action]:
        yield from self.security_repo.actions(page, page_len, tag)
