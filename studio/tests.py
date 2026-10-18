import io
import json
import shutil
import tempfile
from datetime import datetime, time, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from . import instagram, scheduler
from .media import save_upload
from .models import InstagramAccount, MediaAsset, Membership, MusicTrack, Post, QueueSettings, RecurringRule, next_occurrence

TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(LANGUAGE_CODE="en")
class TestCase(DjangoTestCase):
    """Most tests check English wording; Greek (the default for users) is covered by GreekTests."""


def image_upload(name="photo.png", size=(800, 1000)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "purple").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def video_upload(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code, self.text = data, status, str(data)

    def json(self):
        return self._data


class FakeGraph:
    """Stands in for requests.get/post against the Instagram Graph API and records calls."""

    def __init__(self):
        self.created = []
        self.published = []
        self.status_checks = 0
        self.processing_checks = 0  # how many status checks report IN_PROGRESS before FINISHED
        self.private_users = set()  # usernames Instagram refuses to tag (code 110)
        self.profile = {"user_id": "17841", "username": "lineofdance", "account_type": "BUSINESS",
                        "profile_picture_url": "https://cdn.example.com/p.jpg"}
        self._n = 0

    def post(self, url, data=None, **kwargs):
        if url.endswith("/media"):
            blocked = [t["username"] for t in json.loads(data.get("user_tags", "[]")) if t["username"] in self.private_users]
            if blocked:
                return FakeResponse({"error": {"code": 110, "message": "The following user(s) cannot be accessed: "
                                               + ", ".join(blocked)}}, status=400)
            self._n += 1
            self.created.append(data)
            return FakeResponse({"id": f"c{self._n}"})
        if url.endswith("/media_publish"):
            self.published.append(data["creation_id"])
            return FakeResponse({"id": "m1"})
        raise AssertionError(url)

    def get(self, url, params=None, **kwargs):
        if "fields" in (params or {}) and "status_code" in params["fields"]:
            self.status_checks += 1
            if self.status_checks <= self.processing_checks:
                return FakeResponse({"status_code": "IN_PROGRESS"})
            return FakeResponse({"status_code": "FINISHED"})
        if "permalink" in (params or {}).get("fields", ""):
            return FakeResponse({"permalink": "https://instagram.com/p/abc"})
        if url.endswith("/me"):
            if params.get("access_token", "").startswith("bad"):
                return FakeResponse({"error": {"message": "Invalid OAuth access token", "code": 190}}, status=400)
            return FakeResponse(self.profile)
        if url.endswith("/content_publishing_limit"):
            return FakeResponse({"data": [{"quota_usage": 3, "config": {"quota_total": 100}}]})
        if "refresh_access_token" in url:
            return FakeResponse({"access_token": "new", "expires_in": 5184000})
        raise AssertionError(url)


@override_settings(MEDIA_ROOT=TEMP_MEDIA, SITE_URL="https://studio.example.com", TIME_ZONE="Europe/Athens")
class BaseTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("staff", email="staff@example.com", password="pw-123456!")
        Membership.objects.create(user=self.user, role=Membership.OWNER, approved=True)
        InstagramAccount.objects.create(
            ig_user_id="17841", username="studio", access_token="tok",
            token_expires_at=timezone.now() + timedelta(days=50),
        )
        self.graph = FakeGraph()
        patcher_post = mock.patch.object(instagram.requests, "post", side_effect=self.graph.post)
        patcher_get = mock.patch.object(instagram.requests, "get", side_effect=self.graph.get)
        patcher_post.start()
        patcher_get.start()
        self.addCleanup(patcher_post.stop)
        self.addCleanup(patcher_get.stop)

    def make_post(self, post_type, assets, **kwargs):
        post = Post.objects.create(post_type=post_type, caption="Hello", status=Post.SCHEDULED,
                                   scheduled_at=timezone.now() - timedelta(seconds=1), **kwargs)
        post.set_media(assets)
        return post


class ScheduleMathTests(TestCase):
    @override_settings(TIME_ZONE="Europe/Athens")
    def test_next_occurrence_picks_next_matching_weekday_and_time(self):
        monday_10 = timezone.make_aware(datetime(2026, 10, 12, 10, 0))  # a Monday
        result = next_occurrence([0, 3], [time(9, 0), time(18, 0)], monday_10)
        self.assertEqual(timezone.localtime(result).replace(tzinfo=None), datetime(2026, 10, 12, 18, 0))
        after_last = timezone.make_aware(datetime(2026, 10, 12, 18, 0))
        result = next_occurrence([0, 3], [time(9, 0), time(18, 0)], after_last)
        self.assertEqual(timezone.localtime(result).replace(tzinfo=None), datetime(2026, 10, 15, 9, 0))

    def test_no_days_means_never(self):
        self.assertIsNone(next_occurrence([], [time(9)]))


class UploadTests(BaseTest):
    def test_png_is_converted_to_jpeg(self):
        asset = save_upload(image_upload())
        self.assertEqual(asset.kind, MediaAsset.IMAGE)
        self.assertTrue(asset.file.name.endswith(".jpg"))
        self.assertEqual((asset.width, asset.height), (800, 1000))

    def test_tall_photo_gets_padded_copy_for_feed(self):
        from .media import feed_ready_url
        asset = save_upload(image_upload(size=(500, 1000)))
        url = feed_ready_url(asset)
        self.assertTrue(url.endswith("_feed.jpg"))
        path = TEMP_MEDIA + url.split("/media", 1)[1]
        with Image.open(path) as padded:
            self.assertAlmostEqual(padded.width / padded.height, 0.8, places=2)


class PublishTests(BaseTest):
    def test_link_is_appended_to_caption_on_instagram(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())], link="https://lineofdance.gr/summer")
        scheduler.publish_due_posts()
        self.assertEqual(self.graph.created[0]["caption"], "Hello\n\n🔗 lineofdance.gr/summer")

    def test_link_section_after_hash_is_never_turned_into_a_hashtag(self):
        self.make_post(Post.FEED, [save_upload(image_upload())], link="https://lineofdance.gr/epikoinonia.php#interest")
        scheduler.publish_due_posts()
        self.assertEqual(self.graph.created[0]["caption"], "Hello\n\n🔗 lineofdance.gr/epikoinonia.php")

    def test_photo_post(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())])
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED, post.error)
        self.assertEqual(post.permalink, "https://instagram.com/p/abc")
        self.assertTrue(self.graph.created[0]["image_url"].startswith("https://studio.example.com/media/"))
        self.assertEqual(self.graph.created[0]["caption"], "Hello")

    def test_carousel_creates_children_then_parent(self):
        assets = [save_upload(image_upload()), save_upload(video_upload())]
        post = self.make_post(Post.CAROUSEL, assets)
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED, post.error)
        self.assertEqual(self.graph.created[0]["is_carousel_item"], "true")
        self.assertEqual(self.graph.created[1]["media_type"], "VIDEO")
        self.assertEqual(self.graph.created[2]["media_type"], "CAROUSEL")
        self.assertEqual(self.graph.created[2]["children"], "c1,c2")

    def test_reel_and_story(self):
        reel = self.make_post(Post.REEL, [save_upload(video_upload())])
        story = self.make_post(Post.STORY, [save_upload(image_upload())])
        scheduler.publish_due_posts()
        reel.refresh_from_db()
        story.refresh_from_db()
        self.assertEqual((reel.status, story.status), (Post.PUBLISHED, Post.PUBLISHED))
        types = [c.get("media_type") for c in self.graph.created]
        self.assertIn("REELS", types)
        self.assertIn("STORIES", types)

    def test_tagged_people_are_sent_to_instagram(self):
        self.make_post(Post.FEED, [save_upload(image_upload())], user_tags="maria_dance john.s")
        self.make_post(Post.REEL, [save_upload(video_upload())], user_tags="maria_dance")
        scheduler.publish_due_posts()
        photo_tags = json.loads(self.graph.created[0]["user_tags"])
        self.assertEqual([t["username"] for t in photo_tags], ["maria_dance", "john.s"])
        self.assertTrue(all(0 <= t["x"] <= 1 and 0 <= t["y"] <= 1 for t in photo_tags))
        self.assertEqual(json.loads(self.graph.created[1]["user_tags"]), [{"username": "maria_dance"}])

    def test_collab_post_invites_collaborators(self):
        self.make_post(Post.FEED, [save_upload(image_upload())], collaborators="anna john")
        self.make_post(Post.CAROUSEL, [save_upload(image_upload()), save_upload(image_upload())], collaborators="anna")
        story = self.make_post(Post.STORY, [save_upload(image_upload())], collaborators="anna")
        scheduler.publish_due_posts()
        self.assertEqual(json.loads(self.graph.created[0]["collaborators"]), ["anna", "john"])
        self.assertNotIn("collaborators", self.graph.created[1])  # carousel slide
        self.assertEqual(json.loads(self.graph.created[3]["collaborators"]), ["anna"])  # carousel itself
        story.refresh_from_db()
        self.assertEqual(story.status, Post.FAILED)

    def test_private_accounts_are_skipped_and_the_post_still_publishes(self):
        self.graph.private_users = {"_.private", "peggy"}
        post = self.make_post(Post.FEED, [save_upload(image_upload())], user_tags="maria _.private peggy")
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED, post.error)
        self.assertEqual([t["username"] for t in json.loads(self.graph.created[0]["user_tags"])], ["maria"])
        self.assertEqual(post.user_tags, "maria")
        self.assertEqual(post.publish_state["untagged"], ["_.private", "peggy"])
        self.client.login(username="staff", password="pw-123456!")
        self.assertContains(self.client.get(reverse("post_list")), "peggy")

    def test_tags_go_on_first_carousel_slide_and_stories_refuse_them(self):
        self.make_post(Post.CAROUSEL, [save_upload(image_upload()), save_upload(image_upload())], user_tags="maria")
        story = self.make_post(Post.STORY, [save_upload(image_upload())], user_tags="maria")
        scheduler.publish_due_posts()
        self.assertIn("user_tags", self.graph.created[0])
        self.assertNotIn("user_tags", self.graph.created[1])
        self.assertNotIn("user_tags", self.graph.created[2])
        story.refresh_from_db()
        self.assertEqual(story.status, Post.FAILED)

    def test_invalid_post_fails_with_message(self):
        post = self.make_post(Post.REEL, [save_upload(image_upload())])
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.FAILED)
        self.assertIn("Reel needs exactly one video", post.error)

    def test_api_error_marks_post_failed(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())])
        error = FakeResponse({"error": {"message": "Media download failed", "code": 9004}}, status=400)
        with mock.patch.object(instagram.requests, "post", return_value=error):
            scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.FAILED)
        self.assertIn("Media download failed", post.error)

    def test_future_and_draft_posts_are_left_alone(self):
        future = self.make_post(Post.FEED, [save_upload(image_upload())])
        future.scheduled_at = timezone.now() + timedelta(hours=1)
        future.save()
        draft = self.make_post(Post.FEED, [save_upload(image_upload())])
        Post.objects.filter(pk=draft.pk).update(status=Post.DRAFT)
        scheduler.publish_due_posts()
        self.assertEqual(self.graph.published, [])

    def test_post_locked_by_another_run_is_left_alone(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())])
        Post.objects.filter(pk=post.pk).update(
            status=Post.PUBLISHING, publish_started_at=timezone.now(), locked_until=timezone.now() + timedelta(minutes=1),
        )
        scheduler.publish_due_posts()
        self.assertEqual(self.graph.published, [])

    def test_slow_video_is_finished_by_a_later_run(self):
        self.graph.processing_checks = 5
        post = self.make_post(Post.REEL, [save_upload(video_upload())])
        with mock.patch.object(scheduler.time, "sleep"):
            summary = scheduler.publish_due_posts(budget_seconds=0)
        post.refresh_from_db()
        self.assertEqual((summary["waiting"], post.status), (1, Post.PUBLISHING))
        self.assertIn("container", post.publish_state)
        self.assertEqual(len(self.graph.created), 1)
        with mock.patch.object(scheduler.time, "sleep"):
            scheduler.publish_due_posts(budget_seconds=60)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED, post.error)
        self.assertEqual(len(self.graph.created), 1)  # the container was reused, not created again
        self.assertEqual(self.graph.published, ["c1"])

    def test_carousel_waits_for_children_before_creating_parent(self):
        self.graph.processing_checks = 1
        post = self.make_post(Post.CAROUSEL, [save_upload(image_upload()), save_upload(video_upload())])
        scheduler.publish_due_posts(budget_seconds=0)
        post.refresh_from_db()
        self.assertEqual(len(post.publish_state["children"]), 2)
        self.assertNotIn("container", post.publish_state)
        scheduler.publish_due_posts(budget_seconds=0)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED, post.error)

    def test_publishing_that_never_finishes_times_out(self):
        post = self.make_post(Post.REEL, [save_upload(video_upload())])
        Post.objects.filter(pk=post.pk).update(
            status=Post.PUBLISHING, publish_started_at=timezone.now() - timedelta(hours=1),
        )
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual(post.status, Post.FAILED)

    def test_already_published_post_is_never_published_again(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())])
        Post.objects.filter(pk=post.pk).update(
            status=Post.PUBLISHING, publish_started_at=timezone.now(), publish_state={"container": "c9", "media_id": "m9"},
        )
        scheduler.publish_due_posts()
        post.refresh_from_db()
        self.assertEqual((post.status, post.ig_media_id), (Post.PUBLISHED, "m9"))
        self.assertEqual(self.graph.published, [])


