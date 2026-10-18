import re
from datetime import date, datetime, timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import WEEKDAY_CHOICES, MediaAsset, MusicTrack, Post, QueueSettings, RecurringRule, clean_link, parse_times


class LinkCleaningMixin:
    """Removes the '#…' part of links (Instagram would turn it into a hashtag) and remembers that it did."""

    link_was_trimmed = False

    def clean_link(self):
        raw = (self.cleaned_data.get("link") or "").strip()
        cleaned = clean_link(raw)
        if " " in cleaned:
            raise forms.ValidationError(_("A link can't contain spaces."))
        self.link_was_trimmed = cleaned != raw
        return cleaned


USERNAME_RE = re.compile(r"[a-z0-9._]{1,30}")
MAX_USER_TAGS = 20
MAX_COLLABORATORS = 3
USER_TAGS_WIDGET = forms.TextInput(attrs={"placeholder": _("e.g. @maria_dance, @johnsmith"), "autocapitalize": "off"})


def clean_usernames(value):
    """Turns '@Maria, instagram.com/john/' into ['maria', 'john'] and rejects anything that isn't a username."""
    names = []
    for raw in re.split(r"[\s,;]+", value or ""):
        name = raw.strip().lstrip("@").removeprefix("https://").removeprefix("www.").removeprefix("instagram.com/")
        name = name.strip("/").lower()
        if not name:
            continue
        if not USERNAME_RE.fullmatch(name):
            raise forms.ValidationError(_("“%(name)s” isn't a valid Instagram username.") % {"name": raw})
        if name not in names:
            names.append(name)
    return names


class UserTagsCleaningMixin:
    def clean_user_tags(self):
        names = clean_usernames(self.cleaned_data.get("user_tags"))
        if len(names) > MAX_USER_TAGS:
            raise forms.ValidationError(_("Instagram allows at most 20 tagged people."))
        return " ".join(names)


DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*,video/mp4,video/quicktime"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super(MultipleFileField, self).clean(d, initial) for d in data if d]
        return [super().clean(data, initial)] if data else []


class UploadForm(forms.Form):
    files = MultipleFileField(required=True, label=_("Photos or videos"))
    add_to_queue = forms.BooleanField(required=False, label=_("Add to the content queue"))


MUSIC_ACCEPT = ".mp3,.m4a,.aac,.wav,audio/mpeg,audio/mp4,audio/x-m4a,audio/aac,audio/wav"


class MusicUploadForm(forms.Form):
    files = MultipleFileField(required=True, label=_("Music files"), widget=MultipleFileInput(attrs={"accept": MUSIC_ACCEPT}))


class MusicVideoForm(forms.Form):
    asset = forms.ModelChoiceField(MediaAsset.objects.all(), widget=forms.RadioSelect, label=_("Photo or video"),
                                   error_messages={"required": _("Pick a photo or video.")})
    track = forms.ModelChoiceField(MusicTrack.objects.all(), widget=forms.RadioSelect, label=_("Music"),
                                   error_messages={"required": _("Pick a song.")})
    start = forms.CharField(initial="0:00", label=_("Start the song at"),
                            widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "0:30"}))
    length = forms.IntegerField(initial=15, min_value=3, max_value=30, label=_("Length (seconds)"),
                                widget=forms.NumberInput(attrs={"min": 3, "max": 30}))
    keep_original_sound = forms.BooleanField(required=False, label=_("Keep the video's own sound, quieter, under the music"))

    def clean_start(self):
        raw = self.cleaned_data["start"].strip()
        try:
            minutes, _sep, seconds = raw.rpartition(":")
            value = int(minutes or 0) * 60 + float(seconds or 0)
        except ValueError:
            raise forms.ValidationError(_("Use minutes:seconds, e.g. 0:45"))
        if value < 0:
            raise forms.ValidationError(_("Use minutes:seconds, e.g. 0:45"))
        return value

    def clean(self):
        cleaned = super().clean()
        track, start = cleaned.get("track"), cleaned.get("start")
        if track and track.duration and start is not None and start >= track.duration - 1:
            self.add_error("start", _("The song is only %(length)s long.") % {"length": track.duration_display})
        return cleaned


