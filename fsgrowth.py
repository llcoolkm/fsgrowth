#!/usr/bin/env python3
#
# fsgrowth - report the daily growth of filesystems through mail
#
# - Schedule in cron every hour or every day
# - Delta is given in seconds in report
# - Writes to history file and compare delta
# - Sends a report every time it's run with diff and delta
#
# pip3 install matplotlib pandas pretty_html_table
#
# -----------------------------------------------------------------------------

# Imports
import argparse
import base64
from datetime import datetime, timedelta
import io
import json
import math
import os
import requests
import shutil
import sys

from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.style as style
import msal
import pandas as pd
from pretty_html_table import build_table

hostname = os.uname()[1]


# -----------------------------------------------------------------------------

def main():
    """Load history, collect data, save history, send an e-mail report"""

    # Load history
    data = loadhistory(args.history_file)

    # Collect new data
    if args.update:
        present = collectdata(args.filesystem)

        # Append present to history...
        if 'used' in data:
            present['delta'] = present['used'] - data['used'].iloc[-1]
            data = pd.concat([data, pd.DataFrame.from_records([present])])
        # ...or start fresh
        else:
            present['delta'] = 0
            data = pd.DataFrame([present])
    else:
        if not args.quiet:
            print('Did not collect new data.')

    # Die if we don't have a dataframe to play with
    if not isinstance(data, pd.DataFrame):
        print('ERROR: Have neither history nor new data to work with. '
              'Please provide at least one')
        raise SystemExit(1)

    # Set index and normalize datetime
    data['date'] = pd.to_datetime(data['date'])
    data = data.set_index('date')
    data.index = data.index.normalize()

    # Warn if missing dates in data
    try:
        data = data.asfreq('D')
    except Exception as e:
        print(f'ERROR: Data for today already exists: {e}')
        raise SystemExit(1)

    for date in data.index[data['total'].isnull()]:
        print(f'WARNING: Missing date {
              date.to_pydatetime().date().isoformat()}')

    # Calculate some columns
    data['avg'] = data.free.rolling(7).mean().shift(-3)
    data['weekday'] = data.index.weekday
    data['weekend'] = [True if value >= 5 else False for value in data.weekday]

    # Update history file...
    if args.update:
        try:
            data.to_csv(args.history_file)
            if not args.quiet:
                print(f'Updated history file: {args.history_file}')
        except Exception as e:
            print(f'ERROR: Unable to update history file '
                  f'{args.history_file}: {e}')
            raise SystemExit(1)
    # ...or not!
    else:
        if not args.quiet:
            print('Did not update history file.')

    # Since we have now saved history we are free to truncate our work sample
    # to the requested reporting period
    thirtydaysago = datetime.now() - timedelta(args.days)
    data = data.truncate(before=thirtydaysago, copy=False)

    # Calulcate delta means and out-of-space days
    mean = {}
    mean['total'] = round(data.delta.mean())
    mean['positive'] = round(data.delta.where(data.delta.ge(0)).mean())
    if mean['positive'] > 0:
        mean['days'] = math.floor(data['free'].iloc[-1] / mean['positive'])
    else:
        mean['days'] = 'infinite'

    # Generate a report and send it...
    if args.report:

        # Generate a graph
        graph = creategraph_pyplot(data, mean, args.filesystem)

        # Fix the dataframe for reporting: normalize it, reverse it and drop
        # superfluous columns
        data.index = data.index.normalize()
        data = data[::-1]
        data = data.drop(columns=['fs', 'avg'], axis=1)

        # Send report
        # writereport(data, fs, graph)
        mailreport(data, graph, args.filesystem, mean, args.marker)
    # ...or not!
    else:
        if not args.quiet:
            print('Did not send a report.')

    return None


# -----------------------------------------------------------------------------

def loadhistory(history_file) -> pd.DataFrame:
    """Load history from pickle or csv"""
    history = {}

    if os.path.isfile(history_file):
        try:
            history = pd.read_csv(history_file, parse_dates=['date'])
            if not args.quiet:
                begin = history['date'].iloc[0]
                end = history['date'].iloc[-1]

                print(f'Loaded history file {history_file} with {len(history)}'
                      f' data points from {begin} to {end}.')
        except Exception as e:
            print(f'ERROR: Unable to load history file {history_file}: {e}')
            raise SystemExit(1)
    else:
        if not args.quiet:
            print(f'Did not load history file {history_file}.')

    return history


# -----------------------------------------------------------------------------

