# BGP prefix hijacking

During the project, we like to hijack students' prefixes so that they need to implement mitigation steps, e.g. using more specific advertisements or RPKI+ROV.
We prepared scripts to automatically hijacks students' prefixes.
The script `utils/hijacks/hijack.sh` is the core script used to generate hijacks.

This script takes the following mandatory arguments:

* Argument #1: the hijacker AS.
* Argument #2: the hijacked prefix.
* Argument #3: the sequence number used within the prefix-list (just write something like 100 and it should work).

For instance, the following command will make AS5 hijack part of AS13's prefix:

```
./run_hijack 5 13.104.0.0/25 100
```

There are two optional arguments:

* `--clear`: To undo an ongoing hijack.
* `--origin_as X`: To perform a Type-1 hijack where X is the origin of the hijacked route.

## Network-wide hijacks

Using the `hijack.sh` script you can then activate hijacks for every student group.
For example, we do this in the scripts `question_3_1.sh`, `question_3_2.sh` and `question_3_3.sh`.
You can just adapt these scripts according to your topology and your questions.
