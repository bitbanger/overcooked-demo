#!/usr/bin/env bash

python run_parser.py --input inps/overcooked.txt --load oc_learned --freeform && cat out | nc localhost 4444
