#!/usr/bin/python

'''
Convert Thunderbird LDIF to vCard 3.0 suitable for use with iCloud.

Author: Xavier Zelf <ldif2vc3@vintius.neomailbox.net>
'''

import argparse
import ldif
import os
import re
import sys
import vobject

from cStringIO import StringIO
from datetime import datetime
from vobject.vcard import Address

_args = None                     # global parsed arguments

# Name of the LDIF field where you store contacts' ringtone names.  If
# you're already using "Custom 1" for something else, just edit this.
# (Not quite enough to justify adding support for a config file.)
#
# By the way, Thunderbird does not export "Extra field N" fields.
# Only "Custom N" fields.  I'm sure there's an excellent reason.
#
LDIF_RINGTONE = 'mozillaCustom1'

class AppError(Exception):
    pass

def _dbg(*args):
    '''Print a verbose log message.'''
    if _args.verbose:
        print >>sys.stderr, ' '.join(map(str, args))

def to_utf8(x):
    '''Helper function to decode str or [str, ...] into UTF-8.'''
    def ff(x):
        return unicode(x, 'utf-8')
    if isinstance(x, basestring):
        return ff(x)
    return map(ff, x)


class DnFixer(object):
    '''A filter for fixing 'dn: ...' lines before ldif sees them.

    The ldif module just hates embedded commas (ones not separating
    components of the distinguished name).
    '''
    def __init__(self, fil):
        self._input_file = fil
    def readline(self):
        line = self._input_file.readline()
        if line is not None and line.startswith('dn:'):
            return line.replace(', ', r'\, ')
        return line


