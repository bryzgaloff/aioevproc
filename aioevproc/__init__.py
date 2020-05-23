import asyncio
from contextlib import AsyncExitStack
from typing import *

Event = TypeVar('Event')
EventPredicate = Callable[[Event], bool]
HandlerMethodRetType = Union[
    Awaitable[Optional[Literal[True]]],  # async handler
    Optional[Literal[True]],             # sync handler
    AsyncContextManager[None],           # async middleware
    ContextManager[None],                # sync middleware
]
HandlerMethod = Callable[['Bot', Event], HandlerMethodRetType]
_HANDLER_ATTR = '__handler_predicates__'


def handler(*predicates: EventPredicate) \
        -> Callable[[HandlerMethod], HandlerMethod]:
    """ Usage:

    >>> class Bot(EventsProcessor):
    >>>     @handler(lambda event: event['type'] == 'bot_started')
    >>>     @handler(
    >>>         lambda event: event['type'] == 'message_created',
    >>>         lambda event: event['message']['text'] == '/start',
    >>>     )
    >>>     def handle_event(self, event): pass

    Equivalent to following condition:
    ``if type == bot_started or type == message_created and text == '/start'``
    """
    def decorator(handler_method: HandlerMethod) -> HandlerMethod:
        if not predicates:
            assert hasattr(handler_method, _HANDLER_ATTR) is False
            setattr(handler_method, _HANDLER_ATTR, None)
        else:
            if not hasattr(handler_method, _HANDLER_ATTR):
                setattr(handler_method, _HANDLER_ATTR, [])
            _handler_predicates: Optional[List[Tuple[EventPredicate, ...]]] = \
                getattr(handler_method, _HANDLER_ATTR)
            assert _handler_predicates is not None
            _handler_predicates.append(predicates)
        return handler_method
    return decorator


class EventsProcessor:
    _handlers: ClassVar[Tuple[
        Tuple[
            Optional[List[Tuple[EventPredicate, ...]]],
            HandlerMethod,
        ],
        ...,
    ]]

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls._handlers = tuple(
            (
                # predicates are reversed to follow the order of the decorators
                tuple(reversed(predicates))
                    if (predicates := getattr(handler_method, _HANDLER_ATTR))
                        is not None
                    else None,
                handler_method,
            )
            for handler_method in cls.__dict__.values()
            if hasattr(handler_method, _HANDLER_ATTR)
        )

    async def process_event(self, event: Event) -> None:
        async with AsyncExitStack() as middlewares_stack:
            for or_predicates, handler_method in self._handlers:
                if or_predicates is not None and not any(
                        all(pred(event) for pred in and_predicates)
                        for and_predicates in or_predicates
                ):
                    continue
                ret_val = handler_method(self, event)
                call_next_handlers = True
                if asyncio.iscoroutine(ret_val):
                    call_next_handlers = await ret_val
                elif isinstance(ret_val, AsyncContextManager):
                    await middlewares_stack.enter_async_context(ret_val)
                elif isinstance(ret_val, ContextManager):
                    middlewares_stack.enter_context(ret_val)
                else:  # handler_method is just a synchronous method
                    call_next_handlers = ret_val
                if not call_next_handlers:
                    break
