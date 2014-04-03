#! /usr/bin/python

import Image
import sys, argparse

class Glyph:
  def __init__(self, sourcefile, idx=1):
    self.sourcefile = sourcefile
    self.height = 0
    self.width  = 0
    self.index  = idx
    self.layers = {}  # Colors
    self.padding= 0
    self.image = None
    self.parseImage()
    
  def header(self, idx):
    output = "STARTCHAR %03d\n" % idx
    output += "ENCODING %d\n" % idx
    output += "SWIDTH 1008\n"
    output += "DWIDTH %d 0\n" % self.width
    output += "BBX %d %d 0 0\n" % (self.width, self.height)
    output += "BITMAP\n"
    return output

  def get_glyph(self,layer):
    output = ""
    for row in self.layers[layer]:
      output += "%0*x\n" % (self.padding, row)
    return output

  def getcolors(self):
    palette = {}
    colors = self.image.getcolors()
    for color in colors:
      # No support for alpha channels, just drop them
      if color[1][3] == 255:
        self.layers[t2h(color[1])] = [0] * self.image.size[0]

  def parseImage(self):
    self.image = Image.open(self.sourcefile).convert('RGBA')
    self.height,self.width = self.image.size
    self.getcolors()
    if self.width % 8:
      self.padding=(8 - (self.width % 8) + self.width)/4
    else:
      self.padding=self.width/4
    x = y = 0
    pix = self.image.load()
    while y < self.height:
      while x < self.width:
        c = t2h(pix[x,y])
        if c:
          self.layers[c][y] += (1 << ((self.padding * 4)-x-1))
        x+= 1
      x = 0
      y += 1

  def __str__(self):
    output = "COMMENT Conversion of file %s\n" % file
    idx = self.index
    for layer in self.layers:
      output += "COMMENT Next glyph is color %s\n" % layer
      output += self.header(idx)
      output += self.get_glyph(layer)
      output += "ENDCHAR\n"
      idx += 1
    return output


def t2h(t):
  if t[3] == 255:
    return "#%02x%02x%02x" % t[:3]
  return None

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
  parser = argparse.ArgumentParser(description='Converts a list of image files into color seperated font glyphs in a single BDF file')
  parser.add_argument('files', metavar='FILE', type=str, nargs='+')
  parser.add_argument('-o','--output', help='Output BDFR font file', required=False, default="font.bdf")
  parser.add_argument('-i','--index', help='Starting char number', type=int, required=False, default=1)
  parser.add_argument('-H','--height', help='Total font height.  If an image is larger, this value will be overwritten', type=int, required=False, default=0)
  parser.add_argument('-W','--width', help='Total font width.  If an image is larger, this value will be overwritten', type=int, required=False, default=0)
  parser.add_argument('-c','--color', help='Color to be used as background in hex 000000 - FFFFFF', required=False, default=None)
  args = vars(parser.parse_args())
  
  #files = sys.argv[1:]
  idx = args['index']
  w = args['width']
  h = args['height']
  outfile = open(args['output'], 'w')
  glyphs = []
  if len(args['files']) > 0:
    for file in args['files']:
      g = Glyph(file, idx)
      glyphs.append(g)
      idx += len(g.layers)
      if g.width > w: w = g.width
      if g.height > h: h = g.height
  outfile.write(f_header(w,h, idx))
  for glyph in glyphs:
    outfile.write(str(glyph))
  outfile.write("ENDFONT")
