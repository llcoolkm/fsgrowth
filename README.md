# fsgrowth
File system growth reporter with deltas

## Prerequisites

Install python modules

```
python3 -m pip install --upgrade pandas matplotlib pretty_htnml_table
```

## How to run

Edit the script and change the email parameters. Run once every day, either in the morning or the evening. Run it once to see that it works

```
./fsgrowth.py
```

Install it into crontab:
```
echo '00 09 * * * root /opt/scripts/fsgrowth/fsgrowth.py --filesystem /tmp --history-file=/tmp/fsgrowth.csv' > /etc/cron.d/fsgrowth
```

If everything works add --quiet. The first day will contain an empty graph and also a 0 delta change.


