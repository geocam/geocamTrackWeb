# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

"""
Test geocamTrack.
"""

from django.test import TestCase
from django.core.urlresolvers import reverse

try:
    import pykml
    from pykml import parser as kmlparser
except ImportError:
    pykml = None


class TestGeocamTrackViews(TestCase):
    def assertKmlValid(self, response):
        self.assertEqual(response.status_code, 200)
        self.assert_(response['Content-Type'].startswith('application/vnd.google-earth.kml+xml'))
        if pykml:
            # real validation against KML schema
            doc = kmlparser.fromstring(response.content)
            schema = kmlparser.Schema("kml22gx.xsd")
            schema.assertValid(doc)
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
