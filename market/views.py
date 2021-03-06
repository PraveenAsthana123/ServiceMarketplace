from django.db.models import Avg
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template.context_processors import csrf
from django.contrib import auth, messages
from django.contrib.auth.models import User, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, render_to_response, get_object_or_404
from market.models import Service, Bid, Review
from market.forms import MyRegistrationForm, ServiceForm, ReviewForm
from market.functions import is_owner, get_avg_rating, paginate, add_permission
from datetime import datetime




####### Home #######

def home(request):
    return render(request, 'market/home.html')


####### About #######
def about(request):
    return render(request, 'market/about.html')


####### Login authorization #######
def login(request):
    c = {}
    c.update(csrf(request))

    # check if error message exists
    site_messages = messages.get_messages(request)
    for message in site_messages:
        if message.tags == 'error':
            c['error'] = message.message

    # Get redirextion url if redirect to this page
    redirect_url = request.GET.get('next', False)
    if redirect_url:
        messages.info(request, redirect_url)

    return render_to_response('market/login.html', c)


def auth_view(request):
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    user = auth.authenticate(username=username, password=password)

    site_messages = messages.get_messages(request)

    if user is not None:
        auth.login(request, user)

        # Redirect to redirected from url
        for message in site_messages:
            return HttpResponseRedirect(message.message)

        return HttpResponseRedirect('/browse/')
    else:
        messages.error(request, "Invalid username or password")
        return HttpResponseRedirect('/accounts/login/')


@login_required()
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')


def register_user(request):
    args = {}
    args.update(csrf(request))
    args['form'] = MyRegistrationForm()
    if request.method == "POST":  # Occurs after user submits info
        form = MyRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/accounts/register_success/')
        else:
            args['errors'] = form.errors
            print(args['errors'])
            args['form'] = form

    return render(request, 'market/register.html', args)


def register_success(request):
    return render_to_response('market/register_success.html')





####### Services #######

@login_required
def service_create(request):
    args = {}
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.client = request.user
            service.save()
            return HttpResponseRedirect('/service/' + str(service.pk))
    else:
        form = ServiceForm()

    args.update(csrf(request))
    args['form'] = form
    args['action'] = "Create"
    return render(request, 'market/service_action.html', args)


def service_detail(request, pk):
    args = {}
    service = get_object_or_404(Service, pk=pk)
    args['service'] = service
    args['is_owner'] = is_owner(request=request, service=service)

    if service.is_open:
        args['is_open'] = True
    else:
        args['is_open'] = False

    return render(request, 'market/service_detail.html', args)


