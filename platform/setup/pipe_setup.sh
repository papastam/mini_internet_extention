DIRECTORY="$1"
PIPE_DIR="$1/utils/pipe/docker_pipe"

# Properly setup the pipe
# it has been noticed that when the project is pulled
# the pipe exists as a directory and not as a pipe
# so we remove the directory and create a new pipe
if [ ! -d "${DIRECTORY}/utils/pipe" ]
then
    mkdir "${DIRECTORY}/utils/pipe"
fi
if [ ! -p "${PIPE_DIR}" ]; then
	echo "Pipe exists but not as a fifo pipe, removing it and creating a new pipe"
	rm -rf "${PIPE_DIR}"
	mkfifo "${PIPE_DIR}"
fi

rm -f ${DIRECTORY}/nohup.out
time nohup ./pipe_listener.sh "${DIRECTORY}" &
echo "Docker pipe output is: ${DIRECTORY}/nohup.out"
