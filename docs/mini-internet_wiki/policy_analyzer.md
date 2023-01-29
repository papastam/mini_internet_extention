# The BGP policy analyzer  

To help the students understanding if their BGP policies are correctly implemented, we provide a BGP policy analyzer
that automatically parses the looking glass files and infers the currently configured BGP policies by looking at which prefixes each AS advertises to its neighboring ASes. When the analyzer detects a policy violation, it reports the error.
The analyzer runs in the `WEB` container and its output is printed in the mini-Internet website under the `looking glass` tab (towards the end of the page).