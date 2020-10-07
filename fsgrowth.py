#!/usr/bin/python3
#
# fsgrowth - report the daily growth of filesystems through mail
#
#   Schedule in cron
#   Writes historical data to a PyStore collection
#   Sends a report every time it's run with delta, growth and projection
#   
# 
#------------------------------------------------------------------------------
# Imports {{{
import smtplib
import socket
import shutil
import os
import sys
import pystore

# }}}
# Config {{{
filesystems = ['/omd/data/archive08', '/omd/data/archive07']
interval = 1
environment = 'SEB'
hostname = socket.gethostname()
db = '/tmp/fsgrowth.db'

# SMTP server
smtphost = 'smtp.sebot.local'
smtpport = 25
smtpfrom = 'fsreport-seb@addpro.se'
smtprcvr = 'david.henden@addpro.se'

# }}}
# Script start {{{
data = ''
for fs in filesystems:
    try:
        [total, used, free] = shutil.disk_usage(fs)
        pct = floor((used / total) * 100)
        fsdata = '{}: {} {} {} {}'.format(fs, total, used, free, pct)
    except Exception as e:
        fsdata = '{}: {}'.format(fs, e)
    print(fsdata)
    data = '\n'.join([data, fsdata])


# }}}
# def sendmail(data): {{{
#------------------------------------------------------------------------------
def sendmail(data):
    """Send email report"""

    message = """Subject: {environment} file system growth report for {hostname}

{data}

/fsgrowth reporter on {hostname}
"""

    try:
        smtpserver = smtplib.SMTP(smtphost, smtpport)
        smtpserver.ehlo()
        smtpserver.sendmail(smtpfrom, smtprcvr, message
            .format(environment=environment, data=data, hostname=hostname))
    except Exception as e:
        print(e)
#    finally:
#        if smtpserver:
#            smtpserver.quit() 

    return None


#if __name__ == '__main__':
#    main()