@login_required
def service_close(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_open = False
    service.save()
    return HttpResponseRedirect('/my_account/')


@login_required
def service_update(request, pk):
    args = {}
    service = get_object_or_404(Service, pk=pk)
    form = ServiceForm(request.POST or None, instance=service)
    if request.method == "POST":
        if form.is_valid():
            service = form.save(commit=False)
            service.save()
            return HttpResponseRedirect('/service/' + pk)

    args.update(csrf(request))
    args['form'] = form
    args['action'] = "Update"
    return render(request, 'market/service_action.html', args)


@login_required
def service_end(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_open = False
    now = datetime.now()
    service.final_time = now
    service.service_provider = request.user
    service.save()
    return HttpResponse("Service Ended")


# Give permission to review once bid
def bidded(request):
    username = request.GET.get('username')
    add_permission(username, 'can_add_review')
    return HttpResponse(username + " bidded")


def bid(request):
    service = get_object_or_404(Service, pk=request.GET['pk'])
    bid = Bid(bid=request.GET['bid'], service=service,
              service_provider=request.user)
    print(request.GET['bid'])
    bid.save()

    return HttpResponse("Added Bid")




####### Reviews #######

@login_required
@permission_required('market.can_add_review', raise_exception=True)  # if permision denied, user will be redirected to 403 (HTTP Forbidden) view
def add_review(request, username):
    user = User.objects.get(username=username)
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = user
            review.rating = form.cleaned_data['rating']
            review.account_type = form.cleaned_data['account_type']
            review.author = request.user
            review.comment = form.cleaned_data['comment']
            review.save()
            return HttpResponseRedirect(reverse('user_profile', args=(username,)))
    else:
        form = ReviewForm()
    return render(request, 'market/add_review.html', {'form': form, 'user': user})





####### MyAccount + Users profiles #######

@login_required
def my_account(request):
    avg_rating_c = get_avg_rating(username=request.user, mode='client')
    avg_rating_p = get_avg_rating(username=request.user, mode='provider')

    reviews = Review.objects.filter(user=request.user).order_by('-created_date')
    reviews_clients = reviews.filter(account_type='client')[:2]
    reviews_providers = reviews.filter(account_type='provider')[:2]

    services_open = Service.objects.filter(client=request.user, is_open=True).order_by('-created_date')[:3]
    services_closed = Service.objects.filter(client=request.user, is_open=False).order_by('-created_date')[:3]

    return render(
        request,
        'market/my_account.html', {
            'avg_rating_clients': avg_rating_c,
            'avg_rating_providers': avg_rating_p,
            'reviews_clients': reviews_clients,
            'reviews_providers': reviews_providers,
            'services_open': services_open,
            'services_closed': services_closed
        }
    )

@login_required
def more_reviews(request):
    avg_rating_c = get_avg_rating(username=request.user, mode='client')
    avg_rating_p = get_avg_rating(username=request.user, mode='provider')

    reviews = Review.objects.filter(user=request.user).order_by('-created_date')
    reviews_clients = reviews.filter(account_type='client')
    reviews_providers = reviews.filter(account_type='provider')

    return render(
        request,
        'market/reviews.html', {
            'avg_rating_clients': avg_rating_c,
            'avg_rating_providers': avg_rating_p,
            'reviews_clients': reviews_clients,
            'reviews_providers': reviews_providers,
        }
    )

@login_required
def more_services(request):
    services_open = Service.objects.filter(client=request.user, is_open=True).order_by('-created_date')
    services_closed = Service.objects.filter(client=request.user, is_open=False).order_by('-created_date')

    return render(
        request,
        'market/services.html', {
            'services_open': services_open,
            'services_closed': services_closed
        }
    )


def user_profile(request, username):
    user = User.objects.get(username=username)

    # redirect to user's my_account if s(he)'s vising his/her profile
    if request.user == user:
        return HttpResponseRedirect('/my_account/')

    owner = is_owner(request=request, username=username)

    avg_rating_c = get_avg_rating(username=user, mode='client')
    avg_rating_p = get_avg_rating(username=user, mode='provider')

    reviews = Review.objects.filter(user=user).order_by('-created_date')
    reviews_clients = reviews.filter(account_type='client')
    reviews_providers = reviews.filter(account_type='provider')

    return render(
        request,
        'market/user_profile.html', {
            'user': user,
            'avg_rating_clients': avg_rating_c,
            'avg_rating_providers': avg_rating_p,
            'reviews_clients': reviews_clients,
            'reviews_providers': reviews_providers,
            'is_owner': owner,
        }
    )





####### Search + Browse view #######

def search(request):
    query = request.GET.get('q')
    if query:
        # user entered query
        results_list = (Service.objects.filter(title__contains=query) |  \
                        Service.objects.filter(description__contains=query)).order_by('-created_date')
    else:
        # user did not enter query. return all results
        results_list = Service.objects.all().order_by('-created_date')

    services = paginate(request, results_list, 9)   # Show 9 results per page

    return render(request, 'market/search_result.html', {"services": services})


def browse(request):
    results_list = Service.objects.all().order_by('-created_date')
    services = paginate(request, results_list, 9)
    return render(request, 'market/search_result.html', {'services': services})
