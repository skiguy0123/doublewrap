from __future__ import unicode_literals
from __future__ import print_function
import unittest
import subprocess
import tempfile
import os
import doublewrap
import filecmp
import shutil
import sys


CFG_CONTENT = '''
[PATHS]
{}
{}
[DESTINATION]
Host = localhost
backup_root = {}
[AUTH]
keyid = 33EA05F1
'''

KEY_FINGERPRINT = 'E490 B8B0 D8EC A34C 10AE  D442 7A4B 3644 33EA 05F1'.replace(' ', '')

PUBLIC_KEY = b'''-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v2

mI0EU54tfQEEAOaYMzAnppcwjmY868SQA0IDluBnnKRjmV4sK9Ydqv36fJ35cKT0
+qtSighPX434gdT5feAKlMjFJR8TJBDVjY9NvPE8lLBXaI9RRYFYUd21TlYQAFa/
4A27eRPy+drxpQV/LCqQChiEpBL2rtepPStfax7SqA4AMsfSDR8EbFN9ABEBAAG0
MmRvdWJsZXdyYXAgdGVzdGVyIChkb3VibGV3cmFwIHRlc3Qga2V5IERPIE5PVCBV
U0UpiLkEEwECACMFAlOeLX0CGwMHCwkIBwMCAQYVCAIJCgsEFgIDAQIeAQIXgAAK
CRB6SzZEM+oF8fV6A/4+1oDa3eXLz0cL7IvhpowELrY/ZlLTds/J867DAU3IP8u+
A/pOTMaZKkulS9vKi+d99FwduJZH07YwHLdsC+mZPSL/s/Izoxdi1on5pbSm0uKH
YfFrhF0HoGRI6rYYRdt/en2+O2WE4F9HBdOUe2Zffzh8K+iYSwStq4Ey21sCDbiN
BFOeLX0BBADm/HdaJZrtcr16S16sY3GItJ+CD160QDIAcDqDp4G+rvt3OnPX+jA8
9l2Bxs5ml1Jy/W10d3Au0KwAX7PGt7o4fLzWcBp3/Gn6wEt2BGtOsahbI/fh4Cn4
fuIbEPkq7O4LYCrIXgXLE3wYhpzfOr42GcVagFo3Renv3PsIbd6W5QARAQABiJ8E
GAECAAkFAlOeLX0CGwwACgkQeks2RDPqBfE7WwP+LDIYxfKUGhLe/dzns/3cBYsC
GkJazdgSrHkrz2kQkyRYhtUYa6WQh/2liqYiGlsvgmb/kCWGi+EVFBzwJIGbutEW
qBG1Aw2lOppkkhB9b0OQhondUg8HSDz0aOaw2B/0590pWjA1Ktu2EZYBQu5FIUjR
tIgSvrnFWX/boA2iny0=
=DAfY
-----END PGP PUBLIC KEY BLOCK-----'''


