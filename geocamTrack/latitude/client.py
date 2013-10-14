# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import oauth2 as oauth
import urllib
import httplib2

from geocamUtil import anyjson as json

RESOURCE_URL_PREFIX = "https://www.googleapis.com/latitude/v1/"


class LatitudeClient(object):
    class LatitudeError(Exception):
        pass

    class ServerNotFoundError(LatitudeError):
        pass

    class HttpError(LatitudeError):
        def __init__(self, response):
            super(HttpError, self).__init__()  # pylint: disable=E0602
            self.response = response

        def __str__(self):
            return 'HTTP error %s' % self.response['status']

    class ApiError(LatitudeError):
        def __init__(self, contentJson):
            super(ApiError, self).__init__()  # pylint: disable=E0602
            self.contentJson = contentJson

        def __str__(self):
            return 'Google Latitude API error %s' % json.dumps(self.contentJson['error'])

    def __init__(self, consumerKey, consumerSecret, accessToken, accessSecret):
        self._consumerKey = consumerKey
        self._consumerSecret = consumerSecret
        self._accessToken = accessToken
        self._accessSecret = accessSecret

    def _invoke(self, path, params=None):
        resource_url = RESOURCE_URL_PREFIX + path.lstrip('/')

        consumer = oauth.Consumer(self._consumerKey, self._consumerSecret)
        token = oauth.Token(self._accessToken, self._accessSecret)
        oauth_request = oauth.Request.from_consumer_and_token(consumer, token, 'GET', resource_url, params)
        oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)

        headers = {}
        headers.update(oauth_request.to_header())
        headers['user-agent'] = 'python-latitude'
        headers['content-type'] = 'application/json; charset=UTF-8'

        if params:
            resource_url = "%s?%s" % (resource_url, urllib.urlencode(params))

        h = httplib2.Http()
        try:
            response, content = h.request(resource_url, method='GET', headers=headers)
        except httplib2.ServerNotFoundError, e:
            raise self.ServerNotFoundError(str(e))

        if response['status'] != '200':
            raise self.HttpError(response)

        contentJson = json.loads(content)
        if 'error' in contentJson:
            raise self.ApiError(contentJson)

        return contentJson

    def getCurrentLocation(self):
        return self._invoke("/currentLocation", {'granularity': 'best'})

    def getLocationList(self, params=None):
        """
        Available parameters: minTime, maxTime, maxResults.  minTime and maxTime are
        expressed as milliseconds since UNIX epoch (like a Java timestamp).
        """

        if params is None:
            params = {}

        # map from python-friendly param names to the names used by the latitude api
        NAME_MAPPING = (('minTime', 'min-time'),
                        ('maxTime', 'max-time'),
                        ('maxResults', 'max-results'))
        for pyName, latName in NAME_MAPPING:
            if pyName in params:
                params[latName] = params[pyName]
                del params[pyName]

        useParams = {'granularity': 'best'}
        useParams.update(params)

        return self._invoke("/location", useParams)
