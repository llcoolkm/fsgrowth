#!/usr/bin/env python3
#
# fsgrowth - report the daily growth of filesystems through mail
#
# - Schedule in cron every hour or every day. Delta is given in seconds in report
# - Writes to history file and compare delta
# - Sends a report every time it's run with diff and delta
#   
# pip3 install psutil plotly pandas
# 
#------------------------------------------------------------------------------
# Imports {{{
import socket
import shutil
import os
import pickle
import argparse
import psutil
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import pandas as pd
#import plotly.express as px
#from plotly.offline import plot
import matplotlib.pyplot as plt
#import matplotlib.colormap as cm
import seaborn as sns
import io
from email import encoders
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid

# }}}
# Config {{{
fsfilter = ['/omd/data/archive*', '/app/omd/data']
environment = 'SEB'
hostname = socket.gethostname()
historyfile = '/tmp/fsgrowth.db'

# SMTP server
smtphost = 'smtp.sebot.local'
smtpport = 25
smtpfrom = 'fsgrowth@addpro.se'
smtprcvr = 'david.henden@addpro.se'

# }}}
# def main(): {{{
#------------------------------------------------------------------------------
def main(args):
    """Load history, collect data, save history, send an e-mail report"""

    # Load history
    history = loadhistory(args.import_file)

    # Collect data
    now = datetime.now()
    fstotal = {}
    for fs in psutil.disk_partitions():

        fs = fs.mountpoint
        [total, used, free] = map(lambda x: round(x / 1024 / 1024 / 1024),
            shutil.disk_usage(fs))

        try:
            if total == 0:
                pct = 0
            else:
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

#        print('{}/{}/{}/{}/{}/{}/{}/{}'.format(fs, now, total, used, free, pct, used_delta, time_delta))

    # Print data
#    history['Date'] = history.to_datetime(history['DateTime'])
#    history['categories'] = pd.cut(df.index, bins, labels=group_names)

#    history['Date'] = history['DateTime'].dt.date
#    history = history[history['Free'].str.isnumeric()]
#    history['Date'] = history['Date'].astype(np.datetime64)

#    history.set_index('Date', inplace=True)

#    for column in ('Total', 'Used', 'Pct'):
#        del history[column]
#    history.resample('D').size().plot.bar()

#    print(history.index)
#    print(history.columns)
#    print(history.dtypes)

#    # Trend
#    from scipy import stats
#    slope, intercept, r_value, p_value, std_err = stats.linregress(history.index, history['Free'])
#    history['Line'] = slope * history.index + intercept
#    ax1 = fig.add_subplot(1,1,1)

#    sns.displot(data=history, x='Date', y='Free', shade=True)
#    sns.displot(data=history, x='Date', y='Diff', shade=True)

    # Matplotlib
    history.set_index('date', inplace=True)

    # Create some extra columns with rolling average, positive growth, status
    history['7dayavg'] = history.free.rolling(7).mean().shift(-3)
    history['positive'] = history['diff'] > 0
    print(history)

#    # Create a graph
    plt.figure(figsize = (20,15))
#
#    ax1 = fig.add_subplot(2, 1, 1)
#    ax2 = fig.add_subplot(2, 1, 2)
#    history.plot(use_index=True, y='Free', kind='line', grid=True, linewidth=1, title='Free GB', color='r', drawstyle='steps-post', ylim=0, ax=ax1)
#    history.plot(use_index=True, y='7DayAvg', kind='line', grid=True, linewidth=1, title='Free GB', color='y', ylim=0, ax=ax1)
#    history.plot(use_index=True, y='Diff', kind='bar', grid=True, linewidth=1, title='Delta GB', ax=ax2, color=history.Positive.map({True: 'g', False: 'r'}))

    # Overlay
#    plt.rcParams['figure.figsize']=(20,15) # set the figure size
#    plt.style.use('fivethirtyeight') # using the fivethirtyeight matplotlib theme
#    fig, ax1 = plt.subplots()
#    ax2 = ax1.twinx
#    history.plot(use_index=True, y='free', kind='line', grid=True, title='Free GB', color='r', drawstyle='steps-post', ylim=0)
#    history.plot(use_index=True, y='7dayavg', kind='line', grid=True, linewidth=1, title='Free GB', color='y', ylim=0)
#    history.plot(use_index=True, y='diff', kind='bar', alpha=0.2, grid=False, title='Delta GB', color=history.positive.map({True: 'g', False: 'r'}), secondary_y=True)

    # Seaborn
    plt.clf()
    fig, ax = plt.subplots()
    sns.set()
    sns.set_style("whitegrid")

