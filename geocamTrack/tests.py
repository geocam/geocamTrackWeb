# __BEGIN_LICENSE__
#Copyright © 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
#
#The xGDS platform is licensed under the Apache License, Version 2.0 
#(the "License"); you may not use this file except in compliance with the License. 
#You may obtain a copy of the License at 
#http://www.apache.org/licenses/LICENSE-2.0.
#
#Unless required by applicable law or agreed to in writing, software distributed 
#under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
#CONDITIONS OF ANY KIND, either express or implied. See the License for the 
#specific language governing permissions and limitations under the License.
# __END_LICENSE__

"""
Test geocamTrack.
"""

import os
import logging
import tempfile

from django.test import TestCase
from django.core.urlresolvers import reverse

try:
    import pykml
    from pykml import parser as kmlparser
    import lxml.etree
except ImportError:
    pykml = None


class TestGeocamTrackViews(TestCase):
    def assertKmlValid(self, response):
        self.assertEqual(response.status_code, 200)
        self.assert_(response['Content-Type'].startswith('application/vnd.google-earth.kml+xml'))
        if 0 and pykml:
            # real validation against KML schema -- disabled for now because it seems to reject
            # some valid kml files.
            doc = kmlparser.fromstring(response.content)
            schema = kmlparser.Schema("kml22gx.xsd")
            try:
                schema.assertValid(doc)
            except lxml.etree.DocumentInvalid:
                fd, path = tempfile.mkstemp('-TestGeocamTrackViews.kml')
                with os.fdopen(fd, 'w') as f:
                    f.write(response.content)
                logging.warning('kml contents written to %s for debugging', path)
                raise
        else:
            # superficial check that it looks like KML
            self.assert_(response.content.startswith('<?xml'))
            self.assert_('<kml' in response.content)
            self.assert_('</kml>' in response.content)

    def test_index(self):
        response = self.client.get(reverse('geocamTrack_index'))
        self.assertEqual(response.status_code, 200)

    def test_tracks(self):
        response = self.client.get(reverse('geocamTrack_tracks'))
        self.assertKmlValid(response)

    def test_recentTracks(self):
        response = self.client.get(reverse('geocamTrack_recentTracks'))
        self.assertKmlValid(response)

    def test_cachedTracks(self):
        response = self.client.get(reverse('geocamTrack_cachedTracks'))
        self.assertKmlValid(response)

    def test_trackIndex(self):
        response = self.client.get(reverse('geocamTrack_trackIndex'))
        self.assertKmlValid(response)

    def test_csvTrackIndex(self):
        response = self.client.get(reverse('geocamTrack_csvTrackIndex'))
        self.assertEqual(response.status_code, 200)

    # this test won't work until we have a test fixture
    #def test_trackCsv(self):
    #    response = self.client.get(reverse('geocamTrack_trackCsv',
    #                                       args=['test.csv']),
    #                               {'track': 'test'})
    #    self.assertEqual(response.status_code, 200)
