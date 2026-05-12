from django import forms
from .models import Strategy, StrategyCondition

class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StrategyConditionForm(forms.ModelForm):
    class Meta:
        model = StrategyCondition
        fields = ['indicator', 'operator', 'value']

StrategyConditionFormSet = forms.inlineformset_factory(
    Strategy, StrategyCondition, form=StrategyConditionForm,
    extra=1, can_delete=True
)