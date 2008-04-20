from django.template import Library
from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from userprofile.models import Profile,Avatar
from django.conf import settings
import datetime
import os.path

register = Library()

@register.inclusion_tag('userprofile/usercard.html')
def get_usercard(user):
    profile, created = Profile.objects.get_or_create(user=user)
    return locals()

@register.filter
@stringfilter
def avatar(user, width):
    user = User.objects.get(username=user)
    try:
        if type(user) == type(u"") or type(user) == type(""):
            user = User.objects.get(username=user)

        avatar = Avatar.objects.get(user=user)
        if avatar.get_photo_filename() and os.path.isfile(avatar.get_photo_filename()):
            avatar_url = avatar.get_absolute_url()
        else:
            raise Exception()
    except:
        avatar_url = "%simages/default.gif" % settings.MEDIA_URL

    path, extension = os.path.splitext(avatar_url)
    return  "%s.%s%s" % (path, width, extension)