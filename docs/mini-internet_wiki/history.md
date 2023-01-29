# Keeping track of the configurations and connectivity

Every year when we run the mini-Internet we also keep track of the students' configurations as well as of how the connectivity evolves throughout the project. This is useful to see when and how the students did progress, and also to create the connectivity GIF. 

## Saving the students' configurations

In the directory `utils/gif/` you can find the script `history_config.sh`. Every 10 minutes (by default) this script saves all current student configurations to a git repository. Because we use git, only the changes will be pushed to your git repo and you can keep track of the changes over time using the various git commands.

To use this script, you must change the following variables:

* USERNAME: Your username on the server.
* PLATFORM_DIR: The full path of the `platform` directory. 
* GITADDR: The remote address of your git repository.
* GITDIR: A local directory that contains the cloned git repository and is used to commit and push to the remote.

## Saving the connectivity 

Aside from pushing the configurations to the git repository, the `history_config.sh` script also pushes the raw connectivity files used to generate the matrix and available at `https://your-server-domain/matrix?raw`. 
With the history of the connectivity, you can then make a connectivity GIF and share it with your students.
The connectivity history is available under the `matrix` folder in the git repository.

## Saving the connectivity GIF

The `history_config.sh` also pushes one connectivity GIF that is built from PNG images.
The script also pushes the matrix as HTML files so you can generate your own connectivity GIF. These files are available in the `images` folder in the git repository.