def collectdata(fs) -> dict:
    """Collect data from all file systems and return as an array"""

    now = datetime.now().replace(microsecond=0)

    try:
        total, used, free = map(lambda x: int(round(x / 1024 / 1024 / 1024)),
                                shutil.disk_usage(fs))

        # Get pct
        if total == 0:
            pct = 0
        else:
            pct = round((used / total) * 100)

        fsvalues = {'date': now, 'fs': fs, 'total': total, 'used': used,
                    'free': free, 'pct': pct}
    except Exception as e:
        print(f'ERROR: Unable to collect filesystem data: {e}')
        raise SystemExit(1)

    if not args.quiet:
        print(f'Collected data for filesystem: {fs}')

    return fsvalues


# -----------------------------------------------------------------------------

def creategraph_pyplot(data: pd.DataFrame, mean: dict, fs: str):
    """Plot a beautiful graph and return a png in a string"""

    # fivethirtyeight palette
    palette = {
        'blue': '#30a2da',
        'red': '#fc4f30',
        'yellow': '#e5ae38',
        'green': '#6d904f',
        'gray': '#8b8b8b',
        'bg': '#f0f0f0',
        'weekend': '#ffeeee'
    }

    # Create the plots
    fig, ax = plt.subplots(figsize=(12, 4))
    plt.gcf().subplots_adjust(bottom=0.20)
    plt.title(f'Free GB by day - {hostname}:{fs}', fontsize=16)

    # Highlight weekends
    for i, (date, row) in enumerate(data.iterrows()):
        if row['weekend']:
            ax.axvspan(mdates.date2num(date) - 0.5,
                       mdates.date2num(date) + 0.5,
                       color=palette['weekend'],
                       alpha=0.3)

    # Free
    plt.plot(mdates.date2num(list(data.index)), data.free, linewidth=3,
             color=palette['blue'])
#    # Rolling 7day average [useless, this just overwrites the "normal" line]
#    plt.plot(mdates.date2num(list(data.index)), data.avg, linewidth=3,
#        color=palette['yellow'])

    # Delta change
    plt.bar(mdates.date2num(list(data.index)), data.delta, alpha=.5,
            align='center',
            color=[palette['green'] if value >= 0
            else palette['red'] for value in data.delta])

    ax.grid(visible=True, which='major', color='gray', linestyle='-', alpha=.3)
    [ax.spines[x].set_visible(False)
     for x in ['top', 'right', 'bottom', 'left']]
    style.use('fivethirtyeight')
    ax.set_facecolor(palette['bg'])
    fig.set_edgecolor(palette['bg'])

    # Set the x axis
    plt.xticks(rotation=90, fontsize=12)
    ax.axhline(y=0, color='black', linewidth=1.3, alpha=.7)
    ax.xaxis_date()
    ax.xaxis.label.set_visible(False)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.set_xticks(ax.get_xticks())
    # ax.set_xticks(ax.get_xticks()[1:-1])

    # Set the y axis
    plt.yticks(fontsize=12)
    bottom = int(round(ax.get_yticks()[0]))
    top = int(round(ax.get_yticks()[-1]))
    ystep = int(round((top - bottom) / 10))
    yrange = list(range(bottom, top, ystep))
    ax.set_yticks(yrange[1:])
    ax.set_ylabel('GB', fontsize=14)

    # Is this a first run? Make a sad empty graph with a promise
    if len(ax.get_xticks()) <= 1:
        print('Only one data point. A pretty sad graph will be generated')
        plt.title('Tomorrow will bring you a better graph - promise!')
        ax.xaxis.label.set_visible(False)
        ax.yaxis.label.set_visible(False)
        ax.set_yticks([])
        ax.set_xticks([])

    # This doesnt work with less than 2 data points
    else:
        # Put a text box in upper right corner with some stats
        props = dict(boxstyle='square', facecolor='wheat', alpha=.6, pad=.5)
        ax.text(.5, .5,
                f'Mean growth: {mean['total']}\n'
                f'Positive mean growth: {mean['positive']}\n'
                f'Out of space in {mean['days']} days',
                transform=ax.transAxes, fontsize=14, va='center', ha='center',
                bbox=props)

    # Save
    graph = io.BytesIO()
    plt.savefig(graph, format='png', dpi=72)
    graph.seek(0)
    if not args.quiet:
        print('Created a beautiful graph')

    return graph.read()


# -----------------------------------------------------------------------------

