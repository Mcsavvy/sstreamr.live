import typing
import re
from _vars import *
from collections import OrderedDict, namedtuple


class HandledBug(Exception):
    """
    The base exception class for all handled bugs
    """


class DrownedBug(HandledBug):
    """
    The base exception class for all drowned bugs
    """


class UnExpectedBug(Exception):
    """
    The base exception class for all unexpected errors
    """


class AnonymousError(HandledBug):
    """
    UnNamed Errors
    """


class ReRaised(Exception):
    "For exceptions that are reraised"


def _makeRepr(function, *position_arguments, **keyword_arguments):
    if not callable(function):
        return
    name = function.__name__ if hasattr(
        function,
        '__name__'
    ) else function.__class__
    args = ', '.join(f"{x!r}" for x in position_arguments) + (
        (', ' if position_arguments else '') if keyword_arguments else ''
    )
    kwargs = ', '.join(
        f"{x}={keyword_arguments[x]!r}" for x in keyword_arguments
    )
    return f"{name}({args}{kwargs})"


def _isBug(
    bug: BaseException, throw=True
) -> tuple((bool, bool)):
    is_exception = False
    is_instance = True
    if not isinstance(bug, BaseException):
        if isinstance(bug, type):
            if issubclass(bug, BaseException):
                is_exception = True
                is_instance = False
    else:
        is_exception = True
    if not is_exception and throw:
        raise TypeError(
            'bug must be an instance or subclass of BaseException.'
        )
    return is_exception, is_instance


def _flatten_(
    o: typing.Union[
        Exception,
        typing.Iterable[Exception],
        typing.Callable
    ]
):
    is_bug, _ = _isBug(o, throw=False)
    if isinstance(o, str) and bool(o):
        yield o
    elif isinstance(
        o, (tuple, set, list)
    ):
        for i in o:
            yield from _flatten_(i)
    elif is_bug:
        yield o


class ON:
    def __init__(self, this):
        self.this = this

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            raise SyntaxError(
                'Not enough arguments. '
                'Syntax -> on[Exc, func:(*args):{**kwargs}].'
            )
        bugs = tuple(_flatten_(key[0]))
        if not bugs:
            raise ValueError(
                'arg 0 must be an exception, '
                'a str pattern or an iterable of (either|both).'
            )
        if not isinstance(key[1], slice):
            if callable(key[1]):
                key = key[0], slice(key[1])
            else:
                raise ValueError(
                    'arg 1 must be an slice, '
                    'Syntax -> function:(*args):{**kwargs}'
                )
        if callable(key[1].start):
            if not isinstance(
                key[1].stop, (
                    type(None),
                    tuple,
                    list,
                    set
                )
            ):
                raise ValueError(
                    'arg 1 second argument must be an iterable or None. '
                )
            if not isinstance(key[1].step, (dict, type(None))):
                raise ValueError(
                    'arg 1 third argument must be a dict. '
                )
        elif callable(key[1].stop):
            if any((key[1].start, key[1].step)):
                raise TypeError(
                    "arg 1 second argument was interpreted as a standalone"
                    " function, no arguments were expected"
                )
        else:
            raise ValueError(
                'arg 1 first argument must be a callable. '
            )

        self.this._await_(bugs, key[1])
        return self.this

    def __call__(
        self,
        bug: Exception,
        function,
        *args,
        **kwargs,
    ):
        return self[bug, slice(function, args, kwargs)]


