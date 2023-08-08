#!/usr/bin/env bash

trap 'kill $(ps -A | grep "Python -u app.py" | grep -v "grep" | awk "{print $1}"); pkill -P $$; kill $(jobs -p); rm /Users/l/Library/Application\ Support/Google/Chrome/SingletonLock; exit' EXIT
trap 'kill $(ps -A | grep "Python -u app.py" | grep -v "grep" | awk "{print $1}"); pkill -P $$; kill $(jobs -p); rm /Users/l/Library/Application\ Support/Google/Chrome/SingletonLock; exit' SIGINT
trap 'kill $(ps -A | grep "Python -u app.py" | grep -v "grep" | awk "{print $1}"); pkill -P $$; kill $(jobs -p); rm /Users/l/Library/Application\ Support/Google/Chrome/SingletonLock; exit' SIGTERM

mv api_cache replay_api_cache

python3.7 mk_replay.py ${1} > tmp_replay

# kill $(jobs -p)
# sleep 2
# rm /Users/l/Library/Application\ Support/Google/Chrome/SingletonLock

# ./run.sh | grep EVENT > replay_outp &
python3.7 -u app.py > replay_outp &

sleep 5

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --run-all-compositor-stages-before-draw --virtual-time-budget=999999999 --headless=new http://localhost:5000/?chatlog=tmp_replay &

LASTLINE=$(grep EVENT replay_outp | tail -n 1)
WANTLINE="EVENT: done"
while [ "$LASTLINE" != "$WANTLINE" ]
	do sleep 1; echo 'tick'; echo "\"$LASTLINE\" vs. \"$WANTLINE\""; LASTLINE=$(grep EVENT replay_outp | tail -n 1)
done

grep EVENT replay_outp > replay_out_tmp
mv replay_out_tmp replay_outp

kill $(jobs -p)

mv replay_api_cache api_cache
