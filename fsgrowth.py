#!/usr/bin/env python3
#
# fsgrowth - report the daily growth of filesystems through mail
#
#   Schedule in cron
#   Writes historical data to ???
#   Sends a report every time it's run with delta, growth and projection
#   
# 
#------------------------------------------------------------------------------
# Imports {{{
import smtplib
import socket
import shutil
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os

# }}}
# Config {{{
filesystems = ['/omd/data/archive08', '/omd/data/archive07', '/omd/data/archive06', '/omd/data/archive09']
environment = 'SEB'
hostname = socket.gethostname()
histfile = '/tmp/fsgrowth.csv'

# SMTP server
smtphost = 'smtp.sebot.local'
smtpport = 25
smtpfrom = 'fsgrowth@addpro.se'
smtprcvr = 'david.henden@addpro.se'

# }}}
# def main(): {{{
#------------------------------------------------------------------------------
def main():

    if os.path.isfile(histfile):
        dataframe = pd.read_csv(histfile)
        print()
        print('Found and loaded historical data!')
        dataframe.info(verbose=False)
        print()
    else:
        dataframe = None

    # Setup a template and print headers
#    template = '{0:30} {1:19} {2:>7} {3:>7} {4:>7} {5:>4}'
#    print(template
#        .format('Filesystem', 'Datetime', 'Total', 'Used', 'Free', 'Pct'))
    columns = ['Filesystem', 'Datetime', 'Total', 'Used', 'Free', 'Pct']
    template = '{0:30} {1:19} {2:>7,d} {2:>7,d} {4:>7,d} {5:>3,d}%'

    # Loop file systems
    now = datetime.now()
    fstotal = []
    for fs in filesystems:
        try:
            [total, used, free] = map(lambda x: round(x / 1024 / 1024 / 1024),
                 shutil.disk_usage(fs))
            pct = round((used / total) * 100)
            fsrow = [fs, now, total, used, free, pct]
            fstotal.append(fsrow)

        except Exception as e:
            print('{}: {}'.format(fs, e))

    if dataframe is None:
        dataframe = pd.DataFrame(fstotal, columns=columns)
    else:
        newframe = pd.DataFrame(fstotal, columns=columns)
        dataframe = dataframe.append(newframe, ignore_index=True)
            
#    dataframe.to_csv(histfile, index=False)
    report(dataframe)

    return None

# }}}
# def report(dataframe): {{{
#------------------------------------------------------------------------------
def report(data):

#    data= data.sort(columns=Datetime)
    print(data)
    data.set_index('Datetime').diff()
    print(data)

    return None


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

# }}}
# def isotime(self, time): {{{
#------------------------------------------------------------------------------
    def isotime(self, time):
        """Convert epoch to isotime"""
        return '{}'.format(datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S'))

# }}}

if __name__ == '__main__':
    main()

