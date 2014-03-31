#! /usr/bin/python

import Image
import sys

def g_header(idx, w, h):
  output = "STARTCHAR %03d\n" % idx
  output += "ENCODING %d\n" % idx
  output += "SWIDTH 1008\n"
  output += "DWIDTH %d\n" % w
  output += "BBX %d %d 0 0\n" % (w, h)
  output += "BITMAP\n"
  return output

def getglyph(glyph, padding, idx, w, h):
  output = g_header(idx, w, h)
  for row in glyph:
    output += "%0*x\n" % (padding, row)
  return output + "ENDCHAR\n"

def t2h(t):
  if t[3] == 255:
    return "0x%02x%02x%02x" % t[:3]
  return None

def getcolors(im):
  palette = {}
  colors = im.getcolors()
  for color in colors:
    # No support for alpha channels, just drop them
    if color[1][3] == 255:
      palette[t2h(color[1])] = [0] * im.size[0]
  return palette

def parseImage(file, idx):
  output = "COMMENT Conversion of file %s\n" % file
  im = Image.open(file).convert('RGBA')
  h,w = im.size
  colors = getcolors(im)
  if w % 16:
    padding=(16 - (w % 16) + w)/4
  else:
    padding=w/4
  x = y = 0
  pix = im.load()
  while y < h:
    while x < w:
      c = t2h(pix[x,y])
      if c:
        colors[c][y] += (1 << (w-x-1))
      x+= 1
    x = 0
    y += 1
  for color in colors:
    output += "COMMENT Next glyph is color %s\n" % color
    output += getglyph(colors[color], padding, idx, w, h)
    idx += 1
  return (len(colors), output)

def f_header(h, w, count):
  output = "STARTFONT 2.1\n"
  output += "FONT Untitled\n"
  output += "SIZE %d 96 96\n" % w
  output += "FONTBOUNDINGBOX %d %d 0 0\n" % (w, h)
  output += "STARTPROPERTIES 2\n"
  output += "FONT_ASCENT %d\n" % h
  output += "FONT_DESCENT 0\n"
  output += "ENDPROPERTIES\n"
  output += "CHARS %d" % count
  return output

if __name__ == '__main__':
  files = sys.argv[1:]
  # Change these to your start char, the height and width of the font overall
  # eventually, these should either be computed or prompted from the user
  idx = 0
  w = 16
  h = 16
  output = ""
  if len(files) > 0:
    for file in files:
      res = parseImage(file, idx)
      idx += res[0]
      output += res[1]
  print f_header(w,h, idx)
  print output
  print "ENDFONT"
