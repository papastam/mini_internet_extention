#!/bin/bash
as=$1

if [ -z "$as" ]; then
	echo "Invalid syntax!"
	echo "./gotoAS.sh <AS#>"
	exit
fi

# AS passwords in a dictionary
declare -A as_pass

as_pass[3]="cb3b117a0832866d"
as_pass[4]="54ba5390fa9e963c"
as_pass[5]="768c45148842151f"
as_pass[6]="6c268b528182df8b"
as_pass[7]="f9a3aa7ef7796e04"
as_pass[8]="6c21b6165154efbd"
as_pass[9]="928615d26db85f11"
as_pass[10]="d7dc67c330205580"
as_pass[11]="394b82d9810a9373"
as_pass[12]="7e62de71bfb23353"
as_pass[23]="23a0d508d44827f2"
as_pass[24]="87433d72654820dd"
as_pass[25]="ce00f3659a3f9954"
as_pass[26]="8c6da953a3bcd1a9"
as_pass[27]="a1febd0bb551421b"
as_pass[28]="a2512cc0878dd6d7"
as_pass[29]="8a18420737b34bcf"
as_pass[30]="d1bcac4f5a8ec77e"
as_pass[31]="c70ea35daf3f6934"
as_pass[32]="40b18bc3f516b08d"
as_pass[43]="eba778bf837079e1"
as_pass[44]="3a0a920ea5e22a5a"
as_pass[45]="b842559a2cd6d8de"
as_pass[46]="0edbf0039efcb49f"
as_pass[47]="dd9bf7494ca9a25f"
as_pass[48]="4ad6bc500962e39f"
as_pass[49]="478e350d802b2e2e"
as_pass[50]="bc7f6b2c154495d2"
as_pass[51]="ca063a52917e63e0"
as_pass[52]="c6fd6bae66073089"
as_pass[63]="407b23d40f5e08bb"
as_pass[64]="f4e850e9c9e7ad52"
as_pass[65]="5d98e334e4cb5aa2"
as_pass[66]="7a8e5f104dfa01c8"
as_pass[67]="b6ccf61aae0e950a"
as_pass[68]="f1b58b02169c7ee1"
as_pass[69]="d54afce483a36532"
as_pass[70]="6defaa9a67a20220"
as_pass[83]="03cce9da1021cf31"
as_pass[84]="0fe862a5b724a318"
as_pass[85]="746384ce351bb58e"
as_pass[86]="2a50f652d4f12460"
as_pass[87]="7167c99d03bca285"
as_pass[88]="44485402923b73f9"
as_pass[89]="9bf4111fca3df211"
as_pass[90]="1f594175e9ececf3"
as_pass[103]="b035034c391bc393"
as_pass[104]="3f4c07752dbcb239"
as_pass[105]="b5745df443bc8ad4"
as_pass[106]="414b0cadd4e988b6"
as_pass[107]="894ceacd06e2d3b3"
as_pass[108]="0403c89db5e1d0e3"
as_pass[109]="738975a0396e79b9"
as_pass[110]="be95562999cfd94d"


if [ $1 = "server" ]; then
	sshpass -p !hy335bhy335b! ssh -o StrictHostKeyChecking=no csduser01@147.52.203.13
else
	portn=$((2000+${as}))
	echo "Connecting to AS ${as}..."
	sshpass -p ${as_pass[${as}]} ssh -o StrictHostKeyChecking=no root@147.52.203.13 -p ${portn}
	exit
fi
