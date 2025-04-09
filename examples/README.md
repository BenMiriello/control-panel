# Control Panel Examples

This directory contains example services that you can use to test Control Panel functionality.

## Simple Server

`simple_server.py` is a basic HTTP server that displays a simple webpage. It reads the port from the environment variable `PORT`, which Control Panel automatically sets when managing services.

### Registering the Simple Server

You can register this example server using the following command:

```bash
# From the control-panel directory
./control.py register --name simple-web --command "python3 $(pwd)/examples/simple_server.py"
```

Or using the web interface:

1. Start the web UI: `./start.sh`
2. Go to "Add Service"
3. Fill in the form:
   - Name: `simple-web`
   - Command: `python3 /full/path/to/control-panel/examples/simple_server.py`
   - Port: Leave empty for auto-assignment or set a specific port

### Testing the Service

After registering:

1. Start the service: `./control.py start simple-web` or use the web UI
2. Open a web browser and navigate to `http://localhost:PORT` where PORT is the port assigned to the service
3. You should see a simple webpage showing the server information

## Using Examples with Your Own Services

These examples can serve as templates for creating your own services to be managed by Control Panel. Key things to remember:

1. Always read the `PORT` environment variable in your services
2. Make your services resilient to restarts
3. Use proper logging so that logs can be viewed through Control Panel
