#! /usr/bin/python

import Image
import sys, argparse
import logging

class Font:
  def __init__(self, fontname='Font', index=0, width=0, height=0, xoffset=0, yoffset=0, ascent=None, descent=0):
    self.fontname = fontname
    self.start = index
    self.width = width
    self.height = height
    self.ascent = ascent or height
    self.descent = descent
    self.minx = width
    self.maxx = 0
    self.miny = height
    self.maxy = 0
    self.glyphs = []

  def addGlyph(self, glyph):
    ''' Process Glyph for proper dimensions '''
    if self.start + len(self.glyphs) > 255:
      logging.error("Too many glyphs.  Ignoring...")
      return False
    if glyph.width > self.width or glyph.height > self.height:
       logging.critical("Glyph is too large for font structure.")
       sys.exit()
    glyph.idx = self.start + len(self.glyphs)
    self.glyphs.append(glyph)

  def getBBX(self):
    for glyph in self.glyphs:
      if glyph.minx < self.minx:
        self.minx = glyph.minx
      if glyph.miny < self.miny:
        self.miny = glyph.miny
      if glyph.maxx > self.maxx:
        self.maxx = glyph.maxx
      if glyph.maxy > self.maxy:
        self.maxy = glyph.maxy
    width = self.maxx - self.minx + 1
    height = self.maxy - self.minx + 1
    return (width, height, self.minx, self.miny)
    

  def getBDFstr(self):
    output = "STARTFONT 2.1\n"
    output += "FONT %s\n" % self.fontname
    output += "SIZE %d 96 96\n" % self.width # Almost useless as this is for X-windows
    output += "FONTBOUNDINGBOX %d %d %d %d\n" % (self.width, self.height, 0, 0)
    #self.getBBX()
    output += "STARTPROPERTIES 2\n"
    output += "FONT_ASCENT %d\n" % self.ascent
    output += "FONT_DESCENT %d\n" % self.descent
    output += "ENDPROPERTIES\n"
    output += "CHARS %d\n" % len(self.glyphs)
    for glyph in self.glyphs:
      output += glyph.getBDFstr()
    output += 'ENDFONT\n'
    return output

  def getu8glibstr(self):
    bbx = self.getBBX()
    end = self.start + len(self.glyphs) - 1
    font = [0,         # Font Format
           self.width, # FONTBOUNDINGBOX width
           bbx[1],     # FONTBOUNDINGBOX height
           bbx[2],     # FONTBOUNDINGBOX x-offset
           bbx[3],     # FONTBOUNDINGBOX y-offset
           self.height,# Capital A Height
           0,          # byte offset of encoding 65 'A' high byte
           0,          # byte offset of encoding 65 'A' low byte 
           0,          # byte offset of encoding 97 'a' high byte
           0,          # byte offset of encoding 97 'a' low byte
           self.start, # begin char idx 0-255
           end,        # end char idx 0-255
           0,          # lower g descent
           self.height,# max ascent
           0,          # min y = descent
           self.height,# x ascent
           0]          # x descent
    for glyph in self.glyphs:
      if glyph.idx == 65:
        byte = len(font)
        font[6] = (byte & 0xFF00) >> 8 
        font[7] = (byte & 0xFF) 
      if glyph.idx == 97:
        byte = len(font)
        font[8] = (byte & 0xFF00) >> 8 
        font[9] = (byte & 0xFF) 
      font.extend(glyph.getu8glibstr())
    
    fontstr = 'const uint8_t userfont[] = {\n'
    i = 0
    while i < len(font):
      fontstr += " %s\n" % ','.join(str(x) for x in font[i:i+16])
      i += 16
    fontstr += "};"
    return fontstr


def findboundbits(value, length):
  logging.error("Finding bounds for %s value %s" % (length, value))
  x = 0
  bits = [0,0]
  length -= 1
  while x <= length:
    if (value & 1) == 1:
      off = length - x
      if bits[1] == 0:
        print "Low bit %s" % off
        bits[1] = off
      bits[0] = off
    x += 1
    value = value >> 1
  return bits

