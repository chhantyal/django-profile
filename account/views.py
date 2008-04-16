from django.shortcuts import render_to_response, get_object_or_404
from django import newforms as forms
from django.http import Http404
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from models import LostPassword, EmailValidate
from django.utils import simplejson
from django.template import RequestContext
from django.contrib.sites.models import Site
from forms import UserForm, EmailChangeForm, PasswordResetForm, changePasswordKeyForm, changePasswordAuthForm
from django.contrib.auth.decorators import login_required
from django.template import Context, loader
from django.conf import settings
from django.core.validators import email_re

def json_error_response(error_message, *args, **kwargs):
    return HttpResponse(simplejson.dumps(dict(success=False,
                                              error_message=error_message), ensure_ascii=False))

def email_new_key():
    while True:
        key = User.objects.make_random_password(70)
        try:
            EmailValidate.objects.get(key=key)
        except EmailValidate.DoesNotExist:
            return key

@login_required
def change_email_with_key(request, key, template):
    """
    Verify key and change email
    """
    try:
        verify = EmailValidate.objects.get(key=key, user=request.user)
        user = User.objects.get(username=str(request.user))
        user.email = verify.email
        user.save()
        verify.delete()
        message = _('E-mail changed successfully.')
        successful = True
    except:
        message = _('The key you received via e-mail is no longer valid. Please try the e-mail change process again.')
        successful = False

    return render_to_response(template, locals(), context_instance=RequestContext(request))

def email_change(request, template):
    """
    Change the e-mail page
    """
    if request.method == 'POST':
        form = EmailChangeForm(request.POST)
        if form.is_valid():

            email = form.cleaned_data.get('email')
            EmailValidate.objects.filter(user=request.user, email=email).delete()
            validate = EmailValidate(user=request.user, email=email, key=email_new_key())
            site = Site.objects.get_current()
            site_name = site.name
            t = loader.get_template('account/email_change_confirmation.txt')
            message = 'http://%s/accounts/email/change/%s/' % (site_name, validate.key)
            send_mail('Email change confirmation on %s' % site.name, t.render(Context(locals())), None, [email])
            validate.save()

            return HttpResponseRedirect('%sprocessed/' % request.path)
    else:
        form = EmailChangeForm()

    return render_to_response(template, locals(), context_instance=RequestContext(request))

def register(request, template):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            newuser = User.objects.create_user(username=username, email='', password=password)

            if not hasattr(settings, "EMAIL_VALIDATION"):
                newuser.is_active = False
                newuser.email = form.cleaned_data.get('email')
                newuser.save()
                return HttpResponseRedirect('%svalidate/' % request.path)
            else:
                newuser.save()
                return HttpResponseRedirect('%scomplete/' % request.path)
    else:
        form = UserForm()

    if hasattr(settings, "EMAIL_VALIDATION"):
        email = True

    return render_to_response(template, locals(), context_instance=RequestContext(request))

def reset_password(request, template):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            user = User.objects.get(email=email)

            if email and user:
                from django.core.mail import send_mail
                LostPassword.objects.filter(user=user).delete()
                pwd = LostPassword.objects.create(user=user, key=email_new_key())
                site = Site.objects.get_current()
                site_name = site.name
                t = loader.get_template('account/password_reset_email.txt')
                message = 'http://%s/accounts/password/change/%s/' % (site_name, pwd.key)
                send_mail(_('Password reset on %s') % site.name, t.render(Context(locals())), None, [user.email])
                return HttpResponseRedirect('%sdone/' % request.path)

    else:
        form = PasswordResetForm()

    return render_to_response(template, locals(), context_instance=RequestContext(request))


def change_password_with_key(request, key, template):
    """
    Change a user password with the key sended by e-mail
    """
    lostpassword = get_object_or_404(LostPassword, key=key)

    if lostpassword.is_expired():
        lostpassword.delete()
        return render_to_response('passwd/expired.html', context_instance=context)

    user = lostpassword.user
    if request.method == "POST":
        form = changePasswordKeyForm(request.POST)
        if form.is_valid():
            form.save(key)
            return HttpResponseRedirect('/accounts/password/change/done/')
    else:
        form = changePasswordKeyForm()

    return render_to_response(template, locals(), context_instance=RequestContext(request))

@login_required
def change_password_authenticated(request, template):
    """
    Change the password of the authenticated user
    """
    if request.method == "POST":
        form = changePasswordAuthForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            return HttpResponseRedirect('/accounts/password/change/done/')
    else:
        form = changePasswordAuthForm()

    return render_to_response(template, locals(), context_instance=RequestContext(request))

def check_user(request, user):
    """
    Check if a username exists. Only HTTPXMLRequest. Returns JSON
    """
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        if len(user) < 3 or not set(user).issubset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") or len(User.objects.filter(username=user)) == 1:
            return json_error_response(simplejson.dumps({'success': False}))
        else:
            return HttpResponse(simplejson.dumps({'success': True}))
    else:
        raise Http404()

def check_email_unused(request, email):
    """
    Check if an e-mail exists. Only HTTPXMLRequest. Returns JSON
    """
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        if not email_re.search(email):
            return json_error_response(_("Invalid e-mail"))

        if not User.objects.filter(email=email):
            return HttpResponse(simplejson.dumps({'success': True}))
        else:
            return json_error_response(_("E-mail not registered"))
    else:
        raise Http404()

def check_email(request, email):
    """
    Check if a username exists. Only HTTPXMLRequest. Returns JSON
    """
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        if (len(User.objects.filter(email=email)) == 1):
            return HttpResponse(simplejson.dumps({'success': True}))
        else:
            return json_error_response(_("E-mail not registered"))
    else:
        raise Http404()

def logout(request, template):
    from django.contrib.auth import logout
    logout(request)
    return render_to_response(template, locals(), context_instance=RequestContext(request))