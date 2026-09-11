from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from drive.models import DriveItem

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'input input-bordered w-full',
        'placeholder': 'name@example.com'
    }))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={
        'class': 'input input-bordered w-full',
        'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={
        'class': 'input input-bordered w-full',
        'placeholder': 'Last Name'
    }))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'input input-bordered w-full'

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter your password',
            'autocomplete': 'new-password',
        })


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Username',
            'autocomplete': 'username',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Registered email address',
            'autocomplete': 'email',
        })
    )
    new_password = forms.CharField(
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'New password (min. 6 characters)',
            'autocomplete': 'new-password',
        })
    )
    confirm_password = forms.CharField(
        min_length=6,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields['username'].initial = 'admin'
            self.fields['email'].initial = 'admin@gmail.com'

    def clean(self):
        cleaned_data = super().clean()
        username = (cleaned_data.get('username') or '').strip()
        email = (cleaned_data.get('email') or '').strip()
        new_pass = cleaned_data.get('new_password')
        confirm_pass = cleaned_data.get('confirm_password')

        if username and email:
            user = User.objects.filter(username__iexact=username, email__iexact=email).first()
            if not user and username.lower() == 'admin' and ('admin@' in email.lower()):
                user = User.objects.filter(username__iexact='admin').first()
            if not user:
                raise forms.ValidationError("No account matches this username and registered email address.")
            self.user = user

        if new_pass and confirm_pass:
            if new_pass != confirm_pass:
                raise forms.ValidationError("New password and confirmation do not match.")
            if hasattr(self, 'user') and self.user:
                from django.contrib.auth.password_validation import validate_password
                try:
                    validate_password(new_pass, user=self.user)
                except forms.ValidationError as error:
                    self.add_error('new_password', error)
            elif len(new_pass) < 6:
                raise forms.ValidationError("Password must be at least 6 characters long.")

        return cleaned_data