class Glyph:
  def __init__(self, width=0, height=0, data=None, name=None):
    '''
    width    Width of overall glyph.  Blank columns will be reduced throuh BB calculation
    height   Height of overall glyph.  Blank rows will be reduced throuh BB calculation
    data     List or rows as integers
    name     Simple name to be used in the BDF file.
    '''
    self.idx = None
    self.name = name
    self.glyphwidth = width
    self.glyphheight = height
    self.width = 0
    self.height = 0
    self.dwidth = self.glyphwidth
    self.size = (self.glyphwidth + 7) / 8 # Size in bytes
    self.pad = (self.size * 8) - self.glyphwidth
    self.minx = width
    self.maxx = 0
    self.miny = height
    self.maxy = 0
    self.rows = []
    if data:
      self.processData(data)

  def getName(self):
    return (self.name or self.idx or 'Unknown')

  def getrowbytesarr(self, value):
    r = []
    for x in range(self.size):
      ''' Append each byte of the row '''
      shift = (self.size - 1 - x) * 8
      mask = 255 << shift
      r.append(int((value & mask) >> shift))
    return r

  def getrowhexbytes(self, value):
    row = self.getrowbytesarr(value)
    r = ''.join('%02x' % x for x in row)
    return r

  def processData(self, data):
    logging.error("Height: %s" % len(data))
    print data
    for a in range(len(data)):
      row = data[a]
      rint = 0
      if row > 0:
        # Shift row to full byte boundary
        if self.pad > 0:
          rint = row << self.pad
        else:
          rint = row >> (self.pad * -1)
          logging.error("%s shifts to %s" % (row, rint))
        # Determine minx and maxx
        (minx, maxx) = findboundbits(rint, self.size * 8)
        print minx, maxx
        if minx < self.minx: self.minx = minx
        if maxx > self.maxx: self.maxx = maxx
        #update miny/maxy
        logging.error("Maxy: %s, Len: %s, A: %s, RINT: %s" % (self.maxy, len(data), a, rint))
        if self.maxy == 0: 
          self.maxy = len(data) - a - 1
        else:
          print self.maxy
        self.miny = len(data) - a - 1
      if self.maxy > 0: 
        self.rows.append(rint) 
    self.width = self.maxx - self.minx + 1
    if (self.width + 7) / 8 < self.size:
      self.size = (self.width + 7) / 8
      self.pad = -1 *  (self.glyphwidth - self.minx - (self.size * 8))
      self.rows = []
      self.maxx = 0
      self.minx = self.size * 8
      self.maxy = 0
      self.miny = self.glyphheight
      logging.error("Reprocessing due to small width, shifting %s" % (-1 * self.pad))
      self.processData(data)
    # Reshift to bounding edge
    nrows = []
    for row in self.rows:
      nrows.append(row << self.minx)
    self.rows = nrows
    self.height = self.maxy - self.miny + 1
    logging.error("MaxX: %s, MinX: %s" % (self.maxx, self.minx))
    logging.error("MaxY: %s, MinY: %s" % (self.maxy, self.miny))
    logging.error("width: %s, height: %s" % (self.width, self.height))

  def getBBX(self):
    return (self.width, self.height, self.minx, self.miny)

  def getBDFstr(self):
    output = "STARTCHAR %s\n" % self.name
    output += "ENCODING %d\n" % self.idx
    output += "SWIDTH 500 0\n"
    output += "DWIDTH %d 0\n" % self.dwidth
    output += "BBX %d %d %d %d\n" % self.getBBX()
    output += "BITMAP\n"
    for row in self.rows:
      output += self.getrowhexbytes(row)
      # ''.join('%02x' % x for x in row)
      output += '\n'
    output += 'ENDCHAR\n'
    return output

  def getu8glibstr(self):
    data = [self.width,                # BBX width
            self.height,               # BBX height
            self.size * self.height,   # Glyph data size (bytes)
            self.dwidth,               # Glyph device width
            self.minx,                 # BBX x offset
            self.miny]                 # BBX y offset
    for row in self.rows:
      data.extend(self.getrowbytesarr(row))
    return data