class VCardBuilder(object):

    '''Embodies rules for building a vCard from LDIF entry fields.'''

    unsupported_fields = set()

    def __init__(self):
        self.vcard = vobject.vCard()
        self.memos = dict()

    # Name stuff
    def _put_cn(self, val):
        self.vcard.add('fn').value = val[0]
    def _put_givenName(self, val):
        self.memos['givenName'] = val[0]
    def _put_mozillaNickname(self, val):
        self.vcard.add('nickname').value = val[0]
    def _put_sn(self, val):
        self.memos['sn'] = val[0]
    def _put_title(self, val):
        self.vcard.add('title').value = val[0]

    # Phone 'n email stuff
    def _put_homePhone(self, val):
        tel = self.vcard.add('tel')
        tel.value = val[0]
        tel.type_param = 'HOME'
    def _put_mobile(self, val):
        tel = self.vcard.add('tel')
        tel.value = val[0]
        tel.type_param = 'CELL'
    def _put_mail(self, val):
        em = self.vcard.add('email')
        em.value = val[0]
        em.type_paramlist = ['INTERNET', 'PREF']
    def _put_mozillaSecondEmail(self, val):
        em = self.vcard.add('email')
        em.value = val[0]
        em.type_param = 'INTERNET'
    def _put_telephoneNumber(self, val):
        tel = self.vcard.add('tel')
        tel.value = val[0]
        tel.type_param = 'WORK'
    def _put_facsimiletelephonenumber(self, val):
        tel = self.vcard.add('tel')
        tel.value = val[0]
        tel.type_param = 'FAX'
    def _put_pager(self, val):
        tel = self.vcard.add('tel')
        tel.value = val[0]
        tel.type_param = 'PAGER'
    def _put_ringtone(self, val):
        tone = val[0].strip()
        if ":" not in tone:
            tone = "system:%s" % tone
        if " " in tone:
            tone = '"%s"' % tone
        alert = self.vcard.add('x-activity-alert')
        alert.value = "type=call,snd=%s" % tone
        self.memos['ringtone'] = True
    def _put_mozillaHomeUrl(self, val):
        url = self.vcard.add('url')
        url.type_param = 'HOME'
        url.value = val[0]
    def _put_mozillaWorkUrl(self, val):
        url = self.vcard.add('url')
        url.type_param = 'WORK'
        url.value = val[0]

    # You say it's your birthday?!  Happy birthday to you!!!
    def _put_birthyear(self, val):
        self.memos.setdefault('bday', ['????', '??', '??'])[0] = val[0]
    def _put_birthmonth(self, val):
        self.memos.setdefault('bday', ['????', '??', '??'])[1] = val[0]
    def _put_birthday(self, val):
        self.memos.setdefault('bday', ['????', '??', '??'])[2] = val[0]

    # Address stuff.  Seven items per RFC-2426 section 3.2.1.
    def _put_mozillaHomePoBox(self, val): # not its real name
        self.memos.setdefault('homeAddr', Address()).box = val[0]
    def _put_mozillaHomeExtended(self, val): # not its real name
        self.memos.setdefault('homeAddr', Address()).extended = val[0]
    def _put_mozillaHomeStreet(self, val):
        self.memos.setdefault('homeStreet', []).append(val[0])
        self.memos.setdefault('homeAddr', Address())
    def _put_mozillaHomeStreet2(self, val):
        self.memos.setdefault('homeStreet2', []).append(val[0])
        self.memos.setdefault('homeAddr', Address())
    def _put_mozillaHomeLocalityName(self, val):
        self.memos.setdefault('homeAddr', Address()).city = val[0]
    def _put_mozillaHomeState(self, val):
        self.memos.setdefault('homeAddr', Address()).region = val[0]
    def _put_mozillaHomePostalCode(self, val):
        self.memos.setdefault('homeAddr', Address()).code = val[0]
    def _put_mozillaHomeCountryName(self, val):
        self.memos.setdefault('homeAddr', Address()).country = val[0]
    def _put_street(self, val):
        self.memos.setdefault('workStreet', []).append(val[0])
        self.memos.setdefault('workAddr', Address())
    def _put_mozillaWorkStreet2(self, val):
        self.memos.setdefault('workStreet2', []).append(val[0])
        self.memos.setdefault('workAddr', Address())
    def _put_l(self, val):
        self.memos.setdefault('workAddr', Address()).city = val[0]
    def _put_st(self, val):
        self.memos.setdefault('workAddr', Address()).region = val[0]
    def _put_postalCode(self, val):
        self.memos.setdefault('workAddr', Address()).code = val[0]
    def _put_c(self, val):
        self.memos.setdefault('workAddr', Address()).country = val[0]

    # Miscellaneous stuff
    def _put_description(self, val):
        note = val[0].strip()
        if note:
            self.vcard.add('note').value = note
    def _put_nsAIMid(self, val):
        # Can't find any clue in RFC-2426 so just append a note.
        note = 'AIM: %s' % val[0].strip()
        self.vcard.add('note').value = note
    def _put_o(self, val):
        self.memos['org'] = val[0]
    def _put_ou(self, val):
        self.memos.setdefault('ou', []).extend(val)
    def _put_modifytimestamp(self, val):
        if int(val[0]) != 0:
            rev = self.vcard.add('rev')
            rev.value = (datetime.utcfromtimestamp(float(val[0])).isoformat()
                         + 'Z') # Zulu time!
    def _put_objectclass(self, val):
        # We generally ignore these, but we do want to skip over group
        # aliases so if this is one of those, mark the vcard.
        if 'groupOfNames' in val:
            self.memos['skip'] = 1
    def _put_member(self, val):
        # We're going to skip this one anyway, it's in a groupOfNames.
        pass

    # Tricky multi-line street addresses, bah.
    def _build_street(self, kind):
        # Inputs: foo_street[], foo_street2[]
        # Outputs: foo Address.street, .extended, .box
        assert kind == 'home' or kind == 'work'
        parts = []
        adr = self.memos[kind + 'Addr']
        try:
            parts = self.memos[kind + 'Street']
        except KeyError:
            pass
        try:
            parts.extend(self.memos[kind + 'Street2'])
        except KeyError:
            pass
        lines = []
        for part in parts:
            for prt in map(unicode.strip, part.split(';')):
                lwr = prt.lower()
                if lwr.startswith('suite'):
                    adr.extended = prt
                elif lwr.startswith('apt.'):
                    adr.extended = prt
                elif lwr.startswith('p.o. box') or lwr.startswith('pob '):
                    adr.box = prt
                else:
                    # "Nth floor" is extended but "12 Foo St., Nth floor" not.
                    # If we were less lazy we'd parse it out.
                    m = re.match(ur'\w+\s+fl(oor|r|)$', lwr)
                    if m:
                        adr.extended = prt
                    else:
                        lines.append(prt)
        if lines:
            adr.street = lines

    # Public methods!
    def put(self, ldif_field, ldif_values):
        '''Ingest an LDIF field/value pair.'''
        _dbg('Put:', ldif_field, 'is', ldif_values)
        method = '_put_%s' % ldif_field
        try:
            VCardBuilder.__dict__[method](self, to_utf8(ldif_values))
        except KeyError:
            print >>sys.stderr, 'No support (yet) for', ldif_field
            VCardBuilder.unsupported_fields.add(ldif_field)

    def build(self):
        '''Compute derived fields and return completed vCard.'''
        if 'skip' in self.memos:
            _dbg('Skipping:', self.vcard.contents)
            return None
        _dbg('Building:', self.vcard.contents)
        if not 'n' in self.vcard.contents:
            if 'sn' in self.memos and 'givenName' in self.memos:
                self.vcard.add('n').value = vobject.vcard.Name(
                    family=self.memos['sn'], given=self.memos['givenName'])
            elif 'fn' in self.vcard.contents:
                self.vcard.add('n').value = vobject.vcard.Name(
                    self.vcard.fn.value)
        if 'homeAddr' in self.memos:
            self._build_street('home')
            a = self.vcard.add('adr')
            a.value = self.memos['homeAddr']
            a.type_param = 'home'
        if 'workAddr' in self.memos:
            self._build_street('work')
            a = self.vcard.add('adr')
            a.value = self.memos['workAddr']
            a.type_param = 'work'
        if 'bday' in self.memos:
            self.vcard.add('bday').value = '-'.join(self.memos['bday'])
        orgvals = []
        if 'org' in self.memos:
            orgvals.append(self.memos['org'])
        if 'ou' in self.memos:
            orgvals.extend(self.memos['ou'])
        if orgvals:
            o = self.vcard.add('org')
            o.value = orgvals
        # Even if the vcard has no 'tel' entries, it's good to set the
        # ringtone.  Otherwise if you add a phone number via your
        # iPhone, you'll get the default ringtone... which is probably
        # "Silence" if you're using the --ringtone option at all.
        if _args.ringtone and 'ringtone' not in self.memos:
            self._put_ringtone([_args.ringtone])
        return self.vcard


