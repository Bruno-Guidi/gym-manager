from __future__ import annotations

from typing import Callable, ClassVar

from gym_manager.core.base import String


class SecurityError(Exception):
    """Exception raised when there is a security related problem.
    """
    def __init__(
            self, responsible: String, executed_fn: Callable, action_tag: str, action_name: str, *args: object
    ) -> None:
        super().__init__(*args)
        self.responsible = responsible
        self.executed_fn = executed_fn
        self.action_tag = action_tag
        self.action_name = action_name


class log_responsible:
    """Decorator used to facilitate the registering of action's responsible.

    Before executing a function, checks if it requires a responsible and then checks if the responsible was set in
    the handler. If both conditions are met, raise a SecurityException.

    After executing a function, calls ResponsibleHandler.handle(args), so it can do whatever action is required. This
    action could be logging in a file, in a database, etc.
    """
    def __init__(self, handler: SecurityHandler, action_tag: str, action_name: str):
        """Init method.

        Args:
            handler: handles security related things.
            action_tag: tag used to identify the function being performed.
            action_name: display name of the function being performed.
        """
        self.handler = handler
        self.action_tag = action_tag
        self.action_name = action_name

    def __call__(self, fn, *args, **kwargs):
        def wrapped():
            if self.handler.responsible_not_set(self.action_tag):
                raise SecurityError(self.handler.responsible, fn, self.action_tag, self.action_name)
            fn(*args, **kwargs)
            self.handler.handle(self.action_tag, self.action_name)
        return wrapped


class SecurityHandler:
    _singleton: ClassVar[SecurityHandler] = None

    @classmethod
    def get(cls, action_tags: set[str] | None = None, needs_responsible: set[str] | None = None) -> SecurityHandler:
        """Returns a singleton instance of SecurityHandler. If it is None, then create one.

        Args:
            action_tags: tags of existing actions in the system.
            needs_responsible: tags of existing actions that need a responsible to be executed. It must be a subset of
                *action_tags*.

        Raises:
            ValueError if *needs_responsible* is not a subset of *action_tags*, or if calling the method for the first
                time without all arguments.
        """
        if SecurityHandler._singleton is None:
            if action_tags is None or needs_responsible is None:
                raise ValueError(
                    "The first call of ResponsibleHandler.get(args) classmethod requires the arguments [action_tags="
                    "{action_tags}] and [needs_responsible{needs_responsible}] to be not None.")
            SecurityHandler._singleton = SecurityHandler(action_tags, needs_responsible)
        return SecurityHandler._singleton

    def __init__(self, action_tags: set[str], needs_responsible: set[str]):
        """Init method.

        Args:
            action_tags: tags of existing actions in the system.
            needs_responsible: tags of existing actions that need a responsible to be executed. It must be a subset of
                *action_tags*.

        Raises:
            ValueError if *needs_responsible* is not a subset of *action_tags*.
        """
        if not needs_responsible.issubset(action_tags):
            raise ValueError(f"Argument [needs_responsible={needs_responsible}] must be a subset of argument ["
                             f"action_tags={action_tags}].")

        self.responsible = String("", optional=True, max_len=30)
        self.action_tags = action_tags
        self._needs_responsible = needs_responsible

    def responsible_not_set(self, action_tag: str) -> bool:
        """Returns True if *action_tag* needs a responsible to be executed and there is no responsible specified.
        """
        return action_tag in self._needs_responsible and len(self.responsible) == 0

    def handle(self, action_level, action_name):
        """Does whatever is needed after executing a given action.
        """
        print(f"Responsible '{self.responsible}' did the action '{action_name}' that has a level '{action_level}'.")
