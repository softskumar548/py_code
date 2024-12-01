from django.contrib import admin, messages
from .models import Role, CustomUser, Agent, Client, Plan
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from .models import Plan, ClientDetails

class PlanAdminForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        plan = self.instance

        if plan.pk:  # Existing plan
            existing_plan = Plan.objects.get(pk=plan.pk)
            if ClientDetails.objects.filter(plan=existing_plan).exists():
                # Check if fields have changed
                if (
                    cleaned_data.get('name') != existing_plan.name or
                    cleaned_data.get('duration_type') != existing_plan.duration_type or
                    cleaned_data.get('duration_value') != existing_plan.duration_value
                ):
                    raise ValidationError("You cannot modify a plan that is already assigned to a client.")

        return cleaned_data

class PlanAdmin(admin.ModelAdmin):
    form = PlanAdminForm
    
    def has_delete_permission(self, request, obj=None):
        if obj and ClientDetails.objects.filter(plan=obj).exists():
            return False  # Prevent deletion if the plan is assigned to a client
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        # Add extra validation before deletion
        if ClientDetails.objects.filter(plan=obj).exists():
            messages.error(request, "This plan is assigned to clients and cannot be deleted.")
        else:
            super().delete_model(request, obj)

class ClientDetailsAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        # Trigger save to ensure expiration date is recalculated
        obj.save()


# Register your models here.
admin.site.register(Role)
admin.site.register(CustomUser)
admin.site.register(Agent)
admin.site.register(Client)
admin.site.register(ClientDetails, ClientDetailsAdmin)
admin.site.register(Plan, PlanAdmin)