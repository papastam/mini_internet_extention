# Connectivity Matrix

The matrix page on the website shows the connectivity matrix.
The connectivity matrix indicates the networks that each group:

- can reach with a valid AS-level path (green);
- can reach with an invalid AS-level path (orange);
- cannot reach (red).

We determine reachability by sending periodic pings between all networks. If the ping succeeds, we consider the AS reachable. In addition to the ping, we compare the BGP looking glass outputs with the project topology to determine whether the path between two ASes is valid, i.e. if it does not violate any policies. 

The source and destination hosts used for the ping can be configured in the [`l3_routers.txt`](layer3_configuration#l3_routerstxt) configuration file (with the `MATRIX` and `MATRIX_TARGET` parameters).

We determine the validity of a path by looking at all the possible paths and not only the best ones. Thus, as soon as one path from _i_ to _j_ is invalid, the _(i,j)_ cell will be orange (assuming data-plane connectivity).

## Turn on the connectivity matrix

By default, the matrix does not run. This is the default behavior because the matrix requires sending regular pings which might 
increase the load on the server.

The pings used by the matrix are sent from a `MATRIX` container that is connected to every AS. the [`l3_routers.txt`](layer3_configuration#l3_routerstxt) configuration file indicates
to which router in every group this container is connected to.
Only the instructor can access the MATRIX container directly from the server with:

```
docker exec -it MATRIX bash
```

To start the ping and turn on the matrix, just run the following script (we recommend to run it from a `tmux` session so that it never stops):

```
cd /home
python ping.py
```

The resulting connectivity file (`/home/connectivity.txt`) is then processed by the `WEB` container to show the connectivity matrix on the website.
