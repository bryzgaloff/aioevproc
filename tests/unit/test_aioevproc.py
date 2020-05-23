import asyncio
import contextlib
import unittest
import unittest.mock
from typing import AsyncGenerator, Generator, Literal

from aioevproc import EventsProcessor, handler, Event


class _AioEvProcTestCase(unittest.TestCase):
    def setUp(self):
        self._loop = asyncio.get_event_loop()


class WithPredicateTestCase(_AioEvProcTestCase):
    @staticmethod
    def _test_predicate(return_value: bool):
        predicate_mock = unittest.mock.Mock(return_value=return_value)
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(predicate_mock)
            async def handler_with_true_predicate(self, _: Event) -> None:
                handler_mock()

        proc = TestEventsProcessor()
        event = {}
        asyncio.get_event_loop().run_until_complete(proc.process_event(event))
        predicate_mock.assert_called_once_with(event)
        handler_mock.assert_called_once() \
            if return_value else handler_mock.assert_not_called()

    @classmethod
    def test_predicate_true(cls):
        cls._test_predicate(True)

    @classmethod
    def test_predicate_false(cls):
        cls._test_predicate(False)


class NoPredicateTestCase(_AioEvProcTestCase):
    @staticmethod
    def test_handler_called():
        class TestEventsProcessor(EventsProcessor):
            @handler()
            def handler_with_no_predicate(self, _: Event) -> None:
                mock()
        mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        mock.assert_called_once()


class MiddlewareTestCase(_AioEvProcTestCase):
    def test_async(self):
        class TestEventsProcessor(EventsProcessor):
            @handler()
            @contextlib.asynccontextmanager
            async def async_middleware(self, _: Event) -> AsyncGenerator:
                middleware_mock()
                handler_mock.assert_not_called()
                yield
                handler_mock.assert_called_once()
                middleware_mock()

            @handler()
            def handler(self, _: Event) -> None:
                middleware_mock.assert_called_once()
                handler_mock()

        middleware_mock = unittest.mock.Mock()
        handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        self.assertEqual(2, middleware_mock.call_count)

    def test_sync_exception(self):
        class TestEventsProcessor(EventsProcessor):
            @handler()
            @contextlib.contextmanager
            def sync_middleware(self, _: Event) -> Generator:
                middleware_mock()
                handler_mock.assert_not_called()
                try:
                    yield
                except RuntimeError:
                    handler_mock.assert_called_once()
                    middleware_mock()

            @handler()
            def handler(self, _: Event) -> None:
                middleware_mock.assert_called_once()
                handler_mock()

        middleware_mock = unittest.mock.Mock()
        handler_mock = unittest.mock.Mock(side_effect=RuntimeError)
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        self.assertEqual(2, middleware_mock.call_count)


class PredicatesConjunctionTestCase(_AioEvProcTestCase):
    @staticmethod
    def test_first_predicate_false():
        first_predicate_mock = unittest.mock.Mock(return_value=False)
        second_predicate_mock = unittest.mock.Mock()
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(first_predicate_mock, second_predicate_mock)
            def handler_with_predicates_conjunction(self, _: Event) -> None:
                handler_mock()

        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        first_predicate_mock.assert_called_once()
        second_predicate_mock.assert_not_called()  # short circuit logic
        handler_mock.assert_not_called()

    @staticmethod
    def test_second_predicate_false():
        first_predicate_mock = unittest.mock.Mock(return_value=True)
        second_predicate_mock = unittest.mock.Mock(
            side_effect=lambda _:
            first_predicate_mock.assert_called_once() or False,
        )

        class TestEventsProcessor(EventsProcessor):
            @handler(first_predicate_mock, second_predicate_mock)
            def handler_with_predicates_conjunction(self, _: Event) -> None:
                handler_mock()

        handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        second_predicate_mock.assert_called_once()
        handler_mock.assert_not_called()

    def test_both_predicates_true(self):
        predicate_mock = unittest.mock.Mock(return_value=True)
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(predicate_mock, predicate_mock)
            def handler_with_predicates_conjunction(self, _: Event) -> None:
                handler_mock()

        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        self.assertEqual(2, predicate_mock.call_count)
        handler_mock.assert_called_once()


