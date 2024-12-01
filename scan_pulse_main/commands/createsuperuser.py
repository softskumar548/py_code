from django.contrib.auth.management.commands.createsuperuser import Command as BaseCreateSuperuserCommand
from your_app_name.models import Role, CustomUser
from django.core.management.base import CommandError

class Command(BaseCreateSuperuserCommand):
    def handle(self, *args, **options):
        super().handle(*args, **options)

        # Assign the "Superuser" role
        username = options.get('username')
        user = CustomUser.objects.get(username=username)
        try:
            role = Role.objects.get(name="Superuser")
        except Role.DoesNotExist:
            raise CommandError("Superuser role does not exist. Create it first.")

        user.role = role
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Superuser '{user.username}' assigned to role '{role.name}'."))
