AS="$1"
N_PASSWORD=$2 # new password
DIRECTORY="$3"

echo -e ""${N_PASSWORD}"\n"${N_PASSWORD}"" | docker exec -i "${AS}"_ssh passwd root
docker exec "${AS}"_ssh bash -c "kill -HUP \$(cat /var/run/sshd.pid)"

# Change in password text file as well
sed -i "s/${AS} .*/${AS} ${N_PASSWORD}/" ${DIRECTORY}/groups/passwords.txt