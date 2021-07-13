from core import render
from django.views.generic import View
from django.shortcuts import redirect
from core.models import User, Node, nodify
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.core import serializers
from core.decorators import Request
from django.http import JsonResponse

# Create your views here.


class Main(View):
    def ajax(self, request):
        return JsonResponse({
            'message': 'Ajax requests not allowed.',
            'level': 'warning'
        })

    @Request.ajax(False, method=(True, True), view_func=ajax)
    def dispatch(self, *args, **kwargs):
        return super(Main, self).dispatch(*args, **kwargs)

    def get(self, request):
        return render(request, 'auth/main.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        request.session['username'] = username
        request.session['password'] = password
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return redirect('/auth/redirect//auth/join')
        nodify(user)
        if authenticate(request, username=username, password=password):
            request.session['user'] = serializers.serialize(
                "json", [user]
            )
            return redirect('/auth/redirect//auth/login')
        else:
            messages.error(request, 'Try again..??title=Invalid Credentials')
            return self.authentify(request, redirect('auth.main'))
        return render(request, 'auth/main.html')

    def authentify(self, request, response):
        if 'retries' not in request.session:
            request.session['retries'] = 0

        request.session['retries'] += 1
        if request.session['retries'] in [3, 5]:
            messages.info(
                request,
                'We can\'t seem to find your account.??title=Oops'
            )
        elif request.session['retries'] in [4, 6]:
            messages.info(
                request,
                'try recovering your account.??title=Why not..'
            )
        elif request.session['retries'] in [2, 8]:
            messages.info(
                request,
                'try to type more slowly.??title=We suggest you..'
            )
        elif request.session['retries'] >= 10:
            messages.info(
                request,
                'Try to type more slowly.??title=We suggest you..'
            )
            return redirect('/auth/redirect//auth')
        return response


class Create(View):
    @Request.ajax(False, method=(True, True))
    def get(self, request):
        if not request.session.get('username'):
            return redirect('/auth/redirect//auth')
        context = {
            'h1': 'Welcome streamr...',
            'h2': 'your account setup is nearly complete',
            'h3': 'confirm your password and email address...'
        }
        return render(request, 'auth/create.html', context=context)

    @Request.ajax(False, method=(True, True))
    def post(self, request):
        if request.session['password'] != request.POST['password']:
            messages.error(request, 'passwords don\'t match.')
            return redirect('/auth/redirect//auth/join')
        try:
            user = User.objects.get(
                username=request.session['username']
            )
            messages.warning(
                request,
                f'that username is no longer available.??title=Yo!'
            )
            del request.session['username']
            del request.session['password']
            return redirect('/auth/redirect//auth/join')
        except User.DoesNotExist:
            user = User.objects.create(
                username=request.session['username'],
                email=request.POST['email']
            )
            user.set_password(request.POST['password'])
            nodify(user)
            messages.success(
                request,
                f'{user.username}, you are now one of our streamrs.??title=YaY!'
            )
            messages.info(
                request,
                f'We\'ll be with you shortly.??title=take your time'
            )
            login(request, user)
            del request.session['username']
            del request.session['password']
            return redirect('/auth/redirect///')


class Login(View):
    @Request.ajax(False, method=(True, True))
    def get(self, request):
        if not request.session.get('username'):
            return redirect('/auth/redirect//auth')
        username, password = request.session['username'],\
            request.session['password']
        if not (username and password):
            messages.error(request, 'An error occurred!??It\'s on us.')
            del request.session['username']
            del request.session['password']
            return redirect('/auth/redirect//auth')
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if not user:
            messages.error(
                request,
                'we could not validate your credentials.??title=Sorry'
            )
            del request.session['username']
            del request.session['password']
            return redirect('/auth/redirect//auth')
        login(request, user)
        messages.info(
            request,
            f'let us show you what you missed..??title=Welcome back {username}!'
        )
        return redirect('/auth/redirect///')


class Redirect(View):
    def non_ajax_post(self, request, *args, **kwargs):
        return JsonResponse({
            'message': 'Message could not be understood',
            'level': 'error'
        })

    def do_redirect(self, request, *args, **kwargs):
        print(args, kwargs, sep="??")
        return JsonResponse({
            'url': kwargs['path']
        })

    @Request.on('do:redirect', do_redirect, method=(True, True))
    def get(self, request, path):
        print(request.headers)
        return render(request, 'auth/redirect.html')

    @Request.ajax(True, method=(True, True), view_func=non_ajax_post)
    def post(self, request):
        pass
