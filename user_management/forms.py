from django import forms
from .models import CustomUser, Client, Agent, ClientDetails, Plan


class LoginForm(forms.Form):
    """Login form for users."""
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your password'
    }))


class CustomUserCreationForm(forms.ModelForm):
    """Form to create CustomUser instances."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter a password'
    }))

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter an email address'}),
        }


class ClientCreationForm(forms.ModelForm):
    """Form to create Client instances."""
    class Meta:
        model = Client
        fields = ['company_name', 'address']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter company name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter company address'}),
        }

class ClientDetailsForm(forms.ModelForm):
    """Form to handle additional client details."""
    
    def __init__(self, *args, **kwargs):
        is_plan_read_only = kwargs.pop('is_plan_read_only', False)
        super().__init__(*args, **kwargs)
        
        # Make expiration_date read-only
        self.fields['expiration_date'].disabled = True
        self.fields['expiration_date'].widget.attrs['readonly'] = True
        
        # Restrict plan modifications for non-superadmins
        if is_plan_read_only:
            self.fields['plan'].disabled = True
            self.fields['plan'].widget.attrs['readonly'] = True


    class Meta:
        model = ClientDetails
        fields = ['phone', 'contact_person_name', 'url_path', 'plan', 'expiration_date']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'contact_person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person name'
            }),
            'url_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter URL'
            }),
            'plan': forms.Select(attrs={
                'class': 'form-control',
            }),
            'expiration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'readonly': 'readonly'
            }),
        }




class DynamicPublicForm(forms.Form):
    """Dynamic form for public feedback."""
    def __init__(self, fields, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in fields:
            if field.field_type == 'text':
                self.fields[field.name] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif field.field_type == 'textarea':
                self.fields[field.name] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    widget=forms.Textarea(attrs={'class': 'form-control'})
                )
            elif field.field_type == 'radio':
                choices = [(choice.strip(), choice.strip()) for choice in field.choices.split(',')]
                self.fields[field.name] = forms.ChoiceField(
                    label=field.label,
                    required=field.required,
                    widget=forms.RadioSelect,
                    choices=choices
                )
            elif field.field_type == 'checkbox':
                if field.choices:  # Handle multiple checkboxes for options
                   choices = [(choice.strip(), choice.strip()) for choice in field.choices.split(',')]
                   self.fields[field.name] = forms.MultipleChoiceField(
                        label=field.label,
                        required=field.required,
                        widget=forms.CheckboxSelectMultiple,
                        choices=choices
                    )
                else:
                    self.fields[field.name] = forms.BooleanField(
                        label=field.label,
                        required=field.required
                    )
            elif field.field_type == 'dropdown':
                choices = [(choice.strip(), choice.strip()) for choice in field.choices.split(',')]
                self.fields[field.name] = forms.ChoiceField(
                    label=field.label,
                    required=field.required,
                    widget=forms.Select(attrs={'class': 'form-control'}),
                    choices=choices
                )
            elif field.field_type == 'star_rating':
                self.fields[field.name] = forms.ChoiceField(
                    label=field.label,
                    required=field.required,
                    widget=forms.HiddenInput(attrs={'class': 'star-rating'}),
                    choices=[(i, f"{i} Stars") for i in range(0, 5)]  # 0 to 5 stars
                )

class AgentCreationForm(forms.ModelForm):
    """Form to create Agent instances."""
    class Meta:
        model = Agent
        fields = []

class CustomUserEditForm(forms.ModelForm):
    # Add a password reset field
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password'}),
        label="New Password"
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email']  # Include other fields you want to edit

    def save(self, commit=True):
        # Override save to handle password reset
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)  # Hash and set the new password
        if commit:
            user.save()
        return user