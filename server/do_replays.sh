#!/usr/bin/env bash

rm -rf replay_api_cache 2>/dev/null

for pf in $(cat participant_folders); do echo ${pf}; ./replay.sh ${pf} > ${pf}/replay_events; done
