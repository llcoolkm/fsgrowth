#!/usr/bin/env python3
#
# fsgrowth - report the daily growth of filesystems through mail
#
# - Schedule in cron every hour or every day. Delta is given in seconds in report
# - Writes to history file and compare delta
# - Sends a report every time it's run with diff and delta
#   
# 
#------------------------------------------------------------------------------
# Imports {{{
import smtplib
import socket
import shutil
import os
import pickle
from datetime import datetime

# }}}
# Config {{{
filesystems = ['/app/omd/data', '/omd/data/archive08', '/omd/data/archive09']
environment = 'SEB'
hostname = socket.gethostname()
histfile = '/tmp/fsgrowth.db'

# SMTP server
smtphost = 'smtp.sebot.local'
smtpport = 25
smtpfrom = 'fsgrowth@addpro.se'
smtprcvr = 'david.henden@addpro.se'

# }}}
# def main(): {{{
#------------------------------------------------------------------------------
def main():

    # Check for old data to compare with
    if os.path.isfile(histfile):
        history = pickle.load(open(histfile, 'rb'))
    else:
        history = {}

    # Setup a template and print headers
    template = '{0:30} {1:10} {2:>7} {3:>7} {4:>7} {5:>4} {6:>7} {7:>7}'
    headers = template.format('Filesystem', 'Datetime', 'Total', 'Used',
        'Free', 'Pct', 'Diff', 'Delta')
    template = '{0:30} {1:%Y-%m-%d} {2:>7,d} {3:>7,d} {4:>7,d} {5:>3,d}% {6:>7,d} {7:>7,d}'

    # Loop file systems
    now = datetime.now()
    fstotal = {}
    for fs in filesystems:
        try:
            [total, used, free] = map(lambda x: round(x / 1024 / 1024 / 1024),
                 shutil.disk_usage(fs))
            pct = round((used / total) * 100)

            # Add some deltas if we have a history
            if fs in history:
                used_delta = used - history[fs][2]
                time_delta = now - history[fs][0]
            else:
                used_delta = 0
                time_delta = now - now

            # A complete fs row with metrics
            fstotal[fs] = [now, total, used, free, pct, used_delta, time_delta]

        except Exception as e:
            print('{}: {}'.format(fs, e))

    # Prettify history
    olddata = []
    for fs, metrics in history.items():
        olddata.append(template.format(fs, metrics[0], metrics[1], metrics[2],
             metrics[3], metrics[4], metrics[5], round(metrics[6].seconds / 3600)))

    # Prettify contemporary
    data = []
    for fs, metrics in fstotal.items():
        data.append(template.format(fs, metrics[0], metrics[1], metrics[2],
             metrics[3], metrics[4], metrics[5], round(metrics[6].seconds / 3600)))

    olddata = '\n'.join(olddata)
    data = '\n'.join(data)

    # DEBUG
    #    print('CONTEMPORARY\n{}'.format(data))
    #    print('HISTORY\n{}'.format(olddata))

    # Write history
    pickle.dump(fstotal, open(histfile, 'wb'))

    # Report to master
    sendreport(headers, data, olddata)
    
    return None


# }}}
# def sendmail(data): {{{
#------------------------------------------------------------------------------
def sendreport(headers, data, olddata):
    """Send email report"""

    message = """Subject: {environment} file system growth report for {hostname}

{headers}
{data}

LAST REPORT

{headers}
{olddata}

/fsgrowth reporter on {hostname}
"""

    try:
        smtpserver = smtplib.SMTP(smtphost, smtpport)
        smtpserver.ehlo()
        smtpserver.sendmail(smtpfrom, smtprcvr, message
            .format(environment=environment, headers=headers, data=data,
                olddata=olddata, hostname=hostname))
    except Exception as e:
        print(e)
    finally:
        if smtpserver:
            smtpserver.quit() 

    return None


# }}}

if __name__ == '__main__':
    main()

