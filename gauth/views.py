import os

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from oauth2client.contrib import xsrfutil
from oauth2client.contrib.django_orm import Storage
from oauth2client.client import flow_from_clientsecrets

from models import (CredentialsModel,
                    FlowModel)
from sefaria import settings

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')


@login_required
def index(request):
    """
    Step 1 of Google OAuth 2.0 flow.
    """
    FLOW = flow_from_clientsecrets(
        CLIENT_SECRETS,
        scope=request.session.get('gauth_scope', ''),
        # approval_prompt='force',
        redirect_uri=request.build_absolute_uri(reverse('gauth_callback')))

    FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
                                                   request.user)
    authorize_url = FLOW.step1_get_authorize_url()
    flow_storage = Storage(FlowModel, 'id', request.user, 'flow')
    flow_storage.put(FLOW)

    request.session['next_view'] = request.GET.get('next', '/')

    return redirect(authorize_url)


@login_required
def auth_return(request):
    """
    Step 2 of Google OAuth 2.0 flow.
    """
    if 'state' not in request.REQUEST:
        return redirect('gauth_index')

    if not xsrfutil.validate_token(settings.SECRET_KEY,
                                   str(request.REQUEST['state']),
                                   request.user):
        return HttpResponseBadRequest()

    FLOW = Storage(FlowModel, 'id', request.user, 'flow').get()
    # Not sure if this test is needed in addition to
    # the `if 'state' not in request.REQUEST` test.
    if FLOW is None:
        return redirect('gauth_index')

    credential = FLOW.step2_exchange(request.REQUEST)
    cred_storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    cred_storage.put(credential)

    return redirect(request.session.get('next_view', '/'))
