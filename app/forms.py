from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q


class InstructorProfileForm(forms.Form):
    full_name = forms.CharField(
        label="Họ và tên",
        max_length=150,
        error_messages={"required": "Vui lòng nhập họ và tên."},
    )
    email = forms.EmailField(
        label="Email",
        max_length=150,
        error_messages={
            "required": "Vui lòng nhập email.",
            "invalid": "Email không hợp lệ.",
        },
    )
    bio = forms.CharField(
        label="Giới thiệu",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    avatar = forms.ImageField(
        label="Ảnh đại diện",
        required=False,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control rounded-3"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        user_model = get_user_model()
        other_accounts = user_model.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email),
        ).exclude(pk=self.user.pk)
        if other_accounts.exists():
            raise forms.ValidationError("Email này đã được tài khoản khác sử dụng.")
        return email


class StudentProfileForm(forms.Form):
    full_name = forms.CharField(
        label="Họ và tên",
        max_length=150,
        error_messages={"required": "Vui lòng nhập họ và tên."},
    )
    email = forms.EmailField(
        label="Email",
        max_length=150,
        error_messages={
            "required": "Vui lòng nhập email.",
            "invalid": "Email không hợp lệ.",
        },
    )
    avatar = forms.ImageField(
        label="Ảnh đại diện",
        required=False,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control rounded-3"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        user_model = get_user_model()
        other_accounts = user_model.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email),
        ).exclude(pk=self.user.pk)
        if other_accounts.exists():
            raise forms.ValidationError("Email này đã được tài khoản khác sử dụng.")
        return email
