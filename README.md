## spotify-history
(incomplete README)

If sqlite3 is not installed on your target machine:
```
sudo apt-get update && \

sudo apt-get install sqlite3 -y
```

Create a venv, activate it, and install python libraries:
```
python3 -m venv venv && \

source venv/bin/activate && \

pip install -r requirements.txt && \

./run.sh
```

View logs:
```
cat spotify.log
```