def _compare(
    trigger: BaseException,
    bug: BaseException = BaseException,
    matchMessage: bool = False
):
    bug_is_exception, _ = _isBug(bug, throw=True)
    trigger_is_exception, _ = _isBug(
        trigger,
        throw=False
    )

    def match_exc_exc(e1, e2):
        _, e1_isinstance = _isBug(e1)
        _, e2_isinstance = _isBug(e2)
        if e1_isinstance:
            if e2_isinstance:
                # check to see if they are of the same type
                same_type = isinstance(e1, e2.__class__)
                both_have_message = all(
                    getattr(e, 'args') for e in (e1, e2)
                )
                if same_type:
                    if matchMessage:
                        if both_have_message and re.search(
                            str(e1.args[0]), str(e2.args[0])
                        ):
                            return True
                    else:
                        return True
                else:
                    if matchMessage:
                        if both_have_message and re.search(
                            str(e1.args[0]), str(e2.args[0])
                        ):
                            return True
                return False
            else:
                return isinstance(e1, e2) or (bool(
                    re.search(
                        (str(e1) if str(e1) else repr(e1)),
                        (str(e2) if str(e2) else repr(e2))
                    )
                ) if matchMessage else False)
        else:
            if e2_isinstance:
                return issubclass(e1, e2.__class__) or (bool(
                    re.search(
                        (str(e1) if str(e1) else repr(e1)),
                        (str(e2) if str(e2) else repr(e2))
                    )
                ) if matchMessage else False)
            else:
                return issubclass(e1, e2) or (bool(
                    re.search(
                        (str(e1) if str(e1) else repr(e1)),
                        (str(e2) if str(e2) else repr(e2))
                    )
                ) if matchMessage else False)
        return False

    def match_str_exc(pat, e):
        _, e_isinstance = _isBug(e)
        if e_isinstance:
            if str(e):
                return bool(re.search(pat, str(e)))
            else:
                return bool(re.search(pat, f'{e!r}'))
        else:
            return bool(re.search(pat, f'{e!r}'))
        return False

    def match_exc_str(e, pat):
        return False

    def match_str_str(pat1, pat2):
        if matchMessage:
            pass
        return False

    if bug_is_exception:
        if trigger_is_exception:
            return match_exc_exc(trigger, bug)
        return match_str_exc(trigger, bug)
    else:
        if trigger_is_exception:
            return match_exc_str(trigger, bug)
        return match_str_str(trigger, bug)


def _parseSlice(slice_: slice):
    try:
        if not isinstance(slice_, slice):
            if isinstance(slice_, typing.Callable):
                _callback, _args, _kwargs = slice_, tuple(), dict()
            else:
                raise TypeError(
                    f"Expected a callable but got [{type(slice_)}]"
                )
        else:
            if isinstance(slice_.start, typing.Callable):
                _callback = slice_.start
            elif isinstance(slice_.stop, typing.Callable):
                return slice_.stop, tuple(), dict()
            else:
                raise TypeError(
                    "slice expected a callable as "
                    f"first argument but got [{type(slice_.start)}]"
                )
            if isinstance(slice_.stop, typing.Iterable):
                _args = tuple(slice_.stop)
            elif slice_.stop is None:
                _args = tuple()
            else:
                raise TypeError(
                    "slice expected a Sequence as "
                    f"second argument but got [{type(slice_.stop)}]"
                )
            if isinstance(slice_.step, dict):
                _kwargs = slice_.step
            elif slice_.step is None:
                _kwargs = dict()
            else:
                raise TypeError(
                    "slice expected None|dict as "
                    f"last argument but got [{type(slice_.step)}]"
                )
    except TypeError as e:
        raise e from SyntaxError(PARSE_SLICE_SYNTAX)
    return _callback, _args, _kwargs


class __parseBugs__:
    def __init__(
        self,
        bugs: typing.Union[BaseException, typing.Iterable[BaseException]]
    ):
        self._bugs = OrderedDict()
        self._disperse(bugs)

    @property
    def bug(self):
        return self._compress(getattr(self, '_bugs', tuple()))

    def _disperse(self, bugz):
        collect = namedtuple(
            'Exception',
            ['ERR_NO', 'OBJECT', 'CLASS', 'MESSAGE']
        )
        for index, bug in enumerate(_flatten_(bugz)):
            if not _isBug(bug, throw=False)[0]:
                bug = AnonymousError(bug)
            if not _isBug(bug, throw=False)[1]:
                try:
                    bug = bug()
                    bug.__bug__ = bug
                except Exception as e:
                    bug = UnExpectedBug()
                    bug.__name__ = e.__name__
                    bug.__bug__ = e
            if not isinstance(getattr(bug, 'args') or None, tuple):
                bug.args = (
                    str(bug) or getattr(
                        bug, '__name__',
                        repr(bug).strip('()')
                    )
                )
            bug.message = bug.args[0]
            bug.err_no = f'{self.index}'.zfill(3)
            self._bugs[bug] = collect(
                bug.err_no,
                bug,
                bug.__bug__.__class__,
                bug.message
            )

    def _compress(self, bugs):
        return bugs