def writereport(table, graph) -> None:

    html_table = build_table(table.reset_index(), 'grey_light',
                             font_size='small', font_family='Verdana')
    html = """\
<html>
  <body>
    <center>
      <table width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#FFFFFF">
        <tr>
          <td align="center" valign="top">
            <div><p><img src="graph.png"></p></div>
            <div><p>{table}</p></div>
            <div><p>/fsgrowth e-mail reporter on {hostname}</p></div>
          </td>
        </tr>
      </table>
  </body>
</html>
""".format(hostname=hostname, table=html_table)

    with open('graph.png', 'wb') as f:
        f.write(graph)
    f.close()

    reportfile = 'report.html'
    with open(reportfile, 'w') as f:
        f.write(html)
    f.close()

    if not args.quiet:
        print(f'Wrote report to disk: {reportfile}')

    return None


# -----------------------------------------------------------------------------

def mailreport(data: pd.DataFrame, graph: bytes, fs: str, mean: dict,
               marker: str) -> None:
    """Build the e-mail report and send it"""

    load_dotenv()

    # MSAL variables
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    tenant_id = os.getenv('TENANT_ID')
    mailrcvr = os.getenv('MAILRCVR')
    mailfrom = os.getenv('MAILFROM')
    authority = f'https://login.microsoftonline.com/{tenant_id}'
    scope = ['https://graph.microsoft.com/.default']

    # Create our content
    subject = f'{marker}: File system {hostname}:{fs} has ' \
        f'{data["free"].iloc[0]} GB free ({mean["days"]} days)'
    graphb64 = base64.b64encode(graph).decode('utf-8')
    htmltable = build_table(data.reset_index(), 'grey_light',
                            font_size='small', font_family='Verdana')
    htmlbody = f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>Filesystem Report</title>
    </head>
    <body>
        <table border="0" cellpadding="0" cellspacing="0" height="100%" width="100%" id="bodyTable">
            <tr>
                <td align="center" valign="top">
                    <table border="0" cellpadding="20" cellspacing="0" width="600" id="emailContainer">
                        <tr>
                            <td align="center" valign="top">
                                <img src="data:image/png;base64,{graphb64}" alt="Filesystem Graph" />
                            </td>
                        </tr>
                        <tr>
                            <td align="center" valign="top">
                                {htmltable}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>
"""

    access_token = get_access_token(client_id, client_secret, authority, scope)

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    email_data = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": htmlbody
            },
            'from': {
                'emailAddress': {
                    'address': mailfrom
                }
            },
            'toRecipients': [
                {
                    'emailAddress': {
                        'address': mailrcvr
                    }
                }
            ]
        }
    }
    endpoint = f'https://graph.microsoft.com/v1.0/users/{mailfrom}/sendMail'
    response = requests.post(
        endpoint,
        headers=headers,
        data=json.dumps(email_data)
    )
    if response.status_code != 202:
        sys.stderr.write(f'Error sending email: {response.status_code} - '
                         f"{response.text}")
        raise SystemExit(1)

    if not args.quiet:
        print('E-mail sent')

    return None


# -----------------------------------------------------------------------------

def get_access_token(client_id: str, client_secret: str, authority: str,
                     scope: dict):
    app = msal.ConfidentialClientApplication(client_id,
                                             authority=authority,
                                             client_credential=client_secret
                                             )
    result = app.acquire_token_for_client(scopes=scope)
    if 'access_token' in result:
        return result['access_token']
    else:
        raise Exception('Failed to acquire token',
                        result.get('error'), result.get('error_description'))

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    """Parse arguments and call main"""

    parser = argparse.ArgumentParser(description='fsgrowth')
    parser.add_argument('--days', '-d', type=int, default=30,
                        help='Number of days to report on counting backwards '
                        'from today. Default 30')
    parser.add_argument('--filesystem', '-f', type=str,
                        required=True, help='Filesystem to report on. '
                        'Required')
    parser.add_argument('--history-file', '-H', type=str,
                        required=True, help='History file to use. Required')
    parser.add_argument('--marker', '-m', type=str,
                        help='Put this string as a marker in the beginning '
                        'of the e-mail report subject. Good for filtering')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Be quiet. Dont print any output except for '
                        'errors. Great for crontab')
    parser.add_argument('--report', '-r', action='store_true',
                        help='Create and e-mail a report')
    parser.add_argument('--update', '-u', action='store_true',
                        help='Collect new data and update the history file')
    args = parser.parse_args()
    main()
