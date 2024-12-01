from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from .models import CustomUser, Role, Agent, Client, ClientFormField, ClientDetails, ClientResponse
from .forms import CustomUserCreationForm, ClientCreationForm, DynamicPublicForm, ClientDetailsForm, AgentCreationForm, CustomUserEditForm
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.forms import modelformset_factory
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
from django.contrib import messages



# Create your views here.

def home(request):
    return render(request, 'home.html', {'year': datetime.now().year})

def landing_page(request):
    return render(request, 'landing_page.html')

# def login_view(request):
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         user = authenticate(request, username=email, password=password)
#         if user:
#             login(request, user)
#             return redirect('dashboard')
#         else:
#             return render(request, 'login.html', {'error': 'Invalid credentials'})

#     return render(request, 'login.html')

def login_view(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def custom_logout(request):
    """
    Logs out the user and redirects to the home page with a success message.
    """
    logout(request)  # Log out the user
    messages.success(request, "You have been successfully logged out.")  # Add a success message
    return redirect('home')  # Redirect to the home page

@login_required
def dashboard(request):
    role = request.user.role.name if request.user.role else None
    if role == 'Superuser':
        return redirect('superuser_dashboard')
    elif role == 'Agent':
        return redirect('agent_dashboard')
    elif role == 'Client':
        return redirect('client_dashboard')
    return HttpResponseForbidden("Access denied")

@login_required
def superuser_dashboard(request):
    if request.user.role.name != 'Superuser':
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Fetch agents created by the superuser
    agents = CustomUser.objects.filter(role__name='Agent', created_by=request.user)

    # Fetch clients created directly by the superuser
    superuser_clients = CustomUser.objects.filter(role__name='Client', created_by=request.user)

    # Fetch clients created by agents under the superuser
    agent_clients = CustomUser.objects.filter(
        role__name='Client',
        created_by__in=agents  # Match agents created by this superuser
    )

    # Combine both sets of clients
    clients = superuser_clients.union(agent_clients)

    return render(request, 'superuser_dashboard.html', {
        'agents': agents,
        'clients': clients,
    })


@login_required
def agent_dashboard(request):
    if request.user.role.name != 'Agent':
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Fetch clients created by the logged-in agent
    created_clients = Client.objects.filter(created_by=request.user)

    return render(request, 'agent_dashboard.html', {
        'agent': request.user,  # Pass the agent object,
        'created_clients': created_clients,  # Pass the list of clients
    })

@login_required
def client_dashboard(request):
    if request.user.role.name != 'Client':
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Fetch the client profile and responses
    client = request.user.client_profile
    responses = client.responses.all()  # Assuming a related_name="responses" in ClientResponse

    return render(request, 'client_dashboard.html', {
        'client': client,
        'responses': responses,
    })

@login_required
def create_agent(request):
    if request.user.role.name != 'Superuser':
        return HttpResponseForbidden("You are not authorized to create agents.")
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = Role.objects.get(name='Agent')  # Assign Agent role
            user.created_by = request.user
            user.set_password(form.cleaned_data['password'])
            user.save()
            Agent.objects.create(user=user, created_by=request.user)
            return redirect('superuser_dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'create_agent.html', {'form': form})

@login_required
def create_client(request):
    if request.user.role.name not in ['Superuser', 'Agent']:
        return HttpResponseForbidden("You are not authorized to create clients.")

    if request.method == 'POST':
        # Process the forms
        form = CustomUserCreationForm(request.POST)
        details_form = ClientDetailsForm(request.POST or None, user=request.user)
        client_form = ClientCreationForm(request.POST)

        # Process dynamic fields
        field_names = request.POST.getlist('field_name')
        field_labels = request.POST.getlist('field_label')
        field_types = request.POST.getlist('field_type')
        field_required = request.POST.getlist('field_required')
        field_choices = request.POST.getlist('field_choices')
        field_hidden = request.POST.getlist('field_hidden')

        # Debugging POST data
        print("POST Data:", request.POST)

        if form.is_valid() and details_form.is_valid() and client_form.is_valid():
            try:
                # Validate dynamic fields
                valid_fields = []
                max_length = max(len(field_names), len(field_labels), len(field_types))

                # Extend lists to the same length
                field_required = (field_required + [''] * (max_length - len(field_required)))
                field_choices = (field_choices + [''] * (max_length - len(field_choices)))
                field_hidden = (field_hidden + [''] * (max_length - len(field_hidden)))

                for index, (name, label, ftype, required, choices, hidden) in enumerate(zip(
                    field_names, field_labels, field_types, field_required, field_choices, field_hidden
                )):
                    name = name.strip()
                    label = label.strip()
                    ftype = ftype.strip()
                    choices = choices.strip()

                    print(f"Processing Field {index}: name='{name}', label='{label}', type='{ftype}', required='{required}', choices='{choices}', hidden='{hidden}'")

                    if not name or not label or not ftype:
                        print(f"Skipping field {index}: Missing name, label, or type.")
                        continue

                    if ftype in ['radio', 'dropdown'] and not choices:
                        print(f"Skipping field {index} ({label}): Missing choices for {ftype}.")
                        continue

                    valid_fields.append({
                        'name': name,
                        'label': label,
                        'field_type': ftype,
                        'required': (required == 'on'),
                        'choices': choices if ftype in ['radio', 'dropdown'] else '',
                        'hidden': (hidden == 'on'),
                    })

                # Debugging valid fields
                print("Valid Fields to Save:", valid_fields)

                with transaction.atomic():
                    # Create the user
                    user = form.save(commit=False)
                    user.role = Role.objects.get(name='Client')  # Assign Client role
                    user.created_by = request.user
                    user.set_password(form.cleaned_data['password'])
                    user.save()

                    # Create the Client profile
                    client = client_form.save(commit=False)
                    client.user = user
                    client.created_by = request.user
                    client.save()

                    # Create the ClientDetails instance
                    details = details_form.save(commit=False)
                    details.client = client
                    details.save()

                    # Save valid dynamic fields
                    for field in valid_fields:
                        ClientFormField.objects.create(
                            client=client,
                            name=field['name'],
                            label=field['label'],
                            field_type=field['field_type'],
                            required=field['required'],
                            choices=field['choices'],
                            hidden=field['hidden']
                        )

                # Redirect based on the role
                if request.user.role.name == 'Superuser':
                    return redirect('superuser_dashboard')
                elif request.user.role.name == 'Agent':
                    return redirect('agent_dashboard')
            except Exception as e:
                print("Unexpected Error:", e)
                return render(request, 'create_client.html', {
                    'form': form,
                    'details_form': details_form,
                    'error': f"An unexpected error occurred: {e}"
                })

        # Log form validation errors
        print("Form Errors:", form.errors)
        print("Details Form Errors:", details_form.errors)

        return render(request, 'create_client.html', {
            'form': form,
            'client_form': client_form,
            'details_form': details_form,
            'error': 'Please correct the errors in the form.'
        })

    # For GET request
    form = CustomUserCreationForm()
    details_form = ClientDetailsForm()
    client_form = ClientCreationForm()
    return render(request, 'create_client.html', {'form': form, 'client_form': client_form, 'details_form': details_form})



# @login_required
# def create_client(request):
#     if request.user.role.name != 'Superuser':
#         return HttpResponseForbidden("You are not authorized to create clients.")

#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         details_form = ClientDetailsForm(request.POST)

#         # Process configurable fields
#         field_names = request.POST.getlist('field_name')
#         field_labels = request.POST.getlist('field_label')
#         field_types = request.POST.getlist('field_type')
#         field_required = request.POST.getlist('field_required')
#         field_choices = request.POST.getlist('field_choices')
#         field_hidden = request.POST.getlist('field_hidden')

#         if form.is_valid() and details_form.is_valid():
#             # Validate dynamic fields
#             for name, label, ftype in zip(field_names, field_labels, field_types):
#                 if not name or not label or not ftype:
#                     return render(request, 'create_client.html', {
#                         'form': form,
#                         'details_form': details_form,
#                         'error': 'Each dynamic field must have a name, label, and type.'
#                     })
#                 if ftype in ['radio', 'dropdown'] and not field_choices:
#                     return render(request, 'create_client.html', {
#                         'form': form,
#                         'details_form': details_form,
#                         'error': 'Radio and dropdown fields require choices.'
#                     })

#             try:
#                 with transaction.atomic():
#                     # Create the user
#                     user = form.save(commit=False)
#                     user.role = Role.objects.get(name='Client')  # Assign Client role
#                     user.created_by = request.user
#                     user.set_password(form.cleaned_data['password'])
#                     user.save()

#                     # Create the Client profile
#                     client = Client.objects.create(user=user, created_by=request.user)

#                     # Create the ClientDetails instance
#                     details = details_form.save(commit=False)
#                     details.client = client
#                     details.save()

#                     # Save configurable fields
#                     for name, label, ftype, required, choices, hidden in zip(
#                         field_names, field_labels, field_types, field_required, field_choices, field_hidden
#                     ):
#                         ClientFormField.objects.create(
#                             client=client,
#                             name=name,
#                             label=label,
#                             field_type=ftype,
#                             required=(required == 'on'),
#                             choices=choices if ftype in ['radio', 'dropdown'] else '',
#                             hidden=(hidden == 'on')
#                         )

#                 return redirect('superuser_dashboard')
#             except Exception as e:
#                 print("Error:", e)
#                 return render(request, 'create_client.html', {
#                     'form': form,
#                     'details_form': details_form,
#                     'error': 'An unexpected error occurred. Please try again.'
#                 })
#     else:
#         form = CustomUserCreationForm()
#         details_form = ClientDetailsForm()

#     return render(request, 'create_client.html', {'form': form, 'details_form': details_form})


@login_required
def view_agent(request, agent_id):
    if request.user.role.name != 'Superuser':
        return HttpResponseForbidden("You are not authorized to view this page.")

    agent = CustomUser.objects.filter(id=agent_id, role__name='Agent', created_by=request.user).first()
    if not agent:
        return HttpResponseForbidden("Agent not found or you do not have permission to view this agent.")

    return render(request, 'view_agent.html', {'agent': agent})


@login_required
def view_client(request, client_id):
    # Check if the user is authorized
    if request.user.role.name not in ['Superuser', 'Agent']:
        return HttpResponseForbidden("You are not authorized to view this page.")

    # Fetch the client object
    client = CustomUser.objects.filter(id=client_id, role__name='Client').first()
    if not client:
        return HttpResponseForbidden("Client not found or you do not have permission to view this client.")

    # Superuser access: Check if the client is created by the superuser or their agents
    if request.user.role.name == 'Superuser':
        # Get agents created by the superuser
        agents = CustomUser.objects.filter(role__name='Agent', created_by=request.user)
        # Check if the client was created by the superuser or their agents
        if client.client_profile.created_by != request.user and client.client_profile.created_by not in agents:
            return HttpResponseForbidden("You do not have permission to view this client.")

    # Agent access: Check if the agent created the client
    if request.user.role.name == 'Agent' and client.client_profile.created_by != request.user:
        return HttpResponseForbidden("You do not have permission to view this client.")

    # Fetch client details
    client_profile = client.client_profile  # One-to-one relationship
    additional_details = client_profile.details  # One-to-one relationship with ClientDetails
    configurable_fields = client_profile.form_fields.all()  # Many-to-one relationship

    context = {
        'client': client,
        'client_profile': client_profile,
        'additional_details': additional_details,
        'configurable_fields': configurable_fields,
    }

    return render(request, 'view_client.html', context)


@login_required
def edit_agent(request, agent_id):
    if request.user.role.name != 'Superuser':
        return HttpResponseForbidden("You are not authorized to edit agents.")

    agent = get_object_or_404(CustomUser, id=agent_id, role__name='Agent', created_by=request.user)

    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('superuser_dashboard')
    else:
        form = CustomUserEditForm(instance=agent)

    return render(request, 'edit_agent.html', {'form': form, 'agent': agent})


@login_required
def edit_client(request, client_id):
    client = get_object_or_404(CustomUser, id=client_id, role__name='Client')
    
    # Restrict access: Superusers can edit all clients, agents can edit only their own clients
    if request.user.role.name not in ['Superuser', 'Agent'] or (
        request.user.role.name == 'Agent' and client.client_profile.created_by != request.user
    ):
        return HttpResponseForbidden("You are not authorized to edit clients.")

    # Fetch client and related data
    # client = get_object_or_404(CustomUser, id=client_id, role__name='Client', created_by=request.user)
    client_profile = client.client_profile  # One-to-one relationship
    additional_details = client_profile.details  # One-to-one relationship with ClientDetails

    # Set read-only flag for the plan field if the user is an agent
    is_plan_read_only = request.user.role.name == 'Agent'

    # Formset for configurable fields
    ConfigurableFieldFormSet = modelformset_factory(
        ClientFormField,
        fields=('name', 'label', 'field_type', 'required', 'choices', 'hidden'),
        extra=0,
        can_delete=True,
    )

    print("POST Data for Formset:", request.POST)

    if request.method == 'POST':
        user_form = CustomUserEditForm(request.POST, instance=client)
        client_form = ClientCreationForm(request.POST, instance=client_profile)
        details_form = ClientDetailsForm(request.POST or None, instance=additional_details, is_plan_read_only=is_plan_read_only)
        formset = ConfigurableFieldFormSet(request.POST, queryset=client_profile.form_fields.all())

        # Debugging management form
        print("Formset Management Data:")
        print("TOTAL_FORMS:", request.POST.get("form-TOTAL_FORMS"))
        print("INITIAL_FORMS:", request.POST.get("form-INITIAL_FORMS"))

        if user_form.is_valid() and details_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Save user and details
                    user_form.save()
                    client_form.save()
                    details_form.save()

                    # Handle formset (new rows, updates, deletions)
                    for form in formset:
                        if form.cleaned_data.get('DELETE'):
                            if form.instance.pk:
                                form.instance.delete()
                        else:
                            field = form.save(commit=False)
                            field.client = client_profile  # Link the field to the client
                            field.save()

                # Redirect based on user role
                if request.user.role.name == 'Superuser':
                    return redirect('superuser_dashboard')
                else:
                    return redirect('agent_dashboard')

            except Exception as e:
                print("Unexpected Error:", e)
                return render(request, 'edit_client.html', {
                    'user_form': user_form,
                    'client_form': client_form,
                    'details_form': details_form,
                    'formset': formset,
                    'client': client,
                    'error': f"An unexpected error occurred: {e}",
                })

        # Debugging form validation errors
        print("User Form Errors:", user_form.errors)
        print("Details Form Errors:", details_form.errors)
        print("Formset Errors:", formset.errors)

        return render(request, 'edit_client.html', {
            'user_form': user_form,
            'client_form': client_form,
            'details_form': details_form,
            'formset': formset,
            'client': client,
            'error': 'Please correct the errors in the form.',
        })

    # For GET request
    user_form = CustomUserEditForm(instance=client)
    client_form = ClientCreationForm(instance=client_profile)
    details_form = ClientDetailsForm(instance=additional_details)
    formset = ConfigurableFieldFormSet(queryset=client_profile.form_fields.all())

    context = {
        'user_form': user_form,
        'client_form': client_form,
        'details_form': details_form,
        'formset': formset,
        'client': client,
    }

    return render(request, 'edit_client.html', context)


@csrf_exempt
def public_feedback_page(request, unique_url_path):
    # Retrieve ClientDetails using the URL path
    client_details = get_object_or_404(ClientDetails, url_path=unique_url_path)
    client = client_details.client  # Access the related Client object
    user = client.user  # Access the associated CustomUser instance
    
    # Check if the expiration date has passed
    if client_details.expiration_date and client_details.expiration_date < now():
        # Optional: Render a custom expired page or return a 403 response
        return render(request, 'expired_feedback_page.html', {
            'client': client,
            'details': client_details,
        }, status=403)

    # Fetch dynamic fields for this client
    form_fields = client.form_fields.filter(hidden=False)

    # Dynamically generate the feedback form
    form = DynamicPublicForm(form_fields)

    if request.method == 'POST':
        # Validate the submitted form data
        form = DynamicPublicForm(form_fields, request.POST)
        if form.is_valid():
            # Save the response
            ClientResponse.objects.create(
                client=client,
                data=form.cleaned_data
            )
            return HttpResponseRedirect(f"/thank-you/{unique_url_path}/")

    return render(request, 'client_public_page.html', {
        'client': client,
        'user': user,
        'details': client_details,
        'form': form,
    })

def thank_you_page(request, unique_url_path):
    return render(request, 'thank_you.html', {
        'message': 'Thank you for providing your feedback!'
    })
