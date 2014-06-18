doublewrap
==========

SOFTWARE IS PROVIDED AS IS. NO WARRANTY.

Wrapper for the duplicity backup program

doublewrap.py can be execute from the command line

run doublewrap.py --help for argument info

This wrapper requires a config file.
The default file location is ~/.config/doublewrap.conf

An example config file

    [PATHS]
        #list any files or directories to back up, giving each it's own line
        ~/Music
        ~/Pictures
    [DESTINATION]
        # Host is a valid ssh target
        Host = localhost
        # backup_root is the relative location of the backup
        backup_root = backup

        #poorly/not tested options
        #User = user
        #Port = port
    [AUTH]
        #keyid is a gpg recognized key id used for the backup
        keyid = 12345678

        #Untested options
        
        #currently the only way to use a passphrase protected key
        #this is not recommended, as the passphrase is stored
        #as an environment variable

        #prompt_for_passphrase = True
