from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from .forms import HotelAdminSignupForm
from django.contrib.auth import logout



def home(request):
    return render(request, "website/home.html")




def signup(request):
    if request.method == "POST":
        form = HotelAdminSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
    else:
        form = HotelAdminSignupForm()
    return render(request, "website/signup.html", {"form": form})

class S2SLoginView(LoginView):
    template_name = "registration/login.html"

class S2SLogoutView(LogoutView):
    pass



def signout(request):
    logout(request)          # clears the session
    return redirect("/login")     # back to login