class ImageFile:
  def __init__(self, sourcefile, alpha=255, binary=False, mask=None):
    '''
     Get color
     for each color
       create glyph
       get color data
    '''
    self.sourcefile = sourcefile
    self.height = None
    self.width  = None
    self.alpha = alpha
    self.binary = binary
    self.mask = mask
    self.colors = {}  # Colors
    self.image = None
    self.parseImage()
    
  def getcolors(self):
    palette = {}
    colors = self.image.getcolors()
    for color in colors:
      # No support for alpha channels, just drop them
      if color[1][3] >= self.alpha:
        c = self.t2h(color[1])
        if c[1:] != self.mask:
          print c[1:], self.mask
          self.colors[c] = [0] * self.image.size[0]
      else:
        print "Unsupported Alpha color: %s" % (color, )

  def parseImage(self):
    print "Reading image %s..." % self.sourcefile
    self.image = Image.open(self.sourcefile)
    # Attempt to convert to bitmap
    if self.binary:
      bg = Image.new('RGB', self.image.size, (255,255,255))
      bg.paste(self.image, mask=self.image.split()[3])
      self.image = bg.convert('1').convert('RGBA')
    # convert indexed images to RGBA
    if self.image.mode == 'P':
      self.image = self.image.convert('RGBA')
    self.height,self.width = self.image.size
    self.getcolors()
    x = y = 0
    pix = self.image.load()
    while y < self.height:
      while x < self.width:
        c = self.t2h(pix[x,y])
        if c:
          if c in self.colors:
            #self.colors[c][y] += (1 << ((self.padding * 4)-x-1))
            self.colors[c][y] += (1 << (self.width - x - 1))
        x+= 1
      x = 0
      y += 1

  def t2h(self, t):
    if t[3] >= self.alpha:
      return "#%02x%02x%02x" % t[:3]
    return None

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Converts a list of image files into color seperated font glyphs in a single BDF file')
  parser.add_argument('files', metavar='FILE', type=str, nargs='+')
  parser.add_argument('-n','--name', help='Output font file name', required=False, default="userfont")
  parser.add_argument('-o','--bdf', help='Output BDFR font file', required=False, action='store_true')
  parser.add_argument('-u','--u8glib', help='Output additional u8glib font file', required=False, action='store_true')
  parser.add_argument('-s','--start', help='Starting char number', type=int, required=False, default=32)
  parser.add_argument('-a','--alpha', help='Alpha threshold', type=int, required=False, default=255)
  parser.add_argument('-b','--binary', help='Convert images to b/w before processing', required=False, action='store_true')
  parser.add_argument('-H','--height', help='Total font height.  If an image is larger, this value will be overwritten', type=int, required=True, default=0)
  parser.add_argument('-W','--width', help='Total font width.  If an image is larger, this value will be overwritten', type=int, required=True, default=0)
  parser.add_argument('-c','--color', help='Color to be used as background in hex 000000 - FFFFFF', required=False, default=None)
  parser.set_defaults(u8glib=False)
  parser.set_defaults(binary=False)
  args = vars(parser.parse_args())
  
  #files = sys.argv[1:]
  idx = args['index']
  w = args['width']
  h = args['height']
  print w, h
  glyphs = []
  f = Font(fontname='UserFont', index=args['index'], width=w, height=h)

  if len(args['files']) > 0:
    for file in args['files']:
      i = ImageFile(file, args['alpha'], args['binary'], args['color'])
      for color in i.colors:
        g = Glyph(width=w, height=h, data=i.colors[color], name='%s-%s' % (file, color))
        f.addGlyph(g)

  if args['bdf']:
    outfile = open('%s.bdf' % args['name'], 'w')
    outfile.write(f.getBDFstr())
  if args['u8glib']:
    u8gfile = open('%s.u8g' % args['name'],'w')
    u8gfile.write(f.getu8glibstr())