class AutomationTests(BaseTest):
    def test_recurring_rule_creates_and_publishes_post(self):
        asset = save_upload(image_upload())
        rule = RecurringRule.objects.create(
            name="Timetable", post_type=Post.FEED, caption="Classes for {weekday}!",
            weekdays="0,1,2,3,4,5,6", times="09:00", next_run_at=timezone.now() - timedelta(minutes=1),
        )
        rule.media.set([asset])
        scheduler.tick()
        post = Post.objects.get(recurring_rule=rule)
        self.assertEqual(post.status, Post.PUBLISHED, post.error)
        self.assertTrue(post.caption.startswith("Classes for "))
        rule.refresh_from_db()
        self.assertGreater(rule.next_run_at, timezone.now())
        scheduler.tick()  # same run must not fire twice
        self.assertEqual(Post.objects.filter(recurring_rule=rule).count(), 1)

    def test_long_missed_run_is_skipped(self):
        rule = RecurringRule.objects.create(
            name="Old", post_type=Post.FEED, weekdays="0,1,2,3,4,5,6", times="09:00",
            next_run_at=timezone.now() - timedelta(days=2),
        )
        scheduler.run_recurring_rules()
        self.assertFalse(Post.objects.filter(recurring_rule=rule).exists())

    def test_queue_posts_least_used_item_with_its_caption(self):
        first = save_upload(image_upload())
        first.in_queue, first.caption = True, "From the queue"
        first.save()
        video = save_upload(video_upload())
        video.in_queue, video.times_used = True, 0
        video.save()
        queue = QueueSettings.load()
        queue.active, queue.caption_mode = True, QueueSettings.CAPTION_DEFAULT
        queue.default_caption = "Default"
        queue.next_run_at = timezone.now() - timedelta(minutes=1)
        queue.save()
        scheduler.run_queue()
        post = Post.objects.get(source="queue")
        self.assertEqual(post.ordered_media, [first])
        self.assertEqual(post.caption, "From the queue")
        first.refresh_from_db()
        self.assertEqual(first.times_used, 1)

        QueueSettings.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
        scheduler.run_queue()
        second = Post.objects.filter(source="queue").latest("id")
        self.assertEqual((second.post_type, second.caption), (Post.REEL, "Default"))

    def test_queue_and_recurring_posts_get_the_tags(self):
        asset = save_upload(image_upload())
        rule = RecurringRule.objects.create(
            name="Timetable", post_type=Post.FEED, weekdays="0,1,2,3,4,5,6", times="09:00",
            next_run_at=timezone.now() - timedelta(minutes=1), user_tags="maria",
        )
        rule.media.set([asset])
        scheduler.run_recurring_rules()
        self.assertEqual(Post.objects.get(source="recurring").user_tags, "maria")
        asset.in_queue = True
        asset.save()
        self._queue(user_tags="john.s")
        scheduler.run_queue()
        self.assertEqual(Post.objects.get(source="queue").user_tags, "john.s")
        self._queue(user_tags="john.s", as_story=True, reuse_items=True)
        scheduler.run_queue()
        self.assertEqual(Post.objects.filter(source="queue").latest("id").user_tags, "")

    def test_queue_settings_clean_tags(self):
        self.client.login(username="staff", password="pw-123456!")
        self.client.post(reverse("queue"), {"active": "on", "weekday_list": ["1"], "times": "18:00",
                                            "timing_mode": "fixed", "window_start": "10:00", "window_end": "21:00",
                                            "posts_per_day": "2", "source": "queue", "caption_mode": "default",
                                            "user_tags": "@Maria, john.s"})
        self.assertEqual(QueueSettings.load().user_tags, "maria john.s")

    def _queue(self, **kwargs):
        queue = QueueSettings.load()
        for k, v in {"active": True, "caption_mode": QueueSettings.CAPTION_DEFAULT, "default_caption": "Hi",
                     "next_run_at": timezone.now() - timedelta(minutes=1), **kwargs}.items():
            setattr(queue, k, v)
        queue.save()
        return queue

    def test_queue_can_post_randomly_from_whole_library(self):
        assets = [save_upload(image_upload()) for _ in range(6)]  # none marked "in queue"
        self._queue(source=QueueSettings.SOURCE_LIBRARY, random_order=True, link="https://www.lineofdance.gr/classes/")
        picked = set()
        for _ in range(6):
            QueueSettings.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
            scheduler.run_queue()
        posts = list(Post.objects.filter(source="queue"))
        self.assertEqual(len(posts), 6)
        picked = {p.ordered_media[0].pk for p in posts}
        self.assertEqual(picked, {a.pk for a in assets})  # each item used once, no repeats
        self.assertTrue(posts[0].full_caption.endswith("🔗 lineofdance.gr/classes"))
        QueueSettings.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
        scheduler.run_queue()
        self.assertEqual(Post.objects.filter(source="queue").count(), 6)  # library used up, reuse off

    def test_random_times_are_spread_inside_the_window_and_change_daily(self):
        from datetime import time as dtime
        queue = QueueSettings.load()
        queue.timing_mode, queue.weekdays = QueueSettings.TIMING_RANDOM, "0,1,2,3,4,5,6"
        queue.window_start, queue.window_end, queue.posts_per_day = dtime(10, 0), dtime(20, 0), 4
        monday_8am = timezone.make_aware(datetime(2026, 10, 12, 8, 0))
        first, planned = queue.plan_after(monday_8am)
        times = [timezone.localtime(datetime.fromisoformat(t)) for t in planned]
        self.assertEqual(len(times), 4)
        self.assertEqual(first, datetime.fromisoformat(planned[0]))
        for i, t in enumerate(times):  # one in each 2.5-hour slice of 10:00-20:00
            self.assertEqual(t.date(), monday_8am.date())
            slice_start = timezone.make_aware(datetime(2026, 10, 12, 10, 0)) + timedelta(minutes=150 * i)
            self.assertTrue(slice_start <= t < slice_start + timedelta(minutes=150), t)
        # after the day's last post, the next day is planned with different times
        queue.planned_runs = planned
        nxt, planned2 = queue.plan_after(times[-1])
        days2 = {timezone.localtime(datetime.fromisoformat(t)).date() for t in planned2}
        self.assertEqual(days2, {monday_8am.date() + timedelta(days=1)})
        self.assertFalse({t.strftime("%H:%M") for t in times} & {
            timezone.localtime(datetime.fromisoformat(t)).strftime("%H:%M") for t in planned2})

    def test_random_times_queue_posts_then_moves_to_next_planned_time(self):
        save_upload(image_upload()); save_upload(image_upload())
        queue = self._queue(source=QueueSettings.SOURCE_LIBRARY, timing_mode=QueueSettings.TIMING_RANDOM,
                            weekdays="0,1,2,3,4,5,6")
        later = timezone.now() + timedelta(hours=2)
        QueueSettings.objects.update(planned_runs=[queue.next_run_at.isoformat(), later.isoformat()])
        scheduler.run_queue()
        queue.refresh_from_db()
        self.assertEqual(Post.objects.filter(source="queue").count(), 1)
        self.assertEqual(queue.next_run_at, later)

    def test_random_mode_form_validates_window(self):
        self.client.login(username="staff", password="pw-123456!")
        base = {"active": "on", "weekday_list": ["0", "2"], "timing_mode": "random", "times": "",
                "source": "library", "caption_mode": "default", "posts_per_day": "3"}
        resp = self.client.post(reverse("queue"), {**base, "window_start": "20:00", "window_end": "10:00"})
        self.assertContains(resp, "must be later")
        resp = self.client.post(reverse("queue"), {**base, "window_start": "10:00", "window_end": "10:30"})
        self.assertContains(resp, "too many for this window")
        resp = self.client.post(reverse("queue"), {**base, "window_start": "10:00", "window_end": "21:00"})
        self.assertRedirects(resp, reverse("queue"))
        queue = QueueSettings.load()
        self.assertEqual((queue.timing_mode, queue.posts_per_day), ("random", 3))
        self.assertTrue(queue.planned_runs)
        self.assertEqual(queue.next_run_at, datetime.fromisoformat(queue.planned_runs[0]))

    def test_every_choice_on_the_settings_pages_is_a_real_clickable_input(self):
        """Regression: choices drawn as buttons must be real radio inputs with a name, or they can't be clicked."""
        import re
        self.client.login(username="staff", password="pw-123456!")
        checks = {"queue": ["timing_mode", "source"], "recurring_new": ["post_type"], "post_new": ["post_type"]}
        for page, names in checks.items():
            html = self.client.get(reverse(page)).content.decode()
            self.assertNotIn("<label><option", html.replace("\n", ""), page)
            for name in names:
                with self.subTest(page=page, field=name):
                    self.assertGreaterEqual(len(re.findall(rf'<input type="radio" name="{name}"', html)), 2)

    def test_queue_form_errors_are_always_visible(self):
        self.client.login(username="staff", password="pw-123456!")
        resp = self.client.post(reverse("queue"), {"active": "on", "weekday_list": ["1"], "times": "18:00",
                                                   "caption_mode": "default"})  # e.g. an old page without "When"
        self.assertContains(resp, "Not saved yet")
        self.assertContains(resp, "When:")

    def test_random_order_with_reuse_prefers_least_used(self):
        a, b = save_upload(image_upload()), save_upload(image_upload())
        MediaAsset.objects.filter(pk=a.pk).update(times_used=3)
        MediaAsset.objects.filter(pk=b.pk).update(times_used=1)
        queue = self._queue(source=QueueSettings.SOURCE_LIBRARY, random_order=True, reuse_items=True)
        for _ in range(5):
            self.assertEqual(queue.next_asset().pk, b.pk)

    def test_expiring_token_is_refreshed(self):
        InstagramAccount.objects.update(token_expires_at=timezone.now() + timedelta(days=2),
                                        token_obtained_at=timezone.now() - timedelta(days=58))
        scheduler.refresh_token_if_needed()
        self.assertEqual(InstagramAccount.current().access_token, "new")


class ViewTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.login(username="staff", password="pw-123456!")

    def test_pages_render(self):
        for name in ["dashboard", "post_list", "post_new", "media_list", "recurring_list", "recurring_new", "queue",
                     "instagram", "team", "account_email"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_schedule_post_with_new_upload(self):
        when = (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        resp = self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "Recital!", "scheduled_at": when, "action": "schedule",
            "media_ids": "", "new_files": image_upload(), "share_reel_to_feed": "on",
        })
        self.assertRedirects(resp, reverse("post_list"))
        post = Post.objects.get()
        self.assertEqual(post.status, Post.SCHEDULED)
        self.assertEqual(len(post.ordered_media), 1)

    def test_carousel_with_one_item_is_rejected(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("post_new"), {
            "post_type": "carousel", "caption": "x", "action": "now", "media_ids": str(asset.pk),
        })
        self.assertContains(resp, "between 2 and 10")
        self.assertFalse(Post.objects.exists())

    def test_tagged_usernames_are_cleaned_when_saving(self):
        asset = save_upload(image_upload())
        self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "x", "action": "draft", "media_ids": str(asset.pk),
            "user_tags": "@Maria_Dance, john.s  https://instagram.com/eleni/ @maria_dance",
        })
        self.assertEqual(Post.objects.get().user_tags, "maria_dance john.s eleni")
        resp = self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "x", "action": "draft", "media_ids": str(asset.pk),
            "user_tags": "not-valid!",
        })
        self.assertContains(resp, "valid Instagram username")

    def test_at_most_three_collaborators(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "x", "action": "draft", "media_ids": str(asset.pk),
            "collaborators": "@Anna, b, c, d",
        })
        self.assertContains(resp, "at most 3 collaborators")
        self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "x", "action": "draft", "media_ids": str(asset.pk),
            "collaborators": "@Anna, instagram.com/john/",
        })
        self.assertEqual(Post.objects.get().collaborators, "anna john")

    def test_link_with_hash_is_trimmed_when_saving(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "x", "action": "draft", "media_ids": str(asset.pk),
            "link": "lineofdance.gr/epikoinonia.php#interest",
        }, follow=True)
        self.assertEqual(Post.objects.get().link, "lineofdance.gr/epikoinonia.php")
        self.assertContains(resp, "turns it into a hashtag")

    def test_carousel_order_follows_selection(self):
        a, b = save_upload(image_upload()), save_upload(image_upload())
        self.client.post(reverse("post_new"), {
            "post_type": "carousel", "caption": "x", "action": "draft", "media_ids": f"{b.pk},{a.pk}",
        })
        self.assertEqual(Post.objects.get().ordered_media, [b, a])

    def test_recurring_rule_form_sets_next_run(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("recurring_new"), {
            "name": "Timetable", "active": "on", "post_type": "feed", "weekday_list": ["0", "3"],
            "times": "9:00, 18:30", "caption": "Week ahead", "media": [asset.pk],
        })
        self.assertRedirects(resp, reverse("recurring_list"))
        rule = RecurringRule.objects.get()
        self.assertEqual((rule.weekdays, rule.times), ("0,3", "09:00,18:30"))
        self.assertIsNotNone(rule.next_run_at)

    @override_settings(ANTHROPIC_API_KEY="")
    def test_ai_captions_report_when_not_configured(self):
        resp = self.client.post(reverse("caption_suggestions"), {"brief": "Summer intensive"})
        self.assertEqual(resp.status_code, 502)
        self.assertIn("ANTHROPIC_API_KEY", resp.json()["error"])

    @override_settings(ANTHROPIC_API_KEY="sk-test")
    def test_ai_captions_parse_structured_output(self):
        fake = mock.Mock(stop_reason="end_turn", content=[mock.Mock(type="text", text='{"captions": ["One", "Two"]}')])
        with mock.patch("studio.ai.anthropic.Anthropic") as client_cls:
            client_cls.return_value.beta.messages.create.return_value = fake
            asset = save_upload(image_upload())
            resp = self.client.post(reverse("caption_suggestions"), {"brief": "Recital", "media_ids": str(asset.pk)})
        self.assertEqual(resp.json(), {"captions": ["One", "Two"]})
        kwargs = client_cls.return_value.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["messages"][0]["content"][0]["type"], "image")


