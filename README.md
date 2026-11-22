# Lab Test Automation: Stress Test Logger

A Python script that loads the CPU and disk of a machine for a set time, logs system metrics to a CSV file, plots the results, and reports PASS or FAIL.

It automates the check I used to do by hand after repairing a computer: run it under load, watch stability, record the result.

## What it does

- Runs CPU load on all cores (or a number you choose) and a continuous disk write load
- Logs time, CPU %, memory %, and disk write speed every second to `results.csv`
- Prints a summary (min, max, average)
- Saves a graph to `results.png`
- Returns PASS or FAIL: FAIL if memory goes above a limit or a load process stops unexpectedly
- Exit code 0 for PASS and 1 for FAIL, so it can be used in other scripts

## Install

```
pip install -r requirements.txt
```

## Usage

```
python stress_test.py --duration 60 --interval 1
python stress_test.py --duration 30 --workers 2 --no-disk --mem-limit 80 --output test1.csv
```

| Option | Meaning | Default |
|---|---|---|
| `--duration` | test length, seconds | 30 |
| `--interval` | seconds between samples | 1 |
| `--workers` | CPU load processes | all cores |
| `--no-disk` | skip disk load | off |
| `--mem-limit` | FAIL above this memory % | 90 |
| `--output` | CSV file name | results.csv |

## Example output

```
Started 3 load processes for 5 s
   1.0s  CPU 100.0%  MEM   6.4%  DISK   76.86 MB/s
   ...
--- Summary ---
CPU %:    min 100.0  max 100.0  avg 100.0
Memory %: min 6.4  max 6.9  avg 6.8
RESULT: PASS
```

## Built with

Python 3, psutil, matplotlib.
