from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Hotel
from django.contrib.auth import get_user_model

class HotelAdminSignupForm(UserCreationForm):
    # hotel fields bundled into signup
    hotel_name = forms.CharField(max_length=150, label="Hotel name")
    city = forms.CharField(max_length=80, required=False)
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False, help_text="Hotel contact email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)  # we’ll capture username; email is hotel email here

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "HOTEL_ADMIN"
        # create hotel
        hotel = Hotel.objects.create(
            name=self.cleaned_data["hotel_name"],
            city=self.cleaned_data.get("city", ""),
            phone=self.cleaned_data.get("phone", ""),
            email=self.cleaned_data.get("email", ""),
            status="ACTIVE",
        )
        user.hotel = hotel
        if commit:
            user.save()
        return user






User = get_user_model()

class StaffCreateForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")  # password1/password2 come from UserCreationForm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "STAFF"  # hotel will be set in the view for safety
        if commit:
            user.save()
        return user