@override_settings(OWNER_EMAILS=set())
class AccountTests(TestCase):
    password = "Dance-floor-2026!"

    def signup(self, email):
        return self.client.post(reverse("account_signup"), {
            "email": email, "password1": self.password, "password2": self.password,
        })

    def test_first_signup_becomes_owner_and_next_waits_for_approval(self):
        self.signup("owner@studio.gr")
        owner = User.objects.get(email="owner@studio.gr")
        self.assertTrue(owner.membership.is_owner)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

        self.client.logout()
        self.signup("teacher@gmail.com")
        teacher = User.objects.get(email="teacher@gmail.com")
        self.assertFalse(teacher.membership.approved)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("pending"))
        self.assertRedirects(self.client.get(reverse("post_new")), reverse("pending"))
        self.assertEqual(self.client.get(reverse("pending")).status_code, 200)

        self.client.force_login(owner)
        self.assertContains(self.client.get(reverse("team")), "teacher@gmail.com")
        self.client.post(reverse("team_update", args=[teacher.membership.pk]), {"action": "approve", "role": "editor"})
        teacher.membership.refresh_from_db()
        self.assertTrue(teacher.membership.approved)
        self.assertEqual(teacher.membership.role, Membership.EDITOR)

    @override_settings(OWNER_EMAILS={"boss@studio.gr"})
    def test_owner_emails_setting(self):
        self.signup("stranger@example.com")
        self.assertFalse(User.objects.get(email="stranger@example.com").membership.approved)
        self.client.logout()
        self.signup("Boss@studio.gr")
        self.assertTrue(User.objects.get(email__iexact="boss@studio.gr").membership.is_owner)

    def test_owner_is_emailed_about_new_signup(self):
        from django.core import mail
        self.signup("owner@studio.gr")
        self.client.logout()
        self.signup("new@example.com")
        alerts = [m for m in mail.outbox if "wants access" in m.subject]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].to, ["owner@studio.gr"])
        self.assertIn("new@example.com", alerts[0].body)

    def test_editor_cannot_use_owner_pages(self):
        editor = User.objects.create_user("ed", email="ed@example.com")
        Membership.objects.create(user=editor, role=Membership.EDITOR, approved=True)
        self.client.force_login(editor)
        for name in ["instagram", "team", "recurring_new"]:
            with self.subTest(page=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse("dashboard"))
        self.client.post(reverse("queue"), {"active": "on", "weekday_list": ["0"], "times": "10:00",
                                            "caption_mode": "default"})
        self.assertFalse(QueueSettings.load().active)
        self.assertEqual(self.client.get(reverse("post_new")).status_code, 200)

    def test_last_owner_cannot_be_removed_or_demoted(self):
        a = User.objects.create_user("a", email="a@example.com")
        b = User.objects.create_user("b", email="b@example.com")
        ma = Membership.objects.create(user=a, role=Membership.OWNER, approved=True)
        mb = Membership.objects.create(user=b, role=Membership.OWNER, approved=True)
        self.client.force_login(a)
        self.client.post(reverse("team_update", args=[mb.pk]), {"action": "role", "role": "editor"})
        mb.refresh_from_db()
        self.assertEqual(mb.role, Membership.EDITOR)  # fine: a is still an owner
        self.client.post(reverse("team_update", args=[ma.pk]), {"action": "remove"})
        a.refresh_from_db()
        self.assertTrue(a.is_active)  # can't remove yourself

    def test_removed_member_cannot_sign_in(self):
        self.signup("owner@studio.gr")
        owner = User.objects.get(email="owner@studio.gr")
        member = User.objects.create_user("m", email="m@example.com", password=self.password)
        mm = Membership.objects.create(user=member, role=Membership.EDITOR, approved=True)
        self.client.post(reverse("team_update", args=[mm.pk]), {"action": "remove"})
        self.client.logout()
        resp = self.client.post(reverse("account_login"), {"login": "m@example.com", "password": self.password})
        self.assertNotEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertTrue(owner.membership.is_owner)

    def test_google_button_only_when_configured(self):
        self.assertNotContains(self.client.get(reverse("account_login")), "Continue with Google")
        google = {"google": {"APPS": [{"client_id": "id", "secret": "s", "key": ""}], "SCOPE": ["email"]}}
        with override_settings(SOCIALACCOUNT_PROVIDERS=google):
            resp = self.client.get(reverse("account_login"))
        self.assertContains(resp, "Continue with Google")
        self.assertContains(resp, "/accounts/google/login/")


class ServerlessTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.login(username="staff", password="pw-123456!")

    @override_settings(CRON_SECRET="s3cret")
    def test_cron_tick_requires_secret_and_publishes(self):
        post = self.make_post(Post.FEED, [save_upload(image_upload())])
        self.client.logout()
        self.assertEqual(self.client.get("/cron/tick/").status_code, 403)
        self.assertEqual(self.client.get("/cron/tick/?key=wrong").status_code, 403)
        resp = self.client.get("/cron/tick/", HTTP_AUTHORIZATION="Bearer s3cret")
        self.assertEqual(resp.json()["published"], 1)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED)

    @override_settings(CRON_SECRET="s3cret")
    def test_owner_is_warned_until_the_timer_runs(self):
        self.assertContains(self.client.get(reverse("dashboard")), "Automatic publishing isn")
        page = self.client.get(reverse("scheduler_setup"))
        self.assertContains(page, "/cron/tick/?key=s3cret")
        self.client.get("/cron/tick/?key=s3cret")
        self.assertNotContains(self.client.get(reverse("dashboard")), "Automatic publishing isn")
        self.assertContains(self.client.get(reverse("scheduler_setup")), "Running")

    @override_settings(CRON_SECRET="")
    def test_cron_tick_disabled_without_secret(self):
        self.assertEqual(self.client.get("/cron/tick/?key=").status_code, 403)

    @override_settings(SERVERLESS=True)
    def test_publish_now_runs_immediately_when_serverless(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("post_new"), {
            "post_type": "feed", "caption": "Now!", "action": "now", "media_ids": str(asset.pk),
        }, follow=True)
        self.assertContains(resp, "Published to Instagram")
        self.assertEqual(Post.objects.get().status, Post.PUBLISHED)

    @override_settings(BLOB_READ_WRITE_TOKEN="vercel_blob_rw_StoreAbc123_secretpart")
    def test_upload_token_matches_vercel_client_token_format(self):
        import base64, hashlib, hmac, json
        resp = self.client.post(reverse("media_upload_token"), data=json.dumps(
            {"name": "recital.mov", "type": "video/quicktime", "size": 50_000_000}), content_type="application/json")
        data = resp.json()
        self.assertTrue(data["pathname"].startswith("library/") and data["pathname"].endswith(".mov"))
        prefix = "vercel_blob_client_StoreAbc123_"
        self.assertTrue(data["token"].startswith(prefix))
        signature, payload = base64.b64decode(data["token"][len(prefix):]).decode().split(".", 1)
        expected = hmac.new(b"vercel_blob_rw_StoreAbc123_secretpart", payload.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(signature, expected)
        claims = json.loads(base64.b64decode(payload))
        self.assertEqual(claims["pathname"], data["pathname"])
        self.assertEqual(claims["maximumSizeInBytes"], 300 * 1024 * 1024)

    @override_settings(BLOB_READ_WRITE_TOKEN="vercel_blob_rw_StoreAbc123_secretpart")
    def test_upload_token_rejects_huge_or_unknown_files(self):
        import json
        for body in ({"name": "big.mp4", "type": "video/mp4", "size": 400 * 1024 * 1024},
                     {"name": "notes.pdf", "type": "application/pdf", "size": 1000}):
            resp = self.client.post(reverse("media_upload_token"), data=json.dumps(body), content_type="application/json")
            self.assertEqual(resp.status_code, 400)

    def test_direct_upload_complete_processes_photo_and_keeps_video(self):
        import json
        from django.core.files.storage import default_storage
        from .media import plan_direct_upload
        photo_path, _, _ = plan_direct_upload("IMG_1.png", "image/png", 1000)
        default_storage.save(photo_path, image_upload())
        resp = self.client.post(reverse("media_upload_complete"), data=json.dumps(
            {"pathname": photo_path, "name": "IMG_1.png", "in_queue": True}), content_type="application/json")
        photo = MediaAsset.objects.get(pk=resp.json()["id"])
        self.assertEqual((photo.kind, photo.in_queue, photo.width), (MediaAsset.IMAGE, True, 800))
        self.assertTrue(photo.file.name.endswith(".jpg"))
        self.assertFalse(default_storage.exists(photo_path))  # the raw upload is cleaned up

        video_path, _, _ = plan_direct_upload("dance.mp4", "video/mp4", 1000)
        default_storage.save(video_path, video_upload())
        resp = self.client.post(reverse("media_upload_complete"), data=json.dumps(
            {"pathname": video_path, "name": "dance.mp4"}), content_type="application/json")
        video = MediaAsset.objects.get(pk=resp.json()["id"])
        self.assertEqual((video.kind, video.file.name), (MediaAsset.VIDEO, video_path))

    @override_settings(SERVERLESS=True, BLOB_READ_WRITE_TOKEN="")
    def test_uploads_without_cloud_storage_explain_instead_of_crashing(self):
        resp = self.client.post(reverse("media_list"), {"files": image_upload()}, follow=True)
        self.assertContains(resp, "connect Blob storage")
        self.assertFalse(MediaAsset.objects.exists())
        resp = self.client.post(reverse("post_new"), {"post_type": "feed", "action": "draft", "new_files": image_upload()}, follow=True)
        self.assertContains(resp, "connect Blob storage")
        self.assertFalse(Post.objects.exists())

    def test_direct_upload_complete_rejects_unknown_paths(self):
        import json
        resp = self.client.post(reverse("media_upload_complete"), data=json.dumps(
            {"pathname": "../../etc/passwd", "name": "x"}), content_type="application/json")
        self.assertEqual(resp.status_code, 400)


class InstagramSetupTests(BaseTest):
    TOKEN = "IGAAexampleexampleexampleexampleexample123"

    def setUp(self):
        super().setUp()
        InstagramAccount.objects.all().delete()
        self.client.login(username="staff", password="pw-123456!")

    def test_setup_steps_show_when_not_connected(self):
        resp = self.client.get(reverse("instagram"))
        self.assertContains(resp, "Open Meta for Developers")
        self.assertContains(resp, "Paste it here")

    def test_pasting_a_token_connects_without_renewing_it(self):
        resp = self.client.post(reverse("instagram"), {"step": "token", "access_token": f' "Bearer {self.TOKEN}\n" '})
        self.assertRedirects(resp, reverse("instagram"))
        account = InstagramAccount.current()
        self.assertEqual((account.username, account.access_token, account.account_type),
                         ("lineofdance", self.TOKEN, "BUSINESS"))
        self.assertGreater(account.token_expires_at, timezone.now() + timedelta(days=59))
        self.assertFalse(account.should_refresh)  # brand-new tokens can't be renewed yet
        page = self.client.get(reverse("instagram"))
        self.assertContains(page, "@lineofdance")
        self.assertNotContains(page, "Paste it here")

    def test_personal_account_is_explained(self):
        self.graph.profile["account_type"] = "PERSONAL"
        resp = self.client.post(reverse("instagram"), {"step": "token", "access_token": self.TOKEN}, follow=True)
        self.assertContains(resp, "Switch to professional")
        self.assertIsNone(InstagramAccount.current())

    def test_invalid_token_gets_a_plain_explanation(self):
        resp = self.client.post(reverse("instagram"), {"step": "token", "access_token": "bad" * 20}, follow=True)
        self.assertIsNone(InstagramAccount.current())
        with mock.patch.object(instagram.requests, "get", return_value=FakeResponse(
                {"error": {"message": "Error validating access token", "code": 190}}, status=400)):
            with self.assertRaisesMessage(instagram.InstagramError, "invalid or has expired"):
                instagram.connect_with_token(self.TOKEN)

    def test_short_garbage_is_rejected(self):
        resp = self.client.post(reverse("instagram"), {"step": "token", "access_token": "hello"}, follow=True)
        self.assertContains(resp, "look like an access token")

    def test_check_connection_reports_quota(self):
        instagram.connect_with_token(self.TOKEN)
        resp = self.client.post(reverse("instagram"), {"step": "check"}, follow=True)
        self.assertContains(resp, "Connection works")
        self.assertContains(resp, "3 of 100")

    def test_app_keys_saved_in_page_are_used_for_login_button(self):
        self.client.post(reverse("instagram"), {"step": "app", "app_id": "123456", "app_secret": "shh"})
        from .models import InstagramApp
        self.assertEqual(InstagramApp.credentials(), ("123456", "shh"))
        self.assertIn("client_id=123456", instagram.authorize_url("state"))
        # saving again without a secret keeps the old one
        self.client.post(reverse("instagram"), {"step": "app", "app_id": "999", "app_secret": ""})
        self.assertEqual(InstagramApp.credentials(), ("999", "shh"))
        self.assertContains(self.client.get(reverse("instagram")), "Log in with Instagram</a>")


class LinksPageTests(BaseTest):
    def test_public_page_shows_buttons_and_linked_posts_without_login(self):
        from .models import LinkPage
        page = LinkPage.load()
        page.buttons = [{"label": "Sign up", "url": "lineofdance.gr/epikoinonia.php#interest"}]
        page.save()
        linked = self.make_post(Post.FEED, [save_upload(image_upload())], link="lineofdance.gr/summer")
        unlinked = self.make_post(Post.FEED, [save_upload(image_upload())])
        Post.objects.update(status=Post.PUBLISHED, published_at=timezone.now())
        html = self.client.get("/links/").content.decode()
        self.assertIn("https://lineofdance.gr/epikoinonia.php", html)
        self.assertIn("https://lineofdance.gr/summer", html)
        self.assertEqual(html.count('class="go"'), 1)  # only the post with a link

    def test_owner_can_edit_buttons(self):
        self.client.login(username="staff", password="pw-123456!")
        resp = self.client.post(reverse("links_settings"), {
            "headline": "Line of Dance", "bio": "Thessaloniki", "show_posts": "on",
            "label_0": "Sign up", "url_0": "lineofdance.gr/epikoinonia.php", "label_1": "Website", "url_1": "",
        })
        self.assertContains(resp, "Add the link for this button")
        self.client.post(reverse("links_settings"), {"headline": "Line of Dance", "label_0": "Sign up",
                                                     "url_0": "lineofdance.gr/x"})
        from .models import LinkPage
        self.assertEqual(LinkPage.load().buttons, [{"label": "Sign up", "url": "lineofdance.gr/x"}])


class StatsTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.login(username="staff", password="pw-123456!")
        # 8 posts: those published at 19:00 Athens time do much better than the morning ones.
        self.media = []
        for i in range(8):
            hour = 16 if i % 2 else 6  # UTC → 19:00 / 09:00 in Athens (summer time)
            ts = f"2026-09-{10 + i:02d}T{hour:02d}:00:00+0000"
            self.media.append({"id": f"m{i}", "media_type": "IMAGE", "media_product_type": "FEED", "timestamp": ts,
                               "permalink": f"https://instagram.com/p/{i}", "like_count": 40 if hour == 16 else 5,
                               "comments_count": 2, "media_url": "https://cdn.example.com/x.jpg", "caption": "c"})
        self.insights_denied = False

    def fake_get(self, url, params=None, **kwargs):
        params = params or {}
        if url.endswith("/17841/media"):
            return FakeResponse({"data": self.media})
        if url.endswith("/insights") and "/17841/" not in url:
            if self.insights_denied:
                return FakeResponse({"error": {"message": "(#10) Application does not have permission", "code": 10}}, 400)
            return FakeResponse({"data": [{"name": "reach", "values": [{"value": 100}]},
                                          {"name": "saved", "total_value": {"value": 3}}, {"name": "shares", "values": [{"value": 1}]}]})
        if url.endswith("/me"):
            return FakeResponse({"followers_count": 512})
        if url.endswith("/17841/insights"):
            return FakeResponse({"data": []})
        return self.graph.get(url, params=params, **kwargs)

    def test_refresh_collects_results_and_suggests_best_window(self):
        from . import stats
        with mock.patch.object(instagram.requests, "get", side_effect=self.fake_get), \
                mock.patch("studio.stats.requests.get", side_effect=self.fake_get):
            state = stats.refresh(force=True)
        self.assertEqual((state.error, state.followers), ("", 512))
        from .models import MediaStat
        self.assertEqual(MediaStat.objects.count(), 8)
        best = MediaStat.objects.get(ig_media_id="m1")
        self.assertEqual((best.reach, best.saves, best.shares, best.engagement_rate), (100, 3, 1, 46.0))
        window = stats.summary()["best_window"]
        self.assertTrue(window["start"] <= 19 < window["end"], window)
        page = self.client.get(reverse("stats"))
        self.assertContains(page, "Best time to post")
        self.assertContains(page, "46.0%")

    def test_missing_permission_is_explained(self):
        from . import stats
        self.insights_denied = True
        with mock.patch("studio.stats.requests.get", side_effect=self.fake_get):
            state = stats.refresh(force=True)
        self.assertIn("instagram_business_manage_insights", state.error)
        self.assertContains(self.client.get(reverse("stats")), "instagram_business_manage_insights")

    def test_use_window_sets_random_queue_times(self):
        from . import stats
        with mock.patch("studio.stats.requests.get", side_effect=self.fake_get):
            stats.refresh(force=True)
        self.client.post(reverse("stats"), {"action": "use_window"})
        queue = QueueSettings.load()
        self.assertEqual(queue.timing_mode, QueueSettings.TIMING_RANDOM)
        self.assertLessEqual(queue.window_start.hour, 19)
        self.assertGreater(queue.window_end.hour, 19)

    def test_scheduler_refresh_is_throttled_and_never_breaks_publishing(self):
        with mock.patch("studio.stats.refresh", side_effect=RuntimeError("boom")):
            self.assertIn("published", scheduler.tick())


class GreekTests(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", email="o@example.com", password="pw-123456!")
        Membership.objects.create(user=self.user, role=Membership.OWNER, approved=True)
        self.client.login(username="owner", password="pw-123456!")

    def test_every_text_has_a_greek_translation(self):
        from django.core.management import call_command
        call_command("build_translations", "--check")  # raises if anything is missing

    def test_greek_is_the_default_and_english_can_be_chosen(self):
        page = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn("Αρχική", page)
        self.assertIn("Νέα ανάρτηση", page)
        self.assertIn('lang="el"', page)
        self.client.post("/i18n/setlang/", {"language": "en", "next": "/"})
        page = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn("+ New post", page)

    def test_all_pages_render_in_greek(self):
        for name in ["dashboard", "post_list", "post_new", "media_list", "recurring_list", "recurring_new", "queue",
                     "instagram", "team", "stats", "links_settings", "scheduler_setup"]:
            with self.subTest(page=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Αρχική", resp.content.decode())

    def test_messages_and_scripts_are_greek(self):
        asset = save_upload(image_upload())
        resp = self.client.post(reverse("post_new"), {"post_type": "carousel", "caption": "x", "action": "now",
                                                      "media_ids": str(asset.pk)})
        self.assertContains(resp, "Ένα καρουζέλ χρειάζεται από 2 έως 10")
        import json, re
        texts = json.loads(re.search(r'id="studio-i18n" type="application/json">(.*?)</script>',
                                     resp.content.decode()).group(1))
        self.assertEqual(texts["use_caption"], "Χρήση αυτής της λεζάντας")  # page-script texts

    def test_sign_in_page_is_greek_for_visitors(self):
        self.client.logout()
        page = self.client.get(reverse("account_login")).content.decode()
        self.assertIn("Σύνδεση", page)
        self.assertIn("English", page)  # language switch shows each language in its own name
        self.assertIn("Ελληνικά", page)


def _ffmpeg_file(suffix, *args):
    """A real media file made by ffmpeg, e.g. a few seconds of tone or a test-pattern video."""
    import subprocess

    from .video import ffmpeg_exe

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/out{suffix}"
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", *args, path], check=True)
        with open(path, "rb") as fh:
            return fh.read()


def song_upload(name="song.mp3", seconds=6):
    data = _ffmpeg_file(".mp3", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}")
    return SimpleUploadedFile(name, data, content_type="audio/mpeg")


def real_video_upload(name="dance.mp4", seconds=4):
    data = _ffmpeg_file(".mp4", "-f", "lavfi", "-i", f"testsrc=size=320x568:rate=24:duration={seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest")
    return SimpleUploadedFile(name, data, content_type="video/mp4")


class MusicTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.login(username="staff", password="pw-123456!")

    def upload_song(self, **kwargs):
        self.client.post(reverse("music_list"), {"files": song_upload(**kwargs)})
        return MusicTrack.objects.latest("id")

    def probe_asset(self, asset):
        from .video import probe

        return probe(asset.file.path)

    def test_music_upload_reads_length_and_rejects_non_audio(self):
        track = self.upload_song(seconds=6)
        self.assertEqual(track.title, "song")
        self.assertAlmostEqual(track.duration, 6, delta=0.3)
        self.assertEqual(track.duration_display, "0:06")
        resp = self.client.post(reverse("music_list"), {"files": SimpleUploadedFile("fake.mp3", b"not music")},
                                follow=True)
        self.assertContains(resp, "couldn")
        self.assertEqual(MusicTrack.objects.count(), 1)
        self.assertContains(self.client.get(reverse("music_list")), "song")

    def test_photo_becomes_story_video_with_music(self):
        photo = save_upload(image_upload())
        track = self.upload_song(seconds=6)
        resp = self.client.post(reverse("music_video"), {
            "asset": photo.pk, "track": track.pk, "start": "0:02", "length": "8",
        })
        video = MediaAsset.objects.filter(kind=MediaAsset.VIDEO).get()
        self.assertRedirects(resp, f"{reverse('post_new')}?media={video.pk}&type=story", fetch_redirect_response=False)
        duration, has_audio = self.probe_asset(video)
        self.assertAlmostEqual(duration, 8, delta=0.3)  # the 6 s song loops to fill 8 s
        self.assertTrue(has_audio)
        self.assertEqual((video.width, video.height), (1080, 1920))
        form = self.client.get(resp["Location"]).context["form"]
        self.assertEqual(form["post_type"].value(), "story")

    def test_video_gets_music_and_keeps_its_length(self):
        clip = save_upload(real_video_upload(seconds=4))
        track = self.upload_song(seconds=6)
        self.client.post(reverse("music_video"), {
            "asset": clip.pk, "track": track.pk, "start": "0", "length": "15", "keep_original_sound": "on",
        })
        video = MediaAsset.objects.filter(kind=MediaAsset.VIDEO).latest("id")
        self.assertNotEqual(video.pk, clip.pk)
        duration, has_audio = self.probe_asset(video)
        self.assertAlmostEqual(duration, 4, delta=0.3)
        self.assertTrue(has_audio)

    def test_start_past_the_end_of_the_song_is_refused(self):
        photo = save_upload(image_upload())
        track = self.upload_song(seconds=6)
        resp = self.client.post(reverse("music_video"), {
            "asset": photo.pk, "track": track.pk, "start": "1:30", "length": "15",
        })
        self.assertContains(resp, "only 0:06 long")
        self.assertFalse(MediaAsset.objects.filter(kind=MediaAsset.VIDEO).exists())

    def test_music_goes_to_its_own_folder_in_cloud_uploads(self):
        from .media import plan_direct_upload

        pathname, types, _max = plan_direct_upload("Line Dance.m4a", "audio/x-m4a", 5_000_000)
        self.assertTrue(pathname.startswith("music/") and pathname.endswith(".m4a"))
        self.assertIn("audio/x-m4a", types)


class StoryTextTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.login(username="staff", password="pw-123456!")

    def test_preview_is_a_story_sized_image(self):
        photo = save_upload(image_upload())
        resp = self.client.post(reverse("story_text"), {
            "asset": photo.pk, "headline": "Απόψε 20:00 💃", "text": "", "position": "top", "style": "brand",
            "headline_size": "150", "text_size": "60", "preview": "1",
        })
        import base64

        data_url = resp.json()["image"]
        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))
        preview = Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1])))
        self.assertEqual(preview.size, (540, 960))
        self.assertEqual(MediaAsset.objects.count(), 1)  # previews aren't saved

    def test_story_image_is_saved_and_opens_as_story(self):
        resp = self.client.post(reverse("story_text"), {
            "asset": "", "headline": "Καλοκαιρινό πάρτι", "text": "Σάββατο 21:00", "position": "middle",
            "style": "none", "headline_size": "100", "text_size": "100",
        })
        story = MediaAsset.objects.get()
        self.assertRedirects(resp, f"{reverse('post_new')}?media={story.pk}&type=story", fetch_redirect_response=False)
        self.assertEqual((story.kind, story.width, story.height), (MediaAsset.IMAGE, 1080, 1920))

    def test_story_needs_some_text(self):
        resp = self.client.post(reverse("story_text"), {"asset": "", "headline": " ", "text": "", "position": "bottom",
                                                        "style": "dark", "headline_size": "100", "text_size": "100"})
        self.assertContains(resp, "Write some text")
        self.assertFalse(MediaAsset.objects.exists())
        self.assertContains(self.client.get(reverse("story_text")), "data-story-preview")

    def test_story_can_repeat_every_week(self):
        resp = self.client.post(reverse("story_text"), {
            "asset": "", "headline": "Απόψε 20:00 Αρχάριοι", "text": "", "position": "bottom", "style": "dark",
            "headline_size": "100", "text_size": "100", "repeat": "on", "weekday_list": ["0", "2"],
            "times": "17:00",
        })
        self.assertRedirects(resp, reverse("recurring_list"), fetch_redirect_response=False)
        rule = RecurringRule.objects.get()
        self.assertEqual((rule.post_type, rule.weekdays, rule.times), (Post.STORY, "0,2", "17:00"))
        self.assertEqual(list(rule.media.all()), [MediaAsset.objects.get()])
        self.assertIn(timezone.localtime(rule.next_run_at).weekday(), (0, 2))

    def test_repeat_needs_days(self):
        resp = self.client.post(reverse("story_text"), {
            "asset": "", "headline": "x", "text": "", "position": "bottom", "style": "dark",
            "headline_size": "100", "text_size": "100", "repeat": "on", "times": "17:00",
        })
        self.assertContains(resp, "Pick at least one day")
        self.assertFalse(RecurringRule.objects.exists())

    def test_bigger_size_makes_bigger_letters(self):
        from .story import render_story

        def ink_height(size):
            image = render_story(None, "Νέο τμήμα", position="middle", style="none", headline_size=size)
            column = [image.getpixel((540, y)) for y in range(1920)]
            white = [y for y, px in enumerate(column) if min(px) > 230]
            return max(white) - min(white) if white else 0

        self.assertGreater(ink_height(180), ink_height(100) * 1.4)


