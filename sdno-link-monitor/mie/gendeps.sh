#!/bin/sh

find . -name '*.py' -exec grep -w '^\s*\(import\|from\)' {} -h \; | sed 's/,/ /g' | awk '{print $2}' | tr 'A-Z' 'a-z' | sort -u > /tmp/left
pip list 2> /dev/null  | awk '{print $1}' | tr 'A-Z' 'a-z' | sort -u > /tmp/right
comm -12 /tmp/left /tmp/right > requirements.txt

echo "requirements.txt generated..."
cat requirements.txt