PRIVATE_KEY = b'''-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v2

lQHYBFOeLX0BBADmmDMwJ6aXMI5mPOvEkANCA5bgZ5ykY5leLCvWHar9+nyd+XCk
9PqrUooIT1+N+IHU+X3gCpTIxSUfEyQQ1Y2PTbzxPJSwV2iPUUWBWFHdtU5WEABW
v+ANu3kT8vna8aUFfywqkAoYhKQS9q7XqT0rX2se0qgOADLH0g0fBGxTfQARAQAB
AAP9HYf2Xj9ltU0Rn4RDyWuMD0M4akq6o87hkE7l2kj4YghXNz//rhB1ncU3SjMo
EJ13uxesiCmyvjeJNn6UCtfehfJ5q+Rjw03KErfEHhEIg3mfswYVfzUoYVDCXZci
it60TnmTWOzyCaU3b3mPpe8T1Q/zIkbUYQSNxeV0JIrkW90CAPCsBFoWlSp/09Oy
AumJsjG+57Myrv6OUHdQ60Eaed2cEwMJwVoBmLN+5pX1NNU97nouoalJThM7Kuhf
jik5HIMCAPVH4MYTXCCDktY4BlAUYMP5b1hdXrberD35irYzIvBfiSqb6gKra705
pjtbXvhsTq8+EW5YQezxcBlZzvypz/8B/3KCzMl4JJf9s8YlvVyqiGXLZtoBoQhu
tJy8xO2ehMLadH8AYD8Pen79iBpF0B/IV3tvRaLFTRQw83aNF6rj80WfYLQyZG91
Ymxld3JhcCB0ZXN0ZXIgKGRvdWJsZXdyYXAgdGVzdCBrZXkgRE8gTk9UIFVTRSmI
uQQTAQIAIwUCU54tfQIbAwcLCQgHAwIBBhUIAgkKCwQWAgMBAh4BAheAAAoJEHpL
NkQz6gXx9XoD/j7WgNrd5cvPRwvsi+GmjAQutj9mUtN2z8nzrsMBTcg/y74D+k5M
xpkqS6VL28qL5330XB24lkfTtjAct2wL6Zk9Iv+z8jOjF2LWifmltKbS4odh8WuE
XQegZEjqthhF2396fb47ZYTgX0cF05R7Zl9/OHwr6JhLBK2rgTLbWwINnQHYBFOe
LX0BBADm/HdaJZrtcr16S16sY3GItJ+CD160QDIAcDqDp4G+rvt3OnPX+jA89l2B
xs5ml1Jy/W10d3Au0KwAX7PGt7o4fLzWcBp3/Gn6wEt2BGtOsahbI/fh4Cn4fuIb
EPkq7O4LYCrIXgXLE3wYhpzfOr42GcVagFo3Renv3PsIbd6W5QARAQABAAP/XnOl
IFUZPXg6N5xDOc2uGr71LJs5WA6aA6jgnH4t5TmrNS1POmUhPYRmZw9SzguZmNC9
Za8DTflhJAP+QMdXG0QzOjlHrNaakKsAOa8sca/T5dixpsYmCLBxcyV8JXwopIgZ
lb+TsH1K3XKuRlerhYJrptyWCMMnAUy8GM/V6U8CAPLsKhGJ3FpIzOWItFF8ocsQ
wOHYWjQVva1h94cTykCEDgqvdT5nL3gArfQ9roqfevxzFyEKPzjfyc4W909O7F8C
APNrzTFRsnAaR4ghWyG9DgpRmluTmLJ3hdiXlwvwnKqxfEm3ZNyJKn93F2P7P7SY
yPUB0Qrd6kFEUhvGFv63AzsCAIXyusV6qb+Sv9psN8g0YpzG92QkfN9y3EMArdAt
Hz7/fBiu58eEP1AB1gCUY1tr0TAt7ddN2p3a6bHOq7r97/idkoifBBgBAgAJBQJT
ni19AhsMAAoJEHpLNkQz6gXxO1sD/iwyGMXylBoS3v3c57P93AWLAhpCWs3YEqx5
K89pEJMkWIbVGGulkIf9pYqmIhpbL4Jm/5AlhovhFRQc8CSBm7rRFqgRtQMNpTqa
ZJIQfW9DkIaJ3VIPB0g89GjmsNgf9OfdKVowNSrbthGWAULuRSFI0bSIEr65xVl/
26ANop8t
=GZK7
-----END PGP PRIVATE KEY BLOCK-----'''


class TestExecs(unittest.TestCase):

    def test_duplicity(self):
        subprocess.check_output(['duplicity', '--version'])

    def test_git(self):
        subprocess.check_output(['git', '--version'])

    def test_rsync(self):
        subprocess.check_output(['rsync', '--version'])

    def test_gpg(self):
        subprocess.check_output(['gpg', '--version'])

    def test_ssh(self):
        subprocess.check_output(['ssh', '-V'])


