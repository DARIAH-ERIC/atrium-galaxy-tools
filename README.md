# Galaxy Tool Wrappers for ATRIUM Components

This repository contains a simple Docker Compose based Galaxy instance that is pre-configured to include the currently available Galaxy tool wrappers for the components produced as part of the ATRIUM project.

Once you have cloned this repository run the `init.sh` script to correctly create the configuration directory.

You should then be able to bring up a Galaxy instance using the command

```
docker compose up
```

On the first occassion it will take a few minutes to start up as it pulls in the relevant dependencies and creates the required databases etc.

Once the instance is running it will be available at http://localhost:8080 -- the port number can be configured in `docker-compose.yml` if you need to change it.

Whilst the tools should appear within the ATRIUM section they won't initially work as the dependencies will not have been installed. Log in as an admin user (default is `admin@example.org` with a password of... `password`) and navigate to Admin > Manage Dependencies. Select the ATRIUM tools and then click Install. Again this may take a while as the relevant libraries etc. are downloaded and installed.

A number of workflows that make use of the tools in this repository are providedin the [`workflows`](./workflows/README.md) directory. Note that these are only examples and the tools can hopefully be combined in many other ways to build workflows which we haven't yet envisaged.
