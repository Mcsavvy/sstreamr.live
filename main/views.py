from core import render
from django.views.generic import View
from django.shortcuts import redirect
from core.models import User, Node, nodify
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.core import serializers
from core.decorators import (
    Request, login_required
)
from django.http import JsonResponse

# Create your views here.


class Main(View):
    @login_required(login_url='auth.main', method=True)
    def get(self, request):
        context = {
            'node': request.user.node
        }
        return render(request, 'main/landing.html', context)