class Testdoublewrap(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.mkdtemp()
        cls.file1 = os.path.join(cls.tempdir, 'test1')
        cls.file1_copy = os.path.join(cls.tempdir, 'test1_copy')
        with open(cls.file1, 'w') as f:
            f.write('aaaaaaaaaa')
        shutil.copy(cls.file1, cls.file1_copy)
        cls.dir1 = os.path.join(cls.tempdir, 'test2')
        os.mkdir(cls.dir1)
        cls.file2 = os.path.join(cls.dir1, 'test3')
        with open(cls.file2, 'w') as f:
            f.write('bbbbbbbbb')
        backup_dir = os.path.join(cls.tempdir, 'backups')
        cls.cfg_name = os.path.join(cls.tempdir, 'test.cfg')
        with open(cls.cfg_name, 'w') as cfg:
            cfg.write(CFG_CONTENT.format(cls.file1, cls.dir1, backup_dir))
        for key in [PRIVATE_KEY]:
            p = subprocess.Popen(['gpg', '--dearmor'], stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            (dearmored_key, _) = p.communicate(key)
            p = subprocess.Popen(['gpg', '--import'], stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            p.communicate(dearmored_key)

    @classmethod
    def tearDownClass(cls):
        subprocess.check_output(['rm', '-rf', cls.tempdir])
        subprocess.check_output(['gpg', '--delete-secret-and-public-key',
                                '--yes', '--batch', KEY_FINGERPRINT])

    def setUp(self):
        self.dw = doublewrap.DuplicityWrapper(self.cfg_name, verbosity=9)

    def test_0init(self):
        pass

    def test_1bkup(self):
        self.dw.backup('--gpg-options', '--trust-model=always')

    def test_2listfiles(self):
        f = [l.split()[-1] for l in self.dw.listfiles() if len(l) > 0]
        self.assertTrue(self.file1[1:] in f)  # remove first /
        self.assertTrue(self.file2[1:] in f)

    def test_3verify(self):
        self.dw.verify

    def test_4verify(self):
        with open(self.file1, 'a') as f:
            f.write('\nmoretext')
        self.assertRaises(subprocess.CalledProcessError, self.dw.verify)

    def test_5restore(self):
        self.dw.backup('--gpg-options', '--trust-model=always')
        restored_f1 = os.path.join(self.tempdir, 'file1_restored')
        self.dw.restore(file_=self.file1[1:], target=restored_f1)
        if sys.version_info.major > 3.:
            filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.file1, restored_f1, shallow=False))

    def test_6restore(self):
        restored_f2 = os.path.join(self.tempdir, 'dir1_restored')
        self.dw.restore(file_=self.dir1[1:], target=restored_f2)
        if sys.version_info.major > 3.:
            filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.file2, os.path.join(restored_f2, os.path.split(self.file2)[1]), shallow=False))

    def test_7gitrestore(self):
        gitrestored = os.path.join(self.tempdir, 'dir1_gitrestored')
        os.mkdir(gitrestored)
        restored_f1 = os.path.join(gitrestored, 'file1_restored')
        self.dw.restoreGit(dir_=gitrestored, file_=self.file1[1:], target=restored_f1)
        if sys.version_info.major > 3.:
            filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.file1, restored_f1, shallow=False))
        with open(os.devnull, 'a') as null:
            subprocess.check_call(['git', 'checkout', 'master^'], stdout=null, stderr=null, cwd=gitrestored)
        self.assertTrue(filecmp.cmp(self.file1_copy, restored_f1, shallow=False))

    def test_8gitrestore(self):
        gitrestored = os.path.join(self.tempdir, 'dir2_gitrestored')
        os.mkdir(gitrestored)
        restored_d1 = os.path.join(gitrestored, 'dir1_restored')
        self.dw.restoreGit(dir_=gitrestored, file_=self.dir1[1:], target=restored_d1)
        if sys.version_info.major > 3.:
            filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.file2, os.path.join(restored_d1, 'test3'), shallow=False))


if __name__ == '__main__':
    unittest.main()
