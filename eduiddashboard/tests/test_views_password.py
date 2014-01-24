from mock import patch

import simplejson as json
import vccs_client

from eduid_am.exceptions import UserDoesNotExist

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard import vccs
from eduiddashboard.vccs import (check_password, add_credentials,
                                 provision_credentials)


class FakeVCCSClient(vccs_client.VCCSClient):

    def __init__(self, fake_response=None):
        self.fake_response = fake_response

    def _execute_request_response(self, _service, _values):
        if self.fake_response is not None:
            return self.fake_response

        fake_response = {}
        if _service == 'add_creds':
            fake_response = {
                'add_creds_response': {
                    'version': 1,
                    'success': True,
                },
            }
        elif _service == 'authenticate':
            fake_response = {
                'auth_response': {
                    'version': 1,
                    'authenticated': True,
                },
            }
        elif _service == 'revoke_creds':
            fake_response = {
                'revoke_creds_response': {
                    'version': 1,
                    'success': True,
                },
            }
        return json.dumps(fake_response)


class PasswordFormTests(LoggedInReguestTests):

    formname = 'passwordsview-form'
    initial_password = 'old-password'

    def setUp(self, settings={}):
        super(PasswordFormTests, self).setUp(settings=settings)
        vccs_url = self.settings['vccs_url']
        fake_vccs_client = FakeVCCSClient()
        mock_config = {
            'return_value': fake_vccs_client,
        }
        self.patcher = patch.object(vccs, 'get_vccs_client', **mock_config)
        self.patcher.start()
        provision_credentials(vccs_url, self.initial_password, self.user)

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/security/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/security/')
        self.assertEqual(response.status, '302 Found')

    def test_add_credentials(self):
        vccs_url = self.settings['vccs_url']
        self.assertTrue(check_password(vccs_url, self.initial_password, self.user))
        new_password = 'new-password'
        add_credentials(vccs_url, self.initial_password, new_password, self.user)
        self.assertTrue(check_password(vccs_url, new_password, self.user))

        with patch('eduiddashboard.vccs', clear=True):
            vccs.get_vccs_client.return_value = FakeVCCSClient(fake_response={
                'auth_response': {
                    'version': 1,
                    'authenticated': False,
                },
            })
            self.assertFalse(check_password(vccs_url, self.initial_password, self.user))

    def test_valid_current_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/security/')

        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password

        response = form.submit('save')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('Your password has been successfully updated',
                      response.body)
        self.assertNotIn('Old password do not match', response.body)
        self.assertNotIn("Both passwords don't match", response.body)

    def test_not_valid_current_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/security/', status=200)

        form = response_form.forms[self.formname]
        form['old_password'].value = 'nonexistingpassword'

        with patch('eduiddashboard.vccs', clear=True):
            vccs.get_vccs_client.return_value = FakeVCCSClient(fake_response={
                'auth_response': {
                    'version': 1,
                    'authenticated': False,
                },
            })
            response = form.submit('save')
            self.assertEqual(response.status, '200 OK')
            self.assertIn('Current password is incorrect', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_password_form_entropy(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/security/')

        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password
        form['custom_password'].value = '0l8m vta8 j9lr'
        form['repeated_password'].value = form['custom_password'].value

        response = form.submit('save')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('Your password has been successfully updated',
                      response.body)
        self.assertNotIn('Old password do not match', response.body)
        self.assertNotIn("Both passwords don't match", response.body)

    def test_password_form_entropy_notvalid(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/security/')

        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password

        for password in [
            'april march',
            'April March',
            'meat with potatoes and bread',
            '123412341234',
            'asdfasdfasdf',
            'eduid',
            'aaaaaaaaaaaaa',
            'onetwothreefour',
        ]:
            form['custom_password'].value = password
            form['repeated_password'].value = password

            response = form.submit('save')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('The password complexity is too weak.',
                          response.body, msg='The entropy for {0} is bigger than required'.format(password))
            self.assertNotIn('Your password has been successfully updated',
                             response.body)

    def test_reset_password(self):
        response_form = self.testapp.get('/profile/reset-password/email/')

        form = response_form.forms['resetpasswordemailview-form']

        form['email_or_username'].value = 'notexistingmail@foodomain.com'
        with self.assertRaises(UserDoesNotExist):
            response = form.submit('reset')

        reset_passwords = list(self.db.reset_passwords.find())
        for email in self.user['mailAliases']:
            form['email_or_username'].value = email['email']
            response = form.submit('reset')
            self.assertEqual(response.status, '302 Found')
        reset_passwords_after = list(self.db.reset_passwords.find())
        self.assertNotEqual(len(reset_passwords), len(reset_passwords_after))

    def tearDown(self):
        super(PasswordFormTests, self).tearDown()
        self.patcher.stop()
