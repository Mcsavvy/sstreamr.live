import unittest
from exceptions import (
    Bug, _get_db_index,
    _compare, _isBug,
    _makeRepr, _flatten_,
    ON, _parseSlice, HandledBug, ReRaised,
    Bind, Expect
)


class _UtilsTest(unittest.TestCase):
    def setUp(self):
        pass

    def testIsBug(self):
        self.assertFalse(_isBug('An exception', throw=False)[0])
        self.assertTrue(
            _isBug(BaseException)[0]
        )
        self.assertTrue(
            _isBug(BaseException())[0]
        )
        self.assertTrue(
            _isBug(BaseException())[1]
        )
        self.assertFalse(
            _isBug(BaseException)[1]
        )
        self.assertRaises(
            TypeError,
            _isBug,
            'BaseException'
        )

    def testMakeRepr(self):
        self.assertEqual(
            _makeRepr(print, 'Hello', 'World!', sep=" "),
            "print('Hello', 'World!', sep=' ')",
            'Bad *args, **kwargs formatting'
        )
        self.assertEqual(
            _makeRepr(print, 'Hello', 'World!'),
            "print('Hello', 'World!')",
            'Bad *args formatting'
        )
        self.assertEqual(
            _makeRepr(print, sep=":"),
            "print(sep=':')",
            'Bad **kwargs formatting'
        )

    def testParseSlice(self):
        self.assertEqual(
            _parseSlice(print),
            (print, tuple(), dict()),
            'Cannot parse Callback[Callable]'
        )
        self.assertEqual(
            _parseSlice(slice(print)),
            (print, tuple(), dict()),
            'Cannot parse Callback[Callable]:'
        )
        self.assertEqual(
            _parseSlice(slice(print, ('Hello', 'World!'))),
            (print, ('Hello', 'World!'), dict()),
            'Cannot parse Callback[...]:Args[Iterable]'
        )
        self.assertEqual(
            _parseSlice(slice(print, None, {'sep': ' '})),
            (print, tuple(), {'sep': ' '}),
            'Cannot parse Callback[...]::Kwargs[dict]'
        )
        self.assertEqual(
            _parseSlice(slice(print, ('Hello', 'World!'), {'sep': ' '})),
            (print, ('Hello', 'World!'), {'sep': ' '}),
            'Cannot parse Callback[...]:Args[...]:Kwargs[...]'
        )

    def testFlatten(self):
        self.assertEqual(
            tuple(_flatten_(Exception)),
            (Exception,),
            'Could not flatten single object'
        )
        self.assertEqual(
            tuple(_flatten_('Exception')),
            ('Exception',),
            'Could not flatten single string object'
        )
        self.assertEqual(
            tuple(_flatten_([Exception, 'ThisToo'])),
            (Exception, 'ThisToo'),
            'Could not parse str object'
        )
        self.assertEqual(
            tuple(_flatten_([Exception, 'ThisToo', 1234, dict, bool, object])),
            (Exception, 'ThisToo'),
            'Parsed :not(Exception, str)'
        )

    def testCompare(self):
        '''
        I make the assumtions that the following are true

        * the trigger is compared to the bug
        * the trigger can be a regex pat, str or another Exception
        '''

        """
        A regex trigger with match an exception or it's message

        """
        self.assertTrue(_compare('.*', Exception))
        self.assertTrue(_compare('[Me]{2}s{2}...', Exception('Message')))
        self.assertTrue(_compare('Except', Exception))
        self.assertTrue(_compare('Message', Exception('thisMessage')))

        """
        Two exceptions of different types will never match even if their
        messages matches
        """
        self.assertFalse(_compare(SyntaxError('FOO'), TypeError('FOO')))
        self.assertFalse(_compare(SyntaxError('.*'), TypeError('FOO')))
        # except you explicitly declared matchMessage=True
        self.assertTrue(_compare(SyntaxError('FOO'),
                                 TypeError('FOO'), matchMessage=True))
        self.assertTrue(_compare(SyntaxError('.*'),
                                 TypeError('FOO'), matchMessage=True))

        """
        Two exceptions would always match as long as the first
        is a subclass or instance of the second
        """
        self.assertTrue(
            _compare(TypeError('invalid type'), Exception('generic')))
        self.assertTrue(_compare(TypeError(), Exception))
        self.assertTrue(_compare(TypeError(), Exception()))
        self.assertTrue(_compare(TypeError, Exception()))
        self.assertTrue(_compare(TypeError, TypeError))
        #  except you explicitly declared matchMessage=True
        self.assertFalse(_compare(
            SyntaxError('invalid syntax at a'),
            SyntaxError('invalid syntax at b'),
            matchMessage=True
        ))
        self.assertFalse(_compare(
            SyntaxError('invalid syntax'),
            Exception('generic'),
            matchMessage=True
        ))

        """
        A TypeError would be raised if the second argument is not
        a subclass or instance of BaseException
        """
        self.assertRaises(TypeError, _compare, TypeError(), '.*')
        self.assertRaises(TypeError, _compare, '.*', '.*')

    def testON(self):
        bug = Bug(Exception, skip=False, drown=False)
        on = ON(bug)
        on[Exception, print]
        on[TypeError, print:]
        on(SyntaxError, print, 'Hello', 'World!')
        on(ValueError, print, sep=" ")
        on(NameError, print, 'Hello', 'World!', sep=" ")
        self.assertEqual(
            bug.AWAITING[Exception],
            _parseSlice(slice(print)),
            "Cannot parse Exception, Callback[Callable]"
        )
        self.assertEqual(
            bug.AWAITING[TypeError],
            _parseSlice(slice(print)),
            "Cannot parse Exception, Callback[Callable]:"
        )
        self.assertEqual(
            bug.AWAITING[SyntaxError],
            _parseSlice(slice(print, ('Hello', 'World!'))),
            "Cannot parse Exception, Callback[...]:Args[Iterable]"
        )
        self.assertEqual(
            bug.AWAITING[ValueError],
            _parseSlice(slice(print, tuple(), {'sep': ' '})),
            "Cannot parse Exception, Callback[...]::Kwargs[dict]"
        )
        self.assertEqual(
            bug.AWAITING[NameError],
            _parseSlice(slice(print, ('Hello', 'World!'), {'sep': ' '})),
            "Cannot parse Exception, Callback[...]::Kwargs[dict]"
        )


