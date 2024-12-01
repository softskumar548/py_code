from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class Role(models.Model):
    """Model to define roles."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    @staticmethod
    def default_roles():
        """Prepopulate roles."""
        roles = ['Superuser', 'Agent', 'Client']
        for role in roles:
            Role.objects.get_or_create(name=role)


class CustomUser(AbstractUser):
    """Custom user model with role support."""
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="created_users")
    created_at = models.DateTimeField(auto_now_add=True)


    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f"{self.username} ({self.role.name if self.role else 'No Role'})"


class Client(models.Model):
    """Client-specific profile."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="client_profile")
    company_name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_clients")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Agent(models.Model):
    """Agent-specific profile."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="agent_profile")
    assigned_clients = models.ManyToManyField(Client, related_name="agents")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_agents")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

DURATION_TYPES = [
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('months', 'Months'),
    ('years', 'Years'),
]

class Plan(models.Model):
    """Dropdown options for client plans."""
    name = models.CharField(max_length=50, unique=True)
    duration_type = models.CharField(max_length=10, choices=DURATION_TYPES)
    duration_value = models.PositiveIntegerField()
    
    def __str__(self):
        return self.name

class ClientDetails(models.Model):
    """Additional fields for clients."""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="details")
    phone = models.CharField(max_length=15, blank=True)
    contact_person_name = models.CharField(max_length=100, blank=True)
    url_path = models.SlugField(unique=True, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Automatically calculate expiration date based on the plan
        if self.plan:
            if self.plan.duration_type == 'hours':
                self.expiration_date = self.client.created_at + timedelta(hours=self.plan.duration_value)
            elif self.plan.duration_type == 'days':
                self.expiration_date = self.client.created_at + timedelta(days=self.plan.duration_value)
            elif self.plan.duration_type == 'months':
                self.expiration_date = self.client.created_at + relativedelta(months=self.plan.duration_value)
            elif self.plan.duration_type == 'years':
                self.expiration_date = self.client.created_at + relativedelta(years=self.plan.duration_value)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Details for {self.client.company_name}"

FIELD_TYPES = [
    ('text', 'Text'),
    ('textarea', 'Textarea'),
    ('radio', 'Radio'),
    ('checkbox', 'Checkbox'),
    ('dropdown', 'Dropdown'),
    ('star_rating', 'Star Rating')
]

class ClientFormField(models.Model):
    """Configurable fields for a client's public page."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='form_fields')
    name = models.CharField(max_length=50)  # Internal field name
    label = models.CharField(max_length=100)  # Field label for public page
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)  # Type of field
    required = models.BooleanField(default=False)  # Whether the field is required
    choices = models.TextField(blank=True, help_text="Comma-separated values for dropdown/radio fields")
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.client.company_name} - {self.label}"
        

class ClientResponse(models.Model):
    """Responses from anonymous users."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='responses')
    data = models.JSONField()  # Store anonymous responses as a JSON object
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response for {self.client.company_name} at {self.submitted_at}"