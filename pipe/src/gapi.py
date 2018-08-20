#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from datetime import date

import httplib2
import os
from apiclient import discovery, errors
from oauth2client import client, tools
from oauth2client.file import Storage
import base64
import argparse

from pipe.src.gapi_email import GapiEmail
from pipe.src.util import Util


class Gapi:
    def __init__(self):
        # If modified, delete previously saved credentials at ~/.credentials/gmail-credentials.json
        self.__SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
        self.__CLIENT_SECRET_FILE = 'client_secret.json'
        self.__APPLICATION_NAME = 'DCP Pipeline'

    def main(self):
        # Get authenticated Gmail Service Object
        service = self.get_credentials()

        # Retrieve list of ids of unread emails
        unread_emails = self.list_unread_emails(service)

        # List to hold gapi_emails
        email_objects = []

        # For each email, get the full text, parse and convert to gapi_email objects
        for n in unread_emails:
            full_email = self.get_email_full(service, n['id'])
            email_obj = self.parse_email(full_email)
            email_objects.append(email_obj)

        # self.store_emails(email_objects)

        return email_objects

    @staticmethod
    def store_emails(email_values):
        parameter_list = [i.get_values for i in email_values]

        sql = """INSERT INTO email_store (harvested_date, sent_date, label_id, message_count, 
        gapi_email_id) VALUES (%s, %s, %s, %s, %s)"""

        print(parameter_list)

        u = Util()
        u.update_db(sql, parameter_list)


    def get_credentials(self):
        """Gets user credentials from storage.
        If credentials not found or invalid, the OAuth2 flow
        is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
            :return: Gmail Service object
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')

        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'gmail-credentials.json')
        store = Storage(credential_path)
        credentials = store.get()
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()

        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.__CLIENT_SECRET_FILE, self.__SCOPES)
            flow.user_agent = self.__APPLICATION_NAME
            credentials = tools.run_flow(flow, store, flags)
            print('Storing credentials to ' + credential_path)

        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)
        return service

    @staticmethod
    def list_unread_emails(service):
        """Lists all unread emails in the user's mailbox ,
        :param service: Authorised Gmail API Service object
        :return: List of email IDs
        """
        try:
            response = service.users().messages().list(userId='me', q='is:unread').execute()
            p_emails = []
            if 'messages' in response:
                p_emails.extend(response['messages'])
                while 'nextPageToken' in response:
                    page_token = response['nextPageToken']
                    response = service.users().messages().list(userId='me', q='is:unread',
                                                               pageToken=page_token).execute()
                    p_emails.extend(response['messages'])
            return p_emails

        except errors.HttpError as error:
            print(f'An error occurred during unread email retrieval: ${error}')

    @staticmethod
    def get_email_full(service, email_id):
        """
        Get email from inbox via id
        :param service: Authorised Gmail API Service object
        :param email_id: email message GUID
        :return: Email payload
        """
        try:
            p_email = service.users().messages().get(userId='me', id=email_id, format='full').execute()
            return p_email
        except errors.HttpError as error:
            print(f'An error occurred during full-text message retrieval: {error}')

    @staticmethod
    def parse_email(p_email):
        # Get data to feed into p_email constructor
        date_harvested = date.today()
        date_received = date.fromtimestamp(int(p_email['internalDate']) / 1000).isoformat()
        email_body = base64.urlsafe_b64decode(p_email['payload']['body']['data'])
        gapi_email_id = p_email['id']
        label = None

        # Go through labels looking for custom ones
        for lab in p_email['labelIds']:
            match = re.match("Label", lab)
            if match:
                label = lab
                break

        # Create Email object and return
        email_obj = GapiEmail(harvested_date=date_harvested, sent_date=date_received, email_body=email_body,
                              gapi_email_id=gapi_email_id, label=label)
        return email_obj
