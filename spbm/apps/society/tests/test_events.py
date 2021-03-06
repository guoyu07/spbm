from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from spbm.helpers.auth import user_society
from . import test_fixtures
from ..models import Event, Society
from ...accounts.models import SpfUser


class EventLoggedInWithPermissionsTests(TestCase):
    fixtures = test_fixtures
    HTTP_OK = 200

    @classmethod
    def setUpTestData(cls):
        # Some useful helpers for validating
        cls.last_event = Event.objects.last()
        cls.magic_event = {
            'name': "Magical Test Event",
            'date': "2017-01-25",
            'shifts-0-worker': 1,
            'shifts-0-wage': 168.00,
            'shifts-0-hours': 4,
            'shifts-1-worker': 2,
            'shifts-1-wage': 128.00,
            'shifts-1-hours': 8,
            'shifts-TOTAL_FORMS': 2,
            'shifts-MIN_NUM_FORMS': 1,
            'shifts-INITIAL_FORMS': 0
        }
        cls.society_id = 1

    def setUp(self):
        # Create the user and add the needed permissions
        self.user = User(username='kungfury')
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename='add_event'),
                                       Permission.objects.get(codename='change_event'))

        # set him as part of a society, then force login
        self.spf_user = SpfUser(user=self.user, society=Society.objects.get(pk=self.society_id))
        self.spf_user.save()
        self.client.force_login(self.user)

    def test_index(self):
        """
        Test the events index page returns a 200 with a short list of processed events.
        NOTE: Depends heavily on the fixtures.
        """
        self.assertTrue(Event.objects.filter(society=self.user.spfuser.society).count() != 0,
                        "No events loaded for the view")
        events_index = self.client.get(reverse('events'), follow=True)
        self.assertEqual(events_index.status_code, self.HTTP_OK)
        self.assertEqual(len(events_index.context['events']), 3)

    def test_can_access_logged_in(self):
        """
        Test that we can access these pages being logged in.
        """
        for view in ['events', 'event-add']:
            with self.subTest(msg=view):
                self.assertEqual(self.client.get(reverse(view), follow=True).status_code, self.HTTP_OK,
                                 "Incorrect HTTP response given!")

    def test_can_add_two_workers_event(self):
        """
        Test that we can add an event with two workers.
        """
        event_data = dict(self.magic_event)

        adding_event = self.client.post(reverse('event-add'), event_data, follow=True)
        self.assertEqual(adding_event.status_code, self.HTTP_OK)
        last_event = Event.objects.last()
        self.assertNotEqual(self.last_event, last_event, "event not added")
        self.assertEqual(last_event, adding_event.context['event'])
        self.assertEqual(last_event.shifts.count(), 2)

    def test_can_add_single_worker_event(self):
        """
        Test that we can add an event with one worker.
        """
        event_data = dict(self.magic_event)
        [event_data.pop(key, None) for key in ['shifts-1-worker', 'shifts-1-wage', 'shifts-1-hours']]
        event_data['shifts-TOTAL_FORMS'] = 1

        adding_event = self.client.post(reverse('event-add'), event_data, follow=True)
        self.assertEqual(adding_event.status_code, self.HTTP_OK)
        last_event = Event.objects.last()
        self.assertNotEqual(self.last_event, last_event, "event not added")
        self.assertEqual(last_event, adding_event.context['event'])
        self.assertEqual(last_event.shifts.count(), 1)

    def test_add_fail_on_duplicate_worker(self):
        """
        Test that we fail when adding a worker twice to an event.
        """
        event_data = {
            'name': "Magical Test Event",
            'date': "2017-01-25",
            'shifts-0-worker': 1,
            'shifts-0-wage': 128.00,
            'shifts-0-hours': 8,
            'shifts-1-worker': 1,
            'shifts-1-wage': 128.00,
            'shifts-1-hours': 8,
            'shifts-TOTAL_FORMS': 2,
            'shifts-MIN_NUM_FORMS': 1,
            'shifts-INITIAL_FORMS': 0
        }
        added_event = self.client.post(reverse('event-add'), event_data, follow=True)
        self.assertTrue(added_event.context['inlines'][0].non_form_errors())
        self.assertEqual(Event.objects.last(), self.last_event)

    def test_add_fail_on_zero_hours(self):
        """
        Test that we fail when trying to send in data that is invalid.
        """
        event_data = dict(self.magic_event)
        # we make it zero hours, which is invalid
        event_data['shifts-0-hours'] = 0

        added_event = self.client.post(reverse('event-add'), event_data, follow=True)
        self.assertFalse(added_event.context['inlines'][0].is_valid())
        self.assertEqual(Event.objects.last(), self.last_event)


class EventAdminTests(TestCase):
    fixtures = test_fixtures

    def setUp(self):
        self.user = User(username='the_admin', is_staff=True)
        self.user.save()
        self.user.user_permissions.add(Permission.objects.get(codename='add_event'),
                                       Permission.objects.get(codename='change_event'))

        # set him as part of a society, then force login
        self.spf_user = SpfUser(user=self.user, society=Society.objects.get(pk=1))
        self.spf_user.save()
        self.client.force_login(self.user)

    def test_view_processed_event(self):
        """
        We can access the change page of an processed event.
        """
        e = Event.objects.filter(processed__isnull=False).first()
        response = self.client.get(reverse('admin:society_event_change', args=(e.id,)))
        self.assertTrue(response.status_code, 200)

    def test_view_unprocessed_event(self):
        """
        We can access the change page of an unprocessed event.
        """
        e = Event.objects.filter(processed__isnull=True).first()
        response = self.client.get(reverse('admin:society_event_change', args=(e.id,)))
        self.assertTrue(response.status_code, 200)

    def test_update_shift_processed_event(self):
        """
        We can update the hours of the shift object of an event that is processed.
        """
        e = Event.objects.first()
        self.assertTrue(e.shifts.first().hours != 8, "Hours from testdata is incorrect")
        event_data = {
            'name': e.name,
            'date': e.date,
            'society': e.society.id,
            'shifts-0-id': 1,
            'shifts-0-event': 1,
            'shifts-0-worker': 1,
            'shifts-0-wage': 300,
            'shifts-0-hours': 8,
            'shifts-TOTAL_FORMS': 1,
            'shifts-MIN_NUM_FORMS': 0,
            'shifts-INITIAL_FORMS': 1
        }
        response = self.client.post(reverse('admin:society_event_change', args=(e.id,)), event_data, follow=True)
        self.assertTrue(response.status_code, 200)
        self.assertEqual(Event.objects.get(pk=e.id).hours, event_data['shifts-0-hours'])


class EventLoggedOutTests(TestCase):
    def test_cannot_access_logged_out(self):
        """
        Verify that endpoints cannot be accessed while logged out.
        In other words, verify that they forward to the login screen.
        """
        from ..urls import event_urls
        for view in event_urls:
            from django.urls import NoReverseMatch
            try:
                response = self.client.get(reverse(view.name))
            except NoReverseMatch:
                # Better way to try views with a single parameter?
                response = self.client.get(reverse(view.name, args=[1]))
            self.assertEqual(response.status_code,
                             302,
                             "Did not receive expected HTTP UNAUTHORIZED")
            self.assertTrue("/accounts/login" in response.url)
