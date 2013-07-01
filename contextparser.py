# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from HTMLParser import HTMLParser

#==============================================================================
class Element(object):
    #--------------------------------------------------------------------------
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = {}
        for attr in attrs:
            self.attrs[attr[0]] = attr[1]

#==============================================================================
class ContextParser(HTMLParser):
    #--------------------------------------------------------------------------
    def __init__(self):
        HTMLParser.__init__(self)
        self.m_elements = []

    #--------------------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self.m_elements.append(Element(tag, attrs))
        self.startElement(tag, attrs)

    #--------------------------------------------------------------------------
    def handle_endtag(self, tag):
        self.endElement(tag)
        self.m_elements.pop()

    #--------------------------------------------------------------------------
    def handle_data(self, data):
        pass # TODO?

    #--------------------------------------------------------------------------
    def startElement(self, name, attrs):
        pass

    #--------------------------------------------------------------------------
    def endElement(self, name):
        pass

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
