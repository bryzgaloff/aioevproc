# aioevproc

It is a minimal async/sync event processing framework. Has **no dependencies**
    and uses nothing except **pure Python 3.8**.

_TL;DR_ Do not have much time? See [recap on examples](#recap-on-examples) and
    [recap on conditions](#recap-on-conditions). Now go and use `aioevproc`! :)

## Examples

Simplest example for a single async handler, just echo the message text:

```python
from aioevproc import EventsProcessor, handler, Event

class EchoTelegramBot(EventsProcessor):
    @handler(lambda event: 'message' in event and 'text' in event['message'])
    async def echo_message(self, event: Event) -> None:
        await self.reply_to_message(text=event['message']['text'])
```

A little bit more complex Telegram bot example, see the
    [explanation below](#what-do-the-examples-demonstrate):

```python
from aioevproc import EventsProcessor, handler, Event
from contextlib import asynccontextmanager, contextmanager

class TelegramBot(EventsProcessor):
    # synchronous middleware for any exception: log exception
    @handler()
    @contextmanager
    def log_exception(self, event: Event) -> Generator[None, None, None]:
        try:
            yield
        except:
            logging.exception('Error!')

    # async middleware for any exception: send excuse message to the user
    @handler()
    @asynccontextmanager
    def send_excuse_message(self, event: Event) -> AsyncGenerator[None, None]:
        try:
            yield
        except:
            await self.send_message('Sorry!')

    # synchronous handler for all updates: log message
    @handler()
    def log_update_id(self, event: Event) -> Literal[True]:
        logging.info(event['update_id'])
        return True  # call following handlers

    # async handler to check if user is admin for update with messages and cb
    @handler(lambda event: 'message' in event or 'callback_query' in event)
    async def check_admin(self, event: Event) -> bool:
        # the next handler will be called only if this returns True
        return event['message']['from_user']['id'] in await self.get_admins()
 
    # async handler to echo updates containing a message
    @handler(lambda event: 'message' in event and 'text' in event['message'])
    async def echo_message(self, event: Event) -> None:
        # if the update contains a message then echo it
        await self.reply_to_message(text=event['message']['text'])

    # async handler to answer a callback query
    @handler(lambda event: 'callback_query' in event)
    async def echo_message(self, event: Event) -> None:
        # if the update does not contain a message but a callback query, answer
        await self.answer_callback_query(event['callback_query']['id'])
```

## What do the examples demonstrate?

`handler` decorates methods of `EventsProcessor` subclasses. The method can be
    one of: async function (like `check_admin`, `handle_message` and
    `echo_message` in the example above), sync function (`log_update_id`), async
    context manager (`send_excuse_message`) or sync context manager
    (`log_exception`).

All of the handlers are called in the same order as they are declared in the
    class body. Middlewares follow the same rule: they are entered in the order
    of declaration and exited in the reversed order (in a recursive manner).

Sync and async handlers may return a value: if it is not a truthy value then
    none of the following handlers will be called and event processing will be
    stopped at the handler which **did not** return truthy value.

Please notice: if you return nothing from the sync/async handler method (means
    you implicitly `return None`) then none of the following handlers will be
    called. This is an intended default behavior since usually an event requires
    a single handler. None is a falsy (not truthy) value.

Returning `True` from the handler is useful for logging purposes: the logging
    method should not block further processing of the event. This is shown in
    the example below (`log_update_id`) as well as the filtering use case for
    admins: if the user is not an admin then `check_admin` will return `False`
    and no further processing will be done.

Middlewares are based on context managers and are intended to be used for
    exceptions handling. Also use them when some related actions are required
    before and after the event is processed by other handlers: for example, for
    measuring the execution time.

### Recap on examples

Let's sum up on the [examples](#examples):
1. `aioevproc` supports both sync and async handlers and middlewares.
2. Every handler or middleware has to be a method of `EventsProcessor` subclass.
3. If the handler does not return a truthy value then the following handlers are
    not called.
4. Middlewares are sync/async context managers.
5. Handlers and middlewares are called in the same order as they are declared.

## How to use the handlers conditions

Handler usually has to be applied to certain types of events, not all. The
    following handler will be applied only to updates containing a message:
```python
@handler(lambda event: 'message' in event)
async def handle_event(self, event: Event) -> None:
    pass
```

If the condition check fails then the next handler condition will be checked:
```python
@handler(lambda event: False)
def always_skipped(self, event: Event) -> Literal[False]:
    # this handler is never called since its predicate always evaluates to False
    return False  # has no effect since this handler is not called

# since previous handler condition check failed this one will be checked next
@handler(lambda event: 'edited_message' in event)
def log_message_edit(self, event: Event) -> None:
    pass
```

Please notice: if the handler condition check failed then the handler's return
    value does not affect the next handlers. The return value of the handler
    affects the next handlers only if the handler itself is called (meaning 
    that its condition check is passed).

You can specify multiple predicates in a `handler` call: this will make handler
    to be called only if **all** of the predicates evaluate to a truthy value
    for the event. Example below shows the handers which will be applied only to
    updates with text messages:
```python
@handler(
        lambda event: 'message' in event,
        lambda event: 'text' in event['message'],
)
async def handle_event(self, event: Event) -> None:
    pass
```

The predicates are evaluated in the same order as they are declared. So the
    above pair of conditions is equivalent to
    `'message' in event and 'text' in event['message']`. This means that
    specifying multiple predicates for a single `handler` call implements AND
    semantics (conditions conjunction).

If you need to apply single handler if **any** of the conditions is true, use
    multiple `handler` calls:
```python
@handler(lambda event: 'message' in event)
@handler(lambda event: 'callback_query' in event)
async def handle_event(self, event: Event) -> None:
    pass
```

This will apply the handler for either update with a message or update with a
    callback query. This form implements OR semantics (conditions disjunction).

Please notice: the implementation of `aioevproc` checks handlers predicates in
    the same order as they are declared. First `'message' in event` will be
    checked and after that the `'callback_query' in event` predicate will be
    evaluated. This is a reversed order to how Python applies decorators: Python
    applies the most inner decorator first. But `aioevproc` applies the most
    outer `handler` call first since it is more intuitive.

If you need a handler to be applied unconditionally then use just `handler()`
    without arguments.

Please notice: you cannot use `handler()` without arguments on a handler with
    any other `handler` call with arguments since this has no sense:
```python
@handler()  # will raise an AssertionError
@handler(lambda event: 'message' in event)
async def handle_event(self, event: Event) -> None:
    pass
```

Don't forget to `return True` from unconditionally applied handler to not ignore
    all of the following handlers!

### Recap on conditions

Let's sum up on [conditions](#how-to-use-the-handlers-conditions):
1. Single `handler` call accepts multiple predicates as arguments. The handler
    then will be called only if **all** of the predicates are true (AND semantics).
2. If a handler method (or middleware) is decorated with multiple `handler`
    calls then the handler will be called if **any** of the `handler`s'
    conditions is true (OR semantics).
3. OR and AND semantics can be combined.
4. If the handler's conditions check failed then the handler is skipped and the
    next handlers' conditions are checked until the matching handler is found.
5. All the conditions are checked in the same order as they are declared. The
    most outer `handler` decorator is applied first.
6. Handler decorated with `handler()` w/o arguments is applied unconditionally.

## Installation

`pip install aioevproc`

## How to run tests

From project root directory: `python -m unittest discover -s tests/unit`
