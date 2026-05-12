"""
Формы для регистрации пользователей.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class RegistrationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.

    Расширяет стандартную UserCreationForm, добавляя обязательное
    поле email. Убирает подсказки (help_text) у всех полей.
    """

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        """
        Убирает help_text у всех полей формы.
        """
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.help_text = ''

    def save(self, commit=True):
        """
        Сохраняет пользователя с указанным email.

        Args:
            commit (bool): сохранять ли объект в базу данных (по умолчанию True).

        Returns:
            User: созданный объект пользователя.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['age']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if self.user and commit:
            self.user.email = self.cleaned_data['email']
            self.user.save()
        return profile

class BalanceUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['balance']

    def clean_balance(self):
        balance = self.cleaned_data['balance']
        if balance < 0:
            raise forms.ValidationError("Баланс не может быть отрицательным.")
        return balance

class BalanceTopUpForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label='Сумма пополнения (₽)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )