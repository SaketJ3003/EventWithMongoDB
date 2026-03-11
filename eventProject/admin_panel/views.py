from django.shortcuts import render


def dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


def categories(request):
    return render(request, 'admin_panel/categories.html')


def tags(request):
    return render(request, 'admin_panel/tags.html')


def countries(request):
    return render(request, 'admin_panel/countries.html')


def states(request):
    return render(request, 'admin_panel/states.html')


def cities(request):
    return render(request, 'admin_panel/cities.html')


def create_event(request):
    return render(request, 'admin_panel/create_event.html')


def edit_event(request):
    return render(request, 'admin_panel/edit_event.html')