class BugTest(unittest.TestCase):
    def setUp(self):
        self.bug = Bug(Exception, skip=False, drown=False)

    def testIndex(self):
        self.assertEqual(
            self.bug.index,
            _get_db_index() - 1,
            'Bug\'s indexing is wrong.'
        )

    def test__init__(self):
        skipped_bug = Bug(Exception, skip=True, drown=False)
        self.assertFalse(
            hasattr(skipped_bug, 'index')
        )
        drowned_bug = Bug('Drowned', skip=False, drown=True)
        self.assertTrue(_compare(
            "Drowned",
            tuple(drowned_bug.DROWN)[0]
        ))
        self.assertRaises(
            AttributeError,
            Bug,
            Exception,
            skip=True,
            drown=True
        )

    def testInvokeAwaiting(self):
        def test_fn():
            return 'works!'
        self.bug.on('test invoke', test_fn)
        self.assertEqual(
            tuple(self.bug._invokeAwaiting(Exception('test invoke'))),
            (dict(
                trigger='test invoke',
                function="test_fn()",
                result="works!"
            ),),
            "Not yielding invoked correctly"
        )

    def testWillDrown(self):
        '''
        promises to truthfully tell you if an exception would be drowned
        on encounter
        '''
        self.bug.drown('incorrect')
        self.assertTrue(self.bug.willDrown(ValueError('incorrect')))
        self.bug.drown(KeyError('key not found'))
        self.assertTrue(self.bug.willDrown(KeyError))
        self.assertFalse(self.bug.willDrown(KeyError('val not found')))

    def testReraise(self):
        self.assertRaises(ReRaised, self.bug.reraise)

    def testCapture(self):
        mock = Exception('CapturedException')
        self.bug.drown(mock)
        self.assertTrue(self.bug._capture(
            FileExistsError('CapturedException'),
            drown=True, append=False
        ))

        self.assertIn(mock, self.bug.DROWNED)

    def testThrowIf(self):
        '''
        Tests all triggers against a supplied exception
        if any trigger goes off:
            throwIf(exc): reraises Exception
            throwIfNot(exc): does nothing
        if none goes off:
            throwIf(exc): does nothing
            throwIfNot(exc): reraises Exception
        '''
        self.bug.DROWN = set()
        # Add a regex/str trigger
        self.bug.drown('NameError')
        # NameError is triggered so reraised
        self.assertRaises(
            ReRaised,
            self.bug.throwIf,
            NameError
        )
        # NameError is triggered so nothing happens
        self.bug.throwIfNot(NameError)

        self.bug.drown('.*')  # match all exceptions
        self.assertRaises(
            ReRaised,
            self.bug.throwIf,
            SyntaxError
        )
        self.bug.throwIfNot(BaseException)

    def testBind(self):
        def foo_callback():
            print(
                "I was called because a TypeError was raised"
            )

        def bar_callback():
            print(
                "I was called because a ValueError was raised"
            )

        @Bind(ZeroDivisionError, foo_callback)
        def foo(div):
            return 100 / div

        class bar:
            @Bind(ValueError, bar_callback, is_method=True)
            def __init__(self):
                raise KeyError
        self.assertRaises(ReRaised, foo, 'div')
        foo(0)  # silences the ZeroDivisionError
        self.assertRaises(ReRaised, bar)

    def testExpect(self):
        with Expect((ValueError, TypeError)) as bug:
            print(bug.DROWN)
            raise ValueError
        with bug:
            raise TypeError

        def do_something():
            print('Did something')
            raise SyntaxError

        bug.on[SyntaxError, print:['An error occurred']]
        with bug:
            bug.drown(SyntaxError)
            do_something()


if __name__ == '__main__':
    unittest.main()
