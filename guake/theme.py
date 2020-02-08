import itertools
import logging
import os
from pathlib import Path
from textwrap import dedent

import gi
from gi.repository import Gdk, GLib, Gtk

from guake.paths import GUAKE_THEME_DIR

gi.require_version('Gtk', '3.0')


log = logging.getLogger(__name__)

# Reference:
# https://gitlab.gnome.org/GNOME/gnome-tweaks/blob/master/gtweak/utils.py (GPL)


def get_resource_dirs(resource):
    """Returns a list of all known resource dirs for a given resource.

    :param str resource:
        Name of the resource (e.g. "themes")
    :return:
        A list of resource dirs
    """
    dirs = [
        os.path.join(dir, resource) for dir in
        itertools.chain(GLib.get_system_data_dirs(), GUAKE_THEME_DIR, GLib.get_user_data_dir())
    ]
    dirs += [os.path.join(os.path.expanduser("~"), f".{resource}")]

    return [Path(dir) for dir in dirs if os.path.isdir(dir)]


def list_all_themes():
    return sorted(
        {
            x.name for theme_dir in get_resource_dirs("themes") for x in theme_dir.iterdir()
            if x.is_dir()
        }
    )


def select_gtk_theme(settings):
    gtk_theme_name = settings.general.get_string('gtk-theme-name')
    log.debug("Wanted GTK theme: %r", gtk_theme_name)
    gtk_settings = Gtk.Settings.get_default()
    gtk_settings.set_property("gtk-theme-name", gtk_theme_name)

    prefer_dark_theme = settings.general.get_boolean('gtk-prefer-dark-theme')
    log.debug("Prefer dark theme: %r", prefer_dark_theme)
    gtk_settings.set_property("gtk-application-prefer-dark-theme", prefer_dark_theme)


def get_gtk_theme(settings):
    gtk_theme_name = settings.general.get_string('gtk-theme-name')
    prefer_dark_theme = settings.general.get_boolean('gtk-prefer-dark-theme')
    return (gtk_theme_name, "dark" if prefer_dark_theme else None)


def patch_gtk_theme(style_context, settings):
    theme_name, variant = get_gtk_theme(settings)

    def rgba_to_hex(color):
        return f"#{int(color.red * 255):02x}{int(color.green * 255):02x}{int(color.blue * 255):02x}"

    # for n in [
    #     "inverted_bg_color",
    #     "inverted_fg_color",
    #     "selected_bg_color",
    #     "selected_fg_color",
    #     "theme_inverted_bg_color",
    #     "theme_inverted_fg_color",
    #     "theme_selected_bg_color",
    #     "theme_selected_fg_color",
    #     ]:
    #     s = style_context.lookup_color(n)
    #     print(n, s, rgba_to_hex(s[1]))
    selected_fg_color = rgba_to_hex(style_context.lookup_color("theme_selected_fg_color")[1])
    selected_bg_color = rgba_to_hex(style_context.lookup_color("theme_selected_bg_color")[1])
    log.debug(
        "Patching theme '%s' (prefer dark = '%r'), overriding tab 'checked' state': "
        "foreground: %r, background: %r", theme_name, "yes" if variant == "dark" else "no",
        selected_fg_color, selected_bg_color
    )
    css_data = dedent(
        """
        .custom_tab:checked {{
            color: {selected_fg_color};
            background: {selected_bg_color};
        }}
        """.format(selected_bg_color=selected_bg_color, selected_fg_color=selected_fg_color)
    ).encode()
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(css_data)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
