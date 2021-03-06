"""
Module for jenkinsapi requester (which is a wrapper around python-requests)
"""

import requests
import urlparse
from jenkinsapi.custom_exceptions import JenkinsAPIException
# import logging

# # these two lines enable debugging at httplib level (requests->urllib3->httplib)
# # you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# # the only thing missing will be the response.body which is not logged.
# import httplib
# httplib.HTTPConnection.debuglevel = 1

# logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class Requester(object):

    """
    A class which carries out HTTP requests. You can replace this class with one of your
    own implementation if you require some other way to access Jenkins.

    This default class can handle simple authentication only.
    """

    VALID_STATUS_CODES = [200, ]

    def __init__(self, username=None, password=None, ssl_verify=True, baseurl=None):
        if username:
            assert password, 'Cannot set a username without a password!'

        self.base_scheme = baseurl and urlparse.urlsplit(baseurl).scheme
        self.auth = (username, password) if (username and password) else None
        self.ssl_verify = ssl_verify

    # FIXME This was created because the unit tests hit properties of the Requester
    @property
    def username(self):
        return self.auth[0] if self.auth else None

    # FIXME This was created because the unit tests hit properties of the Requester
    @property
    def password(self):
        return self.auth[1] if self.auth else None

    def get_request_dict(self, params=None, data=None, files=None, headers=None):
        # Perform assertions
        for arg, name in ((params, "Params"), (headers, "Headers")):
            msg = "{0} must be a dict, got '{1}'".format(name, arg)
            assert (not arg) or isinstance(arg, dict), msg

        # Set up lists of key-value tuples for dictionary construction
        filtered_args = [
            (key, value)
            for key, value in [('params', params), ('headers', headers), ('files', files), ('data', data)]
            if value is not None
        ]
        unfiltered_args = [('auth', self.auth), ('verify', self.ssl_verify)]

        return dict(filtered_args + unfiltered_args)

    def _update_url_scheme(self, url):
        """
        Updates scheme of given url to the one used in Jenkins baseurl.
        """
        if self.base_scheme and not url.startswith("%s://" % self.base_scheme):
            url_split = urlparse.urlsplit(url)
            url = urlparse.urlunsplit(
                [
                    self.base_scheme,
                    url_split.netloc,
                    url_split.path,
                    url_split.query,
                    url_split.fragment
                ]
            )
        return url

    def get_url(self, url, params=None, headers=None):
        requestKwargs = self.get_request_dict(params=params, headers=headers)
        return requests.get(self._update_url_scheme(url), **requestKwargs)

    def post_url(self, url, params=None, data=None, files=None, headers=None):
        requestKwargs = self.get_request_dict(params=params, data=data, files=files, headers=headers)
        return requests.post(self._update_url_scheme(url), **requestKwargs)

    def post_xml_and_confirm_status(self, url, params=None, data=None, valid=None):
        headers = {'Content-Type': 'text/xml'}
        return self.post_and_confirm_status(url, params=params, data=data, headers=headers, valid=valid)

    def post_and_confirm_status(self, url, params=None, data=None, files=None, headers=None, valid=None):
        valid = valid or self.VALID_STATUS_CODES
        assert isinstance(data, (
            str, dict)), \
            "Unexpected type of parameter 'data': %s. Expected (str, dict)" % type(data)

        if not headers and not files:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        response = self.post_url(url, params, data, files, headers)
        if not response.status_code in valid:
            raise JenkinsAPIException('Operation failed. url={0}, data={1}, headers={2}, status={3}, text={4}'.format(
                response.url, data, headers, response.status_code, response.text.encode('UTF-8')))
        return response

    def get_and_confirm_status(self, url, params=None, headers=None, valid=None):
        valid = valid or self.VALID_STATUS_CODES
        response = self.get_url(url, params, headers)
        if not response.status_code in valid:
            raise JenkinsAPIException('Operation failed. url={0}, headers={1}, status={2}, text={3}'.format(
                response.url, headers, response.status_code, response.text.encode('UTF-8')))
        return response
