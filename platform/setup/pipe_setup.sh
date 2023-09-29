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
	
	elif [ "${CMD_ARR[0]}" == "docker" ]; then
		if [ "${CMD_ARR[2]}" == all ]; then
			echo "Executing command: docker logs for all containers"
			readarray containers < "docker ps -a --format '{{.Names}}'"
			for ((i=0;i<${#containers[@]};i++)); do
				docker logs "${containers[$i]}" > "$1/groups/docker_logs/${containers[$i]}.log" 2>&1
			done
		else
			echo "Executing command: docker ${CMD_ARR[@]:1} and saving at $1/groups/docker_logs/${CMD_ARR[2]}.log"
			docker logs "${CMD_ARR[2]}" > "$1/groups/docker_logs/${CMD_ARR[2]}.log" 2>&1
		fi
		
	elif [ "${CMD_ARR[0]}" == "exit" ]; then
		echo "Exiting pipe listener"
		break
	
	else
		echo "Unknown command: ${CMD_ARR[@]}"
	fi

	# eval "${COMMAND}"
done