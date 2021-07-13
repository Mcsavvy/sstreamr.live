import typing
import pandas as pd
from datetime import datetime
from collections import OrderedDict
from _utils import (
    HandledBug, DrownedBug, UnExpectedBug, ReRaised,
    _makeRepr, _isBug, _flatten_, ON, _compare,
    _parseSlice
)
from functools import wraps
from _vars import (
    INVOKE, USAGE
)


_DB_INDEX_ = {}


def _get_db_index(instance=None):
    if not instance:
        if not _DB_INDEX_:
            return 0
        else:
            return max(_DB_INDEX_.values()) + 1
    else:
        return _DB_INDEX_.get(instance)


def _make_data_structure(instance):
    instance.dataframe = pd.DataFrame(
        {},
        columns='bug type line_no caught trigger'.split()
    )
    _DB_INDEX_[instance] = _get_db_index()
    instance.index = _get_db_index(instance)
    instance.AWAITING = OrderedDict()
    instance.INVOKED = OrderedDict()
    instance.DROWN = set()
    instance.DROWNED = set()
    instance.EXPECTED = '...'
    instance.logger = print


class Bug(Exception):
    __doc__ = USAGE
    # Exception Stacking Logic

    def _await_(
        self,
        trigger,
        invoker: typing.Union[typing.Callable, slice],
    ):
        trigger = tuple(_flatten_(trigger))
        for t in trigger:
            self.AWAITING[t] = _parseSlice(invoker)

    def _invokeAwaiting(self, bug: BaseException) -> typing.Iterable[dict]:
        _, is_instance = _isBug(bug)
        waiting_triggers = tuple(reversed(self.AWAITING))
        for trigger in waiting_triggers:
            if _compare(trigger, bug, matchMessage=True):
                function, args, kwargs = self.AWAITING.pop(trigger)
                yield dict(
                    trigger=trigger,
                    function=_makeRepr(function, *args, **kwargs),
                    result=function(*args, **kwargs)
                )

    def __init__(
        self,
        bug: Exception = None,
        skip=False,
        drown=False
    ):
        if not skip:
            _make_data_structure(self)
        bug = bug or HandledBug(
            f'index={self.__dict__.get("index", _get_db_index())}'
        )
        is_exception, is_instance = _isBug(
            bug,
            throw=False
        )
        if is_exception:
            if not is_instance:
                bug = bug('...')
            else:
                if not bug.args:
                    bug.args = '...',
        else:
            bug = HandledBug(bug)
        self.err = bug
        if not skip:
            self.logger(f"{self.err!r}")
        if drown:
            self.drown(self.err)
        super().__init__(bug.args[0])

    def willDrown(self, bug: BaseException):
        """
        Return true is error matches drowned triggers
        else false
        """
        for trigger in self.DROWN:
            try:
                if _compare(trigger, bug, matchMessage=True):
                    return True
            except TypeError:
                pass
        return False

    def drown(self, bug: BaseException):
        bugs = tuple(_flatten_(bug))
        # print(f'drowning {" & ".join(str(x) for x in bugs)}')
        for x in bugs:
            self.DROWN.add(x)

    @property
    def on(self):
        return ON(self)

    def reraise(self):
        raise ReRaised(repr(self.err)) from self.err

    def _capture(
        self,
        bug: BaseException,
        drown=True,
        append=True,
    ):
        caught = False
        for trigger in self.DROWN:
            if _compare(trigger, bug, matchMessage=True):
                caught = True
                if drown:
                    self.DROWNED.add(trigger)
                break
        if append:
            self.dataframe = self.dataframe.append(
                dict(
                    bug=self.__class__(bug),
                    type=HandledBug if caught else UnExpectedBug,
                    caught=caught,
                    trigger=None if not caught else trigger
                ),
                ignore_index=True
            )
        return caught

    def invoke(self, bug, loop=None):
        if not loop:
            result = []
            for fn in self._invokeAwaiting(bug):
                self.logger(INVOKE.format(fn=fn))
                result.append(fn)
                self.INVOKED[fn['trigger']] = fn
            return result
        gen = self._invokeAwaiting(bug)
        result = []
        for i in range(int(loop)):
            try:
                fn = next(gen)
                self.logger(INVOKE.format(fn=fn))
                result.append(fn)
                self.INVOKED.add(fn)
            except StopIteration:
                pass
        return result

    def throwIf(self, bug, drown=True, append=True):
        if self.willDrown(bug):
            self._capture(bug, drown=drown, append=append)
            self.reraise()

    def throwIfNot(self, bug, drown=True, append=True):
        if not self.willDrown(bug):
            self._capture(bug, drown=drown, append=append)
            self.reraise()

    def __enter__(self):
        return self

    def __exit__(self, bug_type, bug, trace):
        # breakpoint()
        try:
            self.invoke(bug)
        except TypeError:
            pass
        try:
            self.throwIfNot(bug)
        except TypeError:
            pass
        return True


def Expect(bug: typing.Iterable[BaseException]):
    _isBug(bug, throw=False)
    this = Bug(HandledBug, skip=False, drown=False)
    this.drown(bug)
    return this


def Bind(
    bug: BaseException,
    handler,
    *args,
    is_method=True,
    **kwargs
):
    def wrapper(fn):
        function = type(_get_db_index)
        method = type(Bug(skip=True, drown=False).drown)
        if isinstance(fn, function):
            @wraps(fn)
            def inner(*a, **k):
                inner.bug = Bug(fn.__name__)
                inner.bug.on[bug, handler:args:kwargs]
                inner.bug.drown(bug)
                with inner.bug:
                    return fn(*a, **k)
        elif isinstance(fn, method):
            @wraps(fn)
            def inner(self, *a, **k):
                inner.bug = Bug(fn.__name__)
                inner.bug.on[bug, handler:args:kwargs]
                inner.bug.drown(bug)
                with inner.bug:
                    return fn(self, *a, **k)
        return inner
    return wrapper