class BlobDownloadTests(TestCase):
    @override_settings(BLOB_READ_WRITE_TOKEN="vercel_blob_rw_StoreAbc123_secretpart")
    def test_refused_download_is_retried_with_the_token(self):
        from . import storage

        calls = []

        def fake_get(url, headers=None, params=None, **kwargs):
            calls.append((headers.get("authorization"), params))
            return FakeResponse({}, status=403 if len(calls) == 1 else 200)

        FakeResponse.close = lambda self: None
        with mock.patch.object(storage.requests, "get", side_effect=fake_get):
            self.assertEqual(storage.blob_get("https://x.public.blob.vercel-storage.com/a.jpg").status_code, 200)
        self.assertEqual(calls[0][0], None)
        self.assertEqual(calls[1][0], "Bearer vercel_blob_rw_StoreAbc123_secretpart")

    @override_settings(BLOB_READ_WRITE_TOKEN="vercel_blob_rw_StoreAbc123_secretpart")
    def test_download_error_says_what_storage_answered(self):
        from . import storage

        FakeResponse.close = lambda self: None
        with mock.patch.object(storage.requests, "get", return_value=FakeResponse("Forbidden", status=403)):
            with self.assertRaisesRegex(storage.BlobDownloadError, "403 Forbidden"):
                storage.blob_get("https://x.public.blob.vercel-storage.com/a.jpg")
