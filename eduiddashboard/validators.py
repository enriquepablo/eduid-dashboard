import colander

from eduiddashboard.i18n import TranslationString as _


class EmailUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if 'add' in request.POST:
            if request.userdb.exists_by_field('emails.email', value):
                raise colander.Invalid(node,
                                       _("This email is already registered"))