class TBirdParser(ldif.LDIFParser):
    '''
    Parse Thunderbird LDIF address books.
    '''
    def handle(self, dn, entry):
        '''Transmute parsed LDIF entry into vCard 3.0.'''
        _dbg('DN:', dn)
        _dbg('Entry:', entry)
        _dbg()
        vcb = VCardBuilder()
        for field in entry:
            key = 'ringtone' if field == LDIF_RINGTONE else field
            vcb.put(key, entry[field])
        vc = vcb.build()
        if vc:
            print vc.serialize()


def _process():
    '''Main program logic.'''
    if _args.outfile != '-':
        sys.stdout.close()
        sys.stdout = open(_args.outfile, 'w')
    for f in _args.infiles:
        if f == '-':
            tbp = TBirdParser(DnFixer(sys.stdin))
            tbp.parse()
        else:
            with open(f) as F:
                tbp = TBirdParser(DnFixer(F))
                tbp.parse()
    # Maybe more VCardBuilder._put_foo methods are needed?
    if VCardBuilder.unsupported_fields:
        print >>sys.stderr, 'Unsupported fields:'
        print >>sys.stderr, '\n'.join(VCardBuilder.unsupported_fields)
    return 0

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(prog=os.path.basename(argv[0]))
    parser.add_argument('-o', '--output', action='store', dest='outfile',
                            default='-', help='Output file')
    parser.add_argument('-r', '--ringtone', default="",
                        help="""Use this ringtone for contacts that don't
                                explicitly specify one.""")
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='Print debug info to stderr')
    parser.add_argument('infiles', nargs='+', help='Input file(s)')
    global _args
    _args = parser.parse_args(argv[1:])

    try:
        return _process()
    except AppError as e:
        print >>sys.stderr, e
        return 2

if __name__ == '__main__':
    sys.exit(main())
