## Personal data form

from deform import Button
from pyramid.view import view_config
from pyramid.i18n import get_localizer

from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person

from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView


def get_status(request, user):
    """

    return msg and icon
    """
    schema = Person()
    completed_fields = 0

    for field in schema.children:
        if field.name != 'csrf' and user.get(field.name, None) is not None:
            completed_fields += 1

    status = {
        'completed': (completed_fields, len(schema.children) - 1)
    }
    return status


def get_tab(request):
    label = _('Personal information')
    return {
        'status': get_status,
        'label': get_localizer(request).translate(label),
        'id': 'personaldata',
    }


@view_config(route_name='personaldata', permission='edit',
             renderer='templates/personaldata-form.jinja2')
class PersonalDataView(BaseFormView):
    """
    Provide the handler to personal data form
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Person()
    route = 'personaldata'
    buttons = (Button(name='save', title=_('Save')), )

    def get_template_context(self):

        return {
            'formname': self.classname
        }

    def save_success(self, user_modified):
        person = self.schema.serialize(user_modified)
        del(person['csrf'])  # Don't save the CSRF token in the user database

        new_preferred_language = person.get('preferredLanguage')
        old_preferred_language = self.user.get_preferred_language()

        # Insert the new/updated user object
        self.user.get_doc().update(person)
        try:
            self.user.save(self.request)
        except UserOutOfSync:
            self.sync_user()
        else:
            message = _('Changes saved')
            self.request.session.flash(
                    get_localizer(self.request).translate(message),
                    queue='forms')
            self.request.stats.count('dashboard/personal_data_saved', 1)

        if new_preferred_language != old_preferred_language:
            self.full_page_reload()
