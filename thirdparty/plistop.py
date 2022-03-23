"""
Fast lxml-based XML plist reader/editor.
"""

import datetime
import iso8601
import lxml.etree

__all__ = ['parse', 'factory', 'dumps', 'dict', 'array']

template = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
             '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
            '<plist version="1.0"/>')


def _elem(tag, text=None):
    """Create an lxml.xml.Element.
    """
    elem = lxml.etree.Element(tag)
    if text is not None:
        elem.text = text
    return elem


class PListArray(object):
    def __init__(self, elem):
        self.elem = elem

    def __len__(self):
        return len(self.elem)

    def __getitem__(self, idx):
        return factory(self.elem[idx])

    def __setitem__(self, idx, value):
        if isinstance(idx, slice):
            self.elem.__setitem__(idx, list(map(collapse, value)))
        else:
            self.elem[idx] = collapse(value)

    def __iter__(self):
        return (factory(e) for e in self.elem)

    def append(self, other):
        self.elem.append(collapse(other))


class PListDict(object):
    def __init__(self, elem):
        self.elem = elem

    def __len__(self):
        return len(self.elem) / 2

    def _findValue(self, key):
        for child in self.elem:
            if child.tag == 'key' and child.text == key:
                return child.getnext()

    def __getitem__(self, key):
        elem = self._findValue(str(key))
        if elem is None:
            raise KeyError(key)
        return factory(elem)

    def __setitem__(self, key, value):
        elem = self._findValue(key)
        if elem:
            self.elem.remove(elem.getprevious())
            self.elem.remove(elem)
        collapsed = collapse(value)
        self.elem.append(_elem('key', str(key)))
        self.elem.append(collapsed)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self):
        return (e.text for e in self.elem.findall('./key'))
    iterkeys = __iter__

    def keys(self):
        return list(self)

    def itervalues(self):
        return (factory(e) for e in self.elem if e.tag != 'key')

    def values(self):
        return list(self.values())

    def iteritems(self):
        it = iter(self.elem)
        return ((elem.text, factory(next(it))) for elem in it)


def collapse(v):
    if isinstance(v, str):
        return _elem('string', v)
    elif isinstance(v, float):
        return _elem('real', str(v))
    elif isinstance(v, int):
        return _elem('integer', str(v))
    elif isinstance(v, datetime.datetime):
        return _elem('date', v.isoformat())
    elif isinstance(v, bool):
        return _elem(str(v).lower(), None)
    elif isinstance(v, str):
        return _elem('data', v.encode('base64'))
    elif isinstance(v, (list, PListArray)):
        parent = _elem('array')
        for subv in v:
            parent.append(subv)
        return parent
    elif isinstance(v, (dict, PListDict)):
        parent = _elem('dict')
        for key, value in v.items():
            parent.append(_elem('key', str(key)))
            parent.append(collapse(value))
        return parent
    else:
        raise TypeError('%r is not supported.' % (type(v),))


TYPES = {
    'string':   lambda elem: elem.text,
    'real':     lambda elem: float(elem.text),
    'integer':  lambda elem: int(elem.text),
    'date':     lambda elem: iso8601.parse_date(elem.text),
    'true':     lambda elem: True,
    'false':    lambda elem: False,
    'data':     lambda elem: elem.text.decode('base64'),
    'array':    PListArray,
    'dict':     PListDict
}


def factory(elem):
    """Given a PList value element, return a Python representation of its
    value."""
    return TYPES[elem.tag](elem)


def parse(fp):
    root = lxml.etree.parse(fp).getroot()
    if root.tag != 'plist':
        raise ValueError('root element is not a <plist>')
    return factory(root[0])


def dumps(obj):
    new_root = lxml.etree.fromstring(template)
    new_root.append(obj.elem)
    tree = new_root.getroottree()
    return lxml.etree.tostring(tree, xml_declaration=True, encoding='UTF-8')


def dict():
    return PListDict(lxml.etree.Element('dict'))


def array():
    return PListArray(lxml.etree.Element('array'))