class StoryTextForm(forms.Form):
    POSITION_CHOICES = [("top", _("Top")), ("middle", _("Middle")), ("bottom", _("Bottom"))]
    STYLE_CHOICES = [("dark", _("Dark box")), ("light", _("Light box")), ("brand", _("Pink box")),
                     ("none", _("Text only"))]

    asset = forms.ModelChoiceField(MediaAsset.objects.filter(kind=MediaAsset.IMAGE), required=False,
                                   widget=forms.RadioSelect, label=_("Photo"))
    headline = forms.CharField(max_length=80, required=False, label=_("Title"),
                               widget=forms.TextInput(attrs={"placeholder": _("e.g. Tonight 20:00 · Beginners")}))
    text = forms.CharField(max_length=250, required=False, label=_("Smaller text"),
                           widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("e.g. First class free, bring a friend!")}))
    position = forms.ChoiceField(choices=POSITION_CHOICES, initial="bottom", widget=forms.RadioSelect, label=_("Text position"))
    style = forms.ChoiceField(choices=STYLE_CHOICES, initial="dark", widget=forms.RadioSelect, label=_("Style"))
    headline_size = forms.IntegerField(min_value=40, max_value=200, initial=100, label=_("Title size"),
                                       widget=forms.NumberInput(attrs={"type": "range", "min": 40, "max": 200, "step": 5}))
    text_size = forms.IntegerField(min_value=40, max_value=200, initial=100, label=_("Smaller text size"),
                                   widget=forms.NumberInput(attrs={"type": "range", "min": 40, "max": 200, "step": 5}))

    repeat = forms.BooleanField(required=False, label=_("Post this story every week"))
    weekday_list = forms.MultipleChoiceField(choices=WEEKDAY_CHOICES, widget=forms.CheckboxSelectMultiple,
                                             required=False, label=_("Days"))
    times = forms.CharField(required=False, initial="18:00", label=_("Time(s)"),
                            help_text=_("24h times, comma separated, e.g. 09:00, 18:30"))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("repeat"):
            if not cleaned.get("weekday_list"):
                self.add_error("weekday_list", _("Pick at least one day."))
            try:
                cleaned["times"] = clean_times_value(cleaned.get("times", ""))
            except forms.ValidationError as exc:
                self.add_error("times", exc)
        return cleaned

    def story_options(self):
        keys = ("headline", "text", "position", "style", "headline_size", "text_size")
        return {key: self.cleaned_data[key] for key in keys}


