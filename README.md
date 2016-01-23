ldif2vc3.py
===========

Convert contact lists from LDIF (Thunderbird, etc.) to VCard 3.0
(Apple, etc.) format.  If you maintain your master contact list in
Thunderbird but use an iPhone, this script is for you.

Prerequisites
-------------

You'll need Python 2.7 or later and the vobject package, available on
PyPI at [link](https://pypi.python.org/pypi/vobject/) .  Actually it
may work with earlier versions of Python but I haven't tried it.

Once you've got that, clone this repository and move the *ldif2vc3.py*
script to your $HOME/bin directory.  Gee, I guess I'm kind of assuming
that you're a Linux/BSD/*nix user.  Yup.

How To Use It
-------------

 1. Open the Thunderbird address book with Ctrl-Shift-B.
 2. Select *Personal Address Book* (or any address you want, really) from the left-hand pane.
 3. Click on *Tools > Export*
 4. Save your addresses to a file in LDIF format.  Let's call it *myaddrs.ldif* .
 5. From your command shell, run *ldif2vc3.py myaddrs.ldif > myaddrs.vcf*
 6. Open a browser and log in to your iCloud account.
 7. Open the Contacts app.
 8. Optional: Click on the "gear" symbol in the lower left corner and choosing *Export vCard...* to save your current Apple contacts.
 9. Click on the "gear" and choose *Select All*
10. Click on the "gear" and choose *Delete* .  Goodbye, old Apple contacts!
11. Click on the "gear" and choose *Import vCard...*
12. Upload the *myaddrs.vcf* file you saved earlier.

That's it!  You've wiped your previous Apple contacts (first saving a
copy, because you are a careful frood) and replaced them with your
Thunderbird contact list.

Screen Out Calls From Telemarketers, Phishers, Scammers, and other Scum
-----------------------------------------------------------------------

Wouldn't it be great if you could silence incoming phone calls from
numbers not in your address book?  (Why oh why doesn't Apple provide
this feature?  Sigh.)  Well, now you can do it.  

The first step is to download and install a silent ringtone as the
default ringtone on your iPhone.  The second step is to use
ldif2vc3.py's -r/--ringtone option when doing your LDIF-to-vCard
conversion:

   $ ldif2vc3.py -r "Slow Rise" myaddrs.ldif > myaddrs.vcf

This marks every vCard that does not have an explicitly set ringtone
with the *Slow Rise* ringtone.  Hence every entry in *myaddrs.vcf*
will have a ringtone, and the default (silent!) ringtone will be used
for everyone else.

### How do I set ringtones in Thunderbird?

Just pick your favorite otherwise-useless Thunderbird address book
field and put ringtone names there.  By default, ldif2vc3.py uses the
*mozillaCustom1* field, settable via the *Other* tab when you are
editing a contact.  You can change this by editing the script and
setting the value of LDIF_RINGTONE to something else.

These ringtones will be left alone when ldif2vc3.py runs.  Hence
incoming callers fall into three categories:

 1. those with special ringtones you set up in Thunderbird,
 2. those in your contact list, who get the default ringtone you set with -r ,
 3. those not in your contact list, who get the silent treatment.

### Don't forget: sometimes you **DO** want strangers to call!

If you're expecting a call from someone not in your address book,
don't forget to set your iPhone's default ringtone back to something
audible.  Restaurants want to call you when your table is ready;
kidnappers (probably) won't be in your address book, etc. etc.

Have Fun And Stay Safe!
-----------------------

Zelf out.
