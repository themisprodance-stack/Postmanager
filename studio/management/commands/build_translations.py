"""Build locale/el/LC_MESSAGES/django.po + .mo from studio/translations_el.py.

Every translatable text in the templates and Python code is collected with Django's own template parser,
so the Greek catalog can't silently miss anything. Run after changing any user-facing text:

    .venv/bin/python manage.py build_translations
"""

import ast
import re
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation.template import templatize

ROOT = Path(settings.BASE_DIR)
GETTEXT_NAMES = {"_", "gettext", "gettext_lazy", "_lazy", "pgettext"}
TEMPLATE_CALL = re.compile(r"""\bgettext\((u?(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'))\)""")


def template_msgids():
    found = {}
    for path in sorted((ROOT / "studio" / "templates").rglob("*.html")):
        for match in TEMPLATE_CALL.finditer(templatize(path.read_text(), origin=str(path))):
            found.setdefault(ast.literal_eval(match.group(1).lstrip("u")), str(path.relative_to(ROOT)))
    return found


def python_msgids():
    found = {}
    for path in sorted(list((ROOT / "studio").rglob("*.py")) + list((ROOT / "config").rglob("*.py"))):
        if "migrations" in path.parts or path.name.startswith("translations_"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) in GETTEXT_NAMES
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, str(path.relative_to(ROOT)))
    return found


def all_msgids():
    return {**python_msgids(), **template_msgids()}


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Only report missing translations.")

    def handle(self, *args, check=False, **options):
        from studio.translations_el import EL

        msgids = all_msgids()
        missing = [m for m in msgids if m not in EL]
        unused = [m for m in EL if m not in msgids]
        for m in missing:
            self.stderr.write(f"missing: {m!r}  ({msgids[m]})")
        for m in unused:
            self.stdout.write(f"unused: {m!r}")
        if check:
            if missing:
                raise CommandError(f"{len(missing)} text(s) have no Greek translation.")
            return
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8", "Language": "el",
                       "Plural-Forms": "nplurals=2; plural=(n != 1);"}
        for msgid in sorted(msgids):
            if msgid in EL:
                po.append(polib.POEntry(msgid=msgid, msgstr=EL[msgid], occurrences=[(msgids[msgid], "")]))
        out = ROOT / "locale" / "el" / "LC_MESSAGES"
        out.mkdir(parents=True, exist_ok=True)
        po.save(str(out / "django.po"))
        po.save_as_mofile(str(out / "django.mo"))
        self.stdout.write(self.style.SUCCESS(f"{len(po)} Greek translations built ({len(missing)} missing)."))
