"""
Module for JenkinsBase class
"""

import logging
from jenkinsapi import config
from jenkinsapi.custom_exceptions import JenkinsAPIException
log = logging.getLogger(__name__)


class JenkinsBase(object):
    """
    This appears to be the base object that all other jenkins objects are inherited from
    """
    RETRY_ATTEMPTS = 1

    def __repr__(self):
        return """<%s.%s %s>""" % (self.__class__.__module__,
                                   self.__class__.__name__,
                                   str(self))

    def __str__(self):
        raise NotImplementedError

    def __init__(self, baseurl, poll=True):
        """
        Initialize a jenkins connection
        """
        self._data = None
        self.baseurl = self.strip_trailing_slash(baseurl)
        if poll:
            self.poll()

    def get_jenkins_obj(self):
        raise NotImplementedError('Please implement this method on %s' % self.__class__.__name__)

    def __eq__(self, other):
        """
        Return true if the other object represents a connection to the same server
        """
        if not isinstance(other, self.__class__):
            return False
        return other.baseurl == self.baseurl

    @classmethod
    def strip_trailing_slash(cls, url):
        return url.rstrip('/')

    def poll(self):
        self._data = self._poll()

    def _poll(self):
        url = self.python_api_url(self.baseurl)
        return self.get_data(url)

    def get_data(self, url, params=None):
        requester = self.get_jenkins_obj().requester
        response = requester.get_url(url, params)
        try:
            return eval(response.text)
        except Exception:
            log.exception('Inappropriate content found at %s', url)
            raise JenkinsAPIException('Cannot parse %s' % response.content)

    @classmethod
    def python_api_url(cls, url):
        if url.endswith(config.JENKINS_API):
            return url
        else:
            return "%s/%s" % (url.rstrip("/"), config.JENKINS_API)
