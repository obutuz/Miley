from django.core.serializers import serialize
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
import logging
from .forms import SignupForm, LoginForm
from .models import Contact, Profile
from activities.models import Activity
from videos.models import Video
import json
from activities.utils import create_activity
from shop.models import Product

def user_signup(request):
    logger = logging.getLogger(__name__)
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                user = User.objects.create_user(cd['username'], cd['email'], cd['password'])
                profile = Profile(profile_type=cd['profile_type'], user=user)
                if profile is not None:
                    logger.info('New user profile was signed up successfully: {}, {}'.format(profile.id, user.email))
                    return redirect('login')
            except Exception as e:
                logger.error('Error signing up: {}'.format(e))
            return HttpResponse('Error signing up')
        else:
            logger.error('Invalid form')
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(username=cd['username'], password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))

@login_required
def home_feed(request):
    videos = Video.objects.all()
    profiles = Profile.objects.exclude(user=request.user)
    activities = Activity.objects.all().exclude(user=request.user)
    following_ids = request.user.following.values_list('id', flat=True)
    if following_ids:
        activities = activities.filter(user_id__in=following_ids).select_related('user', 'user__profile').prefetch_related('target')
    activities = activities[:10]

    activities = Activity.objects.all()
    return render(request, 'accounts/home_feed.html', {'section': 'dashboard',
        'activities': activities, 'videos': videos, 'profiles': profiles})

@login_required
def user_list(request):
    users = Profile.active_user_list(request.user)
    return render(request, 'users/list.html',
        {'section': 'people',
        'users': users})

def user_list_json(request):
    users = User.objects.all()
    # return JsonResponse({'users': serialize('json', users)})
    data = list()
    for user in users:
        data.append(dict({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'picture': user.profile.picture.url,
            'type': user.profile.profile_type,
            'birth': user.profile.birth_date,
            'last_login': user.last_login,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined
        }))
    return JsonResponse({'users': data})

@login_required
def user_detail(request, username):
    user = get_object_or_404(User, username=username)
    products = Product.objects.filter(user=user)
    return render(request, 'users/detail.html',
        {'section': 'people',
        'user': user,
        'products': products})

@require_POST
@login_required
def user_follow(request):
    json_data = json.loads(request.body)
    user_id = json_data['id']
    action = json_data['action']
    if user_id and action:
        try:
            user = User.objects.get(id=user_id)
            if action == 'follow':
                Contact.objects.get_or_create(user_from=request.user,
                    user_to=user)
                create_activity(request.user, 'is following', user)
            else:
                Contact.objects.filter(user_from=request.user,
                    user_to=user).delete()

            return JsonResponse({'status': 'ok'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'not found'})

    return JsonResponse({'status': 'error'})

@login_required
def account_settings(request):
    return render(request, 'accounts/settings.html')
