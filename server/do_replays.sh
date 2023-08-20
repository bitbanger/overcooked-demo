#!/usr/bin/env bash

# rm -rf replay_api_cache 2>/dev/null

for pf in $(cat pfs2); do echo ${pf}; ./replay.sh ${pf} > ${pf}/replay_events; wc -l ${pf}/replay_events; done
