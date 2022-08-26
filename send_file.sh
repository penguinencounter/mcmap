#! /bin/bash
# ensure there is an argument provided
if [ $# -eq 0 ]; then
    echo "No argument provided"
    exit 1
fi

# iterate through the arguments
for arg in "$@"; do
    # check if the argument is a file
    if [ -f "$arg" ]; then
        # send the file
        curl -X PUT --data-binary "@$arg" "http://penguintime.local:8888/write/$arg"
    fi
done
echo
echo "Finished"