#    sns.set_style('fivethirtyeight')
#    plt.title('Delta GB by day')
#    ax.set_xticklabels(labels=history.index.date, rotation=45, ha='right')

    sns.lineplot(x='date', y='free', ax=ax, data=history.reset_index(), marker='o', color='r')
    ax2 = ax.twinx()
    sns.lineplot(x='date', y='7dayavg', ax=ax2, data=history.reset_index(), marker='o', color='y')
    sns.barplot(x='date', y='diff', ax=ax2, data=history.reset_index(), color='g')
    #, color=history.positive.map({True: 'g', False: 'r'}))


#    # Seaborn
#    sns.lineplot(x='Date', y='Free', label='Daily', data=history, ci=None, marker='o')
#    sns.lineplot(x='Date', y='7DayAvg', label='7 Day Avg', data=history, ci=None)
#    sns.barplot(x='Date', y='Diff', label='Delta', data=history, ci=None)

#    plt.xlabel('Date')
#    plt.ylabel('Free GB')
#    plt.ylim(0)

    graph = io.BytesIO()
    plt.savefig(graph, format='png')
    graph.seek(0)
    plt.clf()

    # Export
    if args.export_file:
        try:
            history.to_csv(args.export_file)
            print('Wrote export file: {}'.format(args.export_file))
        except Exception as e:
            print(e)

    # Update history file (or not)
    if args.dont_update_history:
        if not args.quiet:
            print('Did not update history file')
    else:
        # Write history and report to master
        pickle.dump(history, open(historyfile, 'wb'))
        print('Updated history file: {}'.format(historyfile))
    
    # Send report
    sendreport(history.to_html(index=False, classes='data', border=1), graph.read())

    return None


# }}}
# def loadhistory(importfile) {{{
#------------------------------------------------------------------------------
def loadhistory(importfile):
    """Load history from pickle or csv"""
    history = {}

    # Import csv...
    if importfile:
        try:
            history = pd.read_csv(importfile, parse_dates=[0])
            if not args.quiet:
                print('Imported csv file with {} data points: {}'
                    .format(len(history), importfile))
        except Exception as e:
            print('Unable to import csv file: {}'.format(e))
            exit(-1)

    # ...or load pickle
    else:
        if os.path.isfile(historyfile):
            try:
                history = pickle.load(open(historyfile, 'rb'))
                if not args.quiet:
                    print('Imported history pickle with {} data points: {}'
                        .format(len(history), historyfile))
            except Exception as e:
                print('Unable to load history file: {}'.format(e))
                exit(-1)
        else:
            if not args.quiet:
                print('No history loaded')

    return history


# }}}
# def sendmail(data): {{{
#------------------------------------------------------------------------------
def sendreport(data, graph):
    """Build the e-mail report and send it"""

    # Create an e-mail
    message = EmailMessage()
    message['From'] = Address(smtpfrom)
    message['To'] =  Address(smtprcvr)
    message['Subject'] = '{}: File system report from {}'.format(environment,
        hostname)

    # Attach a body and our image
    img_cid = make_msgid()
    message.add_alternative("""\
<html>
  <body>
    <center>

      <table width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#FFFFFF">
        <tr>
          <td align="center" valign="top">
            <div><p><img src="cid:{img_cid}"></p></div>
            <div><p>{table}</p></div>
            <div><p>/fsgrowth e-mail reporter on {hostname}</p></div>
          </td>
        </tr>
      </table>
  </body>
</html>
""".format(hostname=hostname, table=data, img_cid=img_cid[1:-1]), subtype='html')
    message.get_payload()[0].add_related(graph, 'image', 'png', cid=img_cid)

    # Send it
    try:
        smtpserver = smtplib.SMTP(smtphost, smtpport)
        smtpserver.ehlo()
        smtpserver.sendmail(smtpfrom, smtprcvr, message.as_string())
    except Exception as e:
        print(e)
    finally:
        if smtpserver:
            smtpserver.close() 
            print('e-mail sent to {}'.format(smtprcvr))

    return None


# }}}
# __main__ {{{
#------------------------------------------------------------------------------
if __name__ == '__main__':
    """Parse arguments and call main"""

    parser = argparse.ArgumentParser(description='fsgrowth')
    parser.add_argument('--days', '-d', type=int, default=7, help='Number of days to include in report')
    parser.add_argument('--export-file', '-e', type=str, help='Export data to this csv file instead of collecting new data and reporting')
    parser.add_argument('--import-file', '-i', type=str, help='Import historical data from this csv file instead of default')
    parser.add_argument('--dont-update-history', '-H', action='store_true', help='Don\'t update history file. Good for testing')
    parser.add_argument('--quiet', '-q', action='store_true', help='Be quiet. Dont print any output except for errors. Good for crontab')
    args = parser.parse_args()
    main(args)

# }}}
