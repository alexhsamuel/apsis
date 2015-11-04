#!/bin/bash

echo "This is $0."
echo "to stdout"
echo "to stderr" >&2
echo "to stderr" >&2
echo "to stdout"
echo "to stderr" >&2
echo "End of $0."
exit 42
