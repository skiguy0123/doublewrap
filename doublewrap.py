#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals
import subprocess as sp
import os
import sys
if sys.version_info.major < 3.:
    import ConfigParser as configparser
else:
    import configparser
import logging
import getpass
import argparse
import time
import shutil


class DuplicityWrapper(object):

    def __init__(self, cfg_file, verbosity=0):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

        c = configparser.ConfigParser(allow_no_value=True)
        c.optionxform = lambda option: option  # Preserve case
        cfg_file = os.path.expanduser(cfg_file)
        if not os.path.exists(cfg_file):
            raise RuntimeError('{} does not exist.'.format(cfg_file))
        c.read(cfg_file)

        required_sections = {'AUTH': ['keyid'], 'DESTINATION': ['Host'], 'PATHS': []}
        for section, subsections in required_sections.items():
            if section not in c.sections():
                raise RuntimeError('{} not found in {}'.format(section, cfg_file))
            for subsection in subsections:
                if subsection not in c.options(section):
                    raise RuntimeError('{} not found in {} section of {}'.format(subsection, section, cfg_file))

        if 'promt_for_passphrase' in c.options('AUTH') and c.getboolean('AUTH', 'prompt_for_passphrase'):
            print('Warning, passphrase is stored as an environment variable', file=sys.stderr)
            os.environ['PASSPHRASE'] = getpass.getpass()
        else:
            os.environ['PASSPHRASE'] = ''

        srcs = []
        for dir_ in c.options('PATHS'):
            dir_adj = os.path.expanduser(dir_)
            if not os.path.exists(dir_adj):
                print('{} does not exists'.format(dir_), file=sys.stderr)

            srcs.append(dir_adj)

        host = c.get('DESTINATION', 'Host')

        keyid = c.get('AUTH', 'keyid')

        ssh_cmd = ['ssh', '-qt']

        self.port = None
        if 'Port' in c.options('DESTINATION'):
            self.port = c.get('DESTINATION', 'Port')
            ssh_cmd.append('-p')
            ssh_cmd.append(self.port)

        tmp = ''
        if 'User' in c.options('DESTINATION'):
            tmp += c.get('DESTINATION', 'User')
            tmp += '@'
        tmp += host
        ssh_cmd.append(tmp)

        self.ssh_cmd = ssh_cmd

        if 'backup_root' in c.options('DESTINATION'):
            self.backup_root = c.get('DESTINATION', 'backup_root')
            # if self.backup_root[0] == '~' or self.backup_root[0] == '/':
            #    raise ValueError('backup_root must be specified relative to starting directory on remoted (no leading ~/ or /')
            self.logger.info('Checking for {} on remote'.format(self.backup_root))
            self.checkAndMake(*os.path.split(self.backup_root))
        else:
            self.backup_root = ''

        self.c = c
        self.host = host
        self.keyid = keyid
        self.srcs = srcs
        self.base_duplicity_cmd = ['duplicity',
                                   '--encrypt-key', self.keyid,
                                   '--encrypt-sign-key', self.keyid,
                                   '--verbosity', str(verbosity)]

        if self.port is not None:
            portstr = ':{}'.format(self.port)
        else:
            portstr = ''
        self.deststr = 'rsync://{}{}/{}'.format(self.host, portstr, self.backup_root)

        self.filespec = []
        [self.filespec.extend(['--include', src]) for src in self.srcs]
        self.filespec.append('--exclude')
        self.filespec.append('/')

    def remoteLs(self, dir_=None):
        ls_cmd = list(self.ssh_cmd)
        ls_cmd.extend(['ls', '-a'])
        if dir_ is not None:
            ls_cmd.append(dir_)
        self.logger.info('executing {}'.format(' '.join(ls_cmd)))
        return sp.check_output(ls_cmd).decode().split()

    def checkAndMake(self, loc_to_check, dir_):
        remote_ls = self.remoteLs(loc_to_check)
        if dir_ not in remote_ls:
            mkdir_cmd = list(self.ssh_cmd)
            mkdir_cmd.append('mkdir')
            if loc_to_check != '':
                mkdir_cmd.append(os.path.join(loc_to_check, dir_))
            else:
                mkdir_cmd.append(dir_)
            self.logger.info('executing {}'.format(' '.join(mkdir_cmd)))
            sp.check_call(mkdir_cmd)
            remote_ls = self.remoteLs(loc_to_check)
            if dir_ not in remote_ls:
                raise RuntimeError('Unable to create {} in {} at remote'.format(dir_, loc_to_check))
            return False
        return True

    def dirContainsSigs(self, dir_):
        for file_ in self.remoteLs(dir_):
            if 'duplicity-full-signatures' in file_:
                return True
        return False

    def runAndLog(self, cmd, yieldoutput=False):
        self.logger.info('Running command {}'.format(' '.join(cmd)))
        p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        if yieldoutput:
            return self._runAndLogYield(p, cmd)
        else:
            self._runAndLogQuiet(p, cmd)

    def _runAndLogYield(self, p, cmd):
        try:
            for l in p.stdout:
                l_str = l.strip().decode()
                self.logger.info(l_str)
                yield l_str
        finally:
            # ensures that cleanup is run even if generator
            # isn't exhausted
            self._cleanup(p, cmd)

    def _runAndLogQuiet(self, p, cmd):
        for l in p.stdout:
            l_str = l.strip().decode()
            self.logger.info(l_str)
        self._cleanup(p, cmd)

    def _cleanup(self, p, cmd):
        out = p.stderr.read().decode()
        p.stderr.close()
        p.stdout.close()
        if p.wait() != 0:
            raise sp.CalledProcessError(p.returncode, cmd, output=out)

    def backup(self, *args):

        backup_cmd = list(self.base_duplicity_cmd)
        if self.dirContainsSigs(self.backup_root):
            # file already existed
            backup_cmd.insert(1, 'incr')
        else:
            backup_cmd.insert(1, 'full')
        for arg in args:
            backup_cmd.append(arg)
        backup_cmd.extend(self.filespec)
        backup_cmd.append('/')
        backup_cmd.append(self.deststr)
        self.runAndLog(backup_cmd)

    def restore(self, target, file_=None, time_=None):
        restore_cmd = list(self.base_duplicity_cmd)
        restore_cmd.insert(1, 'restore')
        if file_ is not None:
            restore_cmd.append('--file-to-restore')
            restore_cmd.append(file_)
        if time_ is not None:
            restore_cmd.append('--restore-time')
            restore_cmd.append(str(time_))
        restore_cmd.append(self.deststr)
        restore_cmd.append(target)
        self.runAndLog(restore_cmd)

    def listfiles(self, time_=None):
        list_cmd = list(self.base_duplicity_cmd)
        list_cmd.insert(1, 'list')
        if time_ is not None:
            list_cmd.append('--restore-time')
            list_cmd.append(str(time_))
        list_cmd.append(self.deststr)
        return self.runAndLog(list_cmd, yieldoutput=True)

    def verify(self):
        verify_cmd = list(self.base_duplicity_cmd)
        verify_cmd.insert(1, 'verify')
        verify_cmd.extend(self.filespec)
        verify_cmd.append(self.deststr)
        verify_cmd.append('/')
        self.runAndLog(verify_cmd)

    def status(self, display=True):
        if not display:
            out = []
        for line in self._iterstatus():
            if display:
                print(line)
            else:
                out.append(line)
        if not display:
            return out

    def _iterstatus(self):
        status_cmd = list(self.base_duplicity_cmd)
        status_cmd.insert(1, 'collection-status')
        status_cmd.append(self.deststr)
        return self.runAndLog(status_cmd, yieldoutput=True)

    def _getTimes(self):
        for l in self._iterstatus():
            ls = l.split()
            if len(ls) > 0 and ls[0] in ['Full', 'Incremental']:
                yield int(time.mktime(time.strptime(' '.join(ls[1:6]), '%a %b %d %H:%M:%S %Y')))

    def restoreGit(self, dir_, file_, target):
        if os.path.exists(dir_):
            if len(os.listdir(dir_)) > 0:
                raise RuntimeError('{} exists and is not empty. exiting'.format(dir_))
        else:
            os.mkdir(dir_)
        self._gitinit(dir_)
        self._gitcfg(dir_)
        fulltar = os.path.join(dir_, target)
        for time_ in self._getTimes():
            if self._fileInRepo(file_, time_):
                if os.path.exists(fulltar):
                    if os.path.isdir(fulltar):
                        shutil.rmtree(fulltar)
                    else:
                        os.remove(fulltar)
                self.restore(fulltar, file_, time_)
                self._gitadd(dir_, target)
                if self._gitmod(dir_, target):
                    self._gitcommit(dir_, time_)

    def _fileInRepo(self, file_, time_):
        for l in self.listfiles(time_=time_):
            if len(l) > 0 and file_ == l.split()[-1]:
                return True
        else:
            return False

    def _gitcfg(self, dir_):
        sp.check_call(['git', 'config', 'user.name', 'autorecovery'], cwd=dir_)
        sp.check_call(['git', 'config', 'user.email', 'autorecovery'], cwd=dir_)

    def _gitinit(self, dir_):
        sp.check_output(['git', 'init'], cwd=dir_)

    def _gitadd(self, dir_, target):
        sp.check_call(['git', 'add', target], cwd=dir_)

    def _gitmod(self, dir_, target):
        status = sp.check_output(['git', 'status', '--porcelain', target], cwd=dir_)
        for line in status.decode().split('\n'):
            if len(line) > 0:
                s = line.split()[0]
                if s in ['M', 'A']:
                    return True
        return False

    def _gitcommit(self, dir_, time_):
        message = 'Time: {}'.format(time.ctime(time_))
        sp.check_call(['git', 'commit', '-q', '-m', message], cwd=dir_)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wrapper for duplicity')
    parser.add_argument('-c', '--config_file', dest='config_file', type=str, default='~/.config/doublewrap.conf',
                        help='Config file location')
    parser.add_argument('-v', '--verbosity', dest='v', default=0, type=int,
                        help='between 0 (no output) to 9 (full output)')
    subparsers = parser.add_subparsers()
    backup_p = subparsers.add_parser('backup', help='Run backup')
    backup_p.set_defaults(func=DuplicityWrapper.backup)
    backup_p.set_defaults(action='backup')
    list_p = subparsers.add_parser('list', help='List backed up files')
    list_p.set_defaults(func=DuplicityWrapper.listfiles)
    list_p.set_defaults(action='list')
    restore_p = subparsers.add_parser('restore', help='Restore file(s)')
    restore_p.set_defaults(func=DuplicityWrapper.restore)
    restore_p.set_defaults(action='restore')
    restore_p.add_argument('-f', '--file', dest='file_')
    restore_p.add_argument('target')
    verify_p = subparsers.add_parser('verify', help='')
    verify_p.set_defaults(func=DuplicityWrapper.verify)
    verify_p.set_defaults(action='verify')
    status_p = subparsers.add_parser('status', help='')
    status_p.set_defaults(func=DuplicityWrapper.status)
    status_p.set_defaults(action='status')
    gitrestore_p = subparsers.add_parser('gitrestore', help='restore all backed up versions to a git repository')
    gitrestore_p.set_defaults(action='restoreGit')
    gitrestore_p.set_defaults(func=DuplicityWrapper.restoreGit)
    gitrestore_p.add_argument('file_to_restore', type=str)
    gitrestore_p.add_argument('git_directory', type=str, help='directory either must not exist or be empty')
    gitrestore_p.add_argument('target', type=str, help='name of file restored file')
    args = parser.parse_args()
    # 0-1 -> 40
    # 2-3 -> 30
    # 4-8 -> 20
    # 9 -> 10
    v = args.v
    if v <= 0:
        loglevel = 40
    elif v <= 3:
        loglevel = int((3 - v) * 10. / 3. + 30)
    elif v <= 8:
        loglevel = int((8 - v) * 2 + 20)
    elif v > 8:
        loglevel = 10
    logging.basicConfig(level=loglevel)
    dw = DuplicityWrapper(args.config_file, verbosity=v)
    arglist = []
    if args.action == 'restore':
        arglist.append(args.target)
        if 'file_' in args:
            arglist.append(args.file_)
    elif args.action == 'restoreGit':
        arglist.append(args.git_directory)
        arglist.append(args.file_to_restore)
        arglist.append(args.target)

    try:
        out = args.func(dw, *arglist)
    except RuntimeError as r:
        print(r, file=sys.stderr)
        sys.exit(1)
    except sp.CalledProcessError as s:
        print(s, file=sys.stderr)
        sys.exit(1)
    if out is not None:
        for l in out:
            print(l)
