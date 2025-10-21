from django import forms
from .models import Room


from django.core.exceptions import ValidationError  # 4.2A — Catalog forms
from .models import Category, Item, ImageAsset       # 4.2A — Catalog forms

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "floor", "is_active"]













# 4.2A — Catalog forms



class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind", "parent", "position", "is_active"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Limit parent choices to same hotel & same kind
        hotel = getattr(getattr(self.request, "user", None), "hotel", None) if self.request else None
        kind  = self.initial.get("kind") or (self.instance.kind if self.instance.pk else None)
        qs = Category.objects.none()
        if hotel:
            qs = Category.objects.filter(hotel=hotel)
            if kind:
                qs = qs.filter(kind=kind)
        self.fields["parent"].queryset = qs

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.request:  # bind hotel
            obj.hotel = self.request.user.hotel
        # Ensure parent same hotel/kind
        if obj.parent and (obj.parent.hotel_id != obj.hotel_id or obj.parent.kind != obj.kind):
            raise ValidationError("Parent must be same hotel and kind.")
        if commit:
            obj.save()
        return obj


class ItemForm(forms.ModelForm):
    # Choose existing photo OR upload new (we’ll create ImageAsset behind the scenes)
    image_existing = forms.ModelChoiceField(
        queryset=ImageAsset.objects.none(), required=False, label="Choose existing photo"
    )
    image_upload = forms.ImageField(required=False, label="Or upload new photo")

    class Meta:
        model = Item
        fields = ["category", "name", "price", "unit", "description", "is_available", "position"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        hotel = getattr(getattr(self.request, "user", None), "hotel", None) if self.request else None

        if hotel and not self.instance.pk:
            self.instance.hotel = hotel

        # Limit categories to this hotel and active ones
        cat_qs = Category.objects.none()
        img_qs = ImageAsset.objects.none()
        if hotel:
            cat_qs = Category.objects.filter(hotel=hotel, is_active=True)
            img_qs = ImageAsset.objects.filter(hotel=hotel)
        self.fields["category"].queryset = cat_qs
        self.fields["image_existing"].queryset = img_qs

    def clean(self):
        cleaned = super().clean()
        # optional: basic price guard
        if cleaned.get("price") is not None and cleaned["price"] < 0:
            self.add_error("price", "Price cannot be negative.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.request:
            obj.hotel = self.request.user.hotel

        img = self.cleaned_data.get("image_existing")
        upload = self.cleaned_data.get("image_upload")
        if upload:
            # Create an ImageAsset from upload
            name = self.cleaned_data.get("name") or "Item Photo"
            ia = ImageAsset.objects.create(hotel=self.request.user.hotel, name=name, file=upload)
            obj.image = ia
        elif img:
            obj.image = img

        if commit:
            obj.save()
        return obj


