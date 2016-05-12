# -*- coding: utf-8 -*-
"""
Created on Mon May  9 15:33:58 2016

@author: richard
"""

import os
import unittest

from mock import patch, MagicMock

from flask import Flask
import flask_mailgun
from tests import config
from tests.fixtures.email import make_email_request, make_email, sign_email
import ipdb


def get_app(name):
    app = Flask(name)
    app.config.from_object(config)
    return app


class MailgunTestBase(unittest.TestCase):
    def setUp(self):
        self.app = get_app('test')
        self.appclient = self.app.test_client()
        self.mailgun = flask_mailgun.MailGun()
        self.mailgun.init_app(self.app)
        self.post_patcher = patch('flask_mailgun.requests.post')
        self.mock_post = self.post_patcher.start()

    def tearDown(self):
        self.post_patcher.stop()


class SendMessageTest(MailgunTestBase):
    def test_send_simple_message(self):
        message = {"from": "from@example.com",
                   "to": ["user1@example.com", "user2@example.com"],
                   "subject": "Hello",
                   "text": "Testing some Mailgun awesomness!"}
        self.mailgun.send_email(**message)
        self.assertTrue(self.mock_post.called)
        url = self.mock_post.call_args[0][0]
        auth = self.mock_post.call_args[1]['auth']
        data = self.mock_post.call_args[1]['data']
        # files = self.mock_post.call_args[1]['files']
        self.assertEqual(url, 'https://api.mailgun.net/v3/example.com/messages')
        self.assertEqual(auth, ('api', 'testtesttest'))
        # self.assertEqual(files, [])
        self.assertEqual(data['from'], 'from@example.com')
        self.assertEqual(data['to'], message['to'])
        self.assertEqual(data['subject'], message['subject'])
        self.assertEqual(data['text'], message['text'])


class ReceiveMessageTest(MailgunTestBase):
    def test_email_verify(self):
        email = make_email()
        # assert error if email not signed
        with self.assertRaises(flask_mailgun.MailGunException):
            self.mailgun.mailgun_api.verify_email(email)
        # test runs without error on signed email
        email = sign_email(email, self.mailgun)
        self.mailgun.mailgun_api.verify_email(email)

    def test_receive_message(self):
        request = make_email_request(self.mailgun)
        self.mailgun.create_route('/upload')
        self.mailgun.run_async = False
        response = self.appclient.post('/upload', data=request)
        self.assertEqual(response.status_code, 200)


class ProcessMessageTest(MailgunTestBase):
    def __init__(self):
        self.email_request = make_email_request(self.mailgun)

        # Add on_receive and on_attachment functionality to the App
        @self.mailgun.on_receive
        def app_on_attachment(email, filename, stream):
            ipdb.set_trace()
            self.assertEqual(email, self.email_request)
            self.assertEqual(filename, self.email_request)

        @self.mailgun.on_attachment
        def app_on_receive(email):
            ipdb.set_trace()
            self.assertEqual(email, self.email_request)

    def test_on_attachment(self):
        response = self.appclient.post('/upload', data=self.email_request)
        self.assertEqual(response.status_code, 200)

    def test_on_receive(self):
        response = self.appclient.post('/upload', data=self.email_request)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
