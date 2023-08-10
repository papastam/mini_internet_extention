#!/bin/bash
DIRECTORY="$1/utils/pipe/docker_pipe"
CHANGEPASS_SCRIPT="$1/utils/changeASpassword/changeASpass.sh"
echo "Listening to pipe: ${DIRECTORY}"

while true; do
	COMMAND=$(cat "${DIRECTORY}")
	read -ra CMD_ARR <<< "$COMMAND"
	echo "Received and executing command: ${CMD_ARR[@]}"
	if [ "${CMD_ARR[0]}" == "changepass" ]; then
		if [ "${#CMD_ARR[@]}" -ne 3 ]; then
			echo "Invalid number of arguments for changepass command"
			continue
		fi
		echo "Changing password for AS: ${CMD_ARR[1]} (new password: ${CMD_ARR[2]})"
		${CHANGEPASS_SCRIPT} "${CMD_ARR[1]}" "${CMD_ARR[2]}"
	else
		echo "Unknown command: ${CMD_ARR[0]}"
	fi

	# eval "${COMMAND}"
done