# BGP Looking glass

Similarly to the real-world where network operators can debug BGP using looking glasses, 
the mini-Internet provides a looking glass service that students can use to see the BGP routing table of every router in the mini-Internet.

Every container that runs a router pulls the routing table from the FRRouting CLI every 30 seconds and stores it in `/home/looking_glass.txt`. This file is bound to a file in the local filesystem according to this scheme: `groups/gX/<location>/looking_glass.txt` where `X` is the group number and `<location>` is e.g. `ZURI`.

Instead of directly looking at those files, the mini-Internet prints their content on the webpage automatically under the `looking glass` page.
