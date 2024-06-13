#!/bin/bash
# Description: Save and restore output logs

directory="../../groups/exabgp_monitor"

function=$1
if [ -z "$function" ]; then
    echo "script usage: ./logs.sh <function>" >&2
    exit 1
elif [ "$function" != "save" ] && [ "$function" != "restore" ]; then
    echo "script usage: ./logs.sh <function>" >&2
    echo "function must be 'save' or 'restore'" >&2
    exit 1
fi

if [ "$function" == "save" ]; then
    # Save the output logs
    cp -r $directory/output $directory/output.saved
    echo "Output logs saved"
elif [ "$function" == "restore" ]; then
    # Restore the output logs
    cp $directory/output.saved/* $directory/output
    echo "Output logs restore"
fi