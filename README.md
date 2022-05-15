# fsgrowth
File system growth reporter with deltas

## Prerequisites

Install python modules

```
python3 -m pip install --upgrade pandas matplotlib pretty-htnml-table
```

## How to run

Edit the script and change the email parameters. You should run it once per day to collect stats. Report can be sent at the same time or scheduled separately, for example in the morning or weekly. Run it once manually first to see that everything works.

```
./fsgrowth.py
```

Install it into crontab:
```
echo '00 23 * * * root /opt/scripts/fsgrowth/fsgrowth.py -f /home -H /tmp/fsgrowth.csv --update' > /etc/cron.d/fsgrowth
echo '00 08 * * * root /opt/scripts/fsgrowth/fsgrowth.py -f /home -H /tmp/fsgrowth.csv --report' >> /etc/cron.d/fsgrowth

```

If everything works add --quiet. The first day will contain an empty graph and also a 0 delta change.


