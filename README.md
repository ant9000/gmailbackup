backup for your Gmail account, using Python's imaplib
-----------------------------------------------------

Quite a few solutions exist for taking a backup of your IMAP account, but they were designed with IMAP folders in mind.

Any of them will work for Gmail too, but due to the semantic difference between Gmail labels and standard IMAP folders, a message will be backed up once for each label it has: a huge waste of disk space if you, like us, use often multiple labels on a single email.

Our approach is extremely simple: every email gets saved in a single local directory (path_to_app/gmail/MailStore/ by default). The original structure of your accounts (yes, multiple accounts are supported!) is stored in the same directory, inside a SQLite database (named gmail.db by default) where we also store the state of our last backup.

We know that this kind of storage is not usable directly from any email client (which is actually a good thing - since it is a backup, you shouldn't mess with it at all!). On the pros side: it is simple to understand, to copy, and is as cross-platform as it could possibly be. Moreover, it might not be too difficult to implement a read-only IMAP server on top of it, by leveraging the existing Twisted implementation of the protocol.

A first version is available in the Downloads section; it works from the command line only for now, stores a local backup of your IMAP account, but is not yet able to restore it. The code is certainly not well polished, but works pretty well in practice: it is able to handle the frequent IMAP disconnections of Gmail, and if you kill it, next time it will restart its job from where it was interrupted.

This version has been developed on Linux (Debian Lenny), and tested also on Windows XP; of course, it requires Python (tested with Python 2.5, but should work without problems under 2.6 too). I don't have OSX available, but apart from minor quirks I would expect the code to work there too (any Mac user willing to give it a shot?)

INSTALL GUIDE: download, decompress it somewhere, launch backup_gmail.py and follow the instructions.

On our TODO list: * the restore functionality! * a web based interface to complement the current CLI one, for mouse-needing people * support for pruning no longer needed local files

