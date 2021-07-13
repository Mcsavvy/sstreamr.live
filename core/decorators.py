from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect
from . import render, error
from .utils import Attr, arg_parser
from .models import User
from .random_fields import Random
from .caching import CachedObject, dbcache
import typing


def test():
    print("works")


def allowed_user(
        allowed_roles: typing.Iterable = [],
        method: bool = False
):
    """
    Restrict user by groups

    args(method):
        specify true if you are decorating a method.
    """
    def decorator(view_func):
        context = {
            "suggested": [
                "This page maybe be restricted to a particular group."
            ],
            "name": 403,
            "reason": "Access Denied",
            "info": f"Allowed-Groups ({':'.join(allowed_roles)})"
        }
        if method:
            def wrapper_func(self, request, *args, **kwargs):
                if request.user.groups.exists():
                    for grp in request.user.groups.all():
                        if grp.name in allowed_roles:
                            return view_func(self, request, *args, **kwargs)
                return error(request, context)
        else:
            def wrapper_func(request, *args, **kwargs):
                if request.user.groups.exists():
                    for grp in request.user.groups.all():
                        if grp.name in allowed_roles:
                            return view_func(request, *args, **kwargs)
                return error(request, context)
        return wrapper_func
    return decorator


def login_required(
        login_url: typing.AnyStr,
        method: bool = False
):
    """
    Restrict view to logged in users

    args(method):
        specify true if you are decorating a method.
    """
    def decorator(view_func):
        if method:
            def wrapper_func(self, request, *args, **kwargs):
                if request.user.is_authenticated:
                    return view_func(self, request, *args, **kwargs)
                return redirect(login_url)
        else:
            def wrapper_func(request, *args, **kwargs):
                if request.user.is_authenticated:
                    return view_func(request, *args, **kwargs)
                return redirect(login_url)
        return wrapper_func
    return decorator


class Request:
    @staticmethod
    def _capture_event(
        request: HttpRequest,
        event_name: str,
        callback=lambda *args, **kwargs: (args, kwargs),
    ):
        print(f'Trying to capture event [{event_name}]')
        if request.headers.get('x-events', request.headers.get('X-Events')):
            args, kwargs = arg_parser(
                request.headers.get(
                    'x-events', request.headers.get('X-Events')
                )
            )
            if event_name in args or event_name in kwargs:
                print('Found in headers.')
                return callback(*args, **kwargs)
        elif event_name.lower() in [
            'post', 'get', 'head', 'put', 'delete'
        ]:
            print('Not found in headers.')
            method = getattr(request, event_name.upper(), {})
            if method:
                print('Found in request methods.')
                return callback(event_name.upper(), **method)
        elif event_name.lower() in ['ajax', 'x-ajax']:
            print('Not found in request methods.')
            if request.isAjax:
                print('Found in isAjax.')
                return callback(
                    'X-AJAX',
                    **{'method': request.method, 'path': request.path}
                )
            print('Not found in isAjax.')
        print('Could not capture event.')
        return False

    @staticmethod
    def on(
        request_event: typing.AnyStr,
        handler_function: typing.Callable[..., HttpRequest],
        method=(True, True)
    ):
        def bind(view_func):
            if method[0]:
                def function(self, request, *args, **kwargs):
                    if Request._capture_event(request, request_event):
                        if method[1]:
                            return handler_function(
                                self,
                                request,
                                *args,
                                **kwargs
                            )
                        return handler_function(
                            request, *args, **kwargs
                        )
                    return view_func(self, request, *args, **kwargs)
            else:
                def function(request, *args, **kwargs):
                    if Request._capture_event(request, request_event):
                        return handler_function(
                            request, *args, **kwargs
                        )
                    return view_func(request, *args, **kwargs)
            return function
        return bind

    @staticmethod
    def fake(
        **options
    ):
        _ = dict(
            path="/",
            user=Random.random(User),
            isAjax=Random.BooleanField(),
            headers={"X-Events": "??event=trigger"}
        )

        options = _ | options

        instance = HttpRequest()
        for k, v in options.items():
            setattr(instance, k, v)
        return instance

    @staticmethod
    def bind(request_event, handler_function):
        cached_obj = CachedObject(
            "request_handlers",
            cache=dbcache,
            version=1,
            timeout=None
        )
        handlers = set(cached_obj.get([]))
        handlers.add((
            request_event,
            handler_function
        ))
        cached_obj.set(list(handlers), timeout=None)
        return cached_obj

    @staticmethod
    def restrict(allowed_methods=("POST", "GET"), method=False):
        def binder(view_func):
            if method:
                def wrapper_func(self, request, *args, **kwargs):
                    context = dict(
                        name="404",
                        reason=f"{request.method} Requests Not Allowed"
                    )
                    if isinstance(allowed_methods, str):
                        if request.method != allowed_methods:
                            return error(request, context)
                    else:
                        if request.method not in allowed_methods:
                            return error(request, context)
                    return view_func(self, request, *args, **kwargs)
            else:
                def wrapper_func(request, *args, **kwargs):
                    context = dict(
                        name="404",
                        reason=f"{request.method} Requests Not Allowed"
                    )
                    if isinstance(allowed_methods, str):
                        if request.method != allowed_methods:
                            return error(request, context)
                    else:
                        if request.method not in allowed_methods:
                            return error(request, context)
                    return view_func(request, *args, **kwargs)
            return wrapper_func
        return binder

    @staticmethod
    def ajax(ajax=False, view_func=None, method=(True, True)):
        """
        set ajax to True if this view only accepts ajax requests
        if a non-ajax request is sent:
            an error is thrown if view_func is None
            else the view_func is called with all arguments
        set ajax to false if this view doesn't accepts ajax request
        if an ajax request is sent:
            an error is thrown if view_func is None
            else the view_func is called with all arguments
        """
        def default_error(request, reason=""):
            context = dict(
                name="404",
                reason=reason or "Ajax Not Allowed Here."
            )
            return error(request, context)

        def binder(view):
            if method[0]:
                def wrapper_func(self, request, *args, **kwargs):
                    if request.isAjax:
                        if ajax is True:
                            return view(
                                self, request, *args, **kwargs
                            )
                        else:
                            if view_func:
                                if method[1]:
                                    return view_func(
                                        self,
                                        request,
                                        *args,
                                        **kwargs
                                    )
                                return view_func(
                                    request, *args, **kwargs
                                )
                            else:
                                return default_error(
                                    request
                                )
                    else:
                        if ajax is False:
                            return view(
                                self,
                                request,
                                *args,
                                **kwargs
                            )
                        else:
                            if view_func:
                                if method[1]:
                                    return view_func(
                                        self,
                                        request,
                                        *args,
                                        **kwargs
                                    )
                                return view_func(
                                    request, *args, **kwargs
                                )
                            else:
                                return default_error(
                                    request,
                                    "Only Ajax Request Allowed Here."
                                )
            else:
                def wrapper_func(request, *args, **kwargs):
                    if request.isAjax:
                        if ajax is True:
                            return view(
                                request,
                                *args,
                                **kwargs
                            )
                        else:
                            if view_func:
                                return view_func(
                                    request,
                                    *args,
                                    **kwargs
                                )
                            else:
                                return default_error(
                                    request
                                )
                    else:
                        if ajax is False:
                            return view(
                                request,
                                *args,
                                **kwargs
                            )
                        else:
                            if view_func:
                                return view_func(
                                    request,
                                    *args,
                                    **kwargs
                                )
                            else:
                                return default_error(
                                    request,
                                    "Only Ajax Request Allowed Here."
                                )
            return wrapper_func
        return binder