class PostForm(UserTagsCleaningMixin, LinkCleaningMixin, forms.ModelForm):
    ACTION_CHOICES = [("draft", _("Save as draft")), ("schedule", _("Schedule")), ("now", _("Publish now"))]

    media_ids = forms.CharField(required=False, widget=forms.HiddenInput)
    new_files = MultipleFileField(required=False, label=_("Upload new photos/videos"))
    action = forms.ChoiceField(choices=ACTION_CHOICES, initial="schedule", widget=forms.HiddenInput)
    scheduled_at = forms.DateTimeField(
        required=False, input_formats=[DATETIME_FORMAT], label=_("Publish at"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_FORMAT),
    )

    class Meta:
        model = Post
        fields = ["post_type", "caption", "link", "user_tags", "collaborators", "share_reel_to_feed", "scheduled_at"]
        widgets = {
            "post_type": forms.RadioSelect,
            "caption": forms.Textarea(attrs={"rows": 8, "maxlength": 2200}),
            "link": forms.TextInput(attrs={"placeholder": _("e.g. lineofdance.gr/classes"), "inputmode": "url"}),
            "user_tags": USER_TAGS_WIDGET,
            "collaborators": forms.TextInput(attrs={"placeholder": _("e.g. @teacher_anna"), "autocapitalize": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["media_ids"] = ",".join(str(a.pk) for a in self.instance.ordered_media)
            if self.instance.scheduled_at:
                self.initial["scheduled_at"] = timezone.localtime(self.instance.scheduled_at).strftime(DATETIME_FORMAT)

    def clean_collaborators(self):
        names = clean_usernames(self.cleaned_data.get("collaborators"))
        if len(names) > MAX_COLLABORATORS:
            raise forms.ValidationError(_("Instagram allows at most 3 collaborators."))
        return " ".join(names)

    def clean_media_ids(self):
        ids = [int(i) for i in self.cleaned_data["media_ids"].split(",") if i.strip().isdigit()]
        found = MediaAsset.objects.in_bulk(ids)
        return [found[i] for i in ids if i in found]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") == "schedule":
            when = cleaned.get("scheduled_at")
            if not when:
                self.add_error("scheduled_at", _("Pick a date and time, or save as draft."))
            elif when < timezone.now() - timedelta(minutes=1):
                self.add_error("scheduled_at", _("This time is in the past."))
        return cleaned


def clean_times_value(value):
    """'18:30, 9:00' -> '09:00,18:30'"""
    try:
        times = parse_times(value)
    except ValueError:
        raise forms.ValidationError(_("Use HH:MM, e.g. 09:00, 18:30"))
    if not times:
        raise forms.ValidationError(_("Add at least one time."))
    return ",".join(t.strftime("%H:%M") for t in sorted(set(times)))


class WeeklyScheduleMixin(forms.ModelForm):
    weekday_list = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES, widget=forms.CheckboxSelectMultiple, label=_("Days"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["times"].help_text = _("24h times, comma separated, e.g. 09:00, 18:30")
        if not self.is_bound:
            self.initial["weekday_list"] = [d for d in self.instance.weekdays.split(",") if d]

    def clean_times(self):
        return clean_times_value(self.cleaned_data["times"])

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.weekdays = ",".join(sorted(self.cleaned_data["weekday_list"]))
        obj.next_run_at = obj.compute_next_run()
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class RecurringRuleForm(UserTagsCleaningMixin, LinkCleaningMixin, WeeklyScheduleMixin):
    class Meta:
        model = RecurringRule
        fields = ["name", "active", "post_type", "weekday_list", "times", "caption", "link", "user_tags", "use_ai_caption",
                  "ai_brief", "media"]
        widgets = {
            "post_type": forms.RadioSelect,
            "caption": forms.Textarea(attrs={"rows": 5}),
            "ai_brief": forms.Textarea(attrs={"rows": 3}),
            "media": forms.CheckboxSelectMultiple,
            "user_tags": USER_TAGS_WIDGET,
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("use_ai_caption") and not cleaned.get("ai_brief", "").strip():
            self.add_error("ai_brief", _("Describe what the AI should write about."))
        return cleaned


class QueueSettingsForm(UserTagsCleaningMixin, LinkCleaningMixin, WeeklyScheduleMixin):
    class Meta:
        model = QueueSettings
        fields = ["active", "weekday_list", "timing_mode", "times", "window_start", "window_end", "posts_per_day",
                  "source", "random_order", "as_story", "caption_mode", "default_caption", "ai_brief", "link",
                  "user_tags", "reuse_items"]
        widgets = {
            "timing_mode": forms.RadioSelect,
            "source": forms.RadioSelect,
            "window_start": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "window_end": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "posts_per_day": forms.NumberInput(attrs={"min": 1, "max": 25}),
            "default_caption": forms.Textarea(attrs={"rows": 3}),
            "ai_brief": forms.Textarea(attrs={"rows": 3}),
            "user_tags": USER_TAGS_WIDGET,
        }

    def clean_times(self):
        if self.data.get("timing_mode") == QueueSettings.TIMING_RANDOM:
            return self.instance.times or "18:00"  # not used in random mode
        return super().clean_times()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("timing_mode") == QueueSettings.TIMING_RANDOM:
            start, end, count = cleaned.get("window_start"), cleaned.get("window_end"), cleaned.get("posts_per_day")
            if start and end and end <= start:
                self.add_error("window_end", _("The last time must be later than the first."))
            if count is not None and not 1 <= count <= 25:
                self.add_error("posts_per_day", _("Choose between 1 and 25 posts a day."))
            elif start and end and count and end > start:
                minutes = (datetime.combine(date.min, end) - datetime.combine(date.min, start)).seconds // 60
                if minutes < count * 15:
                    self.add_error("posts_per_day", _(
                        "That's too many for this window. Allow at least 15 minutes per post (max %(max)s here).")
                        % {"max": max(1, minutes // 15)})
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.planned_runs = []
        obj.next_run_at, obj.planned_runs = obj.plan_after()
        if commit:
            obj.save()
        return obj


class MediaAssetForm(forms.ModelForm):
    class Meta:
        model = MediaAsset
        fields = ["title", "caption", "in_queue"]
        widgets = {"caption": forms.Textarea(attrs={"rows": 5})}


class TokenForm(forms.Form):
    access_token = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "IGAA…", "autocomplete": "off", "spellcheck": "false"}),
        label=_("Access token"),
    )


class InstagramAppForm(forms.Form):
    app_id = forms.CharField(label=_("Instagram app ID"), max_length=64)
    app_secret = forms.CharField(
        label=_("Instagram app secret"), max_length=128, required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}, render_value=False),
        help_text=_("Leave empty to keep the saved secret."),
    )


class LinkPageForm(forms.Form):
    MAX_BUTTONS = 5

    headline = forms.CharField(max_length=100, required=False, label=_("Title"))
    bio = forms.CharField(max_length=300, required=False, label=_("Short text"),
                          widget=forms.Textarea(attrs={"rows": 2}))
    show_posts = forms.BooleanField(required=False, label=_("Show my latest posts that have a link"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(self.MAX_BUTTONS):
            self.fields[f"label_{i}"] = forms.CharField(
                max_length=60, required=False, label=_("Button text"),
                widget=forms.TextInput(attrs={"placeholder": _("Button text")}))
            self.fields[f"url_{i}"] = forms.CharField(
                max_length=300, required=False, label=_("Link"),
                widget=forms.TextInput(attrs={"placeholder": _("Link, e.g. lineofdance.gr"), "inputmode": "url"}))

    def button_rows(self):
        return [(self[f"label_{i}"], self[f"url_{i}"]) for i in range(self.MAX_BUTTONS)]

    def clean(self):
        cleaned = super().clean()
        buttons = []
        for i in range(self.MAX_BUTTONS):
            label, url = cleaned.get(f"label_{i}", "").strip(), cleaned.get(f"url_{i}", "").strip()
            if label and not url:
                self.add_error(f"url_{i}", _("Add the link for this button."))
            elif url and " " in url:
                self.add_error(f"url_{i}", _("A link can't contain spaces."))
            elif url:
                buttons.append({"label": label or url, "url": url})
        cleaned["buttons"] = buttons
        return cleaned

    @classmethod
    def initial_for(cls, page):
        initial = {"headline": page.headline, "bio": page.bio, "show_posts": page.show_posts}
        for i, button in enumerate(page.buttons[: cls.MAX_BUTTONS]):
            initial[f"label_{i}"], initial[f"url_{i}"] = button.get("label", ""), button.get("url", "")
        return initial