class PredicatesDisjunctionTestCase(_AioEvProcTestCase):
    def test_no_predicates_assertion(self):
        with self.assertRaises(AssertionError):
            class TestEventsProcessor(EventsProcessor):
                @handler()
                @handler(lambda _: True)
                def handler_with_incorrect_predicates(self, _: Event) -> None:
                    pass

    @staticmethod
    def test_first_predicate_true():
        first_predicate_mock = unittest.mock.Mock(return_value=True)
        second_predicate_mock = unittest.mock.Mock()
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(first_predicate_mock)
            @handler(second_predicate_mock)
            def handler_with_predicates_disjunction(self, _: Event) -> None:
                handler_mock()

        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        first_predicate_mock.assert_called_once()
        second_predicate_mock.assert_not_called()  # short circuit logic
        handler_mock.assert_called_once()

    @staticmethod
    def test_first_predicate_false():
        first_predicate_mock = unittest.mock.Mock(return_value=False)
        second_predicate_mock = unittest.mock.Mock(
            side_effect=lambda _:
                first_predicate_mock.assert_called_once() or True,
        )
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(first_predicate_mock)
            @handler(second_predicate_mock)
            def handler_with_predicates_disjunction(self, _: Event) -> None:
                second_predicate_mock.assert_called_once()
                handler_mock()

        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        handler_mock.assert_called_once()

    def test_both_predicates_false(self):
        predicate_mock = unittest.mock.Mock(return_value=False)
        handler_mock = unittest.mock.Mock()

        class TestEventsProcessor(EventsProcessor):
            @handler(predicate_mock)
            @handler(predicate_mock)
            def handler_with_predicates_disjunction(self, _: Event) -> None:
                handler_mock()

        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        self.assertEqual(2, predicate_mock.call_count)
        handler_mock.assert_not_called()


class HandlerReturnsTruthyValueTestCase(_AioEvProcTestCase):
    @staticmethod
    def test_true():
        class TestEventsProcessor(EventsProcessor):
            @handler()
            def handler_returns_true(self, _: Event) -> Literal[True]:
                first_handler_mock()
                return True

            @handler()
            def second_handler(self, _: Event) -> None:
                first_handler_mock.assert_called_once()
                second_handler_mock()

        first_handler_mock = unittest.mock.Mock()
        second_handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        second_handler_mock.assert_called_once()

    @staticmethod
    def test_truthy_value():
        class TestEventsProcessor(EventsProcessor):
            @handler()
            def handler_returns_true(self, _: Event) -> str:
                first_handler_mock()
                return 'abc'  # not false

            @handler()
            def second_handler(self, _: Event) -> None:
                first_handler_mock.assert_called_once()
                second_handler_mock()

        first_handler_mock = unittest.mock.Mock()
        second_handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        second_handler_mock.assert_called_once()


class HandlerReturnsFalsyValueTestCase(_AioEvProcTestCase):
    @staticmethod
    def test_none():
        class TestEventsProcessor(EventsProcessor):
            @handler()
            def handler_returns_true(self, _: Event) -> None:
                first_handler_mock()

            @handler()
            def second_handler(self, _: Event) -> None:
                second_handler_mock()

        first_handler_mock = unittest.mock.Mock()
        second_handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        first_handler_mock.assert_called_once()
        second_handler_mock.assert_not_called()

    @staticmethod
    def test_false():
        class TestEventsProcessor(EventsProcessor):
            @handler()
            def handler_returns_true(self, _: Event) -> Literal[False]:
                first_handler_mock()
                return False

            @handler()
            def second_handler(self, _: Event) -> None:
                second_handler_mock()

        first_handler_mock = unittest.mock.Mock()
        second_handler_mock = unittest.mock.Mock()
        processor = TestEventsProcessor()
        asyncio.get_event_loop().run_until_complete(processor.process_event({}))
        first_handler_mock.assert_called_once()
        second_handler_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
