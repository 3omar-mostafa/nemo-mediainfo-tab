#!/usr/bin/python
#coding: utf-8

import locale, gettext, os

try:
  from urllib import unquote
except ImportError:
  from urllib.parse import unquote

from gi.repository import GObject, Gtk, Nemo

from MediaInfoDLL3 import *
import magic
import subprocess
import json


lang = locale.getdefaultlocale()[0]
locale_path = os.path.join(os.path.dirname(__file__), "nemo-mediainfo-tab/locale")
locale_file = os.path.join(locale_path, lang+".csv")
if(not os.path.isfile(locale_file)):
  lang = lang.split("_")[0]
  locale_file = os.path.join(locale_path, lang+".csv")

excludeList = ["METADATA_BLOCK_PICTURE"]

GUI = """
<interface>
  <requires lib="gtk+" version="3.0"/>
  <object class="GtkScrolledWindow" id="mainWindow">
    <property name="visible">True</property>
    <property name="can_focus">True</property>
    <property name="hscrollbar_policy">never</property>
    <child>
      <object class="GtkViewport" id="viewport1">
        <property name="visible">True</property>
        <property name="can_focus">False</property>
        <child>
          <object class="GtkGrid" id="grid">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
            <property name="vexpand">True</property>
            <property name="row_spacing">4</property>
            <property name="column_spacing">16</property>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>"""

class MediainfoPropertyPage(GObject.GObject, Nemo.PropertyPageProvider, Nemo.NameAndDescProvider):


  def run(self, cmd):
      try:
          result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
          return 0, result
      except subprocess.CalledProcessError as proc:
          return proc.returncode, proc.stdout


  def add_row(self, tag, value):
    label = Gtk.Label()
    label.set_markup("<b>" + tag + "</b>")
    label.set_justify(Gtk.Justification.LEFT)
    label.set_halign(Gtk.Align.START)
    label.set_selectable(True)
    label.show()
    self.grid.attach(label, 0, self.top, 1, 1)

    label = Gtk.Label()
    label.set_text(value)
    label.set_justify(Gtk.Justification.LEFT)
    label.set_halign(Gtk.Align.START)
    label.set_selectable(True)
    label.set_line_wrap(True)
    label.set_line_wrap_mode(2) #PANGO_WRAP_WORD_CHAR
    #label.set_max_width_chars(160)
    label.show()
    self.grid.attach(label, 1, self.top, 1, 1)

    self.top += 1


  def get_property_pages(self, files):
    # files: list of NemoVFSFile
    if len(files) != 1:
      return

    file = files[0]
    if file.get_uri_scheme() != 'file':
      return

    if file.is_directory():
      return

    filename = unquote(file.get_uri()[7:])

    try:
      filename = filename.decode("utf-8")
    except:
      pass

    MI = MediaInfo()
    MI.Option_Static("Complete")
    MI.Option_Static("Inform", "Nothing")
    MI.Option_Static("Language", "file://{}".format(locale_file))
    MI.Open(filename)
    info = MI.Inform().splitlines()
    MI.Close()
    if len(info) < 8:
      return

    file_type: str = magic.from_file(filename, mime=True)
    if file_type.startswith("image") :
      return

    exif_data = self.run(f"exiftool -n -g2 -j '{filename}'")
    exif_data = json.loads(exif_data[1])[0]
    exif_data.pop("SourceFile", None)
    exif_data.pop("ExifTool", None)

    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain("nemo-extensions")
    gettext.textdomain("nemo-extensions")
    _ = gettext.gettext

    self.property_label = Gtk.Label(_('Media Info'))
    self.property_label.show()

    self.builder = Gtk.Builder()
    self.builder.set_translation_domain('nemo-extensions')
    self.builder.add_from_string(GUI)

    self.mainWindow = self.builder.get_object("mainWindow")
    self.grid = self.builder.get_object("grid")

    self.top = 0

    for line in info:
      tag = line[:41].strip()
      if tag not in excludeList:
        self.add_row(tag, line[42:].strip())

    self.add_row("", "")
    self.add_row("ExifTool Data", "")
    for tag, value in exif_data.items():
      if isinstance(value, dict):
        self.add_row("", "")
        self.add_row(tag, "")
        for tag2, value2 in value.items():
          self.add_row(str(tag2), str(value2))
      else:
        self.add_row(tag, "")

    self.add_row("", "")

    return Nemo.PropertyPage(name="NemoPython::mediainfo", label=self.property_label, page=self.mainWindow),

  def get_name_and_desc(self):
    return [("Nemo Media Info Tab:::View media information from the properties tab")]

